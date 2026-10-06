"""Potisna obvestila na telefon (Web Push).

Uporabnik v brskalniku enkrat dovoli obvestila; naprava se zapiše v bazo.
Ko mu kdo piše, strežnik pošlje obvestilo tudi, če aplikacija ni odprta.

Ključa (VAPID) se ustvarita sama ob prvi uporabi in se shranita v bazo, zato
ni treba ničesar nastavljati. Lahko pa ju vsiliš z okoljskima spremenljivkama
VAPID_PUBLIC_KEY in VAPID_PRIVATE_KEY.
"""
import os
import threading

from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user

from models import db, PushSubscription, AppSetting, User
import webpush

push_bp = Blueprint("push", __name__, url_prefix="/push")

PUB_KEY_NAME  = "vapid_public"
PRIV_KEY_NAME = "vapid_private"


# ── Ključa ────────────────────────────────────────────────────────────────────

def _setting(key, default=None):
    row = db.session.get(AppSetting, key)
    return row.value if row else default


def vapid_keys():
    """Vrne (javni, zasebni). Ob prvem klicu ju ustvari in shrani."""
    pub  = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if pub and priv:
        return pub, priv

    pub, priv = _setting(PUB_KEY_NAME), _setting(PRIV_KEY_NAME)
    if pub and priv:
        return pub, priv

    pub, priv = webpush.generate_vapid_keys()
    try:
        db.session.merge(AppSetting(key=PUB_KEY_NAME,  value=pub))
        db.session.merge(AppSetting(key=PRIV_KEY_NAME, value=priv))
        db.session.commit()
        print("✅  Ustvarjena ključa za potisna obvestila.")
    except Exception as e:
        db.session.rollback()
        print(f"⚠️  Ključev za obvestila ni bilo mogoče shraniti: {e}")
    return pub, priv


# ── Naročanje naprave ─────────────────────────────────────────────────────────

@push_bp.route("/kljuc")
@login_required
def public_key():
    pub, _ = vapid_keys()
    return jsonify({"key": pub})


@push_bp.route("/narocilo", methods=["POST"])
@login_required
def subscribe():
    d = request.get_json(silent=True) or {}
    endpoint = (d.get("endpoint") or "").strip()
    keys = d.get("keys") or {}
    p256dh, auth = (keys.get("p256dh") or "").strip(), (keys.get("auth") or "").strip()
    if not endpoint or not p256dh or not auth:
        return jsonify({"ok": False, "error": "nepopolni podatki"}), 400

    obstoj = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if obstoj:
        obstoj.user_id, obstoj.p256dh, obstoj.auth = current_user.id, p256dh, auth
    else:
        db.session.add(PushSubscription(user_id=current_user.id, endpoint=endpoint,
                                        p256dh=p256dh, auth=auth))
    db.session.commit()
    return jsonify({"ok": True})


@push_bp.route("/odjava", methods=["POST"])
@login_required
def unsubscribe():
    d = request.get_json(silent=True) or {}
    endpoint = (d.get("endpoint") or "").strip()
    if endpoint:
        PushSubscription.query.filter_by(endpoint=endpoint).delete()
        db.session.commit()
    return jsonify({"ok": True})


@push_bp.route("/stanje")
@login_required
def status():
    n = PushSubscription.query.filter_by(user_id=current_user.id).count()
    return jsonify({"naprav": n})


# ── Pošiljanje ────────────────────────────────────────────────────────────────

def _send_now(app, user_ids, title, body, url, tag, badge):
    """Teče v ozadju, da pisanje sporočila ne čaka na pošiljanje obvestil."""
    with app.app_context():
        pub, priv = vapid_keys()
        if not pub or not priv:
            return
        subject = "mailto:" + os.environ.get("PUSH_CONTACT", "info@r-parts.si")
        subs = PushSubscription.query.filter(PushSubscription.user_id.in_(user_ids)).all()
        mrtve = []
        for s in subs:
            try:
                webpush.send(
                    {"endpoint": s.endpoint, "p256dh": s.p256dh, "auth": s.auth},
                    {"title": title, "body": body, "url": url, "tag": tag, "badge": badge},
                    priv, pub, subject,
                )
            except webpush.PushError as e:
                # 404/410 pomeni, da naprava ne obstaja več
                if e.status in (404, 410):
                    mrtve.append(s.id)
                else:
                    print(f"⚠️  Obvestilo ni bilo poslano ({e}).")
            except Exception as e:
                print(f"⚠️  Obvestilo ni bilo poslano: {e}")
        if mrtve:
            PushSubscription.query.filter(PushSubscription.id.in_(mrtve)).delete(
                synchronize_session=False)
            db.session.commit()


def notify(user_ids, title, body, url="/klepet/", tag="klepet", badge=0):
    """Pošlje obvestilo naštetim uporabnikom. Nikoli ne vrže napake navzgor."""
    user_ids = [u for u in set(user_ids or []) if u]
    if not user_ids:
        return
    try:
        app = current_app._get_current_object()
        threading.Thread(target=_send_now,
                         args=(app, user_ids, title, body, url, tag, badge),
                         daemon=True).start()
    except Exception as e:
        print(f"⚠️  Obvestil ni bilo mogoče sprožiti: {e}")


def staff_ids():
    """Zaposleni, ki naj dobijo obvestilo o sporočilu mehanika."""
    try:
        return [u.id for u in User.query.filter(
            User.is_active_user.is_(True), User.role != "kupec").all()]
    except Exception:
        return []
