from flask import Blueprint, render_template
from flask_login import login_required
from models import Order, Customer, Vehicle, STATUS_DICT

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    total_orders    = Order.query.count()
    total_customers = Customer.query.count()
    total_vehicles  = Vehicle.query.count()

    # Aktivna naročila (še v teku)
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

    # Zadnjih 10 naročil
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    # Odprta naročila (za opozorilo)
    pending_orders = (
        Order.query
        .filter(Order.status.in_(["caka", "naroceno", "v_dostavi"]))
        .order_by(Order.created_at.asc())
        .all()
    )

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        total_customers=total_customers,
        total_vehicles=total_vehicles,
        active_orders=active_orders,
        status_counts=status_counts,
        recent_orders=recent_orders,
        pending_orders=pending_orders,
    )
