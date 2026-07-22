#!/usr/bin/env python3
"""Build a deterministic benchmark APK with controlled static-analysis signals."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.siber.benchmark.fixture"
    android:versionCode="1"
    android:versionName="1.0.0-benchmark">
    <uses-permission android:name="android.permission.READ_SMS" />
    <uses-permission android:name="android.permission.CAMERA" />
    <application
        android:label="SIBER Benchmark Fixture"
        android:debuggable="true"
        android:allowBackup="true"
        android:usesCleartextTraffic="true">
        <activity android:name=".ExportedActivity" android:exported="true" />
    </application>
</manifest>
"""

NETWORK_CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>
"""

STRINGS_XML = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="fake_api_key">FAKE_BENCHMARK_KEY_NOT_REAL_0123456789abcdef</string>
</resources>
"""

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

FIXTURE_ENTRIES: tuple[tuple[str, bytes], ...] = (
    ("AndroidManifest.xml", MANIFEST.encode("utf-8")),
    ("classes.dex", b"dex\n035\x00benchmark"),
    ("res/values/strings.xml", STRINGS_XML.encode("utf-8")),
    ("res/xml/network_security_config.xml", NETWORK_CONFIG.encode("utf-8")),
)


def fixture_source_hash() -> str:
    """Stable identity for fixture content — used for regression gates, not artifact SHA."""
    payload = "\n---\n".join(
        [MANIFEST.strip(), NETWORK_CONFIG.strip(), STRINGS_XML.strip()]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_zip_entry(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(filename=name)
    info.date_time = FIXED_ZIP_TIME
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    zf.writestr(info, data)


def build_apk(output: Path) -> tuple[str, str]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in FIXTURE_ENTRIES:
            _write_zip_entry(zf, name, data)
    data = buffer.getvalue()
    output.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    source_hash = fixture_source_hash()
    meta = {
        "sha256": digest,
        "fixture_source_hash": source_hash,
        "size": len(data),
        "package": "com.siber.benchmark.fixture",
        "deterministic": True,
    }
    output.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return digest, source_hash


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "fixture.apk"
    apk_sha, source_hash = build_apk(out)
    print(f"Built {out} sha256={apk_sha} fixture_source_hash={source_hash}")
