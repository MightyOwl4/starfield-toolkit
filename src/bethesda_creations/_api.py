"""Low-level HTTP helpers for the Bethesda Creations API."""
import re

import httpx

from bethesda_creations.models import CreationInfo

CREATIONS_API = "https://api.bethesda.net/ugcmods/v2/content/{uuid}"
CREATIONS_SEARCH_API = "https://api.bethesda.net/ugcmods/v2/content"
CDN_CONFIG_URL = "https://cdn.bethesda.net/data/core"


def fetch_bnet_key(timeout: int = 15) -> str:
    """Fetch the public API key from Bethesda's CDN config."""
    resp = httpx.get(CDN_CONFIG_URL, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["ugc"]["bnetKey"]


def content_id_to_uuid(content_id: str) -> str | None:
    """Extract UUID from content ID like 'TM_00dbbd21-c13c-400c-...'."""
    if content_id.startswith("TM_"):
        return content_id[3:]
    if re.match(r"^[0-9a-f]{8}-", content_id):
        return content_id
    return None


def search_uuid_by_title(client: httpx.Client, title: str) -> str | None:
    """Search the Creations API for a creation by title, return its UUID."""
    try:
        resp = client.get(CREATIONS_SEARCH_API, params={
            "product": "GENESIS",
            "search": title,
        })
        if resp.status_code != 200:
            return None
        items = resp.json().get("platform", {}).get("response", {}).get("data", [])
        for item in items:
            if item.get("title", "").lower() == title.lower():
                return item.get("content_id")
    except httpx.HTTPError:
        pass
    return None


def _get_platform_data(entries: list, platform: str = "WINDOWS") -> dict | None:
    """Find the entry for a specific platform in a list of per-platform dicts."""
    for entry in entries:
        if isinstance(entry, dict) and entry.get("hardware_platform") == platform:
            return entry
    return None


def parse_response(data: dict) -> CreationInfo:
    """Parse a Creations API JSON response into CreationInfo."""
    resp = data.get("platform", {}).get("response", {})
    info = CreationInfo()

    info.title = resp.get("title")
    info.description = resp.get("description")
    info.author = resp.get("author_displayname")
    info.achievement_friendly = resp.get("achievement_friendly", False)
    info.categories = resp.get("categories", [])

    # Version and size from download (published binaries) — WINDOWS only.
    # The download field is the authoritative per-platform source.
    # release_notes are shared across platforms and can be misleading.
    windows_dl = _get_platform_data(resp.get("download", []), "WINDOWS")
    if windows_dl:
        published = windows_dl.get("published", [])
        if published:
            # First entry is the latest published version
            latest = published[0]
            info.version = latest.get("version_name")
            for _slot, slot_data in latest.get("client", {}).items():
                size_bytes = slot_data.get("size", 0)
                if size_bytes >= 1_073_741_824:
                    info.installation_size = f"{size_bytes / 1_073_741_824:.2f} GB"
                elif size_bytes > 0:
                    info.installation_size = f"{size_bytes / 1_048_576:.2f} MB"
                break

            # Use the latest version's build timestamp as last_updated.
            # The top-level utime is a metadata-edit timestamp (description
            # changes, category tweaks) and does not reflect version releases.
            version_ctime = latest.get("ctime")
            if version_ctime:
                from datetime import datetime, timezone
                info.last_updated = datetime.fromtimestamp(
                    version_ctime, tz=timezone.utc
                ).strftime("%b %d, %Y")

    # Dates from unix timestamps
    if resp.get("first_ptime"):
        from datetime import datetime, timezone
        info.created_on = datetime.fromtimestamp(
            resp["first_ptime"], tz=timezone.utc
        ).strftime("%b %d, %Y")
    # Fallback: use utime only if no version-specific date was found
    if not info.last_updated and resp.get("utime"):
        from datetime import datetime, timezone
        info.last_updated = datetime.fromtimestamp(
            resp["utime"], tz=timezone.utc
        ).strftime("%b %d, %Y")

    # Price from catalog_info
    for catalog in resp.get("catalog_info", []):
        for price_entry in catalog.get("prices", []):
            amount = price_entry.get("amount", 0)
            if amount > 0:
                info.price = amount
                break
        if info.price > 0:
            break

    # Thumbnail URL from preview_image or cover_image objects
    preview = resp.get("preview_image") or {}
    cover = resp.get("cover_image") or {}
    s3key = preview.get("s3key") or cover.get("s3key")
    if s3key:
        bucket = preview.get("s3bucket") or cover.get("s3bucket", "ugcmods.bethesda.net")
        info.thumbnail_url = f"https://{bucket}/{s3key}"

    return info
