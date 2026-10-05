// Owner-only analytics (Vercel Web Analytics). It is cookie-free and
// aggregate: page views, referrers, countries and device types, visible only
// in the site owner's Vercel dashboard. Visitors see nothing and are asked
// nothing. The script is injected by hand, instead of through an npm
// package, so the production Content-Security-Policy can stay at
// script-src 'self'.

let started = false;

export function initAnalytics() {
  if (started || !import.meta.env.PROD) return; // never in dev or tests
  started = true;
  window.va =
    window.va ||
    function () {
      (window.vaq = window.vaq || []).push(arguments);
    };
  const script = document.createElement("script");
  script.defer = true;
  script.src = "/_vercel/insights/script.js";
  document.head.appendChild(script);
}

// Custom events. Vercel only records these on Pro and Enterprise plans;
// on the free plan the call is harmless and page views still count.
export function trackEvent(name, data) {
  window.va?.("event", { name, data });
}
