# backend/models.py

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import uuid

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='player')  # admin, staff, player
    
    # Profile
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
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
    
    id = db.Column(db.String(36), primary_key=True)  # MAC address
    hostname = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    status = db.Column(db.String(20), default='offline')
    
    # Hardware
    cpu_model = db.Column(db.String(100))
    gpu_model = db.Column(db.String(100))
    ram_size = db.Column(db.String(50))
    
    # Telemetry
    cpu_usage = db.Column(db.Float, default=0)
    gpu_usage = db.Column(db.Float, default=0)
    ram_usage = db.Column(db.Float, default=0)
    cpu_temp = db.Column(db.Float, default=0)
    gpu_temp = db.Column(db.Float, default=0)
    
    # Current game
    current_game = db.Column(db.String(100), default='none')
    
    # Location
    branch_id = db.Column(db.String(36), db.ForeignKey('branches.id'))
    
    # Timestamps
    last_heartbeat = db.Column(db.DateTime)
    last_telemetry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = db.relationship('Session', backref='pc_ref', lazy=True)
    
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
            'hardware': {
                'cpu': self.cpu_model,
                'gpu': self.gpu_model,
                'ram': self.ram_size
            }
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
    status = db.Column(db.String(20), default='active')  # active, ended, cancelled
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'pc_id': self.pc_id,
            'user_id': self.user_id,
            'user': self.user_ref.username if self.user_ref else None,
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
    
    # Relationships
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
    
    type = db.Column(db.String(20), nullable=False)  # topup, session, refund
    amount = db.Column(db.Float, nullable=False)
    new_balance = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    
    # For session transactions
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
    
    plan = db.Column(db.String(20), nullable=False)  # basic, premium, pro
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
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pc_id = db.Column(db.String(36), db.ForeignKey('pcs.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    
    user_name = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'pc_id': self.pc_id,
            'user_id': self.user_id,
            'user_name': self.user_name or (self.user_ref.username if self.user_ref else None),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'notes': self.notes
        }

class Branch(db.Model):
    __tablename__ = 'branches'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    
    pcs = db.relationship('PC', backref='branch_ref', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'phone': self.phone
        }