"""Title and tag heuristics that decide whether a posting is in scope.

Skill, seniority, and workplace extraction live in `jobradar.extract`.
`looks_junior` delegates there so the summary and this module share one
definition. Remote OK still attaches unrelated tags, so a tag is not
evidence of a software role unless the title agrees with it.
"""

from __future__ import annotations

import re

# Longer phrases first so "full-stack" is recorded, not a shorter fragment.
_TITLE_SKILLS: tuple[str, ...] = (
    "machine learning",
    "react native",
    "full-stack",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "next.js",
    "node.js",
    "postgresql",
    "postgres",
    "kubernetes",
    "typescript",
    "javascript",
    "tensorflow",
    "terraform",
    "graphql",
    "pytorch",
    "snowflake",
    "airflow",
    "fastapi",
    "django",
    "angular",
    "flutter",
    "android",
    "golang",
    "kotlin",
    "docker",
    "svelte",
    "spring",
    "python",
    "devops",
    "rails",
    "react",
    "flask",
    "redis",
    "kafka",
    "spark",
    "mysql",
    "linux",
    "swift",
    "scala",
    "rust",
    "ruby",
    "java",
    "vue",
    "php",
    "aws",
    "gcp",
    "azure",
    "sql",
    "ios",
    "sre",
    "git",
    "c++",
    "c#",
    ".net",
    "go",
)

def _skill_pattern(skill: str) -> re.Pattern[str]:
    # ".NET" usually appears as "ASP.NET", so the dot cannot require a non-word lookbehind.
    if skill.startswith("."):
        return re.compile(rf"{re.escape(skill)}(?![a-z0-9])")
    return re.compile(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])")


_SKILL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (skill, _skill_pattern(skill)) for skill in _TITLE_SKILLS
)

_SOFTWARE_CATEGORIES = {
    "software development",
    "software engineering",
    "devops",
    "devops / sysadmin",
    "quality assurance",
    "qa",
    "data science",
    "data engineering",
}

_SOFTWARE_TAGS = {"software development", "software engineering"}

_DENY = re.compile(
    r"\b("
    r"nurse|accountant|recruiter|account executive|customer service|"
    r"copywriter|content reviewer|office assistant|video annotation|"
    r"sales engineer|sales manager|vertrieb|success manager|"
    r"implementation manager|mechanical"
    r")\b",
    re.IGNORECASE,
)

_ROLE = re.compile(
    r"\b("
    r"developer|desarrollador|développeur|developpeur|"
    r"entwickler|softwareentwickler|programmierer|"
    r"programmer|software development|full[- ]?stack|front[- ]?end|back[- ]?end|"
    r"devops|devsecops|sre|sdet|mlops|"
    r"machine learning|data scientist|data engineer|analytics engineer|"
    r"security engineer|cloud engineer|platform engineer|"
    r"site reliability|quality assurance|qa engineer|qa|"
    r"ios|android|mobile engineer|web developer|"
    r"forward deployed|test engineer|tester"
    r")\b",
    re.IGNORECASE,
)

_ENGINEER = re.compile(r"\bengineers?\b|\bengineering\b", re.IGNORECASE)

_TECH_WORDS = (
    "javascript",
    "typescript",
    "infrastructure",
    "kubernetes",
    "postgresql",
    "tensorflow",
    "blockchain",
    "full-stack",
    "fullstack",
    "full stack",
    "front-end",
    "front end",
    "frontend",
    "back-end",
    "back end",
    "backend",
    "firmware",
    "embedded",
    "security",
    "platform",
    "software",
    "android",
    "devops",
    "golang",
    "kotlin",
    "django",
    "python",
    "react",
    "rails",
    "linux",
    "swift",
    "scala",
    "cloud",
    "rust",
    "ruby",
    "java",
    "node",
    "vue",
    "php",
    "ios",
    "sre",
    "api",
    "llm",
    "nlp",
    "web",
    "mobile",
    "data",
    "infra",
    "qa",
    "ml",
    "ai",
    "go",
)

_TECH = re.compile(
    r"\b(?:" + "|".join(re.escape(word) for word in _TECH_WORDS) + r")\b",
    re.IGNORECASE,
)

# Employment-type and board-navigation labels. They are not skills.
_TAG_NOISE = {
    "full time",
    "full-time",
    "fulltime",
    "part time",
    "part-time",
    "contract",
    "permanent",
    "remote",
    "on-site",
    "onsite",
    "hybrid",
    "international rss",
    "fulltime permanent",
    "experienced",
    "mid",
    "senior",
    "manager",
    "directors",
    "chief executives",
    # Role words, not skills. "software development" is a different tag and stays.
    "engineer",
    "engineering",
    "developer",
    "developers",
    "software",
    "dev",
    "technical",
    "it",
    "tech",
    "development",
}

# Surface forms that should count as one skill across boards.
_TAG_ALIASES = {
    "front end": "frontend",
    "front-end": "frontend",
    "back end": "backend",
    "back-end": "backend",
    "full stack": "full-stack",
    "fullstack": "full-stack",
    "golang": "go",
    "react.js": "react",
    "reactjs": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "k8s": "kubernetes",
}

def is_software_role(
    title: str,
    *,
    category: str = "",
    tags: list[str] | None = None,
) -> bool:
    """Return whether this posting is in scope for a software job radar."""

    if _DENY.search(title):
        return False
    if category.strip().lower() in _SOFTWARE_CATEGORIES:
        return True
    tagset = {tag.lower() for tag in (tags or [])}
    if tagset & _SOFTWARE_TAGS:
        return True
    if _ROLE.search(title):
        return True
    if _ENGINEER.search(title) and _TECH.search(title):
        return True
    return False


def looks_junior(title: str, tags: list[str] | None = None) -> bool:
    """True when the extractor calls the role intern or junior.

    Description text is ignored here. A senior title stays senior even if
    the description mentions mentoring junior engineers.
    """

    from jobradar.extract import extract_posting

    found = extract_posting(title=title, tags=list(tags or []), refine=False)
    return found.junior_friendly


def skills_in_title(title: str) -> list[str]:
    """Skills literally named in the title, in vocabulary order."""

    lowered = title.lower()
    folded = re.sub(r"[\s_]+", "-", lowered)
    found: list[str] = []
    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(lowered) or pattern.search(folded):
            found.append(skill)
    return found


def tag_supported_by_title(tag: str, title: str) -> bool:
    """True when a source tag is echoed by the title, not merely attached."""

    tag_n = " ".join(tag.lower().split())
    if re.search(rf"(?<![a-z0-9]){re.escape(tag_n)}(?![a-z0-9])", title.lower()):
        return True
    # "full stack" should match "full-stack", but "exec" must not match "execution".
    tag_parts = re.findall(r"[a-z0-9+#]+", tag_n)
    title_parts = re.findall(r"[a-z0-9+#]+", title.lower())
    if len(tag_parts) < 2:
        return False
    width = len(tag_parts)
    return any(title_parts[index : index + width] == tag_parts for index in range(len(title_parts) - width + 1))


def clean_tags(tags: list[object], *, source: str, title: str) -> list[str]:
    """Normalize tags and add skills that appear in the title.

    Remote OK's tag list is noisy, so those tags are kept only when the
    title supports them. Raw tags are still stored in the raw snapshot.
    """

    cleaned: list[str] = []
    seen: set[str] = set()

    def add(tag: str) -> None:
        tag = _TAG_ALIASES.get(tag, tag)
        # Parentheses are team labels ("engineering (ads)"), not skills.
        if not tag or tag in seen or tag in _TAG_NOISE or "(" in tag or ")" in tag:
            return
        seen.add(tag)
        cleaned.append(tag)

    for raw in tags:
        if not isinstance(raw, str):
            continue
        tag = " ".join(raw.strip().lower().split())
        if source == "remoteok" and not tag_supported_by_title(tag, title):
            continue
        add(tag)
    for skill in skills_in_title(title):
        add(skill)
    return cleaned


def junior_signals_from_job_types(job_types: list[object]) -> list[str]:
    """Map board seniority labels onto tags the junior check understands."""

    signals: list[str] = []
    seen: set[str] = set()
    for raw in job_types:
        if not isinstance(raw, str):
            continue
        text = raw.lower()
        additions: list[str] = []
        if "intern" in text:
            additions.append("internship")
        if "entry" in text:
            additions.append("entry-level")
        if "student" in text:
            additions.append("working student")
        for tag in additions:
            if tag not in seen:
                seen.add(tag)
                signals.append(tag)
    return signals
