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
                   request, jsonify, current_app, send_from_directory, abort)
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


def _save_image(f):
    """Shrani priloženo sliko in vrne ime datoteke (ali None)."""
    if not f or not getattr(f, "filename", ""):
        return None
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return None
    folder = current_app.config.get("UPLOAD_FOLDER", "")
    if not folder:
        return None
    name = secure_filename(f"klepet_{uuid.uuid4().hex}{ext}")
    try:
        f.save(os.path.join(folder, name))
        return name
    except Exception as e:
        print(f"⚠️  Slike v klepetu ni bilo mogoče shraniti: {e}")
        return None


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


@chat_bp.route("/<int:partner_id>/poslji", methods=["POST"])
@login_required
def send(partner_id):
    partner = _partner_or_403(partner_id)
    text = (request.form.get("text") or "").strip()
    image = _save_image(request.files.get("image"))

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
        # Kar pošljem sam, je zame že prebrano
        seen_by_partner = _is_partner(),
        seen_by_staff   = not _is_partner(),
    )
    db.session.add(m)
    db.session.commit()

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
    m = ChatMessage.query.get_or_404(message_id)
    if _is_partner() and m.partner_id != current_user.id:
        abort(403)
    if not m.image:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], m.image)


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
