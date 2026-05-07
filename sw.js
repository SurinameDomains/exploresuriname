// ExploreSuriname Service Worker
const CACHE = 'exploresr-v1';
const PRECACHE = ['/', '/tailwind.css', '/favicon.svg', '/offline.html'];
const LIVE_PAGES = new Set(['/currency.html', '/flights.html', '/conditions.html', '/news.html']);

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  const sameOrigin = u.origin === location.origin;
  const isFont = u.hostname === 'fonts.googleapis.com' || u.hostname === 'fonts.gstatic.com';
  if (!sameOrigin && !isFont) return;

  // Network-first for live-data pages (currency, flights, tides, news)
  if (sameOrigin && LIVE_PAGES.has(u.pathname)) {
    e.respondWith(
      fetch(e.request)
        .then(r => { caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; })
        .catch(() => caches.match(e.request).then(r => r || caches.match('/offline.html')))
    );
    return;
  }

  // Cache-first for static assets (CSS, JS, images, fonts, icons)
  if (u.pathname.match(/\.(css|js|svg|webp|png|jpg|ico|woff2?)$/) || isFont) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const network = fetch(e.request).then(r => {
          caches.open(CACHE).then(c => c.put(e.request, r.clone()));
          return r;
        });
        return cached || network;
      })
    );
    return;
  }

  // Stale-while-revalidate for HTML pages
  e.respondWith(
    caches.match(e.request).then(cached => {
      const network = fetch(e.request)
        .then(r => { caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; })
        .catch(() => cached || caches.match('/offline.html'));
      return cached || network;
    })
  );
});
