"""Klepet med zaposlenimi in mehaniki.

En pogovor na mehanika (vloga „kupec"). Zaposleni vidijo seznam vseh pogovorov
z neprebranimi sporočili, mehanik vidi samo svojega. Sporočila se osvežujejo
s poizvedovanjem vsakih nekaj sekund – za delavnico je to povsem dovolj in
ne zahteva posebne nastavitve strežnika.
"""
import os
import uuid
from datetime import datetime

from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, current_app, send_from_directory, abort,
                   Response)
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename

from models import db, ChatMessage, User

chat_bp = Blueprint("chat", __name__, url_prefix="/klepet")

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"}
MAX_PREVIEW = 70          # koliko znakov zadnjega sporočila pokažemo v seznamu


# ── Pomožno ───────────────────────────────────────────────────────────────────

def _is_partner():
    """Mehanik (kupec) – ima samo svoj pogovor."""
    return getattr(current_user, "role", "") == "kupec"


def _partner_or_403(partner_id):
    """Vrne uporabnika pogovora in preveri, ali ga smem videti."""
    partner = User.query.get_or_404(partner_id)
    if getattr(partner, "role", "") != "kupec":
        abort(404)
    if _is_partner() and partner.id != current_user.id:
        abort(403)
    return partner


# Stolpca za vsebino slike dodamo ob prvi uporabi, da ni treba posegati
# v app.py. Teče enkrat na zagon in na obstoječi bazi ne naredi škode.
_stolpci_urejeni = False


def _zagotovi_stolpce():
    global _stolpci_urejeni
    if _stolpci_urejeni:
        return
    _stolpci_urejeni = True
    try:
        from sqlalchemy import inspect, text as sqltext
        obstojeci = [c["name"] for c in inspect(db.engine).get_columns("chat_messages")]
        narecje = db.engine.dialect.name
        blob = "BYTEA" if narecje == "postgresql" else "BLOB"
        for ime, tip in (("image_data", blob), ("image_mime", "VARCHAR(60)")):
            if ime not in obstojeci:
                db.session.execute(sqltext(
                    f"ALTER TABLE chat_messages ADD COLUMN {ime} {tip}"))
                db.session.commit()
                print(f"✅  Dodan stolpec '{ime}' v tabelo chat_messages.")
    except Exception as e:
        db.session.rollback()
        print(f"⚠️  Stolpcev za slike v klepetu ni bilo mogoče dodati: {e}")


@chat_bp.before_app_request
def _poskrbi_za_bazo():
    """Stolpca dodamo pred PRVO zahtevo, ne šele ob pošiljanju slike.

    Takoj po objavi nova koda bere tudi stolpca image_data in image_mime.
    Če ju v bazi še ni, bi padlo vsako branje klepeta – tudi števec
    neprebranih, ki teče na vsaki strani. Zato migracijo opravimo prej.
    Funkcija se po prvem klicu takoj vrne, zato ne upočasnjuje strani.
    """
    _zagotovi_stolpce()


_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp", ".heic": "image/heic"}

MAX_SLIKA = 8 * 1024 * 1024        # 8 MB na sliko


def _save_image(f):
    """Shrani priloženo sliko.

    Vrne (ime_datoteke, vsebina, mime). Vsebina gre v bazo – tako slika
    preživi objavo tudi, kadar mapa z datotekami ni trajna. Na disk jo
    shranimo še vedno, a če to ne uspe, to ni več usodno.
    """
    prazno = (None, None, None)
    if not f or not getattr(f, "filename", ""):
        return prazno
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return prazno

    try:
        vsebina = f.read()
    except Exception as e:
        print(f"⚠️  Slike v klepetu ni bilo mogoče prebrati: {e}")
        return prazno
    if not vsebina or len(vsebina) > MAX_SLIKA:
        return prazno

    mime = f.mimetype or _MIME.get(ext) or "application/octet-stream"
    name = secure_filename(f"klepet_{uuid.uuid4().hex}{ext}")

    folder = current_app.config.get("UPLOAD_FOLDER", "")
    if folder:
        try:
            with open(os.path.join(folder, name), "wb") as d:
                d.write(vsebina)
        except Exception as e:
            print(f"⚠️  Slike v klepetu ni bilo mogoče zapisati na disk: {e}")

    return name, vsebina, mime


def _msg_json(m):
    return {
        "id": m.id,
        "text": m.text or "",
        "image": url_for("chat.message_image", message_id=m.id) if m.image else None,
        "mine": m.sender_id == current_user.id,
        "from_partner": m.from_partner,
        "sender": (m.sender.full_name if m.sender else "?"),
        "time": (m.created_at.isoformat() if m.created_at else ""),
    }


def _mark_seen(partner_id):
    """Označi nasprotnikova sporočila kot prebrana za tistega, ki gleda."""
    q = ChatMessage.query.filter_by(partner_id=partner_id)
    if _is_partner():
        q = q.filter(ChatMessage.sender_id != partner_id,
                     ChatMessage.seen_by_partner.is_(False))
        changed = q.update({"seen_by_partner": True}, synchronize_session=False)
    else:
        q = q.filter(ChatMessage.sender_id == partner_id,
                     ChatMessage.seen_by_staff.is_(False))
        changed = q.update({"seen_by_staff": True}, synchronize_session=False)
    if changed:
        db.session.commit()


def unread_for(user):
    """Št. neprebranih sporočil za danega uporabnika (za oznako v meniju)."""
    try:
        if getattr(user, "role", "") == "kupec":
            return (ChatMessage.query
                    .filter(ChatMessage.partner_id == user.id,
                            ChatMessage.sender_id != user.id,
                            ChatMessage.seen_by_partner.is_(False))
                    .count())
        return (ChatMessage.query
                .filter(ChatMessage.sender_id == ChatMessage.partner_id,
                        ChatMessage.seen_by_staff.is_(False))
                .count())
    except Exception:
        return 0


# ── Seznam pogovorov ──────────────────────────────────────────────────────────

@chat_bp.route("/")
@login_required
def index():
    # Mehanik gre naravnost v svoj pogovor
    if _is_partner():
        return redirect(url_for("chat.thread", partner_id=current_user.id))

    search = request.args.get("search", "").strip()

    # Zadnje sporočilo in število neprebranih po pogovoru – v dveh poizvedbah,
    # da seznam ostane hiter tudi pri več sto mehanikih.
    last_ids = (db.session.query(func.max(ChatMessage.id))
                .group_by(ChatMessage.partner_id).all())
    last_ids = [r[0] for r in last_ids]
    last_msgs = (ChatMessage.query.filter(ChatMessage.id.in_(last_ids)).all()
                 if last_ids else [])

    unread_rows = (db.session.query(ChatMessage.partner_id, func.count(ChatMessage.id))
                   .filter(ChatMessage.sender_id == ChatMessage.partner_id,
                           ChatMessage.seen_by_staff.is_(False))
                   .group_by(ChatMessage.partner_id).all())
    unread_map = {pid: n for pid, n in unread_rows}

    pogovori = []
    for m in last_msgs:
        p = m.partner
        if not p:
            continue
        if search and search.lower() not in (p.full_name or "").lower():
            continue
        besedilo = (m.text or "").strip()
        if not besedilo and m.image:
            besedilo = "📷 slika"
        if len(besedilo) > MAX_PREVIEW:
            besedilo = besedilo[:MAX_PREVIEW] + "…"
        pogovori.append({
            "partner": p,
            "zadnje": besedilo,
            "kdaj": m.created_at,
            "od_mehanika": m.from_partner,
            "neprebrano": unread_map.get(p.id, 0),
        })
    pogovori.sort(key=lambda r: (r["neprebrano"] > 0, r["kdaj"] or datetime.min), reverse=True)

    # Iskanje tudi po mehanikih, ki še nimajo nobenega sporočila
    novi = []
    if search:
        ze = {r["partner"].id for r in pogovori}
        novi = (User.query
                .filter(User.role == "kupec", User.is_active_user.is_(True),
                        User.full_name.ilike(f"%{search}%"))
                .order_by(User.full_name).limit(30).all())
        novi = [u for u in novi if u.id not in ze]

    return render_template("chat/list.html", pogovori=pogovori,
                           novi=novi, search=search,
                           skupaj_neprebranih=sum(unread_map.values()))


# ── Pogovor ───────────────────────────────────────────────────────────────────

@chat_bp.route("/<int:partner_id>")
@login_required
def thread(partner_id):
    partner = _partner_or_403(partner_id)
    sporocila = (ChatMessage.query.filter_by(partner_id=partner.id)
                 .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                 .limit(300).all())
    _mark_seen(partner.id)
    zadnji_id = sporocila[-1].id if sporocila else 0
    return render_template("chat/thread.html", partner=partner,
                           sporocila=sporocila, zadnji_id=zadnji_id,
                           je_mehanik=_is_partner())


def _neprebranih_za_mehanika(partner_id):
    """Koliko sporočil od nas mehanik še ni prebral."""
    try:
        return (ChatMessage.query
                .filter(ChatMessage.partner_id == partner_id,
                        ChatMessage.sender_id != partner_id,
                        ChatMessage.seen_by_partner.is_(False)).count())
    except Exception:
        return 0


def _neprebranih_za_osebje():
    """Koliko sporočil mehanikov zaposleni še niso prebrali (skupno)."""
    try:
        return (ChatMessage.query
                .filter(ChatMessage.sender_id == ChatMessage.partner_id,
                        ChatMessage.seen_by_staff.is_(False)).count())
    except Exception:
        return 0


def _obvesti(partner, m):
    """Potisno obvestilo nasprotni strani. Mehaniku se predstavimo z imenom
    podjetja, zaposlenim pa z imenom mehanika, da takoj vedo, kdo piše."""
    try:
        from routes.push import notify, staff_ids
    except Exception:
        return

    besedilo = (m.text or "").strip() or "📷 Slika"
    if len(besedilo) > 120:
        besedilo = besedilo[:120] + "…"
    url = url_for("chat.thread", partner_id=partner.id)

    if m.sender_id == partner.id:
        # Mehanik je pisal nam → obvestimo zaposlene (razen njega samega)
        prejemniki = [u for u in staff_ids() if u != m.sender_id]
        # Pri zaposlenih je število neprebranih skupno, zato je za vse enako
        notify(prejemniki, partner.full_name, besedilo, url,
               f"klepet-{partner.id}", _neprebranih_za_osebje())
    else:
        # Zaposleni je pisal mehaniku
        notify([partner.id], "Bartog Ajdovščina", besedilo,
               url_for("chat.index"), f"klepet-{partner.id}",
               _neprebranih_za_mehanika(partner.id))


@chat_bp.route("/<int:partner_id>/poslji", methods=["POST"])
@login_required
def send(partner_id):
    partner = _partner_or_403(partner_id)
    _zagotovi_stolpce()
    text = (request.form.get("text") or "").strip()
    image, slika_vsebina, slika_mime = _save_image(request.files.get("image"))

    if not text and not image:
        if request.form.get("ajax"):
            return jsonify({"ok": False, "error": "prazno"}), 400
        flash("Vpiši sporočilo ali pripni sliko.", "danger")
        return redirect(url_for("chat.thread", partner_id=partner.id))

    m = ChatMessage(
        partner_id = partner.id,
        sender_id  = current_user.id,
        text       = text or None,
        image      = image,
        image_data = slika_vsebina,
        image_mime = slika_mime,
        # Kar pošljem sam, je zame že prebrano
        seen_by_partner = _is_partner(),
        seen_by_staff   = not _is_partner(),
    )
    db.session.add(m)
    db.session.commit()

    _obvesti(partner, m)

    if request.form.get("ajax"):
        return jsonify({"ok": True, "message": _msg_json(m)})
    return redirect(url_for("chat.thread", partner_id=partner.id))


@chat_bp.route("/api/<int:partner_id>/nova")
@login_required
def poll(partner_id):
    """Vrne sporočila, novejša od danega ID – za sprotno osveževanje."""
    partner = _partner_or_403(partner_id)
    try:
        after = int(request.args.get("after", 0))
    except ValueError:
        after = 0
    nova = (ChatMessage.query
            .filter(ChatMessage.partner_id == partner.id, ChatMessage.id > after)
            .order_by(ChatMessage.id.asc()).limit(100).all())
    if nova:
        _mark_seen(partner.id)
    return jsonify({"ok": True, "messages": [_msg_json(m) for m in nova]})


@chat_bp.route("/api/neprebrano")
@login_required
def unread_count():
    return jsonify({"count": unread_for(current_user)})


@chat_bp.route("/slika/<int:message_id>")
@login_required
def message_image(message_id):
    """Postreže sliko sporočila.

    Najprej iz baze – tam je trajno. Na disku pogledamo le pri starejših
    sporočilih, ki so nastala, preden so se slike shranjevale v bazo.
    """
    m = ChatMessage.query.get_or_404(message_id)
    if _is_partner() and m.partner_id != current_user.id:
        abort(403)

    vsebina = None
    try:
        vsebina = m.image_data
    except Exception:
        pass                       # stolpca (še) ni – gremo na disk

    if vsebina:
        odgovor = Response(vsebina, mimetype=(m.image_mime or "image/jpeg"))
        odgovor.headers["Cache-Control"] = "private, max-age=604800"
        odgovor.headers["Content-Disposition"] = f'inline; filename="{m.image or "slika.jpg"}"'
        return odgovor

    if m.image:
        pot = os.path.join(current_app.config.get("UPLOAD_FOLDER", ""),
                           os.path.basename(m.image))
        if os.path.exists(pot):
            return send_from_directory(current_app.config["UPLOAD_FOLDER"],
                                       os.path.basename(m.image))
        # Datoteke ni več (mapa se ob objavi izprazni, če disk ni priklopljen).
        # Namesto pokvarjenega kvadratka pokažemo razumljivo sličico.
        return Response(_NI_SLIKE, mimetype="image/svg+xml",
                        headers={"Cache-Control": "no-store"})
    abort(404)


# Nadomestna sličica, kadar slike ni več na voljo
_NI_SLIKE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="150">'
    '<rect width="100%" height="100%" rx="8" fill="#f1f3f5" stroke="#dee2e6"/>'
    '<text x="50%" y="46%" text-anchor="middle" font-family="system-ui,sans-serif"'
    ' font-size="13" fill="#868e96">Slike ni več na strežniku</text>'
    '<text x="50%" y="66%" text-anchor="middle" font-family="system-ui,sans-serif"'
    ' font-size="11" fill="#adb5bd">prosi za ponovno pošiljanje</text>'
    "</svg>"
).encode()


@chat_bp.route("/<int:message_id>/izbrisi", methods=["POST"])
@login_required
def delete_message(message_id):
    """Brisanje svojega sporočila (admin lahko katerokoli)."""
    m = ChatMessage.query.get_or_404(message_id)
    if m.sender_id != current_user.id and not current_user.is_admin:
        flash("Brišeš lahko samo svoja sporočila.", "danger")
        return redirect(url_for("chat.thread", partner_id=m.partner_id))
    pid = m.partner_id
    if m.image:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], m.image))
        except Exception:
            pass
    db.session.delete(m)
    db.session.commit()
    return redirect(url_for("chat.thread", partner_id=pid))
