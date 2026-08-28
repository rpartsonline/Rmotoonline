import os
from flask import Flask
from flask_login import LoginManager

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    # ── Config ──────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-tajni-kljuc-zamenjaj-v-produkciji")

    # Določitev baze podatkov:
    #   1) Če je nastavljen DATABASE_URL (npr. PostgreSQL) → uporabi tega.
    #   2) Sicer SQLite v mapi DATA_DIR. Na Renderju nastaviš DATA_DIR na
    #      priklopno pot diska (npr. /var/data) in podatki so trajni.
    #   3) Brez obojega → SQLite v mapi projekta (samo za lokalni razvoj).
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Render za PostgreSQL vrača postgres://, SQLAlchemy zahteva postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
    else:
        data_dir = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, "narocila.db")
        db_url = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Mapa za naložene slike (Render Disk prek DATA_DIR, sicer lokalno)
    _data_dir = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
    upload_dir = os.path.join(_data_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_dir
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB skupaj

    # ── Extensions ──────────────────────────────────────────────────────────
    from models import db, User
    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Za dostop se prijavite."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── Jinja filters ───────────────────────────────────────────────────────
    @app.template_filter("sl_date")
    def sl_date(dt):
        return dt.strftime("%d.%m.%Y") if dt else "–"

    @app.template_filter("sl_datetime")
    def sl_datetime(dt):
        return dt.strftime("%d.%m.%Y %H:%M") if dt else "–"

    @app.template_filter("sl_time")
    def sl_time(dt):
        """Ura po slovenskem času (created_at je shranjen v UTC)."""
        if not dt:
            return "–"
        try:
            from zoneinfo import ZoneInfo
            return (dt.replace(tzinfo=ZoneInfo("UTC"))
                      .astimezone(ZoneInfo("Europe/Ljubljana"))
                      .strftime("%H:%M"))
        except Exception:
            return dt.strftime("%H:%M")

    # Opozorila – na voljo v vseh predlogah (za oblačke)
    @app.context_processor
    def inject_alerts():
        from datetime import timedelta
        from models import Order, today_local
        new_count = 0
        deliv_count = 0
        deliv_red = False
        try:
            from flask_login import current_user as _cu
            is_kupec_ctx = _cu.is_authenticated and getattr(_cu, "role", "") == "kupec"
            new_count = Order.query.filter_by(kind="narocilo", status="novo").count()
            today = today_local()
            tomorrow = today + timedelta(days=1)
            dq = (
                Order.query
                .filter_by(kind="povprasevanje", status="narocena_caka")
                .filter(Order.delivery_date.isnot(None))
                .filter(Order.delivery_date <= tomorrow)
            )
            # Kupec (mehanik) vidi „Dostava dela" samo za svoje
            if is_kupec_ctx:
                dq = dq.filter_by(employee_id=_cu.id)
            due = dq.all()
            deliv_count = len(due)
            deliv_red = any(o.delivery_date <= today for o in due)
        except Exception:
            pass
        # Števec novih obvestil za kupca (naročila, ki so prešla na „naročeno")
        kupec_notif = 0
        kupec_inquiry_notif = 0
        kupec_order_notif = 0
        try:
            from flask_login import current_user
            if current_user.is_authenticated and getattr(current_user, "role", "") == "kupec":
                kupec_notif = Order.query.filter_by(
                    employee_id=current_user.id, notify_customer=True).count()
                kupec_inquiry_notif = Order.query.filter_by(
                    employee_id=current_user.id, kind="povprasevanje",
                    notify_customer=True).count()
                kupec_order_notif = Order.query.filter_by(
                    employee_id=current_user.id, kind="narocilo",
                    notify_customer=True).count()
        except Exception:
            pass
        note_notif_count = 0
        done_notif_count = 0
        try:
            from models import Note
            note_notif_count = Note.query.filter_by(done=False).count()
            done_notif_count = Note.query.filter_by(done=True).count()
        except Exception:
            pass
        # Moje beležke, ki jih je sodelavec potrdil kot urejene in jih še nisem videl
        my_notes_done_count = 0
        my_notes_incoming_count = 0
        try:
            from flask_login import current_user
            from models import Note
            if current_user.is_authenticated:
                my_notes_done_count = Note.query.filter_by(
                    created_by_id=current_user.id, done=True,
                    creator_seen_done=False).count()
                # Beležke, namenjene meni (po imenu) in še neobdelane
                if getattr(current_user, "full_name", None):
                    my_notes_incoming_count = Note.query.filter_by(
                        person=current_user.full_name, done=False).count()
        except Exception:
            pass
        # Nova povprasevanja mehanikov (za oblacek) – samo za osebje
        new_inq_count = 0
        try:
            from flask_login import current_user as _cu2
            if _cu2.is_authenticated and getattr(_cu2, "role", "") != "kupec":
                new_inq_count = Order.query.filter_by(
                    kind="povprasevanje", status="novo_povprasevanje").count()
        except Exception:
            pass
        return {
            "new_orders_count": new_count,
            "new_inquiries_count": new_inq_count,
            "delivery_alert_count": deliv_count,
            "delivery_alert_red": deliv_red,
            "kupec_notif_count": kupec_notif,
            "kupec_inquiry_notif_count": kupec_inquiry_notif,
            "kupec_order_notif_count": kupec_order_notif,
            "note_notif_count": note_notif_count,
            "done_notif_count": done_notif_count,
            "my_notes_done_count": my_notes_done_count,
            "my_notes_incoming_count": my_notes_incoming_count,
        }

    # ── Blueprints ──────────────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.orders import orders_bp
    from routes.customers import customers_bp
    from routes.vehicles import vehicles_bp
    from routes.admin import admin_bp
    from routes.notes import notes_bp
    from routes.delivery import delivery_bp
    from routes.staff import staff_bp
    from routes.complaints import complaints_bp
    from routes.create_accounts import create_acc_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(delivery_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(create_acc_bp)

    # ── Omejitev dostopa za kupce (vidijo samo svoja naročila/povpraševanja) ──
    @app.before_request
    def _restrict_kupci():
        from flask import request, redirect, url_for, flash
        from flask_login import current_user
        if not current_user.is_authenticated:
            return
        if getattr(current_user, "role", "") != "kupec":
            return
        ep = request.endpoint or ""
        # dovoljeni deli + VIN branje/razčlemba (vehicles API) za izpolnjevanje naročila
        allowed_vehicle_eps = {"vehicles.api_vin_ocr", "vehicles.api_decode_vin", "vehicles.api_models"}
        if ep == "static" or ep.startswith(("orders.", "auth.", "main.", "complaints.", "static")) or ep in allowed_vehicle_eps:
            return
        flash("Do te strani nimaš dostopa.", "danger")
        return redirect(url_for("orders.list_orders"))

    @app.before_request
    def _restrict_racunovodja():
        from flask import request, redirect, url_for, flash
        from flask_login import current_user
        if not current_user.is_authenticated:
            return
        if getattr(current_user, "role", "") != "racunovodja":
            return
        ep = request.endpoint or ""
        # Računovodja: samo Ure, Dopusti, Beležka (+ prijava/statika)
        if ep == "static" or ep.startswith(("staff.", "notes.", "auth.", "static")):
            return
        # Osnovne main. strani dovolimo (npr. odjava, sw.js), a preusmerimo na Ure
        if ep in ("main.sw", "main.zamenjaj_platformo"):
            return
        flash("Do te strani nimaš dostopa.", "danger")
        return redirect(url_for("staff.hours"))

    # ── Init DB & default admin ──────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _ensure_schema(db)
        _seed_admin(db, User)
        _seed_staff(db, User)
        _seed_kupec(db, User)
        _seed_racunovodja(db, User)
        _seed_roster_updates(db, User)

    return app


def _ensure_schema(db):
    """Varno doda nove stolpce v obstoječo bazo (SQLite)."""
    from sqlalchemy import inspect, text
    try:
        cols = [c["name"] for c in inspect(db.engine).get_columns("orders")]
        if "kind" not in cols:
            db.session.execute(text(
                "ALTER TABLE orders ADD COLUMN kind VARCHAR(20) DEFAULT 'narocilo'"
            ))
            db.session.commit()
            print("✅  Dodan stolpec 'kind' v tabelo orders.")
        if "delivery_date" not in cols:
            db.session.execute(text(
                "ALTER TABLE orders ADD COLUMN delivery_date DATE"
            ))
            db.session.commit()
            print("✅  Dodan stolpec 'delivery_date' v tabelo orders.")
    except Exception as e:
        print(f"⚠️  Migracija preskočena: {e}")

    # delivery_stops.tires
    try:
        dcols = [c["name"] for c in inspect(db.engine).get_columns("delivery_stops")]
        if "tires" not in dcols:
            db.session.execute(text("ALTER TABLE delivery_stops ADD COLUMN tires VARCHAR(50)"))
            db.session.commit()
            print("✅  Dodan stolpec 'tires' v tabelo delivery_stops.")
    except Exception as e:
        print(f"⚠️  Migracija (tires) preskočena: {e}")

    # work_hours.arrival / departure
    try:
        wcols = [c["name"] for c in inspect(db.engine).get_columns("work_hours")]
        if "arrival" not in wcols:
            db.session.execute(text("ALTER TABLE work_hours ADD COLUMN arrival VARCHAR(5)"))
            db.session.commit()
            print("✅  Dodan stolpec 'arrival' v tabelo work_hours.")
        if "departure" not in wcols:
            db.session.execute(text("ALTER TABLE work_hours ADD COLUMN departure VARCHAR(5)"))
            db.session.commit()
            print("✅  Dodan stolpec 'departure' v tabelo work_hours.")
    except Exception as e:
        print(f"⚠️  Migracija (work_hours) preskočena: {e}")

    # users.role
    try:
        ucols = [c["name"] for c in inspect(db.engine).get_columns("users")]
        if "role" not in ucols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'zaposleni'"))
            db.session.commit()
            print("✅  Dodan stolpec 'role' v tabelo users.")
        if "login_token" not in ucols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN login_token VARCHAR(64)"))
            db.session.commit()
            print("✅  Dodan stolpec 'login_token' v tabelo users.")
    except Exception as e:
        print(f"⚠️  Migracija (users.role) preskočena: {e}")

    # orders.notify_customer
    try:
        ocols = [c["name"] for c in inspect(db.engine).get_columns("orders")]
        if "notify_customer" not in ocols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN notify_customer BOOLEAN DEFAULT 0"))
            db.session.commit()
            print("✅  Dodan stolpec 'notify_customer' v tabelo orders.")
        if "delivery_urgency" not in ocols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN delivery_urgency VARCHAR(20)"))
            db.session.commit()
            print("✅  Dodan stolpec 'delivery_urgency' v tabelo orders.")
        if "offer_price" not in ocols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN offer_price VARCHAR(100)"))
            db.session.commit()
            print("✅  Dodan stolpec 'offer_price' v tabelo orders.")
        if "offer_delivery" not in ocols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN offer_delivery VARCHAR(100)"))
            db.session.commit()
            print("✅  Dodan stolpec 'offer_delivery' v tabelo orders.")
        if "offer_note" not in ocols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN offer_note TEXT"))
            db.session.commit()
            print("✅  Dodan stolpec 'offer_note' v tabelo orders.")
        if "sms_variant" not in ocols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN sms_variant VARCHAR(5)"))
            db.session.commit()
            print("✅  Dodan stolpec 'sms_variant' v tabelo orders.")
        if "vin" not in ocols:
            db.session.execute(text("ALTER TABLE orders ADD COLUMN vin VARCHAR(32)"))
            db.session.commit()
            print("✅  Dodan stolpec 'vin' v tabelo orders.")
            # Enkratni prenos: obstoječim naročilom prepiši VIN iz vozila,
            # da stare številke ostanejo vidne tudi pri naročilu.
            try:
                db.session.execute(text(
                    "UPDATE orders SET vin = ("
                    "  SELECT v.vin FROM vehicles v WHERE v.id = orders.vehicle_id"
                    ") WHERE vin IS NULL AND vehicle_id IS NOT NULL"
                ))
                db.session.commit()
                print("✅  VIN prepisan iz vozil v obstoječa naročila.")
            except Exception as e2:
                print(f"⚠️  Prenos VIN v naročila preskočen: {e2}")
    except Exception as e:
        print(f"⚠️  Migracija (orders.notify_customer) preskočena: {e}")

    # customers.customer_code / postal
    try:
        ccols = [c["name"] for c in inspect(db.engine).get_columns("customers")]
        if "customer_code" not in ccols:
            db.session.execute(text("ALTER TABLE customers ADD COLUMN customer_code VARCHAR(50)"))
            db.session.commit()
            print("✅  Dodan stolpec 'customer_code' v tabelo customers.")
        if "postal" not in ccols:
            db.session.execute(text("ALTER TABLE customers ADD COLUMN postal VARCHAR(100)"))
            db.session.commit()
            print("✅  Dodan stolpec 'postal' v tabelo customers.")
    except Exception as e:
        print(f"⚠️  Migracija (customers) preskočena: {e}")


def _seed_admin(db, User):
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", full_name="Administrator", is_admin=True)
        admin.set_password(os.environ.get("ADMIN_PASSWORD", "Admin123!"))
        db.session.add(admin)
        db.session.commit()
        print("✅  Admin uporabnik ustvarjen (geslo v ADMIN_PASSWORD env var).")


def _seed_racunovodja(db, User):
    """Ustvari računovodkinjo Marjano, če še ne obstaja. Začetno geslo: bartog111."""
    if not User.query.filter_by(username="marjana").first():
        u = User(username="marjana", full_name="Marjana Računovodja",
                 is_admin=False, role="racunovodja", is_active_user=True)
        u.set_password("bartog111")
        db.session.add(u)
        db.session.commit()
        print("✅  Računovodja 'marjana' ustvarjena (geslo: bartog111 – zamenjaj!).")


def _seed_staff(db, User):
    """Ustvari prijave za sodelavce, če še ne obstajajo. Začetno geslo: Bartog123!"""
    staff = [
        ("saso",  "Sašo Juretič"),
        ("alan",  "Alan Daksobler"),
        ("vid",   "Vid Kenda"),
        ("nejc",  "Nejc Tominec"),
        ("borut", "Borut Čermelj"),
    ]
    created = []
    for username, full_name in staff:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, full_name=full_name, is_admin=False)
            u.set_password(os.environ.get("STAFF_DEFAULT_PASSWORD", "Bartog123!"))
            db.session.add(u)
            created.append(username)
    if created:
        db.session.commit()
        print(f"✅  Ustvarjeni uporabniki: {', '.join(created)} (začetno geslo Bartog123!).")


def _seed_kupec(db, User):
    """Ustvari kupca 'Bartog Ajdovščina', če še ne obstaja."""
    if not User.query.filter_by(username="bartog").first():
        u = User(username="bartog", full_name="Bartog Ajdovščina",
                 is_admin=False, role="kupec")
        u.set_password(os.environ.get("KUPEC_DEFAULT_PASSWORD", "Bartog123!"))
        db.session.add(u)
        db.session.commit()
        print("✅  Ustvarjen kupec 'bartog' (Bartog Ajdovščina, geslo Bartog123!).")


def _seed_racunovodja(db, User):
    """Ustvari računovodkinjo Marjano, če še ne obstaja. Začetno geslo: bartog111."""
    if not User.query.filter_by(username="marjana").first():
        u = User(username="marjana", full_name="Marjana Računovodja",
                 is_admin=False, role="racunovodja", is_active_user=True)
        u.set_password(os.environ.get("RACUNOVODJA_DEFAULT_PASSWORD", "bartog111"))
        db.session.add(u)
        db.session.commit()
        print("✅  Ustvarjena računovodkinja 'marjana' (Marjana Računovodja, geslo bartog111).")


def _seed_roster_updates(db, User):
    """Posodobi ekipo: odstrani (deaktivira) odhajajoče, doda nove zaposlene."""
    changed = False

    # Odstrani (deaktivira) – ne izbrišemo, da ostane zgodovina (ure, dopusti)
    for full_name in ["Ervin Nemec", "Mojca Čermelj", "Nejc Tominec"]:
        u = User.query.filter_by(full_name=full_name).first()
        if u and u.is_active_user:
            u.is_active_user = False
            changed = True
            print(f"➖  Deaktiviran zaposleni: {full_name}")

    # Dodaj nove zaposlene (če še ne obstajajo)
    for username, full_name in [("nina", "Nina Hrobat"),
                                ("robert", "Robert Bratož")]:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, full_name=full_name,
                     is_admin=False, is_active_user=True)
            u.set_password(os.environ.get("STAFF_DEFAULT_PASSWORD", "Bartog123!"))
            db.session.add(u)
            changed = True
            print(f"➕  Dodan zaposleni: {full_name} ({username})")

    if changed:
        db.session.commit()




app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
