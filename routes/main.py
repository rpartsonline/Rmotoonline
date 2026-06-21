from datetime import datetime, timedelta

from flask import Blueprint, render_template, jsonify
from flask_login import login_required
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

    return render_template(
        "dashboard.html",
        today_orders=today_orders,
        new_orders=new_orders,
        ordered_orders=ordered_orders,
        active_orders=active_orders,
        today_str=_today_str(),
        inquiry_breakdown=inquiry_breakdown,
        note_counts=note_counts,
        recent_orders=recent_orders,
        pending_orders=pending_orders,
    )


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
