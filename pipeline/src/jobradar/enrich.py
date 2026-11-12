"""Fill extraction fields on snapshots that were stored before Day 3.

A row that already has seniority, skills, workplace, junior_friendly, and
regions is left alone, so description-only skills from a later fetch are
not replaced by a title-only pass. Running this twice writes nothing when
the catalog already matches.
"""

from __future__ import annotations

from pathlib import Path

from jobradar.extract import apply_extraction, needs_extraction
from jobradar.models import JobPosting
from jobradar.snapshot import load_normalized, normalized_snapshots, replace_normalized_jobs
from jobradar.store import catalog_path, sync_catalog, write_catalog
from jobradar.trends import build_trends, trends_path, write_trends


def enrich_repository(root: Path) -> str:
    snapshots = normalized_snapshots(root)
    if not snapshots:
        return "No snapshot found. Run: uv run jobradar fetch"
    rewritten = [path for path in snapshots if enrich_normalized_file(path)]
    document, stats = sync_catalog(root, date=snapshots[-1].stem)
    catalog = write_catalog(catalog_path(root), document)
    trends = build_trends(_postings(document))
    trends_file = write_trends(trends_path(root), trends)
    return _format(
        root,
        rewritten=rewritten,
        total=stats.total,
        catalog=catalog,
        trends_file=trends_file,
        trends=trends,
    )


def enrich_normalized_file(path: Path) -> bool:
    """Rewrite one snapshot in place when any row is missing extraction fields."""

    rows = load_normalized(path)
    if rows and not any(needs_extraction(row) for row in rows):
        return False
    jobs: list[JobPosting] = []
    for row in rows:
        posting = JobPosting.from_dict(row)
        if needs_extraction(row):
            posting = apply_extraction(posting)
        jobs.append(posting)
    replace_normalized_jobs(path, jobs)
    return True


def _postings(document: dict[str, object]) -> list[dict[str, object]]:
    postings = document.get("postings")
    if not isinstance(postings, list):
        return []
    return [row for row in postings if isinstance(row, dict)]


def _format(
    root: Path,
    *,
    rewritten: list[Path],
    total: int,
    catalog: Path,
    trends_file: Path,
    trends: dict[str, object],
) -> str:
    junior = int(trends.get("junior_friendly") or 0)
    lines = [
        "Junior Job Radar — extract",
        f"snapshots rewritten: {len(rewritten)}" if rewritten else "snapshots already extracted",
        f"catalog: {total} unique postings",
        f"wrote {catalog.relative_to(root).as_posix()}",
        f"wrote {trends_file.relative_to(root).as_posix()}",
        f"junior-friendly: {_share(junior, total)}",
        "",
        "Workplace",
    ]
    workplace = trends.get("workplace")
    if isinstance(workplace, dict):
        for name in ("remote", "hybrid", "onsite", "unknown"):
            lines.append(f"  {name:<8}  {int(workplace.get(name) or 0)}")
    lines.append("")
    lines.append("Seniority")
    seniority = trends.get("seniority")
    if isinstance(seniority, dict):
        width = max(len(str(name)) for name in seniority) if seniority else 0
        for name, count in seniority.items():
            lines.append(f"  {name:<{width}}  {int(count or 0)}")
    lines.append("")
    lines.append("Top skills")
    top = trends.get("top_skills")
    if isinstance(top, list) and top:
        for index, row in enumerate(top, start=1):
            if isinstance(row, dict):
                lines.append(f"  {index:>2}. {row.get('skill')} ({row.get('count')})")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def _share(count: int, total: int) -> str:
    if total == 0:
        return "n/a (no postings)"
    percent = 100.0 * count / total
    return f"{count}/{total} ({percent:.1f}%)"
