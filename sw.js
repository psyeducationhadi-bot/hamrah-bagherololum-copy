/**
 * Service Worker: Hamrah Bagherololum (PWA & Android TWA)
 * Strategy: Strict Network-First for CMS/Dynamic Data & HTML Navigation
 * Cache-First with Network Fallback for Static Assets (Images, Fonts, Stylesheets, Scripts)
 * Fallback: Persian RTL offline.html on navigation network failure
 */

const CACHE_NAME = 'hamrah-bagherololum-v1';
const OFFLINE_URL = './offline.html';

// Static assets pre-cached during service worker installation
const PRECACHE_URLS = [
  './offline.html',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

// 1. Installation: pre-cache static assets and skip waiting for immediate activation
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch((err) => {
        console.warn('[SW] Pre-cache partial warning:', err);
      });
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

// 2. Activation: purge stale cache versions and immediately claim clients
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// 3. Fetch interceptor: Strict Network-First for Dynamic Data & Navigation; Cache-First for Static Assets
self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Only handle HTTP/HTTPS GET requests
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  // Ignore unsupported protocols (e.g., chrome-extension:)
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    return;
  }

  // A. Navigation requests (HTML documents)
  // Strict Network-First with cache: 'no-store' to guarantee instant CMS freshness
  const isNavigation = request.mode === 'navigate' ||
                       request.destination === 'document' ||
                       (request.headers.get('accept') && request.headers.get('accept').includes('text/html'));

  if (isNavigation) {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .then((networkResponse) => {
          return networkResponse;
        })
        .catch(async (error) => {
          console.warn('[SW] Navigation failed, serving offline fallback:', error);
          const cache = await caches.open(CACHE_NAME);
          const cachedOffline = await cache.match(OFFLINE_URL) ||
                                await cache.match('./offline.html') ||
                                await cache.match('offline.html');
          if (cachedOffline) {
            return cachedOffline;
          }
          return new Response(
            '<!DOCTYPE html><html lang="fa-IR" dir="rtl"><head><meta charset="utf-8"><title>ارتباط با اینترنت برقرار نیست</title></head><body style="background:#0f172a;color:#fff;font-family:sans-serif;text-align:center;padding:2rem;"><h1>ارتباط با اینترنت برقرار نیست</h1><p>دستگاه شما آفلاین است. لطفاً اتصال را بررسی و مجدداً تلاش کنید.</p><button onclick="window.location.reload()">تلاش مجدد</button></body></html>',
            {
              status: 503,
              headers: { 'Content-Type': 'text/html; charset=utf-8' }
            }
          );
        })
    );
    return;
  }

  // B. Static assets evaluation (images, fonts, stylesheets, scripts)
  // Checks destination and file extension to prevent static assets on workers.dev origin from being hijacked
  const isStaticAsset = request.destination === 'image' ||
                        request.destination === 'style' ||
                        request.destination === 'font' ||
                        request.destination === 'script' ||
                        /\.(png|jpe?g|gif|svg|ico|webp|css|woff2?|ttf|js)$/i.test(url.pathname);

  // C. Dynamic data requests (db.json, /api/, and non-static Cloudflare Workers endpoints)
  // Strict Network-First (cache: 'no-store') — ensures live updates from Admin Panel
  const isDynamicData = !isStaticAsset && (
                        url.pathname.endsWith('.json') ||
                        url.pathname.includes('/api/') ||
                        url.pathname.includes('db.json') ||
                        url.hostname.includes('workers.dev')
  );

  if (isDynamicData) {
    event.respondWith(
      fetch(request, { cache: 'no-store' }).catch((error) => {
        console.warn('[SW] Dynamic data fetch failed:', error);
        return new Response(
          JSON.stringify({ error: 'Network unavailable', offline: true }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
          }
        );
      })
    );
    return;
  }

  // D. Static assets (images, icons, fonts, CSS, JS)
  // Cache-First with Network Fallback and dynamic caching
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && (networkResponse.type === 'basic' || networkResponse.type === 'cors')) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return networkResponse;
      });
    }).catch(() => {
      // Offline fallback: check relative pre-cached paths or return 408
      return caches.match('.' + url.pathname)
        .then((relMatch) => relMatch || caches.match(url.pathname))
        .then((fallback) => fallback || new Response('', { status: 408 }));
    })
  );
});
