const PREFIX = 'cq-shell-';
const CACHE = PREFIX + '__ASSET_REVISION__';
const ASSETS = ['/static/app.css', '/static/app.js', '/static/icon.svg', '/static/icon-192.png', '/static/icon-512.png', '/static/manifest.webmanifest', '/offline'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith(PREFIX) && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return; // Never cache or queue writes.
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/offline')));
  } else if (url.pathname.startsWith('/static/')) {
    // Fresh while online; a deliberate shell fallback when offline.
    event.respondWith(fetch(event.request).then(async response => {
      if (response.ok) {
        const cache = await caches.open(CACHE);
        await cache.put(event.request, response.clone());
      }
      return response;
    }).catch(() => caches.match(event.request)));
  }
});
