"""Standalone CLI tool to build a local catalogue of all Bethesda Starfield creations.

Usage:
    python src/scrape_catalogue.py [OPTIONS]

This is a developer tool, not part of the distributed application.
See specs/005-creations-catalogue/ for full specification.
"""
import argparse
import logging
import sys
import time

import httpx

from bethesda_creations._api import (
    CATALOGUE_USER_AGENT,
    CREATIONS_SEARCH_API,
    enumerate_creations,
    fetch_bnet_key,
    fetch_creation_summary,
)
from bethesda_creations.catalogue import (
    api_response_to_entry,
    load_catalogue,
    save_catalogue,
)
from bethesda_creations.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

# Exit codes per contracts/cli.md
EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_FATAL = 2


class RateLimitExhausted(Exception):
    """Raised when HTTP 429 persists after max retries."""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local catalogue of all Starfield creations."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force-refresh all entries (or specific ones with --id)",
    )
    parser.add_argument(
        "--id", dest="ids", action="append", default=[],
        help="Specific content_id(s) to fetch/refresh (repeatable)",
    )
    parser.add_argument(
        "--rate-limit", type=int, default=100,
        help="Max requests per 5-minute window (default: 100)",
    )
    parser.add_argument(
        "--max-entries", type=int, default=None,
        help="Max new entries to process before concluding the session",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Enumerate creations and report count without fetching",
    )
    parser.add_argument(
        "--skip-summaries", action="store_true",
        help="Skip phase 2 (plugin summary fetching via individual detail endpoints)",
    )
    return parser.parse_args(argv)


def _fetch_page_with_retry(
    client: httpx.Client,
    page: int,
    size: int,
    limiter: RateLimiter,
    max_retries: int = 2,
) -> tuple[list[dict], int]:
    """Fetch a page, retrying on HTTP 429 with exponential back-off."""
    for attempt in range(max_retries + 1):
        limiter.acquire()
        try:
            return enumerate_creations(client, page=page, size=size)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                if attempt < max_retries:
                    delay = 2 ** (attempt + 1)  # 2s, then 8s (2^1, 2^3... but simpler: 2, 8)
                    delay = [2, 8][attempt] if attempt < 2 else 2 ** (attempt + 2)
                    print(
                        f"\r429 rate limited. Backing off {delay}s "
                        f"(retry {attempt + 1}/{max_retries})...",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    continue
                raise RateLimitExhausted(
                    f"Still rate-limited after {max_retries} retries"
                ) from exc
            raise


def _print_progress(label: str, current: int, total: int) -> None:
    """Print in-place progress counter to stderr."""
    print(f"\r{label}[{current} of ~{total}]", end="", file=sys.stderr, flush=True)


def _fetch_summary_with_retry(
    client: httpx.Client,
    content_id: str,
    limiter: RateLimiter,
    max_retries: int = 2,
) -> dict | None:
    """Fetch a creation's plugin summary, retrying on HTTP 429."""
    for attempt in range(max_retries + 1):
        limiter.acquire()
        try:
            return fetch_creation_summary(client, content_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                if attempt < max_retries:
                    delay = [2, 8][attempt] if attempt < 2 else 2 ** (attempt + 2)
                    print(
                        f"\r429 rate limited. Backing off {delay}s "
                        f"(retry {attempt + 1}/{max_retries})...",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    continue
                raise RateLimitExhausted(
                    f"Still rate-limited after {max_retries} retries"
                ) from exc
            raise


def run(argv: list[str] | None = None) -> int:
    """Main entry point. Returns exit code."""
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # Fetch API key
    try:
        bnet_key = fetch_bnet_key()
    except Exception as exc:
        print(f"Fatal: cannot fetch API key: {exc}", file=sys.stderr)
        return EXIT_FATAL

    limiter = RateLimiter(max_tokens=args.rate_limit, window_seconds=300.0)

    client = httpx.Client(
        timeout=15,
        follow_redirects=True,
        headers={
            "x-bnet-key": bnet_key,
            "Content-Type": "application/json",
            "User-Agent": CATALOGUE_USER_AGENT,
        },
    )

    catalogue = load_catalogue()
    new_count = 0
    skipped_count = 0
    failed_count = 0
    total_creations = 0
    try:
        # If specific IDs requested, fetch them individually
        if args.ids:
            for content_id in args.ids:
                if content_id in catalogue and not args.force:
                    skipped_count += 1
                    continue
                try:
                    limiter.acquire()
                    resp = client.get(
                        CREATIONS_SEARCH_API,
                        params={"product": "GENESIS", "search": content_id},
                    )
                    resp.raise_for_status()
                    body = resp.json()
                    payload = body.get("platform", {}).get("response", body)
                    items = payload.get("data", [])
                    for item in items:
                        if item.get("content_id") == content_id:
                            catalogue[content_id] = api_response_to_entry(item)
                            new_count += 1
                            break
                    else:
                        print(
                            f"Warning: {content_id} not found",
                            file=sys.stderr,
                        )
                        failed_count += 1
                except Exception as exc:
                    print(
                        f"Error fetching {content_id}: {exc}",
                        file=sys.stderr,
                    )
                    failed_count += 1
            save_catalogue(catalogue)
            _print_summary(new_count, skipped_count, failed_count)
            return EXIT_SUCCESS if not failed_count else EXIT_PARTIAL

        # Paginated full catalogue build
        page = 1
        size = 20
        processed = 0

        while True:
            try:
                items, total_creations = _fetch_page_with_retry(
                    client, page, size, limiter
                )
            except RateLimitExhausted:
                print(
                    f"\nRate limited after {new_count} new entries. "
                    "Run again to continue.",
                    file=sys.stderr,
                )
                save_catalogue(catalogue)
                return EXIT_PARTIAL
            except httpx.HTTPError as exc:
                print(f"\nFatal HTTP error: {exc}", file=sys.stderr)
                save_catalogue(catalogue)
                return EXIT_FATAL

            if not items:
                break

            if args.dry_run:
                print(f"Total creations: {total_creations}")
                return EXIT_SUCCESS

            for item in items:
                content_id = item.get("content_id")
                if not content_id:
                    continue

                processed += 1
                _print_progress("Phase 1: ", processed, total_creations)

                if content_id in catalogue and not args.force:
                    skipped_count += 1
                    continue

                try:
                    catalogue[content_id] = api_response_to_entry(item)
                    new_count += 1
                except Exception as exc:
                    log.warning("Failed to process %s: %s", content_id, exc)
                    failed_count += 1

                if args.max_entries and new_count >= args.max_entries:
                    save_catalogue(catalogue)
                    print("", file=sys.stderr)  # newline after progress
                    _print_summary(new_count, skipped_count, failed_count)
                    print(
                        f"Stopped at --max-entries={args.max_entries}. "
                        "Run again to continue.",
                        file=sys.stderr,
                    )
                    return EXIT_PARTIAL

            # Save after each page for crash safety
            save_catalogue(catalogue)

            # Check if we've processed all pages
            if len(items) < size:
                break
            page += 1

        print("", file=sys.stderr)  # newline after progress
        _print_summary(new_count, skipped_count, failed_count)

        # Phase 2: Fetch plugin summaries for entries that don't have them
        if not args.skip_summaries:
            exit_code = _run_summary_phase(
                client, catalogue, limiter, args, new_count
            )
            if exit_code is not None:
                return exit_code

        return EXIT_SUCCESS

    except KeyboardInterrupt:
        print("\nInterrupted. Saving progress...", file=sys.stderr)
        save_catalogue(catalogue)
        _print_summary(new_count, skipped_count, failed_count)
        return EXIT_PARTIAL

    except Exception as exc:
        print(f"\nFatal error: {exc}", file=sys.stderr)
        try:
            save_catalogue(catalogue)
        except Exception:
            pass
        return EXIT_FATAL

    finally:
        client.close()


def _run_summary_phase(
    client: httpx.Client,
    catalogue: dict,
    limiter: RateLimiter,
    args: argparse.Namespace,
    phase1_new: int,
) -> int | None:
    """Phase 2: fetch plugin summaries for entries missing them.

    Returns an exit code if the phase was interrupted, or None if completed.
    """
    missing = [
        cid for cid, entry in catalogue.items()
        if entry.get("plugin_summary") is None
    ]
    if not missing:
        return None

    print(
        f"\nPhase 2: Fetching plugin summaries for {len(missing)} creations...",
        file=sys.stderr,
    )
    summary_new = 0
    summary_failed = 0
    max_entries = args.max_entries - phase1_new if args.max_entries else None

    for i, content_id in enumerate(missing, 1):
        _print_progress("Phase 2: ", i, len(missing))

        if max_entries is not None and summary_new >= max_entries:
            save_catalogue(catalogue)
            print("", file=sys.stderr)
            print(f"Phase 2: {summary_new} summaries fetched, stopped at --max-entries.")
            print(
                "Run again to continue.",
                file=sys.stderr,
            )
            return EXIT_PARTIAL

        try:
            # fetch_creation_summary makes 2 requests (detail + summary JSON),
            # so acquire the limiter once here; the second request is a CDN
            # fetch that doesn't count against the API rate limit.
            summary = _fetch_summary_with_retry(
                client, content_id, limiter
            )
            catalogue[content_id]["plugin_summary"] = summary  # None if no WINDOWS dl
            summary_new += 1
        except RateLimitExhausted:
            print(
                f"\nPhase 2: Rate limited after {summary_new} summaries. "
                "Run again to continue.",
                file=sys.stderr,
            )
            save_catalogue(catalogue)
            return EXIT_PARTIAL
        except Exception as exc:
            log.warning("Failed summary for %s: %s", content_id, exc)
            # Mark as empty dict so we don't retry failures endlessly
            catalogue[content_id]["plugin_summary"] = {}
            summary_failed += 1

        # Save every 50 summaries for crash safety
        if summary_new % 50 == 0:
            save_catalogue(catalogue)

    save_catalogue(catalogue)
    print("", file=sys.stderr)
    parts = []
    if summary_new:
        parts.append(f"{summary_new} summaries fetched")
    if summary_failed:
        parts.append(f"{summary_failed} failed")
    if parts:
        print(f"Phase 2: {', '.join(parts)}")
    return None


def _print_summary(new: int, skipped: int, failed: int) -> None:
    parts = []
    if new:
        parts.append(f"{new} new")
    if skipped:
        parts.append(f"{skipped} skipped (already in catalogue)")
    if failed:
        parts.append(f"{failed} failed")
    if parts:
        print(f"Done: {', '.join(parts)}")
    else:
        print("Done: nothing to do")


if __name__ == "__main__":
    sys.exit(run())
