"""Write dated raw and normalized snapshots under the repo `data/` directory."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from jobradar.models import JobPosting

CSV_FIELDS = [
    "id",
    "source",
    "title",
    "company",
    "location",
    "remote",
    "tags",
    "salary_text",
    "posted_at",
    "url",
    "fetched_at",
]


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


def _write_csv(path: Path, jobs: list[JobPosting]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for job in jobs:
            row = job.to_dict()
            tags = row["tags"]
            row["tags"] = "|".join(tags) if isinstance(tags, list) else ""
            row["remote"] = "true" if row["remote"] else "false"
            if row["salary_text"] is None:
                row["salary_text"] = ""
            if row["posted_at"] is None:
                row["posted_at"] = ""
            writer.writerow(row)
