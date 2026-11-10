from jobradar.dedupe import dedupe_jobs
from jobradar.models import JobPosting


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
        "fetched_at": "2026-11-10T00:00:00Z",
    }
    data.update(overrides)
    return JobPosting(**data)  # type: ignore[arg-type]


def test_same_role_on_two_boards_keeps_the_richer_record():
    first = _job()
    second = _job(
        id="remotive:2",
        source="remotive",
        company="Acme Inc",
        salary_text="$90,000",
        tags=["python", "django"],
        url="https://remotive.com/remote-jobs/backend-engineer",
    )
    same_url = _job(
        id="remoteok:1-copy",
        url="https://www.remoteok.com/jobs/1",
        title="Different title that shares the url",
    )

    kept = dedupe_jobs([first, second, same_url])

    assert [job.id for job in kept] == ["remotive:2"]
    assert kept[0].salary_text == "$90,000"


def test_distinct_roles_both_stay():
    jobs = dedupe_jobs(
        [
            _job(id="a", title="Backend Engineer", url="https://example.com/a"),
            _job(
                id="b",
                title="Frontend Engineer",
                company="Other",
                url="https://example.com/b",
            ),
        ]
    )
    assert [job.id for job in jobs] == ["a", "b"]
