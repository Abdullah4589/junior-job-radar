"""Drop duplicate postings inside a single fetch."""

from __future__ import annotations

from jobradar.models import JobPosting
from jobradar.normalize import canonical_url, identity_key


def dedupe_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    """Keep one posting per canonical URL and per company + title.

    When two records collide, the one with more filled-in fields wins.
    A tie keeps the earlier record, so source order stays predictable.
    """

    by_url: dict[str, int] = {}
    by_identity: dict[str, int] = {}
    kept: list[JobPosting] = []

    for job in jobs:
        url_key = canonical_url(job.url)
        ident = identity_key(job.company, job.title)
        existing_index = by_url.get(url_key)
        if existing_index is None:
            existing_index = by_identity.get(ident)
        if existing_index is None:
            index = len(kept)
            by_url[url_key] = index
            by_identity[ident] = index
            kept.append(job)
            continue
        current = kept[existing_index]
        if _richness(job) > _richness(current):
            kept[existing_index] = job
            by_url[canonical_url(job.url)] = existing_index
            by_identity[identity_key(job.company, job.title)] = existing_index
    return kept


def _richness(job: JobPosting) -> tuple[int, int, int, int]:
    return (
        1 if job.salary_text else 0,
        len(job.tags),
        1 if job.posted_at else 0,
        len(job.location),
    )
