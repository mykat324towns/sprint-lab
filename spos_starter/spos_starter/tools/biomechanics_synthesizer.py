"""
Step 3: Synthesize biomechanics extracts into structured principles.
Calls OpenRouter (Claude) with extracted content.
Saves to tmp/biomechanics_principles.json.
"""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a biomechanics research synthesizer for sprint performance.
You receive extracted sections from peer-reviewed and practitioner sources on sprint mechanics.
Your job is to synthesize this into structured principles that directly govern sprint coaching decisions.
Output ONLY valid JSON matching this exact schema, nothing else:

{
  "raw_sources": [
    {
      "title": "",
      "authors": "",
      "year": "",
      "link": "",
      "key_findings": [],
      "mechanisms": [],
      "sprint_specific_takeaways": []
    }
  ],
  "principles": [
    {
      "id": "",
      "name": "",
      "summary": "",
      "mechanism": "",
      "sprint_implication": "",
      "triggers": [],
      "confidence": 0.0,
      "source_links": []
    }
  ]
}

Rules you must follow:
- Output 12-20 principles. No more, no fewer.
- Principles must be reusable across sessions — they describe biomechanical truths, not one-session observations.
- Each principle must directly influence a sprint coaching or programming decision.
- No generic advice. Every principle must cite a specific mechanism and a concrete sprint implication.
- triggers must be an array containing only values from this exact set: quality_drop, fatigue_pattern, rhythm_loss, low_readiness, high_variability
- confidence is a float from 0.0 to 1.0 representing how strongly the sources support this principle.
- id must be a short snake_case identifier, e.g. "leg_stiffness_gct_tradeoff"
- source_links must be URLs from the provided sources only.
- raw_sources must reflect only sources actually used, with accurate titles, years, and links.
- authors and year: use best available information from the text; use "" if not determinable.
- Do NOT include endurance, hypertrophy, or general fitness research.
- Do NOT output explanatory text outside the JSON."""


def build_user_message(sources: list[dict]) -> str:
    MAX_SECTIONS_PER_SOURCE = 5
    MAX_CHARS_PER_SECTION = 400
    MAX_TOTAL_CHARS = 12000

    lines = [f"Biomechanics research extracts from {len(sources)} sources follow. Synthesize these into sprint principles.\n"]

    for i, src in enumerate(sources, 1):
        header = f"\n=== SOURCE {i}: {src.get('title', 'Untitled')} ==="
        meta = f"URL: {src.get('url', '')}"
        if src.get("published_date"):
            meta += f"  |  Date: {src['published_date']}"
        sections = src.get("relevant_sections", [])[:MAX_SECTIONS_PER_SOURCE]
        body = "\n".join(s[:MAX_CHARS_PER_SECTION] for s in sections) if sections else "(no extracted sections)"
        lines.append(header)
        lines.append(meta)
        lines.append("---")
        lines.append(body)

    message = "\n".join(lines)
    if len(message) > MAX_TOTAL_CHARS:
        message = message[:MAX_TOTAL_CHARS] + "\n\n[content truncated to fit context window]"

    message += "\n\nSynthesize the above into the JSON schema provided."
    return message


def run() -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing in .env")

    extracts_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "tmp", "biomechanics_extracts.json")
    )
    if not os.path.exists(extracts_path):
        raise FileNotFoundError(f"Run biomechanics_firecrawl_runner.py first. Expected: {extracts_path}")

    with open(extracts_path, encoding="utf-8") as f:
        extracts = json.load(f)

    sources = extracts.get("sources", [])
    print(f"  Building prompt from {len(sources)} sources...")
    user_message = build_user_message(sources)
    print(f"  Prompt length: {len(user_message):,} chars")

    print("  Calling OpenRouter (claude-sonnet-4-6)...")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "anthropic/claude-sonnet-4-6",
            "temperature": 0.1,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
        },
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenRouter error {response.status_code}: {response.text[:500]}"
        )

    raw_content = response.json()["choices"][0]["message"]["content"]

    try:
        principles = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse JSON response: {e}\nRaw content (first 500 chars):\n{raw_content[:500]}"
        )

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "tmp", "biomechanics_principles.json")
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(principles, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved -> {out_path}")
    print(f"  raw_sources: {len(principles.get('raw_sources', []))}")
    print(f"  principles:  {len(principles.get('principles', []))}")
    return principles


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
