"""
Step 1: Run 6 targeted Exa queries for biomechanics research.
Filters to top 10 sources by content richness.
Saves to tmp/biomechanics_exa_results.json.
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

try:
    from exa_py import Exa
except ImportError:
    raise SystemExit("Missing dependency: exa-py. Run: pip install exa-py")

QUERIES = {
    "Q1_max_velocity_kinematics": "max velocity sprint biomechanics ground contact time force production kinematics",
    "Q2_leg_stiffness_elastic":   "sprint leg stiffness elastic energy return ankle tendon storage",
    "Q3_neuromuscular_fatigue":   "neuromuscular fatigue maximal sprint performance CNS",
    "Q4_elite_variability":       "elite sprint variability consistency step-to-step kinematics",
    "Q5_swing_stance_coupling":   "swing phase stance phase coupling sprint mechanics frequency",
    "Q6_touchdown_braking":       "sprint touchdown foot placement overstriding braking force contact",
}

NUM_RESULTS = 5


def score_result(r):
    text = getattr(r, "text", "") or ""
    date = getattr(r, "published_date", "") or ""
    score = len(text)
    if date and date[:4] >= "2018":
        score += 500
    return score


def run():
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY is missing in .env")
    exa = Exa(api_key=api_key)

    all_results = {}
    flat_results = []

    for key, query in QUERIES.items():
        print(f"Searching [{key}]: {query}")
        try:
            raw = exa.search_and_contents(
                query,
                num_results=NUM_RESULTS,
                start_published_date="2010-01-01",
            )
            results = []
            for r in raw.results:
                entry = {
                    "query_key":      key,
                    "title":          getattr(r, "title", "") or "",
                    "url":            getattr(r, "url", "") or "",
                    "text":           getattr(r, "text", "") or "",
                    "published_date": getattr(r, "published_date", "") or "",
                    "_score":         score_result(r),
                }
                results.append(entry)
                flat_results.append(entry)
            all_results[key] = {"query": query, "results": results}
            print(f"  -> {len(results)} results found")
        except Exception as e:
            print(f"  ERROR: {e}")
            all_results[key] = {"query": query, "results": [], "error": str(e)}

    # Filter to top 10 by score
    flat_results.sort(key=lambda x: x["_score"], reverse=True)
    filtered = []
    seen_urls = set()
    for r in flat_results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            filtered.append(r)
        if len(filtered) >= 10:
            break

    # Remove internal scoring field from output
    for r in filtered:
        r.pop("_score", None)
    for key_data in all_results.values():
        for r in key_data.get("results", []):
            r.pop("_score", None)

    output = {
        "all_results":     all_results,
        "filtered_results": filtered,
    }

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "tmp", "biomechanics_exa_results.json")
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(filtered)} filtered sources -> {out_path}")
    return output


if __name__ == "__main__":
    run()
