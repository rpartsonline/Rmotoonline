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


def _vin_cleanup(text):
    """Iz besedila Vision izlušči pravi VIN (17 znakov), ne napisa poleg."""
    if not text:
        return ""

    raw_upper = text.upper()

    # Slovenske/oznake besede, ki NISO VIN (da ne zajamemo napisa)
    bad_words = ("IDENTIFIKAC", "STEVILKA", "ŠTEVILKA", "VOZILO", "LETO",
                 "IZDELAVE", "SEDEZ", "SEDEŽ", "PROMETN", "DOVOLJENJ")

    def vin_substitute(s):
        return s.replace("I", "1").replace("O", "0").replace("Q", "0")

    def has_letter_and_digit(s):
        return any(c.isalpha() for c in s) and any(c.isdigit() for c in s)

    candidates = []

    # 1) Najprej po vrsticah – išči vrstico, ki je videti kot VIN
    for line in raw_upper.splitlines():
        # preskoči vrstice z očitnimi napisi
        if any(w in line for w in bad_words):
            continue
        compact = re.sub(r"[^A-Z0-9]", "", vin_substitute(line))
        # drsno okno 17 znakov
        for i in range(0, max(0, len(compact) - 16)):
            w = compact[i:i + 17]
            if re.match(r"^[A-HJ-NPR-Z0-9]{17}$", w) and has_letter_and_digit(w):
                candidates.append(w)

    # 2) Če nič, poskusi čez cel niz (zadnja možnost)
    if not candidates:
        compact = re.sub(r"[^A-Z0-9]", "", vin_substitute(raw_upper))
        for i in range(0, max(0, len(compact) - 16)):
            w = compact[i:i + 17]
            if re.match(r"^[A-HJ-NPR-Z0-9]{17}$", w) and has_letter_and_digit(w):
                candidates.append(w)

    if not candidates:
        return ""

    # Ocenjevanje: VIN ima običajno mešanico črk in števk.
    # Znane WMI predpone evropskih znamk (prvi 3 znaki) → večja verjetnost.
    known_wmi = ("WVW", "WVG", "WV1", "WV2", "WAU", "WA1", "TRU",  # VW/Audi
                 "WBA", "WBS", "WBY", "4US", "5UX",                # BMW
                 "WDB", "WDC", "WDD", "WDF", "W1K", "W1N", "W1V",  # Mercedes
                 "VF1", "VF3", "VF7", "VF6",                       # Renault/Peugeot/Citroen
                 "ZFA", "ZFF", "ZAR",                              # Fiat/Ferrari/Alfa
                 "TMB", "TMP",                                     # Škoda
                 "VSS", "VSK",                                     # Seat/Nissan ES
                 "SB1", "SJN", "JTD", "JTM", "JT1",                # Toyota
                 "KMH", "KNA", "KNB", "U5Y", "TMA",                # Hyundai/Kia
                 "ZAC", "1C4", "SAL", "SAJ",                       # Jeep/LandRover/Jaguar
                 "YV1", "YV4", "VF8", "W0L", "W0V", "VXK")         # Volvo/Opel

    def score(v):
        digits = sum(ch.isdigit() for ch in v)
        letters = 17 - digits
        s = 0
        # Veljavna kontrolna številka (ISO 3779) → skoraj gotovo pravi VIN
        if _vin_check_valid(v):
            s += 40
        # Mešanica črk in števk (pravi VIN)
        if 3 <= digits <= 12:
            s += 5
        if 5 <= letters <= 14:
            s += 5
        # Znana WMI predpona → skoraj gotovo VIN
        if v[:3] in known_wmi:
            s += 20
        # 10. znak (leto) je črka ali številka brez I,O,Q,U,Z,0 → tipično VIN
        year_char = v[9]
        if year_char in "ABCDEFGHJKLMNPRSTVWXY123456789":
            s += 3
        # Kazen če je preveč enega znaka zapored (npr. OCR napaka)
        if re.search(r"(.)\1{4,}", v):
            s -= 10
        return s

    candidates = list(dict.fromkeys(candidates))  # odstrani duplikate, ohrani vrstni red
    candidates.sort(key=score, reverse=True)
    return candidates[0]


@vehicles_bp.route("/api/vin-ocr", methods=["POST"])
@login_required
def api_vin_ocr():
    api_key = os.environ.get("GOOGLE_VISION_API_KEY", "").strip()
    if not api_key:
        return jsonify({"ok": False, "error": "no_key"}), 200  # rezerva (Tesseract) na strani odjemalca

    # Dnevna varnostna omejitev (privzeto 200 poizvedb/dan)
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

    data = request.get_json(silent=True) or {}
    img_b64 = (data.get("image") or "").split(",")[-1]  # odstrani "data:image/...;base64,"
    if not img_b64:
        return jsonify({"ok": False, "error": "no_image"}), 400

    payload = json.dumps({
        "requests": [{
            "image": {"content": img_b64},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
        }]
    }).encode()

    url = f"https://vision.googleapis.com/v1/images:annotate?key={urllib.parse.quote(api_key)}"
    try:
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            res = json.loads(r.read().decode())
        _vision_quota["count"] += 1
        anno = (res.get("responses") or [{}])[0]
        text = (anno.get("fullTextAnnotation") or {}).get("text", "") \
            or (anno.get("textAnnotations") or [{}])[0].get("description", "")
        vin = _vin_cleanup(text)
        if vin:
            return jsonify({"ok": True, "vin": vin, "valid": _vin_check_valid(vin)})
        return jsonify({"ok": False, "error": "no_vin", "raw": text[:200]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502
