from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from sqlalchemy import or_
from models import db, Customer, User

customers_bp = Blueprint("customers", __name__, url_prefix="/customers")


@customers_bp.route("/")
@login_required
def list_customers():
    search = request.args.get("search", "").strip()
    q = Customer.query
    if search:
        q = q.filter(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%"),
            )
        )
    customers = q.order_by(Customer.name).all()
    # Set customer ID-jev ki že imajo račun
    linked_customer_ids = set(
        u.linked_customer_id for u in User.query.filter(
            User.linked_customer_id.isnot(None)
        ).all()
    )
    return render_template("customers/list.html", customers=customers,
                           search=search, linked_customer_ids=linked_customer_ids)


@customers_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_customer():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Ime stranke je obvezno.", "danger")
            return render_template("customers/new.html", customer=None)

        customer = Customer(
            name    = name,
            phone   = request.form.get("phone",   "").strip(),
            email   = request.form.get("email",   "").strip(),
            address = request.form.get("address", "").strip(),
            notes   = request.form.get("notes",   "").strip(),
        )
        db.session.add(customer)
        db.session.commit()
        flash(f"Stranka {customer.name} je bila dodana.", "success")
        return redirect(url_for("customers.customer_detail", customer_id=customer.id))

    return render_template("customers/new.html", customer=None)


@customers_bp.route("/<int:customer_id>")
@login_required
def customer_detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    linked_user = User.query.filter_by(linked_customer_id=customer_id).first()
    return render_template("customers/detail.html", customer=customer, linked_user=linked_user)


@customers_bp.route("/<int:customer_id>/ustvari-racun", methods=["POST"])
@login_required
def create_customer_account(customer_id):
    from flask_login import current_user
    if not current_user.is_admin:
        flash("Samo admin lahko ustvari račun.", "danger")
        return redirect(url_for("customers.customer_detail", customer_id=customer_id))

    customer = Customer.query.get_or_404(customer_id)

    # Preveri ali račun že obstaja
    existing = User.query.filter_by(linked_customer_id=customer_id).first()
    if existing:
        flash(f"Račun za to stranko že obstaja: '{existing.username}'", "warning")
        return redirect(url_for("customers.customer_detail", customer_id=customer_id))

    # Ustvari username iz imena stranke
    base = customer.name.strip()
    username = base
    used = set(u.username for u in User.query.all())
    i = 2
    while username in used:
        username = f"{base}_{i}"
        i += 1

    u = User(username=username, full_name=customer.name,
             is_admin=False, role="kupec",
             linked_customer_id=customer_id)
    u.set_password("bartog111")
    db.session.add(u)
    db.session.commit()
    flash(f"✅ Račun ustvarjen! Uporabniško ime: '{username}' · Geslo: bartog111", "success")
    return redirect(url_for("customers.customer_detail", customer_id=customer_id))


@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == "POST":
        customer.name    = request.form.get("name",    "").strip()
        customer.phone   = request.form.get("phone",   "").strip()
        customer.email   = request.form.get("email",   "").strip()
        customer.address = request.form.get("address", "").strip()
        customer.notes   = request.form.get("notes",   "").strip()
        if not customer.name:
            flash("Ime stranke je obvezno.", "danger")
        else:
            db.session.commit()
            flash("Podatki stranke so bili posodobljeni.", "success")
            return redirect(url_for("customers.customer_detail", customer_id=customer.id))

    return render_template("customers/new.html", customer=customer)


@customers_bp.route("/<int:customer_id>/delete", methods=["POST"])
@login_required
def delete_customer(customer_id):
    from flask_login import current_user
    from models import Order, OrderItem, OrderStatusLog, OrderImage
    import os
    if not current_user.is_admin:
        flash("Samo admin lahko izbriše stranko.", "danger")
        return redirect(url_for("customers.list_customers"))
    customer = Customer.query.get_or_404(customer_id)
    name = customer.name
    orders = Order.query.filter_by(customer_id=customer_id).all()
    for order in orders:
        OrderStatusLog.query.filter_by(order_id=order.id).delete()
        OrderItem.query.filter_by(order_id=order.id).delete()
        from flask import current_app
        folder = current_app.config.get("UPLOAD_FOLDER", "")
        for img in order.images:
            try:
                from werkzeug.utils import secure_filename
                os.remove(os.path.join(folder, secure_filename(img.filename)))
            except Exception:
                pass
            db.session.delete(img)
        db.session.delete(order)
    db.session.delete(customer)
    db.session.commit()
    flash(f"Stranka {name} je bila izbrisana.", "success")
    return redirect(url_for("customers.list_customers"))
