"""Aggregate a normalized snapshot for the `summary` command."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from jobradar.classify import looks_junior


@dataclass(slots=True)
class SnapshotSummary:
    date: str
    total: int
    by_source: list[tuple[str, int]]
    top_tags: list[tuple[str, int]]
    remote_count: int
    junior_count: int
    path: str


def summarize(jobs: list[dict[str, object]], *, date: str, path: str) -> SnapshotSummary:
    counts: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    remote_count = 0
    junior_count = 0
    for job in jobs:
        source = str(job.get("source") or "unknown")
        counts[source] += 1
        title = str(job.get("title") or "")
        job_tags = [str(tag) for tag in job.get("tags") or [] if isinstance(tag, str)]
        tags.update(job_tags)
        if job.get("remote") is True:
            remote_count += 1
        if looks_junior(title, job_tags):
            junior_count += 1
    ranked_sources = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top_tags = sorted(tags.items(), key=lambda item: (-item[1], item[0]))[:15]
    return SnapshotSummary(
        date=date,
        total=len(jobs),
        by_source=ranked_sources,
        top_tags=top_tags,
        remote_count=remote_count,
        junior_count=junior_count,
        path=path,
    )


def format_summary(summary: SnapshotSummary) -> str:
    lines = [
        f"Junior Job Radar — summary {summary.date}",
        f"snapshot: {summary.path}",
        f"{summary.total} software postings",
        "",
        "Counts by source",
    ]
    if summary.by_source:
        width = max(len(name) for name, _count in summary.by_source)
        for name, count in summary.by_source:
            lines.append(f"  {name:<{width}}  {count}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append(f"Remote share: {_share(summary.remote_count, summary.total)}")
    lines.append(f"Junior / entry-level: {_share(summary.junior_count, summary.total)}")
    lines.append("")
    lines.append("Top 15 tags")
    if summary.top_tags:
        for index, (tag, count) in enumerate(summary.top_tags, start=1):
            lines.append(f"  {index:>2}. {tag} ({count})")
    else:
        lines.append("  (no tags)")
    return "\n".join(lines)


def _share(count: int, total: int) -> str:
    if total == 0:
        return "n/a (no postings)"
    percent = 100.0 * count / total
    return f"{count}/{total} ({percent:.1f}%)"
