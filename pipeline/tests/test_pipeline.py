import json
from pathlib import Path

import urllib.error

from jobradar.http_client import get_json
from jobradar.models import JobPosting
from jobradar.pipeline import build_normalized_document, build_raw_document, collect
from jobradar.snapshot import load_normalized, write_snapshots
from jobradar.sources.base import SourceBatch


class _Response:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class _FakeSource:
    def __init__(self, name: str, jobs: list[JobPosting] | None = None, error: Exception | None = None):
        self.name = name
        self.endpoint = f"https://example.test/{name}"
        self._jobs = jobs or []
        self._error = error

    def fetch(self, *, fetched_at: str) -> SourceBatch:
        if self._error:
            raise self._error
        return SourceBatch(
            source=self.name,
            endpoint=self.endpoint,
            records=[{"id": job.id, "title": job.title} for job in self._jobs],
            jobs=self._jobs,
        )


def _job(source: str, native: str, title: str) -> JobPosting:
    return JobPosting(
        id=f"{source}:{native}",
        source=source,
        title=title,
        company="Acme",
        location="Remote",
        remote=True,
        tags=["python"],
        salary_text=None,
        posted_at="2026-11-09T00:00:00Z",
        url=f"https://example.test/{source}/{native}",
        fetched_at="2026-11-10T08:00:00Z",
    )


def test_collect_continues_when_one_source_fails():
    ok = _FakeSource("remotive", [_job("remotive", "1", "Backend Engineer")])
    down = _FakeSource("remoteok", error=TimeoutError("timed out"))
    collection = collect([ok, down], fetched_at="2026-11-10T08:00:00Z")

    assert collection.any_ok is True
    assert [report.source for report in collection.sources] == ["remotive", "remoteok"]
    assert collection.sources[1].ok is False
    assert "TimeoutError" in (collection.sources[1].error or "")
    assert [job.id for job in collection.jobs] == ["remotive:1"]


def test_snapshots_round_trip(tmp_path: Path):
    job = _job("arbeitnow", "slug", "Python Developer")
    collection = collect(
        [_FakeSource("arbeitnow", [job])],
        fetched_at="2026-11-10T08:00:00Z",
    )
    paths = write_snapshots(
        tmp_path,
        date="2026-11-10",
        raw_document=build_raw_document(collection),
        normalized_document=build_normalized_document(collection, date="2026-11-10"),
        jobs=collection.jobs,
    )
    raw = json.loads(paths[0].read_text(encoding="utf-8"))
    assert raw["sources"][0]["fetched_count"] == 1
    loaded = load_normalized(paths[1])
    assert loaded[0]["title"] == "Python Developer"
    assert "python" in paths[2].read_text(encoding="utf-8")
    document = json.loads(paths[1].read_text(encoding="utf-8"))
    assert document["attribution"][0]["name"] == "Arbeitnow"


def test_get_json_retries_timeouts_then_succeeds():
    calls = {"n": 0, "slept": []}

    def urlopen(request, timeout):  # noqa: ANN001
        calls["n"] += 1
        assert request.get_header("User-agent").startswith("JuniorJobRadar/")
        assert timeout == 20.0
        if calls["n"] < 3:
            raise urllib.error.URLError("timed out")
        return _Response(b'{"ok": true}')

    payload = get_json(
        "https://example.test/jobs",
        urlopen=urlopen,
        sleep=calls["slept"].append,
    )
    assert payload == {"ok": True}
    assert calls["n"] == 3
    assert calls["slept"] == [1.0, 2.0]


def test_get_json_does_not_retry_a_404():
    calls = {"n": 0}

    def urlopen(request, timeout):  # noqa: ANN001
        calls["n"] += 1
        raise urllib.error.HTTPError(
            "https://example.test/missing",
            404,
            "Not Found",
            hdrs=None,
            fp=None,
        )

    try:
        get_json("https://example.test/missing", urlopen=urlopen, sleep=lambda _seconds: None)
    except Exception as exc:
        assert type(exc).__name__ == "SourceFetchError"
    else:
        raise AssertionError("expected SourceFetchError")
    assert calls["n"] == 1
