from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, DeliveryStop, Customer, DELIVERY_ROUTES, DELIVERY_ROUTE_DICT

delivery_bp = Blueprint("delivery", __name__, url_prefix="/dostava")


def _route_label(key):
    return DELIVERY_ROUTE_DICT.get(key, key)


@delivery_bp.route("/")
@login_required
def overview():
    counts = {}
    for key, _ in DELIVERY_ROUTES:
        counts[key] = DeliveryStop.query.filter_by(route=key, done=False).count()
    return render_template("delivery/overview.html",
                           routes=DELIVERY_ROUTES, counts=counts)


@delivery_bp.route("/<route_key>")
@login_required
def route_view(route_key):
    if route_key not in DELIVERY_ROUTE_DICT:
        flash("Neznana ruta.", "danger")
        return redirect(url_for("delivery.overview"))
    stops = (DeliveryStop.query
             .filter_by(route=route_key)
             .order_by(DeliveryStop.done.asc(), DeliveryStop.position.asc(), DeliveryStop.id.asc())
             .all())
    return render_template("delivery/route.html",
                           route_key=route_key,
                           route_label=_route_label(route_key),
                           routes=DELIVERY_ROUTES,
                           stops=stops,
                           customers=Customer.query.order_by(Customer.name).all())


@delivery_bp.route("/<route_key>/add", methods=["POST"])
@login_required
def add_stop(route_key):
    if route_key not in DELIVERY_ROUTE_DICT:
        flash("Neznana ruta.", "danger")
        return redirect(url_for("delivery.overview"))
    customer = request.form.get("customer", "").strip()
    if not customer:
        flash("Vpiši ime stranke.", "danger")
        return redirect(url_for("delivery.route_view", route_key=route_key))
    maxpos = db.session.query(db.func.max(DeliveryStop.position)).filter_by(route=route_key).scalar() or 0
    db.session.add(DeliveryStop(
        route=route_key,
        customer=customer,
        address=request.form.get("address", "").strip(),
        phone=request.form.get("phone", "").strip(),
        note=request.form.get("note", "").strip(),
        tires=request.form.get("tires", "").strip(),
        position=maxpos + 1,
    ))
    db.session.commit()
    flash("Stranka dodana na ruto.", "success")
    return redirect(url_for("delivery.route_view", route_key=route_key))


@delivery_bp.route("/stop/<int:stop_id>/move", methods=["POST"])
@login_required
def move_stop(stop_id):
    stop = DeliveryStop.query.get_or_404(stop_id)
    direction = request.form.get("dir")
    siblings = (DeliveryStop.query
                .filter_by(route=stop.route)
                .order_by(DeliveryStop.position.asc(), DeliveryStop.id.asc())
                .all())
    idx = next((i for i, s in enumerate(siblings) if s.id == stop.id), None)
    if idx is not None:
        swap = idx - 1 if direction == "up" else idx + 1
        if 0 <= swap < len(siblings):
            siblings[idx].position, siblings[swap].position = siblings[swap].position, siblings[idx].position
            db.session.commit()
    return redirect(url_for("delivery.route_view", route_key=stop.route))


@delivery_bp.route("/stop/<int:stop_id>/toggle", methods=["POST"])
@login_required
def toggle_stop(stop_id):
    stop = DeliveryStop.query.get_or_404(stop_id)
    stop.done = not stop.done
    db.session.commit()
    return redirect(request.referrer or url_for("delivery.route_view", route_key=stop.route))


@delivery_bp.route("/stop/<int:stop_id>/delete", methods=["POST"])
@login_required
def delete_stop(stop_id):
    stop = DeliveryStop.query.get_or_404(stop_id)
    route_key = stop.route
    db.session.delete(stop)
    db.session.commit()
    flash("Stranka odstranjena z rute.", "info")
    return redirect(url_for("delivery.route_view", route_key=route_key))


@delivery_bp.route("/<route_key>/print")
@login_required
def print_route(route_key):
    if route_key not in DELIVERY_ROUTE_DICT:
        flash("Neznana ruta.", "danger")
        return redirect(url_for("delivery.overview"))
    stops = (DeliveryStop.query
             .filter_by(route=route_key, done=False)
             .order_by(DeliveryStop.position.asc(), DeliveryStop.id.asc())
             .all())
    return render_template("delivery/print.html",
                           route_label=_route_label(route_key),
                           stops=stops)
