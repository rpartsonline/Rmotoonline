# AutoNaročila – Evidenca naročil avtodelov

Interna aplikacija za avtoservis: evidenca telefonskih in WhatsApp naročil, 
sledenje statusov, upravljanje strank in vozil.

---

## Lokalni zagon (razvoj)

### Zahteve
- Python 3.10+
- pip

### Namestitev

```bash
# Kloniraj repozitorij
git clone https://github.com/tvoj-username/narocilnice.git
cd narocilnice

# Virtualno okolje
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Namesti odvisnosti
pip install -r requirements.txt

# Nastavi spremenljivke okolja
cp .env.example .env
# Uredi .env (vsaj SECRET_KEY)

# Zaženi
python app.py
```

Aplikacija bo dostopna na http://localhost:5000

**Privzete prijave:** `admin` / `Admin123!`  
*Geslo takoj zamenjaj pod Admin → Uporabniki!*

---

## Deploy na Render

### 1. GitHub repozitorij
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/tvoj-username/narocilnice.git
git push -u origin main
```

### 2. Ustvari Web Service na Render
1. Dashboard → **New** → **Web Service**
2. Poveži GitHub repo
3. Nastavi:
   - **Name:** `narocilnice`
   - **Language:** Python 3
   - **Branch:** `main`
   - **Region:** Frankfurt (EU Central)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Starter ali višje (disk ni na voljo na Free planu!)

### 3. Dodaj trajni disk (Disk)
Disk poskrbi, da se baza ne izbriše ob posodobitvah.
1. Med ustvarjanjem (ali kasneje pod **Settings → Disks → Add Disk**):
   - **Name:** `podatki`
   - **Mount Path:** `/var/data`
   - **Size:** 1 GB (dovolj; lahko kasneje povečaš)
2. Render samodejno dela snapshot diska vsakih 24 ur (varnostna kopija).

### 4. Environment Variables na Render
V sekciji **Environment** dodaj:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | dolg naključen niz (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ADMIN_PASSWORD` | varno geslo za admin račun |
| `DATA_DIR` | `/var/data` (ista pot kot Mount Path diska) |

> SQLite baza se bo shranila v `/var/data/narocila.db` na disku — trajno.
> `DATABASE_URL` **ni potreben**, razen če bi raje uporabljal PostgreSQL.

### 5. Deploy
Render bo avtomatsko deployal ob vsakem `git push` na `main`.

> Opomba: storitev z diskom ima ob posodobitvi nekaj sekund nedostopnosti
> (ni "zero-downtime"), ker se stari in novi proces ne smeta hkrati dotikati
> baze. Za interno orodje delavnice to ni problem.

---

## Struktura projekta

```
narocilnice/
├── app.py                  # Vstopna točka, app factory
├── models.py               # Podatkovni modeli (SQLAlchemy)
├── requirements.txt
├── Procfile                # Render: gunicorn
├── .env.example
├── routes/
│   ├── auth.py             # Prijava / odjava
│   ├── main.py             # Nadzorna plošča
│   ├── orders.py           # Naročila (CRUD + status)
│   ├── customers.py        # Stranke
│   ├── vehicles.py         # Vozila
│   └── admin.py            # Upravljanje uporabnikov
├── templates/
│   ├── base.html           # Osnova z stransko vrstico
│   ├── login.html
│   ├── dashboard.html
│   ├── orders/             # Seznam, novo, detajl
│   ├── customers/          # Seznam, novo, detajl
│   ├── vehicles/           # Novo/uredi, detajl
│   └── admin/              # Uporabniki
└── static/css/style.css
```

## Modeli

- **User** – zaposleni (username, geslo, je admin)
- **Customer** – stranka (ime, tel, email, naslov)
- **Vehicle** – vozilo (VIN, znamka, model, letnik, motor…)
- **Order** – naročilo (NAR-YYYY-NNNN, status, vir)
- **OrderItem** – postavka naročila (naziv, Bartog ID, količina, status)
- **OrderStatusLog** – dnevnik sprememb statusa

## Statusi naročil

`Novo` → `Čaka na naročilo` → `Naročeno` → `V dostavi` → `Prejeto` → `Zaključeno`  
(ali kadarkoli `Preklicano`)

## Licenca

Interna raba. Vse pravice pridržane.
