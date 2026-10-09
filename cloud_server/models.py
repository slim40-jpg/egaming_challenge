from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='player')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 👇 NEW: Player Wallet Balance
    wallet_balance = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'wallet_balance': self.wallet_balance,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 👇 NEW: Transaction Model for Audit Logging
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'recharge' or 'session_deduction'
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'type': self.type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat()
        }


class PCMirror(db.Model):
    """Minimal public representation of each PC — kept in sync by the local server."""
    __tablename__ = 'pc_mirror'
    id = db.Column(db.Integer, primary_key=True)
    center_id = db.Column(db.String(50), nullable=False, default='main')
    pc_id = db.Column(db.String(100), nullable=False)  # MAC address
    name = db.Column(db.String(100), default='PC')
    online = db.Column(db.Boolean, default=False)
    state = db.Column(db.String(20), default='offline')  # available|reserved|in_session|offline|maintenance
    installed_games = db.Column(db.JSON, default=list)
    last_sync = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('center_id', 'pc_id', name='uq_center_pc'),)

    def to_dict(self):
        return {
            'pc_id': self.pc_id,
            'center_id': self.center_id,
            'name': self.name,
            'online': self.online,
            'state': self.state,
            'installed_games': self.installed_games or [],
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
        }


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.String(36), primary_key=True)
    pc_id = db.Column(db.String(50), nullable=False)
    center_id = db.Column(db.String(50), nullable=False, default='main')
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(100), nullable=False)
    user_phone = db.Column(db.String(20))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='accepted')
    synced = db.Column(db.Boolean, default=False)
    synced_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'pc_id': self.pc_id,
            'center_id': self.center_id,
            'user_name': self.user_name,
            'user_email': self.user_email,
            'user_phone': self.user_phone,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'status': self.status,
            'synced': self.synced,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }