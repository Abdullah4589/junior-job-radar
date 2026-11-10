"""Small JSON client: User-Agent, timeout, and retries. No API keys."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

USER_AGENT = (
    "JuniorJobRadar/0.1 "
    "(+https://github.com/Abdullah4589/junior-job-radar; educational portfolio)"
)

# Retry transient failures only. A 404 will not start working on the next try.
RETRY_STATUSES = {429, 500, 502, 503, 504}

UrlOpen = Callable[..., Any]
Sleeper = Callable[[float], None]


class SourceFetchError(Exception):
    """A source could not be fetched after retries. Other sources should continue."""


def get_json(
    url: str,
    *,
    timeout: float = 20.0,
    retries: int = 3,
    urlopen: UrlOpen = urllib.request.urlopen,
    sleep: Sleeper = time.sleep,
) -> Any:
    """GET `url` and parse a JSON body.

    Retries timeouts, connection errors, HTTP 429/5xx, and invalid JSON.
    Backoff is 1s, 2s, 4s (capped at 8s). `sleep` is injectable so tests
    do not wait.
    """

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
            return json.loads(payload.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in RETRY_STATUSES or attempt == retries:
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            last_error = exc
            if attempt == retries:
                break
        sleep(min(8.0, 2 ** (attempt - 1)))

    raise SourceFetchError(
        f"GET {url} failed after {attempt} attempt(s): {last_error}"
    ) from last_error
