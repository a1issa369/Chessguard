import { useEffect, useState } from "react";

export default function useTheme() {
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem("chessguard-theme");
      if (saved === "dark" || saved === "light") return saved;
    } catch {
      /* storage can be blocked; fall through to the OS preference */
    }
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem("chessguard-theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  return [theme, setTheme];
}
