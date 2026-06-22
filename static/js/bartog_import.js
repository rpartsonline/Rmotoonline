/* Uvoz iz Bartog košarice: prilepiš/naložiš sliko (print screen),
   OCR prebere vrstice (naziv + ID), jih razvrsti v FO/FZ/FG/FK/… in
   po potrditvi vpiše ID v ustrezno polje ter obkljuka postavko. */
(function () {
  "use strict";

  // Razvrščanje naziva → ključ postavke (preverja po vrsti, prvi zadetek velja)
  const RULES = [
    [/filter(ja)?\s+olj/i,            "FO"],
    [/oljn[ai]\s+filter/i,            "FO"],
    [/filter(ja)?\s+zrak/i,           "FZ"],
    [/zra[čc]n[ai]\s+filter/i,        "FZ"],
    [/filter(ja)?\s+gori/i,           "FG"],
    [/filter\s+kabin/i,              "FK"],
    [/kabinsk[ia]\s+filter/i,         "FK"],
    [/filter\s+(notranjega\s+)?prostora/i, "FK"],
    [/sve[čc]k/i,                     "SVECKE"],
    [/\bolje\b/i,                     "OLJE"],
    [/motorno\s+olje/i,               "OLJE"],
    // Veliki servis
    [/jermen.*vodn[oai].*[čc]rpalk/i, "GZVC"],
    [/set.*vodn[ao].*[čc]rpalk/i,     "GZVC"],
    [/(zobat|pogonsk).*jermen.*set/i, "GZ"],
    [/jermensk[ia]\s+set/i,           "GZ"],
    [/jermen/i,                       "GZ"],
    [/napenjal/i,                     "NAPENJALEC"],
    [/drsnik/i,                       "DRSNIK"],
    [/mikro.*jermen|set\s+mikro/i,    "SET_MIKRO"],
    // Zavore
    [/zavorn[ae]\s+plo[šs][čc].*spred|plo[šs][čc].*spred/i, "PD"],
    [/zavorn[ae]\s+plo[šs][čc].*zad|plo[šs][čc].*zad/i,     "ZD"],
    [/zavorn[ae]\s+plo[šs][čc]/i,     "PD"],
    [/zavorn[ai]\s+disk.*spred|disk.*spred/i, "PP"],
    [/zavorn[ai]\s+disk.*zad|disk.*zad/i,     "ZP"],
    [/zavorn[ai]\s+disk|kolut/i,      "PP"],
    [/zavorn[ai]\s+cilind/i,          "ZAV_CILINDRI"],
    [/ferod/i,                        "FERODE"],
    [/zavorn[ae]\s+[čc]eljust.*spred/i, "PD_CELJUST"],
    [/zavorn[ae]\s+[čc]eljust.*zad/i,   "ZD_CELJUST"],
    [/ro[čc]n[ae].*[žz]ic|[žz]ice\s+ro[čc]n/i, "ZICE_ROCNE"],
    // Volan / podvozje
    [/volansk[ia]\s+kon[čc]nik.*lev/i, "VOL_KONCNIK_L"],
    [/volansk[ia]\s+kon[čc]nik.*desn/i, "VOL_KONCNIK_D"],
    [/volansk[ia]\s+kon[čc]nik/i,     "VOL_KONCNIK_L"],
    [/spona\s+volan/i,                "SPONA_VOLANA"],
    [/man[šs]et.*zunan/i,             "MANSETA_ZUN"],
    [/man[šs]et.*notran/i,            "MANSETA_NOT"],
    [/man[šs]et.*volan/i,             "MANSETA_VOLANA"],
    [/kolesn[ia]\s+le[žz]aj.*spred|le[žz]aj.*spred/i, "LEZAJ_SP"],
    [/kolesn[ia]\s+le[žz]aj.*zad|le[žz]aj.*zad/i,     "LEZAJ_ZA"],
    [/le[žz]aj/i,                     "LEZAJ_SP"],
  ];

  function classify(name) {
    for (const [re, key] of RULES) if (re.test(name)) return key;
    return null;
  }

  // Iz OCR besedila izlušči vrstice (naziv + ID)
  function parseLines(text) {
    const lines = (text || "").split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const out = [];
    let lastName = "";
    for (const ln of lines) {
      // ID: 20957  ali  ID 20957
      const idm = ln.match(/\bID\s*[:.]?\s*(\d{4,8})\b/i);
      // čista številka v vrstici (6-mestna) kot rezerva
      const numOnly = ln.match(/^(\d{5,8})$/);
      if (idm) {
        const name = ln.slice(0, idm.index).trim() || lastName;
        out.push({ name: name, id: idm[1] });
        lastName = "";
      } else if (numOnly && lastName) {
        out.push({ name: lastName, id: numOnly[1] });
        lastName = "";
      } else if (!/dob\.?\s*[šs]ifr/i.test(ln) && /[a-zA-ZčšžČŠŽ]/.test(ln)) {
        // verjetno naziv izdelka (preskočimo vrstico „Dob. šifra")
        lastName = ln;
      }
    }
    return out;
  }

  const KEY_LABEL = window.CATALOG_LABELS || {};

  function run(file, statusEl, tableEl, applyBtn) {
    statusEl.innerHTML = '<i class="bi bi-arrow-repeat"></i> Berem sliko… (nekaj sekund)';
    tableEl.innerHTML = ""; applyBtn.style.display = "none";
    Tesseract.recognize(file, "slv+eng").then(({ data: { text } }) => {
      const rows = parseLines(text);
      if (!rows.length) {
        statusEl.innerHTML = '<span class="text-danger">Iz slike nisem prebral nobenega ID. Poskusi bolj ostro sliko ali vpiši ročno.</span>';
        return;
      }
      let html = '<table class="table table-sm align-middle"><thead><tr>'
        + '<th>Iz slike</th><th>ID</th><th style="width:200px">Postavka</th></tr></thead><tbody>';
      rows.forEach((r, i) => {
        const guess = classify(r.name);
        html += `<tr>
          <td class="small">${escapeHtml(r.name)}</td>
          <td><input class="form-control form-control-sm bi-id" value="${escapeHtml(r.id)}" style="width:100px"></td>
          <td><select class="form-select form-select-sm bi-key">
            <option value="">— ne uvozi —</option>
            ${Object.keys(KEY_LABEL).map(k =>
              `<option value="${k}" ${k === guess ? "selected" : ""}>${escapeHtml(KEY_LABEL[k])}</option>`).join("")}
          </select></td></tr>`;
      });
      html += "</tbody></table>";
      tableEl.innerHTML = html;
      const matched = rows.filter(r => classify(r.name)).length;
      statusEl.innerHTML = `<span class="text-success">Prebrano: ${rows.length} vrstic, predlagano razvrščenih: ${matched}.</span> Preveri in po potrebi popravi, nato „Vpiši v naročilo".`;
      applyBtn.style.display = "";
    }).catch(() => {
      statusEl.innerHTML = '<span class="text-danger">Napaka pri branju slike.</span>';
    });
  }

  function apply(tableEl, statusEl) {
    let n = 0;
    tableEl.querySelectorAll("tbody tr").forEach(tr => {
      const key = tr.querySelector(".bi-key").value;
      const id = tr.querySelector(".bi-id").value.trim();
      if (!key || !id) return;
      const row = document.querySelector(`.ci-row[data-key="${key}"]`);
      if (!row) return;
      const cb = row.querySelector(".ci-cb");
      if (cb) { cb.checked = true; cb.dispatchEvent(new Event("change", { bubbles: true })); }
      const ident = row.querySelector(`[name="ident_${key}"]`);
      if (ident) ident.value = id;
      n++;
    });
    statusEl.innerHTML = `<span class="text-success"><i class="bi bi-check-circle"></i> Vpisanih ${n} postavk. Preveri spodaj v „Postavke naročila".</span>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  }

  // Inicializacija (paste + upload)
  window.BartogImport = {
    init() {
      const drop = document.getElementById("bi-drop");
      const fileInput = document.getElementById("bi-file");
      const statusEl = document.getElementById("bi-status");
      const tableEl = document.getElementById("bi-table");
      const applyBtn = document.getElementById("bi-apply");
      if (!drop) return;

      function handle(file) { if (file) run(file, statusEl, tableEl, applyBtn); }

      drop.addEventListener("click", () => fileInput.click());
      fileInput.addEventListener("change", e => handle(e.target.files[0]));
      document.addEventListener("paste", e => {
        const items = (e.clipboardData || {}).items || [];
        for (const it of items) {
          if (it.type && it.type.indexOf("image") === 0) { handle(it.getAsFile()); break; }
        }
      });
      drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("bi-over"); });
      drop.addEventListener("dragleave", () => drop.classList.remove("bi-over"));
      drop.addEventListener("drop", e => {
        e.preventDefault(); drop.classList.remove("bi-over");
        if (e.dataTransfer.files[0]) handle(e.dataTransfer.files[0]);
      });
      applyBtn.addEventListener("click", () => apply(tableEl, statusEl));
    }
  };
})();
