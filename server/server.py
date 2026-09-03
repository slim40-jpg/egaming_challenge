# server.py - Local Gaming Center Server
# This runs on the local server in the gaming center

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import socket
import threading
import time
import os
import netifaces
import uuid
import requests
from functools import wraps

# ============================================================
# APP INITIALIZATION
# ============================================================

app = Flask(__name__, static_folder='../frontend')
CORS(app)

# ============================================================
# CLOUD SYNC CONFIGURATION
# ============================================================

CLOUD_API_URL = os.environ.get('CLOUD_API_URL', 'https://your-cloud-app.railway.app')  # Your cloud service URL
CENTER_ID = os.environ.get('CENTER_ID', 'main')
SYNC_INTERVAL = int(os.environ.get('SYNC_INTERVAL', '10'))  # seconds

# ============================================================
# CONFIGURATION
# ============================================================

SERVER_PORT = 8003
DISCOVERY_PORT = 9000

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/gaming_house')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# ============================================================
# MODELS
# ============================================================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='player')
    
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    sessions = db.relationship('Session', backref='user_ref', lazy=True)
    transactions = db.relationship('Transaction', backref='user_ref', lazy=True)
    reservations = db.relationship('Reservation', backref='user_ref', lazy=True)
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'full_name': self.full_name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

class PC(db.Model):
    __tablename__ = 'pcs'
    
    id = db.Column(db.String(36), primary_key=True)
    hostname = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    status = db.Column(db.String(20), default='offline')
    
    cpu_model = db.Column(db.String(100))
    gpu_model = db.Column(db.String(100))
    ram_size = db.Column(db.String(50))
    
    cpu_usage = db.Column(db.Float, default=0)
    gpu_usage = db.Column(db.Float, default=0)
    ram_usage = db.Column(db.Float, default=0)
    cpu_temp = db.Column(db.Float, default=0)
    gpu_temp = db.Column(db.Float, default=0)
    
    current_game = db.Column(db.String(100), default='none')
    window_title = db.Column(db.String(200))
    is_fullscreen = db.Column(db.Boolean, default=False)
    
    last_heartbeat = db.Column(db.DateTime)
    last_telemetry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    installed_games = db.Column(db.JSON, default=[])
    
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'status': self.status,
            'online': self.status == 'online',
            'cpu': self.cpu_usage,
            'ram': self.ram_usage,
            'gpu': self.gpu_usage,
            'cpu_temp': self.cpu_temp,
            'gpu_temp': self.gpu_temp,
            'game': self.current_game,
            'window_title': self.window_title,
            'is_fullscreen': self.is_fullscreen,
            'hardware': {
                'cpu': self.cpu_model,
                'gpu': self.gpu_model,
                'ram': self.ram_size
            },
            'installed_games': self.installed_games or []
        }

class Session(db.Model):
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pc_id = db.Column(db.String(36), db.ForeignKey('pcs.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Float, default=0)
    cost = db.Column(db.Float, default=0)
    price_per_minute = db.Column(db.Float, default=0.10)
    
    game = db.Column(db.String(100))
    session_type = db.Column(db.String(20), default='time')
    status = db.Column(db.String(20), default='active')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'pc_id': self.pc_id,
            'user_id': self.user_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': self.duration_minutes,
            'cost': self.cost,
            'price_per_minute': self.price_per_minute,
            'game': self.game,
            'session_type': self.session_type,
            'status': self.status
        }

class Wallet(db.Model):
    __tablename__ = 'wallets'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='wallet_ref')
    transactions = db.relationship('Transaction', backref='wallet_ref', lazy=True)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'balance': self.balance,
            'currency': 'TND'
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = db.Column(db.String(36), db.ForeignKey('wallets.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    new_balance = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'amount': self.amount,
            'new_balance': self.new_balance,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Membership(db.Model):
    __tablename__ = 'memberships'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), unique=True, nullable=False)
    
    plan = db.Column(db.String(20), nullable=False)
    plan_name = db.Column(db.String(50))
    hours_total = db.Column(db.Float, nullable=False)
    hours_used = db.Column(db.Float, default=0)
    hours_left = db.Column(db.Float, nullable=False)
    
    purchase_date = db.Column(db.DateTime, nullable=False)
    expiry_date = db.Column(db.DateTime)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'plan': self.plan,
            'plan_name': self.plan_name,
            'hours_total': self.hours_total,
            'hours_used': self.hours_used,
            'hours_left': self.hours_left,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_active': self.is_active
        }

class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.String(36), primary_key=True)
    pc_id = db.Column(db.String(36), db.ForeignKey('pcs.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')
    
    user_name = db.Column(db.String(100))
    user_email = db.Column(db.String(100))
    user_phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    
    # Cloud sync fields
    source = db.Column(db.String(20), default='local')
    cloud_id = db.Column(db.String(36))
    synced = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'pc_id': self.pc_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_email': self.user_email,
            'user_phone': self.user_phone,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'source': self.source,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Branch(db.Model):
    __tablename__ = 'branches'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'phone': self.phone
        }

# ============================================================
# AUTH DECORATORS
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'status': 'error', 'message': 'Missing authorization token'}), 401
        
        try:
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            from flask_jwt_extended import decode_token
            decoded = decode_token(token)
            request.user_id = decoded.get('sub')
            request.user_role = decoded.get('role')
        except Exception as e:
            return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 401
        
        return f(*args, **kwargs)
    return decorated

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            user = User.query.get(request.user_id)
            if not user:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
            
            if user.role not in allowed_roles:
                return jsonify({
                    'status': 'error', 
                    'message': f'Insufficient permissions. Required role: {", ".join(allowed_roles)}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

# ============================================================
# LOCAL IP DETECTION
# ============================================================

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.') and not ip.startswith('169.254'):
            return ip
    except:
        pass
    
    try:
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)[2]
        for ip in ips:
            if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                if not ip.startswith('169.254'):
                    return ip
        for ip in ips:
            if not ip.startswith('127.') and not ip.startswith('169.254'):
                return ip
    except:
        pass
    
    try:
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if not ip.startswith('127.') and not ip.startswith('169.254'):
                        if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                            return ip
                        if ip != '127.0.0.1':
                            return ip
    except:
        pass
    
    return "127.0.0.1"

SERVER_IP = get_local_ip()
print(f"[SERVER] Detected IP Address: {SERVER_IP}")
print(f"[SERVER] Server URL: http://{SERVER_IP}:{SERVER_PORT}")

# ============================================================
# DISCOVERY BROADCAST
# ============================================================

def start_discovery_broadcast():
    discovery_message = f"SERVER:{SERVER_IP}:{SERVER_PORT}".encode('utf-8')
    
    print(f"[DISCOVERY] Broadcasting server presence on port {DISCOVERY_PORT}")
    print(f"[DISCOVERY] Server IP: {SERVER_IP}:{SERVER_PORT}")
    
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(1)
            sock.sendto(discovery_message, ('255.255.255.255', DISCOVERY_PORT))
            
            ip_parts = SERVER_IP.split('.')
            if len(ip_parts) == 4:
                subnets = [
                    f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255",
                    f"{ip_parts[0]}.{ip_parts[1]}.255.255",
                ]
                for subnet in subnets:
                    try:
                        sock.sendto(discovery_message, (subnet, DISCOVERY_PORT))
                    except:
                        pass
            sock.close()
        except Exception as e:
            print(f"[DISCOVERY] Error: {e}")
        time.sleep(2)

# ============================================================
# STORE DATA (Cache)
# ============================================================

pcs_cache = {}
pending_commands = {}
sessions_cache = {}
session_history = []
usb_alerts = []

# ============================================================
# GAME CATALOG
# ============================================================

GAME_CATALOG = [
    {'id': 1, 'name': 'Counter-Strike 2', 'category': 'FPS', 'icon': '🎯', 'executable': 'cs2.exe'},
    {'id': 2, 'name': 'EA FC 24', 'category': 'Sports', 'icon': '⚽', 'executable': 'fifa24.exe'},
    {'id': 3, 'name': 'Valorant', 'category': 'FPS', 'icon': '🔫', 'executable': 'valorant.exe'},
    {'id': 4, 'name': 'League of Legends', 'category': 'MOBA', 'icon': '🏆', 'executable': 'League of Legends.exe'},
    {'id': 5, 'name': 'Fortnite', 'category': 'Battle Royale', 'icon': '🎮', 'executable': 'fortnite.exe'},
    {'id': 6, 'name': 'Dota 2', 'category': 'MOBA', 'icon': '⚔️', 'executable': 'dota2.exe'},
    {'id': 7, 'name': 'Rocket League', 'category': 'Sports', 'icon': '🚗', 'executable': 'rocketleague.exe'},
    {'id': 8, 'name': 'MUGEN', 'category': 'Fighting', 'icon': '👊', 'executable': 'mugen.exe'},
    {'id': 9, 'name': 'Naruto Storm Revolution', 'category': 'Fighting', 'icon': '🐉', 'executable': 'NSUNSR.exe'},
    {'id': 10, 'name': 'Grand Theft Auto V', 'category': 'Action', 'icon': '🚗', 'executable': 'gta5.exe'},
]

MEMBERSHIP_PLANS = {
    'basic': {'name': 'Basic', 'price': 10, 'hours': 5, 'color': '#43b581'},
    'premium': {'name': 'Premium', 'price': 25, 'hours': 15, 'color': '#faa61a'},
    'pro': {'name': 'Pro', 'price': 50, 'hours': 40, 'color': '#f04747'}
}

# ============================================================
# CLOUD SYNC FUNCTIONS
# ============================================================

def sync_reservations_from_cloud():
    """Sync reservations from cloud to local database"""
    if not CLOUD_API_URL:
        return
    
    try:
        print(f"[SYNC] Checking cloud for new reservations...")
        response = requests.get(
            f"{CLOUD_API_URL}/api/sync/center/{CENTER_ID}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            cloud_reservations = data.get('reservations', [])
            
            if cloud_reservations:
                print(f"[SYNC] Found {len(cloud_reservations)} new cloud reservations")
            
            for cr in cloud_reservations:
                # Check if reservation already exists locally
                existing = Reservation.query.filter_by(cloud_id=cr['id']).first()
                if not existing:
                    # Create local reservation
                    reservation = Reservation(
                        id=str(uuid.uuid4()),
                        pc_id=cr['pc_id'],
                        user_name=cr['user_name'],
                        user_email=cr.get('user_email', ''),
                        user_phone=cr.get('user_phone', ''),
                        start_time=datetime.fromisoformat(cr['start_time']),
                        end_time=datetime.fromisoformat(cr['end_time']),
                        status=cr['status'],
                        source='cloud',
                        cloud_id=cr['id'],
                        synced=True
                    )
                    db.session.add(reservation)
                    print(f"[SYNC] ✅ New cloud reservation: {cr['id']} - {cr['user_name']}")
            
            db.session.commit()
            
            # Confirm sync to cloud
            if cloud_reservations:
                reservation_ids = [r['id'] for r in cloud_reservations]
                try:
                    requests.post(
                        f"{CLOUD_API_URL}/api/sync/confirm",
                        json={'reservation_ids': reservation_ids},
                        timeout=5
                    )
                    print(f"[SYNC] ✅ Confirmed {len(reservation_ids)} reservations")
                except Exception as e:
                    print(f"[SYNC] ⚠️ Could not confirm sync: {e}")
        else:
            print(f"[SYNC] ❌ Cloud returned status: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print(f"[SYNC] ❌ Could not connect to cloud: {CLOUD_API_URL}")
    except Exception as e:
        print(f"[SYNC] ❌ Error: {e}")

def start_sync_thread():
    """Start background sync thread"""
    def sync_loop():
        while True:
            sync_reservations_from_cloud()
            time.sleep(SYNC_INTERVAL)
    
    if CLOUD_API_URL:
        thread = threading.Thread(target=sync_loop, daemon=True)
        thread.start()
        print(f"[SYNC] ✅ Sync thread started (interval: {SYNC_INTERVAL}s)")
        print(f"[SYNC] ✅ Cloud URL: {CLOUD_API_URL}")
        print(f"[SYNC] ✅ Center ID: {CENTER_ID}")
    else:
        print("[SYNC] ⚠️ Cloud sync disabled (CLOUD_API_URL not set)")

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """Initialize database with error handling"""
    try:
        with app.app_context():
            db.create_all()
            print("[DB] ✅ Tables created successfully")
            
            # Create default admin if not exists
            admin = User.query.filter_by(role='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@ninetygaming.com',
                    role='admin',
                    full_name='System Administrator',
                    is_active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.flush()
                
                wallet = Wallet(user_id=admin.id, balance=100)
                db.session.add(wallet)
                
                db.session.commit()
                print("[DB] ✅ Default admin created: admin / admin123")
                print("[DB] ✅ Admin wallet created with 100€")
            else:
                wallet = Wallet.query.filter_by(user_id=admin.id).first()
                if not wallet:
                    wallet = Wallet(user_id=admin.id, balance=100)
                    db.session.add(wallet)
                    db.session.commit()
                    print("[DB] ✅ Admin wallet created with 100€")
                else:
                    print("[DB] ✅ Admin user and wallet already exist")
            
            user_count = User.query.count()
            print(f"[DB] Total users: {user_count}")
            
            return True
    except Exception as e:
        print(f"[DB] ❌ Database initialization failed: {e}")
        return False

# ============================================================
# AUTHENTICATION ENDPOINTS
# ============================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name', '')
    
    if not username or not email or not password:
        return jsonify({'status': 'error', 'message': 'Username, email and password required'}), 400
    
    if len(password) < 6:
        return jsonify({'status': 'error', 'message': 'Password must be at least 6 characters'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'Username already exists'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'status': 'error', 'message': 'Email already exists'}), 400
    
    user = User(
        username=username,
        email=email,
        role='player',
        full_name=full_name,
        is_active=True
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    wallet = Wallet(user_id=user.id, balance=0)
    db.session.add(wallet)
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password required'}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401
    
    if not user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'status': 'error', 'message': 'Account is disabled'}), 403
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role, 'username': user.username}
    )
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        'status': 'ok',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
        'role': user.role
    })

@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role, 'username': user.username}
    )
    
    return jsonify({
        'status': 'ok',
        'access_token': access_token
    })

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    return jsonify({
        'status': 'ok',
        'user': user.to_dict()
    })

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    return jsonify({'status': 'ok', 'message': 'Logged out successfully'})

# ============================================================
# ADMIN ENDPOINTS
# ============================================================

@app.route('/api/admin/users', methods=['GET'])
@role_required(['admin'])
def admin_get_users():
    users = User.query.all()
    return jsonify({
        'status': 'ok',
        'users': [u.to_dict() for u in users],
        'total': len(users)
    })

@app.route('/api/admin/users/<user_id>', methods=['PUT'])
@role_required(['admin'])
def admin_update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    data = request.json
    if 'role' in data:
        user.role = data['role']
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'phone' in data:
        user.phone = data['phone']
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'user': user.to_dict()
    })

@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@role_required(['admin'])
def admin_delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    if user.role == 'admin':
        return jsonify({'status': 'error', 'message': 'Cannot delete admin user'}), 400
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'status': 'ok', 'message': 'User deleted'})

# ============================================================
# GAME ENDPOINTS
# ============================================================

@app.route('/api/games', methods=['GET'])
@login_required
def get_games():
    return jsonify({
        'status': 'ok',
        'games': GAME_CATALOG
    })

@app.route('/api/games/launch', methods=['POST'])
@role_required(['admin', 'staff'])
def launch_game():
    data = request.json
    pc_id = data.get('pc_id')
    game_id = data.get('game_id')
    
    if pc_id not in pcs_cache:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404
    
    game = next((g for g in GAME_CATALOG if g['id'] == game_id), None)
    if not game:
        return jsonify({'status': 'error', 'message': 'Game not found'}), 404
    
    if pc_id not in pending_commands:
        pending_commands[pc_id] = []
    
    pending_commands[pc_id].append({
        'action': 'LAUNCH_GAME',
        'parameter': game['executable'],
        'timestamp': datetime.now().isoformat()
    })
    
    print(f"[GAME LAUNCH] {pc_id} -> {game['name']}")
    return jsonify({'status': 'ok', 'message': f'Launching {game["name"]}'})

# ============================================================
# INSTALLED GAMES ENDPOINTS
# ============================================================

@app.route('/api/games/installed', methods=['POST'])
def receive_installed_games():
    try:
        data = request.json
        pc_id = data.get('pc_id')
        hostname = data.get('hostname', 'Unknown')
        games = data.get('games', [])
        
        if not pc_id:
            return jsonify({'status': 'error', 'message': 'No PC ID'}), 400
        
        pc = PC.query.get(pc_id)
        if not pc:
            pc = PC(id=pc_id, hostname=hostname)
            db.session.add(pc)
        
        pc.installed_games = games
        pc.last_telemetry = datetime.utcnow()
        db.session.commit()
        
        pcs_cache[pc_id] = pc.to_dict()
        
        print(f"[GAMES] {pc_id} - Found {len(games)} games")
        return jsonify({'status': 'ok', 'message': f'Received {len(games)} games'})
    
    except Exception as e:
        print(f"[ERROR] Failed to receive games: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/pc/<pc_id>/games', methods=['GET'])
@login_required
def get_pc_games(pc_id):
    pc = PC.query.get(pc_id)
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404
    
    games = pc.installed_games or []
    return jsonify({
        'status': 'ok',
        'pc_id': pc_id,
        'games': games,
        'total': len(games)
    })

@app.route('/api/games/launch-installed', methods=['POST'])
@role_required(['admin', 'staff'])
def launch_installed_game():
    try:
        data = request.json
        pc_id = data.get('pc_id')
        game_name = data.get('game_name')
        executable = data.get('executable')
        shortcut = data.get('shortcut', '')
        
        print(f"[GAME LAUNCH] Received request: {data}")
        
        if not pc_id:
            return jsonify({'status': 'error', 'message': 'Missing PC ID'}), 400
        
        if pc_id not in pcs:
            return jsonify({'status': 'error', 'message': 'PC not found'}), 404
        
        games = pcs[pc_id].get('installed_games', [])
        
        game_found = None
        for g in games:
            if g.get('name') == game_name:
                game_found = g
                break
        
        if not game_found:
            for g in games:
                if g.get('name', '').lower() == game_name.lower():
                    game_found = g
                    break
        
        if game_found:
            stored_executable = game_found.get('executable_path', '')
            if stored_executable:
                executable = stored_executable
                print(f"[GAME LAUNCH] Using stored path: {executable}")
            else:
                executable = game_found.get('executable', '')
                if executable:
                    print(f"[GAME LAUNCH] Using executable field: {executable}")
        
        if not executable:
            return jsonify({'status': 'error', 'message': 'No executable path found for this game'}), 400
        
        if pc_id not in pending_commands:
            pending_commands[pc_id] = []
        
        pending_commands[pc_id].append({
            'action': 'LAUNCH_GAME',
            'parameter': executable,
            'game_name': game_name,
            'shortcut': shortcut,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"[GAME LAUNCH] {pc_id} -> {game_name} ({executable})")
        
        return jsonify({
            'status': 'ok',
            'message': f'Launching {game_name} on {pc_id}'
        })
    
    except Exception as e:
        print(f"[ERROR] Launch failed: {e}")

# ============================================================
# WALLET ENDPOINTS
# ============================================================

@app.route('/api/wallet', methods=['GET'])
@login_required
def get_wallet():
    user = User.query.get(request.user_id)
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)
        db.session.commit()
    
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.created_at.desc()).limit(20).all()
    
    return jsonify({
        'status': 'ok',
        'wallet': wallet.to_dict(),
        'transactions': [t.to_dict() for t in transactions]
    })

@app.route('/api/wallet/topup', methods=['POST'])
@login_required
def topup_wallet():
    user = User.query.get(request.user_id)
    data = request.json
    amount = data.get('amount', 0)
    
    if amount <= 0:
        return jsonify({'status': 'error', 'message': 'Amount must be positive'}), 400
    
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)
    
    wallet.balance += amount
    wallet.updated_at = datetime.utcnow()
    
    transaction = Transaction(
        wallet_id=wallet.id,
        user_id=user.id,
        type='topup',
        amount=amount,
        new_balance=wallet.balance,
        description=f'Top-up of {amount}€'
    )
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'wallet': wallet.to_dict(),
        'transaction': transaction.to_dict()
    })

# ============================================================
# MEMBERSHIP ENDPOINTS
# ============================================================

@app.route('/api/membership/plans', methods=['GET'])
def get_membership_plans():
    return jsonify({'status': 'ok', 'plans': MEMBERSHIP_PLANS})

@app.route('/api/membership', methods=['GET'])
@login_required
def get_membership():
    user = User.query.get(request.user_id)
    membership = Membership.query.filter_by(user_id=user.id).first()
    
    if not membership:
        return jsonify({'status': 'ok', 'membership': None})
    
    return jsonify({'status': 'ok', 'membership': membership.to_dict()})

@app.route('/api/membership/buy', methods=['POST'])
@login_required
def buy_membership():
    user = User.query.get(request.user_id)
    data = request.json
    plan = data.get('plan')
    
    if plan not in MEMBERSHIP_PLANS:
        return jsonify({'status': 'error', 'message': 'Invalid plan'}), 400
    
    plan_data = MEMBERSHIP_PLANS[plan]
    
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet or wallet.balance < plan_data['price']:
        return jsonify({'status': 'error', 'message': 'Insufficient balance'}), 400
    
    wallet.balance -= plan_data['price']
    wallet.updated_at = datetime.utcnow()
    
    transaction = Transaction(
        wallet_id=wallet.id,
        user_id=user.id,
        type='membership',
        amount=-plan_data['price'],
        new_balance=wallet.balance,
        description=f'Purchased {plan} membership'
    )
    db.session.add(transaction)
    
    membership = Membership(
        user_id=user.id,
        plan=plan,
        plan_name=plan_data['name'],
        hours_total=plan_data['hours'],
        hours_left=plan_data['hours'],
        purchase_date=datetime.utcnow(),
        expiry_date=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    db.session.add(membership)
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'membership': membership.to_dict(),
        'balance': wallet.balance
    })

# ============================================================
# RESERVATION ENDPOINTS (UPDATED WITH CLOUD SYNC)
# ============================================================

@app.route('/api/reservations', methods=['GET'])
@login_required
def get_reservations():
    user = User.query.get(request.user_id)
    
    # Get local reservations
    if user.role in ['admin', 'staff']:
        local_reservations = Reservation.query.filter_by(source='local').order_by(Reservation.start_time).all()
        cloud_reservations = Reservation.query.filter_by(source='cloud').order_by(Reservation.start_time).all()
    else:
        local_reservations = Reservation.query.filter_by(user_id=user.id, source='local').order_by(Reservation.start_time).all()
        cloud_reservations = Reservation.query.filter_by(user_email=user.email, source='cloud').order_by(Reservation.start_time).all()
    
    # Combine and sort
    all_reservations = list(local_reservations) + list(cloud_reservations)
    all_reservations.sort(key=lambda x: x.start_time)
    
    return jsonify({
        'status': 'ok',
        'reservations': [r.to_dict() for r in all_reservations],
        'total': len(all_reservations),
        'sources': {
            'local': len(local_reservations),
            'cloud': len(cloud_reservations)
        }
    })

@app.route('/api/reservations/create', methods=['POST'])
@login_required
def create_reservation():
    user = User.query.get(request.user_id)
    data = request.json
    
    pc_id = data.get('pc_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    user_name = data.get('user_name', user.username)
    
    if not pc_id or not start_time or not end_time:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except:
        return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400
    
    if start >= end:
        return jsonify({'status': 'error', 'message': 'End time must be after start time'}), 400
    
    # Check conflicts (both local and cloud reservations)
    existing = Reservation.query.filter_by(pc_id=pc_id, status='pending').all()
    for r in existing:
        if r.start_time < end and r.end_time > start:
            return jsonify({'status': 'error', 'message': 'PC already reserved during this time'}), 400
    
    reservation = Reservation(
        pc_id=pc_id,
        user_id=user.id,
        start_time=start,
        end_time=end,
        user_name=user_name,
        status='pending',
        source='local'
    )
    db.session.add(reservation)
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'reservation': reservation.to_dict()
    })

@app.route('/api/reservations/<reservation_id>/cancel', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    user = User.query.get(request.user_id)
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'status': 'error', 'message': 'Reservation not found'}), 404
    
    if user.role not in ['admin', 'staff'] and reservation.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    reservation.status = 'cancelled'
    db.session.commit()
    
    return jsonify({'status': 'ok', 'message': 'Reservation cancelled'})

# ============================================================
# BRANCH ENDPOINTS
# ============================================================

@app.route('/api/branches', methods=['GET'])
@login_required
def get_branches():
    branches = Branch.query.all()
    return jsonify({
        'status': 'ok',
        'branches': [b.to_dict() for b in branches]
    })

@app.route('/api/branches', methods=['POST'])
@role_required(['admin'])
def create_branch():
    data = request.json
    name = data.get('name')
    address = data.get('address', '')
    city = data.get('city', '')
    phone = data.get('phone', '')
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Branch name required'}), 400
    
    branch = Branch(
        name=name,
        address=address,
        city=city,
        phone=phone
    )
    db.session.add(branch)
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'branch': branch.to_dict()
    })

# ============================================================
# SESSION ENDPOINTS
# ============================================================

@app.route('/api/session/start', methods=['POST'])
@login_required
def start_session():
    user = User.query.get(request.user_id)
    data = request.json
    
    pc_id = data.get('pc_id')
    user_name = data.get('user_name', user.username)
    session_type = data.get('session_type', 'time')
    
    if not pc_id:
        return jsonify({'status': 'error', 'message': 'PC ID required'}), 400
    
    if pc_id in sessions_cache and sessions_cache[pc_id].get('status') == 'active':
        return jsonify({'status': 'error', 'message': 'PC already in session'}), 400
    
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)
        db.session.commit()
    
    MIN_BALANCE = 1.0
    if wallet.balance < MIN_BALANCE:
        return jsonify({
            'status': 'error',
            'message': f'Insufficient balance. Minimum {MIN_BALANCE}€ required',
            'balance': wallet.balance
        }), 400
    
    pc = PC.query.get(pc_id)
    current_game = pc.current_game if pc else 'unknown'
    
    session = Session(
        pc_id=pc_id,
        user_id=user.id,
        start_time=datetime.utcnow(),
        game=current_game,
        session_type=session_type,
        status='active',
        price_per_minute=0.10
    )
    db.session.add(session)
    db.session.commit()
    
    sessions_cache[pc_id] = {
        'user': user.username,
        'start_time': session.start_time.isoformat(),
        'game': session.game,
        'game_type': session_type,
        'status': 'active',
        'price_per_minute': 0.10
    }
    
    if pc_id not in pending_commands:
        pending_commands[pc_id] = []
    
    pending_commands[pc_id].append({
        'action': 'START_SESSION',
        'parameter': user.username,
        'timestamp': datetime.now().isoformat()
    })
    
    return jsonify({
        'status': 'ok',
        'message': f'Session started for {user_name}',
        'session': session.to_dict(),
        'balance': wallet.balance
    })

@app.route('/api/session/end', methods=['POST'])
@login_required
def end_session():
    user = User.query.get(request.user_id)
    data = request.json
    
    pc_id = data.get('pc_id')
    
    if not pc_id:
        return jsonify({'status': 'error', 'message': 'PC ID required'}), 400
    
    if pc_id not in sessions_cache or sessions_cache[pc_id].get('status') != 'active':
        return jsonify({'status': 'error', 'message': 'No active session'}), 400
    
    session = Session.query.filter_by(pc_id=pc_id, status='active').first()
    if not session:
        return jsonify({'status': 'error', 'message': 'Session not found'}), 404
    
    start = session.start_time
    end = datetime.utcnow()
    duration_seconds = (end - start).total_seconds()
    duration_minutes = round(duration_seconds / 60, 2)
    cost = round(duration_minutes * session.price_per_minute, 2)
    
    session.end_time = end
    session.duration_minutes = duration_minutes
    session.cost = cost
    session.status = 'ended'
    
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if wallet:
        wallet.balance = max(0, wallet.balance - cost)
        wallet.updated_at = datetime.utcnow()
        
        transaction = Transaction(
            wallet_id=wallet.id,
            user_id=user.id,
            type='session',
            amount=-cost,
            new_balance=wallet.balance,
            description=f'Session: {duration_minutes}min, Game: {session.game}',
            session_id=session.id
        )
        db.session.add(transaction)
    
    db.session.commit()
    
    sessions_cache[pc_id]['status'] = 'ended'
    sessions_cache[pc_id]['duration'] = duration_minutes
    sessions_cache[pc_id]['cost'] = cost
    
    session_history.append({
        'pc_id': pc_id,
        'user': user.username,
        'start_time': session.start_time.isoformat(),
        'end_time': end.isoformat(),
        'duration_minutes': duration_minutes,
        'cost': cost,
        'game': session.game
    })
    
    if pc_id not in pending_commands:
        pending_commands[pc_id] = []
    
    pending_commands[pc_id].append({
        'action': 'END_SESSION',
        'parameter': '',
        'timestamp': datetime.now().isoformat()
    })
    
    return jsonify({
        'status': 'ok',
        'message': 'Session ended',
        'session': {
            'user': user.username,
            'duration_minutes': duration_minutes,
            'cost': cost,
            'game': session.game,
            'session_type': session.session_type,
            'balance_after': wallet.balance if wallet else 0
        }
    })

@app.route('/api/session/status/<pc_id>', methods=['GET'])
@login_required
def get_session_status(pc_id):
    if pc_id in sessions_cache:
        return jsonify({
            'pc_id': pc_id,
            'session': sessions_cache[pc_id]
        })
    return jsonify({
        'pc_id': pc_id,
        'session': None
    })

@app.route('/api/session/history', methods=['GET'])
@login_required
def get_session_history():
    limit = request.args.get('limit', 50, type=int)
    user = User.query.get(request.user_id)
    
    if user.role in ['admin', 'staff']:
        history = session_history[-limit:]
    else:
        history = [h for h in session_history if h.get('user') == user.username][-limit:]
    
    return jsonify({
        'status': 'ok',
        'history': history,
        'total': len(history)
    })

# ============================================================
# COMMAND ENDPOINTS
# ============================================================

@app.route('/api/commands/<pc_id>', methods=['GET'])
def get_commands(pc_id):
    commands = []
    if pc_id in pending_commands and pending_commands[pc_id]:
        commands = pending_commands[pc_id]
        pending_commands[pc_id] = []
        print(f"[POLL] Sending {len(commands)} command(s) to {pc_id}")
    return jsonify(commands)

@app.route('/api/command', methods=['POST'])
@role_required(['admin', 'staff'])
def send_command():
    data = request.json
    pc_id = data.get('pc_id')
    command = data.get('command')
    parameter = data.get('parameter', '')
    
    if not pc_id or not command:
        return jsonify({'status': 'error', 'message': 'Missing pc_id or command'}), 400
    
    if pc_id not in pending_commands:
        pending_commands[pc_id] = []
    
    pending_commands[pc_id].append({
        'action': command,
        'parameter': parameter,
        'timestamp': datetime.now().isoformat()
    })
    
    print(f"[COMMAND] Sending {command} to {pc_id}")
    return jsonify({'status': 'ok', 'message': f'Command {command} sent'})

# ============================================================
# HEARTBEAT & TELEMETRY
# ============================================================

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    
    pc_id = data.get('pc_id') or data.get('mac_address')
    if not pc_id:
        return jsonify({'status': 'error', 'message': 'No PC ID'}), 400
    
    hostname = data.get('hostname', 'Unknown')
    ip_address = data.get('ip_address', '')
    if not ip_address and 'features' in data:
        ip_address = data['features'].get('ip_address', '')
    if not ip_address:
        ip_address = request.remote_addr
    
    hardware = data.get('hardware', {})
    if not hardware and 'features' in data:
        features = data['features']
        hardware = {
            'cpu': features.get('cpu_name', 'Unknown CPU'),
            'gpu': features.get('gpu_name', 'Unknown GPU'),
            'ram': features.get('ram_size', 'Unknown RAM')
        }
    
    pc = PC.query.get(pc_id)
    if not pc:
        pc = PC(id=pc_id)
        db.session.add(pc)
    
    pc.hostname = hostname
    pc.ip_address = ip_address
    pc.status = 'online'
    pc.last_heartbeat = datetime.utcnow()
    
    if hardware:
        pc.cpu_model = hardware.get('cpu', pc.cpu_model)
        pc.gpu_model = hardware.get('gpu', pc.gpu_model)
        pc.ram_size = hardware.get('ram', pc.ram_size)
    
    if 'features' in data:
        features = data['features']
        pc.cpu_usage = features.get('cpu_usage', 0)
        pc.gpu_usage = features.get('gpu_usage', 0)
        pc.ram_usage = features.get('ram_usage', 0)
        pc.cpu_temp = features.get('cpu_temperature', 0)
        pc.current_game = features.get('process_name', 'none')
        pc.window_title = features.get('window_title', '')
        pc.is_fullscreen = features.get('is_fullscreen', False)
        pc.last_telemetry = datetime.utcnow()
    
    db.session.commit()
    pcs_cache[pc_id] = pc.to_dict()
    
    return jsonify({'status': 'ok'})

# ============================================================
# ANTI-THEFT ALERTS
# ============================================================

@app.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    return jsonify({
        'status': 'ok',
        'alerts': usb_alerts[-20:],
        'total': len(usb_alerts)
    })

@app.route('/api/alerts/clear', methods=['POST'])
@role_required(['admin', 'staff'])
def clear_alerts():
    global usb_alerts
    usb_alerts = []
    return jsonify({'status': 'ok'})

# ============================================================
# PC DATA ENDPOINTS
# ============================================================

@app.route('/api/pcs', methods=['GET'])
@login_required
def get_pcs():
    user = User.query.get(request.user_id)
    pcs = PC.query.all()
    result = []
    
    for pc in pcs:
        pc_data = pc.to_dict()
        pc_data['in_session'] = pc.id in sessions_cache and sessions_cache[pc.id].get('status') == 'active'
        pc_data['session'] = sessions_cache.get(pc.id)
        
        wallet = Wallet.query.filter_by(user_id=user.id).first()
        pc_data['wallet_balance'] = wallet.balance if wallet else 0
        
        result.append(pc_data)
    
    return jsonify({
        'status': 'ok',
        'pcs': result,
        'active_sessions': len([s for s in sessions_cache.values() if s.get('status') == 'active'])
    })

@app.route('/api/pc/<pc_id>', methods=['GET'])
@login_required
def get_pc_details(pc_id):
    pc = PC.query.get(pc_id)
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404
    
    result = pc.to_dict()
    result['in_session'] = pc_id in sessions_cache and sessions_cache[pc_id].get('status') == 'active'
    result['session'] = sessions_cache.get(pc_id)
    
    user = User.query.get(request.user_id)
    wallet = Wallet.query.filter_by(user_id=user.id).first()
    result['wallet_balance'] = wallet.balance if wallet else 0
    
    return jsonify(result)

# ============================================================
# SERVE FRONTEND
# ============================================================

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/pc/<pc_id>')
def pc_detail(pc_id):
    return send_from_directory('../frontend', 'pc-detail.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

# ============================================================
# SERVER DISCOVERY - STARTUP
# ============================================================

def start_discovery():
    discovery_thread = threading.Thread(target=start_discovery_broadcast, daemon=True)
    discovery_thread.start()
    print("[DISCOVERY] Discovery broadcast thread started")

# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("   NINETY GAMING HOUSE - LOCAL SERVER")
    print("=" * 60)
    print(f"🌐 Server running at: http://{SERVER_IP}:{SERVER_PORT}")
    print("=" * 60)
    print("📡 Discovery broadcast on port 9000")
    print("🔄 Broadcasting every 2 seconds")
    print("=" * 60)
    print("☁️ Cloud Sync:")
    if CLOUD_API_URL:
        print(f"   ✅ Cloud URL: {CLOUD_API_URL}")
        print(f"   ✅ Center ID: {CENTER_ID}")
        print(f"   ✅ Sync interval: {SYNC_INTERVAL}s")
    else:
        print("   ❌ Cloud sync disabled")
    print("=" * 60)
    print("🔐 Authentication:")
    print("   - Admin: admin / admin123")
    print("=" * 60)
    print("🎮 Features:")
    print("   - PC Node Tracking")
    print("   - Session & Financial Control")
    print("   - Remote Administration")
    print("   - Hardware Telemetry")
    print("   - Electronic Wallet")
    print("   - Subscription Plans")
    print("   - Reservation System (Local + Cloud)")
    print("   - Multi-Branch Support")
    print("   - Game Catalog")
    print("   - Anti-Theft Alerts")
    print("   - Installed Games Discovery")
    print("   - User Authentication & Roles")
    print("=" * 60)
    
    # Initialize database
    print("\n[DB] Initializing database...")
    if not init_db():
        print("\n[ERROR] Database initialization failed!")
        print("Please fix the database connection and restart the server.")
        exit(1)
    
    # Start cloud sync thread
    start_sync_thread()
    
    # Start discovery
    start_discovery()
    
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=True, threaded=True)