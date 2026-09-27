"""Serves the BNS / BNSS / IT Act legal reference glossary."""
import json
import os
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "laws_glossary.json")
_LAWS_CACHE = None


def _load_laws():
    global _LAWS_CACHE
    if _LAWS_CACHE is None:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            _LAWS_CACHE = json.load(f)["results"]
    return _LAWS_CACHE


@router.get("/api/laws")
def get_laws(q: Optional[str] = Query(None), act: Optional[str] = Query(None), topic: Optional[str] = Query(None)):
    laws = _load_laws()

    if act and act.lower() != "all":
        laws = [law for law in laws if law["act"].lower() == act.lower()]

    if topic:
        laws = [law for law in laws if topic in law.get("topics", [])]

    if q:
        needle = q.strip().lower()
        if needle:
            laws = [
                law
                for law in laws
                if needle in law["title"].lower()
                or needle in law["description"].lower()
                or needle in law["section"].lower()
                or needle in law["act"].lower()
                or any(needle in topic.lower() for topic in law.get("topics", []))
                or (law.get("former") and needle in law["former"].lower())
            ]

    return {"results": laws}