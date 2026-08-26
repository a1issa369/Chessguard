"""
fetch_games.py

Pulls a player's recent games from the Chess.com Public API.
Run this LOCALLY (it needs internet access), not in a sandbox.

Usage:
    python3 fetch_games.py <chess.com_username> [--months 1] [--out sample_games]

Docs: https://www.chess.com/news/view/published-data-api
"""

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL = "https://api.chess.com/pub/player/{username}/games/archives"

# Chess.com blocks requests with no/generic User-Agent. Put your real
# contact info here if you plan to make many requests, as a courtesy
# to their ops team and keeps you from getting rate-limited.
HEADERS = {
    "User-Agent": "ChessGuard-Project/0.1 (contact: ahmedkadarissa@gmail.com)"
}


def get_json(url: str) -> dict:
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"HTTP error {e.code} fetching {url}", file=sys.stderr)
        raise


def fetch_recent_games(username: str, months: int = 1) -> list:
    """Returns a list of raw game dicts (each has a 'pgn' field) from the
    most recent `months` monthly archives."""
    archives_url = BASE_URL.format(username=username)
    archives = get_json(archives_url)["archives"]

    if not archives:
        print(f"No archives found for '{username}'. Typo, or private/no games?")
        return []

    # archives are ordered oldest -> newest; take the last N
    recent_archive_urls = archives[-months:]

    all_games = []
    for url in recent_archive_urls:
        month_data = get_json(url)
        all_games.extend(month_data.get("games", []))

    return all_games


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="Chess.com username to fetch")
    parser.add_argument("--months", type=int, default=1,
                         help="How many recent monthly archives to pull")
    parser.add_argument("--out", default="sample_games",
                         help="Directory to save individual .pgn files")
    args = parser.parse_args()

    games = fetch_recent_games(args.username, args.months)
    print(f"Fetched {len(games)} games for '{args.username}'.")

    os.makedirs(args.out, exist_ok=True)
    saved = 0
    for i, game in enumerate(games):
        pgn = game.get("pgn")
        if not pgn:
            continue  # some entries (e.g. daily games in progress) lack PGN
        # skip games with no clock data - useless for our timing features
        if "%clk" not in pgn:
            continue
        path = os.path.join(args.out, f"{args.username}_{i}.pgn")
        with open(path, "w") as f:
            f.write(pgn)
        saved += 1

    print(f"Saved {saved} games with clock data to '{args.out}/'.")
    if games and saved == 0:
        print("(Games found, but none had clock annotations, try 'rapid' "
              "or 'blitz' games, since some formats/bots omit clocks.)")


if __name__ == "__main__":
    main()
