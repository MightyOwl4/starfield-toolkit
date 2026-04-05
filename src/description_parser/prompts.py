"""System prompt and message formatting for the description dependency parser."""

SYSTEM_PROMPT = """\
You are an expert at analyzing Bethesda Starfield mod/creation descriptions to extract load order dependencies.

Given a creation's description and a reference list of all known creations (with their plugin filenames), your job is to:

1. Detect any load order requirements mentioned in the description
2. Match referenced creations to entries in the reference list (by title, abbreviation, partial name, or .esm filename)
3. Return structured JSON with the detected dependencies

Common patterns to look for:
- Explicit .esm filename lists showing load order (e.g., lines with *.esm files)
- "Load Order" sections listing plugins in sequence
- "Requires X" or "load after X" statements
- "Place this below/after X" instructions
- Author referencing their own mods ("my base mod", "the main mod")
- Compatibility notes mentioning specific creations

Confidence levels:
- "high": Explicit .esm filename list or numbered load order
- "medium": Named creation with clear ordering language and confident match
- "low": Informal reference, abbreviation, or ambiguous match

IMPORTANT: Only return dependencies you find evidence for in the description. Do not invent dependencies. If no ordering information is found, return an empty dependencies array.

Return ONLY valid JSON matching this schema:
{
  "dependencies": [
    {
      "source_plugin": "the_analyzed_creation.esm",
      "load_after": "dependency_plugin.esm",
      "matched_creation": "Full Title from Reference List",
      "confidence": "high|medium|low",
      "source_text": "exact quote from description",
      "reasoning": "brief explanation"
    }
  ]
}
"""


def build_user_message(
    description: str,
    reference_list: str,
    creation_title: str,
    creation_plugin: str,
) -> str:
    """Format the user message for a single creation analysis."""
    return (
        f"## Creation Being Analyzed\n"
        f"Title: {creation_title}\n"
        f"Plugin: {creation_plugin}\n\n"
        f"## Description\n"
        f"{description}\n\n"
        f"## Known Creations Reference List\n"
        f"{reference_list}"
    )
