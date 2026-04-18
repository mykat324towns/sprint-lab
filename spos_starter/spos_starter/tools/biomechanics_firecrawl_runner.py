"""
Step 2: Extract relevant content from biomechanics Exa results.
Tries Exa text first, falls back to Firecrawl.
Filters paragraphs by biomechanics keywords.
Saves to tmp/biomechanics_extracts.json.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scrape_firecrawl import scrape

KEYWORDS = {
    "stiffness":    ["stiffness", "elastic", "tendon", "GCT", "ground contact", "spring-mass", "leg spring"],
    "fatigue":      ["fatigue", "CNS", "neuromuscular", "velocity loss", "force decline", "power output"],
    "variability":  ["variability", "CV", "coefficient of variation", "consistency", "step-to-step", "within-athlete"],
    "swing_stance": ["swing", "stance", "coupling", "frequency", "stride rate", "recovery", "clearance"],
    "touchdown":    ["touchdown", "foot placement", "overstride", "braking", "horizontal force", "contact point"],
    "force":        ["force", "GRF", "impulse", "peak force", "rate of force", "power", "propulsion"],
}

# Which keyword categories apply to each query key
QUERY_KEYWORD_MAP = {
    "Q1_max_velocity_kinematics": ["force", "touchdown"],
    "Q2_leg_stiffness_elastic":   ["stiffness"],
    "Q3_neuromuscular_fatigue":   ["fatigue"],
    "Q4_elite_variability":       ["variability"],
    "Q5_swing_stance_coupling":   ["swing_stance"],
    "Q6_touchdown_braking":       ["touchdown", "force"],
}

MAX_PARAGRAPHS = 8


def get_keywords_for_query(query_key: str) -> list[str]:
    cats = QUERY_KEYWORD_MAP.get(query_key, list(KEYWORDS.keys()))
    merged = []
    for cat in cats:
        merged.extend(KEYWORDS.get(cat, []))
    return list(set(merged))


def filter_paragraphs(text: str, keywords: list[str]) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 60]
    kw_lower = [k.lower() for k in keywords]
    filtered = [p for p in paragraphs if any(k in p.lower() for k in kw_lower)]
    return filtered[:MAX_PARAGRAPHS]


def run():
    exa_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "tmp", "biomechanics_exa_results.json")
    )
    if not os.path.exists(exa_path):
        raise FileNotFoundError(f"Run biomechanics_exa_runner.py first. Expected: {exa_path}")

    with open(exa_path, encoding="utf-8") as f:
        exa_data = json.load(f)

    filtered_results = exa_data.get("filtered_results", [])
    sources = []

    for result in filtered_results:
        url = result.get("url", "")
        if not url:
            continue

        query_key = result.get("query_key", "")
        keywords = get_keywords_for_query(query_key)

        exa_text = result.get("text", "")
        if exa_text and len(exa_text) > 200:
            relevant = filter_paragraphs(exa_text, keywords)
            source_type = "exa_text"
        else:
            print(f"  Firecrawl: {url}")
            try:
                scraped = scrape(url)
                raw_text = ""
                if isinstance(scraped, dict):
                    raw_text = scraped.get("markdown", "") or scraped.get("content", "")
                elif hasattr(scraped, "markdown"):
                    raw_text = scraped.markdown or ""
                relevant = filter_paragraphs(raw_text, keywords)
                source_type = "firecrawl"
            except Exception as e:
                print(f"    ERROR scraping {url}: {e}")
                relevant = []
                source_type = "error"

        sources.append({
            "url":               url,
            "title":             result.get("title", ""),
            "query_key":         query_key,
            "published_date":    result.get("published_date", ""),
            "source":            source_type,
            "relevant_sections": relevant,
        })
        print(f"  [{query_key}] {url[:60]} -> {len(relevant)} paragraphs kept")

    output = {"sources": sources}

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "tmp", "biomechanics_extracts.json")
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(sources)} sources -> {out_path}")
    return output


if __name__ == "__main__":
    run()
