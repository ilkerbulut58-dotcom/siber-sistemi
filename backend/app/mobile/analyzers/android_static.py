"""Android APK static analysis (zipfile only, no code execution)."""

from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path

from app.mobile.analyzers.base import MobileAnalysisResult, MobileAnalyzer, MobileFinding
from app.mobile.storage import MAX_ENTRY_READ_BYTES

MANIFEST_PATH = "AndroidManifest.xml"
NETWORK_SECURITY_CONFIG = "res/xml/network_security_config.xml"

DANGEROUS_PERMISSIONS = frozenset(
    {
        "android.permission.READ_SMS",
        "android.permission.RECEIVE_SMS",
        "android.permission.SEND_SMS",
        "android.permission.READ_CONTACTS",
        "android.permission.WRITE_CONTACTS",
        "android.permission.READ_CALL_LOG",
        "android.permission.WRITE_CALL_LOG",
        "android.permission.RECORD_AUDIO",
        "android.permission.CAMERA",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.READ_PHONE_STATE",
        "android.permission.CALL_PHONE",
        "android.permission.PROCESS_OUTGOING_CALLS",
        "android.permission.BODY_SENSORS",
        "android.permission.GET_ACCOUNTS",
    }
)

SECRET_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "aws-access-key",
        re.compile(rb"AKIA[0-9A-Z]{16}"),
        "high",
    ),
    (
        "generic-api-key",
        re.compile(rb"(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        "medium",
    ),
    (
        "private-key-block",
        re.compile(rb"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
        "critical",
    ),
]

EXPORTED_COMPONENT_PATTERN = re.compile(
    rb"android:exported\s*=\s*[\"']true[\"']",
    re.IGNORECASE,
)


def _extract_utf16le_strings(data: bytes, min_len: int = 4) -> list[str]:
    strings: list[str] = []
    i = 0
    while i < len(data) - 1:
        if data[i] == 0 and 32 <= data[i + 1] <= 126:
            start = i
            chars: list[str] = []
            j = i
            while j < len(data) - 1:
                lo, hi = data[j], data[j + 1]
                if hi != 0 or lo < 32 or lo > 126:
                    break
                chars.append(chr(lo))
                j += 2
            if len(chars) >= min_len:
                strings.append("".join(chars))
            i = j + 2
            continue
        i += 1
    return strings


def _extract_utf8_strings(data: bytes, min_len: int = 4) -> list[str]:
    return re.findall(rb"[ -~]{%d,}" % min_len, data)


def _extract_binary_manifest_strings(data: bytes) -> str:
    parts: list[str] = []
    parts.extend(s.decode("utf-8", errors="ignore") for s in _extract_utf8_strings(data))
    parts.extend(_extract_utf16le_strings(data))
    return "\n".join(dict.fromkeys(parts))


def _manifest_search_blob(data: bytes) -> str:
    stripped = data.lstrip()
    if stripped.startswith(b"<?xml") or stripped.startswith(b"<manifest"):
        return data.decode("utf-8", errors="replace")
    return _extract_binary_manifest_strings(data)


def _match_attr(blob: str, attr: str, value: str = "true") -> bool:
    patterns = [
        rf'{attr}\s*=\s*["\']{re.escape(value)}["\']',
        rf'{attr}={re.escape(value)}',
    ]
    return any(re.search(p, blob, re.IGNORECASE) for p in patterns)


def _extract_manifest_metadata(blob: str) -> dict[str, str | None]:
    package = None
    version_name = None
    version_code = None
    app_label = None

    pkg_match = re.search(r'package\s*=\s*"([^"]+)"', blob)
    if pkg_match:
        package = pkg_match.group(1)

    vn_match = re.search(r'android:versionName\s*=\s*"([^"]+)"', blob)
    if vn_match:
        version_name = vn_match.group(1)

    vc_match = re.search(r'android:versionCode\s*=\s*"([^"]+)"', blob)
    if vc_match:
        version_code = vc_match.group(1)

    label_match = re.search(r'android:label\s*=\s*"([^"]+)"', blob)
    if label_match:
        app_label = label_match.group(1)

    return {
        "package_name": package,
        "version_name": version_name,
        "version_code": version_code,
        "application_name": app_label,
    }


def _parse_string_pool(data: bytes) -> list[str]:
    """Best-effort AXML string pool extraction."""
    if len(data) < 8:
        return []
    try:
        _chunk_type, header_size = struct.unpack_from("<HH", data, 0)
        if header_size < 8 or header_size > len(data):
            return []
        string_count, _style_count, _flags, strings_start, _styles_start = struct.unpack_from(
            "<IIIII", data, 8
        )
        if string_count <= 0 or string_count > 5000:
            return _extract_binary_manifest_strings(data).split("\n")

        base = header_size
        offsets = [
            struct.unpack_from("<I", data, base + i * 4)[0]
            for i in range(string_count)
            if base + (i + 1) * 4 <= len(data)
        ]
        pool_start = strings_start if strings_start else header_size + string_count * 4
        strings: list[str] = []
        for offset in offsets:
            pos = pool_start + offset
            if pos + 2 > len(data):
                continue
            length = struct.unpack_from("<H", data, pos)[0]
            if length & 0x8000:
                if pos + 4 > len(data):
                    continue
                length = struct.unpack_from("<H", data, pos + 2)[0]
                pos += 4
            else:
                pos += 2
            end = pos + length * 2
            if end > len(data):
                continue
            try:
                strings.append(data[pos:end].decode("utf-16-le", errors="ignore"))
            except UnicodeDecodeError:
                continue
        if strings:
            return strings
    except struct.error:
        pass
    return _extract_binary_manifest_strings(data).split("\n")


def _manifest_blob_from_zip(zf: zipfile.ZipFile) -> str:
    try:
        raw = zf.read(MANIFEST_PATH)
    except KeyError:
        return ""
    stripped = raw.lstrip()
    if stripped.startswith(b"<?xml") or stripped.startswith(b"<manifest"):
        return raw.decode("utf-8", errors="replace")
    pool_strings = _parse_string_pool(raw)
    if pool_strings:
        return "\n".join(pool_strings)
    return _manifest_search_blob(raw)


def _scan_zip_secrets(zf: zipfile.ZipFile) -> list[MobileFinding]:
    findings: list[MobileFinding] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        name_lower = info.filename.lower()
        if not (
            name_lower.endswith((".xml", ".json", ".properties", ".txt", ".js", ".kotlin", ".java"))
            or "assets/" in name_lower
            or "res/" in name_lower
        ):
            continue
        if info.file_size > MAX_ENTRY_READ_BYTES:
            continue
        try:
            content = zf.read(info.filename)[:MAX_ENTRY_READ_BYTES]
        except (zipfile.BadZipFile, RuntimeError):
            continue
        for rule_id, pattern, severity in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(
                    MobileFinding(
                        source_rule_id=f"mobile-secret-{rule_id}",
                        title=f"Possible secret in APK entry ({rule_id})",
                        description=f"Pattern matched in {info.filename}.",
                        severity=severity,
                        masvs_category="MASVS-STORAGE-1",
                        affected_component=info.filename,
                        evidence={"entry": info.filename, "pattern": rule_id},
                        remediation="Remove secrets from the APK and rotate exposed credentials.",
                        confidence="medium",
                    )
                )
                break
    return findings


def _network_security_findings(zf: zipfile.ZipFile) -> list[MobileFinding]:
    findings: list[MobileFinding] = []
    candidates = [
        name
        for name in zf.namelist()
        if name.endswith("network_security_config.xml") or name == NETWORK_SECURITY_CONFIG
    ]
    for name in candidates:
        try:
            content = zf.read(name)[:MAX_ENTRY_READ_BYTES].decode("utf-8", errors="replace")
        except (KeyError, zipfile.BadZipFile):
            continue
        if re.search(r"cleartextTrafficPermitted\s*=\s*\"true\"", content, re.IGNORECASE):
            findings.append(
                MobileFinding(
                    source_rule_id="mobile-cleartext-network-config",
                    title="Cleartext traffic permitted in network security config",
                    description=f"{name} allows cleartext HTTP traffic.",
                    severity="medium",
                    masvs_category="MASVS-NETWORK-1",
                    affected_component=name,
                    evidence={"config_file": name},
                    remediation="Disable cleartextTrafficPermitted or restrict to debug builds only.",
                )
            )
        if "trust-anchors" in content and "user" in content.lower():
            findings.append(
                MobileFinding(
                    source_rule_id="mobile-user-trust-anchors",
                    title="User-installed CA trust anchors configured",
                    description=f"{name} may trust user CAs, enabling MITM with user consent.",
                    severity="medium",
                    masvs_category="MASVS-NETWORK-2",
                    affected_component=name,
                    evidence={"config_file": name},
                    remediation="Avoid user trust anchors in production builds.",
                )
            )
    return findings


class AndroidStaticAnalyzer(MobileAnalyzer):
    def analyze(self, artifact_path: Path) -> MobileAnalysisResult:
        findings: list[MobileFinding] = []
        metadata: dict[str, str | None] = {
            "package_name": None,
            "version_name": None,
            "version_code": None,
            "application_name": None,
        }

        with zipfile.ZipFile(artifact_path, "r") as zf:
            manifest_blob = _manifest_blob_from_zip(zf)
            if manifest_blob:
                metadata.update(_extract_manifest_metadata(manifest_blob))

            if _match_attr(manifest_blob, "android:debuggable"):
                findings.append(
                    MobileFinding(
                        source_rule_id="mobile-debuggable",
                        title="Application is debuggable",
                        description="android:debuggable is enabled, allowing runtime inspection.",
                        severity="high",
                        masvs_category="MASVS-RESILIENCE-1",
                        affected_component="AndroidManifest.xml",
                        remediation="Set android:debuggable to false for release builds.",
                    )
                )

            if _match_attr(manifest_blob, "android:allowBackup"):
                findings.append(
                    MobileFinding(
                        source_rule_id="mobile-allow-backup",
                        title="Application backup is allowed",
                        description="android:allowBackup may expose app data via adb backup.",
                        severity="medium",
                        masvs_category="MASVS-STORAGE-2",
                        affected_component="AndroidManifest.xml",
                        remediation="Set android:allowBackup to false or use backup rules.",
                    )
                )

            if _match_attr(manifest_blob, "android:usesCleartextTraffic"):
                findings.append(
                    MobileFinding(
                        source_rule_id="mobile-cleartext-traffic",
                        title="Cleartext traffic is permitted",
                        description="android:usesCleartextTraffic allows unencrypted HTTP.",
                        severity="medium",
                        masvs_category="MASVS-NETWORK-1",
                        affected_component="AndroidManifest.xml",
                        remediation="Disable cleartext traffic and use HTTPS exclusively.",
                    )
                )

            if EXPORTED_COMPONENT_PATTERN.search(manifest_blob.encode("utf-8", errors="ignore")):
                findings.append(
                    MobileFinding(
                        source_rule_id="mobile-exported-component",
                        title="Exported Android component detected",
                        description="One or more components are exported (android:exported=true).",
                        severity="medium",
                        masvs_category="MASVS-PLATFORM-1",
                        affected_component="AndroidManifest.xml",
                        evidence={"note": "Review intent filters and permissions on exported components."},
                        remediation="Export only required components and protect with permissions.",
                    )
                )

            for perm in DANGEROUS_PERMISSIONS:
                if perm in manifest_blob:
                    short = perm.rsplit(".", maxsplit=1)[-1]
                    findings.append(
                        MobileFinding(
                            source_rule_id=f"mobile-permission-{short.lower()}",
                            title=f"Dangerous permission requested: {short}",
                            description=f"Manifest declares {perm}.",
                            severity="low",
                            masvs_category="MASVS-PLATFORM-2",
                            affected_component=perm,
                            remediation="Request dangerous permissions only when strictly required.",
                            confidence="high",
                        )
                    )

            findings.extend(_scan_zip_secrets(zf))
            findings.extend(_network_security_findings(zf))

        severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        findings.sort(key=lambda f: (-severity_rank.get(f.severity, 0), f.title))

        return MobileAnalysisResult(
            application_name=metadata.get("application_name"),
            package_name=metadata.get("package_name"),
            version_name=metadata.get("version_name"),
            version_code=metadata.get("version_code"),
            findings=findings,
            summary={
                "checks_run": [
                    "debuggable",
                    "allowBackup",
                    "cleartext",
                    "exported_components",
                    "dangerous_permissions",
                    "secrets_scan",
                    "network_security_config",
                ],
                "findings_by_severity": {
                    sev: sum(1 for f in findings if f.severity == sev)
                    for sev in ("critical", "high", "medium", "low", "info")
                },
            },
        )
