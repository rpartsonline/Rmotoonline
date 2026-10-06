/* Delavec za potisna obvestila.

   Namenoma ločen od glavnega sw.js, ki skrbi za namestitev aplikacije na
   telefon in predpomnjenje. Tako se ti dve stvari ne moreta zmotiti med sabo. */

self.addEventListener("install", function () { self.skipWaiting(); });
self.addEventListener("activate", function (e) { e.waitUntil(self.clients.claim()); });

self.addEventListener("push", function (event) {
  var d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) {}

  var naslov = d.title || "Bartog Ajdovščina";
  var moznosti = {
    body:  d.body || "Novo sporočilo",
    icon:  "/static/img/icons/icon-192.png",
    badge: "/static/img/icons/favicon-32.png",
    tag:   d.tag || "klepet",
    renotify: true,                    // zapiskaj tudi, če je staro še odprto
    vibrate: [120, 60, 120],
    data: { url: d.url || "/klepet/" }
  };
  event.waitUntil(self.registration.showNotification(naslov, moznosti));
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var cilj = (event.notification.data && event.notification.data.url) || "/klepet/";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true })
      .then(function (seznam) {
        // Če je aplikacija že odprta, jo samo preusmerimo in postavimo v ospredje
        for (var i = 0; i < seznam.length; i++) {
          var c = seznam[i];
          if ("focus" in c) {
            if ("navigate" in c) { try { c.navigate(cilj); } catch (e) {} }
            return c.focus();
          }
        }
        return self.clients.openWindow(cilj);
      })
  );
});
