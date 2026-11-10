"""Arbeitnow public job-board API.

Terms, from the payload itself: the API is free, please don't abuse it,
and please link back to Arbeitnow. Page 1 is the newest 300 postings
(updated about hourly). This pipeline requests that single page.
https://www.arbeitnow.com/api/job-board-api
"""

from __future__ import annotations

from typing import Any

from jobradar.classify import is_software_role
from jobradar.http_client import SourceFetchError, get_json
from jobradar.normalize import normalize_arbeitnow
from jobradar.sources.base import SourceBatch

ENDPOINT = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource:
    name = "arbeitnow"
    endpoint = ENDPOINT

    def fetch(self, *, fetched_at: str) -> SourceBatch:
        payload = get_json(self.endpoint)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise SourceFetchError("arbeitnow: response did not contain a data list")
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        notice = meta.get("terms") if isinstance(meta.get("terms"), str) else None
        if notice:
            notice = " ".join(notice.split())
        records: list[dict[str, Any]] = []
        jobs = []
        for item in payload["data"]:
            if not isinstance(item, dict):
                continue
            records.append(_compact(item))
            posting = normalize_arbeitnow(item, fetched_at=fetched_at)
            if posting is None:
                continue
            if is_software_role(posting.title, tags=posting.tags):
                jobs.append(posting)
        return SourceBatch(
            source=self.name,
            endpoint=self.endpoint,
            records=records,
            jobs=jobs,
            notice=notice,
        )


def _compact(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "slug": item.get("slug"),
        "company_name": item.get("company_name"),
        "title": item.get("title"),
        "remote": bool(item.get("remote")),
        "url": item.get("url"),
        "tags": item.get("tags") or [],
        "job_types": item.get("job_types") or [],
        "location": item.get("location") or "",
        "created_at": item.get("created_at"),
    }
