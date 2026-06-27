from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Dostop zavrnjen. Potrebna so skrbniška pooblastila.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.full_name).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    if request.method == "POST":
        username  = request.form.get("username",  "").strip()
        full_name = request.form.get("full_name", "").strip()
        password  = request.form.get("password",  "")
        role      = request.form.get("role", "zaposleni")
        if role not in ("zaposleni", "kupec", "admin"):
            role = "zaposleni"
        is_admin  = (role == "admin") or bool(request.form.get("is_admin"))

        if not username or not full_name or not password:
            flash("Vsa polja so obvezna.", "danger")
            return render_template("admin/new_user.html")

        if len(password) < 6:
            flash("Geslo mora imeti vsaj 6 znakov.", "danger")
            return render_template("admin/new_user.html")

        if User.query.filter_by(username=username).first():
            flash("Uporabniško ime je že zasedeno.", "danger")
            return render_template("admin/new_user.html")

        user = User(username=username, full_name=full_name, is_admin=is_admin, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f"Uporabnik {username} je bil ustvarjen.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/new_user.html")


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(user_id):
    user     = User.query.get_or_404(user_id)
    new_pass = request.form.get("new_password", "")
    if len(new_pass) < 6:
        flash("Geslo mora imeti vsaj 6 znakov.", "danger")
    else:
        user.set_password(new_pass)
        db.session.commit()
        flash(f"Geslo za {user.username} je bilo ponastavljeno.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Ne morete deaktivirati svojega računa.", "danger")
    else:
        user.is_active_user = not user.is_active_user
        db.session.commit()
        status = "aktiviran" if user.is_active_user else "deaktiviran"
        flash(f"Uporabnik {user.username} je bil {status}.", "success")
    return redirect(url_for("admin.users"))
