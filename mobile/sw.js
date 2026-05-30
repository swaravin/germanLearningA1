const CACHE = "de-learn-v12";
const ASSETS = [
  "./",
  "./index.html",
  "./css/app.css",
  "./js/app.js",
  "./manifest.json",
  "./data/levels.json",
  "./data/levels/a1/vocabulary.json",
  "./data/levels/a1/custom_vocabulary.json",
  "./data/levels/a2/vocabulary.json",
  "./data/levels/a2/custom_vocabulary.json",
  "./data/levels/c1/vocabulary.json",
  "./data/levels/c1/custom_vocabulary.json",
];

function isNetworkFirst(url) {
  const path = url.pathname;
  return (
    path.endsWith("/") ||
    path.endsWith("/index.html") ||
    path.endsWith("/js/app.js") ||
    path.endsWith("/css/app.css") ||
    path.endsWith("/data/levels.json")
  );
}

function cacheResponse(request, response) {
  if (response && response.status === 200) {
    const copy = response.clone();
    caches.open(CACHE).then((cache) => cache.put(request, copy));
  }
  return response;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  if (!url.origin.startsWith(self.location.origin)) return;

  if (isNetworkFirst(url)) {
    event.respondWith(
      fetch(event.request)
        .then((resp) => cacheResponse(event.request, resp))
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request)
        .then((resp) => cacheResponse(event.request, resp))
        .catch(() => cached);
      return cached || network;
    })
  );
});
