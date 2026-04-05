# Quickstart: Creations Text Catalogue

**Branch**: `005-creations-catalogue`

## What This Feature Does

A standalone catalogue builder that enumerates ALL Starfield creations via Bethesda's paginated JSON API, collecting description text, release notes (version history), metadata, and dependency declarations. No web scraping — pure API. This is a developer tool (not part of the distributed app) that feeds into feature 006 (dependency graph).

## How to Run

```bash
# Basic run - fetch all missing creations
python src/scrape_catalogue.py

# Limit to N new entries per session
python src/scrape_catalogue.py --max-entries 500

# Force-refresh entire catalogue
python src/scrape_catalogue.py --force

# Force-refresh specific creation(s)
python src/scrape_catalogue.py --force --id beefc7ae-59f4-4934-b2a5-d04e5264f029

# Custom rate limit (default: 100 requests per 5-minute window)
python src/scrape_catalogue.py --rate-limit 50

# Dry run - enumerate and report count without fetching
python src/scrape_catalogue.py --dry-run
```

## Key Files

| File | Purpose |
|------|---------|
| `src/scrape_catalogue.py` | Standalone CLI entrypoint (argparse) |
| `src/bethesda_creations/_api.py` | [EXTENDED] Add `enumerate_all_creations()` paginated listing |
| `src/bethesda_creations/catalogue.py` | Catalogue file I/O: load, save, merge entries, hashing |
| `src/bethesda_creations/rate_limiter.py` | Token Bucket Filter rate limiter |
| `tests/test_catalogue.py` | Tests for catalogue I/O, hashing, merge logic |
| `tests/test_rate_limiter.py` | Tests for TBF rate limiter |
| `tests/test_scrape_catalogue.py` | Tests for end-to-end scraper logic (mocked HTTP) |

## Output

Catalogue file at `%APPDATA%/StarfieldToolkit/creations_catalogue.json`:
```json
{
  "version": 1,
  "entries": {
    "beefc7ae-59f4-4934-b2a5-d04e5264f029": {
      "title": "Starborn Gravis Suit",
      "author": "BethesdaGameStudios",
      "categories": ["Gear"],
      "price": 0,
      "description": "Explore the mysteries of the universe...",
      "overview": "",
      "release_notes": [{"hardware_platform": "WINDOWS", "release_notes": [{"version_name": "1.0", "note": "Initial Upload", "ctime": 1717532554}]}],
      "required_mods": [],
      "achievement_friendly": true,
      "content_hash": "a1b2c3d4...",
      "fetched_at": "2026-04-05T12:00:00Z"
    }
  }
}
```

## Multi-Pass Operation

The catalogue builder supports multi-pass operation. If interrupted, rate-limited, or capped by `--max-entries`, run it again — it picks up where it left off by skipping already-catalogued entries. At default rate (100 req/5min), ~248 page requests covers all ~4,954 creations in about 12 minutes.
