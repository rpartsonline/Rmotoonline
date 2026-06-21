from datetime import datetime, timedelta

from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from models import Order, Customer, Vehicle, STATUS_DICT

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
    today_orders = Order.query.filter(
        Order.created_at >= start, Order.created_at < end
    ).count()

    new_orders       = Order.query.filter_by(status="novo").count()
    completed_orders = Order.query.filter_by(status="zakljuceno").count()

    # Aktivna naročila (še v teku) – za seznam odprtih spodaj
    active_orders = Order.query.filter(
        Order.status.in_(["caka", "naroceno", "v_dostavi"])
    ).count()

    # Števila po statusu
    status_counts = {}
    for key, info in STATUS_DICT.items():
        status_counts[key] = {
            **info,
            "count": Order.query.filter_by(status=key).count(),
        }

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    pending_orders = (
        Order.query
        .filter(Order.status.in_(["caka", "naroceno", "v_dostavi"]))
        .order_by(Order.created_at.asc())
        .all()
    )

    return render_template(
        "dashboard.html",
        today_orders=today_orders,
        new_orders=new_orders,
        completed_orders=completed_orders,
        active_orders=active_orders,
        today_str=_today_str(),
        status_counts=status_counts,
        recent_orders=recent_orders,
        pending_orders=pending_orders,
    )


@main_bp.route("/api/new-orders-count")
@login_required
def new_orders_count():
    return jsonify({"count": Order.query.filter_by(status="novo").count()})
