/* PAXIS AI service worker.
 *
 * Exists mainly so the app is installable - browsers only offer the install
 * prompt to a page controlled by a worker with a fetch handler. It is
 * deliberately conservative: only same-origin GETs are touched, so API calls,
 * the chat's server-sent event stream and anything cross-origin pass straight
 * through to the network untouched.
 */

const CACHE = 'paxis-shell-v1';

const SHELL = [
  '/',
  '/paxis-icon.svg',
  '/site.webmanifest',
  '/favicon-32x32.png',
  '/favicon-16x16.png',
  '/apple-touch-icon.png',
  '/icon-192.png',
  '/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      // A single missing file must not fail the whole install.
      .then((cache) => Promise.allSettled(SHELL.map((url) => cache.add(url))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // Django API, fonts, etc.
  if (url.pathname.startsWith('/api/')) return;

  // Navigations: always try the network so a deploy is picked up immediately,
  // and fall back to the cached shell only when offline.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/').then((cached) => cached || Response.error())),
    );
    return;
  }

  // Static assets: serve from cache when present, refresh in the background.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.ok && response.type === 'basic') {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
