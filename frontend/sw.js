/* Yo'l Guard service worker: app-shell offline + Web Push. */
const VER = "yg-v5";
const SHELL = ["./", "index.html", "app.js", "ui.js", "styles.css",
  "manifest.json", "icons/icon-192.png", "icons/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VER).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((ks) => Promise.all(ks.filter((k) => k !== VER).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET") return; // uploads/posts go to network (queue in app.js)
  if (u.pathname.startsWith("/api/")) {
    e.respondWith(fetch(e.request).catch(() => caches.match("index.html")));
    return;
  }
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((r) => {
    const copy = r.clone();
    caches.open(VER).then((c) => c.put(e.request, copy));
    return r;
  }).catch(() => caches.match("index.html"))));
});
self.addEventListener("push", (e) => {
  let d = {title: "Yo'l Guard", body: "", url: "./"};
  try { if (e.data) d = Object.assign(d, e.data.json()); } catch {}
  e.waitUntil(self.registration.showNotification(d.title,
    {body: d.body || "", icon: "icons/icon-192.png", badge: "icons/icon-192.png", data: {url: d.url}}));
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "./";
  e.waitUntil(clients.matchAll({type: "window"}).then((ws) => {
    for (const w of ws) { if ("focus" in w) { w.navigate(url); return w.focus(); } }
    return clients.openWindow(url);
  }));
});
