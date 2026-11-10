"""Normalized posting schema shared by every source."""

from __future__ import annotations

from dataclasses import dataclass


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
