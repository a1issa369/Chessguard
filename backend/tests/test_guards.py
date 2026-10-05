from guards import ConcurrencyGate, RateLimiter, TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0
    def __call__(self):
        return self.now


def test_cache_returns_value_until_ttl_expires():
    clock = FakeClock()
    cache = TTLCache(ttl_seconds=10, clock=clock)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    clock.now = 9.9
    assert cache.get("k") == "v"
    clock.now = 10.0
    assert cache.get("k") is None


def test_cache_evicts_least_recently_used():
    cache = TTLCache(max_entries=2, clock=FakeClock())
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")          # touch a, so b is now the oldest
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1 and cache.get("c") == 3


def test_rate_limiter_blocks_after_limit_then_recovers():
    clock = FakeClock()
    rl = RateLimiter(limit=2, window_seconds=60, clock=clock)
    assert rl.allow("ip") and rl.allow("ip")
    assert not rl.allow("ip")
    clock.now = 60.0
    assert rl.allow("ip")


def test_rate_limiter_tracks_clients_separately():
    rl = RateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    assert rl.allow("a")
    assert rl.allow("b")
    assert not rl.allow("a")


def test_gate_never_exceeds_capacity_and_frees_slots():
    gate = ConcurrencyGate(max_concurrent=2)
    assert gate.acquire() and gate.acquire()
    assert not gate.acquire()
    gate.release()
    assert gate.acquire()
