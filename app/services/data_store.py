"""
Loads the JSON seed data in app/data/ into memory once, at import time.

This is intentionally file-backed rather than a database for the first
pass: helplines, the rights glossary, and the Ask Nyaya knowledge base are
editorial/legal content that a non-engineer (legal aid volunteer) should
be able to review and update as a JSON/CSV file, reviewed via PR, without
needing DB access. Swap this for a real datastore later if/when an admin
UI is built — the router layer doesn't need to change, only this module.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(filename: str) -> dict[str, Any]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_helplines() -> dict[str, Any]:
    return _load("helplines.json")


@lru_cache(maxsize=1)
def get_rights_glossary() -> dict[str, Any]:
    return _load("rights_glossary.json")


@lru_cache(maxsize=1)
def get_ask_knowledge_base() -> dict[str, Any]:
    return _load("ask_knowledge_base.json")


@lru_cache(maxsize=1)
def get_healing_resources() -> dict[str, Any]:
    return _load("healing_resources.json")
