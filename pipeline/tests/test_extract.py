"""Extractor fixtures, storage backfill, and the optional LLM fallback."""

import json
import urllib.error
from pathlib import Path

from jobradar.enrich import enrich_repository
from jobradar.extract import Extraction, extract_posting, skill_alias_map
from jobradar.llm import maybe_refine
from jobradar.models import JobPosting
from jobradar.normalize import normalize_remoteok, normalize_remotive
from jobradar.pipeline import collect
from jobradar.sources.base import SourceBatch
from jobradar.trends import build_trends

FETCHED_AT = "2026-11-10T08:00:00Z"
FIXTURES = Path(__file__).parent / "fixtures" / "extraction.json"


def test_taxonomy_file_maps_js_and_k8s():
    aliases = skill_alias_map()
    assert aliases["js"] == "JavaScript"
    assert aliases["k8s"] == "Kubernetes"
    assert aliases["golang"] == "Go"
    assert aliases["go"] == "Go"
    assert aliases["c"] == "C"
    assert aliases["r"] == "R"


def test_saved_fixtures_cover_aliases_boundaries_and_level_conflicts():
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert len(cases) >= 20
    for case in cases:
        result = extract_posting(
            title=case["title"],
            description=case.get("description", ""),
            location=case.get("location", ""),
            tags=case.get("tags", []),
            remote=bool(case.get("remote", False)),
            refine=False,
        )
        expect = case["expect"]
        assert result.skills == expect["skills"], case["name"]
        assert result.seniority == expect["seniority"], case["name"]
        assert result.workplace == expect["workplace"], case["name"]
        assert result.junior_friendly is expect["junior_friendly"], case["name"]
        assert result.regions == expect["regions"], case["name"]


def test_a_long_role_catalog_does_not_become_this_jobs_skills():
    posting = normalize_remoteok(
        {
            "id": "1137688",
            "position": "Senior Vue Developer",
            "company": "Lemon.io",
            "location": "",
            "tags": ["exec", "dev", "vue", "golang", "customer support"],
            "salary_min": 0,
            "salary_max": 0,
            "url": "https://remoteok.com/remote-jobs/remote-senior-vue-developer",
            "description": (
                "Other open roles: React, Golang, Kubernetes, Python, Java, Ruby, "
                "PHP, Swift, Flutter, Angular, Rust, Scala, C++, and Machine Learning. "
                "Lemon.io helps companies in the US and Europe."
            ),
        },
        fetched_at=FETCHED_AT,
    )
    assert posting is not None
    assert posting.salary_text is None
    assert posting.skills == ["Vue"]
    assert "Go" not in posting.skills
    assert posting.seniority == "senior"
    assert posting.workplace == "remote"
    assert posting.regions == []

    specific = normalize_remoteok(
        {
            "id": "2",
            "position": "Senior Vue Developer",
            "company": "Acme",
            "url": "https://remoteok.com/remote-jobs/2",
            "description": "This role runs the Vue app on Kubernetes.",
        },
        fetched_at=FETCHED_AT,
    )
    assert specific is not None
    assert specific.skills == ["Vue", "Kubernetes"]


def test_a_long_tag_list_is_not_a_skill_list_and_a_short_one_is():
    catalog = [
        "python",
        "java",
        "go",
        "rust",
        "ruby",
        "php",
        "swift",
        "kotlin",
        "scala",
        "react",
        "vue",
        "angular",
        "django",
    ]
    broad = extract_posting(title="Backend Engineer", tags=catalog, refine=False)
    assert broad.skills == ["Backend"]
    focused = extract_posting(title="Backend Engineer", tags=["python", "django"], refine=False)
    assert focused.skills == ["Backend", "Python", "Django"]


def test_extraction_is_stable_for_the_same_text():
    kwargs = {
        "title": "Senior Go Engineer",
        "description": "We will go to the office. k8s and Python.",
        "location": "Munich",
        "tags": ["golang"],
        "remote": False,
        "refine": False,
    }
    assert extract_posting(**kwargs) == extract_posting(**kwargs)


def test_a_failed_source_keeps_extracted_jobs_and_an_empty_salary():
    posting = normalize_remotive(
        {
            "id": 42,
            "title": "Junior JS Developer",
            "company_name": "Acme",
            "candidate_required_location": "Remote - Germany",
            "salary": "",
            "url": "https://remotive.com/remote-jobs/example-42",
            "description": "<p>k8s and Node.js. We will go to market. Join us.</p>",
            "tags": ["js"],
        },
        fetched_at=FETCHED_AT,
    )
    assert posting is not None
    assert posting.salary_text is None
    assert posting.skills == ["JavaScript", "Kubernetes", "Node.js"]
    assert "Go" not in posting.skills
    assert posting.seniority == "junior"
    assert posting.junior_friendly is True
    assert posting.workplace == "remote"
    assert posting.regions == ["Germany"]
    assert "United States" not in posting.regions

    class _Ok:
        name = "remotive"
        endpoint = "https://example.test/remotive"

        def fetch(self, *, fetched_at: str) -> SourceBatch:
            return SourceBatch(
                source=self.name,
                endpoint=self.endpoint,
                records=[{"id": posting.id, "title": posting.title}],
                jobs=[posting],
            )

    class _Down:
        name = "remoteok"
        endpoint = "https://example.test/remoteok"

        def fetch(self, *, fetched_at: str) -> SourceBatch:
            raise TimeoutError("timed out")

    collection = collect([_Ok(), _Down()], fetched_at=FETCHED_AT)
    assert collection.any_ok is True
    assert collection.sources[1].ok is False
    assert "TimeoutError" in (collection.sources[1].error or "")
    assert collection.jobs[0].salary_text is None
    assert collection.jobs[0].skills == ["JavaScript", "Kubernetes", "Node.js"]


def test_enrich_fills_missing_fields_keeps_stored_skills_and_is_idempotent(tmp_path: Path):
    kept = JobPosting(
        id="remoteok:kept",
        source="remoteok",
        title="Software Engineer",
        company="Acme",
        location="Remote",
        remote=True,
        tags=[],
        salary_text=None,
        posted_at="2026-11-10T00:00:00Z",
        url="https://remoteok.com/jobs/kept",
        fetched_at=FETCHED_AT,
        seniority="junior",
        skills=["Kubernetes"],
        workplace="remote",
        junior_friendly=True,
        regions=["Canada"],
    )
    old = kept.to_dict()
    old["id"] = "remoteok:old"
    old["title"] = "Junior Python Developer"
    old["url"] = "https://remoteok.com/jobs/old"
    for key in ("seniority", "skills", "workplace", "junior_friendly", "regions"):
        del old[key]
    directory = tmp_path / "data" / "normalized"
    directory.mkdir(parents=True)
    document = {
        "date": "2026-11-10",
        "fetched_at": FETCHED_AT,
        "count": 2,
        "attribution": [],
        "jobs": [kept.to_dict(), old],
    }
    path = directory / "2026-11-10.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    first = enrich_repository(tmp_path)
    assert "snapshots rewritten: 1" in first
    loaded = json.loads(path.read_text(encoding="utf-8"))["jobs"]
    assert loaded[0]["skills"] == ["Kubernetes"]
    assert loaded[0]["regions"] == ["Canada"]
    assert loaded[1]["seniority"] == "junior"
    assert loaded[1]["skills"] == ["Python"]
    assert loaded[1]["junior_friendly"] is True
    assert loaded[1]["workplace"] == "remote"
    assert "data/catalog/trends.json" in first

    snapshot = path.read_bytes()
    database = (tmp_path / "data" / "jobradar.sqlite").read_bytes()
    catalog = (tmp_path / "data" / "catalog" / "postings.json").read_bytes()
    trends = (tmp_path / "data" / "catalog" / "trends.json").read_bytes()
    second = enrich_repository(tmp_path)
    assert "snapshots already extracted" in second
    assert path.read_bytes() == snapshot
    assert (tmp_path / "data" / "jobradar.sqlite").read_bytes() == database
    assert (tmp_path / "data" / "catalog" / "postings.json").read_bytes() == catalog
    assert (tmp_path / "data" / "catalog" / "trends.json").read_bytes() == trends

    aggregate = json.loads(trends)
    assert aggregate["postings"] == 2
    assert aggregate["junior_friendly"] == 2
    assert aggregate["workplace"]["remote"] == 2
    assert {"skill": "Kubernetes", "count": 1} in aggregate["top_skills"]
    assert {"skill": "Python", "count": 1} in aggregate["top_skills"]
    assert aggregate["seniority"]["junior"] == 2


def test_trends_count_skills_seniority_and_workplace():
    trends = build_trends(
        [
            {
                "skills": ["Python", "Django"],
                "seniority": "junior",
                "workplace": "remote",
                "junior_friendly": True,
                "regions": ["Germany"],
            },
            {
                "skills": ["Python"],
                "seniority": "senior",
                "workplace": "onsite",
                "junior_friendly": False,
                "regions": ["Germany", "France"],
            },
            {
                "skills": [],
                "seniority": "nope",
                "workplace": "",
                "junior_friendly": False,
                "regions": [],
            },
        ]
    )
    assert trends["postings"] == 3
    assert trends["junior_friendly"] == 1
    assert trends["top_skills"][0] == {"skill": "Python", "count": 2}
    assert trends["seniority"]["junior"] == 1
    assert trends["seniority"]["senior"] == 1
    assert trends["seniority"]["unknown"] == 1
    assert trends["workplace"]["remote"] == 1
    assert trends["workplace"]["onsite"] == 1
    assert trends["workplace"]["unknown"] == 1
    assert trends["regions"][0] == {"region": "Germany", "count": 2}


def test_llm_is_not_called_without_a_url(monkeypatch):
    monkeypatch.delenv("JOBRADAR_LLM_URL", raising=False)
    monkeypatch.delenv("JOBRADAR_LLM_API_KEY", raising=False)

    def transport(request, timeout):  # noqa: ANN001
        raise AssertionError("the LLM should not be called")

    keyword = _keyword()
    assert maybe_refine(keyword, context="Senior Engineer", transport=transport) == keyword


def test_llm_failure_keeps_the_keyword_result(monkeypatch):
    monkeypatch.setenv("JOBRADAR_LLM_URL", "https://llm.example.test/v1/chat/completions")
    monkeypatch.setenv("JOBRADAR_LLM_API_KEY", "test-key")
    seen = {}

    def transport(request, timeout):  # noqa: ANN001
        seen["authorization"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        raise urllib.error.URLError("down")

    keyword = _keyword()
    assert maybe_refine(keyword, context="Senior Engineer", transport=transport) == keyword
    assert seen["authorization"] == "Bearer test-key"
    assert seen["timeout"] == 10


def test_llm_keeps_a_valid_result_and_drops_names_outside_the_taxonomy(monkeypatch):
    monkeypatch.setenv("JOBRADAR_LLM_URL", "https://llm.example.test/v1/chat/completions")
    monkeypatch.delenv("JOBRADAR_LLM_API_KEY", raising=False)
    body = {
        "choices": [
            {
                "message": {
                    "content": (
                        "```json\n"
                        + json.dumps(
                            {
                                "seniority": "junior",
                                "skills": ["Python", "Not A Skill"],
                                "workplace": "remote",
                                "regions": ["Germany", "Atlantis"],
                            }
                        )
                        + "\n```"
                    )
                }
            }
        ]
    }

    def transport(request, timeout):  # noqa: ANN001
        assert request.get_header("Authorization") is None
        return _Body(json.dumps(body).encode("utf-8"))

    result = maybe_refine(_keyword(), context="Junior Python Developer", transport=transport)
    assert result == Extraction(
        seniority="junior",
        skills=["Python"],
        workplace="remote",
        junior_friendly=True,
        regions=["Germany"],
    )


def test_llm_garbage_falls_back_to_keywords(monkeypatch):
    monkeypatch.setenv("JOBRADAR_LLM_URL", "https://llm.example.test/v1/chat/completions")

    def transport(request, timeout):  # noqa: ANN001
        return _Body(b'{"choices":[{"message":{"content":"nope"}}]}')

    keyword = _keyword()
    assert maybe_refine(keyword, context="Senior Engineer", transport=transport) == keyword


class _Body:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


def _keyword() -> Extraction:
    return Extraction(
        seniority="senior",
        skills=["Go"],
        workplace="onsite",
        junior_friendly=False,
        regions=["France"],
    )
