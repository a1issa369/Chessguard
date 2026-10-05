import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Set VITE_SITE_URL (for example in Vercel's environment settings) to the
// public address of the site. It fills in the canonical and social-preview
// URLs in index.html and generates sitemap.xml and robots.txt at build time,
// so no placeholder domain is ever committed.
const SITE_URL = (process.env.VITE_SITE_URL || "http://localhost:5173").replace(/\/+$/, "");
const PAGES = ["/", "/privacy", "/terms"];

function siteUrlPlugin() {
  return {
    name: "chessguard-site-url",
    transformIndexHtml: (html) => html.replaceAll("__SITE_URL__", SITE_URL),
    generateBundle() {
      const urls = PAGES.map((p) => `  <url><loc>${SITE_URL}${p === "/" ? "/" : p}</loc></url>`).join("\n");
      this.emitFile({
        type: "asset",
        fileName: "sitemap.xml",
        source: `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
      });
      this.emitFile({
        type: "asset",
        fileName: "robots.txt",
        source: `User-agent: *\nAllow: /\n\nSitemap: ${SITE_URL}/sitemap.xml\n`,
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), siteUrlPlugin()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test-setup.js",
    globals: true,
    css: false,
  },
});
