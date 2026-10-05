// Chess.com usernames: letters, numbers, underscores and hyphens, up to 25
// characters. The backend enforces the same rule, because the name is placed
// inside a URL and must never contain characters like "/" or "?".
export const MAX_USERNAME_LENGTH = 25;
export const USERNAME_PATTERN = /^[A-Za-z0-9_-]+$/;

export function validateUsername(raw) {
  const name = String(raw ?? "").trim();
  if (!name) return "Enter a Chess.com username.";
  if (name.length > MAX_USERNAME_LENGTH) return `Usernames are at most ${MAX_USERNAME_LENGTH} characters.`;
  if (!USERNAME_PATTERN.test(name)) return "Usernames can only use letters, numbers, underscores and hyphens.";
  return null;
}
