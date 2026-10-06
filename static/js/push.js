/* Potisna obvestila + zvočni pisk.

   Obvestila je treba enkrat dovoliti. Brskalniki dovoljenja ne dajo brez
   uporabnikovega klika, zato pokažemo gumb in ne vprašamo samodejno.

   Na iPhonu obvestila delujejo le, če je aplikacija dodana na začetni zaslon
   (Deli → Dodaj na začetni zaslon). V Safariju kot navadna stran ne delujejo —
   tak uporabnik dobi namig, kaj naj naredi. */
(function () {
  "use strict";

  const Push = {};

  const podprto = ("serviceWorker" in navigator) &&
                  ("PushManager" in window) &&
                  ("Notification" in window);

  const jeIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const namescen = window.matchMedia("(display-mode: standalone)").matches ||
                   window.navigator.standalone === true;

  function b64ToUint8(base64) {
    const pad = "=".repeat((4 - base64.length % 4) % 4);
    const s = (base64 + pad).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(s);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  // ── Pisk ───────────────────────────────────────────────────────────────────
  // Zvok naredimo sproti, da ni treba nalagati datoteke. Brskalnik dovoli
  // predvajanje šele po prvem uporabnikovem kliku – zato zvok pripravimo takrat.
  let ac = null;
  function pripraviZvok() {
    if (ac) return;
    try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {}
  }
  document.addEventListener("click", pripraviZvok, { once: true });
  document.addEventListener("touchstart", pripraviZvok, { once: true });

  Push.pisk = function () {
    if (!ac) return;
    try {
      if (ac.state === "suspended") ac.resume();
      const zdaj = ac.currentTime;
      // Dva kratka tona – prepoznaven, a ne nadležen
      [[880, 0], [1175, 0.13]].forEach(function (par) {
        const o = ac.createOscillator(), g = ac.createGain();
        o.type = "sine";
        o.frequency.value = par[0];
        g.gain.setValueAtTime(0.0001, zdaj + par[1]);
        g.gain.exponentialRampToValueAtTime(0.22, zdaj + par[1] + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, zdaj + par[1] + 0.12);
        o.connect(g); g.connect(ac.destination);
        o.start(zdaj + par[1]); o.stop(zdaj + par[1] + 0.14);
      });
    } catch (e) {}
  };

  // ── Naročanje na obvestila ────────────────────────────────────────────────
  Push.stanje = function () {
    if (!podprto) return jeIOS && !namescen ? "ios-namesti" : "ni-podprto";
    if (Notification.permission === "granted") return "vklopljeno";
    if (Notification.permission === "denied") return "zavrnjeno";
    return "vprasaj";
  };

  Push.vklopi = async function () {
    if (!podprto) return { ok: false, razlog: Push.stanje() };
    try {
      const dovoljenje = await Notification.requestPermission();
      if (dovoljenje !== "granted") return { ok: false, razlog: "zavrnjeno" };

      const reg = await navigator.serviceWorker.register("/static/push-sw.js",
                                                         { scope: "/static/" });
      await navigator.serviceWorker.ready;

      const r = await fetch("/push/kljuc");
      const d = await r.json();
      if (!d.key) return { ok: false, razlog: "ni-kljuca" };

      let narocnina = await reg.pushManager.getSubscription();
      if (!narocnina) {
        narocnina = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: b64ToUint8(d.key),
        });
      }

      const o = narocnina.toJSON();
      const odgovor = await fetch("/push/narocilo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: o.endpoint, keys: o.keys }),
      });
      const rez = await odgovor.json();
      return rez.ok ? { ok: true } : { ok: false, razlog: "streznik" };
    } catch (e) {
      return { ok: false, razlog: String(e && e.message || e) };
    }
  };

  // Če je dovoljenje že dano, poskrbimo, da je naprava zapisana tudi
  // po menjavi naprave ali brskalnika – tiho, brez spraševanja.
  Push.osveziTiho = async function () {
    if (!podprto || Notification.permission !== "granted") return;
    try { await Push.vklopi(); } catch (e) {}
  };

  // ── Značka na ikoni aplikacije ────────────────────────────────────────────
  // Deluje, ko je aplikacija nameščena na začetni zaslon. V navadnem zavihku
  // brskalnika je to tiho brez učinka.
  Push.znacka = function (n) {
    try {
      if (n > 0) {
        if (navigator.setAppBadge) navigator.setAppBadge(n);
      } else {
        if (navigator.clearAppBadge) navigator.clearAppBadge();
        else if (navigator.setAppBadge) navigator.setAppBadge(0);
      }
    } catch (e) {}
  };

  /* Prebere pravo število neprebranih in po njem uskladi oblaček IN značko
     na ikoni. Kličemo takoj, ko uporabnik sporočila prebere – da oblaček
     izgine brez čakanja na naslednje preverjanje. */
  Push.osveziNeprebrano = function () {
    return fetch("/klepet/api/neprebrano", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var n = (d && d.count) || 0;
        var oblacek = document.getElementById("chat-badge");
        var stevilo = document.getElementById("chat-badge-count");
        if (oblacek) oblacek.style.display = n > 0 ? "" : "none";
        if (stevilo && n > 0) stevilo.textContent = n;
        Push.znacka(n);
        return n;
      })
      .catch(function () { return -1; });
  };

  window.BartogPush = Push;

  // ── Vrstica z vabilom ─────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    Push.osveziTiho();

    const stanje = Push.stanje();
    if (stanje !== "vprasaj" && stanje !== "ios-namesti") return;

    // Če je uporabnik vabilo že zaprl, ga ta mesec ne silimo več
    try {
      if (localStorage.getItem("push_skrij") === "1") return;
    } catch (e) {}

    const vrstica = document.createElement("div");
    vrstica.className = "push-vabilo";
    vrstica.innerHTML = stanje === "ios-namesti"
      ? '<i class="bi bi-phone me-2"></i><span>Za obvestila na iPhonu dodajte aplikacijo na '
        + 'začetni zaslon: <b>Deli</b> → <b>Dodaj na začetni zaslon</b>.</span>'
        + '<button type="button" class="btn btn-sm btn-light ms-auto" data-zapri>Razumem</button>'
      : '<i class="bi bi-bell me-2"></i><span>Želite obvestilo na telefon, ko dobite novo sporočilo?</span>'
        + '<button type="button" class="btn btn-sm btn-light ms-auto" data-vklopi>Vklopi</button>'
        + '<button type="button" class="btn btn-sm btn-outline-light" data-zapri>Ne, hvala</button>';
    document.body.appendChild(vrstica);

    vrstica.addEventListener("click", async function (e) {
      if (e.target.closest("[data-zapri]")) {
        try { localStorage.setItem("push_skrij", "1"); } catch (err) {}
        vrstica.remove();
        return;
      }
      if (e.target.closest("[data-vklopi]")) {
        const gumb = e.target.closest("[data-vklopi]");
        gumb.disabled = true;
        gumb.textContent = "Vklapljam…";
        const rez = await Push.vklopi();
        if (rez.ok) {
          pripraviZvok();
          Push.pisk();
          vrstica.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>'
            + '<span>Obvestila so vklopljena.</span>';
          setTimeout(function () { vrstica.remove(); }, 2500);
        } else {
          vrstica.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>'
            + '<span>Obvestil ni bilo mogoče vklopiti. Preverite nastavitve brskalnika.</span>'
            + '<button type="button" class="btn btn-sm btn-light ms-auto" data-zapri>Zapri</button>';
        }
      }
    });
  });
})();
