"""Secure mobile artifact storage and upload validation."""

from __future__ import annotations

import hashlib
import io
import os
import re
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.exceptions import AppError

MAX_ZIP_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_ENTRY_READ_BYTES = 256 * 1024
SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass
class StoredMobileArtifact:
    original_filename: str
    stored_filename: str
    storage_path: Path
    sha256: str
    file_size: int


@dataclass
class StagedMobileArtifact:
    original_filename: str
    staging_path: Path
    sha256: str
    file_size: int


class AsyncUpload(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


def _safe_filename(original: str) -> str:
    if not original or original in {".", ".."}:
        raise AppError("INVALID_FILENAME", "Invalid upload filename.", status_code=400)
    if ".." in original or "/" in original or "\\" in original:
        raise AppError("PATH_TRAVERSAL", "Path traversal in filename is not allowed.", status_code=400)
    name = Path(original).name
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not sanitized or sanitized.startswith("."):
        raise AppError("INVALID_FILENAME", "Invalid upload filename.", status_code=400)
    return sanitized


def _is_zip_archive(data: bytes | Path) -> bool:
    try:
        source = io.BytesIO(data) if isinstance(data, bytes) else data
        with zipfile.ZipFile(source) as zf:
            zf.namelist()
        return True
    except zipfile.BadZipFile:
        return False


def _validate_zip_bomb(data: bytes | Path) -> None:
    if not _is_zip_archive(data):
        raise AppError("INVALID_APK", "Upload must be a valid ZIP/APK archive.", status_code=400)

    try:
        source = io.BytesIO(data) if isinstance(data, bytes) else data
        with zipfile.ZipFile(source) as zf:
            if len(zf.infolist()) > MAX_ZIP_ENTRIES:
                raise AppError(
                    "ZIP_BOMB",
                    f"Archive exceeds maximum entry count ({MAX_ZIP_ENTRIES}).",
                    status_code=400,
                )

            total_uncompressed = 0
            entry_names: set[str] = set()
            for info in zf.infolist():
                if info.filename in entry_names:
                    raise AppError(
                        "INVALID_APK",
                        "Archive contains duplicate entry names.",
                        status_code=400,
                    )
                entry_names.add(info.filename)
                if info.filename.startswith("/") or ".." in Path(info.filename).parts:
                    raise AppError(
                        "PATH_TRAVERSAL",
                        "Archive contains unsafe entry paths.",
                        status_code=400,
                    )
                if info.flag_bits & 0x1:
                    raise AppError(
                        "INVALID_APK",
                        "Encrypted APK archives are not supported.",
                        status_code=400,
                    )
                unix_file_type = (info.external_attr >> 16) & 0o170000
                if unix_file_type == 0o120000:
                    raise AppError(
                        "PATH_TRAVERSAL",
                        "Archive contains symbolic link entries.",
                        status_code=400,
                    )

                uncompressed = info.file_size
                compressed = max(info.compress_size, 1)
                ratio = uncompressed / compressed
                if ratio > MAX_COMPRESSION_RATIO:
                    raise AppError(
                        "ZIP_BOMB",
                        "Suspicious compression ratio detected in archive.",
                        status_code=400,
                    )

                total_uncompressed += uncompressed
                if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                    raise AppError(
                        "ZIP_BOMB",
                        "Archive uncompressed size exceeds allowed limit.",
                        status_code=400,
                    )
            names = set(zf.namelist())
            if "AndroidManifest.xml" not in names or not any(
                name.startswith("classes") and name.endswith(".dex") for name in names
            ):
                raise AppError(
                    "INVALID_APK",
                    "Archive does not contain required Android APK entries.",
                    status_code=400,
                )
            manifest_info = zf.getinfo("AndroidManifest.xml")
            if manifest_info.file_size > MAX_ENTRY_READ_BYTES:
                raise AppError(
                    "INVALID_APK",
                    "Android manifest exceeds the allowed inspection size.",
                    status_code=400,
                )
    except zipfile.BadZipFile as exc:
        raise AppError("INVALID_APK", "Upload must be a valid ZIP/APK archive.", status_code=400) from exc


def validate_apk_upload(filename: str, data: bytes) -> tuple[str, str]:
    """Validate upload and return (safe_original_name, sha256)."""
    settings = get_settings()
    if len(data) == 0:
        raise AppError("EMPTY_UPLOAD", "Uploaded file is empty.", status_code=400)
    if len(data) > settings.mobile_max_upload_bytes:
        raise AppError(
            "FILE_TOO_LARGE",
            f"Upload exceeds maximum size of {settings.mobile_max_upload_bytes} bytes.",
            status_code=400,
        )

    safe_name = _safe_filename(filename)
    lower = safe_name.lower()
    if not lower.endswith(".apk"):
        raise AppError("INVALID_APK", "Only .apk files are supported.", status_code=400)

    _validate_zip_bomb(data)
    digest = hashlib.sha256(data).hexdigest()
    return safe_name, digest


def storage_root() -> Path:
    root = Path(get_settings().mobile_storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def org_storage_dir(organization_id: uuid.UUID) -> Path:
    root = storage_root()
    org_dir = (root / str(organization_id)).resolve()
    if not str(org_dir).startswith(str(root)):
        raise AppError("STORAGE_ERROR", "Invalid storage path.", status_code=500)
    org_dir.mkdir(parents=True, exist_ok=True)
    return org_dir


def store_mobile_artifact(
    organization_id: uuid.UUID,
    original_filename: str,
    data: bytes,
) -> StoredMobileArtifact:
    safe_name, sha256 = validate_apk_upload(original_filename, data)
    org_dir = org_storage_dir(organization_id)
    stored_filename = f"{uuid.uuid4().hex}_{safe_name}"
    target = (org_dir / stored_filename).resolve()
    if not str(target).startswith(str(org_dir)):
        raise AppError("PATH_TRAVERSAL", "Resolved storage path escapes org directory.", status_code=400)
    target.write_bytes(data)
    return StoredMobileArtifact(
        original_filename=safe_name,
        stored_filename=stored_filename,
        storage_path=target,
        sha256=sha256,
        file_size=len(data),
    )


async def stage_mobile_upload(
    organization_id: uuid.UUID,
    original_filename: str,
    upload: AsyncUpload,
) -> StagedMobileArtifact:
    """Stream an upload into private staging without buffering the APK in API memory."""
    settings = get_settings()
    safe_name = _safe_filename(original_filename)
    if not safe_name.lower().endswith(".apk"):
        raise AppError("INVALID_APK", "Only .apk files are supported.", status_code=400)

    org_dir = org_storage_dir(organization_id)
    fd, temporary_name = tempfile.mkstemp(prefix=".upload-", suffix=".apk", dir=org_dir)
    temporary_path = Path(temporary_name)
    digest = hashlib.sha256()
    total = 0
    try:
        with os.fdopen(fd, "wb") as destination:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > settings.mobile_max_upload_bytes:
                    raise AppError(
                        "FILE_TOO_LARGE",
                        f"Upload exceeds maximum size of {settings.mobile_max_upload_bytes} bytes.",
                        status_code=400,
                    )
                digest.update(chunk)
                destination.write(chunk)
        if total == 0:
            raise AppError("EMPTY_UPLOAD", "Uploaded file is empty.", status_code=400)
        _validate_zip_bomb(temporary_path)
        return StagedMobileArtifact(
            original_filename=safe_name,
            staging_path=temporary_path,
            sha256=digest.hexdigest(),
            file_size=total,
        )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def finalize_staged_artifact(
    organization_id: uuid.UUID,
    staged: StagedMobileArtifact,
) -> StoredMobileArtifact:
    """Atomically place a validated staging file under an opaque private name."""
    org_dir = org_storage_dir(organization_id)
    stored_filename = f"{uuid.uuid4().hex}_{staged.original_filename}"
    target = (org_dir / stored_filename).resolve()
    if not str(target).startswith(str(org_dir)):
        raise AppError("PATH_TRAVERSAL", "Resolved storage path escapes org directory.", status_code=400)
    staged.staging_path.replace(target)
    return StoredMobileArtifact(
        original_filename=staged.original_filename,
        stored_filename=stored_filename,
        storage_path=target,
        sha256=staged.sha256,
        file_size=staged.file_size,
    )


def resolve_artifact_path(organization_id: uuid.UUID, stored_filename: str) -> Path:
    if not SAFE_FILENAME_PATTERN.match(stored_filename):
        raise AppError("INVALID_FILENAME", "Invalid stored filename.", status_code=400)
    org_dir = org_storage_dir(organization_id)
    target = (org_dir / stored_filename).resolve()
    if not str(target).startswith(str(org_dir)):
        raise AppError("PATH_TRAVERSAL", "Invalid artifact path.", status_code=400)
    if not target.is_file():
        raise AppError("NOT_FOUND", "Mobile artifact not found on disk.", status_code=404)
    return target


def delete_mobile_artifact(organization_id: uuid.UUID, stored_filename: str) -> None:
    """Remove a private artifact after analysis without trusting its filename."""
    if not SAFE_FILENAME_PATTERN.match(stored_filename):
        raise AppError("INVALID_FILENAME", "Invalid stored filename.", status_code=400)
    org_dir = org_storage_dir(organization_id)
    target = (org_dir / stored_filename).resolve()
    if not str(target).startswith(str(org_dir)):
        raise AppError("PATH_TRAVERSAL", "Invalid artifact path.", status_code=400)
    target.unlink(missing_ok=True)
