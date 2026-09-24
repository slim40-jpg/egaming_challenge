from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='player')


class PC(db.Model):
    __tablename__ = 'pcs'

    # ✅ Primary key: matches your actual DB column "id"
    id = db.Column(db.String(36), primary_key=True)      # MAC address
    hostname = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    status = db.Column(db.String(20), default='offline')  # 'online' | 'offline'
    cpu_model = db.Column(db.String(100))
    gpu_model = db.Column(db.String(100))
    ram_size = db.Column(db.String(50))
    cpu_usage = db.Column(db.Float, default=0.0)
    gpu_usage = db.Column(db.Float, default=0.0)
    ram_usage = db.Column(db.Float, default=0.0)
    cpu_temp = db.Column(db.Float)
    gpu_temp = db.Column(db.Float)
    current_game = db.Column(db.String(100), default='none')
    window_title = db.Column(db.String(200))
    is_fullscreen = db.Column(db.Boolean)
    last_heartbeat = db.Column(db.DateTime)
    last_telemetry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    installed_games = db.Column(db.JSON, default=list)

    # ─────────────────────────────────────────────────
    # Read-only convenience properties.
    # These DO NOT get set by the constructor.
    # Use pc.id for the DB column, pc.pc_id only for reads.
    # ─────────────────────────────────────────────────
    @property
    def pc_id(self):
        return self.id

    @property
    def online(self):
        return self.status == 'online'

    @property
    def cpu(self):
        return int(self.cpu_usage or 0)

    @property
    def ram(self):
        return int(self.ram_usage or 0)

    @property
    def gpu(self):
        return int(self.gpu_usage or 0)

    @property
    def ram_total(self):
        return self.ram_size


class Session(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    pc_id = db.Column(db.String(36), db.ForeignKey('pcs.id'), nullable=False)
    user_name = db.Column(db.String(100))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    price_per_minute = db.Column(db.Float, default=0.10)
    cost = db.Column(db.Float, default=0.0)
    active = db.Column(db.Boolean, default=True)


class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    pc_id = db.Column(db.String(36), db.ForeignKey('pcs.id'), nullable=False)
    user_name = db.Column(db.String(100))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='accepted')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class SyncState(db.Model):
    __tablename__ = 'sync_state'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(100))


class Wallet(db.Model):
    __tablename__ = 'wallets'
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), unique=True)
    balance = db.Column(db.Float, default=0.0)


class Command(db.Model):
    __tablename__ = 'commands'
    id = db.Column(db.Integer, primary_key=True)
    pc_id = db.Column(db.String(36), nullable=False)
    command = db.Column(db.String(50), nullable=False)
    payload = db.Column(db.JSON)
    delivered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)