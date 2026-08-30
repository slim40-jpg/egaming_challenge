from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
from datetime import datetime, timedelta
import socket
import threading
import time
import os
import netifaces

app = Flask(__name__, static_folder='../frontend')
CORS(app)

# ============================================================
# CONFIGURATION
# ============================================================

SERVER_PORT = 8003
DISCOVERY_PORT = 9000

# ============================================================
# LOCAL IP DETECTION
# ============================================================

def get_local_ip():
    """Get the most appropriate local IP address for this machine"""
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
    """Broadcast server presence on the network"""
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
# STORE DATA
# ============================================================

pcs = {}                    # PC data
pending_commands = {}       # Commands waiting for PCs
sessions = {}              # Active sessions
session_history = []       # Session history
wallets = {}               # Wallet balances
memberships = {}           # User memberships
reservations = []          # PC reservations
branches = {              # Multi-branch support
    'main': {
        'name': 'Main Branch',
        'address': '123 Gaming Street',
        'pcs': []
    }
}
game_catalog = []          # Available games
usb_alerts = []            # Anti-theft alerts

# ============================================================
# GAME CATALOG
# ============================================================

def init_game_catalog():
    global game_catalog
    game_catalog = [
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

init_game_catalog()

@app.route('/api/games', methods=['GET'])
def get_games():
    return jsonify({
        'status': 'ok',
        'games': game_catalog
    })

@app.route('/api/games/launch', methods=['POST'])
def launch_game():
    data = request.json
    pc_id = data.get('pc_id')
    game_id = data.get('game_id')
    
    if pc_id not in pcs:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404
    
    game = next((g for g in game_catalog if g['id'] == game_id), None)
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
# WALLET SYSTEM
# ============================================================

@app.route('/api/wallet/<pc_id>', methods=['GET'])
def get_wallet(pc_id):
    balance = wallets.get(pc_id, {}).get('balance', 0)
    return jsonify({
        'status': 'ok',
        'pc_id': pc_id,
        'balance': balance,
        'currency': 'TND'
    })

@app.route('/api/wallet/topup', methods=['POST'])
def topup_wallet():
    data = request.json
    pc_id = data.get('pc_id')
    amount = data.get('amount', 0)
    
    if amount <= 0:
        return jsonify({'status': 'error', 'message': 'Amount must be positive'}), 400
    
    if pc_id not in wallets:
        wallets[pc_id] = {'balance': 0, 'transactions': []}
    
    wallets[pc_id]['balance'] += amount
    wallets[pc_id]['transactions'].append({
        'type': 'topup',
        'amount': amount,
        'timestamp': datetime.now().isoformat(),
        'new_balance': wallets[pc_id]['balance']
    })
    
    print(f"[WALLET] {pc_id} topped up {amount} TND (Balance: {wallets[pc_id]['balance']})")
    return jsonify({
        'status': 'ok',
        'pc_id': pc_id,
        'new_balance': wallets[pc_id]['balance']
    })

# ============================================================
# MEMBERSHIP PLANS
# ============================================================

MEMBERSHIP_PLANS = {
    'basic': {'name': 'Basic', 'price': 10, 'hours': 5, 'color': '#43b581'},
    'premium': {'name': 'Premium', 'price': 25, 'hours': 15, 'color': '#faa61a'},
    'pro': {'name': 'Pro', 'price': 50, 'hours': 40, 'color': '#f04747'}
}

@app.route('/api/membership/plans', methods=['GET'])
def get_membership_plans():
    return jsonify({'status': 'ok', 'plans': MEMBERSHIP_PLANS})

@app.route('/api/membership/<pc_id>', methods=['GET'])
def get_membership(pc_id):
    return jsonify({
        'status': 'ok',
        'pc_id': pc_id,
        'membership': memberships.get(pc_id, {})
    })

@app.route('/api/membership/buy', methods=['POST'])
def buy_membership():
    data = request.json
    pc_id = data.get('pc_id')
    plan = data.get('plan')
    
    if plan not in MEMBERSHIP_PLANS:
        return jsonify({'status': 'error', 'message': 'Invalid plan'}), 400
    
    plan_data = MEMBERSHIP_PLANS[plan]
    
    memberships[pc_id] = {
        'plan': plan,
        'plan_name': plan_data['name'],
        'hours_left': plan_data['hours'],
        'purchase_date': datetime.now().isoformat(),
        'expiry_date': (datetime.now() + timedelta(days=30)).isoformat()
    }
    
    if pc_id not in wallets:
        wallets[pc_id] = {'balance': 0, 'transactions': []}
    
    wallets[pc_id]['balance'] -= plan_data['price']
    wallets[pc_id]['transactions'].append({
        'type': 'membership',
        'plan': plan,
        'amount': -plan_data['price'],
        'timestamp': datetime.now().isoformat(),
        'new_balance': wallets[pc_id]['balance']
    })
    
    return jsonify({'status': 'ok', 'membership': memberships[pc_id]})

# ============================================================
# RESERVATION SYSTEM
# ============================================================

@app.route('/api/reservations', methods=['GET'])
def get_reservations():
    now = datetime.now().isoformat()
    upcoming = [r for r in reservations if r.get('end_time', '') > now and r.get('status') == 'pending']
    return jsonify({
        'status': 'ok',
        'reservations': upcoming,
        'total': len(upcoming)
    })

@app.route('/api/reservations/create', methods=['POST'])
def create_reservation():
    data = request.json
    pc_id = data.get('pc_id')
    user_name = data.get('user_name', 'Anonymous')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not pc_id or not start_time or not end_time:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    for r in reservations:
        if r['pc_id'] == pc_id and r['status'] == 'pending':
            if r['start_time'] < end_time and r['end_time'] > start_time:
                return jsonify({'status': 'error', 'message': 'PC already reserved'}), 400
    
    reservation = {
        'id': len(reservations) + 1,
        'pc_id': pc_id,
        'user_name': user_name,
        'start_time': start_time,
        'end_time': end_time,
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    
    reservations.append(reservation)
    return jsonify({'status': 'ok', 'reservation': reservation})

@app.route('/api/reservations/<int:reservation_id>/cancel', methods=['POST'])
def cancel_reservation(reservation_id):
    for r in reservations:
        if r['id'] == reservation_id:
            r['status'] = 'cancelled'
            r['cancelled_at'] = datetime.now().isoformat()
            return jsonify({'status': 'ok', 'message': 'Reservation cancelled'})
    
    return jsonify({'status': 'error', 'message': 'Reservation not found'}), 404

# ============================================================
# MULTI-BRANCH SUPPORT
# ============================================================

@app.route('/api/branches', methods=['GET'])
def get_branches():
    return jsonify({'status': 'ok', 'branches': branches})

@app.route('/api/branches', methods=['POST'])
def create_branch():
    data = request.json
    branch_id = data.get('branch_id')
    name = data.get('name')
    address = data.get('address', '')
    
    if not branch_id or not name:
        return jsonify({'status': 'error', 'message': 'Branch ID and name required'}), 400
    
    if branch_id in branches:
        return jsonify({'status': 'error', 'message': 'Branch already exists'}), 400
    
    branches[branch_id] = {'name': name, 'address': address, 'pcs': []}
    return jsonify({'status': 'ok', 'branch': branches[branch_id]})

# ============================================================
# HEARTBEAT & TELEMETRY
# ============================================================

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    
    pc_id = data.get('pc_id') or data.get('mac_address')
    if not pc_id:
        return jsonify({'status': 'error', 'message': 'No PC ID'}), 400
    
    # ============================================================
    # DEBUG: Log what we received
    # ============================================================
    print(f"[DEBUG] Received data from {pc_id}")
    print(f"[DEBUG] Keys: {list(data.keys())}")
    
    # ============================================================
    # CHECK: Is this telemetry data? (has 'features')
    # ============================================================
    if 'features' in data:
        # This is telemetry - extract the data!
        features = data.get('features', {})
        
        print(f"[DEBUG] Features keys: {list(features.keys())}")
        print(f"[DEBUG] CPU: {features.get('cpu_usage', 0)}%")
        print(f"[DEBUG] RAM: {features.get('ram_usage', 0)}%")
        print(f"[DEBUG] GPU: {features.get('gpu_usage', 0)}%")
        print(f"[DEBUG] Game: {features.get('process_name', 'none')}")
        
        # Initialize PC if needed
        if pc_id not in pcs:
            pcs[pc_id] = {}
        
        # Get existing hostname if available
        existing_hostname = pcs[pc_id].get('hostname', 'Unknown')
        
        # Update with telemetry data
        pcs[pc_id].update({
            'status': 'online',
            'last_telemetry': datetime.now().isoformat(),
            'cpu': features.get('cpu_usage', 0),
            'ram': features.get('ram_usage', 0),
            'gpu': features.get('gpu_usage', 0),
            'cpu_temp': features.get('cpu_temperature', 0),
            'game': features.get('process_name', 'none'),
            'window_title': features.get('window_title', ''),
            'is_fullscreen': features.get('is_fullscreen', 0),
            'hostname': existing_hostname  # Keep existing hostname
        })
        
        # Also update heartbeat for backward compatibility
        if 'heartbeat' not in pcs[pc_id]:
            pcs[pc_id]['heartbeat'] = {}
        pcs[pc_id]['heartbeat'].update({
            'cpu_usage': features.get('cpu_usage', 0),
            'ram_usage': features.get('ram_usage', 0),
            'gpu_usage': features.get('gpu_usage', 0),
            'cpu_temp': features.get('cpu_temperature', 0),
            'active_game': features.get('process_name', 'none')
        })
        
        print(f"[TELEMETRY] {pc_id} - CPU: {features.get('cpu_usage', 0)}% RAM: {features.get('ram_usage', 0)}%")
        
        return jsonify({'status': 'ok'})
    
    # ============================================================
    # This is a simple heartbeat (no 'features')
    # ============================================================
    client_ip = request.remote_addr
    hostname = data.get('hostname', 'unknown')
    
    if pc_id not in pcs:
        pcs[pc_id] = {}
    
    # Only update status, don't overwrite CPU/RAM
    pcs[pc_id].update({
        'status': 'online',
        'last_heartbeat': datetime.now().isoformat(),
        'hostname': hostname,
        'current_ip': client_ip
    })
    
    print(f"[HEARTBEAT] {hostname} ({pc_id}) - Status: online")
    
    return jsonify({'status': 'ok'})
# ============================================================
# SESSION MANAGEMENT
# ============================================================

@app.route('/api/session/start', methods=['POST'])
def start_session():
    data = request.json
    pc_id = data.get('pc_id')
    user_name = data.get('user_name', 'Player')
    session_type = data.get('session_type', 'time')
    
    if not pc_id:
        return jsonify({'status': 'error', 'message': 'PC ID required'}), 400
    
    if pc_id in sessions and sessions[pc_id].get('status') == 'active':
        return jsonify({'status': 'error', 'message': 'PC already in session'}), 400
    
    current_game = 'unknown'
    if pc_id in pcs:
        telemetry = pcs[pc_id].get('telemetry', {})
        current_game = telemetry.get('process_name', telemetry.get('active_game', 'unknown'))
    
    sessions[pc_id] = {
        'user': user_name,
        'start_time': datetime.now().isoformat(),
        'game': current_game,
        'game_type': session_type,
        'status': 'active',
        'price_per_minute': 0.10
    }
    
    if pc_id not in pending_commands:
        pending_commands[pc_id] = []
    
    pending_commands[pc_id].append({
        'action': 'START_SESSION',
        'parameter': user_name
    })
    
    print(f"[SESSION START] {pc_id}: {user_name} - Game: {current_game}")
    
    return jsonify({
        'status': 'ok',
        'message': f'Session started for {user_name}',
        'session': sessions[pc_id]
    })

@app.route('/api/session/end', methods=['POST'])
def end_session():
    data = request.json
    pc_id = data.get('pc_id')
    
    if not pc_id:
        return jsonify({'status': 'error', 'message': 'PC ID required'}), 400
    
    if pc_id not in sessions or sessions[pc_id].get('status') != 'active':
        return jsonify({'status': 'error', 'message': 'No active session'}), 400
    
    session = sessions[pc_id]
    start = datetime.fromisoformat(session['start_time'])
    end = datetime.now()
    
    duration_seconds = (end - start).total_seconds()
    duration_minutes = round(duration_seconds / 60, 2)
    cost = round(duration_minutes * session.get('price_per_minute', 0.10), 2)
    
    session_history.append({
        'pc_id': pc_id,
        'user': session['user'],
        'start_time': session['start_time'],
        'end_time': end.isoformat(),
        'duration_minutes': duration_minutes,
        'game': session.get('game', 'unknown'),
        'session_type': session.get('game_type', 'time'),
        'cost': cost
    })
    
    sessions[pc_id]['status'] = 'ended'
    sessions[pc_id]['duration'] = duration_minutes
    sessions[pc_id]['cost'] = cost
    
    if pc_id not in pending_commands:
        pending_commands[pc_id] = []
    
    pending_commands[pc_id].append({
        'action': 'END_SESSION',
        'parameter': ''
    })
    
    return jsonify({
        'status': 'ok',
        'message': 'Session ended',
        'session': {
            'user': session['user'],
            'duration_minutes': duration_minutes,
            'cost': cost,
            'game': session.get('game', 'unknown'),
            'session_type': session.get('game_type', 'time')
        }
    })

@app.route('/api/session/status/<pc_id>', methods=['GET'])
def get_session_status(pc_id):
    if pc_id in sessions:
        return jsonify({
            'pc_id': pc_id,
            'session': sessions[pc_id]
        })
    return jsonify({
        'pc_id': pc_id,
        'session': None
    })

@app.route('/api/session/history', methods=['GET'])
def get_session_history():
    limit = request.args.get('limit', 50, type=int)
    return jsonify({
        'status': 'ok',
        'history': session_history[-limit:],
        'total': len(session_history)
    })

# ============================================================
# COMMANDS
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
# ANTI-THEFT ALERTS
# ============================================================

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    return jsonify({
        'status': 'ok',
        'alerts': usb_alerts[-20:],
        'total': len(usb_alerts)
    })

@app.route('/api/alerts/clear', methods=['POST'])
def clear_alerts():
    global usb_alerts
    usb_alerts = []
    return jsonify({'status': 'ok'})

# ============================================================
# PC DATA ENDPOINTS
# ============================================================

@app.route('/api/pcs', methods=['GET'])
def get_pcs():
    result = []
    for pc_id, pc_data in pcs.items():
        heartbeat = pc_data.get('heartbeat', {})
        telemetry = pc_data.get('telemetry', {})
        is_in_session = pc_id in sessions and sessions[pc_id].get('status') == 'active'
        session = sessions.get(pc_id, None)
        
        game = telemetry.get('process_name', heartbeat.get('active_game', 'none'))
        if game == 'none' or game == '':
            game = heartbeat.get('active_game', 'none')
        
        if is_in_session and session:
            game = session.get('game', game)
        
        result.append({
            'id': pc_id,
            'mac_address': pc_id,
            'hostname': pc_data.get('hostname', 'Unknown'),
            'online': pc_data.get('status', 'offline') == 'online',
            'in_session': is_in_session,
            'game': game,
            'session': session,
            'session_type': session.get('game_type', 'none') if session else 'none',
            'status': heartbeat.get('status', 'online'),
            'cpu': heartbeat.get('cpu_usage', 0),
            'ram': heartbeat.get('ram_usage', 0),
            'gpu': heartbeat.get('gpu_usage', 0),
            'cpu_temp': heartbeat.get('cpu_temp', 0),
            'gpu_temp': heartbeat.get('gpu_temp', 0),
            'ip_address': pc_data.get('current_ip', heartbeat.get('ip_address', '')),
            'hardware': heartbeat.get('hardware', {}),
            'wallet_balance': wallets.get(pc_id, {}).get('balance', 0),
            'membership': memberships.get(pc_id, {}),
            'branch': pc_data.get('branch', 'main')
        })
    
    return jsonify({
        'status': 'ok',
        'pcs': result,
        'active_sessions': len([s for s in sessions.values() if s.get('status') == 'active'])
    })

@app.route('/api/pc/<pc_id>', methods=['GET'])
def get_pc_details(pc_id):
    if pc_id not in pcs:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404
    
    pc_data = pcs[pc_id]
    heartbeat = pc_data.get('heartbeat', {})
    telemetry = pc_data.get('telemetry', {})
    
    is_in_session = pc_id in sessions and sessions[pc_id].get('status') == 'active'
    session = sessions.get(pc_id, None)
    
    game = heartbeat.get('active_game', 'none')
    if game == 'none' or game == '':
        game = 'Aucun jeu'
    
    if is_in_session and session:
        game = session.get('game', game)
    
    return jsonify({
        'id': pc_id,
        'mac_address': pc_id,
        'hostname': heartbeat.get('hostname', 'Unknown'),
        'online': pc_data.get('status', 'offline') == 'online',
        'in_session': is_in_session,
        'game': game,
        'session': session,
        'status': heartbeat.get('status', 'online'),
        'last_heartbeat': pc_data.get('last_heartbeat'),
        'cpu': heartbeat.get('cpu_usage', 0),
        'ram': heartbeat.get('ram_usage', 0),
        'gpu': heartbeat.get('gpu_usage', 0),
        'cpu_temp': heartbeat.get('cpu_temp', 0),
        'gpu_temp': heartbeat.get('gpu_temp', 0),
        'ip_address': pc_data.get('current_ip', heartbeat.get('ip_address', '')),
        'hardware': heartbeat.get('hardware', {}),
        'wallet_balance': wallets.get(pc_id, {}).get('balance', 0),
        'membership': memberships.get(pc_id, {}),
        'branch': pc_data.get('branch', 'main')
    })

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
    print("   NINETY GAMING HOUSE - SERVER (NO AUTH)")
    print("=" * 60)
    print(f"🌐 Server running at: http://{SERVER_IP}:{SERVER_PORT}")
    print("=" * 60)
    print("📡 Discovery broadcast on port 9000")
    print("🔄 Broadcasting every 2 seconds")
    print("=" * 60)
    print("🎮 Features (No authentication required):")
    print("   - PC Node Tracking")
    print("   - Session & Financial Control")
    print("   - Remote Administration")
    print("   - Hardware Telemetry")
    print("   - Electronic Wallet")
    print("   - Subscription Plans")
    print("   - Reservation System")
    print("   - Multi-Branch Support")
    print("   - Game Catalog")
    print("   - Anti-Theft Alerts")
    print("=" * 60)
    
    start_discovery()
    
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=True, threaded=True)