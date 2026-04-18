"""
Step 1: Run 4 targeted Exa queries for Phase 0 research.
Saves top 2-3 results per query to tmp/exa_results.json.
"""

import json
import os
import sys

# Ensure the tools directory is in path for local imports
sys.path.insert(0, os.path.dirname(__file__))
from search_exa import search

QUERIES = {
    "A_rep_structure":    "single rep vs cluster vs wave flying sprint max velocity quality exposure",
    "B_session_structure":"ascending descending constant hybrid fly sprint session quality max velocity",
    "C_build_distance":   "optimal build distance 30m 40m breakdown acceleration transition max velocity sprint",
    "D_phase_duration":   "max velocity sprint phase duration weeks progression beginner sprinter offseason",
}

NUM_RESULTS = 3

def run():
    results = {}
    for key, query in QUERIES.items():
        print(f"Searching [{key}]: {query}")
        try:
            raw = search(query, num_results=NUM_RESULTS)
            results[key] = {
                "query": query,
                "results": [
                    {
                        "title": getattr(r, "title", ""),
                        "url":   getattr(r, "url", ""),
                        "text":  getattr(r, "text", "") or "",
                    }
                    for r in raw.results
                ],
            }
            print(f"  -> {len(results[key]['results'])} results found")
        except Exception as e:
            print(f"  ERROR: {e}")
            results[key] = {"query": query, "results": [], "error": str(e)}

    out_path = os.path.join(os.path.dirname(__file__), "..", "tmp", "exa_results.json")
    out_path = os.path.normpath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved -> {out_path}")
    return results

if __name__ == "__main__":
    run()
