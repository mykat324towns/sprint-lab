"""
Master runner for the biomechanics research ingestion pipeline.

Steps:
  1. Exa search        -> tmp/biomechanics_exa_results.json
  2. Firecrawl extract -> tmp/biomechanics_extracts.json
  3. Claude synthesis  -> tmp/biomechanics_principles.json
  Final output         -> outputs/biomechanics_principles.json

Usage:
  python tools/run_biomechanics_pipeline.py [--skip-search] [--skip-synthesis]

  --skip-search      Skip Steps 1-2 (reuse existing tmp/ files)
  --skip-synthesis   Skip Step 3 (reuse existing tmp/biomechanics_principles.json)
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def step1_exa():
    print("\n" + "=" * 60)
    print("STEP 1 — BIOMECHANICS EXA SEARCH")
    print("=" * 60)
    import biomechanics_exa_runner
    return biomechanics_exa_runner.run()


def step2_firecrawl():
    print("\n" + "=" * 60)
    print("STEP 2 — FIRECRAWL EXTRACTION")
    print("=" * 60)
    import biomechanics_firecrawl_runner
    return biomechanics_firecrawl_runner.run()


def step3_synthesize():
    print("\n" + "=" * 60)
    print("STEP 3 — SYNTHESIS VIA OPENROUTER")
    print("=" * 60)
    import biomechanics_synthesizer
    return biomechanics_synthesizer.run()


def load_principles() -> dict:
    path = os.path.join(ROOT, "tmp", "biomechanics_principles.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing: {path}\nRun without --skip-synthesis first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_final_output(principles: dict) -> str:
    out_dir = os.path.join(ROOT, "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "biomechanics_principles.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(principles, f, indent=2, ensure_ascii=False)
    print(f"\nFinal output saved -> {out_path}")
    return out_path


def print_summary(principles: dict):
    print("\n" + "=" * 60)
    print("BIOMECHANICS PRINCIPLES SUMMARY")
    print("=" * 60)
    for p in principles.get("principles", []):
        triggers = ", ".join(p.get("triggers", []))
        summary = p.get("summary", "")[:200]
        print(f"\n[{p.get('id', '')}] {p.get('name', '')}")
        print(f"  Confidence : {p.get('confidence', 0):.2f}")
        print(f"  Triggers   : {triggers}")
        print(f"  Summary    : {summary}")
    n_sources = len(principles.get("raw_sources", []))
    n_principles = len(principles.get("principles", []))
    print(f"\n{'=' * 60}")
    print(f"Total: {n_sources} sources  |  {n_principles} principles")


def main():
    parser = argparse.ArgumentParser(
        description="Biomechanics research ingestion pipeline"
    )
    parser.add_argument(
        "--skip-search",
        action="store_true",
        help="Skip Steps 1-2 (Exa + Firecrawl). Reuse existing tmp/ files.",
    )
    parser.add_argument(
        "--skip-synthesis",
        action="store_true",
        help="Skip Step 3 (OpenRouter synthesis). Reuse existing tmp/biomechanics_principles.json.",
    )
    args = parser.parse_args()

    if not args.skip_search:
        step1_exa()
        step2_firecrawl()

    if args.skip_synthesis:
        principles = load_principles()
        n = len(principles.get("principles", []))
        print(f"\nLoaded existing principles ({n} principles) from tmp/")
    else:
        principles = step3_synthesize()

    save_final_output(principles)
    print_summary(principles)


if __name__ == "__main__":
    main()
