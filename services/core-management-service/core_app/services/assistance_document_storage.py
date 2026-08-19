from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from core_app.config import settings
from core_app.services.kyc_document_storage import sanitize_filename, validate_upload


async def save_assistance_document(
    *,
    user_id: int,
    application_id: int,
    file: UploadFile,
) -> tuple[str, str, str, int]:
    content = await file.read()
    validate_upload(file, content)
    original = sanitize_filename(file.filename or "document")
    unique = f"{uuid.uuid4().hex}_{original}"
    rel_dir = Path("assistance") / str(user_id) / str(application_id)
    target_dir = settings.upload_dir / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / unique
    target_path.write_bytes(content)
    storage_key = str(rel_dir / unique).replace("\\", "/")
    mime = file.content_type or "application/octet-stream"
    return storage_key, original, mime, len(content)


def resolve_assistance_storage_path(storage_key: str) -> Path:
    from core_app.services.kyc_document_storage import resolve_storage_path

    return resolve_storage_path(storage_key)


def delete_assistance_storage_file(storage_key: str) -> None:
    from core_app.services.kyc_document_storage import delete_storage_file

    delete_storage_file(storage_key)
