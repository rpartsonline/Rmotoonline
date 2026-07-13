from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from models import db, Note, NOTE_PEOPLE

notes_bp = Blueprint("notes", __name__, url_prefix="/belezka")


@notes_bp.route("/")
@login_required
def list_notes():
    person_filter = request.args.get("person", "")
    show = request.args.get("show", "todo")  # todo | done | all

    q = Note.query
    if person_filter:
        q = q.filter_by(person=person_filter)
    if show == "todo":
        q = q.filter_by(done=False)
    elif show == "done":
        q = q.filter_by(done=True)

    notes = q.order_by(Note.done.asc(), Note.created_at.desc()).all()

    # Zabeleži čas ogleda (za oblaček novih beležk)
    session["notes_last_visit"] = datetime.utcnow().isoformat()

    # Povratna info: moje beležke ki so bile obdelane in jih še nisem videl
    obdelane_zame = (Note.query
                     .filter_by(created_by_id=current_user.id, done=True,
                                creator_seen_done=False)
                     .order_by(Note.done_at.desc()).all())
    if obdelane_zame:
        for n in obdelane_zame:
            n.creator_seen_done = True
        db.session.commit()

    # Števila nezaključenih po osebi
    counts = {p: Note.query.filter_by(person=p, done=False).count() for p in NOTE_PEOPLE}

    return render_template(
        "notes/list.html",
        notes=notes,
        people=NOTE_PEOPLE,
        counts=counts,
        obdelane_zame=obdelane_zame,
        person_filter=person_filter,
        show=show,
    )


@notes_bp.route("/add", methods=["POST"])
@login_required
def add_note():
    text = request.form.get("text", "").strip()
    person = request.form.get("person", "").strip()
    if not text:
        flash("Vpiši besedilo beležke.", "danger")
        return redirect(url_for("notes.list_notes"))
    db.session.add(Note(
        text=text,
        person=person or None,
        done=False,
        created_by_id=current_user.id,
    ))
    db.session.commit()
    flash("Beležka dodana.", "success")
    return redirect(url_for("notes.list_notes", person=person))


@notes_bp.route("/<int:note_id>/toggle", methods=["POST"])
@login_required
def toggle_note(note_id):
    note = Note.query.get_or_404(note_id)
    note.done = not note.done
    note.done_at = datetime.utcnow() if note.done else None
    db.session.commit()
    return redirect(request.referrer or url_for("notes.list_notes"))


@notes_bp.route("/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    flash("Beležka izbrisana.", "info")
    return redirect(request.referrer or url_for("notes.list_notes"))
