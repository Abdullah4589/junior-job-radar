"""Catalog aggregate for the Day 4 dashboard.

`data/catalog/trends.json` counts the deduped postings. The same catalog
writes the same file, so a second run does not churn git.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from jobradar.models import SENIORITY_LEVELS, WORKPLACES

_NOTES = (
    "Counts over the deduped catalog. seniority, skills, workplace, "
    "junior_friendly, and regions are extracted from each posting. "
    "top_skills and regions keep the first 20 after ties are broken by name."
)


def trends_path(root: Path) -> Path:
    return root / "data" / "catalog" / "trends.json"


def build_trends(postings: list[dict[str, Any]]) -> dict[str, Any]:
    skills: Counter[str] = Counter()
    regions: Counter[str] = Counter()
    seniority = {level: 0 for level in SENIORITY_LEVELS}
    workplace = {place: 0 for place in WORKPLACES}
    junior = 0
    for posting in postings:
        for skill in _strings(posting.get("skills")):
            skills[skill] += 1
        level = posting.get("seniority")
        seniority[level if isinstance(level, str) and level in seniority else "unknown"] += 1
        place = posting.get("workplace")
        workplace[place if isinstance(place, str) and place in workplace else "unknown"] += 1
        if posting.get("junior_friendly") is True:
            junior += 1
        for region in _strings(posting.get("regions")):
            regions[region] += 1
    return {
        "notes": _NOTES,
        "postings": len(postings),
        "junior_friendly": junior,
        "top_skills": _ranked(skills, "skill"),
        "seniority": seniority,
        "workplace": workplace,
        "regions": _ranked(regions, "region"),
    }


def write_trends(path: Path, document: dict[str, Any]) -> Path:
    payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == payload:
        return path
    path.write_text(payload, encoding="utf-8")
    return path


def _ranked(counts: Counter[str], key: str) -> list[dict[str, object]]:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]
    return [{key: name, "count": count} for name, count in ordered]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
