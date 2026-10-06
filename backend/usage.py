"""
usage.py

Anonymous usage logging for ChessGuard, so the author can answer "how is this
actually used?" with real numbers (analyses run, games reviewed, cache hit
rate, speed, error rates).

Design rules:
  * Privacy first. Only the fields in ALLOWED_FIELDS are ever sent. There is
    no field for a username or an IP address, and anything else passed to
    record() is silently dropped, so a future edit cannot leak one by accident.
  * Never hurt a user request. Writes happen on a background thread with a
    short timeout, and every failure is swallowed (and printed).
  * Off by default. With SUPABASE_URL / SUPABASE_SECRET_KEY unset (local runs,
    tests), record() does nothing and makes no network calls.
"""

import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ALLOWED_FIELDS = (
    "outcome",          # "ok" or an error code such as USER_NOT_FOUND
    "games_requested",
    "games_analyzed",
    "cache_hit",
    "duration_ms",
    "is_example",       # the "Try an example" account
    "is_owner",         # the author's own testing, so it can be excluded
)


class UsageLogger:
    def __init__(self, url="", key="", table="usage_events",
                 sender=None, background=True, timeout=3.0):
        self.url = (url or "").rstrip("/")
        self.key = key or ""
        self.table = table
        self.timeout = timeout
        self._sender = sender or self._post
        self._pool = ThreadPoolExecutor(max_workers=1) if background else None

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("SUPABASE_URL", ""),
                   os.environ.get("SUPABASE_SECRET_KEY", ""))

    @property
    def enabled(self):
        return bool(self.url and self.key)

    def record(self, **event):
        if not self.enabled:
            return
        clean = {k: event[k] for k in ALLOWED_FIELDS if k in event}
        if self._pool is not None:
            self._pool.submit(self._safe_send, clean)
        else:
            self._safe_send(clean)

    def _safe_send(self, event):
        try:
            self._sender(event)
        except Exception as e:  # logging must never break anything
            print(f"usage logging failed: {e}")

    def _headers(self):
        headers = {
            "apikey": self.key,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        # Legacy service_role keys are JWTs and are sent as a bearer token.
        # The newer sb_secret_... keys are not JWTs and go in apikey only.
        if self.key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self.key}"
        return headers

    def _post(self, event):
        req = urllib.request.Request(
            f"{self.url}/rest/v1/{self.table}",
            data=json.dumps(event).encode(),
            headers=self._headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            resp.read()
