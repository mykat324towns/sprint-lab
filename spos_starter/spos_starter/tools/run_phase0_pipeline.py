"""
Master runner for Phase 0 SPOS pipeline.

Steps:
  1. Exa search  → tmp/exa_results.json
  2. Firecrawl   → tmp/firecrawl_extracts.json
  (Steps 3-4: synthesis is performed by Claude after reading research.)
  5. Notion write → Sprint Program database

Usage:
  python tools/run_phase0_pipeline.py [--skip-research] [--skip-notion]

  --skip-research   Skip Steps 1-2 (use existing tmp/ files)
  --skip-notion     Skip Step 5 (print program only, don't write to Notion)
"""

import json
import os
import sys
import argparse

# Add tools dir to path
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def step1_exa():
    print("\n" + "="*60)
    print("STEP 1 — EXA RESEARCH")
    print("="*60)
    import search_exa_runner
    return search_exa_runner.run()


def step2_firecrawl():
    print("\n" + "="*60)
    print("STEP 2 — FIRECRAWL EXTRACTION")
    print("="*60)
    import scrape_firecrawl_runner
    return scrape_firecrawl_runner.run()


def load_research():
    extracts_path = os.path.join(ROOT, "tmp", "firecrawl_extracts.json")
    exa_path = os.path.join(ROOT, "tmp", "exa_results.json")

    if not os.path.exists(extracts_path):
        raise FileNotFoundError(f"Missing: {extracts_path}. Run without --skip-research first.")

    with open(extracts_path, encoding="utf-8") as f:
        extracts = json.load(f)
    with open(exa_path, encoding="utf-8") as f:
        exa = json.load(f)

    return exa, extracts


def print_research_summary(exa, extracts):
    print("\n" + "="*60)
    print("RESEARCH SUMMARY (for Claude synthesis)")
    print("="*60)
    for cat, data in extracts.items():
        print(f"\n--- {cat}: {data['query']} ---")
        for src in data["sources"]:
            print(f"\n  Source: {src['title']}")
            print(f"  URL:    {src['url']}")
            for i, para in enumerate(src["relevant_sections"], 1):
                print(f"  [{i}] {para[:300]}{'...' if len(para)>300 else ''}")


def step5_notion(program: dict):
    print("\n" + "="*60)
    print("STEP 5 — NOTION OUTPUT")
    print("="*60)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    import notion_write

    parent_id = os.getenv("NOTION_PARENT_PAGE_ID")
    db_id = os.getenv("NOTION_DATABASE_ID")

    if not db_id:
        if not parent_id:
            raise ValueError(
                "NOTION_PARENT_PAGE_ID not set in .env. "
                "Add the ID of the Notion page where the database should live."
            )
        print("Creating Sprint Program database...")
        db_id = notion_write.create_sprint_database(parent_id)

    print("Writing Phase 0 program to Notion...")
    page_id = notion_write.write_program(program)
    print(f"\nDone. Page ID: {page_id}")
    return page_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-research", action="store_true")
    parser.add_argument("--skip-notion",   action="store_true")
    args = parser.parse_args()

    if not args.skip_research:
        step1_exa()
        step2_firecrawl()

    exa, extracts = load_research()
    print_research_summary(exa, extracts)

    print("\n" + "="*60)
    print("STEPS 3-4: Synthesis by Claude")
    print("="*60)
    print(
        "Research printed above. Claude will now synthesize comparison"
        " analysis and build the Phase 0 program from these findings."
    )
    print("Run this script with a program dict to write to Notion.")

    if not args.skip_notion:
        print(
            "\nTo write to Notion, call step5_notion(program_dict) "
            "after synthesis, or re-run with a filled program."
        )


if __name__ == "__main__":
    main()
