"""Pošiljanje povpraševanj po e-pošti – s prilogami.

Gumb „Pošlji po mailu" je prej odprl poštni program prek `mailto:`. Tak način
po zasnovi brskalnika NE more pripeti datotek, zato je bilo v sporočilu
napisano, naj se slike pripnejo ročno.

Tu pošto sestavi in odda aplikacija sama, zato gredo slike dela in prometnega
dovoljenja zraven kot prave priloge.

Nastavitve poštnega strežnika pridejo iz okoljskih spremenljivk:
    SMTP_HOST      npr. smtp.gmail.com
    SMTP_PORT      587 (STARTTLS) ali 465 (SSL)
    SMTP_USER      uporabniško ime / e-naslov
    SMTP_PASS      geslo (pri Gmailu „geslo za aplikacije", ne običajno geslo)
    SMTP_FROM      naslov pošiljatelja; če ni, se uporabi SMTP_USER
    SMTP_SECURITY  starttls (privzeto) | ssl | none
    MAIL_DEFAULT_TO  neobvezno: privzeti naslov dobavitelja
"""
import os
import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from models import Order, OrderImage

mail_bp = Blueprint("mail", __name__, url_prefix="/posta")

MAX_SKUPAJ = 20 * 1024 * 1024        # največ 20 MB prilog na sporočilo
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def _cfg():
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587") or 587),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "pass": os.environ.get("SMTP_PASS", ""),
        "from": os.environ.get("SMTP_FROM", "").strip() or os.environ.get("SMTP_USER", "").strip(),
        "sec":  (os.environ.get("SMTP_SECURITY", "starttls") or "starttls").strip().lower(),
        "privzeti": os.environ.get("MAIL_DEFAULT_TO", "").strip(),
        "odgovor": os.environ.get("MAIL_REPLY_TO", "").strip(),
    }


def _nastavljeno(c):
    return bool(c["host"] and c["user"] and c["pass"] and c["from"])


@mail_bp.route("/stanje")
@login_required
def stanje():
    c = _cfg()
    return jsonify({
        "nastavljeno": _nastavljeno(c),
        "posiljatelj": c["from"] if _nastavljeno(c) else "",
        "privzeti": c["privzeti"],
        "odgovor": c["odgovor"] or (c["from"] if _nastavljeno(c) else ""),
    })


def _naslovi(raw):
    """Razbije niz naslovov (vejica, podpičje, presledek) in jih preveri."""
    deli = [d.strip() for d in re.split(r"[,;\s]+", raw or "") if d.strip()]
    veljavni = [d for d in deli if EMAIL_RE.match(d)]
    neveljavni = [d for d in deli if not EMAIL_RE.match(d)]
    return veljavni, neveljavni


@mail_bp.route("/povprasevanje/<int:order_id>", methods=["POST"])
@login_required
def poslji_povprasevanje(order_id):
    if getattr(current_user, "role", "") == "kupec":
        return jsonify({"ok": False, "napaka": "Nimaš dovoljenja za pošiljanje."}), 403

    c = _cfg()
    if not _nastavljeno(c):
        return jsonify({"ok": False, "napaka": "no_smtp"}), 200

    order = Order.query.get_or_404(order_id)
    d = request.get_json(silent=True) or {}

    prejemniki, slabi = _naslovi(d.get("za", ""))
    if slabi:
        return jsonify({"ok": False, "napaka": "Napačen e-naslov: " + ", ".join(slabi)}), 400
    if not prejemniki:
        return jsonify({"ok": False, "napaka": "Vpiši vsaj en e-naslov prejemnika."}), 400

    zadeva = (d.get("zadeva") or "").strip() or f"Povpraševanje {order.order_number}"
    besedilo = (d.get("besedilo") or "").strip()
    if not besedilo:
        return jsonify({"ok": False, "napaka": "Sporočilo je prazno."}), 400

    # Katere slike pripeti – privzeto vse od tega naročila
    izbrane = d.get("slike")
    if isinstance(izbrane, list):
        ids = [int(i) for i in izbrane if str(i).isdigit()]
        if ids:
            slike = (OrderImage.query
                     .filter(OrderImage.order_id == order.id,
                             OrderImage.id.in_(ids))
                     .order_by(OrderImage.id).all())
        else:
            slike = []            # uporabnik je odkljukal vse priloge
    else:
        slike = (OrderImage.query.filter_by(order_id=order.id)
                 .order_by(OrderImage.id).all())

    msg = EmailMessage()
    msg["Subject"] = zadeva
    msg["From"] = formataddr(("Bartog Ajdovščina", c["from"]))
    msg["To"] = ", ".join(prejemniki)
    # Kam naj dobavitelj odgovori. Uporabniki v aplikaciji nimajo svojega
    # e-naslova, zato odgovor privzeto pride na poštni predal podjetja
    # (SMTP_FROM). Z MAIL_REPLY_TO ga lahko preusmeriš kam drugam.
    odgovor = c["odgovor"] or getattr(current_user, "email", None)
    if odgovor:
        msg["Reply-To"] = odgovor
    msg["Message-ID"] = make_msgid()
    msg.set_content(besedilo)

    folder = current_app.config.get("UPLOAD_FOLDER", "")
    pripeto, skupaj, prevelike = 0, 0, []
    for s in slike:
        pot = os.path.join(folder, os.path.basename(s.filename or ""))
        try:
            with open(pot, "rb") as f:
                vsebina = f.read()
        except Exception:
            continue
        if skupaj + len(vsebina) > MAX_SKUPAJ:
            prevelike.append(s.filename)
            continue
        ext = os.path.splitext(s.filename)[1].lower().lstrip(".") or "jpeg"
        if ext == "jpg":
            ext = "jpeg"
        pripeto += 1
        skupaj += len(vsebina)
        msg.add_attachment(vsebina, maintype="image", subtype=ext,
                           filename=f"{order.order_number}_{pripeto}.{ext}")

    try:
        if c["sec"] == "ssl":
            strega = smtplib.SMTP_SSL(c["host"], c["port"], timeout=30)
        else:
            strega = smtplib.SMTP(c["host"], c["port"], timeout=30)
        with strega as s:
            if c["sec"] == "starttls":
                s.starttls()
            s.login(c["user"], c["pass"])
            s.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        return jsonify({"ok": False, "napaka":
                        "Poštni strežnik je zavrnil prijavo. Preveri SMTP_USER in SMTP_PASS "
                        "(pri Gmailu je potrebno geslo za aplikacije)."}), 200
    except Exception as e:
        return jsonify({"ok": False, "napaka": f"Pošte ni bilo mogoče poslati: {e}"}), 200

    return jsonify({
        "ok": True,
        "prejemniki": prejemniki,
        "prilog": pripeto,
        "prevelike": prevelike,
    })
