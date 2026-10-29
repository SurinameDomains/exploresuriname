// ExploreSuriname Service Worker
const CACHE = 'exploresr-v14';
const TWV = '9d31e8f1';
const PRECACHE = ['/', '/tailwind.css?v=' + TWV, '/favicon.ico', '/favicon.svg', '/offline.html',
                  '/fonts/newsreader-latin-var.woff2', '/fonts/instrument-latin-var.woff2'];
const LIVE_PAGES = new Set(['/currency', '/flights', '/conditions', '/news', '/daily-notices', '/events',
                            '/currency.html', '/flights.html', '/conditions.html', '/news.html', '/daily-notices.html', '/events.html']);

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

// Store a copy of a good response. The copy is taken right away, before the
// response is handed to the page; cloning later fails ("body already used"),
// which is why nothing but the precache was ever stored up to v12. Errors,
// 404s and redirects are never stored, so a missing file cannot stick.
function keep(req, r) {
  if (r && r.ok && !r.redirected) {
    const copy = r.clone();
    caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
  }
  return r;
}

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
        .then(r => keep(e.request, r))
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
        const network = fetch(e.request).then(r => keep(e.request, r));
        if (cached) return cached;
        if (u.pathname === '/tailwind.css')
          return caches.match('/tailwind.css', {ignoreSearch: true}).then(stale => stale || network);
        return network;
      })
    );
    return;
  }

  // Network-first for HTML pages: always serve the freshest page when online,
  // fall back to cache only when the network is unavailable. This stops the
  // service worker from trapping visitors on a stale build after a deploy.
  e.respondWith(
    fetch(e.request)
      .then(r => keep(e.request, r))
      .catch(() => caches.match(e.request).then(cached => cached || caches.match('/offline.html')))
  );
});

// Web Push (morning rain heads-up, 29 Oct 2026). Payload JSON: {title, body, url, tag}.
self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = {}; }
  e.waitUntil(self.registration.showNotification(d.title || 'Explore Suriname', {
    body: d.body || '', icon: '/icons/icon-192.png', tag: d.tag || 'esr', data: { url: d.url || '/' }
  }));
});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  let url = self.location.origin + '/';
  try {
    const u = new URL((e.notification.data && e.notification.data.url) || '/', self.location.origin);
    if (u.origin === self.location.origin) url = u.href;   // only open our own pages
  } catch (err) {}
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) if (c.url === url && 'focus' in c) return c.focus();
    return self.clients.openWindow(url);
  }));
});
