const CACHE_NAME = 'smc-choir-v1'; // Incremented version
const CORE_ASSETS = [
  './',
  './index.htm',
  './MuXml.htm',
  './Lyrics.htm'
];

// Install Event: Pre-cache the main application shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(CORE_ASSETS);
    })
  );
  self.skipWaiting();
});

// Fetch Event
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  const isCoreAsset = CORE_ASSETS.some(asset => event.request.url.endsWith(asset.replace('./', '')));

  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((cachedResponse) => {
      
      // Strategy 1: Stale-While-Revalidate for Core Assets (index, MuXml, etc.)
      // This makes the app load INSTANTLY from cache, then updates it in background.
      if (isCoreAsset) {
        const fetchPromise = fetch(event.request).then((networkResponse) => {
          if (networkResponse.ok) {
            const cacheCopy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cacheCopy));
          }
          return networkResponse;
        }).catch(() => {
          // If network fails, we already have the cachedResponse which will be returned below
        });
        
        return cachedResponse || fetchPromise;
      }

      // Strategy 2: Cache-First for Music Assets (PDFs, MP3s, M4As)
      // Once these are downloaded, they never change, so we serve from cache always.
      if (cachedResponse) {
        return cachedResponse;
      }

      // Strategy 3: Network-First for everything else
      return fetch(event.request).then((networkResponse) => {
        const cacheableExtensions = ['.xml', '.txt', '.pdf', '.mp3', '.m4a'];
        const shouldCache = cacheableExtensions.some(ext => url.pathname.toLowerCase().endsWith(ext));

        if (shouldCache && networkResponse.ok) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      }).catch(() => {
        // Truly offline and asset not in cache
        console.log('Offline: Resource not found', url.pathname);
      });
    })
  );
});

// Activate Event: Clean up old versions
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    })
  );
  // Ensure the new service worker takes control immediately
  self.clients.claim();
});