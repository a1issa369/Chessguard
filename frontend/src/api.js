const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Keep in sync with the backend limit (Field(le=10) in app.py).
// The deployed site sets VITE_MAX_GAMES lower (Render's free CPU analyzes about
// one game per minute). The backend enforces its own MAX_GAMES_LIMIT as well.
export const MAX_GAMES = Math.min(10, Math.max(1, Number(import.meta.env.VITE_MAX_GAMES) || 10));

// An error that carries a machine-readable code, so the UI can decide
// HOW to show a failure instead of just printing a string.
export class ApiError extends Error {
  constructor(code, message, status) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

// FastAPI sends errors in three shapes:
//   { detail: { code, message } }   our structured errors
//   { detail: "text" }              plain HTTPException
//   { detail: [ {msg, loc}, ... ] } 422 validation errors
export function parseError(status, body) {
  const d = body && body.detail;
  if (d && typeof d === "object" && !Array.isArray(d) && d.code) {
    return new ApiError(d.code, d.message || "Request failed.", status);
  }
  if (Array.isArray(d)) {
    return new ApiError("INVALID_INPUT", d[0]?.msg || "Invalid input.", status);
  }
  if (typeof d === "string") {
    return new ApiError("ERROR", d, status);
  }
  return new ApiError("ERROR", `Request failed (${status}).`, status);
}

export async function analyzeUsername(username, maxGames = 3, sortOrder = "recent") {
  let res;
  try {
    res = await fetch(`${API_BASE}/analyze/username`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, max_games: maxGames, sort_order: sortOrder }),
    });
  } catch {
    throw new ApiError("NETWORK", "Can't reach the ChessGuard server. Check your connection and try again.", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw parseError(res.status, body);
  }
  return res.json();
}

// Free hosting puts the server to sleep when idle, and waking it takes about
// a minute. Pinging it as soon as the page opens means it is usually awake
// by the time the visitor presses Analyze. The response is never read, so
// "no-cors" keeps the console clean. Production builds only.
export function warmUpServer() {
  if (!import.meta.env.PROD) return;
  fetch(`${API_BASE}/`, { mode: "no-cors" }).catch(() => {});
}
