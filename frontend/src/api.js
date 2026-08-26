// api.js
//
// Small wrapper around fetch() so the rest of the app never deals with
// URLs or JSON parsing directly. If the backend's address ever changes
// (e.g. deploying it somewhere other than localhost), this is the only
// file that needs to change.

const API_BASE = "http://localhost:8000";

export async function analyzeUsername(username, maxGames = 3, sortOrder = "recent") {
  const res = await fetch(`${API_BASE}/analyze/username`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, max_games: maxGames, sort_order: sortOrder }),
  });

  if (!res.ok) {
    // FastAPI puts error messages in a "detail" field -- surface that
    // to the user instead of a generic "something went wrong."
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }

  return res.json();
}
