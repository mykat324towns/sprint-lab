"""
Notion tool for Phase 0 SPOS pipeline.

Two public functions:
  create_sprint_database(parent_page_id) → str (database_id)
  write_program(data: dict) → str (page_id)

Database schema: Day | Focus | Sprint Plan | Lift Plan | Notes
Write two rows per phase: one for Day 1, one for Day 2.
"""

import os
import requests
from dotenv import load_dotenv, set_key

load_dotenv()

NOTION_VERSION = "2022-06-28"

_db_id_cache: str | None = None  # in-process cache so multiple write_program() calls reuse the same DB


def _headers():
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        raise ValueError("NOTION_API_KEY missing from .env")
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _rich_text(content: str) -> list:
    """Split long strings into <=2000-char chunks (Notion limit per rich_text object)."""
    chunks = [content[i:i+2000] for i in range(0, max(len(content), 1), 2000)]
    return [{"type": "text", "text": {"content": c}} for c in chunks]


def create_sprint_database(parent_page_id: str) -> str:
    """Create the 'Sprint Program' database under parent_page_id."""
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "Sprint Program"}}],
        "properties": {
            "Day":          {"title": {}},
            "Focus":        {"rich_text": {}},
            "Sprint Plan":  {"rich_text": {}},
            "Lift Plan":    {"rich_text": {}},
            "Notes":        {"rich_text": {}},
        },
    }
    resp = requests.post(
        "https://api.notion.com/v1/databases",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Failed to create database: {resp.status_code} {resp.text}")

    db_id = resp.json()["id"]
    print(f"Created Notion database: {db_id}")

    # Persist to .env
    env_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", ".env")
    )
    set_key(env_path, "NOTION_DATABASE_ID", db_id)
    print(f"NOTION_DATABASE_ID written to .env")
    return db_id


def _extract_notion_id(url_or_id: str) -> str:
    """
    Extract a bare Notion ID (32 hex chars) from a URL or return as-is if already an ID.
    Handles formats like:
      https://www.notion.so/Title-34120d9ecfdb80d79288e6b85b9b6483
      https://www.notion.so/workspace/34120d9ecfdb80d79288e6b85b9b6483
    """
    import re
    # Already a bare UUID (with or without dashes)
    if re.fullmatch(r"[0-9a-f]{32}", url_or_id):
        return url_or_id
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", url_or_id):
        return url_or_id.replace("-", "")
    # Extract trailing 32-char hex from URL
    m = re.search(r"([0-9a-f]{32})(?:[?#]|$)", url_or_id)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot extract Notion ID from: {url_or_id}")


def _get_or_create_db() -> str:
    """Return database ID, creating one if NOTION_DATABASE_ID is unset or a URL pointing to a page."""
    global _db_id_cache
    if _db_id_cache:
        return _db_id_cache

    raw = os.getenv("NOTION_DATABASE_ID", "")

    if not raw:
        parent_id = os.getenv("NOTION_PARENT_PAGE_ID", "")
        if not parent_id:
            raise ValueError(
                "NOTION_DATABASE_ID is not set and NOTION_PARENT_PAGE_ID is not set. "
                "Add one of them to .env."
            )
        print("NOTION_DATABASE_ID missing — creating new Sprint Program database...")
        _db_id_cache = create_sprint_database(parent_id)
        return _db_id_cache

    page_id = _extract_notion_id(raw)

    # Try the ID as a database first; if that fails, treat it as a parent page
    test_resp = requests.get(
        f"https://api.notion.com/v1/databases/{page_id}",
        headers=_headers(),
        timeout=15,
    )
    if test_resp.ok:
        print(f"Using existing database: {page_id[:8]}...")
        _db_id_cache = page_id
        return _db_id_cache

    # Not a database — treat as parent page and create the database there
    print(f"ID {page_id[:8]}... is not a database — creating Sprint Program database under it...")
    _db_id_cache = create_sprint_database(page_id)
    return _db_id_cache


def write_program(data: dict) -> str:
    """
    Write one program row to the Sprint Program database.

    data keys (all str):
      day         — e.g. "Day 1 — Sprint + Lift"
      focus       — e.g. "Max Velocity Exposure (Primary)"
      sprint_plan — full sprint session description
      lift_plan   — full lift session description
      notes       — diagnostics, cues, stop criteria
    """
    db_id = _get_or_create_db()

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Day":         {"title": [{"type": "text", "text": {"content": data.get("day", "")}}]},
            "Focus":       {"rich_text": _rich_text(data.get("focus", ""))},
            "Sprint Plan": {"rich_text": _rich_text(data.get("sprint_plan", ""))},
            "Lift Plan":   {"rich_text": _rich_text(data.get("lift_plan", ""))},
            "Notes":       {"rich_text": _rich_text(data.get("notes", ""))},
        },
    }
    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Failed to create page: {resp.status_code} {resp.text}")

    page_id = resp.json()["id"]
    print(f"Created Notion page: {page_id}")
    return page_id


if __name__ == "__main__":
    load_dotenv()
    parent_id = os.getenv("NOTION_PARENT_PAGE_ID")
    if not parent_id:
        print("ERROR: NOTION_PARENT_PAGE_ID not set in .env")
    else:
        print(f"NOTION_PARENT_PAGE_ID found: {parent_id[:8]}...")
        print("Ready to create database.")
