// Minimal service worker for munro.games — its presence (with a fetch handler)
// is what makes the site an installable PWA, so Android mints a real WebAPK
// (clean icon, no Chrome badge / white border) instead of a bookmark shortcut.
const CACHE = 'munro-games-v1';
const CORE = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/assets/mascot-lockup.png',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/apple-touch-icon.png',
  '/icons/favicon.ico',
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).catch(() => {}));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Only handle this site's own files — leave play.munro.games, fonts, etc. alone.
  if (url.origin !== self.location.origin) return;

  // Network-first for page navigations so the showcase never serves stale cards.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req).then((r) => r || caches.match('/index.html')))
    );
    return;
  }

  // Cache-first for static same-origin assets (icons, thumbnails, manifest).
  e.respondWith(
    caches.match(req).then((hit) =>
      hit ||
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => hit)
    )
  );
});
