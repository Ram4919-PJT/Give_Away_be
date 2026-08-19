from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from core_app.config import settings

ALLOWED_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


def sanitize_filename(name: str) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return cleaned[:180] or "document"


def validate_upload(file: UploadFile, content: bytes) -> None:
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds maximum size of {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_upload_extensions:
        raise ValueError(f"File type {ext or 'unknown'} is not allowed")
    mime = (file.content_type or "").lower()
    if mime and mime not in ALLOWED_MIME:
        raise ValueError(f"MIME type {mime} is not allowed")


async def save_kyc_document(
    *,
    user_id: int,
    request_id: int,
    file: UploadFile,
) -> tuple[str, str, str, int]:
    content = await file.read()
    validate_upload(file, content)
    original = sanitize_filename(file.filename or "document")
    unique = f"{uuid.uuid4().hex}_{original}"
    rel_dir = Path("kyc") / str(user_id) / str(request_id)
    target_dir = settings.upload_dir / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / unique
    target_path.write_bytes(content)
    storage_key = str(rel_dir / unique).replace("\\", "/")
    mime = file.content_type or "application/octet-stream"
    return storage_key, original, mime, len(content)


def resolve_storage_path(storage_key: str) -> Path:
    key = storage_key.replace("\\", "/").lstrip("/")
    if ".." in key.split("/"):
        raise ValueError("Invalid storage key")
    path = (settings.upload_dir / key).resolve()
    root = settings.upload_dir.resolve()
    if not str(path).startswith(str(root)):
        raise ValueError("Invalid storage path")
    if not path.is_file():
        raise FileNotFoundError("Document file not found")
    return path


def delete_storage_file(storage_key: str) -> None:
    try:
        path = resolve_storage_path(storage_key)
        path.unlink(missing_ok=True)
    except (ValueError, FileNotFoundError):
        return
