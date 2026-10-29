"""Small in-memory rate limiter for the AI endpoints.

Every Gemini call can cost money or use up a free quota, so signed-in users get a short allowance
(per minute and per hour), and the whole server has one daily cap as a backstop against many accounts.

Limits are counted in memory, per backend process: they reset when the backend restarts, and with several
workers each worker counts separately. That is enough to stop accidental or casual abuse; for a large public
service, move the counters to Redis or put a rate limit in front of the API.
"""

import threading
import time

from app.core.config import get_settings
from app.core.errors import AppError

MINUTE = 60
HOUR = 3600
DAY = 86400

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}


def reset() -> None:
    """Forget every counted request (used by tests)."""
    with _lock:
        _hits.clear()


def _prune(key: str, keep_for: int, now: float) -> list[float]:
    """Forget requests older than the LONGEST window that uses this key, and return the rest (oldest first).

    Shorter windows are counted from this list without removing anything, otherwise checking the per-minute
    limit would throw away the history the per-hour limit needs.
    """
    kept = [t for t in _hits.get(key, []) if t > now - keep_for]
    if kept:
        _hits[key] = kept
    else:
        _hits.pop(key, None)
    return kept


def _wait_text(seconds: float) -> str:
    seconds = max(1, int(seconds + 0.999))
    if seconds < 90:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    return f"{(seconds + 59) // 60} minutes"


def check_ai_limit(user_id: int) -> None:
    """Count one AI request for this user, or raise a 429 that says how long to wait.

    A refused request is not counted, so waiting out the message always works.
    """
    settings = get_settings()
    now = time.time()
    user_key = f"ai:user:{int(user_id)}"
    global_key = "ai:global"
    checks = (
        (user_key, MINUTE, settings.ai_requests_per_minute, "You are sending AI requests too quickly."),
        (user_key, HOUR, settings.ai_requests_per_hour, "You have reached the hourly AI limit."),
        (global_key, DAY, settings.ai_daily_limit_total, "The daily AI limit for this site has been reached."),
    )
    with _lock:
        stored = {user_key: _prune(user_key, HOUR, now), global_key: _prune(global_key, DAY, now)}
        for key, window, limit, message in checks:
            hits = [t for t in stored[key] if t > now - window]
            if len(hits) >= limit:
                retry_in = hits[0] + window - now
                raise AppError(429, f"{message} Please try again in {_wait_text(retry_in)}.")
        _hits.setdefault(user_key, []).append(now)
        _hits.setdefault(global_key, []).append(now)
