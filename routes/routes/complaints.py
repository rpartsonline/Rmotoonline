from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from sqlalchemy import inspect, text

complaints_bp = Blueprint("complaints", __name__, url_prefix="/reklamacije")


def _ensure_complaints_table(db):
    """Ustvari tabelo reklamacij če ne obstaja."""
    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                customer_name VARCHAR(200),
                description TEXT,
                status VARCHAR(30) DEFAULT 'prejeta',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        """))
        db.session.commit()
    except Exception as e:
        print(f"⚠️  Reklamacije tabela: {e}")


STATUSES = [
    ("prejeta",     "Prejeta reklamacija",        "danger"),
    ("v_obdelavi",  "Reklamacija v obdelavi",      "warning"),
    ("zakljucena",  "Reklamacija zaključena",      "success"),
]
STATUS_DICT = {k: (l, c) for k, l, c in STATUSES}


@complaints_bp.route("/")
@login_required
def list_complaints():
    from flask import current_app
    _ensure_complaints_table(db)

    status_filter = request.args.get("status", "")
    search = request.args.get("search", "").strip()

    query = "SELECT * FROM complaints WHERE 1=1"
    params = {}
    if status_filter:
        query += " AND status = :status"
        params["status"] = status_filter
    if search:
        query += " AND (title LIKE :search OR customer_name LIKE :search)"
        params["search"] = f"%{search}%"
    query += " ORDER BY created_at DESC"

    rows = db.session.execute(text(query), params).fetchall()

    # Števci po statusih
    counts = {}
    for k, _, _ in STATUSES:
        r = db.session.execute(text("SELECT COUNT(*) FROM complaints WHERE status=:s"), {"s": k}).fetchone()
        counts[k] = r[0] if r else 0

    status_breakdown = [{"key": k, "label": l, "color": c, "count": counts.get(k, 0)} for k, l, c in STATUSES]

    return render_template("complaints/list.html",
        complaints=rows,
        statuses=STATUSES,
        status_breakdown=status_breakdown,
        status_filter=status_filter,
        search=search,
        STATUS_DICT=STATUS_DICT,
    )


@complaints_bp.route("/novo", methods=["GET", "POST"])
@login_required
def new_complaint():
    _ensure_complaints_table(db)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        customer_name = request.form.get("customer_name", "").strip()
        description = request.form.get("description", "").strip()
        if not title:
            flash("Naslov je obvezen.", "danger")
            return render_template("complaints/new.html")
        db.session.execute(text("""
            INSERT INTO complaints (title, customer_name, description, status, created_by)
            VALUES (:title, :customer_name, :description, 'prejeta', :uid)
        """), {"title": title, "customer_name": customer_name,
               "description": description, "uid": current_user.id})
        db.session.commit()
        flash("Reklamacija dodana.", "success")
        return redirect(url_for("complaints.list_complaints"))
    return render_template("complaints/new.html")


@complaints_bp.route("/<int:complaint_id>/status", methods=["POST"])
@login_required
def update_status(complaint_id):
    _ensure_complaints_table(db)
    new_status = request.form.get("status")
    if new_status in [k for k, _, _ in STATUSES]:
        db.session.execute(text("""
            UPDATE complaints SET status=:s, updated_at=CURRENT_TIMESTAMP WHERE id=:id
        """), {"s": new_status, "id": complaint_id})
        db.session.commit()
        flash("Status posodobljen.", "success")
    return redirect(url_for("complaints.list_complaints"))


@complaints_bp.route("/<int:complaint_id>/izbrisi", methods=["POST"])
@login_required
def delete_complaint(complaint_id):
    _ensure_complaints_table(db)
    db.session.execute(text("DELETE FROM complaints WHERE id=:id"), {"id": complaint_id})
    db.session.commit()
    flash("Reklamacija izbrisana.", "success")
    return redirect(url_for("complaints.list_complaints"))
