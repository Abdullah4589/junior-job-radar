"""Shared fetch result for every job source."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from jobradar.models import JobPosting


@dataclass(slots=True)
class SourceBatch:
    source: str
    endpoint: str
    records: list[dict[str, Any]]
    jobs: list[JobPosting]
    notice: str | None = None


class JobSource(Protocol):
    name: str
    endpoint: str

    def fetch(self, *, fetched_at: str) -> SourceBatch:
        """Fetch and normalize one board. Raise SourceFetchError on failure."""
