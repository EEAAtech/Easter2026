const CACHE_NAME = 'choir-app-v1'; // Incrementing version to force update
const ASSETS_TO_CACHE = [
  './index.htm',
  './MuXml.htm',
  './Lyrics.htm'
];

// Install Event: Cache the application shells
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Fetch Event: The "Traffic Controller"
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((response) => {
      // 1. If it's a core HTML file (like MuXml.htm?file=...), return it from cache
      if (response) {
        return response;
      }

      // 2. If not in cache, try the network
      return fetch(event.request).then((networkResponse) => {
        // Optional: Cache music files (.xml, .txt) on-the-fly as they are downloaded
        if (event.request.url.includes('.xml') || event.request.url.includes('.txt')) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      }).catch(() => {
        // 3. Fallback: If network fails and it's not in cache, we are truly offline
        console.log('Resource not available offline:', event.request.url);
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
});