from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}
MAX_UPLOAD_BYTES = 3 * 1024 * 1024
DEFAULT_UPLOAD_DIR = Path("assets/uploads")


def sanitize_entity_name(entity_name: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in entity_name)
    compact = "-".join(part for part in normalized.split("-") if part)
    return compact or "image"


def validate_uploaded_image(
    uploaded_file: Any,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> str | None:
    suffix = Path(str(getattr(uploaded_file, "name", ""))).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        return "Unsupported file extension. Use PNG, JPG, JPEG, WEBP or GIF."

    mime_type = str(getattr(uploaded_file, "type", "")).strip().lower()
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        return "Unsupported MIME type. Upload a valid image file."

    size = getattr(uploaded_file, "size", None)
    if size is None:
        size = len(uploaded_file.getvalue())
    if int(size) > max_bytes:
        max_mb = round(max_bytes / (1024 * 1024), 2)
        return f"Image is too large. Max allowed size is {max_mb} MB."
    return None


def persist_uploaded_image(
    uploaded_file: Any,
    scope: str,
    entity_name: str,
    upload_dir: Path = DEFAULT_UPLOAD_DIR,
) -> str:
    error = validate_uploaded_image(uploaded_file)
    if error:
        raise ValueError(error)

    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(str(getattr(uploaded_file, "name", ""))).suffix.lower()
    file_name = (
        f"{scope}_{sanitize_entity_name(entity_name)}_{uuid.uuid4().hex[:8]}{suffix}"
    )
    output_path = upload_dir / file_name
    output_path.write_bytes(uploaded_file.getvalue())
    return str(output_path).replace("\\", "/")


def resolve_image_source(
    image_url: str,
    uploaded_file: Any | None,
    scope: str,
    entity_name: str,
    upload_dir: Path = DEFAULT_UPLOAD_DIR,
) -> str:
    if uploaded_file is not None:
        return persist_uploaded_image(uploaded_file, scope, entity_name, upload_dir)
    return image_url.strip()


def list_recent_uploaded_assets(
    upload_dir: Path = DEFAULT_UPLOAD_DIR,
    limit: int = 8,
) -> list[str]:
    if not upload_dir.exists():
        return []
    files = [
        path
        for path in upload_dir.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES
    ]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [str(path).replace("\\", "/") for path in files[: max(1, limit)]]
