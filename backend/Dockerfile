# Stockfish is a system binary, not a Python package -- pip can't install it.
# We need a real Linux base image where we can apt-get it directly.
FROM python:3.11-slim

# Install Stockfish from Debian's package repository.
RUN apt-get update && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Debian's stockfish package installs to /usr/games/stockfish, NOT
# /opt/homebrew/bin/stockfish (that path is Mac-specific, from Homebrew).
# This is exactly the kind of environment difference that breaks a "works
# on my machine" deployment -- the path is passed as an env var so it's
# configurable per environment instead of hardcoded.
ENV STOCKFISH_PATH=/usr/games/stockfish

# Render sets $PORT at runtime; we bind to it rather than a fixed port.
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
