"""
Run once from the backend folder:  python3 patch_hardening.py
Adds input validation, a result cache, a per-client rate limit and a
concurrency cap to app.py. Safe to re-run (it refuses if already applied).
"""
import re, sys

p = "app.py"
s = open(p).read()
if "guards import" in s:
    sys.exit("already patched")

def must(cond, msg):
    if not cond:
        sys.exit(f"patch failed, no changes written: {msg}")

# 1. imports
s = s.replace("import tempfile\n", "import tempfile\nfrom typing import Literal\n", 1)
s = s.replace("from fastapi import FastAPI, HTTPException",
              "from fastapi import FastAPI, HTTPException, Request", 1)
s = s.replace("from features import windowed_features\n",
              "from features import windowed_features\n"
              "from guards import ConcurrencyGate, RateLimiter, TTLCache\n", 1)
must("from guards import" in s, "import anchor not found")

# 2. request validation. The username is interpolated into a Chess.com URL,
# so restricting it to Chess.com's own character set also blocks path tricks
# like "../".
s, n = re.subn(r"    username: str\n", '    username: str = Field(min_length=1, max_length=25, pattern=r"^[A-Za-z0-9_-]+$")\n', s, count=1)
must(n == 1, "username field not found")
s, n = re.subn(r'    sort_order: str = "recent"[^\n]*\n', '    sort_order: Literal["recent", "earliest"] = "recent"\n', s, count=1)
must(n == 1, "sort_order field not found")

# 3. canonical recent/earliest slice (handles either earlier shape)
canon = ('    if req.sort_order == "earliest":\n'
         '        selected = usable[:req.max_games]\n'
         '    else:\n'
         '        selected = usable[-req.max_games:]\n')
s2, n = re.subn(r'    if req\.sort_order == "earliest":\n        selected = usable\[:req\.max_games\]\n    else:\n        selected = usable\[-req\.max_games:\]\n', canon, s, count=1)
if n == 0:
    s2, n = re.subn(r"    selected = usable\[-req\.max_games:\]\n", canon, s, count=1)
must(n == 1, "slice logic not found")
s = s2

# 4. last 404 gets a code too
s, n = re.subn(
    r'raise HTTPException\(status_code=404,\s*detail="No recent games with clock data found "\s*"\(try a player who plays rapid/blitz, not bullet\)"\)',
    'raise HTTPException(status_code=404, detail={\n'
    '            "code": "NO_USABLE_GAMES",\n'
    '            "message": "No recent games with clock data found. Try a player who plays rapid or blitz, not bullet."})',
    s, count=1)
must(n == 1, "no-usable-games error not found")

# 5. turn the existing endpoint into an internal function...
s, n = re.subn(r'@app\.post\("/analyze/username"\)\ndef analyze_username\(req: UsernameRequest\):',
               'def _analyze_username_uncached(req: UsernameRequest):', s, count=1)
must(n == 1, "endpoint definition not found")

# 6. ...and add the guarded public endpoint at the end of the file
s = s.rstrip("\n") + '''


# ---------------------------------------------------------------------------
# Guards around the expensive endpoint (see guards.py for the reasoning).
# ---------------------------------------------------------------------------
CACHE = TTLCache(ttl_seconds=int(os.environ.get("CACHE_TTL_SECONDS", "600")))
LIMITER = RateLimiter(limit=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "6")), window_seconds=60)
GATE = ConcurrencyGate(max_concurrent=int(os.environ.get("MAX_CONCURRENT_ANALYSES", "2")))


def _client_ip(request: Request) -> str:
    # Behind Render's proxy the real client is in X-Forwarded-For. This is
    # best-effort (a client can spoof it); GATE is the hard protection.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.post("/analyze/username")
def analyze_username(req: UsernameRequest, request: Request):
    key = (req.username.lower(), req.max_games, req.sort_order)

    cached = CACHE.get(key)
    if cached is not None:
        return cached

    if not LIMITER.allow(_client_ip(request)):
        raise HTTPException(status_code=429, detail={
            "code": "RATE_LIMITED",
            "message": "Too many requests. Please wait a minute and try again."})

    if not GATE.acquire():
        raise HTTPException(status_code=429, detail={
            "code": "BUSY",
            "message": "The analyzer is busy with other requests. Try again in a minute."})
    try:
        result = _analyze_username_uncached(req)
    finally:
        GATE.release()

    if result["games_analyzed"] > 0:
        CACHE.set(key, result)
    return result
'''
open(p, "w").write(s)
print("patched")
