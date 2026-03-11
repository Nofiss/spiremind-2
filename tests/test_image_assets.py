from __future__ import annotations

import os
import time
from pathlib import Path

from spiremind.ui.image_assets import (
    list_recent_uploaded_assets,
    persist_uploaded_image,
    resolve_image_source,
    validate_uploaded_image,
)


class DummyUpload:
    def __init__(self, name: str, content_type: str, payload: bytes) -> None:
        self.name = name
        self.type = content_type
        self.size = len(payload)
        self._payload = payload

    def getvalue(self) -> bytes:
        return self._payload


def test_resolve_image_source_prefers_upload(tmp_path: Path) -> None:
    upload = DummyUpload("card.png", "image/png", b"pngbytes")
    resolved = resolve_image_source(
        image_url="https://example.com/card.png",
        uploaded_file=upload,
        scope="card",
        entity_name="Flame Shield",
        upload_dir=tmp_path,
    )
    assert resolved.startswith(str(tmp_path).replace("\\", "/"))
    assert resolved.endswith(".png")


def test_resolve_image_source_uses_url_without_upload() -> None:
    resolved = resolve_image_source(
        image_url=" https://example.com/event.png ",
        uploaded_file=None,
        scope="event",
        entity_name="Random Event",
    )
    assert resolved == "https://example.com/event.png"


def test_validate_rejects_large_upload() -> None:
    huge = DummyUpload("big.png", "image/png", b"x" * (3 * 1024 * 1024 + 1))
    error = validate_uploaded_image(huge)
    assert error is not None
    assert "too large" in error.lower()


def test_validate_rejects_bad_extension() -> None:
    bad = DummyUpload("note.txt", "text/plain", b"abc")
    error = validate_uploaded_image(bad)
    assert error is not None
    assert "extension" in error.lower()


def test_list_recent_uploaded_assets_returns_latest_first(tmp_path: Path) -> None:
    one = DummyUpload("a.png", "image/png", b"a")
    two = DummyUpload("b.png", "image/png", b"b")
    p1 = persist_uploaded_image(one, "card", "First", upload_dir=tmp_path)
    p2 = persist_uploaded_image(two, "card", "Second", upload_dir=tmp_path)
    now = time.time()
    os.utime(Path(p1), (now - 10, now - 10))
    os.utime(Path(p2), (now, now))
    listed = list_recent_uploaded_assets(upload_dir=tmp_path, limit=2)
    assert listed[0] == p2
    assert listed[1] == p1
