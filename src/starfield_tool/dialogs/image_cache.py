"""Persistent on-disk cache for downloaded thumbnail images.

Stores both the original download and pre-resized variants so that
subsequent reads at a known size are a simple file load with no
CPU-intensive resizing.
"""
from __future__ import annotations

import hashlib
import io
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, quote, urlunsplit

if TYPE_CHECKING:
    from PIL import Image as PILImage


def _cache_dir() -> Path:
    import os
    return Path(os.environ.get("APPDATA", "")) / "StarfieldToolkit" / "images"


def _encode_url(url: str) -> str:
    parts = urlsplit(url)
    safe_path = quote(parts.path, safe="/")
    return urlunsplit(parts._replace(path=safe_path))


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _original_filename(content_id: str, url: str) -> str:
    ext = Path(urlsplit(url).path).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        ext = ".jpg"
    return f"{content_id}_{_url_hash(url)}{ext}"


def _sized_filename(content_id: str, url: str, size: tuple[int, int]) -> str:
    w, h = size
    return f"{content_id}_{_url_hash(url)}_{w}x{h}.png"


def _save_resized(
    original_path: Path, content_id: str, url: str, size: tuple[int, int],
) -> "PILImage.Image | None":
    """Resize the original on disk, save the result, and return it."""
    try:
        from PIL import Image
        img = Image.open(original_path)
        img.load()
        img.thumbnail(size, Image.LANCZOS)
        sized_path = _cache_dir() / _sized_filename(content_id, url, size)
        img.save(sized_path, "PNG")
        return img
    except Exception:
        return None


def get_cached_image(
    content_id: str, url: str, size: tuple[int, int],
) -> "PILImage.Image | None":
    """Return a cached image at the requested size, no resizing if possible."""
    try:
        from PIL import Image
        cache = _cache_dir()

        # Try the pre-resized variant first (fast path — just a file load)
        sized_path = cache / _sized_filename(content_id, url, size)
        if sized_path.is_file():
            img = Image.open(sized_path)
            img.load()
            return img

        # Fall back to original and create the resized variant for next time
        orig_path = cache / _original_filename(content_id, url)
        if orig_path.is_file():
            return _save_resized(orig_path, content_id, url, size)

        return None
    except Exception:
        return None


def download_and_cache(
    content_id: str, url: str, size: tuple[int, int],
) -> "PILImage.Image | None":
    """Download an image, save original + resized variant, return resized."""
    try:
        import httpx
        from PIL import Image

        encoded = _encode_url(url)
        resp = httpx.get(encoded, follow_redirects=True, timeout=10)
        resp.raise_for_status()
        raw = resp.content

        # Save original bytes to disk
        cache = _cache_dir()
        cache.mkdir(parents=True, exist_ok=True)
        orig_path = cache / _original_filename(content_id, url)
        orig_path.write_bytes(raw)

        # Resize, save the sized variant, and return
        img = Image.open(io.BytesIO(raw))
        img.load()
        img.thumbnail(size, Image.LANCZOS)
        sized_path = cache / _sized_filename(content_id, url, size)
        img.save(sized_path, "PNG")
        return img
    except Exception:
        return None


def clear_image_cache() -> None:
    """Delete the entire image cache directory."""
    d = _cache_dir()
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)
