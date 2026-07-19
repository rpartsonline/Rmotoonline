"""
moto_app.py — Ločena Flask aplikacija za Moto platformo (R-MotoShop Ajdovščina)
Teče kot ločen Render servis, deli isto PostgreSQL bazo z Avto platformo.
Start command: gunicorn moto_app:app
"""
import os
from flask import Flask
from flask_login import LoginManager

login_manager = LoginManager()


def create_moto_app():
    app = Flask(__name__, template_folder="templates")

    # ── Config ──────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-tajni-kljuc-moto")

    # Ista PostgreSQL baza kot Avto platforma
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
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
    login_manager.login_view = "moto_auth.login"
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
        if not dt:
            return "–"
        try:
            from zoneinfo import ZoneInfo
            return (dt.replace(tzinfo=ZoneInfo("UTC"))
                      .astimezone(ZoneInfo("Europe/Ljubljana"))
                      .strftime("%H:%M"))
        except Exception:
            return dt.strftime("%H:%M")

    # ── Blueprints ──────────────────────────────────────────────────────────
    from routes.moto_auth import moto_auth_bp
    from routes.moto import moto_bp

    app.register_blueprint(moto_auth_bp)
    app.register_blueprint(moto_bp)

    # ── Init DB ─────────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_moto_staff(db, User)

    return app


def _seed_moto_staff(db, User):
    """Ustvari Mojco in Ervina če še ne obstajata."""
    staff = [("mojca", "Mojca Čermelj"), ("ervin", "Ervin Nemec")]
    created = []
    for username, full_name in staff:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, full_name=full_name, is_admin=False)
            u.set_password(os.environ.get("MOTO_STAFF_PASSWORD", "Moto123!"))
            db.session.add(u)
            created.append(username)
    if created:
        db.session.commit()
        print(f"✅ Moto zaposleni ustvarjeni: {', '.join(created)}")


app = create_moto_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
