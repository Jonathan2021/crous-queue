# ADR-0003 — small same-origin browser shell

Accepted 2026-10-07. The UI remains FastAPI/Jinja server-rendered. A small native JavaScript module handles favorites, JSON writes, retries and clock expiry; HTMX would add little to these stateful flows, so it is omitted. No third-party CDN, font, map, geolocation permission or analytics call. The service worker caches only static assets and an offline explanatory page; API responses and writes are never cached or queued.

The initial national list is paginated in HTML and JSON. Favorites are namespaced browser-local venue IDs. A pending contribution keeps the original payload/key in session storage for a deliberate retry after a lost response. Clock expiry derives from the server UTC timestamp plus elapsed browser time; a stale page never keeps a 15-minute estimate alive.

Rendered raster PWA icons are exports of the repository SVG. Browser tests isolate transport interception from service-worker routing and separately verify offline navigation through the actual service worker. Revisit HTMX or a frontend framework only when demonstrated UI complexity warrants it.
