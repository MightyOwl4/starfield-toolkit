"""Core analysis logic: candidate filtering, reference list building, LLM orchestration."""
import json
import logging
import sys
import time

log = logging.getLogger(__name__)

# Keywords that suggest a creation may contain dependency info
_CANDIDATE_KEYWORDS = ("patch", "compatibility", "addon", "fix")


def filter_candidates(catalogue: dict) -> list[dict]:
    """Filter catalogue entries likely to contain dependency hints.

    Returns entries where title contains keywords like "patch", "compatibility",
    "addon", "fix" (case-insensitive) OR required_mods is non-empty.
    """
    candidates = []
    for content_id, entry in catalogue.items():
        title = entry.get("title", "").lower()
        has_keyword = any(kw in title for kw in _CANDIDATE_KEYWORDS)
        has_reqs = bool(entry.get("required_mods"))
        description = entry.get("description", "").strip()

        if (has_keyword or has_reqs) and description:
            # Find the primary plugin filename
            plugin_file = ""
            summary = entry.get("plugin_summary")
            if summary and isinstance(summary, dict):
                for f in summary.get("Files", []):
                    if f.lower().endswith((".esm", ".esp", ".esl")):
                        # Strip "Data\\" prefix if present
                        plugin_file = f.replace("Data\\", "").replace("data\\", "")
                        break

            candidates.append({
                "content_id": content_id,
                "title": entry.get("title", ""),
                "description": description,
                "plugin_file": plugin_file,
            })

    return candidates


def build_reference_list(catalogue: dict) -> str:
    """Build a compact reference list of creations with plugin files.

    Format: 'filename.esm = Title' (one per line, sorted).
    Only includes creations that have .esm/.esp/.esl files — others
    can never appear in load order discussions and waste tokens.
    """
    lines = []
    for entry in catalogue.values():
        title = entry.get("title", "")
        if not title:
            continue

        summary = entry.get("plugin_summary")
        if not summary or not isinstance(summary, dict):
            continue

        for f in summary.get("Files", []):
            if f.lower().endswith((".esm", ".esp", ".esl")):
                clean = f.replace("Data\\", "").replace("data\\", "")
                lines.append(f"{clean} = {title}")
                break  # one filename per creation is enough

    return "\n".join(sorted(lines))


def analyze_creation(
    client,
    description: str,
    reference_list: str,
    creation_title: str,
    creation_plugin: str,
    model: str = "claude-sonnet-4-6",
    max_retries: int = 2,
) -> list[dict]:
    """Send one creation's description to the LLM for analysis.

    Returns list of dependency dicts, or empty list on error.
    """
    from description_parser.prompts import SYSTEM_PROMPT, build_user_message

    user_msg = build_user_message(
        description, reference_list, creation_title, creation_plugin
    )

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )

            # Extract text from response
            text = response.content[0].text.strip()

            # Parse JSON — handle markdown code blocks and surrounding text
            if "```" in text:
                # Extract content between first ``` and last ```
                parts = text.split("```")
                for part in parts[1:]:
                    # Strip optional language tag (e.g., "json\n")
                    content = part.split("\n", 1)[1] if "\n" in part else part
                    content = content.strip()
                    if content.startswith("{"):
                        text = content
                        break

            # Try to find JSON object if text has preamble/postamble
            if not text.startswith("{"):
                start = text.find("{")
                if start >= 0:
                    text = text[start:]
                    # Find matching closing brace
                    depth = 0
                    for j, ch in enumerate(text):
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                text = text[:j + 1]
                                break

            data = json.loads(text)
            return data.get("dependencies", [])

        except json.JSONDecodeError:
            log.warning("Malformed JSON from LLM for %s", creation_title)
            return []
        except Exception as exc:
            if attempt < max_retries:
                delay = 60 * (attempt + 1)  # 60s, 120s
                print(
                    f"\r  API error, retrying in {delay}s...",
                    file=sys.stderr, flush=True,
                )
                time.sleep(delay)
                continue
            log.error("Failed after %d retries for %s: %s",
                      max_retries, creation_title, exc)
            return []


def process_candidates(
    client,
    candidates: list[dict],
    reference_list: str,
    model: str = "claude-sonnet-4-6",
    max_entries: int | None = None,
    save_callback=None,
) -> list[dict]:
    """Process all candidates through the LLM, collecting results.

    Args:
        save_callback: Optional function called every 10 results with
            the current results list, for incremental saving.

    Returns list of {content_id, title, plugin_file, dependencies[]}.
    """
    results = []
    total = min(len(candidates), max_entries) if max_entries else len(candidates)

    for i, candidate in enumerate(candidates[:total]):
        # In-place progress
        print(
            f"\r[{i + 1} of {total}] Analyzing: {candidate['title'][:50]}...",
            end="", file=sys.stderr, flush=True,
        )

        # Rate limit pacing: reference list is ~48K tokens per request.
        # Tier 3 allows 120K input tokens/min — ~30s between calls is safe.
        if i > 0:
            time.sleep(30)

        deps = analyze_creation(
            client,
            candidate["description"],
            reference_list,
            candidate["title"],
            candidate.get("plugin_file", ""),
            model=model,
        )

        if deps:
            results.append({
                "content_id": candidate["content_id"],
                "title": candidate["title"],
                "plugin_file": candidate.get("plugin_file", ""),
                "dependencies": deps,
            })

        if save_callback and deps:
            save_callback(results)

    print("", file=sys.stderr)  # newline after progress
    return results


def generate_rulebook(results: list[dict]) -> dict:
    """Convert extraction results into a 007-compatible rule book."""
    rules = []
    seen = set()  # deduplicate (source_plugin, load_after)

    for result in results:
        for dep in result.get("dependencies", []):
            source = dep.get("source_plugin", "")
            after = dep.get("load_after", "")
            if not source or not after:
                continue

            key = (source.lower(), after.lower())
            if key in seen:
                continue
            seen.add(key)

            confidence = dep.get("confidence", "medium").upper()
            source_text = dep.get("source_text", "")
            reasoning = dep.get("reasoning", "")
            note = f"[{confidence}] {reasoning}"
            if source_text:
                note += f" | Source: \"{source_text[:100]}\""

            rules.append({
                "plugin": source,
                "load_after": [after],
                "note": note,
            })

    return {
        "name": "Auto-detected Patch Order Rules",
        "description": "Generated from creation descriptions by the dependency parser",
        "version": "1.0",
        "rules": rules,
    }
