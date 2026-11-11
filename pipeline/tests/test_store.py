import json
from pathlib import Path

from jobradar.models import JobPosting
from jobradar.paths import find_repo_root
from jobradar.snapshot import load_normalized
from jobradar.store import PostingStore, persist_collection


def _job(**overrides: object) -> JobPosting:
    data: dict[str, object] = {
        "id": "remoteok:1",
        "source": "remoteok",
        "title": "Backend Engineer",
        "company": "Acme, Inc.",
        "location": "Remote",
        "remote": True,
        "tags": ["python"],
        "salary_text": None,
        "posted_at": "2026-11-01T00:00:00Z",
        "url": "https://remoteok.com/jobs/1?utm_source=newsletter",
        "fetched_at": "2026-11-10T08:00:00Z",
    }
    data.update(overrides)
    return JobPosting(**data)  # type: ignore[arg-type]


def _raw(date: str) -> dict[str, object]:
    return {"fetched_at": f"{date}T08:00:00Z", "notes": "test", "sources": []}


def _normalized(date: str, jobs: list[JobPosting]) -> dict[str, object]:
    fetched_at = jobs[0].fetched_at if jobs else f"{date}T08:00:00Z"
    return {
        "date": date,
        "fetched_at": fetched_at,
        "count": len(jobs),
        "attribution": [],
        "jobs": [job.to_dict() for job in jobs],
    }


def _persist(root: Path, date: str, jobs: list[JobPosting]):
    return persist_collection(
        root,
        date=date,
        raw_document=_raw(date),
        normalized_document=_normalized(date, jobs),
        jobs=jobs,
    )


def _catalog(root: Path) -> dict[str, object]:
    return json.loads((root / "data" / "catalog" / "postings.json").read_text(encoding="utf-8"))


def test_repeating_a_day_does_not_rewrite_the_database_or_add_rows(tmp_path: Path):
    job = _job()
    _persist(tmp_path, "2026-11-10", [job])
    database = (tmp_path / "data" / "jobradar.sqlite").read_bytes()
    catalog = (tmp_path / "data" / "catalog" / "postings.json").read_bytes()
    snapshot = (tmp_path / "data" / "normalized" / "2026-11-10.json").read_bytes()

    _persist(tmp_path, "2026-11-10", [job])

    assert (tmp_path / "data" / "jobradar.sqlite").read_bytes() == database
    assert (tmp_path / "data" / "catalog" / "postings.json").read_bytes() == catalog
    assert (tmp_path / "data" / "normalized" / "2026-11-10.json").read_bytes() == snapshot
    document = _catalog(tmp_path)
    assert document["days"] == [
        {"date": "2026-11-10", "new": 1, "seen_again": 0, "collected": 1}
    ]
    assert len(document["postings"]) == 1


def test_repost_on_a_later_day_stays_one_posting(tmp_path: Path):
    first = _job()
    _persist(tmp_path, "2026-11-10", [first])
    earlier_raw = (tmp_path / "data" / "raw" / "2026-11-10.json").read_bytes()
    earlier_normalized = (tmp_path / "data" / "normalized" / "2026-11-10.json").read_bytes()
    earlier_csv = (tmp_path / "data" / "normalized" / "2026-11-10.csv").read_bytes()

    richer = _job(
        id="remotive:9",
        source="remotive",
        company="Acme Inc",
        url="https://remotive.com/remote-jobs/backend-engineer",
        salary_text="$90,000",
        tags=["python", "django"],
        fetched_at="2026-11-11T08:00:00Z",
    )
    extra = _job(
        id="arbeitnow:2",
        source="arbeitnow",
        title="Frontend Engineer",
        company="Other",
        url="https://example.com/jobs/2",
        fetched_at="2026-11-11T08:00:00Z",
    )
    _, stats = _persist(tmp_path, "2026-11-11", [richer, extra])

    assert stats.total == 2
    assert stats.new == 1
    assert stats.seen_again == 1
    assert (tmp_path / "data" / "raw" / "2026-11-10.json").read_bytes() == earlier_raw
    assert (tmp_path / "data" / "normalized" / "2026-11-10.json").read_bytes() == earlier_normalized
    assert (tmp_path / "data" / "normalized" / "2026-11-10.csv").read_bytes() == earlier_csv
    assert (tmp_path / "data" / "normalized" / "2026-11-11.json").is_file()

    document = _catalog(tmp_path)
    stored = next(item for item in document["postings"] if item["first_seen"] == "2026-11-10")
    assert stored["id"] == "remotive:9"
    assert stored["salary_text"] == "$90,000"
    assert stored["last_seen"] == "2026-11-11"
    assert stored["tags"] == ["python", "django"]
    assert document["days"] == [
        {"date": "2026-11-10", "new": 1, "seen_again": 0, "collected": 1},
        {"date": "2026-11-11", "new": 1, "seen_again": 1, "collected": 2},
    ]


def test_poorer_repost_does_not_wipe_salary_or_move_first_seen(tmp_path: Path):
    rich = _job(salary_text="$120,000", tags=["python", "django"])
    _persist(tmp_path, "2026-11-10", [rich])
    poor = _job(
        salary_text=None,
        tags=["python"],
        fetched_at="2026-11-12T08:00:00Z",
        url="https://www.remoteok.com/jobs/1",
    )
    _persist(tmp_path, "2026-11-12", [poor])

    stored = _catalog(tmp_path)["postings"][0]
    assert stored["salary_text"] == "$120,000"
    assert stored["tags"] == ["python", "django"]
    assert stored["fetched_at"] == "2026-11-10T08:00:00Z"
    assert stored["first_seen"] == "2026-11-10"
    assert stored["last_seen"] == "2026-11-12"


def test_an_earlier_snapshot_moves_first_seen_backward(tmp_path: Path):
    later = _job(salary_text="$90,000", fetched_at="2026-11-11T08:00:00Z")
    _persist(tmp_path, "2026-11-11", [later])
    earlier = _job(salary_text=None, fetched_at="2026-11-10T08:00:00Z")
    _persist(tmp_path, "2026-11-10", [earlier])

    stored = _catalog(tmp_path)["postings"][0]
    assert stored["first_seen"] == "2026-11-10"
    assert stored["last_seen"] == "2026-11-11"
    assert stored["salary_text"] == "$90,000"
    assert len(_catalog(tmp_path)["postings"]) == 1


def test_a_later_posting_collapses_rows_that_share_a_url_and_a_title(tmp_path: Path):
    engineer = _job(id="a", title="Backend Engineer", company="Acme", url="https://example.com/a")
    other = _job(id="b", title="Designer", company="Other", url="https://example.com/b")
    with PostingStore(tmp_path / "jobradar.sqlite") as store:
        store.upsert([engineer, other], seen_on="2026-11-10")
        store.upsert(
            [
                _job(
                    id="c",
                    title="Backend Engineer",
                    company="Acme",
                    url="https://example.com/b",
                    salary_text="$1",
                )
            ],
            seen_on="2026-11-11",
        )
        document = store.export_document()

    assert len(document["postings"]) == 1
    assert document["postings"][0]["id"] == "c"
    assert document["postings"][0]["salary_text"] == "$1"
    assert document["postings"][0]["first_seen"] == "2026-11-10"
    assert document["postings"][0]["last_seen"] == "2026-11-11"
    assert document["days"] == [
        {"date": "2026-11-10", "new": 1, "seen_again": 0, "collected": 1},
        {"date": "2026-11-11", "new": 0, "seen_again": 1, "collected": 1},
    ]


def test_tracking_params_do_not_create_a_second_row(tmp_path: Path):
    with PostingStore(tmp_path / "jobradar.sqlite") as store:
        store.upsert([_job(title="Backend Engineer")], seen_on="2026-11-10")
        store.upsert(
            [
                _job(
                    id="remoteok:1-copy",
                    title="A different title for the same url",
                    company="Someone Else",
                    url="https://www.remoteok.com/jobs/1?ref=twitter",
                )
            ],
            seen_on="2026-11-11",
        )
        document = store.export_document()

    assert len(document["postings"]) == 1
    assert document["postings"][0]["first_seen"] == "2026-11-10"
    assert document["postings"][0]["last_seen"] == "2026-11-11"


def test_distinct_postings_both_stay(tmp_path: Path):
    jobs = [
        _job(id="a", title="Backend Engineer", url="https://example.com/a"),
        _job(
            id="b",
            title="Frontend Engineer",
            company="Other",
            url="https://example.com/b",
        ),
    ]
    _, stats = _persist(tmp_path, "2026-11-10", jobs)
    assert stats.total == 2
    assert stats.new == 2
    assert stats.seen_again == 0
    assert [item["id"] for item in _catalog(tmp_path)["postings"]] == ["a", "b"]


def test_upsert_rejects_a_bad_date(tmp_path: Path):
    with PostingStore(tmp_path / "jobradar.sqlite") as store:
        try:
            store.upsert([_job()], seen_on="11/10/2026")
        except ValueError as exc:
            assert "YYYY-MM-DD" in str(exc)
        else:
            raise AssertionError("expected ValueError")


def test_from_dict_rejects_tags_that_are_not_strings():
    payload = _job().to_dict()
    payload["tags"] = ["python", 3]
    try:
        JobPosting.from_dict(payload)
    except ValueError as exc:
        assert "tags" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_committed_snapshot_round_trips_and_a_second_sync_is_stable(tmp_path: Path):
    path = find_repo_root() / "data" / "normalized" / "2026-11-10.json"
    jobs = [JobPosting.from_dict(row) for row in load_normalized(path)]
    assert jobs
    _, stats = _persist(tmp_path, "2026-11-10", jobs)
    assert stats.total == len(jobs)
    assert stats.new == len(jobs)
    assert stats.seen_again == 0

    database = (tmp_path / "data" / "jobradar.sqlite").read_bytes()
    catalog = (tmp_path / "data" / "catalog" / "postings.json").read_bytes()
    _, again = _persist(tmp_path, "2026-11-10", jobs)
    assert again.total == stats.total
    assert (tmp_path / "data" / "jobradar.sqlite").read_bytes() == database
    assert (tmp_path / "data" / "catalog" / "postings.json").read_bytes() == catalog


def test_refreshing_a_date_drops_a_role_that_left_the_snapshot(tmp_path: Path):
    kept = _job(id="a", title="Backend Engineer", url="https://example.com/a")
    gone = _job(
        id="b",
        title="Frontend Engineer",
        company="Other",
        url="https://example.com/b",
    )
    _persist(tmp_path, "2026-11-10", [kept, gone])
    assert [item["id"] for item in _catalog(tmp_path)["postings"]] == ["a", "b"]

    _persist(tmp_path, "2026-11-10", [kept])

    document = _catalog(tmp_path)
    assert [item["id"] for item in document["postings"]] == ["a"]
    assert document["days"] == [
        {"date": "2026-11-10", "new": 1, "seen_again": 0, "collected": 1}
    ]


def test_opening_an_existing_catalog_does_not_rewrite_it(tmp_path: Path):
    path = tmp_path / "jobradar.sqlite"
    with PostingStore(path) as store:
        store.upsert([_job()], seen_on="2026-11-10")
    original = path.read_bytes()
    with PostingStore(path) as store:
        assert store.stats_for("2026-11-10").total == 1
    assert path.read_bytes() == original
