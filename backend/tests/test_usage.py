"""Anonymous usage logging: it must record the right facts, never record
anything identifying, and never be able to break a user's request."""
import urllib.error

import pytest

from tests.conftest import fake_scores, make_game
from usage import ALLOWED_FIELDS, UsageLogger

URL = "/analyze/username"


# ---- UsageLogger on its own ---------------------------------------------

def test_disabled_without_credentials_makes_no_calls():
    sent = []
    log = UsageLogger("", "", sender=sent.append, background=False)
    log.record(outcome="ok")
    assert not log.enabled and sent == []


def test_only_allowed_fields_are_ever_sent():
    sent = []
    log = UsageLogger("https://x.supabase.co", "k", sender=sent.append, background=False)
    log.record(outcome="ok", games_analyzed=2, username="alice", ip="1.2.3.4")
    assert sent == [{"outcome": "ok", "games_analyzed": 2}]
    assert "username" not in ALLOWED_FIELDS and "ip" not in ALLOWED_FIELDS


def test_sender_failure_is_swallowed():
    def boom(_event):
        raise RuntimeError("supabase is down")

    log = UsageLogger("https://x.supabase.co", "k", sender=boom, background=False)
    log.record(outcome="ok")  # must not raise


def test_legacy_jwt_key_is_sent_as_bearer_but_new_keys_are_not():
    legacy = UsageLogger("https://x", "eyJhbGciOi.payload.sig")._headers()
    assert legacy["Authorization"].startswith("Bearer eyJ")
    modern = UsageLogger("https://x", "sb_secret_abc")._headers()
    assert "Authorization" not in modern and modern["apikey"] == "sb_secret_abc"


# ---- wired into the endpoint ---------------------------------------------

class Recorder:
    def __init__(self):
        self.events = []

    def record(self, **event):
        self.events.append(event)


@pytest.fixture
def usage(app_module, monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(app_module, "USAGE", rec)
    return rec


@pytest.fixture
def patched(app_module, monkeypatch):
    state = {"games": [make_game("Alice", "Bob", 1)], "error": None}

    def fake_fetch(username, months=1):
        if state["error"]:
            raise state["error"]
        return state["games"]

    monkeypatch.setattr(app_module, "fetch_recent_games", fake_fetch)
    monkeypatch.setattr(app_module, "score_pgn_text", fake_scores)
    return state


def body(**over):
    return {"username": "Alice", "max_games": 3, "sort_order": "recent", **over}


def test_successful_analysis_is_recorded(client, patched, usage):
    assert client.post(URL, json=body()).status_code == 200
    (event,) = usage.events
    assert event["outcome"] == "ok"
    assert event["games_requested"] == 3 and event["games_analyzed"] == 1
    assert event["cache_hit"] is False and event["is_owner"] is False
    assert event["duration_ms"] >= 0


def test_repeat_request_is_recorded_as_a_cache_hit(client, patched, usage):
    client.post(URL, json=body())
    client.post(URL, json=body())
    assert [e["cache_hit"] for e in usage.events] == [False, True]


def test_errors_are_recorded_with_their_code(client, patched, usage):
    patched["error"] = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    assert client.post(URL, json=body()).status_code == 404
    assert usage.events[0]["outcome"] == "USER_NOT_FOUND"
    assert usage.events[0]["games_analyzed"] == 0


def test_too_many_games_is_recorded(client, patched, usage, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "MAX_GAMES_LIMIT", 2)
    assert client.post(URL, json=body(max_games=3)).status_code == 400
    assert usage.events[0]["outcome"] == "TOO_MANY_GAMES"


def test_example_account_is_flagged(client, patched, usage):
    patched["games"] = [make_game("Nitrobeast705", "Bob", 1)]
    client.post(URL, json=body(username="nitrobeast705"))
    assert usage.events[0]["is_example"] is True


def test_owner_header_flags_own_testing_only_with_the_right_key(client, patched, usage, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "OWNER_KEY", "s3cret")
    client.post(URL, json=body(), headers={"X-ChessGuard-Owner": "s3cret"})
    client.post(URL, json=body(username="Bob"), headers={"X-ChessGuard-Owner": "wrong"})
    assert [e["is_owner"] for e in usage.events] == [True, False]


def test_owner_flag_is_off_when_no_key_is_configured(client, patched, usage):
    client.post(URL, json=body(), headers={"X-ChessGuard-Owner": ""})
    assert usage.events[0]["is_owner"] is False


def test_events_never_contain_the_username(client, patched, usage):
    client.post(URL, json=body(username="Alice"))
    assert "alice" not in repr(usage.events).lower()


def test_a_logging_crash_does_not_break_the_response(client, patched, app_module, monkeypatch):
    class Exploding:
        def record(self, **_):
            raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "USAGE", Exploding())
    assert client.post(URL, json=body()).status_code == 200
