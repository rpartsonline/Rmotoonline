/* Pametna polja za vozilo: predlaganje znamke/modela + skeniranje in
   razčlenjevanje VIN. Uporablja se na obrazcu vozila in pri novem naročilu. */
(function () {
  "use strict";

  const VS = {
    makes: (window.CAR_MAKES || []),
    apiModels: "",
    apiVin: "",
    _cam: { stream: null, raf: null, mode: "barcode", modal: null, cfg: null },
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

  // ── VIN čiščenje / validacija ─────────────────────────────────────────────
  function cleanVin(raw) {
    let s = (raw || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
    s = s.replace(/I/g, "1").replace(/O/g, "0").replace(/Q/g, "0");
    const m = s.match(/[A-HJ-NPR-Z0-9]{17}/);
    return m ? m[0] : "";
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
      const el = $(cfg.status);
      if (!el) return;
      el.className = "small mt-2 text-" + (kind || "muted");
      el.innerHTML = msg;
    }

    function setVal(id, val) { const el = $(id); if (el && val) el.value = val; }
    function setSelect(id, val) {
      const el = $(id); if (!el || !val) return;
      if (el.tagName === "SELECT") {
        if ([...el.options].some((o) => o.value === val)) el.value = val;
      } else { el.value = val; }
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

    // VIN: čiščenje + živo preverjanje 17 znakov
    const vinEl = cfg.vin ? document.getElementById(cfg.vin) : null;
    const lenEl = document.getElementById("nv_vin_len");
    function cleanVin(raw) {
      return (raw || "")
        .toUpperCase()
        .replace(/[IOQ]/g, (m) => ({ I: "1", O: "0", Q: "0" }[m]))  // pogoste zamenjave
        .replace(/[^A-HJ-NPR-Z0-9]/g, "")  // VIN nima I,O,Q + odstrani presledke/ločila
        .slice(0, 17);
    }
    function updateVinLen() {
      if (!vinEl || !lenEl) return;
      const n = vinEl.value.length;
      if (n === 0) { lenEl.textContent = ""; return; }
      if (n === 17) {
        const ok = vinChecksumValid(vinEl.value);
        lenEl.innerHTML = ok
          ? '<span class="text-success">✓ 17 znakov</span>'
          : '<span class="text-warning">17 znakov (preveri točnost)</span>';
      } else {
        lenEl.innerHTML = '<span class="text-danger">' + n + '/17 znakov</span>';
      }
    }
    if (vinEl) {
      vinEl.addEventListener("input", () => {
        const pos = vinEl.selectionStart;
        vinEl.value = cleanVin(vinEl.value);
        try { vinEl.setSelectionRange(pos, pos); } catch (e) {}
        updateVinLen();
      });
      updateVinLen();
    }

    // Gumb „Prilepi VIN" (telefonova prepoznava besedila → odložišče)
    const pasteBtn = document.getElementById("nv_vin_paste");
    if (pasteBtn && vinEl) {
      pasteBtn.addEventListener("click", async () => {
        try {
          const txt = await navigator.clipboard.readText();
          const vin = cleanVin(txt);
          if (vin.length >= 11) {
            vinEl.value = vin;
            updateVinLen();
            status(vin.length === 17
              ? "VIN prilepljen. Preveri točnost in klikni „Razčleni“."
              : "Prilepljeno " + vin.length + " znakov – VIN mora imeti 17. Preveri.", vin.length === 17 ? "success" : "warning");
            vinEl.focus();
          } else {
            status("V odložišču ni videti VIN številke. Kopiraj VIN (17 znakov) in poskusi znova.", "danger");
          }
        } catch (e) {
          status("Brskalnik ni dovolil branja odložišča. Pritisni v polje VIN in prilepi ročno (dolg pritisk → Prilepi).", "warning");
          vinEl.focus();
        }
      });
    }
  };

  // Branje VIN iz fotografije (ostra slika iz telefonske kamere)
  async function readVinFromPhoto(file, cfg, status, decode) {
    status("Berem fotografijo… (nekaj sekund)", "info");
    let bitmap;
    try {
      bitmap = await createImageBitmap(file);
    } catch (e) {
      status("Slike ni bilo mogoče odpreti. Poskusi znova.", "danger");
      return;
    }
    // Pomanjšamo na razumno širino (hitrost), a ohranimo ostrino
    const maxW = 1600;
    const scale = Math.min(1, maxW / bitmap.width);
    const w = Math.round(bitmap.width * scale), h = Math.round(bitmap.height * scale);
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d");
    ctx.drawImage(bitmap, 0, 0, w, h);

    let base;
    try { base = ctx.getImageData(0, 0, w, h); } catch (e) { base = null; }

    function applyThreshold(lo, hi) {
      if (!base) return;
      const img = ctx.createImageData(w, h), s = base.data, d = img.data;
      for (let i = 0; i < s.length; i += 4) {
        let g = 0.3 * s[i] + 0.59 * s[i + 1] + 0.11 * s[i + 2];
        g = g < lo ? 0 : g > hi ? 255 : (g - lo) * (255 / Math.max(1, hi - lo));
        d[i] = d[i + 1] = d[i + 2] = Math.max(0, Math.min(255, g)); d[i + 3] = 255;
      }
      ctx.putImageData(img, 0, 0);
    }

    const passes = [
      { lo: 110, hi: 150, psm: "6" },
      { lo: 95,  hi: 165, psm: "6" },
      { lo: 120, hi: 140, psm: "11" },
      { lo: 100, hi: 160, psm: "3" },
    ];
    const found = [];
    for (const p of passes) {
      applyThreshold(p.lo, p.hi);
      try {
        const { data: { text } } = await Tesseract.recognize(c, "eng", {
          tessedit_char_whitelist: "ABCDEFGHJKLMNPRSTUVWXYZ0123456789",
          tessedit_pageseg_mode: p.psm,
        });
        const vin = bestVin(text);
        if (vin) {
          found.push(vin);
          if (vinChecksumValid(vin)) break;
        }
      } catch (e) {}
    }

    const valid = found.find(vinChecksumValid);
    const best = valid || found[0] || "";
    if (!best) {
      status("VIN ni prepoznan. Poskusi z bolj ostro sliko, več svetlobe in poravnano številko.", "danger");
      return;
    }
    // Zahtevaj potrditev: vpiši v polje, da uporabnik preveri in po potrebi popravi
    if (cfg && cfg.vin) {
      const el2 = document.getElementById(cfg.vin);
      if (el2) { el2.value = best; el2.focus(); el2.select && el2.select(); }
    }
    if (valid) {
      status("VIN prebran in preverjen. Preveri točnost in klikni „Razčleni“.", "success");
    } else {
      status("VIN prebran, a kontrolna številka ne ustreza – natančno preveri vsak znak, nato „Razčleni“.", "warning");
    }
  }

  // ── Skener ────────────────────────────────────────────────────────────────
  function el(id) { return document.getElementById(id); }

  // Kontrolna številka VIN (severnoameriški standard) – uporabljamo kot
  // namig za zanesljivost; evropski VIN-i je nimajo vedno, zato ne zavračamo.
  const VIN_TRANS = { A:1,B:2,C:3,D:4,E:5,F:6,G:7,H:8,J:1,K:2,L:3,M:4,N:5,P:7,R:9,
                      S:2,T:3,U:4,V:5,W:6,X:7,Y:8,Z:9,
                      "0":0,"1":1,"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9 };
  const VIN_WEIGHTS = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2];
  function vinChecksumValid(v) {
    if (v.length !== 17) return false;
    let sum = 0;
    for (let i = 0; i < 17; i++) {
      if (!(v[i] in VIN_TRANS)) return false;
      sum += VIN_TRANS[v[i]] * VIN_WEIGHTS[i];
    }
    const r = sum % 11;
    return v[8] === (r === 10 ? "X" : String(r));
  }
  // Iz prepoznanega besedila izlušči najboljši 17-mestni VIN kandidat.
  function bestVin(text) {
    const s = (text || "").toUpperCase()
      .replace(/[^A-Z0-9]/g, "").replace(/I/g, "1").replace(/O/g, "0").replace(/Q/g, "0");
    const cands = [];
    for (let i = 0; i + 17 <= s.length; i++) {
      const w = s.slice(i, i + 17);
      if (/^[A-HJ-NPR-Z0-9]{17}$/.test(w)) cands.push(w);
    }
    if (!cands.length) return "";
    return cands.find(vinChecksumValid) || cands[0];
  }

  async function openScanner(mode) {
    const cam = VS._cam; cam.mode = mode;
    el("scan-title").textContent = mode === "barcode" ? "Skeniraj identifikacijsko številko / VIN" : "Fotografiraj identifikacijsko številko / VIN";
    el("scan-capture").style.display = mode === "ocr" ? "" : "none";
    if (!cam.modal) cam.modal = new bootstrap.Modal(el("scanModal"));
    cam.modal.show();

    // Pri skeniranju kode brez BarcodeDetector pustimo ZXingu, da odpre kamero.
    const useZxing = (mode === "barcode") && !("BarcodeDetector" in window) && ("ZXing" in window);
    if (useZxing) { startZxing(); return; }

    try {
      cam.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } }
      });
    } catch (e) {
      el("scan-msg").textContent = "Ni dostopa do kamere. Dovoli kamero ali vpiši VIN ročno.";
      return;
    }
    const v = el("scan-video");
    v.srcObject = cam.stream; await v.play();
    if (mode === "barcode") startBarcode();
    else el("scan-msg").textContent = 'Poravnaj VIN v okvir, nato „Zajemi in preberi“.';
  }

  // Native BarcodeDetector (Android Chrome) – hitro in zanesljivo
  function startBarcode() {
    const cam = VS._cam, v = el("scan-video");
    if (!("BarcodeDetector" in window)) {
      if ("ZXing" in window) { startZxing(); return; }
      el("scan-msg").textContent = 'Skeniranje kode tu ni podprto. Uporabi „Fotografiraj VIN“.';
      return;
    }
    const det = new BarcodeDetector({ formats: ["code_39", "code_128", "data_matrix", "pdf417", "qr_code", "itf"] });
    el("scan-msg").textContent = "Iščem VIN kodo…";
    const tick = async () => {
      if (!cam.stream) return;
      try {
        const codes = await det.detect(v);
        for (const c of (codes || [])) {
          const vin = bestVin(c.rawValue) || cleanVin(c.rawValue);
          if (vin) { foundVin(vin); return; }
        }
      } catch (e) {}
      cam.raf = requestAnimationFrame(tick);
    };
    tick();
  }

  // ZXing rezerva (iOS Safari in širši nabor kod)
  function startZxing() {
    const cam = VS._cam;
    el("scan-msg").textContent = "Iščem VIN kodo…";
    try {
      cam.zxing = new ZXing.BrowserMultiFormatReader();
      const onResult = (result, err) => {
        if (result) {
          const vin = bestVin(result.getText()) || cleanVin(result.getText());
          if (vin) foundVin(vin);
        }
      };
      if (typeof cam.zxing.decodeFromConstraints === "function") {
        cam.zxing.decodeFromConstraints(
          { video: { facingMode: { ideal: "environment" } } }, "scan-video", onResult
        );
      } else {
        cam.zxing.decodeFromVideoDevice(undefined, "scan-video", onResult);
      }
    } catch (e) {
      el("scan-msg").textContent = 'Skeniranje kode ni uspelo. Uporabi „Fotografiraj VIN“.';
    }
  }

  async function captureOCR() {
    const v = el("scan-video"), c = el("scan-canvas");
    if (!v.videoWidth) return;
    // Izrežemo samo področje vodila (sredinski pas) in ga povečamo
    const gw = 0.88, gh = 0.22, scale = 3;
    const sx = v.videoWidth * (1 - gw) / 2, sy = v.videoHeight * (1 - gh) / 2;
    const sw = v.videoWidth * gw, sh = v.videoHeight * gh;
    c.width = sw * scale; c.height = sh * scale;
    const ctx = c.getContext("2d");
    ctx.drawImage(v, sx, sy, sw, sh, 0, 0, c.width, c.height);

    // Osnovna sivinska slika
    let base;
    try { base = ctx.getImageData(0, 0, c.width, c.height); } catch (e) { base = null; }

    el("scan-msg").textContent = "Berem VIN… (nekaj sekund)";

    // Pripravi različico z danim pragom (binarizacija)
    function applyThreshold(lo, hi) {
      if (!base) return;
      const img = ctx.createImageData(base.width, base.height);
      const s = base.data, d = img.data;
      for (let i = 0; i < s.length; i += 4) {
        let g = 0.3 * s[i] + 0.59 * s[i + 1] + 0.11 * s[i + 2];
        g = g < lo ? 0 : g > hi ? 255 : (g - lo) * (255 / Math.max(1, hi - lo));
        d[i] = d[i + 1] = d[i + 2] = Math.max(0, Math.min(255, g));
        d[i + 3] = 255;
      }
      ctx.putImageData(img, 0, 0);
    }

    // Več poskusov: različni pragovi + način postavitve (PSM 7 = vrstica, 6 = blok)
    const passes = [
      { lo: 105, hi: 155, psm: "7" },
      { lo: 90,  hi: 170, psm: "7" },
      { lo: 120, hi: 140, psm: "6" },
    ];
    const found = [];
    for (const p of passes) {
      applyThreshold(p.lo, p.hi);
      try {
        const { data: { text } } = await Tesseract.recognize(c, "eng", {
          tessedit_char_whitelist: "ABCDEFGHJKLMNPRSTUVWXYZ0123456789",
          tessedit_pageseg_mode: p.psm,
        });
        const vin = bestVin(text);
        if (vin) {
          found.push(vin);
          if (vinChecksumValid(vin)) { foundVin(vin); return; }  // takoj, če je preverjen
        }
      } catch (e) {}
    }
    if (found.length) {
      foundVin(found[0]);  // ni preverjen s kontrolno številko, a najboljši kandidat
      el("scan-msg").textContent = "VIN prebran (preveri točnost).";
    } else {
      el("scan-msg").textContent = "VIN ni prepoznan. Poskusi bližje, bolj ostro in z več svetlobe.";
    }
  }

  function foundVin(vin) {
    const cfg = VS._cfg;
    if (cfg && cfg.vin) el(cfg.vin).value = vin;
    stopCam();
    if (VS._cam.modal) VS._cam.modal.hide();
    if (VS._decode) VS._decode(vin);
  }

  function stopCam() {
    const cam = VS._cam;
    if (cam.raf) { cancelAnimationFrame(cam.raf); cam.raf = null; }
    if (cam.zxing) { try { cam.zxing.reset(); } catch (e) {} cam.zxing = null; }
    if (cam.stream) { cam.stream.getTracks().forEach((t) => t.stop()); cam.stream = null; }
  }

  VS.captureOCR = captureOCR;
  VS.stopCam = stopCam;
  window.VehicleSmart = VS;
})();
