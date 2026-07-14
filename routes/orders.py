from datetime import datetime, timedelta
import os
import uuid
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from models import (
    db, Order, OrderItem, OrderStatusLog, OrderImage,
    Customer, Vehicle,
    ORDER_STATUSES, STATUS_DICT, ITEM_STATUSES, ITEM_STATUS_DICT,
    ORDER_SOURCES, ITEM_UNITS, ENGINE_TYPES, TRANSMISSIONS,
    DELIVERY_URGENCY, DELIVERY_URGENCY_DICT,
    ORDER_ITEM_CATALOG, ITEM_CATALOG_MAP,
    TIRE_WIDTHS, TIRE_ASPECTS, TIRE_DIAMETERS,
    TIRE_SEASONS, TIRE_BRANDS, MOTO_TIRE_BRANDS, AGRO_TIRE_BRANDS, TRUCK_TIRE_BRANDS,
    INQUIRY_STATUSES, INQUIRY_STATUS_DICT, ALL_STATUS_DICT,
)
from routes.vehicles import CAR_MAKES

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


# ── SMS helper (Infobip) ──────────────────────────────────────────────────────

def send_sms(telefon, sporocilo):
    if not telefon:
        return False
    telefon = telefon.replace(" ", "").replace("-", "")
    if telefon.startswith("0"):
        telefon = "386" + telefon[1:]
    telefon = telefon.replace("+", "")
    api_key  = os.environ.get("INFOBIP_API_KEY")
    base_url = os.environ.get("INFOBIP_BASE_URL")
    sender   = os.environ.get("INFOBIP_SENDER", "38651300548")
    if not api_key or not base_url:
        print("SMS ni poslan – manjka INFOBIP_API_KEY ali INFOBIP_BASE_URL")
        return False
    try:
        import http.client, json as _json
        conn = http.client.HTTPSConnection(base_url)
        payload = _json.dumps({
            "messages": [{
                "destinations": [{"to": telefon}],
                "sender": sender,
                "content": {"text": sporocilo}
            }]
        })
        headers = {
            "Authorization": f"App {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        conn.request("POST", "/sms/3/messages", payload, headers)
        res = conn.getresponse()
        data = res.read()
        print(f"SMS status: {res.status}, odgovor: {data.decode('utf-8')[:200]}")
        return res.status == 200
    except Exception as e:
        print(f"SMS izjema: {e}")
        return False


ALLOWED_IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp"}


def _save_order_images(order, files):
    """Shrani naložene slike v UPLOAD_FOLDER in zabeleži v bazo."""
    if not files:
        return
    folder = current_app.config.get("UPLOAD_FOLDER")
    if not folder:
        return
    for fs in files:
        if not fs or not fs.filename:
            continue
        ext = os.path.splitext(fs.filename)[1].lower()
        if ext not in ALLOWED_IMG_EXT:
            continue
        fname = f"order{order.id}_{uuid.uuid4().hex}{ext}"
        try:
            fs.save(os.path.join(folder, secure_filename(fname)))
            db.session.add(OrderImage(order_id=order.id, filename=fname))
        except Exception as e:
            print(f"⚠️  Slika ni shranjena: {e}")


@orders_bp.route("/image/<int:image_id>")
@login_required
def order_image(image_id):
    img = OrderImage.query.get_or_404(image_id)
    # kupec lahko vidi samo slike svojih naročil
    if getattr(current_user, "role", "") == "kupec" and img.order.employee_id != current_user.id:
        abort(403)
    folder = current_app.config.get("UPLOAD_FOLDER")
    return send_from_directory(folder, secure_filename(img.filename))


@orders_bp.route("/<int:order_id>/add_images", methods=["POST"])
@login_required
def add_images(order_id):
    """Doda slike obstoječemu naročilu (AJAX, za delavce)."""
    order = Order.query.get_or_404(order_id)
    files = request.files.getlist("images")
    added = []
    folder = current_app.config.get("UPLOAD_FOLDER")
    for fs in files:
        if not fs or not fs.filename:
            continue
        ext = os.path.splitext(fs.filename)[1].lower()
        if ext not in ALLOWED_IMG_EXT:
            continue
        fname = f"order{order.id}_{uuid.uuid4().hex}{ext}"
        try:
            fs.save(os.path.join(folder, secure_filename(fname)))
            img = OrderImage(order_id=order.id, filename=fname)
            db.session.add(img)
            db.session.flush()
            added.append({"id": img.id, "url": url_for("orders.order_image", image_id=img.id)})
        except Exception as e:
            print(f"⚠️  Slika ni shranjena: {e}")
    db.session.commit()
    return jsonify({"images": added})


@orders_bp.route("/image/<int:image_id>/delete", methods=["POST"])
@login_required
def delete_image(image_id):
    """Izbriše sliko naročila (AJAX)."""
    img = OrderImage.query.get_or_404(image_id)
    folder = current_app.config.get("UPLOAD_FOLDER")
    try:
        import os as _os
        _os.remove(_os.path.join(folder, secure_filename(img.filename)))
    except Exception:
        pass
    db.session.delete(img)
    db.session.commit()
    return jsonify({"ok": True})


# ── Pomožno: razlikovanje naročilo / povpraševanje ─────────────────────────────

def _kind_cfg(kind):
    """Vrne nastavitve za dani tip (naročilo ali povpraševanje)."""
    if kind == "povprasevanje":
        return {
            "kind": "povprasevanje",
            "prefix": "POV",
            "initial_status": "oddano",
            "statuses": INQUIRY_STATUSES,
            "status_dict": INQUIRY_STATUS_DICT,
            "page_title": "Povpraševanja",
            "new_title": "Novo povpraševanje",
            "list_endpoint": "orders.list_inquiries",
            "new_endpoint": "orders.new_inquiry",
        }
    return {
        "kind": "narocilo",
        "prefix": "NAR",
        "initial_status": "novo",
        "statuses": ORDER_STATUSES,
        "status_dict": STATUS_DICT,
        "page_title": "Naročila",
        "new_title": "Novo naročilo",
        "list_endpoint": "orders.list_orders",
        "new_endpoint": "orders.new_order",
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def generate_order_number(kind="narocilo"):
    prefix = _kind_cfg(kind)["prefix"]
    year = datetime.utcnow().year
    last = (
        Order.query
        .filter(Order.order_number.like(f"{prefix}-{year}-%"))
        .order_by(Order.id.desc())
        .first()
    )
    if last:
        try:
            num = int(last.order_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = Order.query.filter_by(kind=kind).count() + 1
    else:
        num = 1
    return f"{prefix}-{year}-{num:04d}"


# ── List ──────────────────────────────────────────────────────────────────────

@orders_bp.route("/")
@login_required
def list_orders():
    return _render_list("narocilo")


@orders_bp.route("/povprasevanja/")
@login_required
def list_inquiries():
    return _render_list("povprasevanje")


def _render_list(kind):
    cfg = _kind_cfg(kind)
    status_filter   = request.args.get("status", "")
    customer_filter = request.args.get("customer_id", "")
    date_from_str   = request.args.get("date_from", "")
    date_to_str     = request.args.get("date_to", "")
    search          = request.args.get("search", "").strip()

    q = Order.query.filter_by(kind=kind)

    # Kupec vidi samo svoja naročila/povpraševanja
    is_kupec = getattr(current_user, "role", "") == "kupec"
    if is_kupec:
        q = q.filter_by(employee_id=current_user.id)

    if status_filter:
        q = q.filter_by(status=status_filter)
    if customer_filter and not is_kupec:
        q = q.filter_by(customer_id=int(customer_filter))
    if date_from_str:
        try:
            q = q.filter(Order.created_at >= datetime.strptime(date_from_str, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to_str:
        try:
            dt_to = datetime.strptime(date_to_str, "%Y-%m-%d") + timedelta(days=1)
            q = q.filter(Order.created_at < dt_to)
        except ValueError:
            pass
    if search:
        q = q.join(Customer, Order.customer_id == Customer.id).filter(
            db.or_(
                Order.order_number.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )

    orders    = q.order_by(Order.created_at.desc()).all()
    customers = Customer.query.order_by(Customer.name).all()

    # Kupec si je ogledal seznam → obvestila „naročeno" označimo kot prebrana
    if is_kupec:
        changed = False
        for o in orders:
            if o.notify_customer:
                o.notify_customer = False
                changed = True
        if changed:
            db.session.commit()

    # Razčlenitev po statusih (za pregled na vrhu seznama)
    breakdown = []
    for key, label, color in cfg["statuses"]:
        bq = Order.query.filter_by(kind=kind, status=key)
        if is_kupec:
            bq = bq.filter_by(employee_id=current_user.id)
        breakdown.append({
            "key": key, "label": label, "color": color,
            "count": bq.count(),
        })

    return render_template(
        "orders/list.html",
        orders=orders,
        customers=customers,
        statuses=cfg["statuses"],
        STATUS_DICT=cfg["status_dict"],
        status_filter=status_filter,
        customer_filter=customer_filter,
        date_from=date_from_str,
        date_to=date_to_str,
        search=search,
        kind=kind,
        page_title=cfg["page_title"],
        new_title=cfg["new_title"],
        new_url=url_for(cfg["new_endpoint"]),
        list_url=url_for(cfg["list_endpoint"]),
        status_breakdown=breakdown,
    )


# ── New order ─────────────────────────────────────────────────────────────────

@orders_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_order():
    return _handle_new("narocilo")


@orders_bp.route("/povprasevanja/new", methods=["GET", "POST"])
@login_required
def new_inquiry():
    return _handle_new("povprasevanje")


def _handle_new(kind):
    cfg = _kind_cfg(kind)
    if request.method == "POST":
        f = request.form
        is_kupec = getattr(current_user, "role", "") == "kupec"

        # ── Telefon obstoječe stranke: shrani TAKOJ (ne glede na uspeh naročila) ──
        try:
            upd_cust_id = f.get("update_customer_id", "").strip()
            upd_phone   = f.get("update_customer_phone", "").strip()
            if upd_cust_id and upd_phone and upd_cust_id.isdigit():
                upd_cust = Customer.query.get(int(upd_cust_id))
                if upd_cust and (upd_cust.phone or "") != upd_phone:
                    upd_cust.phone = upd_phone
                    db.session.commit()
        except Exception as _phone_err:
            print(f"Telefon shranjevanje: {_phone_err}")
            db.session.rollback()

        # ── Obvezna polja (ime, telefon vedno; znamka vozila samo pri naročilih) ──
        errors = []
        existing_cust = f.get("customer_id", "").strip()
        using_existing_cust = (not is_kupec) and existing_cust and existing_cust != "new"

        if using_existing_cust:
            _c = Customer.query.get(int(existing_cust)) if existing_cust.isdigit() else None
            if not _c:
                errors.append("Izbrana stranka ni veljavna.")
            else:
                if not (_c.name or "").strip():
                    errors.append("Izbrana stranka nima imena.")
                if not (_c.phone or "").strip():
                    errors.append("Izbrana stranka nima telefona – dopolni jo ali vpiši novo.")
        else:
            if not f.get("new_customer_name", "").strip():
                errors.append("Ime in priimek stranke sta obvezna.")
            if not f.get("new_customer_phone", "").strip():
                errors.append("Telefon stranke je obvezen.")

        # Znamka vozila obvezna SAMO pri naročilih
        if kind == "narocilo":
            has_existing_veh = f.get("existing_vehicle_id", "").strip().isdigit()
            has_new_brand = bool(f.get("new_vehicle_brand", "").strip())
            if not (has_existing_veh or has_new_brand):
                errors.append("Znamka vozila je obvezna.")

        # Kupec mora pri naročilu izbrati nujnost dostave
        if is_kupec and kind == "narocilo":
            if f.get("delivery_urgency", "") not in DELIVERY_URGENCY_DICT:
                errors.append("Izberi, kdaj potrebuješ nadomestne dele.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return _render_new_order_form(kind, form_data=request.form)

        # ── Stranka ──────────────────────────────────────────────────────────
        if is_kupec:
            # Kupec ne vidi baze strank – vpiše samo ime končne stranke
            name = f.get("new_customer_name", "").strip()
            if not name:
                flash("Vpiši ime stranke.", "danger")
                return _render_new_order_form(kind, form_data=request.form)
            customer = Customer(
                name    = name,
                phone   = f.get("new_customer_phone", "").strip(),
                email   = "",
                address = "",
            )
            db.session.add(customer)
            db.session.flush()
            customer_id = customer.id
        else:
            customer_id = f.get("customer_id", "").strip()
            if not customer_id or customer_id == "new":
                name = f.get("new_customer_name", "").strip()
                if not name:
                    flash("Ime stranke je obvezno.", "danger")
                    return _render_new_order_form(kind, form_data=request.form)
                customer = Customer(
                    name    = name,
                    phone   = f.get("new_customer_phone", "").strip(),
                    email   = f.get("new_customer_email", "").strip(),
                    address = f.get("new_customer_address", "").strip(),
                )
                db.session.add(customer)
                db.session.flush()
                customer_id = customer.id
            else:
                customer_id = int(customer_id)

        # ── Vozilo ───────────────────────────────────────────────────────────
        existing_id = f.get("existing_vehicle_id", "").strip()
        if existing_id.isdigit():
            vehicle_id = int(existing_id)
        else:
            brand = f.get("new_vehicle_brand", "").strip()
            model = f.get("new_vehicle_model", "").strip()
            if brand and model:
                year_raw = f.get("new_vehicle_year", "").strip()
                vehicle = Vehicle(
                    customer_id         = customer_id,
                    brand               = brand,
                    model               = model,
                    vin                 = f.get("new_vehicle_vin",          "").strip() or None,
                    year                = int(year_raw) if year_raw.isdigit() else None,
                    engine_type         = f.get("new_vehicle_engine_type",  "").strip(),
                    engine_displacement = f.get("new_vehicle_displacement", "").strip(),
                    engine_power_kw     = f.get("new_vehicle_power",        "").strip(),
                    transmission        = f.get("new_vehicle_transmission", "").strip(),
                    color               = f.get("new_vehicle_color",        "").strip(),
                    registration        = f.get("new_vehicle_registration", "").strip(),
                )
                db.session.add(vehicle)
                db.session.flush()
                vehicle_id = vehicle.id
            else:
                vehicle_id = None

        # ── Naročilo / povpraševanje ─────────────────────────────────────────
        order = Order(
            order_number = generate_order_number(kind),
            kind         = kind,
            customer_id  = customer_id,
            vehicle_id   = vehicle_id,
            employee_id  = current_user.id,
            status       = cfg["initial_status"],
            source       = f.get("source", "klic"),
            notes        = f.get("notes", "").strip(),
            delivery_urgency = (f.get("delivery_urgency") if f.get("delivery_urgency") in DELIVERY_URGENCY_DICT else None),
        )
        db.session.add(order)
        db.session.flush()

        # ── Postavke (iz kataloga – samo označene) ────────────────────────────
        selected = f.getlist("items")

        def add_item(description, key):
            raw_qty = f.get(f"kol_{key}", "1").strip().replace(",", ".")
            try:
                qty = float(raw_qty)
                if qty <= 0:
                    qty = 1
            except ValueError:
                qty = 1
            db.session.add(OrderItem(
                order_id    = order.id,
                description = description,
                bartog_id   = f.get(f"ident_{key}", "").strip(),
                supplier    = f.get(f"izvor_{key}", "").strip(),
                quantity    = qty,
                unit        = "kos",
                status      = "caka",
            ))

        for key in selected:
            if key in ITEM_CATALOG_MAP:
                category, label = ITEM_CATALOG_MAP[key]
                add_item(f"{category} – {label}", key)

        # Pnevmatike – osebne
        if "PNEVMATIKE" in selected:
            w = f.get("tire_width", "").strip()
            a = f.get("tire_aspect", "").strip()
            d = f.get("tire_diameter", "").strip()
            dim = f"{w}/{a} R{d}" if (w and a and d) else ""
            meta = " · ".join(x for x in [f.get("tire_season", "").strip(),
                                          f.get("tire_brand", "").strip()] if x)
            desc = "Pnevmatike"
            if dim:  desc += f" {dim}"
            if meta: desc += f" · {meta}"
            add_item(desc, "PNEVMATIKE")

        # Pnevmatike – moto / agro / tovorne
        for key, label in [("MOTO", "Moto pnevmatike"),
                           ("AGRO", "Agro pnevmatike"),
                           ("TOVORNE", "Tovorne pnevmatike")]:
            if key in selected:
                pref = key.lower()
                dim  = f.get(f"{pref}_dim", "").strip()
                meta = " · ".join(x for x in [f.get(f"{pref}_season", "").strip(),
                                              f.get(f"{pref}_brand", "").strip()] if x)
                desc = label
                if dim:  desc += f" {dim}"
                if meta: desc += f" · {meta}"
                add_item(desc, key)

        # Ostali material – več vrstic
        om_opisi  = f.getlist("ostali_opis[]")
        om_identi = f.getlist("ostali_ident[]")
        om_izvori = f.getlist("ostali_izvor[]")
        for i, opis in enumerate(om_opisi):
            opis  = opis.strip()
            ident = om_identi[i].strip() if i < len(om_identi) else ""
            izvor = om_izvori[i].strip() if i < len(om_izvori) else ""
            if not (opis or ident):
                continue
            desc = f"Ostali material: {opis}" if opis else "Ostali material"
            db.session.add(OrderItem(
                order_id=order.id, description=desc, bartog_id=ident,
                supplier=izvor, quantity=1, unit="kos", status="caka",
            ))

        # ── Naložene slike (iskani nadomestni del) ───────────────────────────
        _save_order_images(order, request.files.getlist("order_images"))

        db.session.commit()
        what = "Povpraševanje" if kind == "povprasevanje" else "Naročilo"
        flash(f"{what} {order.order_number} je bilo uspešno ustvarjeno.", "success")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    return _render_new_order_form(kind)


def _render_new_order_form(kind="narocilo", form_data=None):
    cfg = _kind_cfg(kind)
    fd = form_data or {}
    # Pri napaki ohrani predhodno izbrano stranko / vozilo
    presel_cust = fd.get("customer_id") or request.args.get("customer_id")
    presel_veh  = fd.get("existing_vehicle_id") or request.args.get("vehicle_id")
    return render_template(
        "orders/new.html",
        customers    = Customer.query.order_by(Customer.name).all(),
        sources      = ORDER_SOURCES,
        item_catalog = ORDER_ITEM_CATALOG,
        delivery_urgency = DELIVERY_URGENCY,
        car_makes    = CAR_MAKES,
        engine_types = ENGINE_TYPES,
        transmissions = TRANSMISSIONS,
        tire_widths    = TIRE_WIDTHS,
        tire_aspects   = TIRE_ASPECTS,
        tire_diameters = TIRE_DIAMETERS,
        tire_seasons   = TIRE_SEASONS,
        tire_brands    = TIRE_BRANDS,
        moto_brands    = MOTO_TIRE_BRANDS,
        agro_brands    = AGRO_TIRE_BRANDS,
        truck_brands   = TRUCK_TIRE_BRANDS,
        preselected_customer = presel_cust,
        preselected_vehicle  = presel_veh,
        form_data   = fd,
        kind        = kind,
        page_title  = cfg["new_title"],
        form_action = url_for(cfg["new_endpoint"]),
        cancel_url  = url_for(cfg["list_endpoint"]),
    )


# ── Detail ────────────────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)

    # Kupec lahko odpre samo svoja naročila
    if getattr(current_user, "role", "") == "kupec":
        if order.employee_id != current_user.id:
            flash("Do tega naročila nimaš dostopa.", "danger")
            return redirect(url_for("orders.list_orders"))
        # ogled → obvestilo prebrano
        if order.notify_customer:
            order.notify_customer = False
            db.session.commit()

    cfg = _kind_cfg(order.kind or "narocilo")
    return render_template(
        "orders/detail.html",
        order        = order,
        statuses     = cfg["statuses"],
        item_statuses= ITEM_STATUSES,
        item_units   = ITEM_UNITS,
        STATUS_DICT  = cfg["status_dict"],
        delivery_urgency_label = DELIVERY_URGENCY_DICT.get(order.delivery_urgency, ""),
        kind         = cfg["kind"],
        page_title   = cfg["page_title"],
        list_url     = url_for(cfg["list_endpoint"]),
    )


# ── Update order status ───────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/status", methods=["POST"])
@login_required
def update_status(order_id):
    order = Order.query.get_or_404(order_id)

    # Kupec ne sme spreminjati statusa
    if getattr(current_user, "role", "") == "kupec":
        flash("Statusa ne moreš spreminjati.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))

    new_status  = request.form.get("status")
    valid_keys  = [s[0] for s in _kind_cfg(order.kind or "narocilo")["statuses"]]

    if new_status not in valid_keys:
        flash("Neveljaven status.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))

    # Rok dobave je obvezen za „Naročena – čakamo dobavo"
    if new_status == "narocena_caka":
        raw = request.form.get("delivery_days", "").strip()
        try:
            days = int(raw)
            if days < 0:
                raise ValueError
        except ValueError:
            flash("Za status Naročena – čakamo dobavo je obvezen rok dobave (število dni).", "danger")
            return redirect(url_for("orders.order_detail", order_id=order_id))
        from datetime import timedelta
        from models import today_local
        order.delivery_date = today_local() + timedelta(days=days)

    log = OrderStatusLog(
        order_id      = order.id,
        old_status    = order.status,
        new_status    = new_status,
        changed_by_id = current_user.id,
        notes         = request.form.get("status_note", "").strip(),
    )
    db.session.add(log)

    if new_status == "naroceno" and not order.ordered_at:
        order.ordered_at = datetime.utcnow()
    if new_status == "zakljuceno" and not order.completed_at:
        order.completed_at = datetime.utcnow()

    # Ko gre na „Naročeno" → obvesti kupca + SMS
    if new_status == "naroceno":
        order.notify_customer = True
        telefon = order.customer.phone if order.customer else None
        if telefon:
            send_sms(telefon,
                "Pozdravljeni! Vaše naročilo je bilo uspešno obdelano. "
                "Naročene nadomestne dele lahko prevzamete osebno ali pa "
                "vam jih dostavimo v okviru naših rednih dostavnih terminov.\n"
                "Hvala za vaše zaupanje!\n"
                "Ekipa Bartog Ajdovščina"
            )

    order.status     = new_status
    order.updated_at = datetime.utcnow()
    db.session.commit()

    label = ALL_STATUS_DICT.get(new_status, {}).get("label", new_status)
    flash(f"Status posodobljen → {label}", "success")
    return redirect(url_for("orders.order_detail", order_id=order_id))


# ── Update item status ────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/item/<int:item_id>/status", methods=["POST"])
@login_required
def update_item_status(order_id, item_id):
    item = OrderItem.query.get_or_404(item_id)
    if item.order_id != order_id:
        flash("Napaka.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))

    new_status = request.form.get("status")
    if new_status in [s[0] for s in ITEM_STATUSES]:
        item.status = new_status
        db.session.commit()

    return redirect(url_for("orders.order_detail", order_id=order_id))


# ── Save items (edit / add / delete) ──────────────────────────────────────────

@orders_bp.route("/<int:order_id>/items/save", methods=["POST"])
@login_required
def save_items(order_id):
    order = Order.query.get_or_404(order_id)
    f = request.form

    def parse_qty(raw):
        try:
            return float((raw or "1").replace(",", "."))
        except ValueError:
            return 1.0

    valid_item_statuses = [s[0] for s in ITEM_STATUSES]

    # ── Obstoječe postavke ──
    item_ids   = f.getlist("item_id[]")
    delete_ids = set(f.getlist("delete[]"))
    bartogs    = f.getlist("bartog_id[]")
    qtys       = f.getlist("quantity[]")
    units      = f.getlist("unit[]")
    supps      = f.getlist("supplier[]")
    notes      = f.getlist("notes[]")
    statuses   = f.getlist("status[]")

    for idx, iid in enumerate(item_ids):
        item = db.session.get(OrderItem, int(iid))
        if not item or item.order_id != order.id:
            continue
        if iid in delete_ids:
            db.session.delete(item)
            continue
        if idx < len(bartogs):  item.bartog_id = bartogs[idx].strip()
        if idx < len(qtys):     item.quantity  = parse_qty(qtys[idx])
        if idx < len(units):    item.unit      = units[idx]
        if idx < len(supps):    item.supplier  = supps[idx].strip()
        if idx < len(notes):    item.notes     = notes[idx].strip()
        if idx < len(statuses) and statuses[idx] in valid_item_statuses:
            item.status = statuses[idx]

    # ── Nove postavke ──
    nd = f.getlist("new_description[]")
    nb = f.getlist("new_bartog[]")
    nq = f.getlist("new_quantity[]")
    nu = f.getlist("new_unit[]")
    ns = f.getlist("new_supplier[]")
    nn = f.getlist("new_notes[]")
    for idx, desc in enumerate(nd):
        desc = desc.strip()
        if not desc:
            continue
        db.session.add(OrderItem(
            order_id    = order.id,
            description = desc,
            bartog_id   = nb[idx].strip() if idx < len(nb) else "",
            quantity    = parse_qty(nq[idx] if idx < len(nq) else "1"),
            unit        = nu[idx] if idx < len(nu) else "kos",
            supplier    = ns[idx].strip() if idx < len(ns) else "",
            notes       = nn[idx].strip() if idx < len(nn) else "",
            status      = "caka",
        ))

    order.updated_at = datetime.utcnow()
    db.session.commit()
    flash("Postavke so bile shranjene.", "success")
    return redirect(url_for("orders.order_detail", order_id=order.id))


# ── Datum dobave (povpraševanja) ──────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/delivery", methods=["POST"])
@login_required
def set_delivery(order_id):
    from datetime import timedelta
    from models import today_local
    order = Order.query.get_or_404(order_id)
    raw = request.form.get("days", "").strip()
    if raw == "":
        order.delivery_date = None
        flash("Datum dobave odstranjen.", "info")
    else:
        try:
            days = max(0, int(raw))
            order.delivery_date = today_local() + timedelta(days=days)
            flash(f"Dobava predvidena čez {days} dni.", "success")
        except ValueError:
            flash("Vnesi število dni.", "danger")
    db.session.commit()
    return redirect(url_for("orders.order_detail", order_id=order.id))


# ── Delete order (admin only) ─────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    if not current_user.is_admin:
        flash("Samo administratorji lahko brišejo.", "danger")
        return redirect(url_for("orders.order_detail", order_id=order_id))
    num = order.order_number
    list_endpoint = _kind_cfg(order.kind or "narocilo")["list_endpoint"]
    is_inq = (order.kind == "povprasevanje")
    db.session.delete(order)
    db.session.commit()
    flash(f"{'Povpraševanje' if is_inq else 'Naročilo'} {num} je bilo izbrisano.", "info")
    # vrni se tja, od koder je bil klic (npr. pregled), sicer na seznam
    ref = request.referrer
    if ref and url_for(list_endpoint) not in ref:
        return redirect(ref)
    return redirect(url_for(list_endpoint))


# ── AJAX: vehicles for customer ───────────────────────────────────────────────

@orders_bp.route("/api/customer/<int:customer_id>/vehicles")
@login_required
def get_customer_vehicles(customer_id):
    vehicles = Vehicle.query.filter_by(customer_id=customer_id).all()
    return jsonify([
        {
            "id":           v.id,
            "name":         v.display_name,
            "brand":        v.brand,
            "model":        v.model,
            "year":         v.year,
            "vin":          v.vin or "",
            "registration": v.registration or "",
            "engine_type":  v.engine_type or "",
        }
        for v in vehicles
    ])
