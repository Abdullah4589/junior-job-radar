from jobradar.summary import format_summary, summarize


def test_summary_counts_sources_remote_share_junior_share_and_top_tags():
    jobs = [
        {
            "source": "remoteok",
            "title": "Junior Python Developer",
            "remote": True,
            "tags": ["python", "django"],
        },
        {
            "source": "remoteok",
            "title": "Senior Go Engineer",
            "remote": True,
            "tags": ["go", "python"],
        },
        {
            "source": "arbeitnow",
            "title": "Backend Engineer",
            "remote": False,
            "tags": ["python"],
        },
        {
            "source": "remotive",
            "title": "Data Engineer Intern",
            "remote": True,
            "tags": ["sql"],
        },
    ]
    summary = summarize(jobs, date="2026-11-10", path="data/normalized/2026-11-10.json")

    assert summary.total == 4
    assert summary.by_source == [("remoteok", 2), ("arbeitnow", 1), ("remotive", 1)]
    assert summary.remote_count == 3
    assert summary.junior_count == 2
    assert summary.top_tags[0] == ("python", 3)
    text = format_summary(summary)
    assert "Remote share: 3/4 (75.0%)" in text
    assert "Junior / entry-level: 2/4 (50.0%)" in text
    assert "1. python (3)" in text
