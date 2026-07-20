from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from sqlalchemy import inspect, text

complaints_bp = Blueprint("complaints", __name__, url_prefix="/reklamacije")


def _ensure_complaints_table(db):
    """Ustvari tabelo reklamacij (in prilog) če ne obstaja."""
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
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS complaint_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                filename VARCHAR(300) NOT NULL,
                orig_name VARCHAR(300),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.commit()
    except Exception as e:
        print(f"⚠️  Reklamacije tabela: {e}")


# Dovoljene priloge (slike + PDF)
ALLOWED_DOC_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".pdf"}
IMAGE_DOC_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _save_complaint_files(complaint_id, files):
    """Shrani naložene/fotografirane dokumente k reklamaciji."""
    import os
    import uuid
    from flask import current_app
    from werkzeug.utils import secure_filename

    folder = current_app.config.get("UPLOAD_FOLDER", "")
    if not folder:
        return
    saved = 0
    for f in files or []:
        if not f or not getattr(f, "filename", ""):
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_DOC_EXT:
            continue
        fname = secure_filename(f"reklamacija_{complaint_id}_{uuid.uuid4().hex}{ext}")
        try:
            f.save(os.path.join(folder, fname))
            db.session.execute(text(
                "INSERT INTO complaint_files (complaint_id, filename, orig_name) "
                "VALUES (:c, :f, :o)"),
                {"c": complaint_id, "f": fname, "o": (f.filename or "")[:300]})
            saved += 1
        except Exception as e:
            print(f"⚠️  Priloga reklamacije ni shranjena: {e}")
    if saved:
        db.session.commit()
    return saved


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
        # ID nove reklamacije + shranjevanje priloženih dokumentov
        new_id = db.session.execute(text("SELECT last_insert_rowid()")).scalar()
        try:
            _save_complaint_files(new_id, request.files.getlist("documents"))
        except Exception as e:
            print(f"⚠️  Priloge reklamacije: {e}")
        flash("Reklamacija dodana.", "success")
        return redirect(url_for("complaints.complaint_detail", complaint_id=new_id))
    return render_template("complaints/new.html")


@complaints_bp.route("/<int:complaint_id>")
@login_required
def complaint_detail(complaint_id):
    _ensure_complaints_table(db)
    comp = db.session.execute(
        text("SELECT * FROM complaints WHERE id=:id"), {"id": complaint_id}).fetchone()
    if not comp:
        flash("Reklamacija ne obstaja.", "danger")
        return redirect(url_for("complaints.list_complaints"))
    files = db.session.execute(
        text("SELECT * FROM complaint_files WHERE complaint_id=:id ORDER BY id"),
        {"id": complaint_id}).fetchall()
    # Loči slike od ostalih (PDF) za prikaz
    import os
    docs = []
    for fr in files:
        ext = os.path.splitext(fr.filename)[1].lower()
        docs.append({"id": fr.id, "filename": fr.filename,
                     "orig_name": fr.orig_name or fr.filename,
                     "is_image": ext in IMAGE_DOC_EXT})
    return render_template("complaints/detail.html",
                           c=comp, docs=docs,
                           statuses=STATUSES, STATUS_DICT=STATUS_DICT)


@complaints_bp.route("/priloga/<int:file_id>")
@login_required
def complaint_file(file_id):
    from flask import current_app, send_from_directory, abort
    _ensure_complaints_table(db)
    row = db.session.execute(
        text("SELECT filename FROM complaint_files WHERE id=:id"),
        {"id": file_id}).fetchone()
    if not row:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], row[0])


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
    # Počisti priloge (datoteke na disku + zapise)
    import os
    from flask import current_app
    folder = current_app.config.get("UPLOAD_FOLDER", "")
    rows = db.session.execute(
        text("SELECT filename FROM complaint_files WHERE complaint_id=:id"),
        {"id": complaint_id}).fetchall()
    for r in rows:
        try:
            os.remove(os.path.join(folder, r[0]))
        except Exception:
            pass
    db.session.execute(text("DELETE FROM complaint_files WHERE complaint_id=:id"),
                       {"id": complaint_id})
    db.session.execute(text("DELETE FROM complaints WHERE id=:id"), {"id": complaint_id})
    db.session.commit()
    flash("Reklamacija izbrisana.", "success")
    return redirect(url_for("complaints.list_complaints"))
