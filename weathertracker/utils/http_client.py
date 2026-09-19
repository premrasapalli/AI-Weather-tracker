import functools
import logging

import httpx

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _client() -> httpx.Client:
    return httpx.Client(
        timeout=10.0,
        headers={
            "User-Agent": "AI-Weather-Tracker/2.0 (India live weather intelligence)",
            "Accept": "application/json",
        },
    )


def get_json(url: str, params: dict | None = None, retries: int = 2) -> dict:
    client = _client()
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - retryable upstream
            last_exc = exc
            logger.warning("GET %s failed (attempt %s): %s", url, attempt + 1, exc)
    raise RuntimeError(f"Upstream request failed to {url}") from last_exc
