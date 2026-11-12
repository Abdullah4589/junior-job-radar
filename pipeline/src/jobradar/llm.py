"""Optional LLM pass over a keyword extraction.

Nothing is called unless `JOBRADAR_LLM_URL` is set. `JOBRADAR_LLM_API_KEY`
is sent as a bearer token when it is set, and is never written to disk.
`JOBRADAR_LLM_MODEL` selects the model; otherwise the request uses `default`.
Any failure, including a missing key on a server that requires one, keeps
the keyword result. The pipeline runs with no secrets and no network when
the URL is unset.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from jobradar.extract import Extraction, region_names, skill_names
from jobradar.models import SENIORITY_LEVELS, WORKPLACES

_SYSTEM = (
    "Extract one software job posting. Reply with a JSON object and no markdown. "
    "seniority is one of intern, junior, mid, senior, lead, staff, principal, "
    "manager, unknown. workplace is one of remote, hybrid, onsite, unknown. "
    "skills is an array of technologies actually named in the posting. "
    "regions is an array of country or macro-region restrictions actually named. "
    "Do not guess a skill or a region that the posting does not state."
)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

Transport = Callable[..., Any]


def maybe_refine(
    keyword: Extraction,
    *,
    context: str,
    transport: Transport | None = None,
) -> Extraction:
    """Return an LLM extraction, or `keyword` when no URL is set or the call fails."""

    url = os.environ.get("JOBRADAR_LLM_URL", "").strip()
    if not url:
        return keyword
    key = os.environ.get("JOBRADAR_LLM_API_KEY", "").strip()
    model = os.environ.get("JOBRADAR_LLM_MODEL", "").strip() or "default"
    opener = transport or urllib.request.urlopen
    try:
        body = _post(url, key=key, model=model, context=context, transport=opener)
        payload = _payload(body)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError, TypeError):
        return keyword
    if payload is None:
        return keyword
    return _merge(keyword, payload)


def _post(url: str, *, key: str, model: str, context: str, transport: Transport) -> object:
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": context},
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "JuniorJobRadar/0.1",
        },
        method="POST",
    )
    if key:
        request.add_header("Authorization", f"Bearer {key}")
    response = transport(request, timeout=10)
    if hasattr(response, "__enter__"):
        with response as handle:
            raw = handle.read()
    else:
        raw = response.read()
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, bytes):
        return json.loads(raw.decode("utf-8"))
    raise ValueError("LLM response was not JSON text")


def _payload(body: object) -> dict[str, Any] | None:
    if not isinstance(body, dict):
        return None
    if any(key in body for key in ("seniority", "skills", "workplace", "regions")):
        return body
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return None
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    text = _FENCE.sub("", content.strip())
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _merge(keyword: Extraction, payload: dict[str, Any]) -> Extraction:
    seniority = payload.get("seniority")
    if seniority not in SENIORITY_LEVELS or seniority == "unknown":
        seniority = keyword.seniority
    workplace = payload.get("workplace")
    if workplace not in WORKPLACES or workplace == "unknown":
        workplace = keyword.workplace
    skills = _known_list(payload.get("skills"), skill_names()) or list(keyword.skills)
    regions = _known_list(payload.get("regions"), region_names()) or list(keyword.regions)
    return Extraction(
        seniority=str(seniority),
        skills=skills,
        workplace=str(workplace),
        junior_friendly=seniority in {"intern", "junior"},
        regions=regions,
    )


def _known_list(value: object, allowed: set[str]) -> list[str] | None:
    if not isinstance(value, list):
        return None
    chosen: list[str] = []
    for item in value:
        if isinstance(item, str) and item in allowed and item not in chosen:
            chosen.append(item)
    return chosen or None
