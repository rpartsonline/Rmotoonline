from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import (
    db, Order, OrderItem, OrderStatusLog,
    Customer, Vehicle,
    ORDER_STATUSES, STATUS_DICT, ITEM_STATUSES, ITEM_STATUS_DICT,
    ORDER_SOURCES, ITEM_UNITS,
)

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


# ── Helper ────────────────────────────────────────────────────────────────────

def generate_order_number():
    year = datetime.utcnow().year
    last = (
        Order.query
        .filter(Order.order_number.like(f"NAR-{year}-%"))
        .order_by(Order.id.desc())
        .first()
    )
    if last:
        try:
            num = int(last.order_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = Order.query.count() + 1
    else:
        num = 1
    return f"NAR-{year}-{num:04d}"


# ── List ──────────────────────────────────────────────────────────────────────

@orders_bp.route("/")
@login_required
def list_orders():
    status_filter   = request.args.get("status", "")
    customer_filter = request.args.get("customer_id", "")
    date_from_str   = request.args.get("date_from", "")
    date_to_str     = request.args.get("date_to", "")
    search          = request.args.get("search", "").strip()

    q = Order.query

    if status_filter:
        q = q.filter_by(status=status_filter)
    if customer_filter:
        q = q.filter_by(customer_id=int(customer_filter))
    if date_from_str:
        try:
            q = q.filter(Order.created_at >= datetime.strptime(date_from_str, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to_str:
        try:
            dt_to = datetime.strptime(date_to_str, "%Y-%m-%d") + timedelta(days=1)
            q = q.filter(Order.created_at < dt_to)
        except ValueError:
            pass
    if search:
        q = q.filter(Order.order_number.ilike(f"%{search}%"))

    orders    = q.order_by(Order.created_at.desc()).all()
    customers = Customer.query.order_by(Customer.name).all()

    return render_template(
        "orders/list.html",
        orders=orders,
        customers=customers,
        statuses=ORDER_STATUSES,
        STATUS_DICT=STATUS_DICT,
        status_filter=status_filter,
        customer_filter=customer_filter,
        date_from=date_from_str,
        date_to=date_to_str,
        search=search,
    )


# ── New order ─────────────────────────────────────────────────────────────────

@orders_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_order():
    if request.method == "POST":
        f = request.form

        # ── Stranka ──────────────────────────────────────────────────────────
        customer_id = f.get("customer_id", "").strip()
        if not customer_id or customer_id == "new":
            name = f.get("new_customer_name", "").strip()
            if not name:
                flash("Ime stranke je obvezno.", "danger")
                return _render_new_order_form()
            customer = Customer(
                name    = name,
                phone   = f.get("new_customer_phone", "").strip(),
                email   = f.get("new_customer_email", "").strip(),
                address = f.get("new_customer_address", "").strip(),
            )
            db.session.add(customer)
            db.session.flush()
            customer_id = customer.id
        else:
            customer_id = int(customer_id)

        # ── Vozilo ───────────────────────────────────────────────────────────
        vehicle_id = f.get("vehicle_id", "").strip()
        if not vehicle_id or vehicle_id == "new":
            brand = f.get("new_vehicle_brand", "").strip()
            model = f.get("new_vehicle_model", "").strip()
            if brand and model:
                year_raw = f.get("new_vehicle_year", "").strip()
                vehicle = Vehicle(
                    customer_id         = customer_id,
                    brand               = brand,
                    model               = model,
                    vin                 = f.get("new_vehicle_vin",          "").strip() or None,
                    year                = int(year_raw) if year_raw.isdigit() else None,
                    engine_type         = f.get("new_vehicle_engine_type",  "").strip(),
                    engine_displacement = f.get("new_vehicle_displacement", "").strip(),
                    engine_power_kw     = f.get("new_vehicle_power",        "").strip(),
                    registration        = f.get("new_vehicle_registration", "").strip(),
                )
                db.session.add(vehicle)
                db.session.flush()
                vehicle_id = vehicle.id
            else:
                vehicle_id = None
        elif vehicle_id == "none":
            vehicle_id = None
        else:
            vehicle_id = int(vehicle_id)

        # ── Naročilo ─────────────────────────────────────────────────────────
        order = Order(
            order_number = generate_order_number(),
            customer_id  = customer_id,
            vehicle_id   = vehicle_id,
            employee_id  = current_user.id,
            status       = "novo",
            source       = f.get("source", "klic"),
            notes        = f.get("notes", "").strip(),
        )
        db.session.add(order)
        db.session.flush()

        # ── Postavke ─────────────────────────────────────────────────────────
        descs     = f.getlist("item_description[]")
        b_ids     = f.getlist("item_bartog_id[]")
        qtys      = f.getlist("item_quantity[]")
        units     = f.getlist("item_unit[]")
        suppliers = f.getlist("item_supplier[]")
        i_notes   = f.getlist("item_notes[]")

        for idx, desc in enumerate(descs):
            if not desc.strip():
                continue
            qty_raw = qtys[idx] if idx < len(qtys) else "1"
            try:
                qty = float(qty_raw)
            except ValueError:
                qty = 1.0
            item = OrderItem(
                order_id    = order.id,
                description = desc.strip(),
                bartog_id   = b_ids[idx].strip()     if idx < len(b_ids)     else "",
                quantity    = qty,
                unit        = units[idx]              if idx < len(units)     else "kos",
                supplier    = suppliers[idx].strip()  if idx < len(suppliers) else "Bartog",
                notes       = i_notes[idx].strip()    if idx < len(i_notes)   else "",
                status      = "caka",
            )
            db.session.add(item)

        db.session.commit()
        flash(f"Naročilo {order.order_number} je bilo uspešno ustvarjeno.", "success")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    return _render_new_order_form()


def _render_new_order_form():
    return render_template(
        "orders/new.html",
        customers  = Customer.query.order_by(Customer.name).all(),
        sources    = ORDER_SOURCES,
        item_units = ITEM_UNITS,
        preselected_customer = request.args.get("customer_id"),
        preselected_vehicle  = request.args.get("vehicle_id"),
    )


# ── Detail ────────────────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template(
        "orders/detail.html",
        order        = order,
        statuses     = ORDER_STATUSES,
        item_statuses= ITEM_STATUSES,
        STATUS_DICT  = STATUS_DICT,
    )


# ── Update order status ───────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/status", methods=["POST"])
@login_required
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status  = request.form.get("status")
    valid_keys  = [s[0] for s in ORDER_STATUSES]

    if new_status not in valid_keys:
        flash("Neveljaven status.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))

    log = OrderStatusLog(
        order_id      = order.id,
        old_status    = order.status,
        new_status    = new_status,
        changed_by_id = current_user.id,
        notes         = request.form.get("status_note", "").strip(),
    )
    db.session.add(log)

    if new_status == "naroceno" and not order.ordered_at:
        order.ordered_at = datetime.utcnow()
    if new_status == "zakljuceno" and not order.completed_at:
        order.completed_at = datetime.utcnow()

    order.status     = new_status
    order.updated_at = datetime.utcnow()
    db.session.commit()

    flash(f"Status posodobljen → {STATUS_DICT[new_status]['label']}", "success")
    return redirect(url_for("orders.order_detail", order_id=order_id))


# ── Update item status ────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/item/<int:item_id>/status", methods=["POST"])
@login_required
def update_item_status(order_id, item_id):
    item = OrderItem.query.get_or_404(item_id)
    if item.order_id != order_id:
        flash("Napaka.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))

    new_status = request.form.get("status")
    if new_status in [s[0] for s in ITEM_STATUSES]:
        item.status = new_status
        db.session.commit()

    return redirect(url_for("orders.order_detail", order_id=order_id))


# ── Delete order (admin only) ─────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    if not current_user.is_admin:
        flash("Samo administratorji lahko brišejo naročila.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))
    num = order.order_number
    db.session.delete(order)
    db.session.commit()
    flash(f"Naročilo {num} je bilo izbrisano.", "info")
    return redirect(url_for("orders.list_orders"))


# ── AJAX: vehicles for customer ───────────────────────────────────────────────

@orders_bp.route("/api/customer/<int:customer_id>/vehicles")
@login_required
def get_customer_vehicles(customer_id):
    vehicles = Vehicle.query.filter_by(customer_id=customer_id).all()
    return jsonify([
        {
            "id":           v.id,
            "name":         v.display_name,
            "brand":        v.brand,
            "model":        v.model,
            "year":         v.year,
            "vin":          v.vin or "",
            "registration": v.registration or "",
            "engine_type":  v.engine_type or "",
        }
        for v in vehicles
    ])
