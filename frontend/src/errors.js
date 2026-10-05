// Maps an ApiError (see api.js) to a toast. Returns null for errors that are
// better shown inline (for example "this player has no usable games").
export function toastForError(err, username) {
  switch (err?.code) {
    case "USER_NOT_FOUND":
      return {
        kind: "error",
        title: "Account not found",
        message: `There is no Chess.com account named “${username}”. Check the spelling and try again.`,
      };
    case "NETWORK":
      return { kind: "error", title: "Server unreachable", message: err.message };
    case "UPSTREAM_ERROR":
      return { kind: "error", title: "Chess.com is unavailable", message: err.message };
    case "TOO_MANY_GAMES":
    case "BUSY":
      return { kind: "warning", title: "Analyzer is busy", message: err.message };
    case "RATE_LIMITED":
      return { kind: "warning", title: "Slow down a little", message: err.message };
    case "INVALID_INPUT":
      return { kind: "warning", title: "Check your input", message: err.message };
    default:
      return null;
  }
}
