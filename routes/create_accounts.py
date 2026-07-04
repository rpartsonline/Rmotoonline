# routes/create_accounts.py - IZBRIŠI po ustvaritvi računov!
from flask import Blueprint
from flask_login import login_required, current_user
from models import db, User, Customer

create_acc_bp = Blueprint('create_accounts', __name__, url_prefix='/admin')

@create_acc_bp.route('/ustvari-racune')
@login_required
def ustvari_racune():
    if not current_user.is_admin:
        return 'Samo admin.', 403
    ustvarjenih = 0
    preskocenih = 0
    napake = []
    customers = Customer.query.all()
    used_usernames = set(u.username for u in User.query.all())
    for c in customers:
        # Preskoči če že ima račun
        if User.query.filter_by(linked_customer_id=c.id).first():
            preskocenih += 1
            continue
        # Username = točno ime stranke, dodamo _2 _3 če je podvojeno
        username = c.name.strip()
        base = username
        i = 2
        while username in used_usernames:
            username = f'{base}_{i}'
            i += 1
        used_usernames.add(username)
        try:
            u = User(username=username, full_name=c.name,
                     is_admin=False, role='kupec',
                     linked_customer_id=c.id)
            u.set_password('bartog111')
            db.session.add(u)
            ustvarjenih += 1
        except Exception as e:
            napake.append(f'{c.name}: {e}')
    db.session.commit()
    err_html = '<br>'.join(napake[:5]) if napake else 'Ni napak'
    return (f'<h2>Računi ustvarjeni!</h2>'
            f'<p>✅ Ustvarjenih: <b>{ustvarjenih}</b></p>'
            f'<p>⏭ Preskočenih (že obstajajo): {preskocenih}</p>'
            f'<p>Napake: {err_html}</p>'
            f'<br><a href="/admin/users">Pojdi na Uporabniki</a>')
