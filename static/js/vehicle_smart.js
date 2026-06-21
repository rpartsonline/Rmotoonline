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
  };

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
    el("scan-title").textContent = mode === "barcode" ? "Skeniraj VIN kodo" : "Fotografiraj VIN";
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
    const gw = 0.88, gh = 0.22, scale = 2.5;
    const sx = v.videoWidth * (1 - gw) / 2, sy = v.videoHeight * (1 - gh) / 2;
    const sw = v.videoWidth * gw, sh = v.videoHeight * gh;
    c.width = sw * scale; c.height = sh * scale;
    const ctx = c.getContext("2d");
    ctx.drawImage(v, sx, sy, sw, sh, 0, 0, c.width, c.height);
    // Sivine + kontrast (prag) za boljše prepoznavanje
    try {
      const img = ctx.getImageData(0, 0, c.width, c.height), d = img.data;
      for (let i = 0; i < d.length; i += 4) {
        let g = 0.3 * d[i] + 0.59 * d[i + 1] + 0.11 * d[i + 2];
        g = g < 105 ? 0 : g > 155 ? 255 : (g - 105) * (255 / 50);
        d[i] = d[i + 1] = d[i + 2] = Math.max(0, Math.min(255, g));
      }
      ctx.putImageData(img, 0, 0);
    } catch (e) {}
    el("scan-msg").textContent = "Berem VIN… (nekaj sekund)";
    try {
      const { data: { text } } = await Tesseract.recognize(c, "eng", {
        tessedit_char_whitelist: "ABCDEFGHJKLMNPRSTUVWXYZ0123456789",
        tessedit_pageseg_mode: "7",
      });
      const vin = bestVin(text);
      if (vin) foundVin(vin);
      else el("scan-msg").textContent = "VIN ni prepoznan. Poskusi bližje, bolj ostro in z več svetlobe.";
    } catch (e) {
      el("scan-msg").textContent = "Napaka pri branju. Poskusi znova ali vpiši ročno.";
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
