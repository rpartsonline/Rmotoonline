# routes/create_accounts.py - IZBRIŠI po ustvaritvi računov!
import unicodedata, re
from flask import Blueprint, request
from flask_login import login_required, current_user
from models import db, User, Customer

create_acc_bp = Blueprint('create_accounts', __name__, url_prefix='/admin')

@create_acc_bp.route('/ustvari-racune')
@login_required
def ustvari_racune():
    if not current_user.is_admin:
        return 'Samo admin.', 403

    # Batch procesiranje - po 50
    offset = int(request.args.get('offset', 0))
    batch = 50

    customers = Customer.query.order_by(Customer.id).offset(offset).limit(batch).all()
    total = Customer.query.count()

    if not customers:
        return f'<h2>✅ Vsi računi ustvarjeni!</h2><p>Skupaj strank: {total}</p><a href="/admin/users">Pojdi na Uporabniki</a>'

    used_usernames = set(u.username for u in User.query.all())
    ustvarjenih = 0
    preskocenih = 0

    for c in customers:
        if User.query.filter_by(linked_customer_id=c.id).first():
            preskocenih += 1
            continue
        username = c.name.strip()
        base = username
        i = 2
        while username in used_usernames:
            username = f'{base}_{i}'
            i += 1
        used_usernames.add(username)
        u = User(username=username, full_name=c.name,
                 is_admin=False, role='kupec',
                 linked_customer_id=c.id)
        u.set_password('bartog111')
        db.session.add(u)
        ustvarjenih += 1

    db.session.commit()

    next_offset = offset + batch
    progress = min(next_offset, total)

    return (f'<h2>Napredek: {progress}/{total}</h2>'
            f'<p>Ta skupek: ustvarjenih {ustvarjenih}, preskočenih {preskocenih}</p>'
            f'<meta http-equiv="refresh" content="2;url=/admin/ustvari-racune?offset={next_offset}">'
            f'<p>Samodejno nadaljuje čez 2 sekundi... ({next_offset}/{total})</p>'
            f'<a href="/admin/ustvari-racune?offset={next_offset}">Klikni če ne nadaljuje</a>')


# ── Enkratno orodje: poenostavi uporabniška imena kupcem ──────────────────────
# Prva beseda polnega imena (male črke, brez ločil/diakritike), ob podvojitvi -2, -3…
# Velja za vse role='kupec' RAZEN 'bartog'. Polno ime (full_name) ostane nespremenjeno.
# Po uporabi lahko to funkcijo izbrišeš.

def _prva_beseda_slug(full):
    s = (full or '').strip()
    if not s:
        return ''
    prva = s.split()[0]
    prva = ''.join(c for c in unicodedata.normalize('NFKD', prva) if not unicodedata.combining(c))
    prva = re.sub(r'[^A-Za-z0-9]', '', prva).lower()
    return prva


@create_acc_bp.route('/poenostavi-imena')
@login_required
def poenostavi_imena():
    if not current_user.is_admin:
        return 'Samo admin.', 403

    go = request.args.get('go')
    offset = int(request.args.get('offset', 0))
    batch = 50

    q = (User.query
         .filter(User.role == 'kupec', User.username != 'bartog')
         .order_by(User.id))
    total = q.count()

    # Uvodna stran s potrditvijo (prvi obisk)
    if not go:
        return (
            '<div style="font-family:sans-serif;max-width:640px;margin:40px auto;line-height:1.5">'
            '<h2>Poenostavitev uporabniških imen</h2>'
            f'<p>Poenostavil bom uporabniška imena za <b>{total}</b> računov kupcev '
            '(vsi razen zaposlenih in računa <code>bartog</code>).</p>'
            '<p>Novo ime = <b>prva beseda</b> polnega imena (male črke, brez ločil), '
            'ob podvojitvi <code>-2</code>, <code>-3</code>… Polno ime (ime in priimek) '
            '<b>ostane nespremenjeno</b>. Geslo se ne spremeni.</p>'
            '<p style="color:#b45309"><b>Nasvet:</b> pred zagonom je pametno narediti '
            'varnostno kopijo (Render disk snapshot je samodejen).</p>'
            '<p><a href="/admin/poenostavi-imena?go=1&offset=0" '
            'style="display:inline-block;background:#2563eb;color:#fff;padding:10px 18px;'
            'border-radius:8px;text-decoration:none;font-weight:700">Začni</a> &nbsp; '
            '<a href="/admin/users">Prekliči</a></p>'
            '</div>'
        )

    users = q.offset(offset).limit(batch).all()

    if not users:
        return (
            '<div style="font-family:sans-serif;max-width:640px;margin:40px auto">'
            f'<h2>✅ Končano!</h2><p>Pregledanih računov: {total}.</p>'
            '<a href="/admin/users">Na Uporabnike</a></div>'
        )

    used = set(u.username for u in User.query.all())
    spremembe = []
    for u in users:
        base = _prva_beseda_slug(u.full_name) or 'kupec'
        used.discard(u.username)          # sprosti staro ime (če ostane enako)
        candidate = base
        i = 2
        while candidate in used:
            candidate = f'{base}-{i}'
            i += 1
        if candidate != u.username:
            print(f"[POENOSTAVI] '{u.username}' -> '{candidate}' ({u.full_name})")
            spremembe.append((u.username, candidate, u.full_name))
            u.username = candidate
        used.add(candidate)

    db.session.commit()

    next_offset = offset + batch
    progress = min(next_offset, total)

    vrstice = ''.join(
        f'<tr><td style="color:#64748b">{s[2]}</td>'
        f'<td><code>{s[0]}</code></td><td>→</td>'
        f'<td><code style="color:#16a34a">{s[1]}</code></td></tr>'
        for s in spremembe
    ) or '<tr><td colspan="4" style="color:#64748b">V tem skupku ni bilo sprememb.</td></tr>'

    return (
        '<div style="font-family:sans-serif;max-width:820px;margin:24px auto">'
        f'<h2>Napredek: {progress}/{total}</h2>'
        '<table style="border-collapse:collapse;width:100%;font-size:14px">'
        '<tr style="text-align:left;color:#334155"><th>Ime</th><th>Staro</th><th></th><th>Novo</th></tr>'
        f'{vrstice}</table>'
        f'<meta http-equiv="refresh" content="2;url=/admin/poenostavi-imena?go=1&offset={next_offset}">'
        f'<p style="color:#64748b">Samodejno nadaljuje čez 2 sekundi… ({progress}/{total})</p>'
        f'<a href="/admin/poenostavi-imena?go=1&offset={next_offset}">Klikni, če ne nadaljuje</a>'
        '</div>'
    )
