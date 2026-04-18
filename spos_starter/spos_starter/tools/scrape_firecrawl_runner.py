"""
Step 2: Scrape each URL from exa_results.json with Firecrawl.
Extracts ONLY paragraphs relevant to each research question.
Saves filtered extracts to tmp/firecrawl_extracts.json.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scrape_firecrawl import scrape

# Keywords to filter paragraphs per research category
KEYWORDS = {
    "A_rep_structure": [
        "single rep", "cluster", "wave", "flying sprint", "fly", "quality",
        "max velocity", "exposure", "rest", "CNS", "fatigue",
    ],
    "B_session_structure": [
        "ascending", "descending", "constant", "hybrid", "fly",
        "session", "quality", "max velocity", "structure", "warm-up",
    ],
    "C_build_distance": [
        "build", "approach", "run-up", "acceleration", "transition",
        "30m", "40m", "35m", "upright", "entry", "max velocity", "fly zone",
    ],
    "D_phase_duration": [
        "phase", "week", "duration", "progression", "offseason",
        "beginner", "neural", "adaptation", "exposure", "exit", "block",
    ],
}

MAX_PARAGRAPHS = 10


def filter_paragraphs(text: str, keywords: list[str]) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 60]
    kw_lower = [k.lower() for k in keywords]
    filtered = [p for p in paragraphs if any(k in p.lower() for k in kw_lower)]
    return filtered[:MAX_PARAGRAPHS]


def run():
    exa_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "tmp", "exa_results.json")
    )
    if not os.path.exists(exa_path):
        raise FileNotFoundError(f"Run search_exa_runner.py first. Expected: {exa_path}")

    with open(exa_path, encoding="utf-8") as f:
        exa_data = json.load(f)

    extracts = {}

    for category, data in exa_data.items():
        keywords = KEYWORDS.get(category, [])
        category_extracts = []

        for result in data.get("results", []):
            url = result.get("url", "")
            if not url:
                continue

            # First try the text Exa already returned (avoid unnecessary Firecrawl call)
            exa_text = result.get("text", "")
            if exa_text and len(exa_text) > 200:
                relevant = filter_paragraphs(exa_text, keywords)
                source = "exa_text"
            else:
                # Fall back to Firecrawl
                print(f"  Firecrawl: {url}")
                try:
                    scraped = scrape(url)
                    raw_text = ""
                    if isinstance(scraped, dict):
                        raw_text = scraped.get("markdown", "") or scraped.get("content", "")
                    elif hasattr(scraped, "markdown"):
                        raw_text = scraped.markdown or ""
                    relevant = filter_paragraphs(raw_text, keywords)
                    source = "firecrawl"
                except Exception as e:
                    print(f"    ERROR scraping {url}: {e}")
                    relevant = []
                    source = "error"

            category_extracts.append({
                "url": url,
                "title": result.get("title", ""),
                "source": source,
                "relevant_sections": relevant,
            })
            print(f"  [{category}] {url[:60]} -> {len(relevant)} paragraphs kept")

        extracts[category] = {
            "query": data.get("query", ""),
            "sources": category_extracts,
        }

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "tmp", "firecrawl_extracts.json")
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(extracts, f, indent=2, ensure_ascii=False)
    print(f"\nSaved -> {out_path}")
    return extracts


if __name__ == "__main__":
    run()
