from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from core_app.config import settings


class LocalStorage:
    def __init__(self, base_dir: Path | None = None, url_prefix: str | None = None) -> None:
        self.base_dir = base_dir or settings.upload_dir
        self.url_prefix = (url_prefix or settings.UPLOAD_URL_PREFIX).rstrip("/")

    def ensure_base_dir(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_item_donation_file(
        self,
        item_donation_id: int,
        upload: UploadFile,
    ) -> str:
        self.ensure_base_dir()
        original_name = Path(upload.filename or "upload").name
        suffix = Path(original_name).suffix.lower()
        if suffix not in settings.allowed_upload_extensions:
            raise ValueError(f"File type not allowed: {suffix or 'unknown'}")

        content = await upload.read()
        if len(content) > settings.MAX_UPLOAD_BYTES:
            raise ValueError(f"File exceeds maximum size of {settings.MAX_UPLOAD_BYTES} bytes")

        target_dir = self.base_dir / "item_donations" / str(item_donation_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        target_path = target_dir / stored_name
        target_path.write_bytes(content)

        return f"{self.url_prefix}/item_donations/{item_donation_id}/{stored_name}"


local_storage = LocalStorage()
