// ExploreSuriname Service Worker
const CACHE = 'exploresr-v3';
const TWV = 'b85e1057';
const PRECACHE = ['/', '/tailwind.css?v=' + TWV, '/favicon.ico', '/favicon.svg', '/offline.html',
                  '/fonts/playfair-latin-var.woff2', '/fonts/inter-latin-var.woff2'];
const LIVE_PAGES = new Set(['/currency.html', '/flights.html', '/conditions.html', '/news.html', '/daily-notices.html', '/events.html']);

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const ks = await caches.keys();
    await Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)));
    // drop superseded tailwind.css versions so only the current one remains
    const c = await caches.open(CACHE);
    for (const req of await c.keys()) {
      const cu = new URL(req.url);
      if (cu.pathname === '/tailwind.css' && cu.search !== '?v=' + TWV) await c.delete(req);
    }
  })());
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  const sameOrigin = u.origin === location.origin;
  const isFont = u.hostname === 'fonts.googleapis.com' || u.hostname === 'fonts.gstatic.com';
  if (!sameOrigin && !isFont) return;

  // Network-first for live-data pages (currency, flights, tides, news)
  if (sameOrigin && u.pathname.startsWith('/data/')) {
    // network-first for live data JSON
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    return;
  }
  if (sameOrigin && LIVE_PAGES.has(u.pathname)) {
    e.respondWith(
      fetch(e.request)
        .then(r => { caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; })
        .catch(() => caches.match(e.request).then(r => r || caches.match('/offline.html')))
    );
    return;
  }

  // Cache-first for static assets (CSS, JS, images, fonts, icons).
  // tailwind.css special case: if the exact ?v= misses (version just bumped),
  // serve the previous version instantly (ignoreSearch) so first paint never
  // blocks on the network; the background fetch caches the new version.
  if (u.pathname.match(/\.(css|js|svg|webp|png|jpg|ico|woff2?)$/) || isFont) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const network = fetch(e.request).then(r => {
          caches.open(CACHE).then(c => c.put(e.request, r.clone()));
          return r;
        });
        if (cached) return cached;
        if (u.pathname === '/tailwind.css')
          return caches.match('/tailwind.css', {ignoreSearch: true}).then(stale => stale || network);
        return network;
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
