import { useSyncExternalStore } from "react";

// A deliberately tiny client-side router. ChessGuard has four routes, so a
// dependency would cost more (bundle size, upgrades) than these 30 lines.

const subscribers = new Set();

function subscribe(callback) {
  subscribers.add(callback);
  window.addEventListener("popstate", callback);
  return () => {
    subscribers.delete(callback);
    window.removeEventListener("popstate", callback);
  };
}

const getPath = () => window.location.pathname.replace(/\/+$/, "") || "/";

export const usePath = () => useSyncExternalStore(subscribe, getPath, () => "/");

export function navigate(to) {
  if (to === window.location.pathname) return;
  window.history.pushState({}, "", to);
  subscribers.forEach((callback) => callback());
  window.scrollTo(0, 0);
}

// A real <a href>, so it works with right-click, middle-click and crawlers.
// Plain left clicks are intercepted to avoid a full page reload.
export function Link({ to, onClick, children, ...rest }) {
  function handleClick(e) {
    onClick?.(e);
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(to);
  }
  return (
    <a href={to} onClick={handleClick} {...rest}>
      {children}
    </a>
  );
}
