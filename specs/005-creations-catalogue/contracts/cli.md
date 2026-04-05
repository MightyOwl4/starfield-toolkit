# CLI Contract: scrape_catalogue.py

## Command Interface

```
python src/scrape_catalogue.py [OPTIONS]
```

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--force` | boolean | false | Force-refresh all entries (or specific ones with `--id`) |
| `--id` | string (repeatable) | none | Specific content_id(s) to fetch/refresh. Without `--force`, only fetches if missing. |
| `--rate-limit` | integer | 100 | Max requests per 5-minute window |
| `--max-entries` | integer | none (unlimited) | Max new entries to process before concluding the session |
| `--dry-run` | boolean | false | Enumerate creations and report count without scraping |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (all targeted creations scraped or already in catalogue) |
| 1 | Partial completion (session terminated due to rate limiting or `--max-entries` limit; progress saved) |
| 2 | Fatal error (cannot reach API, cannot write catalogue file, etc.) |

## Output

- In-place progress counter to stderr (carriage return, no newline): `[123 of ~1678]` — approximate total derived from page count * items per page after first fetch
- Summary line to stdout on completion: `Done: 300 new, 150 skipped (already in catalogue), 6 failed` or `Rate limited after 300 new entries. Run again to continue.`
- Errors logged to stderr with creation ID and reason
