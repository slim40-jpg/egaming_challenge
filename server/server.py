# server/server.py

import os
import json
import time
import socket
import threading
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, jwt_required, get_jwt_identity, get_jwt
)
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
load_dotenv()

from models import db, PC, Session, Reservation, Wallet, Command, User
from state_machine import compute_state, snapshot_pc
from sync_client import start_sync_threads


# ─────────────────────────────────────────────────────────────
# Debug: show what env vars were actually loaded
# ─────────────────────────────────────────────────────────────
print('─────────────────────────────────────────')
print('ENV:')
print('  DATABASE_URL     =', os.getenv('DATABASE_URL'))
print('  CLOUD_API_URL    =', os.getenv('CLOUD_API_URL'))
print('  CENTER_ID        =', os.getenv('CENTER_ID'))
print('  CENTER_API_KEY   =', (os.getenv('CENTER_API_KEY') or '')[:8] + '…')
print('─────────────────────────────────────────')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
})

db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt().get('role') != 'admin':
            return jsonify({'error': 'admin required'}), 403
        return fn(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'service': 'local'})


# ─────────────────────────────────────────────────────────────
# Agent-facing endpoints (no auth — LAN only)
# ─────────────────────────────────────────────────────────────

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json() or {}
    pc_id = data.get('pc_id')
    if not pc_id:
        return jsonify({'error': 'pc_id required'}), 400

    pc = PC.query.filter_by(id=pc_id).first()
    if not pc:
        pc = PC(id=pc_id)
        db.session.add(pc)

    # ── Extract telemetry from the NESTED shape the agent sends ──
    features = data.get('features') or {}
    hardware = data.get('hardware') or {}

    def _num(*candidates):
        """First candidate that parses as float, else 0.0."""
        for c in candidates:
            if c is None:
                continue
            try:
                return float(c)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _text(*candidates):
        """First non-empty candidate, else None."""
        for c in candidates:
            if c:
                return c
        return None

    pc.hostname = _text(data.get('hostname'), pc.hostname)
    pc.ip_address = _text(data.get('ip_address'), data.get('ip'), pc.ip_address)
    pc.status = 'online'
    pc.last_heartbeat = datetime.utcnow()
    pc.last_telemetry = datetime.utcnow()

    pc.cpu_usage = _num(features.get('cpu_usage'), data.get('cpu'), data.get('cpu_usage'))
    pc.ram_usage = _num(features.get('ram_usage'), data.get('ram'), data.get('ram_usage'))
    pc.gpu_usage = _num(features.get('gpu_usage'), data.get('gpu'), data.get('gpu_usage'))
    pc.cpu_temp  = _num(features.get('cpu_temperature'), data.get('cpu_temp'), data.get('cpu_temperature'))

    pc.current_game  = _text(features.get('process_name'), data.get('game'), data.get('current_game')) or pc.current_game
    pc.window_title  = _text(features.get('window_title'), pc.window_title)
    if 'is_fullscreen' in features:
        pc.is_fullscreen = bool(features['is_fullscreen'])

    pc.cpu_model = _text(hardware.get('cpu'), data.get('cpu_model'), pc.cpu_model)
    pc.gpu_model = _text(hardware.get('gpu'), data.get('gpu_model'), pc.gpu_model)
    pc.ram_size  = _text(hardware.get('ram'), data.get('ram_total'), pc.ram_size)

    db.session.commit()

    # Optional: log to confirm
    print(f'💓 {pc_id}  cpu={pc.cpu_usage}  ram={pc.ram_usage}  gpu={pc.gpu_usage}')

    return jsonify({'status': 'ok'})

@app.route('/api/games/installed', methods=['POST'])
def report_installed_games():
    data = request.get_json() or {}
    pc_id = data.get('pc_id')
    games = data.get('games') or []
    if not pc_id:
        return jsonify({'error': 'pc_id required'}), 400

    pc = PC.query.filter_by(id=pc_id).first()
    if not pc:
        pc = PC(id=pc_id)
        db.session.add(pc)

    pc.installed_games = games
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/commands/<pc_id>', methods=['GET'])
def poll_commands(pc_id):
    """
    Agent polls for pending commands.
    The agent's C++ parser expects:  { "id", "action", "parameter" }
    The DB stores:                    { command, payload }
    So we map between them.
    """
    rows = Command.query.filter_by(pc_id=pc_id, delivered=False).all()

    out = []
    for c in rows:
        # Extract a single string parameter for the agent.
        # The agent only understands one string arg per command.
        parameter = ''
        p = c.payload if isinstance(c.payload, dict) else {}

        if c.command == 'LAUNCH_GAME':
            # Prefer the executable path
            parameter = p.get('executable') or p.get('path') or p.get('game_name') or ''
        elif c.command == 'START_SESSION':
            parameter = p.get('user_name') or p.get('user') or 'Player'
        else:
            # LOCK, SHUTDOWN, RESTART — no parameter
            parameter = ''

        out.append({
            'id': c.id,
            'action': c.command,      # ← agent expects "action"
            'parameter': parameter,   # ← agent expects "parameter"
        })
        c.delivered = True

    db.session.commit()
    return jsonify({'status': 'ok', 'commands': out})

# ─────────────────────────────────────────────────────────────
# Admin / dashboard endpoints (JWT)
# ─────────────────────────────────────────────────────────────

@app.route('/api/pcs', methods=['GET'])
@jwt_required()
def list_pcs():
    pcs = PC.query.all()
    return jsonify({'status': 'ok', 'pcs': [
        {
            'pc_id': p.pc_id,
            'hostname': p.hostname,
            'online': p.online,
            'state': compute_state(p),
            'current_game': p.current_game,
            'cpu': p.cpu, 'ram': p.ram, 'gpu': p.gpu,
        } for p in pcs
    ]})


@app.route('/api/pc/<pc_id>', methods=['GET'])
@jwt_required()
def pc_detail(pc_id):
    pc = PC.query.filter_by(id=pc_id).first()               # ← was pc_id=
    if not pc:
        return jsonify({'error': 'not found'}), 404

    active = Session.query.filter_by(pc_id=pc_id, active=True).first()
    session_data = None
    if active:
        session_data = {
            'user': active.user_name,
            'game': pc.current_game,
            'start_time': active.start_time.isoformat(),
            'price_per_minute': active.price_per_minute,
        }

    return jsonify({
        'pc_id': pc.pc_id,
        'hostname': pc.hostname,
        'ip_address': pc.ip_address,
        'mac_address': pc.pc_id,
        'online': pc.online,
        'state': compute_state(pc),
        'in_session': active is not None,
        'session': session_data,
        'game': pc.current_game,
        'cpu': pc.cpu, 'ram': pc.ram, 'gpu': pc.gpu,
        'hardware': {
            'cpu': pc.cpu_model,
            'gpu': pc.gpu_model,
            'ram': pc.ram_total,
        },
    })


@app.route('/api/pc/<pc_id>/games', methods=['GET'])
@jwt_required()
def pc_games(pc_id):
    pc = PC.query.filter_by(id=pc_id).first()               # ← was pc_id=
    if not pc:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404
    return jsonify({'status': 'ok', 'games': pc.installed_games or []})


@app.route('/api/command', methods=['POST'])
@admin_required
def send_command():
    data = request.get_json() or {}
    pc_id = data.get('pc_id')
    command = data.get('command')
    if not pc_id or not command:
        return jsonify({'error': 'pc_id and command required'}), 400

    c = Command(pc_id=pc_id, command=command, payload=data.get('payload') or {})
    db.session.add(c)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': c.id})


@app.route('/api/games/launch-installed', methods=['POST'])
@admin_required
def launch_game():
    data = request.get_json() or {}
    pc_id = data.get('pc_id')
    game_name = data.get('game_name')
    if not pc_id or not game_name:
        return jsonify({'error': 'pc_id and game_name required'}), 400

    c = Command(
        pc_id=pc_id,
        command='LAUNCH_GAME',
        payload={
            'game_name': game_name,
            'executable': data.get('executable'),
            'shortcut': data.get('shortcut'),
        },
    )
    db.session.add(c)
    db.session.commit()
    return jsonify({'status': 'ok'})


# ─────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────

@app.route('/api/session/start', methods=['POST'])
@jwt_required()
def start_session():
    data = request.get_json() or {}
    pc_id = data.get('pc_id')
    user_name = data.get('user_name', 'Joueur')
    if not pc_id:
        return jsonify({'error': 'pc_id required'}), 400

    existing = Session.query.filter_by(pc_id=pc_id, active=True).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'session already active'}), 409

    s = Session(pc_id=pc_id, user_name=user_name, start_time=datetime.utcnow())
    db.session.add(s)
    db.session.commit()
    return jsonify({'status': 'ok', 'session_id': s.id})


@app.route('/api/session/end', methods=['POST'])
@jwt_required()
def end_session():
    data = request.get_json() or {}
    pc_id = data.get('pc_id')
    s = Session.query.filter_by(pc_id=pc_id, active=True).first()
    if not s:
        return jsonify({'status': 'error', 'message': 'no active session'}), 404

    s.end_time = datetime.utcnow()
    duration_sec = (s.end_time - s.start_time).total_seconds()
    s.cost = round((duration_sec / 60) * s.price_per_minute, 2)
    s.active = False
    db.session.commit()

    return jsonify({'status': 'ok', 'session': {
        'duration_minutes': round(duration_sec / 60, 2),
        'cost': s.cost,
    }})


# ─────────────────────────────────────────────────────────────
# Wallet
# ─────────────────────────────────────────────────────────────

def _wallet_for(username):
    w = Wallet.query.filter_by(user_name=username).first()
    if not w:
        w = Wallet(user_name=username, balance=0.0)
        db.session.add(w)
        db.session.commit()
    return w


@app.route('/api/wallet', methods=['GET'])
@jwt_required()
def get_wallet():
    username = get_jwt().get('username', 'unknown')
    w = _wallet_for(username)
    return jsonify({'status': 'ok', 'wallet': {'balance': w.balance}})


@app.route('/api/wallet/topup', methods=['POST'])
@jwt_required()
def topup():
    username = get_jwt().get('username', 'unknown')
    amount = float((request.get_json() or {}).get('amount', 0))
    if amount <= 0:
        return jsonify({'error': 'amount must be > 0'}), 400
    w = _wallet_for(username)
    w.balance += amount
    db.session.commit()
    return jsonify({'status': 'ok', 'wallet': {'balance': w.balance}})


# ─────────────────────────────────────────────────────────────
# Housekeeping
# ─────────────────────────────────────────────────────────────

def mark_offline_pcs():
    """Mark PCs offline if no heartbeat for 30s."""
    threshold = datetime.utcnow().timestamp() - 30
    dirty = False
    for pc in PC.query.all():
        if pc.last_heartbeat and pc.last_heartbeat.timestamp() < threshold:
            if pc.status != 'offline':                # ← write to status, not online
                pc.status = 'offline'
                dirty = True
    if dirty:
        db.session.commit()


# ─────────────────────────────────────────────────────────────
# UDP discovery broadcaster
# ─────────────────────────────────────────────────────────────
#
# The agent listens on UDP port 9000 for a broadcast. Every
# DISCOVERY_INTERVAL seconds we shout:
#   {"service":"ninety-gaming-local","host":"192.168.x.y","port":8003}
# The agent then knows where to POST heartbeats.
#
DISCOVERY_PORT = 9000
DISCOVERY_INTERVAL = 3   # seconds


def _detect_lan_ip() -> str:
    """Detect the LAN IP provided by the host, with Docker fallback."""

    # Docker/host startup script provides the real LAN IP
    lan_ip = os.getenv("LAN_IP")
    if lan_ip:
        return lan_ip

    # Fallback for running server outside Docker
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

DISCOVERY_PORT = 9000
DISCOVERY_INTERVAL = 2   # seconds — agent waits up to 10s on startup, be generous


def _detect_lan_ip() -> str:
    """Best-effort LAN IP (no real traffic)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def _broadcast_presence():
    ip = _detect_lan_ip()
    # ✅ EXACT format the C++ agent expects: "SERVER:<ip>:<port>"
    payload = f'SERVER:{ip}:8003'.encode('utf-8')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print(f'[discovery] broadcasting "{payload.decode()}" on UDP :{DISCOVERY_PORT}')
    while True:
        try:
            sock.sendto(payload, ('<broadcast>', DISCOVERY_PORT))
            # Also send to the local subnet directly — some Windows setups
            # drop '<broadcast>' but accept the subnet broadcast address.
            try:
                parts = ip.split('.')
                if len(parts) == 4:
                    subnet_bcast = f'{parts[0]}.{parts[1]}.{parts[2]}.255'
                    sock.sendto(payload, (subnet_bcast, DISCOVERY_PORT))
            except Exception:
                pass
        except Exception as e:
            print(f'[discovery] broadcast error: {e}')
        time.sleep(DISCOVERY_INTERVAL)


def start_discovery():
    threading.Thread(target=_broadcast_presence, daemon=True).start()


# ─────────────────────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Start UDP discovery (agent → server)
    start_discovery()
    # Start cloud sync (local → cloud)
    start_sync_threads(app)

    # Housekeeping: mark stale PCs offline
    def _housekeeping():
        while True:
            try:
                with app.app_context():
                    mark_offline_pcs()
            except Exception as e:
                print(f'[housekeeping] {e}')
            time.sleep(10)
    threading.Thread(target=_housekeeping, daemon=True).start()

    app.run(host='0.0.0.0', port=8003, debug=False)