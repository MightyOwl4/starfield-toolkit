# LLM Response Schema Contract

## Request Format

Each API call sends:
- **System prompt**: Task definition + JSON schema + confidence guidelines
- **User message**: One creation's description + full creation reference list

## Expected JSON Response

```json
{
  "dependencies": [
    {
      "source_plugin": "dwn_luxhabs_pdypatch.esm",
      "load_after": "placedoorsyourself.esm",
      "matched_creation": "Place Doors Yourself",
      "confidence": "high",
      "source_text": "PlaceDoorsYourself.esm\nDWN_LuxHabs.esm\nDWN_LuxHabs_PDYPatch.esm",
      "reasoning": "Explicit load order list with .esm filenames in sequence"
    },
    {
      "source_plugin": "dwn_luxhabs_pdypatch.esm",
      "load_after": "dwn_luxhabs.esm",
      "matched_creation": "Luxurious Ship Habs",
      "confidence": "high",
      "source_text": "PlaceDoorsYourself.esm\nDWN_LuxHabs.esm\nDWN_LuxHabs_PDYPatch.esm",
      "reasoning": "Explicit load order list with .esm filenames in sequence"
    }
  ]
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| dependencies | array | yes | List of detected ordering relationships (empty if none found) |
| source_plugin | string | yes | Plugin filename of the creation being ordered (from the analyzed creation) |
| load_after | string | yes | Plugin filename that must load before source_plugin |
| matched_creation | string | yes | Full title of the matched creation from the reference list |
| confidence | enum | yes | "high", "medium", or "low" |
| source_text | string | yes | Excerpt from the description that triggered this detection |
| reasoning | string | yes | Brief explanation of how the match was determined |

## Confidence Level Guidelines

| Level | Criteria | Examples |
|-------|----------|---------|
| high | Explicit .esm filename list or numbered load order | `*ModA.esm / *ModB.esm / *Patch.esm` |
| medium | Named creation with clear ordering language | "Load this after Watchtower" with exact title match |
| low | Informal reference, abbreviation, or ambiguous phrasing | "Requires PDY" matched to "Place Doors Yourself" |
