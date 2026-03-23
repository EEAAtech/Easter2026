const CACHE_NAME = 'choir-app-v4'; // Incremented version
const ASSETS_TO_CACHE = [
  './index.htm',
  './MuXml.htm',
  './Lyrics.htm'
];

// Install Event
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Fetch Event
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((response) => {
      // 1. Return from cache if available
      if (response) {
        return response;
      }

      // 2. Network fetch and dynamic caching for music/data files
      return fetch(event.request).then((networkResponse) => {
        const url = event.request.url;
        const cacheableExtensions = ['.xml', '.txt', '.pdf', '.mp3', '.m4a'];
        
        const shouldCache = cacheableExtensions.some(ext => url.toLowerCase().endsWith(ext)) || 
                           url.includes('.xml') || url.includes('.txt');

        if (shouldCache && networkResponse.ok) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      }).catch(() => {
        // Offline and not in cache
      });
    })
  );
});

// Activate Event
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    })
  );
});