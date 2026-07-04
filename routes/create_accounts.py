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
