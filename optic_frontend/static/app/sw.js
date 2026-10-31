/* Synaps Optic service worker (docs/DESIGN.md "App shell"). Served by the backend at /sw.js with
   Service-Worker-Allowed: / so its scope is the whole site.

   Rules, in order of importance:
   1. Never touch anything that is not a plain GET: htmx posts, uploads, the API and auth flows go straight to the
      network, untouched.
   2. The design system and app shell (CSS, fonts, htmx, icons) are cache-first: they are versioned by this file's
      VERSION, and a new deploy ships a new VERSION so the old cache is dropped on activate.
   3. Pages and htmx partials are network-first with a short fallback: when the network fails, a navigation shows
      the offline page; a partial fails as the network would (htmx keeps the current content).
   4. Nothing under /api, /auth, /admin or /static/music is ever cached. */
const VERSION = "optic-shell-v1";
const SHELL = [
  "/static/ds/synapspaces.css",
  "/static/htmx.min.js",
  "/static/app/offline.html",
  "/static/app/icon-192.png",
  "/static/app/icon-512.png",
  "/static/app/manifest.webmanifest",
];
const NEVER = [/^\/api\//, /^\/auth\//, /^\/admin\//, /^\/static\/music\//, /^\/healthz$/, /^\/sw\.js$/];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isShell(url) {
  return url.pathname.startsWith("/static/") && !url.pathname.startsWith("/static/music/");
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (NEVER.some((re) => re.test(url.pathname))) return;

  if (isShell(url)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res.ok) caches.open(VERSION).then((c) => c.put(req, res.clone()));
        return res;
      }))
    );
    return;
  }

  // pages and partials: network first; a failed navigation shows the offline page
  event.respondWith(
    fetch(req).catch(() => {
      if (req.mode === "navigate") return caches.match("/static/app/offline.html");
      return Response.error();
    })
  );
});
