"""Write dated raw and normalized snapshots under the repo `data/` directory."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from jobradar.models import FIELD_NAMES, JobPosting

CSV_FIELDS = list(FIELD_NAMES)


def write_snapshots(
    root: Path,
    *,
    date: str,
    raw_document: dict[str, Any],
    normalized_document: dict[str, Any],
    jobs: list[JobPosting],
) -> list[Path]:
    raw_path = root / "data" / "raw" / f"{date}.json"
    json_path = root / "data" / "normalized" / f"{date}.json"
    csv_path = root / "data" / "normalized" / f"{date}.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(raw_path, raw_document)
    _write_json(json_path, normalized_document)
    _write_csv(csv_path, jobs)
    return [raw_path, json_path, csv_path]


def snapshot_date_from_name(path: Path) -> str:
    return path.stem


def latest_normalized(root: Path) -> Path | None:
    directory = root / "data" / "normalized"
    if not directory.is_dir():
        return None
    files = sorted(directory.glob("*.json"))
    return files[-1] if files else None


def normalized_path(root: Path, date: str) -> Path:
    return root / "data" / "normalized" / f"{date}.json"


def normalized_snapshots(root: Path) -> list[Path]:
    """Normalized JSON snapshots, oldest date first.

    Only `YYYY-MM-DD.json` names count. Other files in the directory are ignored.
    """

    directory = root / "data" / "normalized"
    if not directory.is_dir():
        return []
    paths = [
        path
        for path in directory.glob("*.json")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.stem)
    ]
    return sorted(paths, key=lambda path: path.stem)


def load_normalized(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    jobs = document.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError(f"{path} has no jobs list")
    return [job for job in jobs if isinstance(job, dict)]


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def replace_normalized_jobs(path: Path, jobs: list[JobPosting]) -> None:
    """Replace the jobs in one snapshot and rewrite its CSV. Other dates stay."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} is not a JSON object")
    document["jobs"] = [job.to_dict() for job in jobs]
    document["count"] = len(jobs)
    _write_json(path, document)
    _write_csv(path.with_suffix(".csv"), jobs)


def _write_csv(path: Path, jobs: list[JobPosting]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for job in jobs:
            row = job.to_dict()
            row["tags"] = _pipe(row["tags"])
            row["skills"] = _pipe(row["skills"])
            row["regions"] = _pipe(row["regions"])
            row["remote"] = "true" if row["remote"] else "false"
            row["junior_friendly"] = "true" if row["junior_friendly"] else "false"
            if row["salary_text"] is None:
                row["salary_text"] = ""
            if row["posted_at"] is None:
                row["posted_at"] = ""
            writer.writerow(row)


def _pipe(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return "|".join(item for item in value if isinstance(item, str))
