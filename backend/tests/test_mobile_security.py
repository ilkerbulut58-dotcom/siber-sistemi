"""Tests for mobile application security (Phase 9B)."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.mobile.analyzers.android_static import AndroidStaticAnalyzer
from app.mobile.storage import store_mobile_artifact, validate_apk_upload


def _make_fake_apk(
    manifest: str | None = None,
    *,
    extra_entries: dict[str, bytes] | None = None,
) -> bytes:
    default_manifest = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.testapp"
    android:versionCode="1"
    android:versionName="1.0.0">
    <application android:label="Test App"
        android:debuggable="true"
        android:allowBackup="true"
        android:usesCleartextTraffic="true">
        <activity android:name=".MainActivity" android:exported="true" />
    </application>
    <uses-permission android:name="android.permission.READ_SMS" />
</manifest>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("AndroidManifest.xml", manifest or default_manifest)
        zf.writestr("classes.dex", b"dex\n035\x00")
        if extra_entries:
            for name, content in extra_entries.items():
                zf.writestr(name, content)
    return buffer.getvalue()


def _make_zip_bomb_apk() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = """<?xml version="1.0"?><manifest package="com.bomb.app"></manifest>"""
        zf.writestr("AndroidManifest.xml", manifest)
        zf.writestr("bomb.bin", b"\x00" * (2 * 1024 * 1024))
    return buffer.getvalue()


async def _mobile_context(client: AsyncClient) -> tuple[dict, dict, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "mobile@example.com", "password": "SecurePass123!", "full_name": "Mobile"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": "Mobile Org"}, headers=headers)
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "Mobile Project", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]
    return headers, org, project


def _upload_form(project_id: str, **extra: str) -> dict[str, str]:
    return {"project_id": project_id, "authorization_accepted": "true", **extra}


@pytest.mark.asyncio
async def test_upload_requires_authorization(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile"))
    get_settings.cache_clear()

    headers, org, project = await _mobile_context(client)
    response = await client.post(
        f"/api/v1/organizations/{org['id']}/mobile/applications",
        headers=headers,
        data={"project_id": project["id"], "authorization_accepted": "false"},
        files={"file": ("app.apk", _make_fake_apk(), "application/vnd.android.package-archive")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AUTHORIZATION_REQUIRED"


@pytest.mark.asyncio
async def test_mobile_report_json(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile"))
    get_settings.cache_clear()

    headers, org, project = await _mobile_context(client)

    with patch("app.api.v1.mobile.dispatch_mobile_analysis", new=_run_analysis_inline):
        upload = await client.post(
            f"/api/v1/organizations/{org['id']}/mobile/applications",
            headers=headers,
            data=_upload_form(project["id"]),
            files={"file": ("report.apk", _make_fake_apk(), "application/vnd.android.package-archive")},
        )
    assert upload.status_code == 201
    app_id = upload.json()["data"]["id"]

    report = await client.get(
        f"/api/v1/organizations/{org['id']}/mobile/applications/{app_id}/report?format=json",
        headers=headers,
    )
    assert report.status_code == 200
    payload = report.json()
    assert payload["application"]["id"] == app_id
    assert "findings" in payload
    assert payload["scope"]["method"] == "static_apk_analysis"


@pytest.mark.asyncio
async def test_upload_rejects_non_apk(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile"))
    get_settings.cache_clear()

    headers, org, project = await _mobile_context(client)
    response = await client.post(
        f"/api/v1/organizations/{org['id']}/mobile/applications",
        headers=headers,
        data=_upload_form(project["id"]),
        files={"file": ("bad.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_APK"


@pytest.mark.asyncio
async def test_upload_rejects_path_traversal_filename(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile"))
    get_settings.cache_clear()

    headers, org, project = await _mobile_context(client)
    apk = _make_fake_apk()
    response = await client.post(
        f"/api/v1/organizations/{org['id']}/mobile/applications",
        headers=headers,
        data=_upload_form(project["id"]),
        files={"file": ("../../evil.apk", apk, "application/vnd.android.package-archive")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PATH_TRAVERSAL"


@pytest.mark.asyncio
async def test_upload_rejects_zip_bomb(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile"))
    get_settings.cache_clear()

    headers, org, project = await _mobile_context(client)
    response = await client.post(
        f"/api/v1/organizations/{org['id']}/mobile/applications",
        headers=headers,
        data=_upload_form(project["id"]),
        files={"file": ("bomb.apk", _make_zip_bomb_apk(), "application/vnd.android.package-archive")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ZIP_BOMB"


@pytest.mark.asyncio
async def test_upload_requires_developer_role(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile"))
    get_settings.cache_clear()

    owner = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner-mobile@example.com", "password": "SecurePass123!", "full_name": "Owner"},
    )
    owner_headers = {"Authorization": f"Bearer {owner.json()['data']['tokens']['access_token']}"}
    org = (
        await client.post("/api/v1/organizations", json={"name": "Role Org"}, headers=owner_headers)
    ).json()["data"]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "P", "environment": "staging"},
            headers=owner_headers,
        )
    ).json()["data"]

    viewer = await client.post(
        "/api/v1/auth/register",
        json={"email": "viewer-mobile@example.com", "password": "SecurePass123!", "full_name": "Viewer"},
    )
    viewer_headers = {"Authorization": f"Bearer {viewer.json()['data']['tokens']['access_token']}"}
    await client.post(
        f"/api/v1/organizations/{org['id']}/members/invite",
        json={"email": "viewer-mobile@example.com", "role": "viewer"},
        headers=owner_headers,
    )

    response = await client.post(
        f"/api/v1/organizations/{org['id']}/mobile/applications",
        headers=viewer_headers,
        data=_upload_form(project["id"]),
        files={"file": ("app.apk", _make_fake_apk(), "application/vnd.android.package-archive")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upload_and_analyze_apk(client: AsyncClient, tmp_path, monkeypatch) -> None:
    storage_dir = tmp_path / "mobile"
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(storage_dir))
    get_settings.cache_clear()

    headers, org, project = await _mobile_context(client)
    apk = _make_fake_apk()

    with patch("app.api.v1.mobile.dispatch_mobile_analysis", new=_run_analysis_inline):
        upload = await client.post(
            f"/api/v1/organizations/{org['id']}/mobile/applications",
            headers=headers,
            data=_upload_form(project["id"], environment="staging"),
            files={"file": ("test.apk", apk, "application/vnd.android.package-archive")},
        )

    assert upload.status_code == 201
    body = upload.json()["data"]
    assert body["duplicate"] is False
    assert body["analysis_status"] in ("completed", "queued")

    app_id = body["id"]
    detail = await client.get(
        f"/api/v1/organizations/{org['id']}/mobile/applications/{app_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["package_name"] == "com.example.testapp"

    findings = await client.get(
        f"/api/v1/organizations/{org['id']}/mobile/applications/{app_id}/findings",
        headers=headers,
    )
    assert findings.status_code == 200
    titles = {f["title"] for f in findings.json()["data"]}
    assert "Application is debuggable" in titles
    assert "Application backup is allowed" in titles


async def _run_analysis_inline(app_id, **kwargs) -> None:
    from app.core.database import async_session_factory
    from app.mobile.services.mobile_service import MobileService

    async with async_session_factory() as session:
        await MobileService(session).run_analysis(app_id)


@pytest.mark.asyncio
async def test_duplicate_sha256_detected(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "mobile"))
    get_settings.cache_clear()

    headers, org, project = await _mobile_context(client)
    apk = _make_fake_apk()

    with patch("app.api.v1.mobile.dispatch_mobile_analysis", new=_run_analysis_inline):
        first = await client.post(
            f"/api/v1/organizations/{org['id']}/mobile/applications",
            headers=headers,
            data=_upload_form(project["id"]),
            files={"file": ("one.apk", apk, "application/vnd.android.package-archive")},
        )
        second = await client.post(
            f"/api/v1/organizations/{org['id']}/mobile/applications",
            headers=headers,
            data=_upload_form(project["id"]),
            files={"file": ("two.apk", apk, "application/vnd.android.package-archive")},
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["data"]["duplicate"] is True
    assert second.json()["data"]["id"] == first.json()["data"]["id"]


def test_validate_apk_upload_ok() -> None:
    apk = _make_fake_apk()
    name, digest = validate_apk_upload("sample.apk", apk)
    assert name == "sample.apk"
    assert len(digest) == 64


def test_store_mobile_artifact_writes_private_path(tmp_path, monkeypatch) -> None:
    from uuid import uuid4

    monkeypatch.setenv("MOBILE_STORAGE_PATH", str(tmp_path / "store"))
    get_settings.cache_clear()

    org_id = uuid4()
    stored = store_mobile_artifact(org_id, "demo.apk", _make_fake_apk())
    assert stored.storage_path.is_file()
    assert stored.storage_path.name.startswith(stored.stored_filename)


def test_android_analyzer_manifest_checks(tmp_path) -> None:
    apk_path = tmp_path / "test.apk"
    apk_path.write_bytes(_make_fake_apk())
    result = AndroidStaticAnalyzer().analyze(apk_path)

    assert result.package_name == "com.example.testapp"
    rule_ids = {f.source_rule_id for f in result.findings}
    assert "mobile-debuggable" in rule_ids
    assert "mobile-allow-backup" in rule_ids
    assert "mobile-cleartext-traffic" in rule_ids
    assert "mobile-exported-component" in rule_ids
    assert any(r.startswith("mobile-permission-") for r in rule_ids)


def test_android_analyzer_detects_secrets(tmp_path) -> None:
    secret_manifest = """<?xml version="1.0"?><manifest package="com.secret.app"></manifest>"""
    apk = _make_fake_apk(
        manifest=secret_manifest,
        extra_entries={
            "assets/config.properties": b"api_key='supersecretvalue12345678'",
        },
    )
    apk_path = tmp_path / "secret.apk"
    apk_path.write_bytes(apk)
    result = AndroidStaticAnalyzer().analyze(apk_path)
    assert any(f.source_rule_id.startswith("mobile-secret-") for f in result.findings)


def test_validate_rejects_oversized(monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_MAX_UPLOAD_BYTES", "128")
    get_settings.cache_clear()
    with pytest.raises(AppError) as exc:
        validate_apk_upload("big.apk", _make_fake_apk())
    assert exc.value.code == "FILE_TOO_LARGE"
