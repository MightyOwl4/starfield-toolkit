"""Fetch creation metadata from Bethesda's Creations API."""
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import NamedTuple

import httpx

from starfield_tool.models import Creation
from starfield_tool.base import StatusBarAPI

CREATIONS_API = "https://api.bethesda.net/ugcmods/v2/content/{uuid}"
CDN_CONFIG_URL = "https://cdn.bethesda.net/data/core"
REQUEST_TIMEOUT = 15


@dataclass
class CreationPageInfo:
    """Metadata from the Bethesda Creations API for a single creation."""
    version: str | None = None
    author: str | None = None
    price: int = 0  # 0 = free, >0 = Creations credits
    installation_size: str | None = None
    last_updated: str | None = None
    created_on: str | None = None
    categories: list[str] = field(default_factory=list)
    achievement_friendly: bool = False
    thumbnail_url: str | None = None


def _compare_versions(installed: str, available: str) -> bool:
    """Return True if available is newer than installed.

    Uses simple tuple comparison of numeric version parts.
    Falls back to string comparison if non-numeric.
    """
    try:
        inst_parts = tuple(int(x) for x in installed.split("."))
        avail_parts = tuple(int(x) for x in available.split("."))
        return avail_parts > inst_parts
    except (ValueError, AttributeError):
        return available > installed


def _content_id_to_uuid(content_id: str) -> str | None:
    """Extract UUID from content ID like 'TM_00dbbd21-c13c-400c-...'."""
    if content_id.startswith("TM_"):
        return content_id[3:]
    # If it already looks like a UUID, return as-is
    if re.match(r"^[0-9a-f]{8}-", content_id):
        return content_id
    return None


def _parse_api_response(data: dict) -> CreationPageInfo:
    """Parse a Creations API JSON response into CreationPageInfo."""
    resp = data.get("platform", {}).get("response", {})
    info = CreationPageInfo()

    info.author = resp.get("author_displayname")
    info.achievement_friendly = resp.get("achievement_friendly", False)
    info.categories = resp.get("categories", [])

    # Version from release_notes (per-platform, prefer WINDOWS)
    for platform_notes in resp.get("release_notes", []):
        if platform_notes.get("hardware_platform") == "WINDOWS":
            notes = platform_notes.get("release_notes", [])
            if notes:
                info.version = notes[0].get("version_name")
            break

    # Installation size from download info (WINDOWS platform)
    for platform_dl in resp.get("download", []):
        if platform_dl.get("hardware_platform") == "WINDOWS":
            for pub in platform_dl.get("published", []):
                for _slot, slot_data in pub.get("client", {}).items():
                    size_bytes = slot_data.get("size", 0)
                    if size_bytes >= 1_073_741_824:
                        info.installation_size = f"{size_bytes / 1_073_741_824:.2f} GB"
                    elif size_bytes > 0:
                        info.installation_size = f"{size_bytes / 1_048_576:.2f} MB"
                    break
                break
            break

    # Dates from unix timestamps
    if resp.get("first_ptime"):
        from datetime import datetime, timezone
        info.created_on = datetime.fromtimestamp(
            resp["first_ptime"], tz=timezone.utc
        ).strftime("%b %d, %Y")
    if resp.get("utime"):
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


def _fetch_bnet_key() -> str:
    """Fetch the public API key from Bethesda's CDN config."""
    resp = httpx.get(CDN_CONFIG_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["ugc"]["bnetKey"]


CREATIONS_SEARCH_API = "https://api.bethesda.net/ugcmods/v2/content"


def _search_uuid_by_title(
    client: httpx.Client, title: str,
) -> str | None:
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


def _fetch_creation_info(
    creations: list[Creation],
    status_bar: StatusBarAPI | None = None,
) -> dict[str, CreationPageInfo]:
    """Fetch metadata for creations via Bethesda's Creations API.

    Returns a dict mapping content_id -> CreationPageInfo.
    """
    bnet_key = _fetch_bnet_key()

    results: dict[str, CreationPageInfo] = {}
    client = httpx.Client(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={
            "x-bnet-key": bnet_key,
            "Content-Type": "application/json",
        },
    )

    try:
        for i, creation in enumerate(creations):
            if status_bar:
                status_bar.set_task(
                    f"Fetching creation info ({i + 1}/{len(creations)})..."
                )

            uuid = _content_id_to_uuid(creation.content_id)
            if not uuid:
                uuid = _search_uuid_by_title(client, creation.display_name)
            if not uuid:
                continue

            try:
                url = CREATIONS_API.format(uuid=uuid)
                resp = client.get(url)
                if resp.status_code == 200:
                    page_info = _parse_api_response(resp.json())
                    results[creation.content_id] = page_info
            except httpx.HTTPError:
                continue
    finally:
        client.close()

    return results


class CheckResult(NamedTuple):
    """Result of a check operation with skipped-creation count."""
    creations: list[Creation]
    skipped: int  # creations not found on Bethesda Creations


def check_for_updates(
    creations: list[Creation],
    status_bar: StatusBarAPI,
) -> CheckResult:
    """Check for updates and return a new list with update info populated.

    Does NOT mutate the input list — returns deep copies with
    available_version and has_update fields set.
    """
    try:
        latest = _fetch_creation_info(creations, status_bar)
    except Exception:
        # Network failure — return unchanged copies
        return CheckResult([deepcopy(c) for c in creations], 0)

    result = []
    skipped = 0
    for creation in creations:
        c = deepcopy(creation)
        page_info = latest.get(c.content_id)
        if page_info and page_info.version:
            c.available_version = page_info.version
            c.has_update = _compare_versions(c.installed_version, page_info.version)
        elif not page_info:
            skipped += 1
        result.append(c)

    return CheckResult(result, skipped)


def check_achievements(
    creations: list[Creation],
    status_bar: StatusBarAPI,
) -> CheckResult:
    """Check achievement friendliness for all creations.

    Does NOT mutate the input list — returns deep copies with
    achievement_friendly field set.
    """
    try:
        info = _fetch_creation_info(creations, status_bar)
    except Exception:
        return CheckResult([deepcopy(c) for c in creations], 0)

    result = []
    skipped = 0
    for creation in creations:
        c = deepcopy(creation)
        page_info = info.get(c.content_id)
        if page_info:
            c.achievement_friendly = page_info.achievement_friendly
        else:
            skipped += 1
        result.append(c)

    return CheckResult(result, skipped)
