"""Aggregate a normalized snapshot for the `summary` command."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from jobradar.extract import Extraction, extract_posting, needs_extraction
from jobradar.models import SENIORITY_LEVELS, WORKPLACES


@dataclass(slots=True)
class SnapshotSummary:
    date: str
    total: int
    by_source: list[tuple[str, int]]
    top_tags: list[tuple[str, int]]
    top_skills: list[tuple[str, int]]
    remote_count: int
    junior_count: int
    workplace: list[tuple[str, int]]
    seniority: list[tuple[str, int]]
    path: str


def summarize(jobs: list[dict[str, object]], *, date: str, path: str) -> SnapshotSummary:
    counts: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    skills: Counter[str] = Counter()
    workplace: Counter[str] = Counter()
    seniority: Counter[str] = Counter()
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
        found = _extraction(job, title=title, tags=job_tags)
        skills.update(found.skills)
        workplace[found.workplace] += 1
        seniority[found.seniority] += 1
        if found.junior_friendly:
            junior_count += 1
    ranked_sources = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top_tags = sorted(tags.items(), key=lambda item: (-item[1], item[0]))[:15]
    top_skills = sorted(skills.items(), key=lambda item: (-item[1], item[0]))[:15]
    return SnapshotSummary(
        date=date,
        total=len(jobs),
        by_source=ranked_sources,
        top_tags=top_tags,
        top_skills=top_skills,
        remote_count=remote_count,
        junior_count=junior_count,
        workplace=[(name, workplace[name]) for name in WORKPLACES],
        seniority=[(name, seniority[name]) for name in SENIORITY_LEVELS],
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
    lines.extend(_count_block("Workplace", summary.workplace))
    lines.extend(_count_block("Seniority", summary.seniority))
    lines.append("")
    lines.append("Top 15 tags")
    if summary.top_tags:
        for index, (tag, count) in enumerate(summary.top_tags, start=1):
            lines.append(f"  {index:>2}. {tag} ({count})")
    else:
        lines.append("  (no tags)")
    lines.append("")
    lines.append("Top skills")
    if summary.top_skills:
        for index, (skill, count) in enumerate(summary.top_skills, start=1):
            lines.append(f"  {index:>2}. {skill} ({count})")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def _extraction(job: dict[str, object], *, title: str, tags: list[str]) -> Extraction:
    if not needs_extraction(job):
        seniority = job.get("seniority")
        workplace = job.get("workplace")
        skills = job.get("skills")
        regions = job.get("regions")
        junior = job.get("junior_friendly")
        return Extraction(
            seniority=seniority if isinstance(seniority, str) else "unknown",
            skills=[skill for skill in skills if isinstance(skill, str)] if isinstance(skills, list) else [],
            workplace=workplace if isinstance(workplace, str) else "unknown",
            junior_friendly=junior is True,
            regions=[region for region in regions if isinstance(region, str)] if isinstance(regions, list) else [],
        )
    location = job.get("location")
    return extract_posting(
        title=title,
        location=location if isinstance(location, str) else "",
        tags=tags,
        remote=job.get("remote") is True,
        refine=False,
    )


def _count_block(title: str, rows: list[tuple[str, int]]) -> list[str]:
    lines = ["", title]
    width = max((len(name) for name, _count in rows), default=0)
    for name, count in rows:
        lines.append(f"  {name:<{width}}  {count}")
    return lines


def _share(count: int, total: int) -> str:
    if total == 0:
        return "n/a (no postings)"
    percent = 100.0 * count / total
    return f"{count}/{total} ({percent:.1f}%)"
