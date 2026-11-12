"""Normalized posting schema shared by every source."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Stored order is the on-disk key order. Later fields are appended.
FIELD_NAMES = (
    "id",
    "source",
    "title",
    "company",
    "location",
    "remote",
    "tags",
    "salary_text",
    "posted_at",
    "url",
    "fetched_at",
    "seniority",
    "skills",
    "workplace",
    "junior_friendly",
    "regions",
)

SENIORITY_LEVELS = (
    "intern",
    "junior",
    "mid",
    "senior",
    "lead",
    "staff",
    "principal",
    "manager",
    "unknown",
)

WORKPLACES = ("remote", "hybrid", "onsite", "unknown")

_JUNIOR_LEVELS = {"intern", "junior"}


@dataclass(slots=True)
class JobPosting:
    """One software job posting after source-specific cleanup.

    `to_dict` is the on-disk contract documented in `docs/ROADMAP.md`.
    """

    id: str
    source: str
    title: str
    company: str
    location: str
    remote: bool
    tags: list[str]
    salary_text: str | None
    posted_at: str | None
    url: str
    fetched_at: str
    seniority: str = "unknown"
    skills: list[str] = field(default_factory=list)
    workplace: str = "unknown"
    junior_friendly: bool = False
    regions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "remote": self.remote,
            "tags": list(self.tags),
            "salary_text": self.salary_text,
            "posted_at": self.posted_at,
            "url": self.url,
            "fetched_at": self.fetched_at,
            "seniority": self.seniority,
            "skills": list(self.skills),
            "workplace": self.workplace,
            "junior_friendly": self.junior_friendly,
            "regions": list(self.regions),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobPosting:
        """Build a posting from a normalized snapshot object."""

        tags = data.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise ValueError("tags must be a list of strings")
        remote = data.get("remote")
        if not isinstance(remote, bool):
            raise ValueError("remote must be a boolean")
        seniority = _choice(data, "seniority", SENIORITY_LEVELS, default="unknown")
        if "junior_friendly" not in data or data.get("junior_friendly") is None:
            junior_friendly = seniority in _JUNIOR_LEVELS
        else:
            junior_friendly = data.get("junior_friendly")
            if not isinstance(junior_friendly, bool):
                raise ValueError("junior_friendly must be a boolean")
        return cls(
            id=_required_text(data, "id"),
            source=_required_text(data, "source"),
            title=_required_text(data, "title"),
            company=_required_text(data, "company"),
            location=_required_text(data, "location"),
            remote=remote,
            tags=list(tags),
            salary_text=_optional_text(data, "salary_text"),
            posted_at=_optional_text(data, "posted_at"),
            url=_required_text(data, "url"),
            fetched_at=_required_text(data, "fetched_at"),
            seniority=seniority,
            skills=_string_list(data, "skills"),
            workplace=_choice(data, "workplace", WORKPLACES, default="unknown"),
            junior_friendly=junior_friendly,
            regions=_string_list(data, "regions"),
        )


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _choice(data: dict[str, Any], key: str, allowed: tuple[str, ...], *, default: str) -> str:
    if key not in data or data[key] is None:
        return default
    value = data[key]
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{key} must be one of {', '.join(allowed)}")
    return value


def _string_list(data: dict[str, Any], key: str) -> list[str]:
    if key not in data or data[key] is None:
        return []
    value = data[key]
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{key} must be a list of non-empty strings")
    return list(value)


def _optional_text(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return value or None
