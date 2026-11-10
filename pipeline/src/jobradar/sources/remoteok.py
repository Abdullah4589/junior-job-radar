"""Remote OK public JSON API.

The first array element is a legal notice, not a job. Remote OK requires a
link back to the posting URL (a normal follow link, not nofollow) and a
mention of the name "Remote OK". Do not use their logo. One GET per run.
https://remoteok.com/api
"""

from __future__ import annotations

from typing import Any

from jobradar.classify import is_software_role
from jobradar.http_client import SourceFetchError, get_json
from jobradar.normalize import normalize_remoteok
from jobradar.sources.base import SourceBatch

ENDPOINT = "https://remoteok.com/api"


class RemoteOkSource:
    name = "remoteok"
    endpoint = ENDPOINT

    def fetch(self, *, fetched_at: str) -> SourceBatch:
        payload = get_json(self.endpoint)
        if not isinstance(payload, list):
            raise SourceFetchError("remoteok: response was not a JSON list")
        notice: str | None = None
        records: list[dict[str, Any]] = []
        jobs = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            if "id" not in item and isinstance(item.get("legal"), str):
                notice = " ".join(item["legal"].split())
                continue
            if "id" not in item:
                continue
            records.append(_compact(item))
            posting = normalize_remoteok(item, fetched_at=fetched_at)
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
        "id": item.get("id"),
        "position": item.get("position"),
        "company": item.get("company"),
        "location": item.get("location") or "",
        "tags": item.get("tags") or [],
        "salary_min": item.get("salary_min") or 0,
        "salary_max": item.get("salary_max") or 0,
        "date": item.get("date"),
        "epoch": item.get("epoch"),
        "url": item.get("url"),
        "apply_url": item.get("apply_url"),
    }
