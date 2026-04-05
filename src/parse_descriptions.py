"""Standalone CLI tool to parse creation descriptions and generate a load order rule book.

Usage:
    python src/parse_descriptions.py [OPTIONS]

Requires: ANTHROPIC_API_KEY environment variable
Requires: Creations catalogue (run scrape_catalogue.py first)
"""
import argparse
import json
import os
import sys
from pathlib import Path

from description_parser.analyzer import (
    build_reference_list,
    filter_candidates,
    generate_rulebook,
    process_candidates,
)
from description_parser.report import generate_report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse creation descriptions to generate a load order rule book."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show candidate count without making API calls",
    )
    parser.add_argument(
        "--max-entries", type=int, default=None,
        help="Max candidates to process (for testing / cost control)",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-6",
        help="Anthropic model to use (default: claude-sonnet-4-6)",
    )
    return parser.parse_args(argv)


def _load_catalogue() -> dict:
    app_data = os.environ.get("APPDATA", "")
    cat_path = Path(app_data) / "StarfieldToolkit" / "creations_catalogue.json"
    if not cat_path.exists():
        print(
            f"Error: Catalogue not found at {cat_path}\n"
            "Run 'python src/scrape_catalogue.py' first.",
            file=sys.stderr,
        )
        sys.exit(2)
    data = json.loads(cat_path.read_text(encoding="utf-8"))
    return data.get("entries", {})


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # Load catalogue
    print("Loading catalogue...", file=sys.stderr)
    catalogue = _load_catalogue()
    print(f"Catalogue: {len(catalogue)} creations", file=sys.stderr)

    # Filter candidates
    candidates = filter_candidates(catalogue)
    print(f"Candidates: {len(candidates)} creations with dependency hints",
          file=sys.stderr)

    if args.dry_run:
        print(f"\nDry run: {len(candidates)} candidates found")
        # Show top 10
        for c in candidates[:10]:
            print(f"  {c['title']} ({c['plugin_file'] or '?'})")
        if len(candidates) > 10:
            print(f"  ... and {len(candidates) - 10} more")
        return 0

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY environment variable not set.\n"
            "Get your key at https://console.anthropic.com",
            file=sys.stderr,
        )
        return 2

    # Build reference list
    print("Building creation reference list...", file=sys.stderr)
    reference_list = build_reference_list(catalogue)
    ref_tokens = len(reference_list) // 4  # rough estimate
    print(f"Reference list: ~{ref_tokens:,} tokens", file=sys.stderr)

    # Cost estimate
    total = min(len(candidates), args.max_entries) if args.max_entries else len(candidates)
    est_input = (ref_tokens + 300) * total  # ref list + description per call
    est_output = 200 * total
    est_cost = est_input * 3 / 1_000_000 + est_output * 15 / 1_000_000  # Sonnet pricing
    print(f"Estimated cost: ~${est_cost:.2f} for {total} API calls", file=sys.stderr)

    # Create client
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    # Output paths
    app_data = os.environ.get("APPDATA", "")
    data_dir = Path(app_data) / "StarfieldToolkit"
    rulebook_path = data_dir / "patch_order_rules.json"
    report_path = data_dir / "patch_order_report.md"

    def _save_progress(current_results):
        """Incremental save — called every 10 results."""
        rb = generate_rulebook(current_results)
        rulebook_path.parent.mkdir(parents=True, exist_ok=True)
        rulebook_path.write_text(
            json.dumps(rb, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        generate_report(current_results, report_path)

    # Process
    print(f"\nProcessing {total} candidates with {args.model}...", file=sys.stderr)
    results = process_candidates(
        client, candidates, reference_list,
        model=args.model,
        max_entries=args.max_entries,
        save_callback=_save_progress,
    )

    # Final save
    rulebook = generate_rulebook(results)
    rulebook_path.parent.mkdir(parents=True, exist_ok=True)
    rulebook_path.write_text(
        json.dumps(rulebook, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    generate_report(results, report_path)

    # Summary
    total_rules = len(rulebook.get("rules", []))
    total_deps = sum(len(r.get("dependencies", [])) for r in results)
    creations_with_deps = len(results)

    print("\nDone:")
    print(f"  Candidates analyzed: {total}")
    print(f"  Creations with dependencies: {creations_with_deps}")
    print(f"  Total dependencies found: {total_deps}")
    print(f"  Rules in rule book: {total_rules}")
    print(f"  Rule book: {rulebook_path}")
    print(f"  Report: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run())
