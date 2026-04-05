"""Markdown report generation for the description dependency parser."""
from datetime import datetime, timezone
from pathlib import Path


def generate_report(results: list[dict], output_path: Path) -> None:
    """Write a human-readable markdown report of the analysis results."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total_deps = sum(len(r.get("dependencies", [])) for r in results)
    by_confidence = {"high": [], "medium": [], "low": []}

    for result in results:
        for dep in result.get("dependencies", []):
            conf = dep.get("confidence", "medium").lower()
            if conf not in by_confidence:
                conf = "medium"
            by_confidence[conf].append((result, dep))

    lines = [
        "# Description Dependency Analysis Report",
        "",
        f"**Generated**: {now}",
        f"**Creations with dependencies**: {len(results)}",
        f"**Total rules detected**: {total_deps}",
        f"**High confidence**: {len(by_confidence['high'])}",
        f"**Medium confidence**: {len(by_confidence['medium'])}",
        f"**Low confidence**: {len(by_confidence['low'])}",
        "",
        "---",
        "",
    ]

    for level in ("high", "medium", "low"):
        entries = by_confidence[level]
        if not entries:
            continue

        lines.append(f"## {level.title()} Confidence ({len(entries)} rules)")
        lines.append("")

        for result, dep in entries:
            lines.append(f"### {result['title']}")
            source_plugin = dep.get("source_plugin", "?")
            after = dep.get("load_after", "?")
            matched = dep.get("matched_creation", "?")
            lines.append(f"- **Rule**: `{source_plugin}` load after `{after}`")
            lines.append(f"- **Matched to**: {matched}")
            source_text = dep.get("source_text", "")
            if source_text:
                # Truncate and indent source text
                truncated = source_text[:200]
                if len(source_text) > 200:
                    truncated += "..."
                lines.append(f"- **Source text**: \"{truncated}\"")
            reasoning = dep.get("reasoning", "")
            if reasoning:
                lines.append(f"- **Reasoning**: {reasoning}")
            lines.append("")

        lines.append("---")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
