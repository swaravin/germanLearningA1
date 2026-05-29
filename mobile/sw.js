const CACHE = "de-learn-v9";
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








self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request)
        .then((resp) => {
          if (resp && resp.status === 200 && event.request.url.startsWith(self.location.origin)) {
            const copy = resp.clone();
            caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          }
          return resp;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
