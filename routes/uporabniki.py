"""Čiščenje uporabnikov – varno brisanje računov.

Zakaj posebna stran: uporabnika ni mogoče kar izbrisati. Na njem visijo
naročila, ure, dopusti, beležke … Naročilo ima polje `employee_id` označeno
kot OBVEZNO, zato bi brisanje uporabnika z naročili bodisi vrglo napako
bodisi pustilo naročila brez lastnika – in strani z naročili bi se sesule.

Zato ta stran za vsakega uporabnika prešteje VSE, kar je nanj vezano, in
gumb za brisanje pokaže samo tam, kjer ni nič poslovnega. Kjer je, ponudi
deaktivacijo – račun ostane, prijava ni več mogoča, zgodovina pa se ohrani.

Dostop: samo admin.  Naslov: /uporabniki/pocisti
"""
from flask import (Blueprint, render_template_string, redirect, url_for,
                   flash, request, abort)
from flask_login import login_required, current_user

from models import (db, User, Order, OrderStatusLog, Note, ChatMessage,
                    PushSubscription, LeaveEntry, WorkHours, MonthLock)

uporabniki_bp = Blueprint("uporabniki", __name__, url_prefix="/uporabniki")

# Modeli iz moto platforme niso povsod prisotni – uvozimo jih previdno.
_MOTO = []
for ime in ("MotoOrder", "MotoRezervacija", "MotoBelezka"):
    try:
        import models as _m
        razred = getattr(_m, ime, None)
        if razred is not None:
            _MOTO.append(razred)
    except Exception:
        pass


def _samo_admin():
    if not getattr(current_user, "is_admin", False):
        abort(403)


def _stetje(u):
    """Prešteje vse, kar visi na uporabniku.

    Vrne (poslovno, osebno) – slovarja {opis: število}.
    „Poslovno" brisanje PREPREČI, „osebno" se pobriše skupaj z računom.
    """
    def n(q):
        try:
            return q.count()
        except Exception:
            return 0

    poslovno = {
        "naročila":            n(Order.query.filter_by(employee_id=u.id)),
        "zapisi o statusih":   n(OrderStatusLog.query.filter_by(changed_by_id=u.id)),
        "beležke":             n(Note.query.filter_by(created_by_id=u.id)),
        "ure":                 n(WorkHours.query.filter_by(user_id=u.id)),
        "dopusti":             n(LeaveEntry.query.filter_by(user_id=u.id)),
        "zaklenjeni meseci":   n(MonthLock.query.filter_by(user_id=u.id)),
    }
    for razred in _MOTO:
        for polje in ("created_by_id", "zaposleni_id", "avtor_id"):
            if hasattr(razred, polje):
                kljuc = "moto: " + razred.__name__
                poslovno[kljuc] = poslovno.get(kljuc, 0) + n(
                    razred.query.filter(getattr(razred, polje) == u.id))

    osebno = {
        "sporočila v klepetu": n(ChatMessage.query.filter(
            (ChatMessage.partner_id == u.id) | (ChatMessage.sender_id == u.id))),
        "naprave za obvestila": n(PushSubscription.query.filter_by(user_id=u.id)),
    }
    return poslovno, osebno


def _zakaj_ne(u, poslovno):
    """Vrne razlog, zakaj uporabnika NI mogoče izbrisati, ali None."""
    if u.id == current_user.id:
        return "To si ti – svojega računa ne moreš izbrisati."
    skupaj = sum(poslovno.values())
    if skupaj:
        deli = [f"{v} × {k}" for k, v in poslovno.items() if v]
        return "Na računu visi: " + ", ".join(deli) + "."
    if u.is_admin:
        preostali = User.query.filter(User.is_admin.is_(True), User.id != u.id).count()
        if preostali == 0:
            return "To je zadnji administrator."
    return None


@uporabniki_bp.route("/pocisti")
@login_required
def pocisti():
    _samo_admin()
    vrstice = []
    for u in User.query.order_by(User.full_name).all():
        poslovno, osebno = _stetje(u)
        vrstice.append({
            "u": u,
            "poslovno": poslovno,
            "osebno": osebno,
            "poslovno_skupaj": sum(poslovno.values()),
            "osebno_skupaj": sum(osebno.values()),
            "ovira": _zakaj_ne(u, poslovno),
        })
    return render_template_string(STRAN, vrstice=vrstice)


@uporabniki_bp.route("/<int:user_id>/izbrisi", methods=["POST"])
@login_required
def izbrisi(user_id):
    _samo_admin()
    u = User.query.get_or_404(user_id)

    # Ponovno preverimo tik pred brisanjem – med ogledom strani se je lahko
    # kaj spremenilo (nekdo mu je medtem pripisal naročilo).
    poslovno, _ = _stetje(u)
    ovira = _zakaj_ne(u, poslovno)
    if ovira:
        flash(f"Uporabnika „{u.full_name}“ nisem izbrisal. {ovira}", "danger")
        return redirect(url_for("uporabniki.pocisti"))

    # Varovalka: ime v obrazcu se mora ujemati – da se ne zgodi napačen klik
    if (request.form.get("potrdi_ime") or "").strip() != (u.full_name or "").strip():
        flash("Ime se ni ujemalo, zato nisem ničesar izbrisal.", "warning")
        return redirect(url_for("uporabniki.pocisti"))

    ime = u.full_name
    try:
        ChatMessage.query.filter(
            (ChatMessage.partner_id == u.id) | (ChatMessage.sender_id == u.id)
        ).delete(synchronize_session=False)
        PushSubscription.query.filter_by(user_id=u.id).delete(synchronize_session=False)
        db.session.delete(u)
        db.session.commit()
        flash(f"Uporabnik „{ime}“ je izbrisan.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Brisanje ni uspelo: {e}", "danger")
    return redirect(url_for("uporabniki.pocisti"))


@uporabniki_bp.route("/<int:user_id>/deaktiviraj", methods=["POST"])
@login_required
def deaktiviraj(user_id):
    _samo_admin()
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash("Sebe ne moreš deaktivirati.", "danger")
        return redirect(url_for("uporabniki.pocisti"))
    u.is_active_user = not bool(u.is_active_user)
    db.session.commit()
    flash(("Račun „%s“ je spet aktiven." if u.is_active_user
           else "Račun „%s“ je deaktiviran – prijava ni več mogoča.") % u.full_name,
          "success")
    return redirect(url_for("uporabniki.pocisti"))


STRAN = """{% extends 'base.html' %}
{% block title %}Čiščenje uporabnikov{% endblock %}
{% block content %}
<div class="container-fluid px-0">
  <h5 class="mb-1"><i class="bi bi-people me-2"></i>Čiščenje uporabnikov</h5>
  <p class="text-muted small">
    Uporabnika je mogoče izbrisati samo, če nanj ni vezano nič poslovnega.
    Kjer je, račun <b>deaktiviraj</b> – prijava ni več mogoča, zgodovina pa ostane.
  </p>

  <div class="table-responsive">
  <table class="table table-sm align-middle bg-white">
    <thead class="table-light">
      <tr>
        <th>Ime</th><th>Uporabniško ime</th><th>Vloga</th><th>Stanje</th>
        <th>Vezano na račun</th><th style="width:230px"></th>
      </tr>
    </thead>
    <tbody>
    {% for r in vrstice %}
      <tr>
        <td class="fw-semibold">{{ r.u.full_name }}</td>
        <td><code>{{ r.u.username }}</code></td>
        <td><span class="badge bg-secondary">{{ r.u.role }}</span></td>
        <td>
          {% if r.u.is_active_user %}<span class="badge bg-success">Aktiven</span>
          {% else %}<span class="badge bg-dark">Deaktiviran</span>{% endif %}
        </td>
        <td class="small">
          {% if r.poslovno_skupaj %}
            {% for k, v in r.poslovno.items() %}{% if v %}
              <span class="badge bg-warning text-dark me-1">{{ v }} {{ k }}</span>
            {% endif %}{% endfor %}
          {% else %}
            <span class="text-muted">nič poslovnega</span>
          {% endif %}
          {% if r.osebno_skupaj %}
            <div class="text-muted mt-1" style="font-size:.78rem">
              se pobriše skupaj:
              {% for k, v in r.osebno.items() %}{% if v %}{{ v }} {{ k }}{{ ", " if not loop.last }}{% endif %}{% endfor %}
            </div>
          {% endif %}
        </td>
        <td class="text-end">
          <form method="POST" action="{{ url_for('uporabniki.deaktiviraj', user_id=r.u.id) }}"
                class="d-inline">
            <button class="btn btn-sm btn-outline-secondary">
              {{ "Aktiviraj" if not r.u.is_active_user else "Deaktiviraj" }}
            </button>
          </form>
          {% if r.ovira %}
            <button class="btn btn-sm btn-outline-danger" disabled
                    title="{{ r.ovira }}">Izbriši</button>
          {% else %}
            <form method="POST" action="{{ url_for('uporabniki.izbrisi', user_id=r.u.id) }}"
                  class="d-inline"
                  onsubmit="return confirm('Res izbrišem uporabnika {{ r.u.full_name }}?\\n\\nTega ni mogoče razveljaviti.');">
              <input type="hidden" name="potrdi_ime" value="{{ r.u.full_name }}">
              <button class="btn btn-sm btn-danger">Izbriši</button>
            </form>
          {% endif %}
        </td>
      </tr>
      {% if r.ovira and r.poslovno_skupaj %}
      <tr class="table-light">
        <td colspan="6" class="small text-muted py-1">
          <i class="bi bi-info-circle me-1"></i>{{ r.ovira }}
          Brisanje bi odneslo tudi te zapise, zato ni dovoljeno.
        </td>
      </tr>
      {% endif %}
    {% endfor %}
    </tbody>
  </table>
  </div>
</div>
{% endblock %}
"""
