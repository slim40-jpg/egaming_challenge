import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

from models import db, User, PCMirror, Reservation, Transaction, Plan, Subscription

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Content-Type", "Authorization", "ngrok-skip-browser-warning"
        ],
        "supports_credentials": True,
        "max_age": 3600,
    }
})

db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

CENTER_API_KEY = os.getenv('CENTER_API_KEY')


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'error': 'admin required'}), 403
        return fn(*args, **kwargs)
    return wrapper


def center_auth_required(fn):
    """Auth for local→cloud sync endpoints (shared API key, not user JWT)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if auth != f'Bearer {CENTER_API_KEY}':
            return jsonify({'error': 'invalid center key'}), 401
        return fn(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'service': 'cloud'})


# ─────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    email = (data.get('email') or '').strip() or None
    role = data.get('role', 'player')

    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'username already exists'}), 409

    user = User(
        username=username,
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode(),
        role=role,
        wallet_balance=0.0
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={'username': user.username, 'role': user.role},
    )
    return jsonify({'status': 'ok', 'access_token': token, 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({'error': 'invalid credentials'}), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={'username': user.username, 'role': user.role},
    )
    return jsonify({'status': 'ok', 'access_token': token, 'user': user.to_dict()})


# ─────────────────────────────────────────────────────────────
# Public PC listing (used by player dashboard)
# ─────────────────────────────────────────────────────────────

@app.route('/api/pcs', methods=['GET'])
def list_pcs():
    center_id = request.args.get('center_id', 'main')
    pcs = PCMirror.query.filter_by(center_id=center_id).all()
    return jsonify({'status': 'ok', 'pcs': [p.to_dict() for p in pcs]})


@app.route('/api/pcs/availability', methods=['GET'])
def availability():
    """Check if a given PC is free at a given time."""
    pc_id = request.args.get('pc_id')
    start = request.args.get('start')
    end = request.args.get('end')

    if not pc_id or not start or not end:
        return jsonify({'error': 'pc_id, start, end required'}), 400

    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return jsonify({'error': 'invalid datetime format'}), 400

    conflict = Reservation.query.filter(
        Reservation.pc_id == pc_id,
        Reservation.status.in_(['accepted', 'paid']),
        Reservation.start_time < end_dt,
        Reservation.end_time > start_dt,
    ).first()

    return jsonify({'status': 'ok', 'available': conflict is None})


# ─────────────────────────────────────────────────────────────
# Reservations (players)
# ─────────────────────────────────────────────────────────────

@app.route('/api/reservations/my', methods=['GET'])
@jwt_required()
def my_reservations():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    rows = Reservation.query.filter_by(user_email=user.email).order_by(
        Reservation.start_time.desc()
    ).all()
    return jsonify({'status': 'ok', 'reservations': [r.to_dict() for r in rows]})


@app.route('/api/reservations/create', methods=['POST'])
@jwt_required()
def create_reservation():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    pc_id = data.get('pc_id')
    start = data.get('start_time')
    end = data.get('end_time')
    center_id = data.get('center_id', 'main')

    if not pc_id or not start or not end:
        return jsonify({'error': 'pc_id, start_time, end_time required'}), 400

    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00')).replace(tzinfo=None)
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        return jsonify({'error': 'invalid datetime format'}), 400

    if end_dt <= start_dt:
        return jsonify({'error': 'end must be after start'}), 400

    pc = PCMirror.query.filter_by(center_id=center_id, pc_id=pc_id).first()
    if not pc:
        return jsonify({'error': 'PC not found'}), 404
    if pc.state == 'maintenance':
        return jsonify({'error': 'PC under maintenance'}), 409

    conflict = Reservation.query.filter(
        Reservation.pc_id == pc_id,
        Reservation.status.in_(['accepted', 'paid']),
        Reservation.start_time < end_dt,
        Reservation.end_time > start_dt,
    ).first()
    if conflict:
        return jsonify({'error': 'time slot already booked'}), 409

    r = Reservation(
        id=os.urandom(16).hex(),
        user_name=user.username,
        user_email=user.email,
        center_id=center_id,
        pc_id=pc_id,
        start_time=start_dt,
        end_time=end_dt,
        status='accepted',
    )
    db.session.add(r)
    db.session.commit()

    return jsonify({'status': 'ok', 'reservation': r.to_dict()}), 201


@app.route('/api/reservations/book-and-pay', methods=['POST'])
@jwt_required()
def book_and_pay_reservation():
    """
    Book a PC AND pay for it from the user's wallet in one atomic operation.
    Applies the user's active subscription discount if any.
    Returns 402 if the wallet has insufficient funds.
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    data = request.get_json() or {}
    pc_id = data.get('pc_id')
    start = data.get('start_time')
    end = data.get('end_time')
    center_id = data.get('center_id', 'main')

    if not pc_id or not start or not end:
        return jsonify({'error': 'pc_id, start_time, and end_time are required'}), 400

    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00')).replace(tzinfo=None)
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00')).replace(tzinfo=None)
    except Exception:
        return jsonify({'error': 'Invalid datetime format'}), 400

    if end_dt <= start_dt:
        return jsonify({'error': 'end_time must be after start_time'}), 400

    duration_minutes = (end_dt - start_dt).total_seconds() / 60.0
    if duration_minutes < 30:
        return jsonify({'error': 'Minimum booking duration is 30 minutes'}), 400

    pc = PCMirror.query.filter_by(center_id=center_id, pc_id=pc_id).first()
    if not pc:
        return jsonify({'error': 'PC not found'}), 404
    if pc.state == 'maintenance':
        return jsonify({'error': 'PC is under maintenance'}), 400

    conflict = Reservation.query.filter(
        Reservation.pc_id == pc_id,
        Reservation.status.in_(['accepted', 'paid']),
        Reservation.start_time < end_dt,
        Reservation.end_time > start_dt,
    ).first()
    if conflict:
        return jsonify({'error': 'PC is not available in that time slot'}), 409

    base_price_per_minute = 0.10
    base_cost = duration_minutes * base_price_per_minute

    sub = Subscription.query.filter_by(user_id=user_id, is_active=True).first()
    discount_percent = 0
    plan_name = 'Free / Guest'
    if sub and sub.expires_at and sub.expires_at >= datetime.utcnow():
        plan_name = sub.plan.name if sub.plan else 'Free / Guest'
        discount_percent = sub.plan.discount_percent if sub.plan else 0

    final_cost = round(base_cost * (1 - discount_percent / 100.0), 2)

    if user.wallet_balance < final_cost:
        return jsonify({
            'error': 'Insufficient funds',
            'required': final_cost,
            'balance': user.wallet_balance,
            'missing': round(final_cost - user.wallet_balance, 2),
        }), 402

    user.wallet_balance = round(user.wallet_balance - final_cost, 2)

    r = Reservation(
        id=os.urandom(16).hex(),
        user_name=user.username,
        user_email=user.email,
        center_id=center_id,
        pc_id=pc_id,
        start_time=start_dt,
        end_time=end_dt,
        status='paid',
    )
    db.session.add(r)

    tx = Transaction(
        user_id=user.id,
        amount=-final_cost,
        type='session_reservation',
        description=f'Booking {pc_id} · {duration_minutes:.0f}min · {plan_name}'
                    + (f' (-{discount_percent}%)' if discount_percent else ''),
        balance_after=user.wallet_balance,
    )
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'reservation': r.to_dict(),
        'payment': {
            'base_cost': round(base_cost, 2),
            'discount_percent': discount_percent,
            'final_cost': final_cost,
            'new_balance': user.wallet_balance,
        },
        'transaction': tx.to_dict(),
    }), 201


@app.route('/api/reservations/<rid>/cancel', methods=['POST'])
@jwt_required()
def cancel_reservation(rid):
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    r = Reservation.query.get(rid)
    if not r:
        return jsonify({'error': 'reservation not found'}), 404

    user = User.query.get(user_id)
    if r.user_email != user.email and claims.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    if r.status not in ('accepted', 'paid'):
        return jsonify({'error': f'cannot cancel reservation with status {r.status}'}), 400

    was_paid = (r.status == 'paid')
    r.status = 'cancelled'

    refund_info = None
    if was_paid:
        duration_minutes = (r.end_time - r.start_time).total_seconds() / 60.0
        base_cost = duration_minutes * 0.10

        sub = Subscription.query.filter_by(user_id=user.id, is_active=True).first()
        discount_percent = 0
        if sub and sub.expires_at and sub.expires_at >= datetime.utcnow():
            discount_percent = sub.plan.discount_percent if sub.plan else 0

        refund_amount = round(base_cost * (1 - discount_percent / 100.0), 2)

        now = datetime.utcnow()
        hours_until_start = (r.start_time - now).total_seconds() / 3600.0

        if hours_until_start >= 1.0:
            user.wallet_balance = round(user.wallet_balance + refund_amount, 2)
            tx = Transaction(
                user_id=user.id,
                amount=refund_amount,
                type='refund',
                description=f'Refund for cancelled booking {r.pc_id}',
                balance_after=user.wallet_balance,
            )
            db.session.add(tx)
            refund_info = {
                'refunded': True,
                'amount': refund_amount,
                'new_balance': user.wallet_balance,
                'reason': 'Cancelled more than 1 hour before start',
            }
        else:
            refund_info = {
                'refunded': False,
                'reason': 'Cancelled less than 1 hour before start — no refund',
            }

    db.session.commit()

    return jsonify({
        'status': 'ok',
        'reservation': r.to_dict(),
        'refund': refund_info,
    })


# ─────────────────────────────────────────────────────────────
# WALLET ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.route('/api/wallet', methods=['GET'])
@jwt_required()
def get_wallet():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    return jsonify({
        'status': 'ok',
        'wallet': {
            'balance': user.wallet_balance,
            'currency': 'TND'
        }
    })


@app.route('/api/wallet/recharge', methods=['POST'])
@jwt_required()
def recharge_wallet():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json() or {}

    amount = data.get('amount')

    if not amount or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({'error': 'Valid positive amount is required'}), 400

    user.wallet_balance += amount

    tx = Transaction(
        user_id=user.id,
        amount=amount,
        type='recharge',
        description=f'Cloud recharge of {amount} TND',
        balance_after=user.wallet_balance
    )

    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'message': 'Wallet recharged successfully',
        'new_balance': user.wallet_balance,
        'transaction': tx.to_dict()
    }), 200


@app.route('/api/wallet/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id = int(get_jwt_identity())
    tx_type = request.args.get('type')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    per_page = min(per_page, 100)

    q = Transaction.query.filter_by(user_id=user_id)
    if tx_type:
        q = q.filter_by(type=tx_type)
    q = q.order_by(Transaction.timestamp.desc())

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'status': 'ok',
        'transactions': [tx.to_dict() for tx in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@app.route('/api/wallet/deduct', methods=['POST'])
@center_auth_required
def deduct_wallet():
    data = request.get_json() or {}
    username = data.get('username')
    amount = data.get('amount')
    duration = data.get('duration_minutes', 0)

    if not username or not amount:
        return jsonify({'error': 'username and amount required'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Player not found in cloud'}), 404

    if user.wallet_balance < amount:
        return jsonify({'error': 'Insufficient funds', 'balance': user.wallet_balance}), 402

    user.wallet_balance -= amount

    tx = Transaction(
        user_id=user.id,
        amount=amount,
        type='session_deduction',
        description=f'Gaming session ({duration} mins)',
        balance_after=user.wallet_balance
    )

    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'new_balance': user.wallet_balance,
        'message': 'Session deducted successfully'
    })


@app.route('/api/admin/wallet/adjust', methods=['POST'])
@jwt_required()
def admin_adjust_wallet():
    """Admin manually adjusts a user's wallet balance (positive or negative)."""
    admin_id = int(get_jwt_identity())
    admin = User.query.get(admin_id)
    if not admin or admin.role != 'admin':
        return jsonify({'error': 'admin only'}), 403

    data = request.get_json() or {}
    username = data.get('username')
    amount = data.get('amount')
    reason = data.get('reason')

    if not username or amount is None or not reason:
        return jsonify({'error': 'username, amount, and reason are required'}), 400
    if not isinstance(amount, (int, float)) or amount == 0:
        return jsonify({'error': 'amount must be a non-zero number'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'user not found'}), 404

    new_balance = user.wallet_balance + amount
    if new_balance < 0:
        return jsonify({'error': 'adjustment would make balance negative'}), 400

    user.wallet_balance = new_balance
    tx = Transaction(
        user_id=user.id,
        amount=amount,
        type='admin_adjustment',
        description=f'Admin adjustment: {reason}',
        balance_after=new_balance,
        created_by=admin.username
    )
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'new_balance': new_balance,
        'transaction': tx.to_dict()
    })


# ─────────────────────────────────────────────────────────────
# PLANS & SUBSCRIPTIONS
# ─────────────────────────────────────────────────────────────

@app.route('/api/plans', methods=['GET'])
def list_plans():
    """Public — list all active plans."""
    plans = Plan.query.filter_by(is_active=True).order_by(Plan.price_per_month).all()
    return jsonify({
        'status': 'ok',
        'plans': [p.to_dict() for p in plans]
    })


@app.route('/api/subscription/me', methods=['GET'])
@jwt_required()
def my_subscription():
    """Player views their current active subscription."""
    user_id = int(get_jwt_identity())
    sub = Subscription.query.filter_by(
        user_id=user_id, is_active=True
    ).order_by(Subscription.expires_at.desc()).first()

    if not sub:
        return jsonify({'status': 'ok', 'subscription': None})

    if sub.expires_at < datetime.utcnow():
        sub.is_active = False
        db.session.commit()
        return jsonify({'status': 'ok', 'subscription': None})

    return jsonify({'status': 'ok', 'subscription': sub.to_dict()})


@app.route('/api/subscription/subscribe', methods=['POST'])
@jwt_required()
def subscribe():
    """Player subscribes to a plan. Deducts from wallet."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    data = request.get_json() or {}
    plan_id = data.get('plan_id')
    if not plan_id:
        return jsonify({'error': 'plan_id required'}), 400

    plan = Plan.query.get(plan_id)
    if not plan or not plan.is_active:
        return jsonify({'error': 'plan not found or inactive'}), 404

    if user.wallet_balance < plan.price_per_month:
        return jsonify({
            'error': 'Insufficient balance',
            'required': plan.price_per_month,
            'available': user.wallet_balance
        }), 402

    Subscription.query.filter_by(user_id=user_id, is_active=True).update({'is_active': False})

    now = datetime.utcnow()
    sub = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        started_at=now,
        expires_at=now + timedelta(days=30),
        hours_remaining=plan.included_hours,
        is_active=True,
    )
    db.session.add(sub)

    user.wallet_balance -= plan.price_per_month

    tx = Transaction(
        user_id=user_id,
        amount=-plan.price_per_month,
        type='subscription',
        description=f'Subscription: {plan.name} plan ({plan.included_hours}h included)',
        balance_after=user.wallet_balance
    )
    db.session.add(tx)

    db.session.commit()

    return jsonify({
        'status': 'ok',
        'subscription': sub.to_dict(),
        'new_balance': user.wallet_balance
    })


@app.route('/api/subscription/consume', methods=['POST'])
@jwt_required()
def consume_subscription():
    """
    Called when a session ends.
    Deducts plan hours first, then charges wallet with the plan's discount.
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    data = request.get_json() or {}
    duration_minutes = float(data.get('duration_minutes', 0))
    base_price_per_minute = float(data.get('price_per_minute', 0.10))

    if duration_minutes <= 0:
        return jsonify({'error': 'duration_minutes must be > 0'}), 400

    sub = Subscription.query.filter_by(
        user_id=user_id, is_active=True
    ).order_by(Subscription.expires_at.desc()).first()

    if sub and sub.expires_at < datetime.utcnow():
        sub.is_active = False
        db.session.commit()
        sub = None

    plan_name = 'Free / Guest'
    discount_percent = 0
    hours_from_plan = 0.0
    hours_from_wallet = duration_minutes / 60.0

    if sub and sub.plan:
        plan_name = sub.plan.name
        discount_percent = sub.plan.discount_percent

        available_hours = sub.hours_remaining or 0.0
        hours_needed = duration_minutes / 60.0
        hours_from_plan = min(available_hours, hours_needed)
        hours_from_wallet = hours_needed - hours_from_plan

        sub.hours_remaining = available_hours - hours_from_plan
        db.session.commit()

    base_cost = hours_from_wallet * 60 * base_price_per_minute
    discounted_cost = base_cost * (1 - discount_percent / 100.0)

    if discounted_cost > 0:
        user.wallet_balance -= discounted_cost
        tx = Transaction(
            user_id=user_id,
            amount=-discounted_cost,
            type='session_deduction',
            description=f'Session ({duration_minutes:.0f}min) — {plan_name}'
                        + (f' -{discount_percent}%' if discount_percent else ''),
            balance_after=user.wallet_balance
        )
        db.session.add(tx)

    db.session.commit()

    return jsonify({
        'status': 'ok',
        'plan_name': plan_name,
        'hours_from_plan': round(hours_from_plan, 2),
        'hours_from_wallet': round(hours_from_wallet, 2),
        'discount_percent': discount_percent,
        'cost': round(discounted_cost, 2),
        'new_balance': user.wallet_balance,
        'hours_remaining': sub.hours_remaining if sub else 0.0,
    })


# ─────────────────────────────────────────────────────────────
# Admin: Manage Plans
# ─────────────────────────────────────────────────────────────

@app.route('/api/admin/plans', methods=['GET'])
@admin_required
def admin_list_plans():
    plans = Plan.query.order_by(Plan.price_per_month).all()
    return jsonify({'status': 'ok', 'plans': [p.to_dict() for p in plans]})


@app.route('/api/admin/plans', methods=['POST'])
@admin_required
def admin_create_plan():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400

    if Plan.query.filter_by(name=name).first():
        return jsonify({'error': 'plan name already exists'}), 409

    plan = Plan(
        name=name,
        price_per_month=float(data.get('price_per_month', 0)),
        included_hours=float(data.get('included_hours', 0)),
        discount_percent=int(data.get('discount_percent', 0)),
        color=data.get('color', 'gray'),
        description=data.get('description', ''),
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify({'status': 'ok', 'plan': plan.to_dict()}), 201


@app.route('/api/admin/plans/<int:plan_id>', methods=['PUT'])
@admin_required
def admin_update_plan(plan_id):
    plan = Plan.query.get(plan_id)
    if not plan:
        return jsonify({'error': 'plan not found'}), 404

    data = request.get_json() or {}
    if 'name' in data: plan.name = data['name']
    if 'price_per_month' in data: plan.price_per_month = float(data['price_per_month'])
    if 'included_hours' in data: plan.included_hours = float(data['included_hours'])
    if 'discount_percent' in data: plan.discount_percent = int(data['discount_percent'])
    if 'color' in data: plan.color = data['color']
    if 'description' in data: plan.description = data['description']
    if 'is_active' in data: plan.is_active = bool(data['is_active'])

    db.session.commit()
    return jsonify({'status': 'ok', 'plan': plan.to_dict()})


@app.route('/api/admin/plans/<int:plan_id>', methods=['DELETE'])
@admin_required
def admin_delete_plan(plan_id):
    plan = Plan.query.get(plan_id)
    if not plan:
        return jsonify({'error': 'plan not found'}), 404

    plan.is_active = False
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/admin/subscriptions', methods=['GET'])
@admin_required
def admin_list_subscriptions():
    subs = Subscription.query.order_by(Subscription.started_at.desc()).all()
    return jsonify({'status': 'ok', 'subscriptions': [s.to_dict() for s in subs]})


# ─────────────────────────────────────────────────────────────
# Sync endpoints (local → cloud)
# ─────────────────────────────────────────────────────────────

@app.route('/api/sync/center/<center_id>', methods=['POST'])
@center_auth_required
def sync_center(center_id):
    data = request.get_json() or {}
    pcs = data.get('pcs') or []
    updated = 0

    for entry in pcs:
        pc_id = entry.get('pc_id')
        if not pc_id:
            continue

        raw_games = entry.get('installed_games') or []
        game_names = []
        for g in raw_games:
            if isinstance(g, str):
                game_names.append(g)
            elif isinstance(g, dict) and g.get('name'):
                game_names.append(g['name'])

        row = PCMirror.query.filter_by(center_id=center_id, pc_id=pc_id).first()
        if not row:
            row = PCMirror(center_id=center_id, pc_id=pc_id)
            db.session.add(row)

        row.name = entry.get('name') or row.name or 'PC'
        row.online = bool(entry.get('online'))
        row.state = entry.get('state') or 'offline'
        row.installed_games = game_names
        row.last_sync = datetime.utcnow()
        updated += 1

    db.session.commit()
    return jsonify({'status': 'ok', 'updated': updated, 'center_id': center_id})


@app.route('/api/sync/center/<center_id>/reservations', methods=['GET'])
@center_auth_required
def sync_reservations(center_id):
    since_str = request.args.get('since')
    q = Reservation.query.filter_by(center_id=center_id)
    if since_str:
        try:
            since_dt = datetime.fromisoformat(since_str.replace('Z', '+00:00')).replace(tzinfo=None)
            q = q.filter(Reservation.created_at >= since_dt)
        except ValueError:
            return jsonify({'error': 'invalid since format'}), 400

    rows = q.order_by(Reservation.created_at.asc()).all()
    return jsonify({
        'status': 'ok',
        'server_time': datetime.utcnow().isoformat(),
        'reservations': [r.to_dict() for r in rows],
    })


# ─────────────────────────────────────────────────────────────
# Admin: Users Management
# ─────────────────────────────────────────────────────────────

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_list_users():
    """Admin fetches all users with wallet balances AND active plan."""
    users = User.query.order_by(User.created_at.desc()).all()
    result = []

    for u in users:
        user_dict = u.to_dict()

        sub = Subscription.query.filter_by(
            user_id=u.id, is_active=True
        ).order_by(Subscription.expires_at.desc()).first()

        if sub and sub.expires_at >= datetime.utcnow():
            user_dict['plan_name'] = sub.plan.name if sub.plan else 'Free / Guest'
            user_dict['plan_color'] = sub.plan.color if sub.plan else 'gray'
            user_dict['hours_remaining'] = sub.hours_remaining or 0
        else:
            user_dict['plan_name'] = 'Free / Guest'
            user_dict['plan_color'] = 'gray'
            user_dict['hours_remaining'] = 0

        result.append(user_dict)

    return jsonify({'status': 'ok', 'users': result})


@app.route('/api/admin/users/<int:user_id>', methods=['GET'])
@admin_required
def admin_get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    txs = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.timestamp.desc()).all()

    sub = Subscription.query.filter_by(
        user_id=user_id, is_active=True
    ).order_by(Subscription.expires_at.desc()).first()

    return jsonify({
        'status': 'ok',
        'user': user.to_dict(),
        'transactions': [tx.to_dict() for tx in txs],
        'subscription': sub.to_dict() if sub else None,
    })


@app.route('/api/admin/users/<int:user_id>/topup', methods=['POST'])
@admin_required
def admin_topup_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    amount = data.get('amount')

    if not amount or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({'error': 'Valid positive amount is required'}), 400

    user.wallet_balance += amount
    tx = Transaction(
        user_id=user.id,
        amount=amount,
        type='recharge',
        description=f'Manual cash top-up by admin',
        balance_after=user.wallet_balance,
        created_by='admin'
    )
    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'status': 'ok',
        'message': 'Wallet topped up',
        'new_balance': user.wallet_balance
    })


# ─────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────

def ensure_seed():
    """Create default accounts + default plans (TND)."""
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(
            username='admin',
            password_hash=bcrypt.generate_password_hash('admin123').decode(),
            role='admin',
            wallet_balance=0.0
        ))
    if not User.query.filter_by(username='player1').first():
        db.session.add(User(
            username='player1',
            password_hash=bcrypt.generate_password_hash('player123').decode(),
            role='player',
            wallet_balance=50.0
        ))

    if not Plan.query.filter_by(name='Free / Guest').first():
        db.session.add_all([
            Plan(
                name='Free / Guest',
                price_per_month=0.0,
                included_hours=0.0,
                discount_percent=0,
                color='gray',
                description='Payez à la session — pas d\'abonnement'
            ),
            Plan(
                name='Basic',
                price_per_month=50.0,
                included_hours=5.0,
                discount_percent=10,
                color='silver',
                description='5h incluses + 10% de réduction membre'
            ),
            Plan(
                name='Premium',
                price_per_month=100.0,
                included_hours=15.0,
                discount_percent=20,
                color='gold',
                description='15h incluses + 20% de réduction + réservation prioritaire'
            ),
            Plan(
                name='Pro Gamer',
                price_per_month=200.0,
                included_hours=40.0,
                discount_percent=30,
                color='platinum',
                description='40h incluses + 30% de réduction + accès tournois + VIP'
            ),
        ])

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_seed()
    app.run(host='0.0.0.0', port=5000, debug=True)