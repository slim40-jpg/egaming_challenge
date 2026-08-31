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
# INSTALLED GAMES ENDPOINTS - FIXED
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
        
        # Initialize PC if needed
        if pc_id not in pcs:
            pcs[pc_id] = {
                'hostname': hostname,
                'first_seen': datetime.now().isoformat()
            }
        
        # Store installed games with full paths - MAKE A COPY
        stored_games = []
        for game in games:
            # Ensure we keep all fields
            stored_game = {
                'name': game.get('name', 'Unknown'),
                'executable': game.get('executable', game.get('executable_path', '')),
                'executable_path': game.get('executable', game.get('executable_path', '')),  # Keep both
                'shortcut': game.get('shortcut', game.get('shortcut_path', '')),
                'shortcut_path': game.get('shortcut', game.get('shortcut_path', '')),  # Keep both
                'platform': game.get('platform', 'standalone'),
                'is_running': game.get('is_running', False)
            }
            stored_games.append(stored_game)
        
        pcs[pc_id]['installed_games'] = stored_games
        pcs[pc_id]['last_game_scan'] = datetime.now().isoformat()
        
        print(f"[GAMES] {pc_id} - Found {len(stored_games)} games")
        for game in stored_games:
            status = "🟢 RUNNING" if game.get('is_running') else "⏸️"
            exe_path = game.get('executable_path', game.get('executable', 'NO_PATH'))
            print(f"  - {game.get('name')} ({game.get('platform', 'standalone')}) {status}")
            print(f"      EXE: {exe_path}")
        
        return jsonify({'status': 'ok', 'message': f'Received {len(stored_games)} games'})
    
    except Exception as e:
        print(f"[ERROR] Failed to receive games: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/pc/<pc_id>/games', methods=['GET'])
def get_pc_games(pc_id):
    if pc_id not in pcs:
        return jsonify({'status': 'error', 'message': 'PC not found'}), 404
    
    games = pcs[pc_id].get('installed_games', [])
    
    # Ensure each game has executable_path
    for game in games:
        if 'executable_path' not in game or not game['executable_path']:
            game['executable_path'] = game.get('executable', '')
        if 'shortcut_path' not in game or not game['shortcut_path']:
            game['shortcut_path'] = game.get('shortcut', '')
    
    return jsonify({
        'status': 'ok',
        'pc_id': pc_id,
        'games': games,
        'total': len(games),
        'last_scan': pcs[pc_id].get('last_game_scan')
    })

@app.route('/api/games/launch-installed', methods=['POST'])
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
        
        if not executable:
            return jsonify({'status': 'error', 'message': 'Missing executable path'}), 400
        
        if pc_id not in pcs:
            return jsonify({'status': 'error', 'message': 'PC not found'}), 404
        
        # Find the game in installed games to verify
        games = pcs[pc_id].get('installed_games', [])
        game_found = None
        for g in games:
            if g.get('name') == game_name:
                game_found = g
                break
        
        if game_found:
            # Use the stored path if available
            stored_executable = game_found.get('executable_path', game_found.get('executable', ''))
            if stored_executable:
                executable = stored_executable
                print(f"[GAME LAUNCH] Using stored path: {executable}")
        
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
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
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
    
    # Extract hostname
    hostname = data.get('hostname', 'Unknown')
    if hostname == 'Unknown' and 'features' in data:
        hostname = data['features'].get('hostname', 'Unknown')
    
    # Extract IP address
    ip_address = data.get('ip_address', '')
    if not ip_address and 'features' in data:
        ip_address = data['features'].get('ip_address', '')
    if not ip_address:
        ip_address = request.remote_addr
    
    # Extract hardware
    hardware = data.get('hardware', {})
    if not hardware and 'features' in data:
        features = data['features']
        hardware = {
            'cpu': features.get('cpu_name', 'Unknown CPU'),
            'gpu': features.get('gpu_name', 'Unknown GPU'),
            'ram': features.get('ram_size', 'Unknown RAM')
        }
    
    if 'features' in data:
        features = data.get('features', {})
        
        if pc_id not in pcs:
            pcs[pc_id] = {
                'hostname': hostname,
                'first_seen': datetime.now().isoformat(),
                'hardware': hardware,
                'current_ip': ip_address
            }
        else:
            pcs[pc_id]['hardware'] = hardware if hardware else pcs[pc_id].get('hardware', {})
            pcs[pc_id]['current_ip'] = ip_address
        
        pcs[pc_id].update({
            'status': 'online',
            'last_telemetry': datetime.now().isoformat(),
            'hostname': hostname,
            'cpu': features.get('cpu_usage', 0),
            'ram': features.get('ram_usage', 0),
            'gpu': features.get('gpu_usage', 0),
            'cpu_temp': features.get('cpu_temperature', 0),
            'game': features.get('process_name', 'none'),
            'window_title': features.get('window_title', ''),
            'is_fullscreen': features.get('is_fullscreen', 0),
            'window_width': features.get('window_width', 0),
            'window_height': features.get('window_height', 0),
            'current_ip': ip_address
        })
        
        return jsonify({'status': 'ok'})
    
    # Simple heartbeat
    if hostname == 'Unknown':
        hostname = data.get('hostname', 'unknown')
    
    if pc_id not in pcs:
        pcs[pc_id] = {
            'hostname': hostname,
            'first_seen': datetime.now().isoformat(),
            'hardware': hardware,
            'current_ip': ip_address
        }
    
    pcs[pc_id].update({
        'status': 'online',
        'last_heartbeat': datetime.now().isoformat(),
        'hostname': hostname,
        'current_ip': ip_address,
        'hardware': hardware if hardware else pcs[pc_id].get('hardware', {})
    })
    
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
        current_game = pcs[pc_id].get('game', 'unknown')
    
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
        is_in_session = pc_id in sessions and sessions[pc_id].get('status') == 'active'
        session = sessions.get(pc_id, None)
        
        game = pc_data.get('game', 'none')
        if game == 'none' or game == '':
            game = 'Aucun jeu'
        
        if is_in_session and session:
            game = session.get('game', game)
        
        hardware = pc_data.get('hardware', {})
        ip_address = pc_data.get('current_ip', '')
        
        result.append({
            'id': pc_id,
            'mac_address': pc_id,
            'hostname': pc_data.get('hostname', 'Unknown'),
            'online': pc_data.get('status', 'offline') == 'online',
            'in_session': is_in_session,
            'game': game,
            'session': session,
            'session_type': session.get('game_type', 'none') if session else 'none',
            'status': pc_data.get('status', 'online'),
            'cpu': pc_data.get('cpu', 0),
            'ram': pc_data.get('ram', 0),
            'gpu': pc_data.get('gpu', 0),
            'cpu_temp': pc_data.get('cpu_temp', 0),
            'gpu_temp': pc_data.get('gpu_temp', 0),
            'ip_address': ip_address,
            'hardware': hardware,
            'wallet_balance': wallets.get(pc_id, {}).get('balance', 0),
            'membership': memberships.get(pc_id, {}),
            'branch': pc_data.get('branch', 'main'),
            'installed_games_count': len(pc_data.get('installed_games', []))
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
    
    is_in_session = pc_id in sessions and sessions[pc_id].get('status') == 'active'
    session = sessions.get(pc_id, None)
    
    game = pc_data.get('game', 'none')
    if game == 'none' or game == '':
        game = 'Aucun jeu'
    
    if is_in_session and session:
        game = session.get('game', game)
    
    hardware = pc_data.get('hardware', {})
    ip_address = pc_data.get('current_ip', '')
    
    return jsonify({
        'id': pc_id,
        'mac_address': pc_id,
        'hostname': pc_data.get('hostname', 'Unknown'),
        'online': pc_data.get('status', 'offline') == 'online',
        'in_session': is_in_session,
        'game': game,
        'session': session,
        'status': pc_data.get('status', 'online'),
        'last_heartbeat': pc_data.get('last_heartbeat'),
        'last_telemetry': pc_data.get('last_telemetry'),
        'cpu': pc_data.get('cpu', 0),
        'ram': pc_data.get('ram', 0),
        'gpu': pc_data.get('gpu', 0),
        'cpu_temp': pc_data.get('cpu_temp', 0),
        'gpu_temp': pc_data.get('gpu_temp', 0),
        'ip_address': ip_address,
        'hardware': hardware,
        'wallet_balance': wallets.get(pc_id, {}).get('balance', 0),
        'membership': memberships.get(pc_id, {}),
        'branch': pc_data.get('branch', 'main'),
        'installed_games': pc_data.get('installed_games', [])
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
    print("   - Installed Games Discovery")
    print("=" * 60)
    
    start_discovery()
    
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=True, threaded=True)