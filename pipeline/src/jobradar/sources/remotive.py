"""Remotive public remote-jobs API.

Docs and terms: https://remotive.com/api-documentation
The public feed is delayed by about 24 hours. Remotive asks callers to
link back to the job URL, mention Remotive, and fetch at most a few times
a day. This pipeline makes one GET per run.
"""

from __future__ import annotations

from typing import Any

from jobradar.classify import is_software_role
from jobradar.http_client import SourceFetchError, get_json
from jobradar.normalize import normalize_remotive
from jobradar.sources.base import SourceBatch

ENDPOINT = "https://remotive.com/api/remote-jobs"


class RemotiveSource:
    name = "remotive"
    endpoint = ENDPOINT

    def fetch(self, *, fetched_at: str) -> SourceBatch:
        payload = get_json(self.endpoint)
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise SourceFetchError("remotive: response did not contain a jobs list")
        notice = _notice(payload.get("0-legal-notice"))
        records: list[dict[str, Any]] = []
        jobs = []
        for item in payload["jobs"]:
            if not isinstance(item, dict):
                continue
            records.append(_compact(item))
            posting = normalize_remotive(item, fetched_at=fetched_at)
            if posting is None:
                continue
            category = item.get("category") if isinstance(item.get("category"), str) else ""
            if is_software_role(posting.title, category=category, tags=posting.tags):
                jobs.append(posting)
        return SourceBatch(
            source=self.name,
            endpoint=self.endpoint,
            records=records,
            jobs=jobs,
            notice=notice,
        )


def _compact(item: dict[str, Any]) -> dict[str, Any]:
    """Keep the fields we normalize. Drop HTML descriptions and logo URLs."""

    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "company_name": item.get("company_name"),
        "candidate_required_location": item.get("candidate_required_location"),
        "job_type": item.get("job_type"),
        "category": item.get("category"),
        "tags": item.get("tags") or [],
        "salary": item.get("salary") or "",
        "publication_date": item.get("publication_date"),
        "url": item.get("url"),
    }


def _notice(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None
