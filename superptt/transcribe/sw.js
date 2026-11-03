// offline shell cache, network-first (Whisper model files are cached by transformers.js itself)
var C = 'sptt-transcribe-v1', F = ['./', 'index.html', 'transcribe.js', 'whisper-worker.js', '../superptt.js', 'manifest.json', 'icon.svg', 'https://unpkg.com/mqtt@5/dist/mqtt.min.js'];
self.addEventListener('install', function (e) { e.waitUntil(caches.open(C).then(function (c) { return c.addAll(F); }).catch(function () {})); self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (e) {
  var u = e.request.url;
  if (e.request.method !== 'GET' || u.indexOf('/api/') >= 0 || u.indexOf('/rec/') >= 0 || u.indexOf('huggingface') >= 0 || u.indexOf(self.location.origin) !== 0 && u.indexOf('unpkg.com') < 0) return;
  e.respondWith(fetch(e.request).then(function (r) { var cp = r.clone(); caches.open(C).then(function (c) { c.put(e.request, cp); }); return r; })
    .catch(function () { return caches.match(e.request); }));
});
