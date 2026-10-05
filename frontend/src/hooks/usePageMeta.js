import { useEffect } from "react";

// Single-page apps keep one <head>, so each route sets its own title and,
// for pages that should not appear in search results, a robots noindex tag.
export default function usePageMeta(title, { noindex = false } = {}) {
  useEffect(() => {
    const previousTitle = document.title;
    document.title = title;

    let robots = null;
    if (noindex) {
      robots = document.createElement("meta");
      robots.name = "robots";
      robots.content = "noindex";
      document.head.appendChild(robots);
    }
    return () => {
      document.title = previousTitle;
      robots?.remove();
    };
  }, [title, noindex]);
}
