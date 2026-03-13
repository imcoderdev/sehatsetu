const CACHE_NAME = 'sehatsetu-v2';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/css/styles.css',
    '/js/app.js',
    '/js/offline-db.js',
    '/js/sync.js',
    '/asha/intake.html',
    '/asha/queue.html',
    '/doctor/login.html',
    '/doctor/dashboard.html',
    '/pharmacy/login.html',
    '/pharmacy/dashboard.html',
    '/manifest.json'
];

// Install — cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate — clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys
                .filter(key => key !== CACHE_NAME)
                .map(key => caches.delete(key))
            )
        ).then(() => self.clients.claim())
    );
});

// Fetch — network first, fallback to cache
self.addEventListener('fetch', event => {
    // Skip non-GET and API requests
    if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then(response => {
                const clone = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});
