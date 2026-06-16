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

  async function openScanner(mode) {
    const cam = VS._cam; cam.mode = mode;
    el("scan-title").textContent = mode === "barcode" ? "Skeniraj črtno kodo" : "Fotografiraj VIN";
    el("scan-capture").style.display = mode === "ocr" ? "" : "none";
    if (!cam.modal) cam.modal = new bootstrap.Modal(el("scanModal"));
    cam.modal.show();
    try {
      cam.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    } catch (e) {
      el("scan-msg").textContent = "Ni dostopa do kamere. Dovoli kamero ali vpiši VIN ročno.";
      return;
    }
    const v = el("scan-video");
    v.srcObject = cam.stream; await v.play();
    if (mode === "barcode") startBarcode();
    else el("scan-msg").textContent = 'Poravnaj VIN, nato "Zajemi in preberi".';
  }

  function startBarcode() {
    const cam = VS._cam, v = el("scan-video");
    if (!("BarcodeDetector" in window)) {
      el("scan-msg").textContent = 'Skeniranje kode tu ni podprto. Uporabi "Fotografiraj VIN".';
      return;
    }
    const det = new BarcodeDetector({ formats: ["code_39", "code_128", "data_matrix", "qr_code", "pdf417"] });
    el("scan-msg").textContent = "Iščem črtno kodo…";
    const tick = async () => {
      if (!cam.stream) return;
      try {
        const codes = await det.detect(v);
        if (codes && codes.length) {
          const vin = cleanVin(codes[0].rawValue);
          if (vin) { foundVin(vin); return; }
        }
      } catch (e) {}
      cam.raf = requestAnimationFrame(tick);
    };
    tick();
  }

  async function captureOCR() {
    const v = el("scan-video"), c = el("scan-canvas");
    if (!v.videoWidth) return;
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d").drawImage(v, 0, 0);
    el("scan-msg").textContent = "Berem besedilo… (nekaj sekund)";
    try {
      const { data: { text } } = await Tesseract.recognize(c, "eng", {
        tessedit_char_whitelist: "ABCDEFGHJKLMNPRSTUVWXYZ0123456789",
      });
      const vin = cleanVin(text);
      if (vin) foundVin(vin);
      else el("scan-msg").textContent = "VIN ni prepoznan. Poskusi bližje/ostreje ali vpiši ročno.";
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
    if (cam.stream) { cam.stream.getTracks().forEach((t) => t.stop()); cam.stream = null; }
  }

  VS.captureOCR = captureOCR;
  VS.stopCam = stopCam;
  window.VehicleSmart = VS;
})();
