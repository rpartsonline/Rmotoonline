import calendar
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, LeaveEntry, WorkHours, MonthLock, leave_color_for

staff_bp = Blueprint("staff", __name__, url_prefix="/osebje")

SL_MONTHS = ["", "Januar", "Februar", "Marec", "April", "Maj", "Junij",
             "Julij", "Avgust", "September", "Oktober", "November", "December"]
SL_DOW = ["Pon", "Tor", "Sre", "Čet", "Pet", "Sob", "Ned"]


def _ym(default_date=None):
    today = default_date or date.today()
    try:
        y = int(request.args.get("year", today.year))
        m = int(request.args.get("month", today.month))
        if not (1 <= m <= 12):
            raise ValueError
    except (TypeError, ValueError):
        y, m = today.year, today.month
    return y, m


def _prev_next(y, m):
    pm, py = (12, y - 1) if m == 1 else (m - 1, y)
    nm, ny = (1, y + 1) if m == 12 else (m + 1, y)
    return (py, pm), (ny, nm)


# ── DOPUSTI (koledar) ─────────────────────────────────────────────────────────
@staff_bp.route("/dopusti")
@login_required
def leave():
    y, m = _ym()
    first = date(y, m, 1)
    days_in_month = calendar.monthrange(y, m)[1]
    last = date(y, m, days_in_month)

    # vsi vnosi, ki se prekrivajo z mesecem
    entries = (LeaveEntry.query
               .filter(LeaveEntry.start_date <= last, LeaveEntry.end_date >= first)
               .all())

    # mapiranje dan -> seznam {name, color}
    day_map = {d: [] for d in range(1, days_in_month + 1)}
    for e in entries:
        d = max(e.start_date, first)
        end = min(e.end_date, last)
        while d <= end:
            day_map[d.day].append({
                "name": e.user.full_name if e.user else "?",
                "color": leave_color_for(e.user_id),
                "uid": e.user_id,
            })
            d += timedelta(days=1)

    # mreža koledarja (tedni)
    cal = calendar.Calendar(firstweekday=0)  # ponedeljek
    weeks = cal.monthdayscalendar(y, m)      # 0 = izven meseca

    # legenda – delavci, ki imajo dopust v tem mesecu
    legend = {}
    for e in entries:
        legend[e.user_id] = {"name": e.user.full_name if e.user else "?",
                             "color": leave_color_for(e.user_id)}

    users = User.query.filter(User.is_active_user==True, User.role!="kupec").order_by(User.full_name).all()
    (py, pm), (ny, nm) = _prev_next(y, m)

    return render_template("staff/leave.html",
                           year=y, month=m, month_name=SL_MONTHS[m],
                           weeks=weeks, day_map=day_map, dow=SL_DOW,
                           legend=legend.values(), users=users,
                           prev_y=py, prev_m=pm, next_y=ny, next_m=nm,
                           today=date.today())


@staff_bp.route("/dopusti/add", methods=["POST"])
@login_required
def add_leave():
    # delavec lahko vpiše samo zase; admin za kogarkoli
    target_id = request.form.get("user_id", type=int)
    if not current_user.is_admin or not target_id:
        target_id = current_user.id

    try:
        sd = datetime.strptime(request.form.get("start_date", ""), "%Y-%m-%d").date()
        ed = datetime.strptime(request.form.get("end_date", ""), "%Y-%m-%d").date()
    except ValueError:
        flash("Vpiši veljaven datum (od – do).", "danger")
        return redirect(url_for("staff.leave"))
    if ed < sd:
        sd, ed = ed, sd

    db.session.add(LeaveEntry(user_id=target_id, start_date=sd, end_date=ed,
                              note=request.form.get("note", "").strip()))
    db.session.commit()
    flash("Dopust dodan.", "success")
    return redirect(url_for("staff.leave", year=sd.year, month=sd.month))


@staff_bp.route("/dopusti/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_leave(entry_id):
    e = LeaveEntry.query.get_or_404(entry_id)
    if not current_user.is_admin and e.user_id != current_user.id:
        flash("Brišeš lahko samo svoje vnose.", "danger")
        return redirect(url_for("staff.leave"))
    y, m = e.start_date.year, e.start_date.month
    db.session.delete(e)
    db.session.commit()
    flash("Dopust izbrisan.", "info")
    return redirect(url_for("staff.leave", year=y, month=m))


@staff_bp.route("/dopusti/seznam")
@login_required
def leave_list():
    # admin vidi vse; delavec samo svoje
    q = LeaveEntry.query
    if not current_user.is_admin:
        q = q.filter_by(user_id=current_user.id)
    entries = q.order_by(LeaveEntry.start_date.desc()).all()
    return render_template("staff/leave_list.html", entries=entries)


# ── URE (mesečni obrazec po dnevih) ───────────────────────────────────────────
@staff_bp.route("/ure")
@login_required
def hours():
    y, m = _ym()

    # admin lahko izbere delavca; delavec vidi samo sebe
    if current_user.is_admin and request.args.get("user_id", type=int):
        target = User.query.get_or_404(request.args.get("user_id", type=int))
    else:
        target = current_user

    days_in_month = calendar.monthrange(y, m)[1]
    existing = {wh.work_date.day: wh for wh in WorkHours.query.filter(
        WorkHours.user_id == target.id,
        WorkHours.work_date >= date(y, m, 1),
        WorkHours.work_date <= date(y, m, days_in_month),
    ).all()}

    rows = []
    sum_h = sum_o = 0.0
    for d in range(1, days_in_month + 1):
        dt = date(y, m, d)
        wh = existing.get(d)
        h = wh.hours if wh else 0
        o = wh.overtime if wh else 0
        sum_h += h or 0
        sum_o += o or 0
        # oddelano (iz prihod/odhod), če obstaja
        worked = ""
        if wh and wh.arrival and wh.departure:
            try:
                ah, am = map(int, wh.arrival.split(":"))
                dh, dm = map(int, wh.departure.split(":"))
                diff = (dh * 60 + dm) - (ah * 60 + am)
                if diff > 0:
                    worked = round(diff / 60 * 2) / 2
            except (ValueError, AttributeError):
                worked = ""
        rows.append({"day": d, "dow": SL_DOW[dt.weekday()],
                     "dow_idx": dt.weekday(),
                     "weekend": dt.weekday() >= 5,
                     "arrival": wh.arrival if wh else "",
                     "departure": wh.departure if wh else "",
                     "worked": (f"{worked:g} h" if worked != "" else ""),
                     "hours": h or "", "overtime": o if (wh and o) else "",
                     "note": wh.note if wh else ""})

    # ure na 15 min (05:00–22:00)
    time_options = []
    for hh in range(5, 23):
        for mm in (0, 15, 30, 45):
            time_options.append(f"{hh:02d}:{mm:02d}")
    # izbor ur/nadur (0–16 po 0.5)
    hour_options = [x / 2 for x in range(0, 33)]

    users = User.query.filter(User.is_active_user==True, User.role!="kupec").order_by(User.full_name).all()
    (py, pm), (ny, nm) = _prev_next(y, m)

    locked = MonthLock.query.filter_by(user_id=target.id, year=y, month=m).first() is not None
    can_edit = (not locked) or current_user.is_admin

    return render_template("staff/hours.html",
                           year=y, month=m, month_name=SL_MONTHS[m],
                           rows=rows, target=target,
                           sum_h=sum_h, sum_o=sum_o, sum_total=sum_h + sum_o,
                           is_admin=current_user.is_admin, users=users,
                           time_options=time_options, hour_options=hour_options,
                           locked=locked, can_edit=can_edit,
                           prev_y=py, prev_m=pm, next_y=ny, next_m=nm)


@staff_bp.route("/ure/save", methods=["POST"])
@login_required
def save_hours():
    y = request.form.get("year", type=int)
    m = request.form.get("month", type=int)

    # admin lahko shrani za izbranega; sicer zase
    target_id = request.form.get("user_id", type=int)
    if not current_user.is_admin or not target_id:
        target_id = current_user.id

    # zaklenjen mesec lahko spreminja samo admin
    locked = MonthLock.query.filter_by(user_id=target_id, year=y, month=m).first() is not None
    if locked and not current_user.is_admin:
        flash("Ta mesec je zaključen in ga ne moreš več urejati. Obrni se na admina.", "danger")
        return redirect(url_for("staff.hours", year=y, month=m))

    days_in_month = calendar.monthrange(y, m)[1]
    for d in range(1, days_in_month + 1):
        arr = (request.form.get(f"a_{d}", "") or "").strip()
        dep = (request.form.get(f"d_{d}", "") or "").strip()
        h_raw = (request.form.get(f"h_{d}", "") or "").strip().replace(",", ".")
        o_raw = (request.form.get(f"o_{d}", "") or "").strip().replace(",", ".")
        note = (request.form.get(f"n_{d}", "") or "").strip()
        try:
            h = float(h_raw) if h_raw else 0
        except ValueError:
            h = 0
        try:
            o = float(o_raw) if o_raw else 0
        except ValueError:
            o = 0

        dt = date(y, m, d)
        wh = WorkHours.query.filter_by(user_id=target_id, work_date=dt).first()
        if h == 0 and o == 0 and not note and not arr and not dep:
            if wh:
                db.session.delete(wh)
            continue
        if not wh:
            wh = WorkHours(user_id=target_id, work_date=dt)
            db.session.add(wh)
        wh.arrival, wh.departure = arr or None, dep or None
        wh.hours, wh.overtime, wh.note = h, o, note

    db.session.commit()
    flash("Ure shranjene.", "success")
    return redirect(url_for("staff.hours", year=y, month=m,
                            user_id=target_id if current_user.is_admin else None))


# ── Zaključi / odkleni mesec (samo admin lahko odklene) ──────────────────────
@staff_bp.route("/ure/zakljuci", methods=["POST"])
@login_required
def lock_month():
    y = request.form.get("year", type=int)
    m = request.form.get("month", type=int)
    target_id = request.form.get("user_id", type=int)
    if not current_user.is_admin or not target_id:
        target_id = current_user.id

    existing = MonthLock.query.filter_by(user_id=target_id, year=y, month=m).first()
    if existing:
        # odkleniti sme samo admin
        if not current_user.is_admin:
            flash("Zaključen mesec lahko odklene samo admin.", "danger")
            return redirect(url_for("staff.hours", year=y, month=m))
        db.session.delete(existing)
        db.session.commit()
        flash("Mesec odklenjen – urejanje znova mogoče.", "info")
    else:
        db.session.add(MonthLock(user_id=target_id, year=y, month=m))
        db.session.commit()
        flash("Mesec zaključen in shranjen v arhiv.", "success")
    return redirect(url_for("staff.hours", year=y, month=m,
                            user_id=target_id if current_user.is_admin else None))


# ── Tisk ur (trenutni mesec) ─────────────────────────────────────────────────
@staff_bp.route("/ure/print")
@login_required
def print_hours():
    y, m = _ym()
    if current_user.is_admin and request.args.get("user_id", type=int):
        target = User.query.get_or_404(request.args.get("user_id", type=int))
    else:
        target = current_user

    days_in_month = calendar.monthrange(y, m)[1]
    existing = {wh.work_date.day: wh for wh in WorkHours.query.filter(
        WorkHours.user_id == target.id,
        WorkHours.work_date >= date(y, m, 1),
        WorkHours.work_date <= date(y, m, days_in_month),
    ).all()}

    rows = []
    sum_h = sum_o = 0.0
    for d in range(1, days_in_month + 1):
        dt = date(y, m, d)
        wh = existing.get(d)
        h = (wh.hours if wh else 0) or 0
        o = (wh.overtime if wh else 0) or 0
        sum_h += h; sum_o += o
        worked = ""
        if wh and wh.arrival and wh.departure:
            try:
                ah, am = map(int, wh.arrival.split(":"))
                dh, dm = map(int, wh.departure.split(":"))
                diff = (dh * 60 + dm) - (ah * 60 + am)
                if diff > 0:
                    worked = f"{round(diff / 60 * 2) / 2:g} h"
            except (ValueError, AttributeError):
                worked = ""
        rows.append({"day": d, "dow": SL_DOW[dt.weekday()], "weekend": dt.weekday() >= 5,
                     "arrival": (wh.arrival if wh else "") or "",
                     "departure": (wh.departure if wh else "") or "",
                     "worked": worked,
                     "hours": h or "", "overtime": o or "",
                     "note": (wh.note if wh else "") or ""})

    return render_template("staff/hours_print.html",
                           year=y, month=m, month_name=SL_MONTHS[m],
                           target=target, rows=rows,
                           sum_h=sum_h, sum_o=sum_o, sum_total=sum_h + sum_o)


# ── Arhiv (zaključeni meseci) ────────────────────────────────────────────────
@staff_bp.route("/arhiv")
@login_required
def archive():
    q = MonthLock.query
    if not current_user.is_admin:
        q = q.filter_by(user_id=current_user.id)
    locks = q.order_by(MonthLock.year.desc(), MonthLock.month.desc()).all()

    items = []
    for lk in locks:
        days = calendar.monthrange(lk.year, lk.month)[1]
        whs = WorkHours.query.filter(
            WorkHours.user_id == lk.user_id,
            WorkHours.work_date >= date(lk.year, lk.month, 1),
            WorkHours.work_date <= date(lk.year, lk.month, days),
        ).all()
        th = sum((w.hours or 0) for w in whs)
        to = sum((w.overtime or 0) for w in whs)
        items.append({"lock": lk, "name": lk.user.full_name if lk.user else "?",
                      "month_name": SL_MONTHS[lk.month], "year": lk.year, "month": lk.month,
                      "user_id": lk.user_id, "sum_h": th, "sum_o": to, "sum_total": th + to})

    return render_template("staff/archive.html", items=items, is_admin=current_user.is_admin)
