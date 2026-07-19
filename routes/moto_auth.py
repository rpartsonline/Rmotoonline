from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db
from models import MOTO_STAFF_NAMES

moto_auth_bp = Blueprint("moto_auth", __name__, url_prefix="/auth")


@moto_auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("moto.narocila"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(username=username).first()

        # Dovoli dostop samo moto osebju in adminu
        if user and user.is_active_user and user.check_password(password):
            if user.is_admin or user.full_name in MOTO_STAFF_NAMES:
                login_user(user, remember=remember)
                return redirect(url_for("moto.narocila"))
            else:
                flash("Nimaš dostopa do moto platforme.", "danger")
        else:
            flash("Napačno uporabniško ime ali geslo.", "danger")

    return render_template("moto/login.html")


@moto_auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Uspešno ste se odjavili.", "info")
    return redirect(url_for("moto_auth.login"))
