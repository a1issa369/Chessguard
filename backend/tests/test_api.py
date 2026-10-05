import urllib.error

import pytest

from tests.conftest import fake_scores, make_game

URL = "/analyze/username"


@pytest.fixture
def patched(app_module, monkeypatch):
    """Fake Chess.com + engine. Returns a dict the test can customise."""
    state = {"games": [], "calls": 0, "error": None}

    def fake_fetch(username, months=1):
        state["calls"] += 1
        if state["error"]:
            raise state["error"]
        return state["games"]

    monkeypatch.setattr(app_module, "fetch_recent_games", fake_fetch)
    monkeypatch.setattr(app_module, "score_pgn_text", fake_scores)
    return state


def body(**over):
    return {"username": "Alice", "max_games": 3, "sort_order": "recent", **over}


def test_health_check(client):
    assert client.get("/").json()["status"] == "ok"


# ---- error codes the frontend toasts depend on -------------------------

def test_unknown_account_returns_user_not_found(client, patched):
    patched["error"] = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    r = client.post(URL, json=body())
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_chesscom_outage_is_a_502_not_a_404(client, patched):
    patched["error"] = urllib.error.HTTPError("u", 500, "Server Error", {}, None)
    r = client.post(URL, json=body())
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "UPSTREAM_ERROR"


def test_network_failure_is_a_502(client, patched):
    patched["error"] = OSError("dns failure")
    assert client.post(URL, json=body()).status_code == 502


def test_account_with_no_games(client, patched):
    r = client.post(URL, json=body())
    assert r.status_code == 404 and r.json()["detail"]["code"] == "NO_GAMES"


def test_games_without_clock_data_are_not_usable(client, patched):
    patched["games"] = [make_game("Alice", "Bob", 1, with_clock=False)]
    r = client.post(URL, json=body())
    assert r.json()["detail"]["code"] == "NO_USABLE_GAMES"


# ---- input validation ---------------------------------------------------

@pytest.mark.parametrize("n", [0, 11, 25, -1])
def test_max_games_outside_1_to_10_is_rejected(client, patched, n):
    assert client.post(URL, json=body(max_games=n)).status_code == 422
    assert patched["calls"] == 0


@pytest.mark.parametrize("name", ["../etc/passwd", "a b", "x" * 26, "", "bob?evil=1", "a/b"])
def test_malformed_usernames_never_reach_chesscom(client, patched, name):
    assert client.post(URL, json=body(username=name)).status_code == 422
    assert patched["calls"] == 0


def test_bad_sort_order_is_rejected(client, patched):
    assert client.post(URL, json=body(sort_order="sideways")).status_code == 422


@pytest.mark.parametrize("name", ["Nitrobeast705", "a_b-c", "x" * 25])
def test_valid_usernames_pass_validation(client, patched, name):
    patched["games"] = [make_game(name, "Bob", 1)]
    assert client.post(URL, json=body(username=name)).status_code == 200


# ---- behaviour ----------------------------------------------------------

def test_returns_requested_players_side_and_opponent(client, patched):
    patched["games"] = [make_game("Alice", "Bob", 100), make_game("Carol", "Alice", 200)]
    data = client.post(URL, json=body(max_games=10)).json()
    assert data["games_analyzed"] == 2
    first, second = data["results"]
    assert (first["player"], first["opponent"], first["cheat_probability"]) == ("Alice", "Bob", 0.2)
    # Alice plays black in game two, so she gets the black-side score
    assert (second["player"], second["opponent"], second["cheat_probability"]) == ("Alice", "Carol", 0.9)


def test_username_match_is_case_insensitive(client, patched):
    patched["games"] = [make_game("Alice", "Bob", 1)]
    assert client.post(URL, json=body(username="aLiCe")).json()["games_analyzed"] == 1


def test_recent_takes_newest_games_and_earliest_takes_oldest(client, patched, app_module):
    patched["games"] = [make_game("Alice", f"Opp{i}", i) for i in range(5)]
    recent = client.post(URL, json=body(max_games=2, sort_order="recent")).json()
    assert [g["end_time"] for g in recent["results"]] == [3, 4]
    app_module.CACHE.clear()
    earliest = client.post(URL, json=body(max_games=2, sort_order="earliest")).json()
    assert [g["end_time"] for g in earliest["results"]] == [0, 1]


def test_one_unanalyzable_game_does_not_fail_the_request(client, patched, app_module, monkeypatch):
    patched["games"] = [make_game("Alice", "Bad", 1), make_game("Alice", "Good", 2)]

    def flaky(pgn):
        if "Bad" in pgn:
            raise RuntimeError("engine crashed")
        return fake_scores(pgn)

    monkeypatch.setattr(app_module, "score_pgn_text", flaky)
    data = client.post(URL, json=body(max_games=10)).json()
    assert [g["opponent"] for g in data["results"]] == ["Good"]


# ---- guards -------------------------------------------------------------

def test_repeat_request_is_served_from_cache(client, patched):
    patched["games"] = [make_game("Alice", "Bob", 1)]
    first = client.post(URL, json=body()).json()
    second = client.post(URL, json=body(username="ALICE")).json()  # same key, different case
    assert patched["calls"] == 1
    assert first["results"] == second["results"]


def test_empty_results_are_not_cached(client, patched):
    patched["games"] = []
    client.post(URL, json=body())
    client.post(URL, json=body())
    assert patched["calls"] == 2


def test_busy_server_answers_429_and_releases_slot(client, patched, app_module):
    patched["games"] = [make_game("Alice", "Bob", 1)]
    held = []
    while app_module.GATE.acquire():
        held.append(1)
    try:
        r = client.post(URL, json=body())
        assert r.status_code == 429 and r.json()["detail"]["code"] == "BUSY"
    finally:
        for _ in held:
            app_module.GATE.release()
    assert client.post(URL, json=body()).status_code == 200


def test_gate_slot_is_released_even_when_analysis_fails(client, patched, app_module):
    patched["error"] = urllib.error.HTTPError("u", 404, "x", {}, None)
    for _ in range(5):   # more failures than slots would deadlock a leaky gate
        client.post(URL, json=body(username=f"user{_}"))
    patched["error"] = None
    patched["games"] = [make_game("Alice", "Bob", 1)]
    assert client.post(URL, json=body()).status_code == 200


def test_rate_limit_triggers_for_uncached_requests(client, patched, app_module):
    patched["games"] = [make_game("Alice", "Bob", 1)]
    limit = app_module.LIMITER.limit
    codes = [client.post(URL, json=body(username=f"user{i}")).status_code for i in range(limit + 1)]
    assert codes[:limit] == [200] * limit
    assert codes[limit] == 429
