"""Cross-run catalog of unique postings.

Daily files under `data/raw/` and `data/normalized/` are the fetch history:
one UTC date each, and a later date never deletes an earlier one. Re-running
a date refreshes only that date.

`data/jobradar.sqlite` is the catalog. The same canonical URL, or the same
company and title, is one row no matter how many days it is reposted.
`first_seen` stays on the earliest snapshot date. A repost updates `last_seen`.
Every fetch rebuilds the catalog from the snapshot files, so a role that
leaves those files drops out. When the rebuilt dump matches the file already
on disk, the database is not rewritten. `data/catalog/postings.json` is that
dump, so a pull request can show the deduped series.

The trend count for a date is `days[].new` (postings whose `first_seen` is
that date). `seen_again` is the reposts kept out of that count.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobradar.dedupe import richness
from jobradar.models import JobPosting
from jobradar.normalize import canonical_url, identity_key
from jobradar.snapshot import load_normalized, normalized_snapshots, write_snapshots

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_NOTES = (
    "One row per posting across every daily snapshot. first_seen is the "
    "earliest snapshot date. A later repost with the same canonical URL, or "
    "the same company and title, updates last_seen and does not add a row. "
    "days.new is the deduped trend count; days.seen_again is reposts."
)

_RECORD_COLUMNS = (
    "job_id",
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
    "canonical_url",
    "identity_key",
)


@dataclass(slots=True)
class CatalogStats:
    total: int
    new: int
    seen_again: int


def database_path(root: Path) -> Path:
    return root / "data" / "jobradar.sqlite"


def catalog_path(root: Path) -> Path:
    return root / "data" / "catalog" / "postings.json"


class PostingStore:
    """SQLite catalog. One connection, explicit transactions, no WAL files."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> PostingStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def upsert(self, jobs: list[JobPosting], *, seen_on: str) -> None:
        """Fold jobs into the catalog for `seen_on`.

        The same jobs on the same date are a no-op: the transaction rolls
        back, so the database file is left untouched.
        """

        if not _DATE.fullmatch(seen_on):
            raise ValueError(f"Invalid date {seen_on!r}. Use YYYY-MM-DD.")
        self._conn.execute("BEGIN")
        try:
            changed = False
            for job in jobs:
                if self._upsert_one(job, seen_on):
                    changed = True
            if changed:
                self._assert_unique_keys()
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        if changed:
            self._conn.execute("COMMIT")
        else:
            self._conn.execute("ROLLBACK")

    def sync_snapshots(self, root: Path) -> None:
        """Upsert every normalized snapshot. Oldest date first.

        `first_seen` is the minimum date either way, so a later file that is
        applied before an earlier one still lands on the earlier date.
        """

        for path in normalized_snapshots(root):
            jobs = [JobPosting.from_dict(row) for row in load_normalized(path)]
            self.upsert(jobs, seen_on=path.stem)

    def stats_for(self, date: str) -> CatalogStats:
        total = int(self._conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0])
        row = self._conn.execute(
            """
            SELECT
                SUM(CASE WHEN p.first_seen = s.seen_on THEN 1 ELSE 0 END) AS new,
                SUM(CASE WHEN p.first_seen < s.seen_on THEN 1 ELSE 0 END) AS seen_again
            FROM sightings AS s
            JOIN postings AS p ON p.id = s.posting_id
            WHERE s.seen_on = ?
            """,
            (date,),
        ).fetchone()
        return CatalogStats(
            total=total,
            new=int(row["new"] or 0),
            seen_again=int(row["seen_again"] or 0),
        )

    def export_document(self) -> dict[str, Any]:
        postings = [
            _export_posting(row)
            for row in self._conn.execute(
                """
                SELECT * FROM postings
                ORDER BY first_seen, source, job_id, id
                """
            )
        ]
        days = [
            {
                "date": row["date"],
                "new": int(row["new"] or 0),
                "seen_again": int(row["seen_again"] or 0),
                "collected": int(row["collected"] or 0),
            }
            for row in self._conn.execute(
                """
                SELECT
                    s.seen_on AS date,
                    SUM(CASE WHEN p.first_seen = s.seen_on THEN 1 ELSE 0 END) AS new,
                    SUM(CASE WHEN p.first_seen < s.seen_on THEN 1 ELSE 0 END) AS seen_again,
                    COUNT(*) AS collected
                FROM sightings AS s
                JOIN postings AS p ON p.id = s.posting_id
                GROUP BY s.seen_on
                ORDER BY s.seen_on
                """
            )
        ]
        return {"notes": _NOTES, "postings": postings, "days": days}

    def _ensure_schema(self) -> None:
        existing = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'postings'"
        ).fetchone()
        if existing is not None:
            return
        self._conn.execute("BEGIN")
        try:
            self._conn.execute(
                """
                CREATE TABLE postings (
                    id INTEGER PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    remote INTEGER NOT NULL,
                    tags TEXT NOT NULL,
                    salary_text TEXT,
                    posted_at TEXT,
                    url TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    identity_key TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE sightings (
                    posting_id INTEGER NOT NULL
                        REFERENCES postings(id) ON DELETE CASCADE,
                    seen_on TEXT NOT NULL,
                    PRIMARY KEY (posting_id, seen_on)
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX idx_postings_canonical_url
                ON postings(canonical_url)
                """
            )
            self._conn.execute(
                """
                CREATE INDEX idx_postings_identity_key
                ON postings(identity_key)
                """
            )
            self._conn.execute("PRAGMA user_version = 1")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        self._conn.execute("COMMIT")

    def _upsert_one(self, job: JobPosting, seen_on: str) -> bool:
        record = _record(job)
        matches = self._conn.execute(
            """
            SELECT * FROM postings
            WHERE canonical_url = ? OR identity_key = ?
            """,
            (record["canonical_url"], record["identity_key"]),
        ).fetchall()
        if not matches:
            posting_id = self._insert(record, seen_on)
            self._add_sighting(posting_id, seen_on)
            return True

        keeper = min(matches, key=lambda row: (row["first_seen"], row["id"]))
        best = min(
            matches,
            key=lambda row: (
                tuple(-part for part in richness(_job_from_row(row))),
                row["first_seen"],
                row["id"],
            ),
        )
        chosen = record if richness(job) > richness(_job_from_row(best)) else _record_from_row(best)
        first_seen = min([row["first_seen"] for row in matches] + [seen_on])
        last_seen = max([row["last_seen"] for row in matches] + [seen_on])
        changed = False
        if not _row_equals(keeper, chosen, first_seen=first_seen, last_seen=last_seen):
            self._update(keeper["id"], chosen, first_seen=first_seen, last_seen=last_seen)
            changed = True
        for row in matches:
            if row["id"] == keeper["id"]:
                continue
            self._reassign_sightings(row["id"], keeper["id"])
            self._conn.execute("DELETE FROM postings WHERE id = ?", (row["id"],))
            changed = True
        if self._add_sighting(keeper["id"], seen_on):
            changed = True
        return changed

    def _insert(self, record: dict[str, Any], seen_on: str) -> int:
        columns = ", ".join((*_RECORD_COLUMNS, "first_seen", "last_seen"))
        placeholders = ", ".join("?" for _ in (*_RECORD_COLUMNS, "first_seen", "last_seen"))
        cursor = self._conn.execute(
            f"INSERT INTO postings ({columns}) VALUES ({placeholders})",
            [record[column] for column in _RECORD_COLUMNS] + [seen_on, seen_on],
        )
        posting_id = cursor.lastrowid
        if posting_id is None:
            raise RuntimeError("SQLite did not return a row id for a new posting")
        return int(posting_id)

    def _update(
        self,
        posting_id: int,
        record: dict[str, Any],
        *,
        first_seen: str,
        last_seen: str,
    ) -> None:
        assignments = ", ".join(f"{column} = ?" for column in _RECORD_COLUMNS)
        self._conn.execute(
            f"""
            UPDATE postings
            SET {assignments}, first_seen = ?, last_seen = ?
            WHERE id = ?
            """,
            [record[column] for column in _RECORD_COLUMNS] + [first_seen, last_seen, posting_id],
        )

    def _add_sighting(self, posting_id: int, seen_on: str) -> bool:
        before = self._conn.total_changes
        self._conn.execute(
            "INSERT OR IGNORE INTO sightings (posting_id, seen_on) VALUES (?, ?)",
            (posting_id, seen_on),
        )
        return self._conn.total_changes > before

    def _reassign_sightings(self, source_id: int, target_id: int) -> None:
        rows = self._conn.execute(
            "SELECT seen_on FROM sightings WHERE posting_id = ?",
            (source_id,),
        ).fetchall()
        for row in rows:
            self._add_sighting(target_id, row["seen_on"])
        self._conn.execute("DELETE FROM sightings WHERE posting_id = ?", (source_id,))

    def _assert_unique_keys(self) -> None:
        url_dupe = self._conn.execute(
            """
            SELECT canonical_url FROM postings
            GROUP BY canonical_url
            HAVING COUNT(*) > 1
            """
        ).fetchone()
        identity_dupe = self._conn.execute(
            """
            SELECT identity_key FROM postings
            GROUP BY identity_key
            HAVING COUNT(*) > 1
            """
        ).fetchone()
        if url_dupe is not None or identity_dupe is not None:
            raise RuntimeError("Catalog has two postings that share a URL or a company and title")


def persist_collection(
    root: Path,
    *,
    date: str,
    raw_document: dict[str, Any],
    normalized_document: dict[str, Any],
    jobs: list[JobPosting],
) -> tuple[list[Path], CatalogStats]:
    """Write one date's snapshot, then rebuild the catalog from every snapshot.

    Files for other dates are not opened for writing. The database is replaced
    only when the rebuilt dump differs, so running the same snapshots again
    leaves `data/jobradar.sqlite` byte for byte.
    """

    if not _DATE.fullmatch(date):
        raise ValueError(f"Invalid date {date!r}. Use YYYY-MM-DD.")
    written = write_snapshots(
        root,
        date=date,
        raw_document=raw_document,
        normalized_document=normalized_document,
        jobs=jobs,
    )
    document, stats = sync_catalog(root, date=date)
    catalog = write_catalog(catalog_path(root), document)
    return [*written, database_path(root), catalog], stats


def sync_catalog(root: Path, *, date: str) -> tuple[dict[str, Any], CatalogStats]:
    """Rebuild the catalog from normalized snapshots.

    The rebuild happens in a temporary database. The file in `data/` is
    replaced only when the dump changed, which keeps an unchanged catalog
    from showing up as a new commit.
    """

    if not _DATE.fullmatch(date):
        raise ValueError(f"Invalid date {date!r}. Use YYYY-MM-DD.")
    with tempfile.TemporaryDirectory() as tmp:
        fresh_path = Path(tmp) / "jobradar.sqlite"
        with PostingStore(fresh_path) as fresh:
            fresh.sync_snapshots(root)
            document = fresh.export_document()
        stats = _stats_from_document(document, date)
        target = database_path(root)
        if target.is_file() and _catalog_matches(target, document):
            return document, stats
        _install_database(fresh_path, target)
    return document, stats


def _stats_from_document(document: dict[str, Any], date: str) -> CatalogStats:
    postings = document.get("postings")
    total = len(postings) if isinstance(postings, list) else 0
    days = document.get("days")
    if isinstance(days, list):
        for day in days:
            if isinstance(day, dict) and day.get("date") == date:
                return CatalogStats(
                    total=total,
                    new=int(day.get("new") or 0),
                    seen_again=int(day.get("seen_again") or 0),
                )
    return CatalogStats(total=total, new=0, seen_again=0)


def _catalog_matches(path: Path, document: dict[str, Any]) -> bool:
    try:
        with PostingStore(path) as current:
            return current.export_document() == document
    except sqlite3.DatabaseError:
        return False


def _install_database(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f".{target.name}.staging")
    try:
        shutil.copy2(source, staging)
        staging.replace(target)
    finally:
        staging.unlink(missing_ok=True)


def write_catalog(path: Path, document: dict[str, Any]) -> Path:
    payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == payload:
        return path
    path.write_text(payload, encoding="utf-8")
    return path


def _record(job: JobPosting) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "source": job.source,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "remote": 1 if job.remote else 0,
        "tags": json.dumps(job.tags, ensure_ascii=False, separators=(",", ":")),
        "salary_text": job.salary_text,
        "posted_at": job.posted_at,
        "url": job.url,
        "fetched_at": job.fetched_at,
        "canonical_url": canonical_url(job.url),
        "identity_key": identity_key(job.company, job.title),
    }


def _record_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {column: row[column] for column in _RECORD_COLUMNS}


def _row_equals(
    row: sqlite3.Row,
    record: dict[str, Any],
    *,
    first_seen: str,
    last_seen: str,
) -> bool:
    for column in _RECORD_COLUMNS:
        if row[column] != record[column]:
            return False
    return row["first_seen"] == first_seen and row["last_seen"] == last_seen


def _job_from_row(row: sqlite3.Row) -> JobPosting:
    tags = json.loads(row["tags"])
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        raise ValueError(f"Stored tags for {row['job_id']} are invalid")
    return JobPosting(
        id=row["job_id"],
        source=row["source"],
        title=row["title"],
        company=row["company"],
        location=row["location"],
        remote=bool(row["remote"]),
        tags=list(tags),
        salary_text=row["salary_text"],
        posted_at=row["posted_at"],
        url=row["url"],
        fetched_at=row["fetched_at"],
    )


def _export_posting(row: sqlite3.Row) -> dict[str, Any]:
    payload = _job_from_row(row).to_dict()
    payload["first_seen"] = row["first_seen"]
    payload["last_seen"] = row["last_seen"]
    return payload
