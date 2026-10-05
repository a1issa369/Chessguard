import { describe, expect, it } from "vitest";
import { validateUsername } from "../validation";
import { toastForError } from "../errors";
import { ApiError } from "../api";

describe("validateUsername", () => {
  it.each(["Nitrobeast705", "a", "under_score", "dash-ed", "x".repeat(25), "  padded  "])(
    "accepts %j",
    (name) => expect(validateUsername(name)).toBeNull()
  );

  it.each([["", /enter a chess.com username/i], ["   ", /enter a chess.com username/i],
           ["x".repeat(26), /at most 25/i], ["bob smith", /letters, numbers/i],
           ["../etc/passwd", /letters, numbers/i], ["bob?x=1", /letters, numbers/i]])(
    "rejects %j",
    (name, message) => expect(validateUsername(name)).toMatch(message)
  );
});

describe("toastForError", () => {
  it("names the missing account", () => {
    const t = toastForError(new ApiError("USER_NOT_FOUND", "x", 404), "ghost99");
    expect(t.kind).toBe("error");
    expect(t.message).toContain("ghost99");
  });

  it.each(["BUSY", "RATE_LIMITED", "INVALID_INPUT"])("%s is a warning", (code) => {
    expect(toastForError(new ApiError(code, "m", 429), "u").kind).toBe("warning");
  });

  it.each(["NETWORK", "UPSTREAM_ERROR"])("%s is an error toast", (code) => {
    expect(toastForError(new ApiError(code, "m", 0), "u").kind).toBe("error");
  });

  it("leaves other errors for the inline banner", () => {
    expect(toastForError(new ApiError("NO_GAMES", "m", 404), "u")).toBeNull();
    expect(toastForError(new Error("boom"), "u")).toBeNull();
  });
});
