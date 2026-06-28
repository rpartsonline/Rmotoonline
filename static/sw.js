// Minimalni service worker – potreben, da je aplikacijo mogoče namestiti (PWA).
// Namenoma NE predpomnimo strani z naročili (da so vedno sveže);
// service worker samo omogoči namestitev ikone na napravo.

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (e) => {
  // Pustimo brskalniku, da naloži vse normalno (vedno sveži podatki).
  return;
});
