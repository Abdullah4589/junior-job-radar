"""Map source records onto the shared JobPosting schema."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from jobradar.classify import clean_tags, junior_signals_from_job_types
from jobradar.extract import apply_extraction
from jobradar.models import JobPosting

_EMPTY_SALARY = {"", "0", "n/a", "na", "none", "not specified", "unspecified"}
_GENDER_MARKER = re.compile(r"\([mfwdx/\s]+\)", re.IGNORECASE)
_LEGAL_SUFFIX = re.compile(
    r"\b(inc|incorporated|llc|ltd|limited|gmbh|corp|corporation|plc)\b",
    re.IGNORECASE,
)


def normalize_remotive(record: dict[str, Any], *, fetched_at: str) -> JobPosting | None:
    title = _clean_text(record.get("title"))
    url = _clean_url(record.get("url"))
    if not title or not url or record.get("id") is None:
        return None
    location = _clean_text(record.get("candidate_required_location")) or "Remote"
    return _finish(
        JobPosting(
            id=f"remotive:{record.get('id')}",
            source="remotive",
            title=title,
            company=_clean_text(record.get("company_name")) or "Unknown",
            location=location,
            remote=True,
            tags=clean_tags(_as_list(record.get("tags")), source="remotive", title=title),
            salary_text=_clean_salary_text(record.get("salary")),
            posted_at=to_utc_iso(record.get("publication_date")),
            url=url,
            fetched_at=fetched_at,
        ),
        record,
    )


def normalize_remoteok(record: dict[str, Any], *, fetched_at: str) -> JobPosting | None:
    title = _clean_text(record.get("position"))
    url = _clean_url(record.get("url")) or _clean_url(record.get("apply_url"))
    if not title or not url or record.get("id") is None:
        return None
    location = _clean_text(record.get("location")) or "Remote"
    return _finish(
        JobPosting(
            id=f"remoteok:{record.get('id')}",
            source="remoteok",
            title=title,
            company=_clean_text(record.get("company")) or "Unknown",
            location=location,
            remote=True,
            tags=clean_tags(_as_list(record.get("tags")), source="remoteok", title=title),
            salary_text=format_salary_range(record.get("salary_min"), record.get("salary_max")),
            posted_at=to_utc_iso(record.get("date") or record.get("epoch")),
            url=url,
            fetched_at=fetched_at,
        ),
        record,
    )


def normalize_arbeitnow(record: dict[str, Any], *, fetched_at: str) -> JobPosting | None:
    title = _clean_text(record.get("title"))
    url = _clean_url(record.get("url"))
    slug = _clean_text(record.get("slug"))
    if not title or not url or not slug:
        return None
    location = _clean_text(record.get("location")) or "Unspecified"
    remote_flag = bool(record.get("remote")) or "remote" in location.lower()
    if remote_flag and location == "Unspecified":
        location = "Remote"
    tags = clean_tags(_as_list(record.get("tags")), source="arbeitnow", title=title)
    for signal in junior_signals_from_job_types(_as_list(record.get("job_types"))):
        if signal not in tags:
            tags.append(signal)
    return _finish(
        JobPosting(
            id=f"arbeitnow:{slug}",
            source="arbeitnow",
            title=title,
            company=_clean_text(record.get("company_name")) or "Unknown",
            location=location,
            remote=remote_flag,
            tags=tags,
            salary_text=None,
            posted_at=to_utc_iso(record.get("created_at")),
            url=url,
            fetched_at=fetched_at,
        ),
        record,
        extra_labels=[item for item in _as_list(record.get("job_types")) if isinstance(item, str)],
    )


def _finish(
    posting: JobPosting,
    record: dict[str, Any],
    *,
    extra_labels: list[str] | None = None,
) -> JobPosting:
    description = record.get("description") if isinstance(record.get("description"), str) else ""
    labels = [item for item in _as_list(record.get("tags")) if isinstance(item, str)]
    if extra_labels:
        labels.extend(extra_labels)
    return apply_extraction(posting, description=description, labels=labels)


def format_salary_range(minimum: object, maximum: object) -> str | None:
    """Format Remote OK's numeric salary fields. Zero means 'not stated'."""

    low = _positive_int(minimum)
    high = _positive_int(maximum)
    if low and high and low > high:
        low, high = high, low
    if low and high and low != high:
        return f"${low:,}–${high:,}"
    if low and high:
        return f"${low:,}"
    if low:
        return f"${low:,}+"
    if high:
        return f"up to ${high:,}"
    return None


def to_utc_iso(value: object) -> str | None:
    """Normalize a date string or unix timestamp to UTC `YYYY-MM-DDTHH:MM:SSZ`."""

    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        stamp = int(value)
        if stamp > 10_000_000_000:
            stamp //= 1000
        if stamp < 946_684_800:
            return None
        moment = datetime.fromtimestamp(stamp, tz=timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_url(url: str) -> str:
    """Drop tracking params and trivial host/path differences before dedupe."""

    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url.strip())
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=False)
        if not key.lower().startswith("utm_") and key.lower() not in {"ref", "source"}
    ]
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))


def identity_key(company: str, title: str) -> str:
    """Company + title key used when two boards republish the same role."""

    return f"{_fold(company)}|{_fold(title)}"


def _fold(value: str) -> str:
    text = _GENDER_MARKER.sub(" ", value.lower())
    text = _LEGAL_SUFFIX.sub(" ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _clean_salary_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if text.lower() in _EMPTY_SALARY:
        return None
    return text


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip().replace(",", "")
        if not stripped or not re.fullmatch(r"-?\d+", stripped):
            return None
        value = int(stripped)
    if isinstance(value, float):
        if not value.is_integer():
            return None
        value = int(value)
    if isinstance(value, int) and value > 0:
        return value
    return None


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return _repair_mojibake(" ".join(value.split()))


def _repair_mojibake(text: str) -> str:
    """Repair UTF-8 punctuation a source decoded as Latin-1, such as â.

    The replacement is kept only when it shrinks the string, which is what
    happens for a multibyte character that was split into Latin-1 code points.
    Ordinary accented text is left alone.
    """

    if "Ã" not in text and "â" not in text:
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    if len(repaired) < len(text):
        return repaired
    return text


def _clean_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.startswith(("http://", "https://")):
        return text
    return None


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []
