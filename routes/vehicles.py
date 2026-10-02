import json
import unicodedata
import urllib.parse
import urllib.request

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from models import db, Vehicle, Customer, ENGINE_TYPES, TRANSMISSIONS

vehicles_bp = Blueprint("vehicles", __name__, url_prefix="/vehicles")

VPIC_BASE = "https://vpic.nhtsa.dot.gov/api/vehicles"

# Pogoste znamke (za spustni seznam). Delavec lahko vpiše tudi svojo.
CAR_MAKES = [
    "Alfa Romeo", "Audi", "BMW", "Citroën", "Cupra", "Dacia", "DS", "Fiat",
    "Ford", "Honda", "Hyundai", "Jaguar", "Jeep", "Kia", "Lancia",
    "Land Rover", "Lexus", "Mazda", "Mercedes-Benz", "Mini", "Mitsubishi",
    "Nissan", "Opel", "Peugeot", "Porsche", "Renault", "Seat", "Škoda",
    "Smart", "SsangYong", "Subaru", "Suzuki", "Tesla", "Toyota",
    "Volkswagen", "Volvo", "Chevrolet", "Chrysler", "Dodge", "Saab",
    "Iveco", "MAN", "DAF", "Scania", "Maserati", "Bentley", "Ferrari",
    "Lamborghini", "Abarth", "Infiniti", "Genesis", "BYD", "MG",
]


# ── Pomožne funkcije za preslikavo vPIC → naše vrednosti ──────────────────────

def _strip_diacritics(text):
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def _map_fuel(value):
    v = (value or "").lower()
    if "diesel" in v:
        return "diesel"
    if "electric" in v and ("gasol" in v or "hybrid" in v):
        return "hibrid"
    if "electric" in v:
        return "elektro"
    if "hybrid" in v:
        return "hibrid"
    if any(g in v for g in ("compressed natural", "propane", "lpg", "cng", "natural gas")):
        return "plin"
    if "gasol" in v or "petrol" in v or "flex" in v:
        return "bencin"
    return ""


def _map_transmission(value):
    v = (value or "").lower()
    if "manual" in v and "auto" in v:
        return "poluavtomatski"
    if "manual" in v:
        return "ročni"
    if "auto" in v or "cvt" in v or "dual" in v:
        return "avtomatski"
    return ""


def _hp_to_kw(hp):
    try:
        return str(round(float(hp) * 0.7457))
    except (TypeError, ValueError):
        return ""


def _vehicle_from_form(f, customer_id, vehicle=None):
    """Fill vehicle object from form data."""
    if vehicle is None:
        vehicle = Vehicle(customer_id=customer_id)
    year_raw = f.get("year", "").strip()
    vehicle.brand               = f.get("brand",               "").strip()
    vehicle.model               = f.get("model",               "").strip()
    vehicle.vin                 = f.get("vin",                 "").strip() or None
    vehicle.year                = int(year_raw) if year_raw.isdigit() else None
    vehicle.engine_type         = f.get("engine_type",         "").strip()
    vehicle.engine_displacement = f.get("engine_displacement", "").strip()
    vehicle.engine_power_kw     = f.get("engine_power_kw",    "").strip()
    vehicle.transmission        = f.get("transmission",        "").strip()
    vehicle.color               = f.get("color",               "").strip()
    vehicle.registration        = f.get("registration",        "").strip()
    vehicle.notes               = f.get("notes",               "").strip()
    return vehicle


def _render_form(vehicle, customers, preselected):
    return render_template(
        "vehicles/new.html",
        customers=customers,
        vehicle=vehicle,
        engine_types=ENGINE_TYPES,
        transmissions=TRANSMISSIONS,
        car_makes=CAR_MAKES,
        preselected_customer=preselected,
    )


@vehicles_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_vehicle():
    customers = Customer.query.order_by(Customer.name).all()
    preselected = request.args.get("customer_id", "")

    if request.method == "POST":
        customer_id = request.form.get("customer_id", "").strip()
        if not customer_id:
            flash("Izberite stranko.", "danger")
            return _render_form(None, customers, preselected)

        vehicle = _vehicle_from_form(request.form, int(customer_id))
        if not vehicle.brand or not vehicle.model:
            flash("Znamka in model sta obvezna.", "danger")
            return _render_form(None, customers, customer_id)

        db.session.add(vehicle)
        db.session.commit()
        flash(f"Vozilo {vehicle.display_name} je bilo dodano.", "success")
        return redirect(url_for("customers.customer_detail", customer_id=vehicle.customer_id))

    return _render_form(None, customers, preselected)


@vehicles_bp.route("/<int:vehicle_id>")
@login_required
def vehicle_detail(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    return render_template("vehicles/detail.html", vehicle=vehicle)


@vehicles_bp.route("/<int:vehicle_id>/edit", methods=["GET", "POST"])
@login_required
def edit_vehicle(vehicle_id):
    vehicle   = Vehicle.query.get_or_404(vehicle_id)
    customers = Customer.query.order_by(Customer.name).all()

    if request.method == "POST":
        vehicle = _vehicle_from_form(request.form, vehicle.customer_id, vehicle)
        if not vehicle.brand or not vehicle.model:
            flash("Znamka in model sta obvezna.", "danger")
        else:
            db.session.commit()
            flash("Podatki vozila so bili posodobljeni.", "success")
            return redirect(url_for("vehicles.vehicle_detail", vehicle_id=vehicle.id))

    return _render_form(vehicle, customers, vehicle.customer_id)


# ── API: modeli za znamko (vPIC) ──────────────────────────────────────────────

@vehicles_bp.route("/api/models/<make>")
@login_required
def api_models(make):
    make_q = _strip_diacritics(make).strip()

    def _fetch_models(url):
        req = urllib.request.Request(url, headers={"User-Agent": "narocilnice"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        return {
            (row.get("Model_Name") or "").strip()
            for row in data.get("Results", [])
            if row.get("Model_Name")
        }

    base_url = f"{VPIC_BASE}/getmodelsformake/{urllib.parse.quote(make_q)}?format=json"
    # Samo motorna kolesa za to znamko – da jih lahko odštejemo (Avto platforma → brez motorjev)
    moto_url = (f"{VPIC_BASE}/getmodelsformakeyear/make/"
                f"{urllib.parse.quote(make_q)}/vehicletype/motorcycle?format=json")

    try:
        all_models = _fetch_models(base_url)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "models": []}), 502

    # Odstrani motorna kolesa. Če ta poizvedba ne uspe, raje pokažemo vse
    # (bolje kot da bi funkcija padla in ne bi bilo nobenih modelov).
    try:
        moto_models = _fetch_models(moto_url)
    except Exception:
        moto_models = set()

    moto_lower = {m.lower() for m in moto_models}
    names = sorted(m for m in all_models if m.lower() not in moto_lower)
    return jsonify({"ok": True, "models": names})


# ── API: razčlenjevanje VIN (vPIC) ────────────────────────────────────────────

@vehicles_bp.route("/api/vin/<vin>")
@login_required
def api_decode_vin(vin):
    vin = vin.strip().upper()
    url = f"{VPIC_BASE}/decodevinvalues/{urllib.parse.quote(vin)}?format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "narocilnice"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        res = (data.get("Results") or [{}])[0]

        power = (res.get("EngineKW") or "").strip()
        if not power:
            power = _hp_to_kw(res.get("EngineHP"))

        return jsonify({
            "ok": True,
            "make":         (res.get("Make") or "").title().strip(),
            "model":        (res.get("Model") or "").strip(),
            "year":         (res.get("ModelYear") or "").strip(),
            "engine_type":  _map_fuel(res.get("FuelTypePrimary")),
            "displacement": (res.get("DisplacementL") or "").strip(),
            "power_kw":     power,
            "transmission": _map_transmission(res.get("TransmissionStyle")),
            "body":         (res.get("BodyClass") or "").strip(),
            "error":        (res.get("ErrorText") or "").strip(),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


# ── Branje VIN iz slike prek Google Cloud Vision (z dnevno omejitvijo) ─────────
import os
import re
import base64
from datetime import date

_vision_quota = {"day": None, "count": 0}

# ── Preverjanje kontrolne številke VIN (ISO 3779, 9. znak) ────────────────────
# Pravi VIN ima kontrolni znak na 9. mestu. Če se ujema, je skoraj gotovo pravi.
# (Nekateri evropski VIN-i ga ne upoštevajo, zato ga uporabimo le kot močan namig,
#  ne kot izločitveni pogoj.)
_VIN_TRANS = {**{str(d): d for d in range(10)},
              "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
              "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
              "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9}
_VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def _vin_check_valid(vin):
    if len(vin) != 17:
        return False
    total = 0
    for ch, w in zip(vin, _VIN_WEIGHTS):
        if ch not in _VIN_TRANS:
            return False
        total += _VIN_TRANS[ch] * w
    r = total % 11
    check = "X" if r == 10 else str(r)
    return vin[8] == check


# Napisi s prometnega dovoljenja in tablic, ki NISO VIN. Odstranimo jih iz
# besedila, preden iščemo številko – sicer iz samih črk napisa (I→1, O→0)
# nastane niz, ki je na pogled videti kot VIN.
_LABEL_RE = re.compile(
    r"IDENTIFIKAC\w*|[ŠS]TEVILK\w*|VOZIL\w*|LETO|IZDELAV\w*|PROMETN\w*|"
    r"DOVOLJENJ\w*|REGISTRSK\w*|VELJAVN\w*|LASTNI\w*|SEDE[ŽZ]\w*|"
    r"TIP|VARIANTA|IZVEDBA|ZNAMKA|MODEL|BARVA|MASA|NAJVE[ČC]J\w*|"
    r"VIN|CHASSIS|FAHRGESTELL|FRAME\s*N[OR]\w*"
)


# Oznaka, ki na tablici ali v dovoljenju stoji tik pred šasijsko številko.
# Kar ji sledi, je skoraj zagotovo VIN – to je najmočnejši posamičen namig.
_LABEL_NEAR_RE = re.compile(
    r"(?:VIN|CHASSIS|FAHRGESTELL(?:NUMMER)?|[ŠS]ASIJ\w*|"
    r"IDENTIFIKACIJSK\w*(?:\s+[ŠS]TEVILK\w*)?)"
    r"[\s:.–—-]*(?P<val>[A-Z0-9][A-Z0-9 \-]{15,34})"
)

_VIN_SHAPE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def _vin_substitute(s):
    """VIN nima črk I, O in Q – vedno so to števke."""
    return s.replace("I", "1").replace("O", "0").replace("Q", "0")


def _emit_windows(raw_chunk, bonus, offer):
    """Vsa 17-znakovna okna v nizu, ki so po obliki lahko VIN."""
    sub = _vin_substitute(raw_chunk)        # pretvorba je znak za znak – indeksi se ujemajo
    for i in range(0, max(0, len(sub) - 16)):
        w = sub[i:i + 17]
        if not _VIN_SHAPE.match(w):
            continue
        digits = sum(c.isdigit() for c in w)
        letters = 17 - digits
        # „Native" so števke, ki so bile števke že pred pretvorbo I→1 / O→0.
        # Brez tega pogoja bi iz besedila „REPUBLIKA SLOVENIJA" nastal
        # navidezni VIN.
        native = sum(c.isdigit() for c in raw_chunk[i:i + 17])
        if native < 2 or digits < 3 or letters < 3:
            continue
        offer(w, bonus)


def _vin_candidates(text):
    """Iz besedila izlušči vse verjetne 17-mestne VIN kandidate, urejene po
    oceni (najboljši prvi).

    Posnetek sme vsebovati poljubno drugo besedilo – registrsko, kode delov,
    datume, številko homologacije. Pravi VIN prepoznamo po tem, da:
      • stoji kot samostojen 17-znakovni blok (ne izrezan iz daljšega niza),
      • mu včasih neposredno predhodi oznaka (VIN, šasija, Fahrgestell …),
      • ustreza obliki VIN (brez I/O/Q, veljavno leto, zaporedna št. na koncu).
    """
    if not text:
        return []

    upper = text.upper()

    bonus = {}

    def offer(vin, b):
        if b > bonus.get(vin, -999):
            bonus[vin] = b

    # 1) Številka tik za oznako – najmočnejši namig
    labelled = {}
    for m in _LABEL_NEAR_RE.finditer(upper):
        val = re.sub(r"[^A-Z0-9]", "", m.group("val"))
        _emit_windows(val, 0, lambda v, _b: labelled.setdefault(v, True))

    # 2) Po vrsticah: sosednje bloke znakov združujemo, ker OCR VIN pogosto
    #    razbije s presledkom (npr. „WVWZZZ1KZ AW000001").
    cleaned = _LABEL_RE.sub(" ", upper)
    for line in cleaned.splitlines():
        runs = re.findall(r"[A-Z0-9]+", line)
        for i in range(len(runs)):
            if len(runs[i]) > 30:
                # Zelo dolg niz – VIN je lahko le del njega, zato z odbitkom.
                _emit_windows(runs[i], -8, offer)
                continue
            total = ""
            for j in range(i, len(runs)):
                total += runs[j]
                if len(total) > 30:
                    break
                if len(total) < 17:
                    continue
                if len(total) == 17:
                    b = 30          # samostojen blok točno 17 znakov
                elif len(total) <= 20:
                    b = 10
                else:
                    b = 0           # izrezan iz daljše kaše – brez prednosti
                _emit_windows(total, b, offer)

    # 3) Če po vrsticah ni nič, poskusi čez celotno besedilo
    if not bonus:
        _emit_windows(re.sub(r"[^A-Z0-9]", "", cleaned), -5, offer)

    def total_score(v):
        return _vin_score(v) + bonus[v] + (25 if v in labelled else 0)

    return sorted(bonus, key=total_score, reverse=True)


def _vin_cleanup(text):
    """Združljivost nazaj: vrne enega, najboljšega kandidata."""
    c = _vin_candidates(text)
    return c[0] if c else ""


# Znane predpone proizvajalcev (WMI) – močan namig, da gre res za VIN.
KNOWN_WMI = (
    "WVW", "WVG", "WV1", "WV2", "WAU", "WA1", "TRU", "WME", "W0L", "W0V", "VXK",
    "WBA", "WBS", "WBY", "4US", "5UX", "WBX",
    "WDB", "WDC", "WDD", "WDF", "W1K", "W1N", "W1V", "W1T", "VSA",
    "VF1", "VF3", "VF7", "VF6", "VF8", "VF9", "VR1", "VR3", "VR7",
    "ZFA", "ZFF", "ZAR", "ZAC", "ZAM", "ZFC",
    "TMB", "TMP", "TMK", "TMA", "TMH",
    "VSS", "VSK", "VSE", "VSX",
    "SB1", "SJN", "JTD", "JTM", "JT1", "JTE", "JHM", "JHL", "SHH", "SHS", "NLA",
    "KMH", "KNA", "KNB", "KNE", "U5Y", "U6Y", "KNM", "VNK",
    "1C4", "SAL", "SAJ", "SAD", "SCA", "SCB",
    "YV1", "YV4", "YS3", "YK1",
    "LVS", "LGX", "LC0", "LSV", "L6T", "LB3",
    "MA1", "MA3", "MAT", "MEE", "ML3",
    "3VW", "9BW", "8AW", "93Y", "935", "936", "8A1", "9BD",
    "ZDM", "ZD4", "ZKH", "JYA", "JS1", "JKA", "VTT", "MLH", "VBK",
    "WP0", "WP1", "WF0", "WFO", "VNE", "VN1", "NM0", "ZCF", "ZAP",
    "1HG", "2HG", "3HG", "19X", "2HK", "5J6", "5FN", "1FA", "1FT",
    "1G1", "1GC", "1N4", "5N1", "4T1", "5TD", "2T1", "1C6", "3C4",
)


def _vin_score(v):
    """Oceni, kako verjetno je niz pravi VIN."""
    if not v or len(v) != 17:
        return -100
    digits = sum(ch.isdigit() for ch in v)
    letters = 17 - digits
    s = 0
    if _vin_check_valid(v):
        s += 40
    if v[:3] in KNOWN_WMI:
        s += 25
    if 3 <= digits <= 12:
        s += 5
    if 5 <= letters <= 14:
        s += 5
    # 10. znak je leto izdelave – nikoli I, O, Q, U, Z ali 0
    if v[9] in "ABCDEFGHJKLMNPRSTVWXY123456789":
        s += 3
    # Zadnjih šest znakov je zaporedna številka vozila – pri skoraj vseh
    # proizvajalcih same števke. Vsaka črka tam je znak napačnega branja.
    s -= 3 * sum(ch.isalpha() for ch in v[11:])
    # pet enakih znakov zapored je skoraj zagotovo napaka branja
    if re.search(r"(.)\1{4,}", v):
        s -= 15
    return s


# Znaki, ki jih OCR najpogosteje zamenja med sabo.
_CONFUSIONS = {
    "8": "B", "B": "8",
    "5": "S", "S": "5",
    "2": "Z", "Z": "2",
    "6": "G", "G": "6",
    "4": "A", "A": "4",
    "0": "D", "D": "0",
    "7": "T", "T": "7",
    "1": "7",
}


def _vin_repair(vin):
    """Popravek ene same napačno prebrane črke s pomočjo kontrolne številke.

    Uporabimo ga SAMO, kadar je 9. znak števka ali X – takrat gre res za
    kontrolno številko. Veliko evropskih vozil ima tam polnilo (npr. „Z") in
    kontrolne številke sploh nima, zato tam ne popravljamo ničesar.

    Vrne (popravljen_vin, izvirnik) ali (None, None), če popravek ni enoličen.
    """
    if len(vin) != 17 or vin[8] not in "0123456789X":
        return (None, None)
    if _vin_check_valid(vin):
        return (None, None)

    fixes = []
    for i, ch in enumerate(vin):
        if i == 8:
            continue
        alt = _CONFUSIONS.get(ch)
        if not alt:
            continue
        cand = vin[:i] + alt + vin[i + 1:]
        if re.match(r"^[A-HJ-NPR-Z0-9]{17}$", cand) and _vin_check_valid(cand):
            fixes.append(cand)

    fixes = list(dict.fromkeys(fixes))
    if not fixes:
        return (None, None)
    if len(fixes) == 1:
        return (fixes[0], vin)

    # Več možnih popravkov: odloči ocena, ob tem pa upoštevaj, da je zadnjih
    # šest znakov zaporedna številka vozila in so skoraj vedno same števke.
    def rank(v):
        return (_vin_score(v), -sum(c.isalpha() for c in v[11:]))

    fixes.sort(key=rank, reverse=True)
    if rank(fixes[0]) > rank(fixes[1]):
        return (fixes[0], vin)
    return (None, None)   # dvoumno – raje pustimo, kar smo prebrali


def _vision_text(api_key, img_b64, feature="TEXT_DETECTION"):
    """Pošlje eno sliko v Google Vision in vrne prebrano besedilo.

    Google zaračuna vsako lastnost (feature) posebej, zato pošljemo samo eno:
      TEXT_DETECTION          – redko besedilo na fotografiji (tablica z VIN)
      DOCUMENT_TEXT_DETECTION – gosto besedilo (prometno dovoljenje)
    """
    payload = json.dumps({
        "requests": [{
            "image": {"content": img_b64},
            "features": [{"type": feature}],
            "imageContext": {"languageHints": ["en", "sl"]},
        }]
    }).encode()

    url = f"https://vision.googleapis.com/v1/images:annotate?key={urllib.parse.quote(api_key)}"
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        res = json.loads(r.read().decode())
    anno = (res.get("responses") or [{}])[0]
    text = (anno.get("fullTextAnnotation") or {}).get("text", "")
    if not text:
        ta = anno.get("textAnnotations") or []
        text = ta[0].get("description", "") if ta else ""
    return text


@vehicles_bp.route("/api/vin-ocr", methods=["POST"])
@login_required
def api_vin_ocr():
    """Prebere VIN z ene ali več slik.

    Sprejme {"image": "<dataURL>"} (staro) ali {"images": [...], "prior": [...]}.
    Pri več slikah o rezultatu glasujemo: ista napaka se na različnih posnetkih
    redko ponovi, zato je najpogostejši odgovor skoraj vedno pravi.
    """
    api_key = os.environ.get("GOOGLE_VISION_API_KEY", "").strip()
    if not api_key:
        return jsonify({"ok": False, "error": "no_key"}), 200  # rezerva (Tesseract) pri odjemalcu

    data = request.get_json(silent=True) or {}
    images = data.get("images")
    if not images:
        one = data.get("image")
        images = [one] if one else []
    if not isinstance(images, list):
        images = [images]
    images = [i for i in images if i][:4]        # največ 4 slike na zahtevo
    if not images:
        return jsonify({"ok": False, "error": "no_image"}), 400

    # Katero branje je za ta posnetek bolj primerno. Drugo uporabimo le, če
    # prvo ne najde ničesar – tako v običajnem primeru porabimo eno enoto.
    if (data.get("mode") or "plate") == "document":
        features = ("DOCUMENT_TEXT_DETECTION", "TEXT_DETECTION")
    else:
        features = ("TEXT_DETECTION", "DOCUMENT_TEXT_DETECTION")

    # Dnevna varnostna omejitev (šteje se vsak klic na Vision)
    try:
        limit = int(os.environ.get("VISION_DAILY_LIMIT", "200"))
    except ValueError:
        limit = 200
    today = date.today().isoformat()
    if _vision_quota["day"] != today:
        _vision_quota["day"] = today
        _vision_quota["count"] = 0
    if _vision_quota["count"] >= limit:
        return jsonify({"ok": False, "error": "daily_limit"}), 200

    votes = {}
    raw_seen = ""
    errors = []
    tried = 0

    def add_vote(vin, weight):
        if vin:
            votes[vin] = votes.get(vin, 0) + weight

    # Kandidati iz prejšnjega kroga (odjemalec jih pošlje, da glasujemo skupaj)
    for p in (data.get("prior") or [])[:4]:
        if isinstance(p, str) and len(p) == 17:
            add_vote(p.upper(), 1)

    for img in images:
        b64 = (img or "").split(",")[-1]
        if not b64:
            continue
        tried += 1
        for feat in features:
            if _vision_quota["count"] >= limit:
                break
            try:
                text = _vision_text(api_key, b64, feat)
                _vision_quota["count"] += 1
            except Exception as e:
                errors.append(str(e))
                break
            if text and not raw_seen:
                raw_seen = text
            cands = _vin_candidates(text)
            if cands:
                # Prvi kandidat šteje polno, drugi pol – da ne izgubimo bližnjih
                for idx, c in enumerate(cands[:2]):
                    add_vote(c, 1 if idx == 0 else 0.5)
                break          # našli smo; drugega načina branja ne rabimo

    if not votes:
        if errors and len(errors) >= tried > 0:
            return jsonify({"ok": False, "error": errors[0]}), 502
        if _vision_quota["count"] >= limit:
            return jsonify({"ok": False, "error": "daily_limit"}), 200
        return jsonify({"ok": False, "error": "no_vin", "raw": raw_seen[:200]})

    # Zmaga največ glasov; ob izenačenju odloči ocena (kontrolna št., WMI …)
    best = max(votes.items(), key=lambda kv: (kv[1], _vin_score(kv[0])))
    vin, n_votes = best[0], best[1]

    # Enkratni popravek po kontrolni številki (le kjer ta sploh obstaja)
    corrected_from = None
    fixed, orig = _vin_repair(vin)
    if fixed:
        corrected_from, vin = orig, fixed

    valid = _vin_check_valid(vin)
    return jsonify({
        "ok": True,
        "vin": vin,
        "valid": valid,
        "votes": int(n_votes) if float(n_votes).is_integer() else n_votes,
        "confident": bool(valid or vin[:3] in KNOWN_WMI or n_votes >= 2),
        "corrected": corrected_from,
        "candidates": sorted(votes, key=lambda k: (votes[k], _vin_score(k)), reverse=True)[:4],
    })
