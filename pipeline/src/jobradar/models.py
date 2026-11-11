"""Normalized posting schema shared by every source."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
        )


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_text(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return value or None
