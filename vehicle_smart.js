/* Pametna polja za vozilo: predlaganje znamke/modela + skeniranje in
   razčlenjevanje VIN. Uporablja se na obrazcu vozila in pri novem naročilu.

   Branje VIN je zgrajeno v štirih plasteh, od najbolj do najmanj zanesljive:
     1) črtna koda / Data Matrix na tablici (100 % točno, teče ves čas)
     2) Google Cloud Vision na več sličicah + glasovanje
     3) Tesseract v brskalniku (rezerva, če ni ključa ali ni povezave)
     4) ročni vnos
   Pred branjem sliko poravnamo po osvetlitvi (odstrani odsev luči/sonca),
   raztegnemo kontrast in izostrimo. */
(function () {
  "use strict";

  const VS = {
    // Oznaka različice. Pokaže se v obrazcu, če brskalnik postreže staro
    // datoteko iz predpomnilnika – takrat je takoj jasno, da ne gre za
    // napako v kodi, ampak za star shranjen js.
    VERZIJA: "2026-10-08-kamera3",
    makes: (window.CAR_MAKES || []),
    apiModels: "",
    apiVin: "",
    _cam: { stream: null, track: null, raf: null, mode: "barcode", modal: null,
            torch: false, zoomCap: null },
    _busy: false,
  };

  // ── Typeahead ───────────────────────────────────────────────────────────
  function attachTypeahead(input, getItems, onPick) {
    if (!input) return;
    const wrap = document.createElement("div");
    wrap.className = "vs-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    const box = document.createElement("div");
    box.className = "vs-suggest";
    box.style.display = "none";
    wrap.appendChild(box);

    let items = [], active = -1;

    function close() { box.style.display = "none"; active = -1; }
    function render(list) {
      items = list;
      if (!list.length) { close(); return; }
      box.innerHTML = list.map((v, i) =>
        `<div class="vs-item${i === active ? " active" : ""}" data-i="${i}">${escapeHtml(v)}</div>`
      ).join("");
      box.style.display = "block";
    }
    function pick(v) {
      input.value = v;
      close();
      if (onPick) onPick(v);
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    async function update() {
      const q = input.value.trim();
      let list = getItems(q);
      if (list && typeof list.then === "function") list = await list;
      render((list || []).slice(0, 8));
    }

    input.addEventListener("input", update);
    input.addEventListener("focus", update);
    input.addEventListener("keydown", (e) => {
      if (box.style.display === "none") return;
      if (e.key === "ArrowDown") { active = Math.min(active + 1, items.length - 1); render(items); e.preventDefault(); }
      else if (e.key === "ArrowUp") { active = Math.max(active - 1, 0); render(items); e.preventDefault(); }
      else if (e.key === "Enter") { if (active >= 0) { pick(items[active]); e.preventDefault(); } }
      else if (e.key === "Escape") { close(); }
    });
    box.addEventListener("mousedown", (e) => {
      const el = e.target.closest(".vs-item");
      if (el) { e.preventDefault(); pick(items[+el.dataset.i]); }
    });
    document.addEventListener("click", (e) => { if (!wrap.contains(e.target)) close(); });
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  }

  // ── VIN: čiščenje, kontrolna številka, ocenjevanje ────────────────────────

  // VIN nima črk I, O, Q – zato jih vedno pretvorimo v števke.
  function vinSubstitute(s) {
    return s.replace(/I/g, "1").replace(/O/g, "0").replace(/Q/g, "0");
  }

  function cleanVin(raw) {
    const s = vinSubstitute((raw || "").toUpperCase().replace(/[^A-Z0-9]/g, ""));
    const m = s.match(/[A-HJ-NPR-Z0-9]{17}/);
    return m ? m[0] : "";
  }

  // Kontrolna številka VIN (ISO 3779, 9. znak). Severnoameriški VIN-i jo imajo
  // vedno, evropski pogosto ne (na 9. mestu je polnilo, npr. „Z"), zato je
  // uporabljamo kot močan namig in NIKOLI kot izločitveni pogoj.
  const VIN_TRANS = { A:1,B:2,C:3,D:4,E:5,F:6,G:7,H:8,J:1,K:2,L:3,M:4,N:5,P:7,R:9,
                      S:2,T:3,U:4,V:5,W:6,X:7,Y:8,Z:9,
                      "0":0,"1":1,"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9 };
  const VIN_WEIGHTS = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2];

  function vinChecksumValid(v) {
    if (!v || v.length !== 17) return false;
    let sum = 0;
    for (let i = 0; i < 17; i++) {
      if (!(v[i] in VIN_TRANS)) return false;
      sum += VIN_TRANS[v[i]] * VIN_WEIGHTS[i];
    }
    const r = sum % 11;
    return v[8] === (r === 10 ? "X" : String(r));
  }

  // Znane predpone proizvajalcev (WMI) – močan namig, da gre res za VIN.
  const KNOWN_WMI = new Set([
    "WVW","WVG","WV1","WV2","WAU","WA1","TRU","WME","W0L","W0V","VXK",
    "WBA","WBS","WBY","4US","5UX","WBX",
    "WDB","WDC","WDD","WDF","W1K","W1N","W1V","W1T","VSA",
    "VF1","VF3","VF7","VF6","VF8","VF9","VR1","VR3","VR7",
    "ZFA","ZFF","ZAR","ZAC","ZAM","ZFC",
    "TMB","TMP","TMK","TMA","TMH",
    "VSS","VSK","VSE","VSX",
    "SB1","SJN","JTD","JTM","JT1","JTE","JHM","JHL","SHH","SHS","NLA",
    "KMH","KNA","KNB","KNE","U5Y","U6Y","KNM","VNK",
    "1C4","SAL","SAJ","SAD","SCA","SCB",
    "YV1","YV4","YS3","YK1",
    "LVS","LGX","LC0","LSV","L6T","LB3",
    "MA1","MA3","MAT","MEE","ML3",
    "3VW","9BW","8AW","93Y","935","936","8A1","9BD",
    "ZDM","ZD4","ZKH","JYA","JS1","JKA","VTT","MLH","VBK",
  ]);

  function vinScore(v) {
    if (!v || v.length !== 17) return -100;
    let s = 0;
    const digits = (v.match(/\d/g) || []).length;
    const letters = 17 - digits;
    if (vinChecksumValid(v)) s += 40;
    if (KNOWN_WMI.has(v.slice(0, 3))) s += 25;
    if (digits >= 3 && digits <= 12) s += 5;
    if (letters >= 5 && letters <= 14) s += 5;
    // 10. znak je leto izdelave – nikoli I, O, Q, U, Z ali 0
    if ("ABCDEFGHJKLMNPRSTVWXY123456789".indexOf(v[9]) >= 0) s += 3;
    // 5 ali več enakih znakov zapored je skoraj zagotovo napaka branja
    if (/(.)\1{4,}/.test(v)) s -= 15;
    return s;
  }

  // „Zaupanja vreden" rezultat – takrat nehamo porabljati Vision poizvedbe.
  function vinConfident(v) {
    return !!v && (vinChecksumValid(v) || KNOWN_WMI.has(v.slice(0, 3)));
  }

  // Iz prepoznanega besedila izlušči najboljšega 17-mestnega kandidata.
  function bestVin(text) {
    const cands = allVins(text);
    if (!cands.length) return "";
    cands.sort((a, b) => vinScore(b) - vinScore(a));
    return cands[0];
  }

  function allVins(text) {
    const out = [];
    const lines = String(text || "").toUpperCase().split(/\r?\n/);
    // Besede z napisov (prometno dovoljenje), ki NISO VIN
    const bad = /IDENTIFIKAC|STEVILKA|ŠTEVILKA|VOZILO|IZDELAVE|PROMETN|DOVOLJENJ|SEDEZ|SEDEŽ/;
    const scan = (str) => {
      const s = vinSubstitute(str.replace(/[^A-Z0-9]/g, ""));
      for (let i = 0; i + 17 <= s.length; i++) {
        const w = s.slice(i, i + 17);
        if (/^[A-HJ-NPR-Z0-9]{17}$/.test(w) && /[A-Z]/.test(w) && /\d/.test(w)) out.push(w);
      }
    };
    for (const ln of lines) { if (!bad.test(ln)) scan(ln); }
    if (!out.length) scan(lines.join(""));
    return [...new Set(out)];
  }

  // ── Obdelava slike ────────────────────────────────────────────────────────
  // Vse spodaj dela na sivinski sliki v Uint8ClampedArray (en bajt na piko).

  function toGray(ctx, w, h) {
    const d = ctx.getImageData(0, 0, w, h).data;
    const g = new Uint8ClampedArray(w * h);
    for (let i = 0, p = 0; p < g.length; i += 4, p++) {
      g[p] = (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]) | 0;
    }
    return g;
  }

  function putGray(ctx, g, w, h) {
    const img = ctx.createImageData(w, h), d = img.data;
    for (let p = 0, i = 0; p < g.length; p++, i += 4) {
      d[i] = d[i + 1] = d[i + 2] = g[p]; d[i + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  }

  // Vsota po pravokotniku (integralna slika) – omogoča hitro lokalno povprečje.
  function integral(g, w, h) {
    const W = w + 1, I = new Float64Array(W * (h + 1));
    for (let y = 0; y < h; y++) {
      let row = 0;
      for (let x = 0; x < w; x++) {
        row += g[y * w + x];
        I[(y + 1) * W + (x + 1)] = I[y * W + (x + 1)] + row;
      }
    }
    return I;
  }

  function boxMean(I, w, h, x, y, r) {
    const x0 = x - r < 0 ? 0 : x - r, y0 = y - r < 0 ? 0 : y - r;
    const x1 = x + r > w - 1 ? w - 1 : x + r, y1 = y + r > h - 1 ? h - 1 : y + r;
    const W = w + 1;
    const s = I[(y1 + 1) * W + (x1 + 1)] - I[y0 * W + (x1 + 1)]
            - I[(y1 + 1) * W + x0] + I[y0 * W + x0];
    return s / ((x1 - x0 + 1) * (y1 - y0 + 1));
  }

  /* Poravnava osvetlitve: vsako piko delimo z lokalnim povprečjem njene okolice.
     S tem izginejo odsevi luči in sonca ter sence – na tablici ostane samo
     razlika med črko in podlago. To je najpomembnejši korak proti bleščanju. */
  function flattenIllumination(g, w, h, radius) {
    const I = integral(g, w, h);
    const out = new Uint8ClampedArray(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const m = boxMean(I, w, h, x, y, radius);
        out[y * w + x] = m > 1 ? (128 * g[y * w + x] / m) : g[y * w + x];
      }
    }
    return out;
  }

  // Raztegne kontrast med 2. in 98. percentilom (odporno na posamezne pike).
  function stretchContrast(g) {
    const hist = new Uint32Array(256);
    for (let p = 0; p < g.length; p++) hist[g[p]]++;
    const lowN = g.length * 0.02, highN = g.length * 0.98;
    let acc = 0, lo = 0, hi = 255;
    for (let v = 0; v < 256; v++) { acc += hist[v]; if (acc >= lowN) { lo = v; break; } }
    acc = 0;
    for (let v = 0; v < 256; v++) { acc += hist[v]; if (acc >= highN) { hi = v; break; } }
    if (hi - lo < 10) return g;
    const k = 255 / (hi - lo);
    const out = new Uint8ClampedArray(g.length);
    for (let p = 0; p < g.length; p++) out[p] = (g[p] - lo) * k;
    return out;
  }

  // Izostritev (unsharp mask) – črke dobijo ostrejši rob.
  function sharpen(g, w, h, amount) {
    const I = integral(g, w, h);
    const out = new Uint8ClampedArray(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const p = y * w + x;
        out[p] = g[p] + amount * (g[p] - boxMean(I, w, h, x, y, 2));
      }
    }
    return out;
  }

  /* Lokalni prag (Bradley) – za Tesseract, ki potrebuje čisto črno-belo sliko.
     Prag se računa za vsako piko posebej, zato osvetljeni del slike ne „poje"
     črk, kot se zgodi pri enotnem pragu čez celo sliko. */
  function adaptiveThreshold(g, w, h, radius, t) {
    const I = integral(g, w, h);
    const out = new Uint8ClampedArray(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const p = y * w + x;
        out[p] = g[p] < boxMean(I, w, h, x, y, radius) * (1 - t) ? 0 : 255;
      }
    }
    return out;
  }

  // ── Zajem sličice iz žive slike ───────────────────────────────────────────

  /* Zajamemo CEL kader, tako kot navaden fotoaparat. Ozek pas je bil potreben
     le, dokler je bral navaden OCR – vizualni model najde šasijsko številko
     kjerkoli na sliki, zato uporabnika ni treba siliti v poravnavanje. */
  const GUIDE_W = 1, GUIDE_H = 1;
  const MAX_OUT_W = 3000;

  /* Med zajemom serije delamo samo poceni stvari (izrez, sivine, ocena ostrine),
     da sličice res sledijo druga drugi. Drago obdelavo opravimo šele na tistih
     nekaj sličicah, ki jih zares pošljemo v branje. */
  /* Poravnana osvetlitev + raztegnjen kontrast + izostritev. Namenoma NE
     binariziramo – Google Vision iz sivinske slike odčita bistveno več. */
  function enhance(f) {
    if (f.prepared) return f.prepared;
    // Isti radij kot pri bistriGray – glej razlago pri flattenRadius().
    let g = flattenIllumination(f.gray, f.w, f.h, flattenRadius(f.w, f.h));
    g = stretchContrast(g);
    g = sharpen(g, f.w, f.h, 0.6);
    f.prepared = g;
    return g;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // ── Branje črtne kode (Code 39 / Data Matrix na tablici) ──────────────────
  // Teče ves čas med odprto kamero. Koda je vedno točna – brez ugibanja črk.

  let _bd = null, _bdTried = false;
  function nativeDetector() {
    if (_bdTried) return _bd;
    _bdTried = true;
    try {
      if ("BarcodeDetector" in window) {
        _bd = new BarcodeDetector({
          formats: ["code_39", "code_128", "data_matrix", "pdf417", "qr_code", "itf"],
        });
      }
    } catch (e) { _bd = null; }
    return _bd;
  }

  let _zx = null, _zxTried = false;
  function zxingReader() {
    if (_zxTried) return _zx;
    _zxTried = true;
    try {
      if (!("ZXing" in window)) return (_zx = null);
      const hints = new Map();
      hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
        ZXing.BarcodeFormat.CODE_39, ZXing.BarcodeFormat.CODE_128,
        ZXing.BarcodeFormat.DATA_MATRIX, ZXing.BarcodeFormat.PDF_417,
        ZXing.BarcodeFormat.QR_CODE, ZXing.BarcodeFormat.ITF,
      ]);
      hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
      _zx = new ZXing.MultiFormatReader();
      _zx.setHints(hints);
    } catch (e) { _zx = null; }
    return _zx;
  }

  async function detectBarcode(canvas) {
    const det = nativeDetector();
    if (det) {
      try {
        const codes = await det.detect(canvas);
        for (const c of (codes || [])) {
          const v = bestVin(c.rawValue) || cleanVin(c.rawValue);
          if (v) return v;
        }
      } catch (e) { /* tiho naprej na ZXing */ }
    }
    const rd = zxingReader();
    if (rd) {
      try {
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const src = new ZXing.RGBLuminanceSource(img.data, canvas.width, canvas.height);
        const bmp = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(src));
        const res = rd.decode(bmp);
        if (res) {
          const v = bestVin(res.getText()) || cleanVin(res.getText());
          if (v) return v;
        }
      } catch (e) { /* kode ni v tej sličici */ }
      finally { try { rd.reset(); } catch (e) {} }
    }
    return "";
  }

  // ── Google Vision ─────────────────────────────────────────────────────────

  // Kateri bralnik je na strežniku. Vizualni model se z odsevi spopade sam,
  // zato mu pošljemo naravno sliko in preskočimo drago obdelavo.
  VS._engine = null;
  async function engineKind() {
    if (VS._engine) return VS._engine;
    try {
      const r = await fetch("/vehicles/api/vin-status");
      const d = await r.json();
      VS._engine = (d && d.engine) || "none";
    } catch (e) { VS._engine = "none"; }
    return VS._engine;
  }

  // mode: "plate" = tablica z VIN (redko besedilo), "document" = prometno
  // dovoljenje (gosto besedilo). Strežnik po tem izbere primernejše branje.
  async function visionRead(jpegs, prior, mode) {
    try {
      const r = await fetch("/vehicles/api/vin-ocr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ images: jpegs, prior: prior || [], mode: mode || "plate" }),
      });
      return await r.json();
    } catch (e) {
      return { ok: false, error: "network" };
    }
  }

  /* Varčna strategija: najprej pošljemo samo najostrejšo sličico. Če je rezultat
     zanesljiv (ujema se kontrolna številka ali poznamo predpono proizvajalca),
     smo porabili eno poizvedbo. Sicer pošljemo še dve in o rezultatu glasujemo –
     odsev se med sličicami premakne, zato se napake ne ponovijo enako.        */
  // ── Tesseract (rezerva v brskalniku) ──────────────────────────────────────

  async function readViaTesseract(frames) {
    if (typeof Tesseract === "undefined") return "";
    const found = [];
    for (const f of frames.slice(0, 2)) {
      const base = enhance(f);
      const radius = Math.max(10, Math.round(f.h / 5));
      for (const t of [0.12, 0.2]) {
        const bw = adaptiveThreshold(base, f.w, f.h, radius, t);
        putGray(f.ctx, bw, f.w, f.h);
        try {
          const { data: { text } } = await Tesseract.recognize(f.canvas, "eng", {
            tessedit_char_whitelist: "ABCDEFGHJKLMNPRSTUVWXYZ0123456789",
            tessedit_pageseg_mode: "7",
          });
          for (const v of allVins(text)) found.push(v);
        } catch (e) { /* naslednji poskus */ }
      }
      if (found.some(vinConfident)) break;
    }
    if (!found.length) return "";
    return voteBest(found);
  }

  // Najpogostejši kandidat; ob izenačenju odloči ocena (kontrolna št., WMI …).
  function voteBest(list) {
    const tally = new Map();
    for (const v of list) tally.set(v, (tally.get(v) || 0) + 1);
    let best = "", bestKey = -1e9;
    for (const [v, n] of tally) {
      const k = n * 100 + vinScore(v);
      if (k > bestKey) { bestKey = k; best = v; }
    }
    return best;
  }

  // ── Fotoaparat ────────────────────────────────────────────────────────────
  /* Namesto žive slike iz brskalnika odpremo kar fotoaparat naprave. Posnetek
     iz kamere telefona je bistveno boljši od video sličice: polna ločljivost,
     prava izostritev in osvetlitev, brez stiskanja in zamegljenosti od premika.
     Prav ta razlika je bila vzrok, da je prilepljena slika delovala, skeniranje
     z živo sliko pa ne. */

  function el(id) { return document.getElementById(id); }

  function nativeCamera() {
    let inp = el("vs-native-cam");
    if (inp) return inp;
    inp = document.createElement("input");
    inp.type = "file";
    inp.id = "vs-native-cam";
    inp.accept = "image/*";
    inp.setAttribute("capture", "environment");   // na telefonu odpre zadnjo kamero
    inp.style.cssText = "position:absolute;left:-9999px;opacity:0;width:1px;height:1px";
    document.body.appendChild(inp);
    inp.addEventListener("change", function () {
      const f = this.files && this.files[0];
      this.value = "";                            // da gre lahko takoj znova
      if (!f) return;
      const cfg = VS._cfg;
      const say = VS._status || function () {};
      if (cfg) readVinFromPhoto(f, cfg, say, VS._decode);
    });
    return inp;
  }

  /* Skupni vhod za vse gumbe „fotografiraj" na vseh straneh.

     Prej je vedno odprl `<input type="file" capture>`. Na telefonu to odpre
     kamero, na RAČUNALNIKU pa samo izbiro datoteke – zato se kamera ni
     odprla. Zdaj na računalniku odpremo spletno kamero.                   */
  function openScanner() {
    /* Vedno najprej kamera v brskalniku – tudi na telefonu.

       Prej smo na telefonu odprli `<input type="file" capture>`. Android
       to prepusti sistemu, sistem pa si zapomni, katero aplikacijo je
       uporabnik enkrat izbral. Če je kdaj izbral upravitelja datotek
       (pri Samsungu „Moje datoteke") in potrdil „Vedno", se odslej ob
       vsakem kliku odpre TA, ne kamera – in tega iz strani ni mogoče
       preglasiti. Kamera v brskalniku se temu povsem izogne.

       Fotoaparat naprave ostane na voljo kot gumb v oknu, ker da na
       telefonu boljšo sliko.                                            */
    VS.photoCamera(
      function (f) {
        shraniVNarocilo(f);                       // slika gre tudi k naročilu
        const cfg = VS._cfg;
        const say = VS._status || function () {};
        if (cfg) readVinFromPhoto(f, cfg, say, VS._decode);
      },
      function () { nativeCamera().click(); }     // uporabnik je izbral datoteko
    );
  }

  /* Posneto sliko pripnemo k naročilu in pokažemo v predogledu.

     Obrazec novega naročila ima skrito polje `vin_photo_store` z imenom
     `order_images` – kar je v njem, se odda skupaj z naročilom. Prej je to
     delala koda v predlogi; tu jo opravimo sami, da zadošča zamenjati
     samo to datoteko.                                                    */
  function shraniVNarocilo(file) {
    const store = el("vin_photo_store");
    if (store) {
      try {
        const dt = new DataTransfer();
        dt.items.add(file);
        store.files = dt.files;
      } catch (e) { /* starejši brskalnik – slika se pač ne pripne */ }
    }
    const predogled = el("nv_paste_preview");
    const slika = el("nv_paste_img");
    const ime = el("nv_paste_name");
    if (predogled && slika) {
      try {
        slika.src = URL.createObjectURL(file);
        predogled.style.display = "";
        if (ime) ime.textContent = file.name || "slika";
      } catch (e) {}
    }
  }

  /* ── Navaden fotoaparat za RAČUNALNIK ────────────────────────────────────

     Na telefonu `capture="environment"` odpre kamero naprave in to je
     najboljše, kar lahko dobimo – polna ločljivost, samodejna izostritev.
     Na računalniku pa ta nastavitev ne naredi nič: brskalnik odpre samo
     izbiro datoteke. Zato tu odpremo spletno kamero.

     To NI stari skener: ni branja v živo, ni ozkega okvirja, ni nenehnega
     prepoznavanja. Je samo fotoaparat – slika se posname šele, ko klikneš
     „Posnemi", in gre nato po isti poti kot vsaka druga fotografija.      */

  const NASVET = "Prometno dovoljenje naj zapolni čim večji del okvirja. " +
                 "Drži pri miru in počakaj, da se slika izostri, nato klikni Posnemi.";

  let _tok = null;                       // trenutni tok iz kamere

  function ustaviKamero() {
    if (_tok) {
      try { _tok.getTracks().forEach((t) => t.stop()); } catch (e) {}
      _tok = null;
    }
  }

  function imaKamero() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  function zapriOkno() {
    ustaviKamero();
    const o = el("vs-cam-okno");
    if (o) o.remove();
    document.removeEventListener("keydown", _escHandler);
  }

  function _escHandler(e) { if (e.key === "Escape") zapriOkno(); }

  function narediOkno() {
    const o = document.createElement("div");
    o.id = "vs-cam-okno";
    o.style.cssText =
      "position:fixed;inset:0;z-index:20000;background:#000;" +
      "display:flex;flex-direction:column;align-items:center;justify-content:center";
    o.innerHTML =
      '<video id="vs-cam-video" autoplay playsinline muted ' +
      'style="max-width:100%;max-height:calc(100% - 132px);background:#000"></video>' +
      '<div id="vs-cam-sporocilo" style="color:#fff;font:14px system-ui,sans-serif;' +
      'padding:10px 16px;text-align:center;max-width:620px"></div>' +
      '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;' +
      'justify-content:center;padding:12px 16px 20px">' +
      '  <select id="vs-cam-izbira" style="display:none;padding:9px 12px;border-radius:8px;' +
      'border:0;font:14px system-ui,sans-serif;max-width:240px"></select>' +
      '  <button type="button" id="vs-cam-snemi" style="display:none;padding:14px 30px;border:0;' +
      'border-radius:10px;background:#0d6efd;color:#fff;font:600 17px system-ui,sans-serif;' +
      'cursor:pointer">Posnemi</button>' +
      '  <button type="button" id="vs-cam-znova" style="display:none;padding:14px 24px;border:0;' +
      'border-radius:10px;background:#0d6efd;color:#fff;font:600 16px system-ui,sans-serif;' +
      'cursor:pointer">Poskusi znova</button>' +
      '  <button type="button" id="vs-cam-naprava" style="padding:14px 20px;border:0;' +
      'border-radius:10px;background:#495057;color:#fff;font:15px system-ui,sans-serif;' +
      'cursor:pointer">Fotoaparat naprave</button>' +
      '  <button type="button" id="vs-cam-datoteka" style="padding:14px 20px;border:0;' +
      'border-radius:10px;background:#495057;color:#fff;font:15px system-ui,sans-serif;' +
      'cursor:pointer">Naloži sliko</button>' +
      '  <button type="button" id="vs-cam-prekini" style="padding:14px 20px;border:0;' +
      'border-radius:10px;background:#343a40;color:#fff;font:15px system-ui,sans-serif;' +
      'cursor:pointer">Prekliči</button>' +
      "</div>";
    document.body.appendChild(o);
    document.addEventListener("keydown", _escHandler);
    return o;
  }

  async function zazeniKamero(deviceId) {
    ustaviKamero();
    // Zahtevamo čim višjo ločljivost – drobna šasijska številka potrebuje pike.
    const zelje = {
      audio: false,
      video: deviceId
        ? { deviceId: { exact: deviceId },
            width: { ideal: 3840 }, height: { ideal: 2160 } }
        : { facingMode: { ideal: "environment" },
            width: { ideal: 3840 }, height: { ideal: 2160 } },
    };
    try {
      _tok = await navigator.mediaDevices.getUserMedia(zelje);
    } catch (e) {
      // Brez zadnje kamere (navaden računalnik) vzamemo katerokoli.
      if (e && (e.name === "OverconstrainedError" || e.name === "NotFoundError") && !deviceId) {
        _tok = await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
      } else {
        throw e;
      }
    }
    const v = el("vs-cam-video");
    if (v) { v.srcObject = _tok; try { await v.play(); } catch (e) {} }
    return _tok;
  }

  async function napolniSeznamKamer(izbira) {
    try {
      const naprave = await navigator.mediaDevices.enumerateDevices();
      const kamere = naprave.filter((d) => d.kind === "videoinput");
      if (kamere.length < 2) return;
      izbira.innerHTML = "";
      kamere.forEach((k, i) => {
        const opt = document.createElement("option");
        opt.value = k.deviceId;
        opt.textContent = k.label || "Kamera " + (i + 1);
        izbira.appendChild(opt);
      });
      const aktivna = _tok && _tok.getVideoTracks()[0];
      const nast = aktivna && aktivna.getSettings ? aktivna.getSettings() : null;
      if (nast && nast.deviceId) izbira.value = nast.deviceId;
      izbira.style.display = "";
    } catch (e) { /* seznam ni nujen */ }
  }

  function videoVDatoteko(video) {
    const w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return null;
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    c.getContext("2d").drawImage(video, 0, 0, w, h);
    const dataUrl = c.toDataURL("image/jpeg", 0.95);
    const bin = atob(dataUrl.split(",")[1]);
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    // Ime je tako, da naročilo sliko pozneje prepozna kot prometno/VIN.
    return new File([buf], "prometno-vin-" + Date.now() + ".jpg",
                    { type: "image/jpeg" });
  }

  /* Pojasnilo, zakaj se kamera ni odprla – v človeškem jeziku. */
  function razlogNapake(e) {
    const ime = (e && e.name) || "";
    if (ime === "NotAllowedError" || ime === "SecurityError")
      return { kaj: "Brskalnik nima dovoljenja za kamero.",
               kako: "Klikni ikono levo od naslova strani (ključavnica ali drsnika) → " +
                     "Kamera → Dovoli, nato klikni „Poskusi znova“." };
    if (ime === "NotFoundError" || ime === "OverconstrainedError")
      return { kaj: "Na tej napravi ni najdene nobene kamere.",
               kako: "Na računalniku brez kamere slikaj s telefonom in sliko naloži, " +
                     "ali priključi USB kamero." };
    if (ime === "NotReadableError")
      return { kaj: "Kamero uporablja drug program.",
               kako: "Zapri Teams, Zoom, Skype ali aplikacijo Kamera in klikni „Poskusi znova“." };
    return { kaj: "Kamere ni bilo mogoče odpreti." + (ime ? " (" + ime + ")" : ""),
             kako: "Poskusi znova ali naloži sliko." };
  }

  /* Odpre fotoaparat.
       onFile(datoteka)  – posneta slika
       onNiKamere()      – uporabnik se je ODLOČIL za izbiro datoteke

     Pomembno: ob napaki se okno NE zapre tiho. Prej se je v tem primeru
     odprla izbira datotek in izgledalo je, kot da gumb ne dela oziroma da
     odpira napačno stvar. Zdaj okno ostane in jasno pove, kaj je narobe. */
  VS.photoCamera = async function (onFile, onNiKamere) {
    naredoOknoVarno();
    const sporocilo = el("vs-cam-sporocilo");
    const izbira  = el("vs-cam-izbira");
    const snemi   = el("vs-cam-snemi");
    const znova   = el("vs-cam-znova");
    const naprava = el("vs-cam-naprava");

    const naDatoteko = () => { zapriOkno(); if (onNiKamere) onNiKamere(); };

    el("vs-cam-prekini").addEventListener("click", zapriOkno);
    el("vs-cam-datoteka").addEventListener("click", naDatoteko);

    // Fotoaparat naprave (na telefonu polna kakovost) – vedno na voljo.
    naprava.addEventListener("click", function () {
      zapriOkno();
      nativeCamera().click();
    });

    izbira.addEventListener("change", function () {
      sporocilo.textContent = "Preklapljam …";
      zazeniKamero(this.value)
        .then(() => pokaziZivo())
        .catch((e) => pokaziNapako(e));
    });

    snemi.addEventListener("click", function () {
      const f = videoVDatoteko(el("vs-cam-video"));
      if (!f) { sporocilo.textContent = "Slike ni bilo mogoče posneti. Poskusi znova."; return; }
      zapriOkno();
      if (onFile) onFile(f);
    });

    znova.addEventListener("click", function () { zacni(); });

    function pokaziZivo() {
      sporocilo.innerHTML = NASVET;
      sporocilo.style.color = "#fff";
      snemi.style.display = "";
      znova.style.display = "none";
    }

    function pokaziNapako(e) {
      const r = razlogNapake(e);
      sporocilo.innerHTML = "<b>" + r.kaj + "</b><br>" + r.kako;
      sporocilo.style.color = "#ffd4d4";
      snemi.style.display = "none";
      znova.style.display = "";
    }

    async function zacni() {
      snemi.style.display = "none";
      znova.style.display = "none";
      sporocilo.style.color = "#fff";
      sporocilo.textContent = "Odpiram kamero …";

      if (!imaKamero()) {
        pokaziNapako({ name: "NotFoundError" });
        return;
      }
      if (!window.isSecureContext && location.hostname !== "localhost") {
        sporocilo.innerHTML = "<b>Kamera deluje samo prek varne povezave (https).</b><br>" +
                              "Odpri stran na naslovu, ki se začne s https://";
        sporocilo.style.color = "#ffd4d4";
        znova.style.display = "none";
        return;
      }
      try {
        await zazeniKamero(null);
        pokaziZivo();
        await napolniSeznamKamer(izbira);
      } catch (e) {
        pokaziNapako(e);
      }
    }

    zacni();
  };

  // Staro okno (če je po napaki ostalo) odstranimo, da jih ni več naenkrat.
  function naredoOknoVarno() {
    const star = el("vs-cam-okno");
    if (star) star.remove();
    return narediOkno();
  }

  // Ostanki starega skenerja – da se starejše predloge, ki jih še kličejo,
  // ne sesujejo. Ne delajo ničesar.
  function stopCam() {}
  function captureOCR() { openScanner(); }
  function toggleTorch() {}

  // ── Branje VIN iz naložene fotografije / printscreena ─────────────────────

  // Blago glajenje – odstrani raster, ki nastane pri fotografiranju zaslona
  // (moiré), ne da bi zabrisalo robove črk.
  function denoise(g, w, h) {
    const I = integral(g, w, h);
    const out = new Uint8ClampedArray(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const p = y * w + x;
        out[p] = 0.45 * g[p] + 0.55 * boxMean(I, w, h, x, y, 1);
      }
    }
    return out;
  }

  /* Sivinsko sliko nariše na svoj platno in vrne JPEG. Vsaka različica dobi
     svoje platno, da si različice med sabo ne pobrišejo. */
  function grayToJpeg(g, w, h, quality) {
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    putGray(ctx, g, w, h);
    return c.toDataURL("image/jpeg", quality || 0.95);
  }

  /* BISTRENJE – najpomembnejši korak pri fotografiji s telefona.

     1) Poravnava osvetlitve: vsako piko delimo z lokalnim povprečjem okolice.
        S tem izginejo odsevi luči in sonca ter sence.
     2) Raztegnjen kontrast med 2. in 98. percentilom.
     3) Unsharp mask – robovi črk se izostrijo.

     Namenoma NE binariziramo: tako vizualni model kot Google Vision iz
     sivinske slike odčitata bistveno več kot iz črno-bele.                   */
  /* Radij okna za oceno osvetlitve ozadja.

     Okno mora biti BISTVENO večje od črk – le tako lokalno povprečje oceni
     svetlost podlage in ne črk samih. Če je okno premajhno, povprečje vsebuje
     predvsem črko in deljenje jo izbriše: kontrast se na osvetljenem delu
     celo zniža. Prej se je radij računal iz KRAJŠE stranice, zato je tesen
     izrez vrstice VIN (npr. 420×90) dobil radij 11 – najslabšo možno
     vrednost. Zato merimo po DALJŠI stranici.
     Izmerjeno na preizkusnih slikah: najslabši znak je pri /6 opazno
     razločnejši kot pri /8 ali manj.                                        */
  function flattenRadius(w, h) {
    const r = Math.round(Math.max(w, h) / 6);
    return Math.max(24, Math.min(400, r));
  }

  function bistriGray(gray, w, h, moc) {
    const radius = flattenRadius(w, h);
    let g = denoise(gray, w, h);
    g = flattenIllumination(g, w, h, radius);
    g = stretchContrast(g);
    g = sharpen(g, w, h, moc == null ? 0.9 : moc);
    return g;
  }

  /* Prebere VIN iz datoteke (fotografija, printscreen, prilepljena slika).
     Vrne objekt rezultata ali null. onStatus(html, vrsta) sproti obvešča.
     To je javni vmesnik – uporabljajo ga tudi druge strani. */
  VS.readImageFile = async function (file, onStatus) {
    const say = (m, k) => { if (onStatus) onStatus(m, k || "primary"); };
    say('<i class="bi bi-arrow-repeat"></i> Berem sliko …');

    let bmp;
    try { bmp = await createImageBitmap(file); }
    catch (e) { return { vin: null, badImage: true }; }

    /* Velikost: daljšo stranico omejimo na 2800 px (dovolj podrobnosti, a
       zahteva ostane dovolj majhna). Majhno sliko – npr. printscreen ali
       posnetek z manjšo ločljivostjo – nasprotno POVEČAMO, ker drobnega
       besedila noben bralnik ne prebere zanesljivo. */
    const MAX_SIDE = 2800, MIN_SIDE = 1500;
    const dolga = Math.max(bmp.width, bmp.height);
    let sc = 1;
    if (dolga > MAX_SIDE)      sc = MAX_SIDE / dolga;
    else if (dolga < MIN_SIDE) sc = Math.min(2.5, MIN_SIDE / dolga);

    const w = Math.max(1, Math.round(bmp.width * sc));
    const h = Math.max(1, Math.round(bmp.height * sc));
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(bmp, 0, 0, w, h);

    // 1) Črtna koda na sliki – če je, je rezultat točen, brez ugibanja črk
    try {
      const vin = await detectBarcode(c);
      if (vin) return { vin, source: "koda", valid: vinChecksumValid(vin) };
    } catch (e) {}

    const rawJpeg = c.toDataURL("image/jpeg", 0.92);
    const gray = toGray(ctx, w, h);

    // 2) Zbistrimo. To zdaj delamo za VSAK bralnik, tudi za vizualni model:
    //    zamegljena ali bleščeča slika je težka tudi zanj.
    say('<i class="bi bi-magic"></i> Bistrim sliko …');
    await sleep(0);                     // pusti brskalniku izrisati sporočilo
    let bistro = null, bistroJpeg = null;
    try {
      bistro = bistriGray(gray, w, h, 0.9);
      bistroJpeg = grayToJpeg(bistro, w, h, 0.95);
    } catch (e) { /* ob pomanjkanju pomnilnika beremo naravno sliko */ }

    const frame = { canvas: c, ctx, w, h, gray, prepared: bistro, score: 1, jpeg: null };

    // 3) Prvi krog: zbistrena + naravna slika. Model ju primerja med sabo in
    //    tako potrdi vsak znak.
    say('<i class="bi bi-arrow-repeat"></i> Berem šasijsko številko …');
    const prviKrog = bistroJpeg ? [bistroJpeg, rawJpeg] : [rawJpeg];
    let j = await visionRead(prviKrog, null, "document");
    if (j.ok && j.vin) return j;

    // 4) Drugi krog: močnejše bistrenje. Pomaga pri zelo zamegljenih
    //    posnetkih in pri vtisnjenih (reliefnih) številkah na karoseriji.
    if (!j.ok && (j.error === "no_vin" || j.error === "network") && bistro) {
      say('<i class="bi bi-magic"></i> Ni šlo – poskušam z močnejšim bistrenjem …',
          "warning");
      await sleep(0);
      try {
        const mocno = grayToJpeg(sharpen(stretchContrast(bistro), w, h, 1.6), w, h, 0.95);
        const j2 = await visionRead([mocno, bistroJpeg], null, "plate");
        if (j2.ok && j2.vin) return j2;
        if (j2.error && j2.error !== "no_vin") j = j2;
      } catch (e) { /* gremo naprej na lokalno branje */ }
    }

    // 5) Rezerva: Tesseract v brskalniku
    say(j.error === "daily_limit"
      ? "Dnevna meja branja je dosežena – berem lokalno …"
      : '<i class="bi bi-arrow-repeat"></i> Poskušam še lokalno branje …', "warning");
    const t = await readViaTesseract([frame]);
    if (t) return { vin: t, source: "lokalno", valid: vinChecksumValid(t) };

    // Nič – a je razlog pomemben: brez ključa na strežniku ni pravega bralnika
    return { vin: null,
             unavailable: (j.error === "no_key" || j.error === "daily_limit")
                          ? j.error : null,
             diag: j.diag || null };
  };

  async function readVinFromPhoto(file, cfg, status, decode) {
    const res = await VS.readImageFile(file, status);
    if (res && res.vin) {
      setVinResult(res.vin, cfg, status, res);
      if (decode) decode(res.vin);
      return;
    }
    status("VIN ni prepoznan. Fotografiraj bližje in brez odseva (rahel kot, več svetlobe).", "danger");
  }

  function setVinResult(vin, cfg, status, info) {
    if (cfg && cfg.vin) {
      const e = document.getElementById(cfg.vin);
      if (e) { e.value = vin; e.focus(); }
    }
    info = info || {};
    if (info.source === "koda") {
      status("VIN prebran s črtne kode – točno.", "success");
    } else if (info.valid || vinChecksumValid(vin)) {
      status("VIN prebran, kontrolna številka se ujema.", "success");
    } else {
      status("VIN prebran – natančno preveri vsak znak, nato „Razčleni“.", "warning");
    }
  }

  // ── Glavna inicializacija ─────────────────────────────────────────────────
  // cfg = { make, model, year, vin, engineType, displacement, power,
  //         transmission, status }  (vrednosti so ID-ji elementov)
  VS.init = function (cfg) {
    const $ = (id) => (id ? document.getElementById(id) : null);
    const make = $(cfg.make), model = $(cfg.model);
    let modelCache = [];

    // Znamka – predlaga iz seznama
    attachTypeahead(make, (q) => {
      const lq = q.toLowerCase();
      return VS.makes.filter((m) => m.toLowerCase().includes(lq));
    }, (val) => loadModels(val));

    // Model – predlaga iz baze (vPIC) za izbrano znamko
    attachTypeahead(model, (q) => {
      const lq = q.toLowerCase();
      return modelCache.filter((m) => m.toLowerCase().includes(lq));
    });

    async function loadModels(makeName) {
      modelCache = [];
      if (!makeName || makeName.length < 2 || !VS.apiModels) return;
      try {
        const r = await fetch(VS.apiModels.replace("__MAKE__", encodeURIComponent(makeName)));
        const d = await r.json();
        modelCache = d.models || [];
      } catch (e) { /* tiho */ }
    }
    if (make) make.addEventListener("change", () => loadModels(make.value.trim()));
    if (make && make.value) loadModels(make.value);

    function status(msg, kind) {
      const el2 = $(cfg.status);
      if (!el2) return;
      el2.className = "small mt-2 text-" + (kind || "muted");
      el2.innerHTML = msg;
    }

    function setVal(id, val) { const e = $(id); if (e && val) e.value = val; }
    function setSelect(id, val) {
      const e = $(id); if (!e || !val) return;
      if (e.tagName === "SELECT") {
        if ([...e.options].some((o) => o.value === val)) e.value = val;
      } else { e.value = val; }
    }

    function applyDecode(d) {
      setVal(cfg.make, d.make);
      setVal(cfg.model, d.model);
      if (d.year) setSelect(cfg.year, String(d.year));
      setVal(cfg.displacement, d.displacement);
      setVal(cfg.power, d.power_kw);
      setSelect(cfg.engineType, d.engine_type);
      setSelect(cfg.transmission, d.transmission);
      if (d.make) loadModels(d.make);
    }

    async function decode(vin) {
      if (!VS.apiVin) return;
      status('<i class="bi bi-arrow-repeat"></i> Razčlenjujem VIN…', "primary");
      try {
        const r = await fetch(VS.apiVin.replace("__VIN__", encodeURIComponent(vin)));
        const d = await r.json();
        if (!d.ok) { status("VIN ni bilo mogoče razčleniti (preveri povezavo).", "danger"); return; }
        applyDecode(d);
        const got = [d.make, d.model, d.year].filter(Boolean).join(" ");
        status(got
          ? '<i class="bi bi-check-circle text-success"></i> Prepoznano: ' + escapeHtml(got)
          : "VIN razčlenjen, a brez podatkov. Vpiši ročno.", got ? "success" : "warning");
      } catch (e) { status("Napaka pri povezavi z bazo VIN.", "danger"); }
    }

    VS._cfg = cfg;
    VS._decode = decode;
    VS._status = status;

    // Gumbi (preko data-vs atributov)
    document.querySelectorAll('[data-vs="decode"]').forEach((b) =>
      b.addEventListener("click", () => {
        const vin = cleanVin($(cfg.vin).value);
        if (vin.length !== 17) { status("VIN mora imeti 17 znakov.", "danger"); return; }
        $(cfg.vin).value = vin; decode(vin);
      }));
    document.querySelectorAll('[data-vs="scan-barcode"]').forEach((b) =>
      b.addEventListener("click", () => openScanner("barcode")));
    document.querySelectorAll('[data-vs="scan-ocr"]').forEach((b) =>
      b.addEventListener("click", () => openScanner("ocr")));

    // Fotografiraj VIN iz datoteke (telefonska kamera) + potrditev.
    // Strani, ki sliko obdelajo same (npr. obrazec novega naročila), dodajo
    // polju data-vs-skip – sicer bi se slika brala dvakrat.
    const photoInput = cfg.vin ? document.getElementById("nv_vin_photo") : null;
    if (photoInput && !photoInput.hasAttribute("data-vs-skip")) {
      photoInput.addEventListener("change", function (e) {
        const file = e.target.files && e.target.files[0];
        if (file) readVinFromPhoto(file, cfg, status, decode);
        photoInput.value = "";  // dovoli ponovno isto datoteko
      });
    }

    // VIN nima črk I, O, Q – ob tipkanju samodejno popravimo (O→0, I→1, Q→0)
    const vinEl = cfg.vin ? document.getElementById(cfg.vin) : null;
    if (vinEl) {
      vinEl.addEventListener("input", () => {
        const pos = vinEl.selectionStart;
        const fixed = vinSubstitute(vinEl.value.toUpperCase());
        if (fixed !== vinEl.value) {
          vinEl.value = fixed;
          try { vinEl.setSelectionRange(pos, pos); } catch (e) {}
        }
      });
    }
  };

  VS.captureOCR  = captureOCR;
  VS.stopCam     = stopCam;
  VS.toggleTorch = toggleTorch;
  VS.cleanVin    = cleanVin;
  VS.checksumOk  = vinChecksumValid;
  window.VehicleSmart = VS;

  /* ── Prevzem gumbov „Fotografiraj" ─────────────────────────────────────

     Poslušamo na ravni dokumenta v FAZI ZAJEMA (tretji argument true).
     Tak poslušalec se sproži, PREDEN dogodek doseže gumb, zato lahko
     ustavimo staro kodo na strani in odpremo kamero sami.

     Zakaj tako: s tem zadošča zamenjati SAMO to datoteko. Predlog strani
     (new.html) lahko ostane star – njegov gumb bo vseeno odprl kamero in
     ne izbire datotek. Tako popravek ni odvisen od tega, ali so vse
     datoteke prišle na strežnik.                                        */
  const GUMBI_ZA_SLIKANJE =
    '#nv_vin_cam_btn,[data-vs="scan-ocr"],[data-vs="scan-barcode"],[data-vs="photo"]';

  document.addEventListener("click", function (e) {
    const t = e.target;
    if (!t || !t.closest) return;
    const gumb = t.closest(GUMBI_ZA_SLIKANJE);
    if (!gumb) return;

    // Ustavimo staro ravnanje gumba (odpiranje izbire datotek)
    e.preventDefault();
    e.stopPropagation();
    if (e.stopImmediatePropagation) e.stopImmediatePropagation();

    openScanner();
  }, true);

  // V konzoli (F12) se takoj vidi, katera različica teče.
  try { console.log("vehicle_smart.js – različica " + VS.VERZIJA); } catch (e) {}
})();
