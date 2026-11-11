"""Fetch every source, dedupe software roles, and build snapshot documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobradar.dedupe import dedupe_jobs
from jobradar.models import JobPosting
from jobradar.sources.base import JobSource, SourceBatch

ATTRIBUTION = {
    "remotive": {"source": "remotive", "name": "Remotive", "url": "https://remotive.com"},
    "remoteok": {"source": "remoteok", "name": "Remote OK", "url": "https://remoteok.com"},
    "arbeitnow": {
        "source": "arbeitnow",
        "name": "Arbeitnow",
        "url": "https://www.arbeitnow.com",
    },
}


@dataclass(slots=True)
class SourceReport:
    source: str
    endpoint: str
    ok: bool
    error: str | None
    fetched_count: int
    software_count: int
    notice: str | None = None
    records: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Collection:
    fetched_at: str
    sources: list[SourceReport]
    jobs: list[JobPosting]
    software_before_dedupe: int

    @property
    def any_ok(self) -> bool:
        return any(source.ok for source in self.sources)


def collect(sources: list[JobSource], *, fetched_at: str) -> Collection:
    """Fetch each source. A failure is recorded and the next source still runs."""

    reports: list[SourceReport] = []
    software_jobs: list[JobPosting] = []
    for source in sources:
        try:
            batch = source.fetch(fetched_at=fetched_at)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}".replace("\n", " ").strip()
            reports.append(
                SourceReport(
                    source=source.name,
                    endpoint=getattr(source, "endpoint", ""),
                    ok=False,
                    error=message,
                    fetched_count=0,
                    software_count=0,
                )
            )
            continue
        reports.append(_report(batch))
        software_jobs.extend(batch.jobs)
    deduped = dedupe_jobs(software_jobs)
    deduped.sort(key=lambda job: (job.posted_at or "", job.id), reverse=True)
    return Collection(
        fetched_at=fetched_at,
        sources=reports,
        jobs=deduped,
        software_before_dedupe=len(software_jobs),
    )


def build_raw_document(collection: Collection) -> dict[str, Any]:
    return {
        "fetched_at": collection.fetched_at,
        "notes": (
            "Compact source payloads. Job descriptions and logos are omitted "
            "so the snapshot stays small. Normalized software roles are in "
            "data/normalized/."
        ),
        "sources": [
            {
                "source": report.source,
                "endpoint": report.endpoint,
                "ok": report.ok,
                "error": report.error,
                "fetched_count": report.fetched_count,
                "software_count": report.software_count,
                "notice": report.notice,
                "records": report.records,
            }
            for report in collection.sources
        ],
    }


def build_normalized_document(collection: Collection, *, date: str) -> dict[str, Any]:
    succeeded = {report.source for report in collection.sources if report.ok}
    attribution = [ATTRIBUTION[name] for name in ("remotive", "remoteok", "arbeitnow") if name in succeeded]
    return {
        "date": date,
        "fetched_at": collection.fetched_at,
        "count": len(collection.jobs),
        "attribution": attribution,
        "jobs": [job.to_dict() for job in collection.jobs],
    }


def format_fetch_report(
    collection: Collection,
    *,
    date: str,
    paths: list[str],
    catalog: tuple[int, int, int] | None = None,
) -> str:
    lines = [
        f"Junior Job Radar — fetch {date}",
        f"fetched_at {collection.fetched_at}",
    ]
    for report in collection.sources:
        if report.ok:
            lines.append(
                f"{report.source}: fetched {report.fetched_count}, "
                f"software {report.software_count}"
            )
        else:
            lines.append(f"{report.source}: FAILED ({report.error}); continuing")
    removed = collection.software_before_dedupe - len(collection.jobs)
    lines.append(
        f"unique software roles after dedupe: {len(collection.jobs)} "
        f"({removed} duplicates removed)"
    )
    for path in paths:
        lines.append(f"wrote {path}")
    if catalog is not None:
        total, first_seen, already_stored = catalog
        lines.append(
            f"catalog: {total} unique postings "
            f"({first_seen} first seen on {date}, {already_stored} already stored)"
        )
    if not collection.any_ok:
        lines.append("no source succeeded")
    return "\n".join(lines)


def _report(batch: SourceBatch) -> SourceReport:
    return SourceReport(
        source=batch.source,
        endpoint=batch.endpoint,
        ok=True,
        error=None,
        fetched_count=len(batch.records),
        software_count=len(batch.jobs),
        notice=batch.notice,
        records=batch.records,
    )
