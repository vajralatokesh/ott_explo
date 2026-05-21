/* ============================================================
   PWA SERVICE WORKER
   ============================================================ */
const CACHE_NAME = "ott-explorer-v1";
const OFFLINE_URL = "/static/offline.html";

const ASSETS_TO_CACHE = [
    "/static/css/base.css",
    "/static/css/components.css",
    "/static/css/pages.css",
    "/static/css/toast.css",
    "/static/js/core.js",
    "/static/manifest.json",
    OFFLINE_URL
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    // Only cache GET requests
    if (event.request.method !== "GET") return;

    event.respondWith(
        fetch(event.request)
            .catch(() => {
                return caches.match(event.request)
                    .then((cachedResponse) => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        if (event.request.headers.get("accept").includes("text/html")) {
                            return caches.match(OFFLINE_URL);
                        }
                    });
            })
    );
});
