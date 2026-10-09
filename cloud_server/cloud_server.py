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

# 👇 Updated Import to include Transaction
from models import db, User, PCMirror, Reservation, Transaction

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
        wallet_balance=0.0  # Initialize wallet to 0
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
    start = request.args.get('start')  # ISO
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
        Reservation.status == 'accepted',
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
    # Note: Your Reservation model uses user_email, not user_id. 
    # You might need to fetch the user's email first to filter correctly.
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

    # Check PC exists and is reservable
    pc = PCMirror.query.filter_by(center_id=center_id, pc_id=pc_id).first()
    if not pc:
        return jsonify({'error': 'PC not found'}), 404
    if pc.state == 'maintenance':
        return jsonify({'error': 'PC under maintenance'}), 409

    # Check overlap
    conflict = Reservation.query.filter(
        Reservation.pc_id == pc_id,
        Reservation.status == 'accepted',
        Reservation.start_time < end_dt,
        Reservation.end_time > start_dt,
    ).first()
    if conflict:
        return jsonify({'error': 'time slot already booked'}), 409

    r = Reservation(
        id=os.urandom(16).hex(), # Generate a UUID string
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


@app.route('/api/reservations/<int:rid>/cancel', methods=['POST'])
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

    r.status = 'cancelled'
    db.session.commit()
    return jsonify({'status': 'ok', 'reservation': r.to_dict()})


# ─────────────────────────────────────────────────────────────
# 👇 NEW: WALLET ENDPOINTS (Cloud-based, Player-facing)
# ─────────────────────────────────────────────────────────────

@app.route('/api/wallet', methods=['GET'])
@jwt_required()
def get_wallet():
    """Player views their own wallet balance"""
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
    """
    Player recharges their wallet from the cloud.
    In a real app, this would be called AFTER a successful payment gateway webhook.
    For the MVP, we simulate the payment success here.
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json() or {}
    
    amount = data.get('amount')
    
    if not amount or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({'error': 'Valid positive amount is required'}), 400

    # Update Balance
    user.wallet_balance += amount
    
    # Create Audit Log
    tx = Transaction(
        user_id=user.id,
        amount=amount,
        type='recharge',
        description=f'Cloud recharge of {amount} TND'
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
    """Player views their recharge/deduction history"""
    user_id = int(get_jwt_identity())
    txs = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.timestamp.desc()).all()
    return jsonify({
        'status': 'ok',
        'transactions': [tx.to_dict() for tx in txs]
    })

@app.route('/api/wallet/deduct', methods=['POST'])
@center_auth_required # 👈 Uses your existing center API key logic
def deduct_wallet():
    """
    Called by the Local Host PC when a gaming session ends.
    Payload: { "username": "player1", "amount": 5.0, "duration_minutes": 60 }
    """
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
        
    # Deduct
    user.wallet_balance -= amount
    
    # Log
    tx = Transaction(
        user_id=user.id,
        amount=amount,
        type='session_deduction',
        description=f'Gaming session ({duration} mins)'
    )
    
    db.session.add(tx)
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'new_balance': user.wallet_balance,
        'message': 'Session deducted successfully'
    })


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
    """Local server pulls reservations changed since `since` (ISO timestamp)."""
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
# Bootstrap
# ─────────────────────────────────────────────────────────────

def ensure_seed():
    """Create default admin / player accounts for testing."""
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
            wallet_balance=50.0 # Give the test player some starting money
        ))
    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_seed()
    app.run(host='0.0.0.0', port=5000, debug=True)