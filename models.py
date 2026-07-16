from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def today_local():
    """Današnji datum po slovenskem času."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Ljubljana")).date()
    except Exception:
        return datetime.now().date()


# ── Lookup tables ────────────────────────────────────────────────────────────

ORDER_STATUSES = [
    ("novo",                  "Novo naročilo",         "danger"),
    ("poslano_povprasevanje", "Naročilo v obdelavi",   "warning"),
    ("naroceno",              "Naročeno",              "success"),
]

STATUS_DICT = {s[0]: {"label": s[1], "color": s[2]} for s in ORDER_STATUSES}

# Stari statusi – samo za prikaz morebitnih obstoječih zapisov
LEGACY_STATUS_DICT = {
    "caka":       {"label": "Čaka na naročilo", "color": "warning"},
    "v_dostavi":  {"label": "V dostavi",        "color": "primary"},
    "prejeto":    {"label": "Prejeto",          "color": "success"},
    "zakljuceno": {"label": "Zaključeno",       "color": "dark"},
    "preklicano": {"label": "Preklicano",       "color": "danger"},
}

# Statusi povpraševanj (ločen nabor)
INQUIRY_STATUSES = [
    ("oddano",        "Poslano povpraševanje",     "danger"),
    ("ponudba",       "Ponudba poslana stranki",   "warning"),
    ("narocena_caka", "Naročena – čakamo dobavo",  "success"),
    ("dobavljeno",    "Dobavljeno",                "secondary"),
    ("ni_dobave",     "Ni dobave",                 "dark"),
    ("ne_zeli",       "Stranka ne želi naročiti",  "dark"),
]
INQUIRY_STATUS_DICT = {s[0]: {"label": s[1], "color": s[2]} for s in INQUIRY_STATUSES}

# Združen slovar za prikaz oznak (ključi se ne prekrivajo)
ALL_STATUS_DICT = {**LEGACY_STATUS_DICT, **STATUS_DICT, **INQUIRY_STATUS_DICT}

ITEM_STATUSES = [
    ("caka",       "Čaka",       "warning"),
    ("naroceno",   "Naročeno",   "info"),
    ("v_dostavi",  "V dostavi",  "primary"),
    ("prejeto",    "Prejeto",    "success"),
    ("ni_voljo",   "Ni na voljo","danger"),
]

ITEM_STATUS_DICT = {s[0]: {"label": s[1], "color": s[2]} for s in ITEM_STATUSES}

ORDER_SOURCES = ["klic", "whatsapp", "email", "osebno", "drugo"]

# Nujnost dostave (izbere končni kupec – Bartog)
DELIVERY_URGENCY = [
    ("takoj",     "Nadomestne dele potrebujem takoj"),
    ("takoj_pop", "Nadomestne dele potrebujem takoj – lahko s popoldansko dostavo"),
    ("jutri",     "Nadomestne dele potrebujem jutri"),
]
DELIVERY_URGENCY_DICT = {k: v for k, v in DELIVERY_URGENCY}
ENGINE_TYPES  = ["bencin", "diesel", "hibrid", "elektro", "plin", "drugo"]
TRANSMISSIONS = ["ročni", "avtomatski", "poluavtomatski"]
ITEM_UNITS    = ["kos", "komplet", "liter", "par", "set", "ura"]


# ── Models ────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    full_name     = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False)
    is_active_user= db.Column(db.Boolean, default=True)
    role          = db.Column(db.String(20), default="zaposleni")  # admin|zaposleni|kupec
    login_token   = db.Column(db.String(64))   # za prijavo prek QR povezave (samo kupci)
    linked_customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)  # poveže kupca s stranko
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="employee", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Customer(db.Model):
    __tablename__ = "customers"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    phone      = db.Column(db.String(50))
    email      = db.Column(db.String(120))
    address    = db.Column(db.String(300))
    notes      = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vehicles = db.relationship("Vehicle", backref="customer", lazy=True, cascade="all, delete-orphan")
    orders   = db.relationship("Order",   backref="customer", lazy=True)

    def __repr__(self):
        return f"<Customer {self.name}>"


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id                  = db.Column(db.Integer, primary_key=True)
    customer_id         = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    vin                 = db.Column(db.String(17))
    brand               = db.Column(db.String(100), nullable=False)
    model               = db.Column(db.String(100), nullable=False)
    year                = db.Column(db.Integer)
    engine_type         = db.Column(db.String(50))
    engine_displacement = db.Column(db.String(20))   # npr. 2.0
    engine_power_kw     = db.Column(db.String(20))   # kW
    transmission        = db.Column(db.String(50))
    color               = db.Column(db.String(50))
    registration        = db.Column(db.String(20))   # registrska
    notes               = db.Column(db.Text)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="vehicle", lazy=True)

    @property
    def display_name(self):
        parts = [self.brand, self.model]
        if self.year:
            parts.append(f"({self.year})")
        if self.registration:
            parts.append(f"· {self.registration}")
        return " ".join(parts)

    def __repr__(self):
        return f"<Vehicle {self.brand} {self.model}>"


class Order(db.Model):
    __tablename__ = "orders"

    id           = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    kind         = db.Column(db.String(20), default="narocilo", nullable=False)  # narocilo | povprasevanje
    customer_id  = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    vehicle_id   = db.Column(db.Integer, db.ForeignKey("vehicles.id"))
    employee_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status       = db.Column(db.String(20), default="novo", nullable=False)
    source       = db.Column(db.String(50), default="klic")
    notes        = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ordered_at   = db.Column(db.DateTime)    # ko je naročeno
    completed_at = db.Column(db.DateTime)    # ko je zaključeno
    delivery_date = db.Column(db.Date)       # predviden prihod materiala (povpraševanja)
    notify_customer = db.Column(db.Boolean, default=False)  # nova obvestilo za kupca (npr. naročeno)
    delivery_urgency = db.Column(db.String(20))  # kupčeva nujnost: takoj | takoj_pop | jutri

    items       = db.relationship("OrderItem",      backref="order", lazy=True, cascade="all, delete-orphan")
    status_logs = db.relationship("OrderStatusLog", backref="order", lazy=True, cascade="all, delete-orphan")

    @property
    def status_info(self):
        return ALL_STATUS_DICT.get(self.status, {"label": self.status, "color": "secondary"})

    @property
    def delivery_days_left(self):
        if not self.delivery_date:
            return None
        return (self.delivery_date - today_local()).days

    def __repr__(self):
        return f"<Order {self.order_number}>"


class OrderImage(db.Model):
    __tablename__ = "order_images"

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    filename   = db.Column(db.String(255), nullable=False)  # shranjeno ime datoteke
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship("Order", backref=db.backref("images", lazy=True, cascade="all, delete-orphan"))


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id          = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    bartog_id   = db.Column(db.String(100))
    supplier    = db.Column(db.String(100), default="Bartog")
    quantity    = db.Column(db.Float, default=1)
    unit        = db.Column(db.String(20), default="kos")
    status      = db.Column(db.String(20), default="caka")
    notes       = db.Column(db.Text)

    @property
    def status_info(self):
        return ITEM_STATUS_DICT.get(self.status, {"label": self.status, "color": "secondary"})


class OrderStatusLog(db.Model):
    __tablename__ = "order_status_logs"

    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    old_status      = db.Column(db.String(20))
    new_status      = db.Column(db.String(20))
    changed_by_id   = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes           = db.Column(db.String(300))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    changed_by = db.relationship("User")

    @property
    def old_status_info(self):
        return STATUS_DICT.get(self.old_status, {"label": self.old_status, "color": "secondary"}) if self.old_status else None

    @property
    def new_status_info(self):
        return STATUS_DICT.get(self.new_status, {"label": self.new_status, "color": "secondary"})


# ── Beležka (skupna tabla obvestil med zaposlenimi) ───────────────────────────
NOTE_PEOPLE = ["Alan Daksobler", "Sašo Juretič", "Vid Kenda", "Rok Jerkič",
               "Nejc Tominec", "Borut Čermelj"]


class Note(db.Model):
    __tablename__ = "notes"

    id         = db.Column(db.Integer, primary_key=True)
    text       = db.Column(db.Text, nullable=False)
    person     = db.Column(db.String(100))           # za koga je beležka
    done       = db.Column(db.Boolean, default=False)  # obdelano / za obdelat
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    done_at    = db.Column(db.DateTime)
    creator_seen_done = db.Column(db.Boolean, default=False)  # je ustvarjalec videl da je obdelano

    created_by = db.relationship("User")


# ── Dostava (rute) ────────────────────────────────────────────────────────────
DELIVERY_ROUTES = [
    ("vipava",         "Ruta Vipava"),
    ("selo",           "Ruta Selo"),
    ("kras_planina",   "Ruta Kras + Planina"),
    ("idrija",         "Ruta Idrija + gora"),
    ("vrhnika",        "Ruta Vrhnika"),
]
DELIVERY_ROUTE_DICT = {k: v for k, v in DELIVERY_ROUTES}


class DeliveryStop(db.Model):
    __tablename__ = "delivery_stops"

    id          = db.Column(db.Integer, primary_key=True)
    route       = db.Column(db.String(30), nullable=False)   # ključ rute
    customer    = db.Column(db.String(150), nullable=False)  # ime stranke
    address     = db.Column(db.String(250))                  # naslov
    phone       = db.Column(db.String(50))
    note        = db.Column(db.String(300))
    tires       = db.Column(db.String(50))                   # pnevmatike (število/opis)
    position    = db.Column(db.Integer, default=0)           # vrstni red v ruti
    done        = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


# ── Dopusti (koledar) ─────────────────────────────────────────────────────────
# Stabilne barve po delavcu (za koledar)
LEAVE_COLORS = [
    "#ef4444", "#3b82f6", "#22c55e", "#f59e0b", "#a855f7",
    "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
]


def leave_color_for(user_id):
    return LEAVE_COLORS[(user_id or 0) % len(LEAVE_COLORS)]


class LeaveEntry(db.Model):
    __tablename__ = "leave_entries"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date   = db.Column(db.Date, nullable=False)
    note       = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")


# ── Ure (mesečni obrazec po dnevih) ───────────────────────────────────────────
class WorkHours(db.Model):
    __tablename__ = "work_hours"

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    arrival   = db.Column(db.String(5))            # prihod "HH:MM"
    departure = db.Column(db.String(5))            # odhod "HH:MM"
    hours     = db.Column(db.Float, default=0)     # redne ure
    overtime  = db.Column(db.Float, default=0)     # nadure
    note      = db.Column(db.String(200))

    user = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("user_id", "work_date", name="uq_user_day"),)


class MonthLock(db.Model):
    """Zaklenjen mesec – delavec ne more več urejati, admin lahko."""
    __tablename__ = "month_locks"

    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    year     = db.Column(db.Integer, nullable=False)
    month    = db.Column(db.Integer, nullable=False)
    locked_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("user_id", "year", "month", name="uq_lock"),)


# ── Katalog postavk za novo naročilo ─────────────────────────────────────────
# Glavne rubrike s podgrupami. Delavec pokljuka, kar potrebuje, in vpiše
# IDENT (Bartog) ter izvor zaloge. Neoznačeno se v naročilo ne shrani.

ORDER_ITEM_CATALOG = [
    {
        "category": "Mali servis",
        "items": [
            {"key": "FO",     "label": "FO"},
            {"key": "FZ",     "label": "FZ"},
            {"key": "FK",     "label": "FK"},
            {"key": "FG",     "label": "FG"},
            {"key": "OLJE",   "label": "OLJE"},
            {"key": "SVECKE", "label": "SVEČKE"},
        ],
    },
    {
        "category": "Velik servis",
        "items": [
            {"key": "GZ",        "label": "GZ"},
            {"key": "VC",        "label": "VČ"},
            {"key": "GZVC",      "label": "GZ+VČ"},
            {"key": "MJ",        "label": "MJ"},
            {"key": "NAPENJALEC","label": "NAPENJALEC"},
            {"key": "DRSNIK",    "label": "DRSNIK"},
            {"key": "SET_MIKRO", "label": "SET MIKRO JERMENA"},
        ],
    },
    {
        "category": "Zavore in podvozje",
        "items": [
            {"key": "PD",            "label": "PD"},
            {"key": "PP",            "label": "PP"},
            {"key": "INDIKATOR_SP",  "label": "INDIKATOR (spredaj)"},
            {"key": "ZD",            "label": "ZD"},
            {"key": "ZP",            "label": "ZP"},
            {"key": "INDIKATOR_ZA",  "label": "INDIKATOR (zadaj)"},
            {"key": "PD_CELJUST",    "label": "PD ČELJUST"},
            {"key": "PL_CELJUST",    "label": "PL ČELJUST"},
            {"key": "ZD_CELJUST",    "label": "ZD ČELJUST"},
            {"key": "ZL_CELJUST",    "label": "ZL ČELJUST"},
            {"key": "ZICE_ROCNE",    "label": "ŽICE ROČNE"},
            {"key": "FERODE",        "label": "FERODE"},
            {"key": "ZAV_CILINDRI",  "label": "ZAVORNI CILINDRI"},
            {"key": "VOL_KONCNIK_L", "label": "VOLANSKI KONČNIK L"},
            {"key": "VOL_KONCNIK_D", "label": "VOLANSKI KONČNIK D"},
            {"key": "SPONA_VOLANA",  "label": "SPONA VOLANA"},
            {"key": "MANSETA_VOLANA","label": "MANŠETA VOLANA"},
            {"key": "MANSETA_ZUN",   "label": "MANŠETA ZUNANJA"},
            {"key": "MANSETA_NOT",   "label": "MANŠETA NOTRANJA"},
            {"key": "LEZAJ_SP",      "label": "KOLESNI LEŽAJ SPREDAJ"},
            {"key": "LEZAJ_ZA",      "label": "KOLESNI LEŽAJ ZADAJ"},
        ],
    },
]

# Ravna preslikava key -> (kategorija, oznaka)
ITEM_CATALOG_MAP = {
    it["key"]: (group["category"], it["label"])
    for group in ORDER_ITEM_CATALOG
    for it in group["items"]
}

# Standardne dimenzije pnevmatik (širina / višina R premer)
TIRE_WIDTHS    = list(range(135, 356, 10))
TIRE_ASPECTS   = list(range(25, 86, 5))
TIRE_DIAMETERS = list(range(13, 23))


# ── Pnevmatike: sezone in znamke ──────────────────────────────────────────────
TIRE_SEASONS = ["Letne", "Celoletne", "Zimske"]

# Najbolj prodajane znamke (osebne pnevmatike)
TIRE_BRANDS = [
    "Michelin", "Continental", "Bridgestone", "Goodyear", "Pirelli", "Dunlop",
    "Hankook", "Nokian", "Vredestein", "Kumho", "Yokohama", "Falken", "Toyo",
    "Cooper", "BFGoodrich", "Sava", "Barum", "Kleber", "Uniroyal", "Firestone",
    "Semperit", "Fulda", "Matador", "Maxxis", "Nexen", "GT Radial", "Riken",
    "Debica", "Kormoran", "Sailun", "Nankang", "Goodride",
]

MOTO_TIRE_BRANDS = [
    "Michelin", "Pirelli", "Bridgestone", "Metzeler", "Dunlop", "Continental",
    "Mitas", "Avon", "Maxxis", "Heidenau", "Shinko", "Anlas",
]

AGRO_TIRE_BRANDS = [
    "Mitas", "BKT", "Michelin", "Continental", "Trelleborg", "Alliance",
    "Firestone", "Kleber", "Vredestein", "Ceat", "Maxam", "Petlas",
]

TRUCK_TIRE_BRANDS = [
    "Michelin", "Continental", "Bridgestone", "Goodyear", "Hankook", "Pirelli",
    "Sava", "Barum", "Matador", "Giti", "Aeolus", "Sailun", "Triangle",
]


# ── Moto platforma: naročila delov ───────────────────────────────────────────

MOTO_BRANDS = [
    "Honda", "Yamaha", "Kawasaki", "Suzuki", "KTM", "BMW", "Ducati",
    "Husqvarna", "Triumph", "Aprilia", "Harley-Davidson", "Royal Enfield",
    "Beta", "GasGas", "Sherco", "TM Racing", "Drugo",
]

MOTO_ORDER_STATUSES = [
    ("cakanje",    "V čakanju",  "warning"),
    ("naroceno",   "Naročeno",   "primary"),
    ("prispelo",   "Prispelo",   "success"),
    ("zakljuceno", "Zaključeno", "secondary"),
]
MOTO_ORDER_STATUS_DICT = {s[0]: {"label": s[1], "color": s[2]} for s in MOTO_ORDER_STATUSES}


class MotoOrder(db.Model):
    __tablename__ = "moto_orders"

    id             = db.Column(db.Integer, primary_key=True)
    stranka        = db.Column(db.String(200), nullable=False)
    telefon        = db.Column(db.String(50))
    znamka         = db.Column(db.String(100))
    model_motorja  = db.Column(db.String(100))
    letnik         = db.Column(db.Integer)
    nadomestni_del = db.Column(db.String(500), nullable=False)
    opomba         = db.Column(db.Text)
    status         = db.Column(db.String(20), default="cakanje", nullable=False)
    created_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship("User")

    @property
    def status_info(self):
        return MOTO_ORDER_STATUS_DICT.get(self.status, {"label": self.status, "color": "secondary"})

    def __repr__(self):
        return f"<MotoOrder {self.id} – {self.stranka}>"
