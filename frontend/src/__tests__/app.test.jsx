import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Root from "../Root";

const ok = (data) => ({ ok: true, status: 200, json: async () => data });
const fail = (status, detail) => ({ ok: false, status, json: async () => ({ detail }) });

function mockFetch(handler) {
  const fn = vi.fn(async (_url, init) => handler(JSON.parse(init.body)));
  vi.stubGlobal("fetch", fn);
  return fn;
}

function renderAt(path = "/") {
  window.history.replaceState({}, "", path);
  return render(<Root />);
}

const game = (over = {}) => ({
  end_time: 1700000000, time_control: "600", opponent: "Bob", player: "Alice",
  moves_analyzed: 30, cheat_probability: 0.2,
  features: { top1_match_rate: 50, avg_centipawn_loss: 40, max_window_match_rate: 60,
              min_window_avg_cp_loss: 20, perfect_move_frac: 0.3, longest_perfect_streak: 4 },
  ...over,
});

describe("analyze form", () => {
  it("shows an inline error and makes no request for an empty username", async () => {
    const fetchMock = mockFetch(() => ok({}));
    renderAt();
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByText("Enter a Chess.com username.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects usernames with illegal characters before calling the API", async () => {
    const fetchMock = mockFetch(() => ok({}));
    renderAt();
    await userEvent.type(screen.getByLabelText("Chess.com username"), "bad/name");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByText(/letters, numbers, underscores/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Chess.com username")).toHaveAttribute("aria-invalid", "true");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("toasts and clamps when the game count goes over 10", async () => {
    renderAt();
    const count = screen.getByLabelText("Number of games to analyze");
    await userEvent.clear(count);
    await userEvent.type(count, "25");
    expect(count).toHaveValue(10);
    expect(await screen.findByText(/up to 10 games at a time/i)).toBeInTheDocument();
  });

  it("toasts when the account does not exist", async () => {
    mockFetch(() => fail(404, { code: "USER_NOT_FOUND", message: "x" }));
    renderAt();
    await userEvent.type(screen.getByLabelText("Chess.com username"), "ghost99");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByText("Account not found")).toBeInTheDocument();
    expect(screen.getByText(/ghost99/)).toBeInTheDocument();
  });

  it("toasts when the server is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    renderAt();
    await userEvent.type(screen.getByLabelText("Chess.com username"), "alice");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByText("Server unreachable")).toBeInTheDocument();
  });

  it("toasts a warning when the analyzer is busy", async () => {
    mockFetch(() => fail(429, { code: "BUSY", message: "Busy right now." }));
    renderAt();
    await userEvent.type(screen.getByLabelText("Chess.com username"), "alice");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByText("Analyzer is busy")).toBeInTheDocument();
  });

  it("shows no-games problems in the inline banner instead of a toast", async () => {
    mockFetch(() => fail(404, { code: "NO_GAMES", message: "No games found for 'alice'." }));
    renderAt();
    await userEvent.type(screen.getByLabelText("Chess.com username"), "alice");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByText("No games found for 'alice'.")).toBeInTheDocument();
  });

  it("renders result cards on success", async () => {
    mockFetch(() => ok({ username: "Alice", games_analyzed: 1, results: [game()] }));
    renderAt();
    await userEvent.type(screen.getByLabelText("Chess.com username"), "Alice");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    expect(await screen.findByText(/1 game analyzed/)).toBeInTheDocument();
    expect(screen.getByText(/Bob/)).toBeInTheDocument();
    expect(screen.getByText(/not proof of cheating/i)).toBeInTheDocument();
  });

  it("re-sorts already fetched games without a new request", async () => {
    const fetchMock = mockFetch(() => ok({
      username: "Alice", games_analyzed: 2,
      results: [game({ opponent: "Older", end_time: 1 }), game({ opponent: "Newer", end_time: 2 })],
    }));
    renderAt();
    await userEvent.type(screen.getByLabelText("Chess.com username"), "Alice");
    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));
    await screen.findByText(/Newer/);
    const order = () =>
      screen.getAllByText(/Older|Newer/).map((n) => (n.textContent.includes("Older") ? "Older" : "Newer"));
    expect(order()).toEqual(["Newer", "Older"]);
    await userEvent.selectOptions(screen.getByLabelText("Which games to analyze"), "earliest");
    expect(order()).toEqual(["Older", "Newer"]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("'Try an example' analyzes the example account in one click", async () => {
    const fetchMock = mockFetch(() => ok({ username: "x", games_analyzed: 0, results: [] }));
    renderAt();
    await userEvent.click(screen.getByRole("button", { name: "Try an example" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).username).toBe("Nitrobeast705");
  });
});

describe("routing and legal pages", () => {
  it("footer states this is a student project with no third-party endorsement", () => {
    renderAt();
    expect(screen.getByText(/student project/i)).toBeInTheDocument();
    expect(screen.getByText(/not endorsed by, affiliated with, or sponsored by/i)).toBeInTheDocument();
  });

  it("navigates to the privacy policy and terms from the footer", async () => {
    renderAt();
    await userEvent.click(screen.getByRole("link", { name: "Privacy Policy" }));
    expect(await screen.findByRole("heading", { name: "Privacy Policy" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/privacy");
    expect(document.title).toMatch(/Privacy Policy/);
    await userEvent.click(screen.getByRole("link", { name: "Terms of Service" }));
    expect(await screen.findByRole("heading", { name: "Terms of Service" })).toBeInTheDocument();
  });

  it("renders the policy pages directly by URL", async () => {
    renderAt("/terms");
    expect(await screen.findByRole("heading", { name: "Terms of Service" })).toBeInTheDocument();
  });

  it("shows a custom 404 with a noindex tag and a way home", async () => {
    renderAt("/definitely-not-a-page");
    expect(await screen.findByText(/that square is empty/i)).toBeInTheDocument();
    expect(document.querySelector('meta[name="robots"][content="noindex"]')).not.toBeNull();
    await userEvent.click(screen.getByRole("link", { name: "Back to ChessGuard" }));
    expect(await screen.findByRole("heading", { name: "ChessGuard" })).toBeInTheDocument();
    expect(document.querySelector('meta[name="robots"]')).toBeNull();
  });

  it("every internal footer link points at a real route", () => {
    renderAt();
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href")).filter((h) => h.startsWith("/"));
    expect(hrefs.sort()).toEqual(["/privacy", "/terms"]);
  });

  it("external links open safely", () => {
    renderAt();
    const gh = screen.getByRole("link", { name: "Source on GitHub" });
    expect(gh).toHaveAttribute("target", "_blank");
    expect(gh.getAttribute("rel")).toContain("noopener");
  });
});

describe("analytics", () => {
  it("shows no banner and no analytics controls to visitors", () => {
    renderAt();
    expect(screen.queryByRole("region", { name: /analytics/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /analytics/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /accept/i })).toBeNull();
  });

  it("does not load the analytics script outside production builds", () => {
    renderAt();
    expect(document.querySelector('script[src*="_vercel"]')).toBeNull();
  });
});
