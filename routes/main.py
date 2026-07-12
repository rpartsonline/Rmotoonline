from datetime import datetime, timedelta

from flask import Blueprint, render_template, jsonify, redirect, url_for, request, session
from flask_login import login_required, current_user
from models import Order, Customer, Vehicle, STATUS_DICT, INQUIRY_STATUSES, Note, NOTE_PEOPLE, INQUIRY_STATUSES

main_bp = Blueprint("main", __name__)


def _ljubljana_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Ljubljana"))
    except Exception:
        return datetime.now()


def _today_str():
    return _ljubljana_now().strftime("%d.%m.%Y")


def _today_utc_range():
    """Začetek in konec današnjega dne (po slovenskem času) v UTC,
    ker se created_at shranjuje kot naivni UTC."""
    try:
        from zoneinfo import ZoneInfo
        now_lj = datetime.now(ZoneInfo("Europe/Ljubljana"))
        start_lj = now_lj.replace(hour=0, minute=0, second=0, microsecond=0)
        end_lj = start_lj + timedelta(days=1)
        start = start_lj.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        end = end_lj.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        return start, end
    except Exception:
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)


@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Kupec ima svojo pozdravno stran
    if getattr(current_user, "role", "") == "kupec":
        return redirect(url_for("main.kupec_home"))
    # Če je izbrana moto platforma → moto naročila
    if session.get("platform") == "moto":
        return redirect(url_for("moto.narocila"))
    start, end = _today_utc_range()
    today_orders = Order.query.filter_by(kind="narocilo").filter(
        Order.created_at >= start, Order.created_at < end
    ).count()

    new_orders     = Order.query.filter_by(kind="narocilo", status="novo").count()
    ordered_orders = Order.query.filter_by(kind="narocilo", status="naroceno").count()

    # Aktivna naročila (še ni naročeno) – za seznam odprtih spodaj
    active_orders = Order.query.filter_by(kind="narocilo").filter(
        Order.status.in_(["novo", "poslano_povprasevanje"])
    ).count()

    # Razčlenitev povpraševanj po 3 statusih
    inquiry_breakdown = []
    for key, label, color in INQUIRY_STATUSES:
        inquiry_breakdown.append({
            "key": key, "label": label, "color": color,
            "count": Order.query.filter_by(kind="povprasevanje", status=key).count(),
        })

    # Beležke – nezaključene po osebi
    note_counts = [
        {"person": p, "count": Note.query.filter_by(person=p, done=False).count()}
        for p in NOTE_PEOPLE
    ]

    recent_orders = (
        Order.query.filter_by(kind="narocilo")
        .order_by(Order.created_at.desc()).limit(10).all()
    )

    pending_orders = (
        Order.query.filter_by(kind="narocilo")
        .filter(Order.status.in_(["novo", "poslano_povprasevanje"]))
        .order_by(Order.created_at.asc())
        .all()
    )

    # Dodatne statistike za dashboard
    from models import Customer, Vehicle
    total_customers = Customer.query.count()
    total_vehicles  = Vehicle.query.count()

    # Status counts za kartice
    try:
        status_counts = {}
        for key, info in STATUS_DICT.items():
            cnt = Order.query.filter_by(kind="narocilo", status=key).count()
            status_counts[key] = {"label": info["label"], "color": info["color"], "count": cnt}
    except Exception:
        status_counts = {}

    total_orders = Order.query.filter_by(kind="narocilo").count()
    # Naročila v obdelavi = status "poslano_povprasevanje" (oranžni)
    orders_v_obdelavi = Order.query.filter_by(
        kind="narocilo", status="poslano_povprasevanje"
    ).count()

    return render_template(
        "dashboard.html",
        today_orders=today_orders,
        new_orders=new_orders,
        ordered_orders=ordered_orders,
        active_orders=active_orders,
        total_orders=total_orders,
        orders_v_obdelavi=orders_v_obdelavi,
        today_str=_today_str(),
        now=_ljubljana_now(),
        total_customers=total_customers,
        total_vehicles=total_vehicles,
        status_counts=status_counts,
        inquiry_breakdown=inquiry_breakdown,
        note_counts=note_counts,
        recent_orders=recent_orders,
        pending_orders=pending_orders,
    )


@main_bp.route("/iskalnik-dobaviteljev")
@login_required
def iskalnik_dobaviteljev():
    return render_template("iskalnik.html")


@main_bp.route("/euroton-isci", methods=["POST"])
@login_required
def euroton_isci():
    """AJAX iskanje po Euroton katalogu."""
    from flask import jsonify
    koda = (request.form.get("koda") or "").strip()
    if not koda:
        return jsonify({"ok": False, "napaka": "Vpiši kodo."})
    try:
        from euroton_scraper import EurotonClient
        client = EurotonClient()
        rez = client.isci(koda)
        return jsonify(rez)
    except Exception as e:
        return jsonify({"ok": False, "napaka": f"Napaka: {e}", "rezultati": []})


@main_bp.route("/zamenjaj-platformo")
@login_required
def zamenjaj_platformo():
    """Preklop platforme (samo admin). Odjavi in vrni na izbiro."""
    if not current_user.is_admin:
        return redirect(url_for("main.dashboard"))
    # Preklopi platformo brez odjave
    cur = session.get("platform", "avto")
    session["platform"] = "moto" if cur == "avto" else "avto"
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dobrodosli")
@login_required
def kupec_home():
    if getattr(current_user, "role", "") != "kupec":
        return redirect(url_for("main.dashboard"))
    recent = (Order.query
              .filter_by(employee_id=current_user.id)
              .order_by(Order.created_at.desc()).limit(5).all())
    open_count = Order.query.filter_by(
        employee_id=current_user.id, kind="narocilo", status="novo").count()
    notif = Order.query.filter_by(
        employee_id=current_user.id, notify_customer=True).count()
    return render_template("kupec_home.html",
                           recent=recent, open_count=open_count, notif=notif)


@main_bp.route("/sw.js")
def service_worker():
    from flask import send_from_directory, current_app
    import os
    resp = send_from_directory(os.path.join(current_app.root_path, "static"), "sw.js")
    resp.headers["Content-Type"] = "application/javascript"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@main_bp.route("/api/new-orders-count")
@login_required
def new_orders_count():
    return jsonify({"count": Order.query.filter_by(kind="narocilo", status="novo").count()})


@main_bp.route("/api/delivery-alert")
@login_required
def delivery_alert():
    from datetime import timedelta
    from models import today_local
    today = today_local()
    tomorrow = today + timedelta(days=1)
    due = (
        Order.query
        .filter_by(kind="povprasevanje", status="narocena_caka")
        .filter(Order.delivery_date.isnot(None))
        .filter(Order.delivery_date <= tomorrow)
        .all()
    )
    return jsonify({
        "count": len(due),
        "red": any(o.delivery_date <= today for o in due),
    })
