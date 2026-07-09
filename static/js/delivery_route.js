/* Dostava – brezplačna izvedba poti:
   1) prilepiš/naložiš print screen z naslovi → OCR (Tesseract) prebere vrstice
   2) naslove geokodiramo (Nominatim, brezplačno) → koordinate
   3) samodejno razvrstimo „najbližji naslednji" iz Ajdovščine
   4) pravo pot po cestah prek brezplačnega OSRM strežnika narišemo na zemljevid (Leaflet + OpenStreetMap)
   5) gumb za tiskanje (zemljevid + seznam)

   Pošteno: vse je odvisno od brezplačnih javnih strežnikov (Nominatim, OSRM),
   ki so počasni in omejeni. Naslov, ki ga ne najde, je označen za ročni popravek.
*/
(function () {
  "use strict";

  // Delavnica Ajdovščina (start in cilj)
  const HOME = { lat: 45.8869, lon: 13.9089, label: "Bartog Ajdovščina" };

  const NOMINATIM = "https://nominatim.openstreetmap.org/search";
  const OSRM = "https://router.project-osrm.org/route/v1/driving/";

  let map = null, layer = null;
  let stops = [];   // {name, address, lat, lon, ok}

  function $(id) { return document.getElementById(id); }
  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  }

  // ── OCR: prebere vrstice (ime + naslov) ─────────────────────────────────────
  // Prepozna naslove: vsebuje hišno številko ali ključno besedo
  function looksLikeAddr(s) {
    if (!s) return false;
    // Hišna številka (npr. "Ulica 13", "Cesta 5A", "13A")
    if (/\b\d+\s*[a-zA-Z]?\s*(,|$)/.test(s)) return true;
    // Ključne besede za slovensko cesto
    if (/\b(ulica|ul\.|cesta|c\.|trg|pot|vas|naselje|aleja|breg|gmajna)\b/i.test(s)) return true;
    // Poštna številka (4 cifre)
    if (/\b\d{4}\b/.test(s)) return true;
    return false;
  }

  function isHeader(s) {
    return /^(stranka|kupec|firma|naslov|ime|telefon|#|št|vrstni)/i.test(s.trim());
  }

  function parseLines(text) {
    const raw = (text || "").split(/\r?\n/).map(s => s.trim()).filter(s => s.length >= 3);
    const out = [];
    let i = 0;
    while (i < raw.length) {
      const ln = raw[i];
      if (isHeader(ln)) { i++; continue; }

      // Format: "Ime, Naslov" ali "Ime - Naslov" ali "Ime | Naslov"
      const sepMatch = ln.match(/^(.+?)[,\-|]\s*(.+)$/);
      if (sepMatch) {
        const a = sepMatch[1].trim(), b = sepMatch[2].trim();
        // Drugi del je naslov?
        if (looksLikeAddr(b) && !looksLikeAddr(a)) {
          out.push({ name: a, address: b });
          i++; continue;
        }
        // Prvi del je naslov?
        if (looksLikeAddr(a) && !looksLikeAddr(b)) {
          out.push({ name: b, address: a });
          i++; continue;
        }
        // Oba sta enaka – vzemi ime brez naslova, naslov pa vse od vejice naprej
        out.push({ name: a, address: ln.slice(ln.indexOf(sepMatch[0][a.length]) + 1).trim() });
        i++; continue;
      }

      // Format: naslednja vrstica je naslov (dve vrstici na postanok)
      if (i + 1 < raw.length) {
        const next = raw[i + 1];
        if (!isHeader(next)) {
          if (looksLikeAddr(next) && !looksLikeAddr(ln)) {
            out.push({ name: ln, address: next });
            i += 2; continue;
          }
          if (looksLikeAddr(ln) && !looksLikeAddr(next)) {
            out.push({ name: next, address: ln });
            i += 2; continue;
          }
        }
      }

      // Ena vrstica – ime in naslov sta enaka (geocodiranje bo poskusilo)
      out.push({ name: ln, address: ln });
      i++;
    }
    return out;
  }

  function runOCR(file) {
    const st = $("dz-status"), tbl = $("dz-table");
    st.innerHTML = '<i class="bi bi-arrow-repeat"></i> Berem sliko…';
    tbl.innerHTML = "";
    Tesseract.recognize(file, "slv+eng").then(({ data: { text } }) => {
      const rows = parseLines(text);
      if (!rows.length) {
        st.innerHTML = '<span class="text-danger">Iz slike nisem prebral naslovov. Vpiši ročno spodaj.</span>';
        return;
      }
      renderEditable(rows);
      st.innerHTML = '<span class="text-success">Prebrano ' + rows.length + ' vrstic.</span> Preveri/popravi naslove, nato „Izračunaj pot".';
    }).catch(() => {
      st.innerHTML = '<span class="text-danger">Napaka pri branju slike.</span>';
    });
  }

  function renderEditable(rows) {
    const tbl = $("dz-table");
    let html = '<table class="table table-sm align-middle"><thead><tr>'
      + '<th style="width:36%">Stranka</th><th>Naslov (ulica, kraj)</th><th style="width:40px"></th>'
      + '</tr></thead><tbody>';
    rows.forEach(r => {
      html += '<tr>'
        + '<td><input class="form-control form-control-sm dz-name" value="' + escapeHtml(r.name) + '"></td>'
        + '<td><input class="form-control form-control-sm dz-addr" value="' + escapeHtml(r.address) + '"></td>'
        + '<td><button type="button" class="btn btn-sm btn-outline-danger dz-del"><i class="bi bi-x"></i></button></td>'
        + '</tr>';
    });
    html += '</tbody></table>'
      + '<button type="button" id="dz-addrow" class="btn btn-sm btn-outline-secondary"><i class="bi bi-plus"></i> Dodaj vrstico</button> '
      + '<button type="button" id="dz-calc" class="btn btn-sm btn-success"><i class="bi bi-geo-alt"></i> Izračunaj pot</button>';
    tbl.innerHTML = html;

    tbl.querySelectorAll(".dz-del").forEach(b =>
      b.addEventListener("click", e => e.target.closest("tr").remove()));
    $("dz-addrow").addEventListener("click", () => {
      const tb = tbl.querySelector("tbody");
      const tr = document.createElement("tr");
      tr.innerHTML = '<td><input class="form-control form-control-sm dz-name"></td>'
        + '<td><input class="form-control form-control-sm dz-addr"></td>'
        + '<td><button type="button" class="btn btn-sm btn-outline-danger dz-del"><i class="bi bi-x"></i></button></td>';
      tb.appendChild(tr);
      tr.querySelector(".dz-del").addEventListener("click", e => e.target.closest("tr").remove());
    });
    $("dz-calc").addEventListener("click", calcRoute);
  }

  // ── Geokodiranje (Nominatim) ────────────────────────────────────────────────
  async function geocode(q) {
    const url = NOMINATIM + "?format=json&limit=1&countrycodes=si&q=" + encodeURIComponent(q);
    try {
      const res = await fetch(url, { headers: { "Accept": "application/json" } });
      const data = await res.json();
      if (data && data.length) {
        return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
      }
    } catch (e) { /* ignore */ }
    return null;
  }

  // ── Razvrstitev „najbližji naslednji" iz Ajdovščine ─────────────────────────
  function haversine(a, b) {
    const R = 6371, toRad = x => x * Math.PI / 180;
    const dLat = toRad(b.lat - a.lat), dLon = toRad(b.lon - a.lon);
    const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(s));
  }

  function nearestOrder(points) {
    const remaining = points.slice();
    const ordered = [];
    let cur = HOME;
    while (remaining.length) {
      let bi = 0, bd = Infinity;
      remaining.forEach((p, i) => { const d = haversine(cur, p); if (d < bd) { bd = d; bi = i; } });
      cur = remaining[bi];
      ordered.push(remaining.splice(bi, 1)[0]);
    }
    return ordered;
  }

  // ── Glavni izračun ──────────────────────────────────────────────────────────
  async function calcRoute() {
    const tbl = $("dz-table"), st = $("dz-status");
    const names = [...tbl.querySelectorAll(".dz-name")].map(i => i.value.trim());
    const addrs = [...tbl.querySelectorAll(".dz-addr")].map(i => i.value.trim());
    const items = names.map((n, i) => ({ name: n, address: addrs[i] }))
      .filter(x => x.address);
    if (!items.length) { st.innerHTML = '<span class="text-danger">Ni naslovov.</span>'; return; }

    st.innerHTML = '<i class="bi bi-arrow-repeat"></i> Iščem naslove na zemljevidu… (po vrsti, ~1 s na naslov)';
    const geocoded = [];
    for (const it of items) {
      const g = await geocode(it.address);
      geocoded.push({ name: it.name || it.address, address: it.address, lat: g ? g.lat : null, lon: g ? g.lon : null, ok: !!g });
      await sleep(1100); // Nominatim: max ~1 poizvedba/s
    }

    const found = geocoded.filter(s => s.ok);
    const missing = geocoded.filter(s => !s.ok);
    if (!found.length) {
      st.innerHTML = '<span class="text-danger">Nobenega naslova nisem našel. Preveri zapis (ulica, hišna št., kraj).</span>';
      return;
    }

    stops = nearestOrder(found);
    drawMap();
    renderOrdered(missing);
    st.innerHTML = '<span class="text-success">Najdenih ' + found.length + ' naslovov.</span>'
      + (missing.length ? ' <span class="text-danger">Ni najdenih: ' + missing.length + ' (popravi naslov in ponovi).</span>' : '');
  }

  // ── Zemljevid ─────────────────────────────────────────────────────────────
  function ensureMap() {
    if (map) return;
    map = L.map("dz-map");
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "© OpenStreetMap"
    }).addTo(map);
  }

  async function drawMap() {
    $("dz-map-wrap").style.display = "";
    ensureMap();
    if (layer) { map.removeLayer(layer); }
    layer = L.layerGroup().addTo(map);

    const seq = [HOME, ...stops, HOME];

    // markerji
    L.marker([HOME.lat, HOME.lon]).addTo(layer).bindPopup("Start/cilj: " + HOME.label);
    stops.forEach((s, i) => {
      L.marker([s.lat, s.lon]).addTo(layer).bindPopup((i + 1) + ". " + s.name);
    });

    // pot po cestah (OSRM) – v enem klicu skozi vse točke
    const coords = seq.map(p => p.lon + "," + p.lat).join(";");
    try {
      const res = await fetch(OSRM + coords + "?overview=full&geometries=geojson");
      const data = await res.json();
      if (data && data.routes && data.routes[0]) {
        const line = data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
        L.polyline(line, { color: "#3b82f6", weight: 5, opacity: .8 }).addTo(layer);
        const km = (data.routes[0].distance / 1000).toFixed(1);
        const min = Math.round(data.routes[0].duration / 60);
        $("dz-summary").textContent = "Skupaj ~" + km + " km · ~" + min + " min vožnje (brez prometa).";
        map.fitBounds(L.polyline(line).getBounds(), { padding: [30, 30] });
        return;
      }
    } catch (e) { /* fallback spodaj */ }

    // rezerva: ravne črte, če OSRM ni dosegljiv
    const straight = seq.map(p => [p.lat, p.lon]);
    L.polyline(straight, { color: "#f59e0b", weight: 4, dashArray: "6 6" }).addTo(layer);
    $("dz-summary").textContent = "Cestna pot ni bila dosegljiva – prikazane so ravne povezave.";
    map.fitBounds(L.polyline(straight).getBounds(), { padding: [30, 30] });
  }

  function renderOrdered(missing) {
    const el = $("dz-ordered");
    let html = '<div class="form-section-title mt-3"><i class="bi bi-list-ol"></i> Predlagan vrstni red</div>';
    html += '<ol class="mb-2">';
    html += '<li class="text-primary fw-semibold">Start: ' + escapeHtml(HOME.label) + '</li>';
    stops.forEach(s => { html += '<li>' + escapeHtml(s.name) + ' <span class="text-muted small">– ' + escapeHtml(s.address) + '</span></li>'; });
    html += '<li class="text-primary fw-semibold">Cilj: ' + escapeHtml(HOME.label) + '</li>';
    html += '</ol>';
    if (missing.length) {
      html += '<div class="small text-danger">Ni najdeni naslovi: ' + missing.map(m => escapeHtml(m.address)).join("; ") + '</div>';
    }
    html += '<button type="button" id="dz-print" class="btn btn-primary btn-sm mt-1"><i class="bi bi-printer me-1"></i>Natisni pot</button>';
    el.innerHTML = html;
    $("dz-print").addEventListener("click", printRoute);
  }

  // ── Tisk (zemljevid kot slika + seznam) ─────────────────────────────────────
  function buildPrintHtml(mapImg) {
    let rows = stops.map((s, i) => "<tr><td>" + (i + 1) + "</td><td>" + escapeHtml(s.name)
      + "</td><td>" + escapeHtml(s.address) + "</td><td style='width:34px'>&#9744;</td></tr>").join("");
    const summary = ($("dz-summary").textContent || "");
    const imgTag = mapImg
      ? "<img src='" + mapImg + "' style='width:100%;max-width:720px;border:1px solid #ccc;border-radius:8px;margin:10px 0;'>"
      : "";
    return "<html><head><meta charset='utf-8'><title>Pot dostave</title><style>"
      + "body{font-family:Arial;margin:24px;} h1{font-size:20px;border-bottom:3px solid #111;padding-bottom:6px;}"
      + "table{width:100%;border-collapse:collapse;margin-top:10px;} th,td{border-bottom:1px solid #ccc;padding:8px;text-align:left;font-size:14px;}"
      + "th{background:#f0f0f0;font-size:12px;text-transform:uppercase;}"
      + ".meta{font-size:13px;color:#444;margin:6px 0;}"
      + "@media print{ img{ max-width:100% !important; } }"
      + "</style></head><body>"
      + "<h1>Pot dostave – Bartog Ajdovščina</h1>"
      + "<div class='meta'>Start/cilj: " + escapeHtml(HOME.label) + " · Datum: ______ · Šofer: ______</div>"
      + "<div class='meta'>" + escapeHtml(summary) + "</div>"
      + imgTag
      + "<table><thead><tr><th>#</th><th>Stranka</th><th>Naslov</th><th>✓</th></tr></thead><tbody>"
      + rows + "</tbody></table>"
      + "<script>setTimeout(function(){window.print();},400);<\/script>"
      + "</body></html>";
  }

  function openPrint(mapImg) {
    const w = window.open("", "_blank");
    w.document.write(buildPrintHtml(mapImg));
    w.document.close();
  }

  function printRoute() {
    const btn = $("dz-print");
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Pripravljam zemljevid…'; }

    function done() { if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-printer me-1"></i>Natisni pot'; } }

    // Poskusi zajeti zemljevid kot sliko (leaflet-image), sicer natisni brez slike
    if (window.leafletImage && map) {
      try {
        window.leafletImage(map, function (err, canvas) {
          let img = null;
          if (!err && canvas) { try { img = canvas.toDataURL("image/png"); } catch (e) { img = null; } }
          openPrint(img);
          done();
        });
        return;
      } catch (e) { /* fallback */ }
    }
    openPrint(null);
    done();
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  window.DeliveryRoute = {
    init() {
      const drop = $("dz-drop"), file = $("dz-file");
      if (!drop) return;
      const handle = f => { if (f) runOCR(f); };
      drop.addEventListener("click", () => file.click());
      file.addEventListener("change", e => handle(e.target.files[0]));
      document.addEventListener("paste", e => {
        const items = (e.clipboardData || {}).items || [];
        for (const it of items) if (it.type && it.type.indexOf("image") === 0) { handle(it.getAsFile()); break; }
      });
      drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("bi-over"); });
      drop.addEventListener("dragleave", () => drop.classList.remove("bi-over"));
      drop.addEventListener("drop", e => { e.preventDefault(); drop.classList.remove("bi-over"); if (e.dataTransfer.files[0]) handle(e.dataTransfer.files[0]); });
    }
  };
})();
