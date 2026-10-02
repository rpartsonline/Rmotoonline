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

  // Ostrina (varianca Laplaceovega operatorja) – za izbor najboljših sličic.
  function sharpnessScore(g, w, h) {
    let sum = 0, n = 0;
    for (let y = 2; y < h - 2; y += 2) {
      for (let x = 2; x < w - 2; x += 2) {
        const p = y * w + x;
        const lap = 4 * g[p] - g[p - 1] - g[p + 1] - g[p - w] - g[p + w];
        sum += lap * lap; n++;
      }
    }
    return n ? sum / n : 0;
  }

  // Delež presvetljenih pik – sličice s hudim odsevom zavržemo.
  function blownFraction(g) {
    let n = 0;
    for (let p = 0; p < g.length; p += 3) if (g[p] >= 250) n++;
    return n / (g.length / 3);
  }

  // ── Zajem sličice iz žive slike ───────────────────────────────────────────

  const GUIDE_W = 0.88, GUIDE_H = 0.22;   // enako kot modri okvir v oknu
  const MAX_OUT_W = 2400;

  function cropFrame(video) {
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw) return null;
    const sw = vw * GUIDE_W, sh = vh * GUIDE_H;
    const sx = (vw - sw) / 2, sy = (vh - sh) / 2;
    const scale = Math.min(2.5, MAX_OUT_W / sw);
    const w = Math.round(sw * scale), h = Math.round(sh * scale);
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, w, h);
    return { canvas: c, ctx, w, h };
  }

  /* Med zajemom serije delamo samo poceni stvari (izrez, sivine, ocena ostrine),
     da sličice res sledijo druga drugi. Drago obdelavo opravimo šele na tistih
     nekaj sličicah, ki jih zares pošljemo v branje. */
  function captureFrame(video) {
    const f = cropFrame(video);
    if (!f) return null;
    const { canvas, ctx, w, h } = f;
    const gray = toGray(ctx, w, h);
    const blown = blownFraction(gray);
    return {
      canvas, ctx, w, h, gray, prepared: null, jpeg: null,
      // sličice z odsevom čez 25 % površine potisnemo na dno vrste
      score: sharpnessScore(gray, w, h) * (blown > 0.25 ? 0.25 : 1),
    };
  }

  /* Poravnana osvetlitev + raztegnjen kontrast + izostritev. Namenoma NE
     binariziramo – Google Vision iz sivinske slike odčita bistveno več. */
  function enhance(f) {
    if (f.prepared) return f.prepared;
    const radius = Math.max(8, Math.round(f.h / 6));
    let g = flattenIllumination(f.gray, f.w, f.h, radius);
    g = stretchContrast(g);
    g = sharpen(g, f.w, f.h, 0.6);
    f.prepared = g;
    return g;
  }

  function frameToJpeg(f) {
    if (f.jpeg) return f.jpeg;
    putGray(f.ctx, enhance(f), f.w, f.h);
    f.jpeg = f.canvas.toDataURL("image/jpeg", 0.92);
    return f.jpeg;
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function grabBurst(video, count, gapMs) {
    const out = [];
    for (let i = 0; i < count; i++) {
      const f = captureFrame(video);
      if (f) out.push(f);
      if (i < count - 1) await sleep(gapMs);
    }
    return out;
  }

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

  async function visionRead(jpegs, prior) {
    try {
      const r = await fetch("/vehicles/api/vin-ocr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ images: jpegs, prior: prior || [] }),
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
  async function readViaVision(frames, onStatus) {
    if (!frames.length) return null;

    const first = await visionRead([frameToJpeg(frames[0])]);
    if (first.error === "no_key" || first.error === "daily_limit" || first.error === "network") {
      return { unavailable: true, why: first.error };
    }
    if (first.ok && first.vin && first.confident) return first;

    const rest = frames.slice(1, 3);
    if (rest.length) {
      if (onStatus) onStatus("Preverjam še z dodatnimi posnetki …");
      const prior = (first.ok && first.vin) ? [first.vin] : [];
      const more = await visionRead(rest.map(frameToJpeg), prior);
      if (more.ok && more.vin) return more;
    }
    return (first.ok && first.vin) ? first : null;
  }

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

  // ── Skener (okno s kamero) ────────────────────────────────────────────────

  function el(id) { return document.getElementById(id); }

  function setMsg(html, kind) {
    const m = el("scan-msg");
    if (!m) return;
    m.className = "small mt-2 mb-0 text-" + (kind || "muted");
    m.innerHTML = html;
  }

  async function openScanner(mode) {
    const cam = VS._cam;
    cam.mode = mode;
    const t = el("scan-title");
    if (t) t.textContent = mode === "barcode" ? "Skeniraj VIN kodo" : "Skeniraj VIN";
    const cap = el("scan-capture");
    if (cap) cap.style.display = "";          // zajem je na voljo v obeh načinih
    if (!cam.modal) cam.modal = new bootstrap.Modal(el("scanModal"));
    cam.modal.show();

    try {
      cam.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width:  { ideal: 2560 },
          height: { ideal: 1440 },
          advanced: [{ focusMode: "continuous" }],
        },
      });
    } catch (e) {
      try {
        cam.stream = await navigator.mediaDevices.getUserMedia({ video: true });
      } catch (e2) {
        setMsg("Ni dostopa do kamere. Dovoli kamero v brskalniku ali vpiši VIN ročno.", "danger");
        return;
      }
    }

    const v = el("scan-video");
    v.srcObject = cam.stream;
    try { await v.play(); } catch (e) {}

    cam.track = cam.stream.getVideoTracks()[0] || null;
    setupCameraControls();

    setMsg("Poravnaj VIN v okvir. Kodo preberem sam, sicer pritisni <b>Zajemi VIN</b>.", "muted");
    startBarcodeLoop();
  }

  // Svetilka, približevanje in izostritev z dotikom – če jih naprava podpira.
  function setupCameraControls() {
    const cam = VS._cam;
    const torchBtn = el("scan-torch"), zoomWrap = el("scan-zoom-wrap"), zoom = el("scan-zoom");
    let caps = null;
    try { caps = cam.track && cam.track.getCapabilities ? cam.track.getCapabilities() : null; } catch (e) {}

    if (torchBtn) torchBtn.style.display = (caps && "torch" in caps) ? "" : "none";
    cam.torch = false;
    if (torchBtn) torchBtn.classList.remove("active");

    if (zoomWrap && zoom) {
      if (caps && caps.zoom) {
        zoomWrap.style.setProperty("display", "flex", "important");
        zoom.min = caps.zoom.min; zoom.max = caps.zoom.max;
        zoom.step = caps.zoom.step || 0.1;
        zoom.value = cam.track.getSettings().zoom || caps.zoom.min;
        zoom.oninput = () => {
          try { cam.track.applyConstraints({ advanced: [{ zoom: +zoom.value }] }); } catch (e) {}
        };
      } else {
        zoomWrap.style.setProperty("display", "none", "important");
      }
    }

    // Dotik na sliko = izostri na to točko
    const v = el("scan-video");
    if (v && caps && caps.focusMode && caps.focusMode.indexOf("single-shot") >= 0) {
      v.onclick = async (ev) => {
        const r = v.getBoundingClientRect();
        const x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
        try {
          await cam.track.applyConstraints({
            advanced: [{ focusMode: "single-shot", pointsOfInterest: [{ x, y }] }],
          });
          setMsg("Ostrim …", "primary");
          setTimeout(() => setMsg("Poravnaj VIN v okvir, nato <b>Zajemi VIN</b>.", "muted"), 900);
        } catch (e) {}
      };
    }
  }

  function toggleTorch() {
    const cam = VS._cam;
    if (!cam.track) return;
    cam.torch = !cam.torch;
    try { cam.track.applyConstraints({ advanced: [{ torch: cam.torch }] }); } catch (e) {}
    const b = el("scan-torch");
    if (b) b.classList.toggle("active", cam.torch);
  }

  // Zvezno iskanje črtne kode v ozadju – brez pritiska na gumb.
  function startBarcodeLoop() {
    const cam = VS._cam, v = el("scan-video");
    let busy = false;
    const tick = async () => {
      if (!cam.stream) return;
      if (!busy && !VS._busy && v.videoWidth) {
        busy = true;
        try {
          const f = cropFrame(v);
          if (f) {
            const vin = await detectBarcode(f.canvas);
            if (vin) { foundVin(vin, { source: "koda", valid: vinChecksumValid(vin) }); return; }
          }
        } catch (e) {}
        busy = false;
      }
      cam.raf = setTimeout(tick, 250);
    };
    tick();
  }

  // Glavni zajem – sproži se z gumbom „Zajemi VIN".
  async function captureOCR() {
    const v = el("scan-video");
    if (!v || !v.videoWidth || VS._busy) return;
    VS._busy = true;
    const btn = el("scan-capture");
    if (btn) btn.disabled = true;

    try {
      setMsg('<i class="bi bi-camera"></i> Zajemam … držite mirno', "primary");
      const frames = await grabBurst(v, 7, 90);
      if (!frames.length) { setMsg("Zajem ni uspel. Poskusi znova.", "danger"); return; }

      // 1) Črtna koda v katerikoli sličici – najbolj točno, kar obstaja
      for (const f of frames) {
        const vin = await detectBarcode(f.canvas);
        if (vin) { foundVin(vin, { source: "koda", valid: vinChecksumValid(vin) }); return; }
      }

      frames.sort((a, b) => b.score - a.score);

      // 2) Google Vision na najostrejših sličicah
      setMsg('<i class="bi bi-arrow-repeat"></i> Berem VIN …', "primary");
      const res = await readViaVision(frames, (m) => setMsg(m, "primary"));
      if (res && res.vin) { foundVin(res.vin, res); return; }

      // 3) Rezerva: Tesseract v brskalniku
      if (res && res.unavailable) {
        setMsg(res.why === "daily_limit"
          ? "Dnevna meja branja je dosežena – berem lokalno …"
          : '<i class="bi bi-arrow-repeat"></i> Berem lokalno …', "warning");
      } else {
        setMsg('<i class="bi bi-arrow-repeat"></i> Poskušam še lokalno branje …', "warning");
      }
      const t = await readViaTesseract(frames);
      if (t) { foundVin(t, { source: "lokalno", valid: vinChecksumValid(t) }); return; }

      setMsg("VIN ni prepoznan. Pojdi bližje (naj okvir zapolni številka), "
           + "prižgi <b>svetilko</b> in poskusi pod rahlim kotom, da ni odseva.", "danger");
    } finally {
      VS._busy = false;
      if (btn) btn.disabled = false;
    }
  }

  function foundVin(vin, info) {
    const cfg = VS._cfg;
    stopCam();
    if (VS._cam.modal) VS._cam.modal.hide();
    if (cfg && cfg.vin) {
      const e = el(cfg.vin);
      if (e) { e.value = vin; e.focus(); }
    }
    announce(vin, info || {});
    if (VS._decode) VS._decode(vin);
  }

  // Pove, od kod je številka in kako zanesljiva je – da jo delavec po potrebi preveri.
  function announce(vin, info) {
    const st = VS._cfg && VS._cfg.status ? el(VS._cfg.status) : null;
    if (!st) return;
    let kind = "success", txt;
    if (info.source === "koda") {
      txt = "VIN prebran s črtne kode – točno.";
    } else if (info.corrected) {
      kind = "warning";
      txt = "VIN prebran in popravljen po kontrolni številki (" + escapeHtml(info.corrected)
          + " → " + escapeHtml(vin) + "). Preveri znake.";
    } else if (info.valid) {
      txt = "VIN prebran, kontrolna številka se ujema.";
    } else if (info.votes && info.votes > 1) {
      txt = "VIN prebran – enako na " + info.votes + " posnetkih.";
    } else {
      kind = "warning";
      txt = "VIN prebran – natančno preveri vsak znak.";
    }
    st.className = "small mt-2 text-" + kind;
    st.innerHTML = '<i class="bi bi-' + (kind === "success" ? "check-circle" : "exclamation-triangle")
                 + ' me-1"></i>' + txt;
  }

  function stopCam() {
    const cam = VS._cam;
    if (cam.raf) { clearTimeout(cam.raf); cam.raf = null; }
    if (cam.torch && cam.track) {
      try { cam.track.applyConstraints({ advanced: [{ torch: false }] }); } catch (e) {}
      cam.torch = false;
    }
    if (cam.stream) { cam.stream.getTracks().forEach((t) => t.stop()); cam.stream = null; }
    cam.track = null;
    const v = el("scan-video");
    if (v) { v.srcObject = null; v.onclick = null; }
  }

  // ── Branje VIN iz naložene fotografije ────────────────────────────────────

  async function readVinFromPhoto(file, cfg, status, decode) {
    status('<i class="bi bi-arrow-repeat"></i> Berem fotografijo …', "primary");

    let bmp;
    try { bmp = await createImageBitmap(file); }
    catch (e) { status("Slike ni bilo mogoče odpreti. Poskusi znova.", "danger"); return; }

    const maxW = 2400;
    const sc = Math.min(1, maxW / bmp.width);
    const w = Math.round(bmp.width * sc), h = Math.round(bmp.height * sc);
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(bmp, 0, 0, w, h);

    // Črtna koda na fotografiji – če je, je rezultat točen
    try {
      const vin = await detectBarcode(c);
      if (vin) { setVinResult(vin, cfg, status, { source: "koda" }); if (decode) decode(vin); return; }
    } catch (e) {}

    const gray = toGray(ctx, w, h);
    const radius = Math.max(12, Math.round(Math.min(w, h) / 8));
    let g = flattenIllumination(gray, w, h, radius);
    g = stretchContrast(g);
    g = sharpen(g, w, h, 0.5);

    const frame = { canvas: c, ctx, w, h, gray, prepared: g, score: 1, jpeg: null };

    // Pošljemo dve različici: surovo in poravnano – Vision o njiju glasuje
    const rawJpeg = c.toDataURL("image/jpeg", 0.92);
    putGray(ctx, g, w, h);
    const flatJpeg = c.toDataURL("image/jpeg", 0.92);

    const j = await visionRead([flatJpeg, rawJpeg]);
    if (j.ok && j.vin) {
      setVinResult(j.vin, cfg, status, j);
      if (decode) decode(j.vin);
      return;
    }
    if (j.error === "daily_limit") {
      status("Dnevna meja branja je dosežena – berem lokalno …", "warning");
    }

    const t = await readViaTesseract([frame]);
    if (t) {
      setVinResult(t, cfg, status, { source: "lokalno", valid: vinChecksumValid(t) });
      if (decode) decode(t);
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
    } else if (info.corrected) {
      status("VIN prebran in popravljen po kontrolni številki (" + escapeHtml(info.corrected)
             + " → " + escapeHtml(vin) + "). Preveri znake.", "warning");
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

    // Fotografiraj VIN iz datoteke (telefonska kamera) + potrditev
    const photoInput = cfg.vin ? document.getElementById("nv_vin_photo") : null;
    if (photoInput) {
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
})();
