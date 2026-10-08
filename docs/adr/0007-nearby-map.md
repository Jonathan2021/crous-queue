# ADR-0007 — Nearby map without location storage

2026-10-08, Q09. Vendor Leaflet **1.9.4** (upstream stable release; BSD-2-Clause)
in the package, with license, origin URLs and byte hashes. No runtime CDN script.
Map data uses public venue coordinates and the existing `aggregate` and
`hours_state` services on one injected read clock. `map-data` accepts directory
search, type and region only; it never needs the user's coordinates. Limit 2,000
matched venues and report truncation; source coordinates `0,0` stay unlocated
and explicitly listed without a marker; current snapshot is 972. Search fits matching
venues; ordinary pan/keyboard navigation filters the accessible list to the map
viewport. No remote geocoder. The regular server-rendered directory remains usable
without JavaScript or the component. Official source links/status do not depend
on the basemap. Reload button fetches fresh observations; client ticks expire them.

Wait palette: 0 min `#c8edb7`, (0,5] pale yellow-green, (5,10] yellow,
(10,20] orange, >20 `#7f1727`. This is a visual scale for the existing wait median,
not measured occupancy. Always show minutes/age/count/text; conflicting range,
unknown, expired and offline are neutral gray. Completed waits remain separate.
Coincident coordinates have a numbered neutral marker; its keyboard-accessible
popup offers every distinct venue and queue. No pooling at an address. Close
markers at small zoom also remain selectable through their individual list rows.

Default basemap: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, best-effort,
no account, no paid service. Visible copyright/ODbL attribution and map-issue link.
Browser sends its normal User-Agent and origin referrer (`strict-origin-when-cross-origin`),
honors HTTP tile caching, and requests only the visible viewport. No proxy,
service-worker tile cache, prefetch, bulk/offline tile download or cache bypass.
`CQ_MAP_TILES=none` disables external tiles. To replace the provider, review its
terms, add a bounded adapter in `map.js`, update CSP origin and attribution, add
fixtures and document the configuration choice. No arbitrary user tile URL.

Location is requested only on “Autour de moi”. Round immediately to .01 degrees;
keep the approximate center/distance in memory only. No query parameter, log,
cookie or web storage records it. Tiles disclose the displayed area/network IP
to OSM; the UI says so. Denial/unavailability preserves search and manual pan.
Failed tiles leave component coordinates/markers and the full visible list usable.
CSP retains self-hosted scripts/styles and no unsafe-inline/eval; only the exact
OSM image origin is added. Revisit provider capacity/policy before any public launch.

Sources checked 2026-10-08: https://leafletjs.com/download.html and
https://operations.osmfoundation.org/policies/tiles/ . These are provider terms and
component documentation, not evidence of crowding or user adoption.
