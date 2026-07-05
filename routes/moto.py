from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, MotoOrder, MOTO_ORDER_STATUSES, MOTO_ORDER_STATUS_DICT, MOTO_BRANDS

moto_bp = Blueprint("moto", __name__, url_prefix="/moto")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Dostop samo za administratorje.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return decorated


@moto_bp.route("/")
@login_required
@admin_required
def narocila():
    status_filter = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    query = MotoOrder.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if q:
        query = query.filter(
            db.or_(
                MotoOrder.stranka.ilike(f"%{q}%"),
                MotoOrder.model_motorja.ilike(f"%{q}%"),
                MotoOrder.nadomestni_del.ilike(f"%{q}%"),
                MotoOrder.znamka.ilike(f"%{q}%"),
            )
        )
    orders = query.order_by(MotoOrder.created_at.desc()).all()
    counts = {s[0]: MotoOrder.query.filter_by(status=s[0]).count()
              for s in MOTO_ORDER_STATUSES}
    counts["vse"] = MotoOrder.query.count()
    return render_template(
        "moto/narocila.html",
        orders=orders,
        counts=counts,
        status_filter=status_filter,
        q=q,
        statuses=MOTO_ORDER_STATUSES,
        status_dict=MOTO_ORDER_STATUS_DICT,
        brands=MOTO_BRANDS,
    )


@moto_bp.route("/novo", methods=["POST"])
@login_required
@admin_required
def novo():
    stranka = request.form.get("stranka", "").strip()
    nadomestni_del = request.form.get("nadomestni_del", "").strip()
    if not stranka or not nadomestni_del:
        flash("Ime stranke in nadomestni del sta obvezni polji.", "danger")
        return redirect(url_for("moto.narocila"))
    letnik_raw = request.form.get("letnik", "").strip()
    o = MotoOrder(
        stranka=stranka,
        telefon=request.form.get("telefon", "").strip() or None,
        znamka=request.form.get("znamka", "").strip() or None,
        model_motorja=request.form.get("model_motorja", "").strip() or None,
        letnik=int(letnik_raw) if letnik_raw.isdigit() else None,
        nadomestni_del=nadomestni_del,
        opomba=request.form.get("opomba", "").strip() or None,
        status="cakanje",
        created_by_id=current_user.id,
    )
    db.session.add(o)
    db.session.commit()
    flash("✅ Naročilo dodano.", "success")
    return redirect(url_for("moto.narocila"))


@moto_bp.route("/<int:order_id>/status", methods=["POST"])
@login_required
@admin_required
def update_status(order_id):
    o = MotoOrder.query.get_or_404(order_id)
    new_status = request.form.get("status")
    if new_status in MOTO_ORDER_STATUS_DICT:
        o.status = new_status
        db.session.commit()
    return redirect(request.referrer or url_for("moto.narocila"))


@moto_bp.route("/<int:order_id>/uredi", methods=["GET", "POST"])
@login_required
@admin_required
def uredi(order_id):
    o = MotoOrder.query.get_or_404(order_id)
    if request.method == "POST":
        stranka = request.form.get("stranka", "").strip()
        nadomestni_del = request.form.get("nadomestni_del", "").strip()
        if not stranka or not nadomestni_del:
            flash("Ime stranke in nadomestni del sta obvezni polji.", "danger")
            return redirect(url_for("moto.uredi", order_id=order_id))
        letnik_raw = request.form.get("letnik", "").strip()
        o.stranka = stranka
        o.telefon = request.form.get("telefon", "").strip() or None
        o.znamka = request.form.get("znamka", "").strip() or None
        o.model_motorja = request.form.get("model_motorja", "").strip() or None
        o.letnik = int(letnik_raw) if letnik_raw.isdigit() else None
        o.nadomestni_del = nadomestni_del
        o.opomba = request.form.get("opomba", "").strip() or None
        o.status = request.form.get("status", o.status)
        db.session.commit()
        flash("✅ Naročilo posodobljeno.", "success")
        return redirect(url_for("moto.narocila"))
    return render_template("moto/uredi.html", o=o,
                           statuses=MOTO_ORDER_STATUSES, brands=MOTO_BRANDS)


@moto_bp.route("/<int:order_id>/izbrisi", methods=["POST"])
@login_required
@admin_required
def izbrisi(order_id):
    o = MotoOrder.query.get_or_404(order_id)
    db.session.delete(o)
    db.session.commit()
    flash("Naročilo izbrisano.", "info")
    return redirect(url_for("moto.narocila"))


# ── Stub routsi za storitve (placeholder strani) ─────────────────────────────

@moto_bp.route("/pnevmatike")
@login_required
@admin_required
def pnevmatike():
    return render_template("moto/storitev.html",
                           naslov="Menjava pnevmatik",
                           ikona="bi-circle",
                           opis="Evidenca menjav pnevmatik – v pripravi.")


@moto_bp.route("/rent-ebike")
@login_required
@admin_required
def rent_ebike():
    return render_template("moto/storitev.html",
                           naslov="Rent E-Bike",
                           ikona="bi-lightning-charge",
                           opis="Rezervacije izposoje e-koles – v pripravi.")


@moto_bp.route("/rent-motorbike")
@login_required
@admin_required
def rent_motorbike():
    return render_template("moto/storitev.html",
                           naslov="Rent Motorbike",
                           ikona="bi-bicycle",
                           opis="Rezervacije izposoje motorjev – v pripravi.")


@moto_bp.route("/rent-atv")
@login_required
@admin_required
def rent_atv():
    return render_template("moto/storitev.html",
                           naslov="Rent ATV / Quad",
                           ikona="bi-truck",
                           opis="Rezervacije izposoje ATV/Quad vozil – v pripravi.")
