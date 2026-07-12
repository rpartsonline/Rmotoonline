from flask import Blueprint, render_template, redirect, url_for, flash, request, session
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


@auth_bp.route("/", methods=["GET"])
def platform_choice():
    """Uvodna stran – izbira platforme PRED prijavo."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("platform_choice.html")


@auth_bp.route("/izberi/<platforma>")
def set_platform(platforma):
    """Shrani izbrano platformo in preusmeri na prijavo."""
    if platforma not in ("moto", "avto"):
        platforma = "avto"
    session["platform"] = platforma
    session.permanent = True
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # Če platforma ni izbrana, vrni na uvodno stran
    platforma = session.get("platform")
    if not platforma:
        return redirect(url_for("auth.platform_choice"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(username=username).first()
        if user and user.is_active_user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("main.dashboard"))

        flash("Napačno uporabniško ime ali geslo.", "danger")

    return render_template("login.html", platforma=platforma)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("platform", None)
    flash("Uspešno ste se odjavili.", "info")
    return redirect(url_for("auth.platform_choice"))
