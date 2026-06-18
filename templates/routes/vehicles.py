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
    url = f"{VPIC_BASE}/getmodelsformake/{urllib.parse.quote(make_q)}?format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "narocilnice"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        names = sorted({
            (row.get("Model_Name") or "").strip()
            for row in data.get("Results", [])
            if row.get("Model_Name")
        })
        return jsonify({"ok": True, "models": names})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "models": []}), 502


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
