"""Command line: `jobradar fetch`, `jobradar summary`, and `jobradar extract`."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone

from jobradar.enrich import enrich_repository
from jobradar.paths import find_repo_root
from jobradar.pipeline import (
    build_normalized_document,
    build_raw_document,
    collect,
    format_fetch_report,
)
from jobradar.snapshot import latest_normalized, load_normalized, normalized_path
from jobradar.sources import default_sources
from jobradar.store import persist_collection
from jobradar.summary import format_summary, summarize

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(argv))


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jobradar",
        description="Fetch public software job postings and summarize a snapshot.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch sources and write today's snapshot")
    fetch.add_argument(
        "--date",
        help=(
            "Snapshot date YYYY-MM-DD (default: today, UTC). "
            "Refreshes that date only; earlier dates stay on disk."
        ),
    )

    summary = sub.add_parser("summary", help="Print counts, tags, remote share, and junior share")
    summary.add_argument("--date", help="Snapshot date YYYY-MM-DD (default: latest)")

    sub.add_parser(
        "extract",
        help="Fill seniority, skills, and workplace on stored snapshots and write trends.json",
    )

    args = parser.parse_args(argv)
    try:
        root = find_repo_root()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.command == "fetch":
        return _fetch(root, args.date)
    if args.command == "extract":
        print(enrich_repository(root))
        return 0
    return _summary(root, args.date)


def _fetch(root, date: str | None) -> int:
    stamp = datetime.now(timezone.utc)
    snapshot_date = date or stamp.strftime("%Y-%m-%d")
    if not _DATE.fullmatch(snapshot_date):
        print(f"Invalid date {snapshot_date!r}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    fetched_at = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    collection = collect(default_sources(), fetched_at=fetched_at)
    if not collection.any_ok:
        print(
            format_fetch_report(collection, date=snapshot_date, paths=[]),
            file=sys.stderr,
        )
        return 1
    written, stats = persist_collection(
        root,
        date=snapshot_date,
        raw_document=build_raw_document(collection),
        normalized_document=build_normalized_document(collection, date=snapshot_date),
        jobs=collection.jobs,
    )
    relative = [path.relative_to(root).as_posix() for path in written]
    print(
        format_fetch_report(
            collection,
            date=snapshot_date,
            paths=relative,
            catalog=(stats.total, stats.new, stats.seen_again),
        )
    )
    return 0


def _summary(root, date: str | None) -> int:
    if date is not None and not _DATE.fullmatch(date):
        print(f"Invalid date {date!r}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if date is None:
        path = latest_normalized(root)
        if path is None:
            print("No snapshot found. Run: uv run jobradar fetch", file=sys.stderr)
            return 1
    else:
        path = normalized_path(root, date)
        if not path.is_file():
            print(
                f"No snapshot for {date}. Run: uv run jobradar fetch",
                file=sys.stderr,
            )
            return 1
    try:
        jobs = load_normalized(path)
    except (OSError, ValueError) as exc:
        print(f"Could not read {path}: {exc}", file=sys.stderr)
        return 1
    relative = path.relative_to(root).as_posix()
    print(format_summary(summarize(jobs, date=path.stem, path=relative)))
    return 0
