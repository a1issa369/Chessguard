"""
guards.py

Small, dependency-free protections for the expensive /analyze/username
endpoint. Each Stockfish analysis burns real CPU, and a public deployment
is reachable by anyone, so we need three things:

  TTLCache         repeat requests for the same input return instantly
                   instead of re-running the engine
  RateLimiter      best-effort cap on requests per client per time window
  ConcurrencyGate  HARD cap on analyses running at once, so a burst of
                   traffic gets a friendly "busy" answer instead of
                   starving the server

Every class takes an injectable clock so tests never have to sleep.
"""

import threading
import time
from collections import OrderedDict, deque


class TTLCache:
    def __init__(self, ttl_seconds=600, max_entries=128, clock=time.monotonic):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._data = OrderedDict()  # key -> (expires_at, value)
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if self._clock() >= expires_at:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key, value):
        with self._lock:
            self._data[key] = (self._clock() + self.ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)  # evict least recently used

    def clear(self):
        with self._lock:
            self._data.clear()


class RateLimiter:
    """Sliding window: at most `limit` hits per `window_seconds` per key."""

    def __init__(self, limit=6, window_seconds=60, clock=time.monotonic):
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits = {}  # key -> deque of timestamps
        self._lock = threading.Lock()

    def allow(self, key) -> bool:
        now = self._clock()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

    def clear(self):
        with self._lock:
            self._hits.clear()


class ConcurrencyGate:
    """Non-blocking semaphore: acquire() returns False instead of waiting."""

    def __init__(self, max_concurrent=2):
        self._sem = threading.BoundedSemaphore(max_concurrent)

    def acquire(self) -> bool:
        return self._sem.acquire(blocking=False)

    def release(self):
        self._sem.release()
