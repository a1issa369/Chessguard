import { describe, expect, it, vi } from "vitest";
import { analyzeUsername, ApiError, parseError } from "../api";

describe("parseError", () => {
  it("reads structured errors", () => {
    const e = parseError(404, { detail: { code: "USER_NOT_FOUND", message: "nope" } });
    expect(e).toMatchObject({ code: "USER_NOT_FOUND", message: "nope", status: 404 });
  });
  it("reads FastAPI validation arrays", () => {
    const e = parseError(422, { detail: [{ msg: "Input should be less than or equal to 10" }] });
    expect(e.code).toBe("INVALID_INPUT");
    expect(e.message).toContain("10");
  });
  it("reads plain string details", () => {
    expect(parseError(500, { detail: "boom" })).toMatchObject({ code: "ERROR", message: "boom" });
  });
  it("falls back when the body is empty", () => {
    expect(parseError(502, {}).message).toContain("502");
  });
});

describe("analyzeUsername", () => {
  it("posts the request body and returns the JSON", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ games_analyzed: 0, results: [] }) }));
    vi.stubGlobal("fetch", fetchMock);
    await analyzeUsername("alice", 4, "earliest");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/analyze\/username$/);
    expect(JSON.parse(init.body)).toEqual({ username: "alice", max_games: 4, sort_order: "earliest" });
  });

  it("turns a dropped connection into a NETWORK error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    await expect(analyzeUsername("alice")).rejects.toMatchObject({ code: "NETWORK" });
  });

  it("throws an ApiError carrying the server's code", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false, status: 404, json: async () => ({ detail: { code: "USER_NOT_FOUND", message: "x" } }),
    })));
    const err = await analyzeUsername("ghost").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("USER_NOT_FOUND");
  });

  it("survives a non-JSON error body", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500, json: async () => { throw new Error("bad json"); } })));
    await expect(analyzeUsername("a")).rejects.toMatchObject({ status: 500 });
  });
});
