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


def build_apk(output: Path) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("AndroidManifest.xml", MANIFEST)
        zf.writestr("classes.dex", b"dex\n035\x00benchmark")
        zf.writestr("res/xml/network_security_config.xml", NETWORK_CONFIG)
        zf.writestr("res/values/strings.xml", STRINGS_XML)
    data = buffer.getvalue()
    output.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    meta = {"sha256": digest, "size": len(data), "package": "com.siber.benchmark.fixture"}
    output.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return digest


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "fixture.apk"
    digest = build_apk(out)
    print(f"Built {out} sha256={digest}")
