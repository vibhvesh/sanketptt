// offline shell cache; network-first so updates on GitHub Pages show up immediately
var C = 'superptt-v2', F = ['./', 'index.html', 'app.js', 'superptt.js', 'manifest.json', 'icon.svg', 'https://unpkg.com/mqtt@5/dist/mqtt.min.js'];
self.addEventListener('install', function (e) { e.waitUntil(caches.open(C).then(function (c) { return c.addAll(F); }).catch(function () {})); self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET' || e.request.url.indexOf('/api/') >= 0) return;
  e.respondWith(fetch(e.request).then(function (r) { var cp = r.clone(); caches.open(C).then(function (c) { c.put(e.request, cp); }); return r; })
    .catch(function () { return caches.match(e.request); }));
});
