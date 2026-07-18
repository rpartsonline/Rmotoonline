from functools import wraps
from datetime import date, datetime
from calendar import month_abbr
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import (db, MotoOrder, MOTO_ORDER_STATUSES, MOTO_ORDER_STATUS_DICT, MOTO_BRANDS,
                    MotoRezervacija, MOTO_STORITVE, MOTO_STORITEV_DICT,
                    MOTO_REZ_STATUS, MOTO_REZ_STATUS_DICT,
                    MotoBelezka, MOTO_STAFF_NAMES)

moto_bp = Blueprint("moto", __name__, url_prefix="/moto")


def moto_access_required(f):
    """Admin ali moto zaposleni (Mojca, Ervin)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.is_admin or current_user.full_name in MOTO_STAFF_NAMES:
            return f(*args, **kwargs)
        flash("Dostop samo za moto osobje.", "danger")
        return redirect(url_for("main.dashboard"))
    return decorated


def is_moto_staff():
    return current_user.is_authenticated and (
        current_user.is_admin or current_user.full_name in MOTO_STAFF_NAMES
    )


# ── Naročila ──────────────────────────────────────────────────────────────────

@moto_bp.route("/")
@login_required
@moto_access_required
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
    counts = {s[0]: MotoOrder.query.filter_by(status=s[0]).count() for s in MOTO_ORDER_STATUSES}
    counts["vse"] = MotoOrder.query.count()
    return render_template("moto/narocila.html",
        orders=orders, counts=counts, status_filter=status_filter, q=q,
        statuses=MOTO_ORDER_STATUSES, status_dict=MOTO_ORDER_STATUS_DICT, brands=MOTO_BRANDS)


@moto_bp.route("/novo", methods=["POST"])
@login_required
@moto_access_required
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
@moto_access_required
def update_status(order_id):
    o = MotoOrder.query.get_or_404(order_id)
    new_status = request.form.get("status")
    if new_status in MOTO_ORDER_STATUS_DICT:
        o.status = new_status
        db.session.commit()
    return redirect(request.referrer or url_for("moto.narocila"))


@moto_bp.route("/<int:order_id>/uredi", methods=["GET", "POST"])
@login_required
@moto_access_required
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
@moto_access_required
def izbrisi(order_id):
    o = MotoOrder.query.get_or_404(order_id)
    db.session.delete(o)
    db.session.commit()
    flash("Naročilo izbrisano.", "info")
    return redirect(url_for("moto.narocila"))


# ── Storitve (skupne funkcije) ────────────────────────────────────────────────

def _storitev_page(vrsta):
    """Skupna logika za vse storitve (ebike, moto, pnevmatika)."""
    info = MOTO_STORITEV_DICT.get(vrsta, {})
    tab = request.args.get("tab", "rezervacije")

    # Rezervacije
    q = MotoRezervacija.query.filter_by(vrsta=vrsta)
    status_f = request.args.get("status", "")
    if status_f:
        q = q.filter_by(status=status_f)
    rezervacije = q.order_by(MotoRezervacija.datum.desc(), MotoRezervacija.cas_od).all()

    # Analize po mesecih (zadnjih 12 mesecev)
    now = datetime.utcnow()
    meseci = []
    for i in range(11, -1, -1):
        m = (now.month - i - 1) % 12 + 1
        y = now.year - ((now.month - i - 1) // 12)
        count = MotoRezervacija.query.filter_by(vrsta=vrsta).filter(
            db.extract("year", MotoRezervacija.datum) == y,
            db.extract("month", MotoRezervacija.datum) == m,
        ).count()
        meseci.append({"mesec": f"{m:02d}/{y}", "kratko": f"{month_abbr[m]} {y}", "stevilo": count})

    return render_template("moto/storitve/storitev.html",
        vrsta=vrsta, info=info, tab=tab,
        rezervacije=rezervacije, meseci=meseci,
        statusi=MOTO_REZ_STATUS, status_dict=MOTO_REZ_STATUS_DICT,
        status_f=status_f,
        storitve=MOTO_STORITVE)


@moto_bp.route("/storitev/<vrsta>")
@login_required
@moto_access_required
def storitev(vrsta):
    if vrsta not in MOTO_STORITEV_DICT:
        flash("Neznana storitev.", "danger")
        return redirect(url_for("moto.narocila"))
    return _storitev_page(vrsta)


@moto_bp.route("/storitev/<vrsta>/nova-rezervacija", methods=["POST"])
@login_required
@moto_access_required
def nova_rezervacija(vrsta):
    if vrsta not in MOTO_STORITEV_DICT:
        return redirect(url_for("moto.narocila"))
    stranka = request.form.get("stranka", "").strip()
    datum_raw = request.form.get("datum", "").strip()
    if not stranka or not datum_raw:
        flash("Ime stranke in datum sta obvezna.", "danger")
        return redirect(url_for("moto.storitev", vrsta=vrsta, tab="rezervacije"))
    try:
        datum = date.fromisoformat(datum_raw)
    except ValueError:
        flash("Napačen datum.", "danger")
        return redirect(url_for("moto.storitev", vrsta=vrsta, tab="rezervacije"))
    r = MotoRezervacija(
        vrsta=vrsta,
        stranka=stranka,
        telefon=request.form.get("telefon", "").strip() or None,
        datum=datum,
        cas_od=request.form.get("cas_od", "").strip() or None,
        cas_do=request.form.get("cas_do", "").strip() or None,
        opomba=request.form.get("opomba", "").strip() or None,
        status="potrjena",
        zaposleni_id=current_user.id,
    )
    db.session.add(r)
    db.session.commit()
    flash("✅ Rezervacija dodana.", "success")
    return redirect(url_for("moto.storitev", vrsta=vrsta, tab="rezervacije"))


@moto_bp.route("/storitev/<vrsta>/rez/<int:rez_id>/status", methods=["POST"])
@login_required
@moto_access_required
def rez_status(vrsta, rez_id):
    r = MotoRezervacija.query.get_or_404(rez_id)
    new_s = request.form.get("status")
    if new_s in MOTO_REZ_STATUS_DICT:
        r.status = new_s
        db.session.commit()
    return redirect(url_for("moto.storitev", vrsta=vrsta, tab="rezervacije"))


@moto_bp.route("/storitev/<vrsta>/rez/<int:rez_id>/izbrisi", methods=["POST"])
@login_required
@moto_access_required
def rez_izbrisi(vrsta, rez_id):
    r = MotoRezervacija.query.get_or_404(rez_id)
    db.session.delete(r)
    db.session.commit()
    flash("Rezervacija izbrisana.", "info")
    return redirect(url_for("moto.storitev", vrsta=vrsta, tab="rezervacije"))


# ── Beležka (samo moto osobje) ───────────────────────────────────────────────

@moto_bp.route("/belezka")
@login_required
@moto_access_required
def belezka():
    zapisi = MotoBelezka.query.order_by(MotoBelezka.updated_at.desc()).all()
    return render_template("moto/belezka.html", zapisi=zapisi)


@moto_bp.route("/belezka/nova", methods=["POST"])
@login_required
@moto_access_required
def belezka_nova():
    vsebina = request.form.get("vsebina", "").strip()
    if not vsebina:
        flash("Vsebina ne sme biti prazna.", "danger")
        return redirect(url_for("moto.belezka"))
    z = MotoBelezka(vsebina=vsebina, avtor_id=current_user.id)
    db.session.add(z)
    db.session.commit()
    flash("✅ Zapis dodan.", "success")
    return redirect(url_for("moto.belezka"))


@moto_bp.route("/belezka/<int:zapis_id>/izbrisi", methods=["POST"])
@login_required
@moto_access_required
def belezka_izbrisi(zapis_id):
    z = MotoBelezka.query.get_or_404(zapis_id)
    db.session.delete(z)
    db.session.commit()
    flash("Zapis izbrisan.", "info")
    return redirect(url_for("moto.belezka"))


# ── Platform select ───────────────────────────────────────────────────────────

@moto_bp.route("/platforma")
@login_required
def platform_select():
    return render_template("platform_select.html")
