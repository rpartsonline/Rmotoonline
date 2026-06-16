from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from sqlalchemy import or_
from models import db, Customer

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
    return render_template("customers/list.html", customers=customers, search=search)


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
    return render_template("customers/detail.html", customer=customer)


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
