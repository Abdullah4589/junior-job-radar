"""Keyword extraction for skills, seniority, workplace, and region limits.

The skill list is `taxonomy/skills.json`. Aliases such as `js` and `k8s`
map to one canonical name. `Go`, `R`, and `C` use a strict boundary so
they do not match inside Google, React, C++, or ordinary prose like
"go to the office".

Seniority is read from the title and tags only. A description that says
"mentor junior engineers" must not relabel a senior role. Workplace reads
the description. Region restrictions read the title, the location, and
restriction phrases in the description ("must be located in", "US only"),
not a marketing list of countries. A description or a tag list that names more than 12 skills is treated as
a catalog of other roles and does not add skills. The title still counts.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from jobradar.models import SENIORITY_LEVELS, WORKPLACES, JobPosting

_TAXONOMY = Path(__file__).resolve().parent / "taxonomy"
_STRICT_TAILS = {"c", "r", "go"}
_JUNIOR_LEVELS = {"intern", "junior"}
# Above this many description-only skills, the text is a catalog of other roles.
_SKILL_CATALOG_CAP = 12
_OPEN_LOCATIONS = {
    "",
    "remote",
    "unspecified",
    "worldwide",
    "anywhere",
    "global",
    "hybrid",
    "wfh",
    "work from home",
}
# Restriction phrasing only. A marketing line such as "companies in the US
# and Europe" is not a region limit.
_RESTRICTION = re.compile(
    r"\b(?:"
    r"only candidates in|"
    r"must be (?:based |located |residing )?(?:in|within)|"
    r"based in|"
    r"located in|"
    r"residing in|"
    r"reside in|"
    r"restricted to|"
    r"open only to|"
    r"candidates (?:based |located )?in|"
    r"on[- ]?sites? in"
    r")\b([^.\n]{0,80})",
    re.IGNORECASE,
)
_ONLY_PHRASE = re.compile(r"([^\n.]{0,30}\bonly)\b", re.IGNORECASE)
_HYBRID = re.compile(r"\bhybrid\b", re.IGNORECASE)
_REMOTE_WORD = re.compile(r"\b(?:remote|work from home|wfh)\b", re.IGNORECASE)
_ONSITE = re.compile(
    r"\b(?:on[- ]?sites?|in[- ]offices?|on[- ]premises?)\b",
    re.IGNORECASE,
)
_SCRIPT = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?s)<[^>]+>")
_EXTRACTION_KEYS = ("seniority", "skills", "workplace", "junior_friendly", "regions")


@dataclass(frozen=True, slots=True)
class Extraction:
    seniority: str
    skills: list[str]
    workplace: str
    junior_friendly: bool
    regions: list[str]


@dataclass(frozen=True, slots=True)
class _Alias:
    canonical: str
    pattern: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class _Level:
    name: str
    rank: int
    patterns: tuple[re.Pattern[str], ...]


def extract_posting(
    *,
    title: str,
    description: str = "",
    location: str = "",
    tags: list[str] | None = None,
    labels: list[str] | None = None,
    remote: bool = False,
    refine: bool = True,
) -> Extraction:
    """Extract one posting. `refine` asks the optional LLM, which no-ops without config."""

    keyword = _keyword_extract(
        title=title,
        description=description,
        location=location,
        tags=tags or [],
        labels=labels if labels is not None else (tags or []),
        remote=remote,
    )
    if not refine:
        return keyword
    from jobradar.llm import maybe_refine

    return maybe_refine(
        keyword,
        context=_context(title=title, description=description, location=location, tags=tags or []),
    )


def apply_extraction(
    posting: JobPosting,
    *,
    description: str = "",
    labels: list[str] | None = None,
) -> JobPosting:
    """Return a copy of `posting` with extraction fields filled in."""

    found = extract_posting(
        title=posting.title,
        description=description,
        location=posting.location,
        tags=posting.tags,
        labels=labels,
        remote=posting.remote,
    )
    return replace(
        posting,
        seniority=found.seniority,
        skills=list(found.skills),
        workplace=found.workplace,
        junior_friendly=found.junior_friendly,
        regions=list(found.regions),
    )


def needs_extraction(data: dict[str, Any]) -> bool:
    return any(key not in data for key in _EXTRACTION_KEYS)


def ensure_extracted(data: dict[str, Any]) -> JobPosting:
    """Load a snapshot row, filling extraction when an older file omitted it."""

    posting = JobPosting.from_dict(data)
    if not needs_extraction(data):
        return posting
    return apply_extraction(posting)


def plain_text(value: str) -> str:
    """Drop HTML, including script blocks, and collapse whitespace."""

    text = _SCRIPT.sub(" ", value)
    text = _TAG.sub(" ", text)
    text = html.unescape(text).replace("\xa0", " ")
    return " ".join(text.split())


def skill_alias_map() -> dict[str, str]:
    """Lowercased alias to canonical name, including case-sensitive tokens."""

    return dict(_skills().lookup)


def skill_names() -> set[str]:
    return set(_skills().lookup.values())


def region_names() -> set[str]:
    return {alias.canonical for alias in _region_aliases()}


def _keyword_extract(
    *,
    title: str,
    description: str,
    location: str,
    tags: list[str],
    labels: list[str],
    remote: bool,
) -> Extraction:
    body = plain_text(description)
    seniority = _seniority(title, tags)
    return Extraction(
        seniority=seniority,
        skills=_skills_from(title, body, tags),
        workplace=_workplace(
            title=title,
            description=body,
            location=location,
            labels=labels,
            remote=remote,
        ),
        junior_friendly=seniority in _JUNIOR_LEVELS,
        regions=_regions(title=title, description=body, location=location),
    )


def _context(*, title: str, description: str, location: str, tags: list[str]) -> str:
    body = plain_text(description)
    lines = [f"Title: {title}", f"Location: {location}", f"Tags: {', '.join(tags)}"]
    if body:
        lines.append(f"Description: {body[:4000]}")
    return "\n".join(lines)


def _seniority(title: str, tags: list[str]) -> str:
    blob = " ".join([title, *tags])
    best_name = "unknown"
    best_rank = -1
    for level in _levels():
        if level.rank > best_rank and any(pattern.search(blob) for pattern in level.patterns):
            best_name = level.name
            best_rank = level.rank
    return best_name


def _skills_from(title: str, description: str, tags: list[str]) -> list[str]:
    index = _skills()
    found = _greedy(plain_text(title), index.aliases)
    seen = set(found)
    if description:
        extra = [skill for skill in _greedy(description, index.aliases) if skill not in seen]
        if len(extra) <= _SKILL_CATALOG_CAP:
            for skill in extra:
                seen.add(skill)
                found.append(skill)
    from_tags: list[str] = []
    for tag in tags:
        canonical = index.lookup.get(" ".join(tag.lower().split()))
        if canonical and canonical not in seen and canonical not in from_tags:
            from_tags.append(canonical)
    if len(from_tags) <= _SKILL_CATALOG_CAP:
        found.extend(from_tags)
    return found


def _workplace(
    *,
    title: str,
    description: str,
    location: str,
    labels: list[str],
    remote: bool,
) -> str:
    blob = "\n".join([title, location, description, " ".join(labels)])
    label_set = {" ".join(label.lower().split()) for label in labels}
    hybrid = bool(_HYBRID.search(blob)) or "hybrid" in label_set
    remote_signal = remote or bool(_REMOTE_WORD.search(blob)) or "remote" in label_set
    onsite = bool(_ONSITE.search(blob)) or bool(label_set & {"on-site", "onsite", "on site"})
    if hybrid or (remote_signal and onsite):
        return "hybrid"
    if remote_signal:
        return "remote"
    if onsite:
        return "onsite"
    if " ".join(location.lower().split()) not in _OPEN_LOCATIONS:
        return "onsite"
    return "unknown"


def _regions(*, title: str, description: str, location: str) -> list[str]:
    aliases = _region_aliases()
    found = _greedy("\n".join(part for part in (title, location) if part), aliases)
    seen = set(found)
    for pattern in (_RESTRICTION, _ONLY_PHRASE):
        for match in pattern.finditer(description):
            for name in _greedy(match.group(0), aliases):
                if name not in seen:
                    seen.add(name)
                    found.append(name)
    return found


def _greedy(text: str, aliases: tuple[_Alias, ...] | list[_Alias]) -> list[str]:
    if not text:
        return []
    spans: list[tuple[int, int, str]] = []
    for alias in aliases:
        for match in alias.pattern.finditer(text):
            spans.append((match.start(), match.end(), alias.canonical))
    spans.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
    chosen: list[str] = []
    seen: set[str] = set()
    occupied = -1
    for start, end, canonical in spans:
        if start < occupied:
            continue
        occupied = end
        if canonical not in seen:
            seen.add(canonical)
            chosen.append(canonical)
    return chosen


def _pattern(alias: str, *, strict: bool, ignore_case: bool) -> re.Pattern[str]:
    """Match an alias on Unicode letter boundaries.

    ASCII `[a-z]` treats `é` as a boundary, so `R` matched the R in
    `Rémunération`. Strict tokens also refuse `+`, `#`, and `-`, which keeps
    `C` out of `C++` and `Go` out of `Go-to-market`.
    """

    body = re.escape(alias)
    if alias.startswith("."):
        left = ""
    elif strict:
        left = r"(?<![\w+#.&-])"
    else:
        left = r"(?<!\w)"
    right = r"(?![\w+#&-])" if strict else r"(?!\w)"
    flags = re.IGNORECASE if ignore_case else 0
    return re.compile(f"{left}{body}{right}", flags)


def _is_strict(alias: str, *, case_sensitive: bool) -> bool:
    if case_sensitive:
        return True
    return alias.split(" ")[-1] in _STRICT_TAILS


@lru_cache(maxsize=1)
def _skills() -> "_SkillIndex":
    document = _read_json("skills.json")
    rows = document.get("skills")
    if not isinstance(rows, list) or not rows:
        raise ValueError("skills.json must contain a skills list")
    aliases: list[_Alias] = []
    lookup: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each skill must be an object")
        canonical = row.get("canonical")
        if not isinstance(canonical, str) or not canonical:
            raise ValueError("Each skill needs a canonical name")
        raw_aliases = row.get("aliases")
        if not isinstance(raw_aliases, list) or not raw_aliases:
            raise ValueError(f"{canonical} needs aliases")
        sensitive = row.get("case_sensitive") or []
        if not isinstance(sensitive, list):
            raise ValueError(f"{canonical} case_sensitive must be a list")
        for alias in [*raw_aliases, *sensitive]:
            if not isinstance(alias, str) or not alias:
                raise ValueError(f"{canonical} has an empty alias")
            case_sensitive = alias in sensitive
            key = " ".join(alias.lower().split())
            previous = lookup.get(key)
            if previous is not None and previous != canonical:
                raise ValueError(f"Alias {alias!r} maps to both {previous} and {canonical}")
            lookup[key] = canonical
            aliases.append(
                _Alias(
                    canonical,
                    _pattern(
                        alias if case_sensitive else key,
                        strict=_is_strict(key, case_sensitive=case_sensitive),
                        ignore_case=not case_sensitive,
                    ),
                )
            )
    return _SkillIndex(tuple(aliases), lookup)


@lru_cache(maxsize=1)
def _levels() -> tuple[_Level, ...]:
    document = _read_json("seniority.json")
    rows = document.get("levels")
    if not isinstance(rows, list):
        raise ValueError("seniority.json must contain levels")
    levels: list[_Level] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each seniority level must be an object")
        name = row.get("name")
        rank = row.get("rank")
        patterns = row.get("patterns")
        if name not in SENIORITY_LEVELS or name == "unknown":
            raise ValueError(f"Unknown seniority level {name!r}")
        if not isinstance(rank, int):
            raise ValueError(f"{name} needs an integer rank")
        if not isinstance(patterns, list) or not patterns:
            raise ValueError(f"{name} needs patterns")
        compiled = tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in patterns
            if isinstance(pattern, str) and pattern
        )
        if len(compiled) != len(patterns):
            raise ValueError(f"{name} has an empty pattern")
        levels.append(_Level(name, rank, compiled))
        seen.add(name)
    expected = {level for level in SENIORITY_LEVELS if level != "unknown"}
    if seen != expected:
        missing = ", ".join(sorted(expected - seen))
        raise ValueError(f"seniority.json is missing {missing}")
    return tuple(levels)


@lru_cache(maxsize=1)
def _region_aliases() -> tuple[_Alias, ...]:
    document = _read_json("regions.json")
    rows = document.get("regions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("regions.json must contain regions")
    aliases: list[_Alias] = []
    seen: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each region must be an object")
        canonical = row.get("canonical")
        raw_aliases = row.get("aliases")
        if not isinstance(canonical, str) or not canonical:
            raise ValueError("Each region needs a canonical name")
        if not isinstance(raw_aliases, list) or not raw_aliases:
            raise ValueError(f"{canonical} needs aliases")
        sensitive = row.get("case_sensitive") or []
        if not isinstance(sensitive, list):
            raise ValueError(f"{canonical} case_sensitive must be a list")
        for alias in [*raw_aliases, *sensitive]:
            if not isinstance(alias, str) or not alias:
                raise ValueError(f"{canonical} has an empty alias")
            case_sensitive = alias in sensitive
            key = " ".join(alias.lower().split())
            previous = seen.get(key)
            if previous is not None and previous != canonical:
                raise ValueError(f"Region alias {alias!r} maps to both {previous} and {canonical}")
            seen[key] = canonical
            strict = case_sensitive or key in {"us", "uk", "eu"}
            aliases.append(
                _Alias(
                    canonical,
                    _pattern(
                        alias if case_sensitive else key,
                        strict=strict,
                        ignore_case=not case_sensitive,
                    ),
                )
            )
    return tuple(aliases)


def _read_json(name: str) -> dict[str, Any]:
    path = _TAXONOMY / name
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{name} must be a JSON object")
    return document


@dataclass(frozen=True, slots=True)
class _SkillIndex:
    aliases: tuple[_Alias, ...]
    lookup: dict[str, str]
