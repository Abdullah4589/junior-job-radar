"""Normalizer tests. These use fixtures, not the live job boards."""

from jobradar.models import JobPosting
from jobradar.normalize import (
    format_salary_range,
    normalize_arbeitnow,
    normalize_remoteok,
    normalize_remotive,
    to_utc_iso,
)

FETCHED_AT = "2026-11-10T08:00:00Z"


def test_remotive_record_maps_onto_the_shared_schema():
    posting = normalize_remotive(
        {
            "id": 2091045,
            "title": "  Full-Stack Developer ",
            "company_name": "Unio Digital",
            "candidate_required_location": "Worldwide",
            "category": "Software Development",
            "tags": ["React", "react", "Node.js"],
            "salary": " $80,000 - $100,000 ",
            "publication_date": "2026-11-07T01:10:55",
            "url": "https://remotive.com/remote-jobs/software-dev/full-stack-developer-2091045",
            "description": "<p>ignore me</p>",
        },
        fetched_at=FETCHED_AT,
    )

    assert isinstance(posting, JobPosting)
    payload = posting.to_dict()
    assert list(payload) == [
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
    assert payload["id"] == "remotive:2091045"
    assert payload["source"] == "remotive"
    assert payload["title"] == "Full-Stack Developer"
    assert payload["company"] == "Unio Digital"
    assert payload["location"] == "Worldwide"
    assert payload["remote"] is True
    assert payload["tags"] == ["react", "node.js", "full-stack"]
    assert payload["salary_text"] == "$80,000 - $100,000"
    assert payload["posted_at"] == "2026-11-07T01:10:55Z"
    assert payload["fetched_at"] == FETCHED_AT


def test_remotive_blank_salary_and_missing_url_are_dropped():
    assert (
        normalize_remotive(
            {
                "id": 1,
                "title": "Software Engineer",
                "company_name": "Acme",
                "url": "",
            },
            fetched_at=FETCHED_AT,
        )
        is None
    )
    posting = normalize_remotive(
        {
            "id": 2,
            "title": "Software Engineer",
            "company_name": "",
            "candidate_required_location": "",
            "salary": "N/A",
            "publication_date": "not-a-date",
            "url": "https://remotive.com/remote-jobs/example",
        },
        fetched_at=FETCHED_AT,
    )
    assert posting is not None
    assert posting.company == "Unknown"
    assert posting.location == "Remote"
    assert posting.salary_text is None
    assert posting.posted_at is None


def test_remoteok_salary_range_and_zero_means_unspecified():
    posting = normalize_remoteok(
        {
            "id": "1137706",
            "position": "Senior Vue Developer",
            "company": "Adaptive Innovations",
            "location": "",
            "tags": ["exec", "dev", "vue", "golang", "customer support"],
            "salary_min": 50000,
            "salary_max": 180000,
            "date": "2026-11-08T16:00:15+00:00",
            "url": "https://remoteOK.com/remote-jobs/remote-senior-vue-developer",
            "description": "long html",
        },
        fetched_at=FETCHED_AT,
    )
    assert posting is not None
    assert posting.id == "remoteok:1137706"
    assert posting.remote is True
    assert posting.location == "Remote"
    assert posting.salary_text == "$50,000–$180,000"
    assert posting.posted_at == "2026-11-08T16:00:15Z"
    # "golang" is a Remote OK tag the title does not support, so it is dropped.
    assert "golang" not in posting.tags
    assert "exec" not in posting.tags
    assert "vue" in posting.tags

    unpaid = normalize_remoteok(
        {
            "id": "9",
            "position": "Backend Engineer",
            "company": "Acme",
            "salary_min": 0,
            "salary_max": 0,
            "url": "https://remoteok.com/jobs/9",
        },
        fetched_at=FETCHED_AT,
    )
    assert unpaid is not None
    assert unpaid.salary_text is None
    assert "backend" in unpaid.tags


def test_remoteok_legal_banner_is_not_a_job():
    assert (
        normalize_remoteok(
            {"last_updated": 1, "legal": "Please link back to Remote OK."},
            fetched_at=FETCHED_AT,
        )
        is None
    )


def test_arbeitnow_unix_timestamp_remote_flag_and_internship():
    posting = normalize_arbeitnow(
        {
            "slug": "working-student-python-berlin-1",
            "company_name": "OpenTable GmbH",
            "title": "Working Student Python Engineer (m/w/d)",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/companies/opentable/working-student-python-berlin-1",
            "tags": ["Software Development", "International RSS"],
            "job_types": ["Student college", "internship"],
            "location": "Berlin",
            "created_at": 1794293724,
            "description": "<p>skip</p>",
        },
        fetched_at=FETCHED_AT,
    )
    assert posting is not None
    assert posting.id == "arbeitnow:working-student-python-berlin-1"
    assert posting.company == "OpenTable GmbH"
    assert posting.remote is False
    assert posting.location == "Berlin"
    assert posting.posted_at == "2026-11-10T06:55:24Z"
    assert "software development" in posting.tags
    assert "international rss" not in posting.tags
    assert "python" in posting.tags
    assert "internship" in posting.tags
    assert "working student" in posting.tags


def test_arbeitnow_remote_location_text_and_missing_slug():
    posting = normalize_arbeitnow(
        {
            "slug": "security-engineer-remote",
            "company_name": "Example",
            "title": "Security Engineer",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/security-engineer-remote",
            "tags": [],
            "job_types": ["Entry"],
            "location": "Remote - Germany",
            "created_at": "1794293724000",
        },
        fetched_at=FETCHED_AT,
    )
    assert posting is not None
    assert posting.remote is True
    assert posting.posted_at == "2026-11-10T06:55:24Z"
    assert "entry-level" in posting.tags
    assert (
        normalize_arbeitnow(
            {"title": "Software Engineer", "url": "https://example.com/job", "slug": ""},
            fetched_at=FETCHED_AT,
        )
        is None
    )


def test_remoteok_repairs_mojibake_punctuation():
    posting = normalize_remoteok(
        {
            "id": "1",
            "position": "ML Inference Engineer â\x80\x93 Terminal-Bench",
            "company": "Sothebyâ\x80\x99s",
            "url": "https://remoteok.com/jobs/1",
        },
        fetched_at=FETCHED_AT,
    )
    assert posting is not None
    assert posting.title == "ML Inference Engineer – Terminal-Bench"
    assert posting.company == "Sotheby’s"
    untouched = normalize_remoteok(
        {
            "id": "2",
            "position": "Backend Engineer",
            "company": "Château Labs",
            "url": "https://remoteok.com/jobs/2",
        },
        fetched_at=FETCHED_AT,
    )
    assert untouched is not None
    assert untouched.company == "Château Labs"


def test_salary_range_edges_and_timestamps():
    assert format_salary_range(0, 0) is None
    assert format_salary_range(60000, 0) == "$60,000+"
    assert format_salary_range(0, 130) == "up to $130"
    assert format_salary_range(180000, 50000) == "$50,000–$180,000"
    assert to_utc_iso(1700000000) == "2023-11-14T22:13:20Z"
    assert to_utc_iso(0) is None
    assert to_utc_iso(None) is None
