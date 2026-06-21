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

    # Opozorila – na voljo v vseh predlogah (za oblačke)
    @app.context_processor
    def inject_alerts():
        from datetime import timedelta
        from models import Order, today_local
        new_count = 0
        deliv_count = 0
        deliv_red = False
        try:
            new_count = Order.query.filter_by(kind="narocilo", status="novo").count()
            today = today_local()
            tomorrow = today + timedelta(days=1)
            due = (
                Order.query
                .filter_by(kind="povprasevanje", status="narocena_caka")
                .filter(Order.delivery_date.isnot(None))
                .filter(Order.delivery_date <= tomorrow)
                .all()
            )
            deliv_count = len(due)
            deliv_red = any(o.delivery_date <= today for o in due)
        except Exception:
            pass
        return {
            "new_orders_count": new_count,
            "delivery_alert_count": deliv_count,
            "delivery_alert_red": deliv_red,
        }

    # ── Blueprints ──────────────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.orders import orders_bp
    from routes.customers import customers_bp
    from routes.vehicles import vehicles_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(admin_bp)

    # ── Init DB & default admin ──────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _ensure_schema(db)
        _seed_admin(db, User)

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


def _seed_admin(db, User):
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", full_name="Administrator", is_admin=True)
        admin.set_password(os.environ.get("ADMIN_PASSWORD", "Admin123!"))
        db.session.add(admin)
        db.session.commit()
        print("✅  Admin uporabnik ustvarjen (geslo v ADMIN_PASSWORD env var).")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
