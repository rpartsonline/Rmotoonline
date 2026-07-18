from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/q/<token>")
def quick_login(token):
    """Hitra prijava prek QR povezave (samo kupci s token-om)."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if token and len(token) >= 16:
        user = User.query.filter_by(login_token=token).first()
        if user and user.is_active_user and user.role == "kupec":
            login_user(user, remember=True)
            return redirect(url_for("main.dashboard"))
    flash("Povezava ni veljavna ali je bila preklicana. Prijavi se z geslom.", "danger")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(username=username).first()
        if user and user.is_active_user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))

        flash("Napačno uporabniško ime ali geslo.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Uspešno ste se odjavili.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/platform-choice")
@login_required
def platform_choice():
    if not current_user.is_admin:
        return redirect(url_for("main.dashboard"))
    return render_template("platform_select.html")


@auth_bp.route("/platform-choice/set/<platforma>")
@login_required  
def set_platform(platforma):
    if platforma == "moto":
        return redirect(url_for("moto.narocila"))
    return redirect(url_for("main.dashboard"))
