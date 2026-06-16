from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, Vehicle, Customer, ENGINE_TYPES, TRANSMISSIONS

vehicles_bp = Blueprint("vehicles", __name__, url_prefix="/vehicles")


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


@vehicles_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_vehicle():
    customers = Customer.query.order_by(Customer.name).all()
    preselected = request.args.get("customer_id", "")

    if request.method == "POST":
        customer_id = request.form.get("customer_id", "").strip()
        if not customer_id:
            flash("Izberite stranko.", "danger")
            return render_template("vehicles/new.html", customers=customers,
                                   vehicle=None, engine_types=ENGINE_TYPES,
                                   transmissions=TRANSMISSIONS, preselected_customer=preselected)

        vehicle = _vehicle_from_form(request.form, int(customer_id))
        if not vehicle.brand or not vehicle.model:
            flash("Znamka in model sta obvezna.", "danger")
            return render_template("vehicles/new.html", customers=customers,
                                   vehicle=None, engine_types=ENGINE_TYPES,
                                   transmissions=TRANSMISSIONS, preselected_customer=customer_id)

        db.session.add(vehicle)
        db.session.commit()
        flash(f"Vozilo {vehicle.display_name} je bilo dodano.", "success")
        return redirect(url_for("customers.customer_detail", customer_id=vehicle.customer_id))

    return render_template("vehicles/new.html", customers=customers,
                           vehicle=None, engine_types=ENGINE_TYPES,
                           transmissions=TRANSMISSIONS, preselected_customer=preselected)


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

    return render_template("vehicles/new.html", customers=customers,
                           vehicle=vehicle, engine_types=ENGINE_TYPES,
                           transmissions=TRANSMISSIONS,
                           preselected_customer=vehicle.customer_id)
