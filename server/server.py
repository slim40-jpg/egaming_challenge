from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Store all PC data in memory
pcs = {}
pending_commands = {}

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Receive heartbeat from agent"""
    data = request.json
    hostname = data.get('hostname')
    
    if not hostname:
        return jsonify({'status': 'error', 'message': 'No hostname'}), 400
    
    pcs[hostname] = {
        'data': data,
        'last_heartbeat': datetime.now().isoformat(),
        'status': data.get('status', 'online')
    }
    
    print(f"[HEARTBEAT] {hostname}: CPU={data.get('cpu_usage')}%, RAM={data.get('ram_usage')}%, GPU={data.get('gpu_usage')}%")
    print(f"   IP: {data.get('ip_address')}")
    
    # DO NOT return or clear commands here - let the agent poll for them
    return jsonify({'status': 'ok'})

@app.route('/api/commands/<hostname>', methods=['GET'])
def get_commands(hostname):
    """Agent polls for commands"""
    print(f"[POLL] Checking commands for {hostname}")
    
    # Get pending commands for this hostname
    commands = []
    if hostname in pending_commands and pending_commands[hostname]:
        commands = pending_commands[hostname]
        # Clear after sending
        pending_commands[hostname] = []
        print(f"[POLL] Sending {len(commands)} command(s) to {hostname}")
        print(f"[POLL] Commands: {commands}")
    else:
        print(f"[POLL] No commands for {hostname}")
    
    # Return as JSON array
    return jsonify(commands)

@app.route('/api/pcs', methods=['GET'])
def get_pcs():
    """Dashboard asks for all PC statuses"""
    now = datetime.now()
    to_remove = []
    for hostname, pc_data in pcs.items():
        try:
            last_time = datetime.fromisoformat(pc_data['last_heartbeat'])
            if (now - last_time).total_seconds() > 60:
                to_remove.append(hostname)
        except:
            to_remove.append(hostname)
    
    for hostname in to_remove:
        del pcs[hostname]
    
    return jsonify(pcs)

@app.route('/api/command', methods=['POST'])
def send_command():
    """Dashboard sends a command to a PC"""
    data = request.json
    hostname = data.get('hostname')
    command = data.get('command')
    parameter = data.get('parameter', '')
    
    if not hostname or not command:
        return jsonify({'status': 'error', 'message': 'Missing hostname or command'}), 400
    
    # Store the command
    if hostname not in pending_commands:
        pending_commands[hostname] = []
    
    cmd_obj = {
        'action': command,
        'parameter': parameter,
        'timestamp': datetime.now().isoformat()
    }
    pending_commands[hostname].append(cmd_obj)
    
    print(f"[COMMAND] Sending {command} to {hostname}" + (f" ({parameter})" if parameter else ""))
    print(f"   Pending commands for {hostname}: {len(pending_commands[hostname])}")
    print(f"   Commands: {pending_commands[hostname]}")
    
    return jsonify({'status': 'ok', 'message': f'Command {command} sent to {hostname}'})

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'running',
        'connected_pcs': len(pcs),
        'pending_commands': sum(len(cmd) for cmd in pending_commands.values())
    })

@app.route('/')
def index():
    return '''<!DOCTYPE html>
    <html>
    <head>
        <title>Gaming Agent Server</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Arial, sans-serif; background: #0a0a1a; color: #fff; min-height: 100vh; padding: 20px; }
            .container { max-width: 1400px; margin: 0 auto; }
            
            .header { 
                background: linear-gradient(135deg, #1a1a2e, #16213e); 
                padding: 25px 30px; 
                border-radius: 15px; 
                margin-bottom: 25px;
                border: 1px solid #2a2a4a;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
            }
            .header h1 { color: #e94560; font-size: 28px; display: flex; align-items: center; gap: 10px; }
            .header-info { display: flex; gap: 30px; flex-wrap: wrap; }
            .header-info .status { color: #00ff88; }
            .header-info .count { color: #ffaa00; font-weight: bold; font-size: 20px; }
            
            .grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
                gap: 20px; 
            }
            
            .pc-card { 
                background: linear-gradient(145deg, #1a1a2e, #0f0f23);
                padding: 20px; 
                border-radius: 15px; 
                border: 1px solid #2a2a4a;
                transition: all 0.3s ease;
            }
            .pc-card:hover { border-color: #e94560; transform: translateY(-2px); box-shadow: 0 10px 30px rgba(233, 69, 96, 0.1); }
            .pc-card.offline { opacity: 0.5; border-color: #444; }
            
            .pc-name { 
                font-size: 22px; 
                font-weight: bold; 
                margin-bottom: 12px;
                color: #fff;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .pc-name .dot { 
                width: 10px; height: 10px; border-radius: 50%; display: inline-block;
            }
            .pc-name .dot.online { background: #00ff88; box-shadow: 0 0 10px #00ff88; }
            .pc-name .dot.offline { background: #ff4444; }
            .pc-name .dot.in_session { background: #ffaa00; box-shadow: 0 0 10px #ffaa00; }
            .pc-name .dot.locked { background: #ff4444; box-shadow: 0 0 10px #ff4444; }
            
            .stat-row { margin: 6px 0; }
            .stat-label { font-size: 13px; color: #888; display: flex; justify-content: space-between; }
            .stat-bar { 
                background: #0a0a1a; 
                border-radius: 6px; 
                height: 8px; 
                margin: 2px 0 8px 0; 
                overflow: hidden; 
            }
            .stat-fill { height: 100%; border-radius: 6px; transition: width 0.8s ease; }
            .stat-fill.cpu { background: linear-gradient(90deg, #00ff88, #00cc66); }
            .stat-fill.ram { background: linear-gradient(90deg, #ffaa00, #ff8800); }
            .stat-fill.gpu { background: linear-gradient(90deg, #e94560, #c0392b); }
            
            .last-seen { font-size: 11px; color: #555; margin-top: 8px; }
            
            .actions { 
                margin-top: 14px; 
                display: flex; 
                gap: 6px; 
                flex-wrap: wrap;
                border-top: 1px solid #1a1a2e;
                padding-top: 14px;
            }
            .btn { 
                background: #1a1a2e; 
                color: #fff; 
                border: 1px solid #333; 
                padding: 6px 14px; 
                border-radius: 6px; 
                cursor: pointer; 
                font-size: 12px;
                font-weight: 600;
                transition: all 0.2s ease;
            }
            .btn:hover { background: #2a2a4a; transform: scale(1.02); }
            .btn.lock { border-color: #ffaa00; color: #ffaa00; }
            .btn.lock:hover { background: #ffaa0022; }
            .btn.start { border-color: #00ff88; color: #00ff88; }
            .btn.start:hover { background: #00ff8822; }
            .btn.end { border-color: #ff6666; color: #ff6666; }
            .btn.end:hover { background: #ff666622; }
            .btn.shutdown { border-color: #ff2222; color: #ff2222; }
            .btn.shutdown:hover { background: #ff222222; }
            .btn.restart { border-color: #44aaff; color: #44aaff; }
            .btn.restart:hover { background: #44aaff22; }
            
            .empty { text-align: center; padding: 60px 20px; color: #555; }
            .empty h2 { font-size: 24px; margin-bottom: 10px; }
            .empty p { font-size: 16px; }
            
            @media (max-width: 600px) {
                .header { flex-direction: column; align-items: stretch; gap: 10px; }
                .header-info { justify-content: space-between; }
                .grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1><span>🎮</span> Gaming Agent Server</h1>
                <div class="header-info">
                    <div><span class="status">●</span> Running</div>
                    <div>PCs: <span class="count" id="pcCount">0</span></div>
                </div>
            </div>
            <div id="pcs" class="grid"></div>
        </div>
        <script>
            function fetchPCs() {
                fetch('/api/pcs')
                    .then(response => response.json())
                    .then(data => {
                        const count = Object.keys(data).length;
                        document.getElementById('pcCount').textContent = count;
                        
                        const container = document.getElementById('pcs');
                        container.innerHTML = '';
                        
                        if (count === 0) {
                            container.innerHTML = `<div class="empty"><h2>🖥️ No PCs Connected</h2><p>Waiting for agents to connect...</p></div>`;
                            return;
                        }
                        
                        for (const [hostname, pc] of Object.entries(data)) {
                            const cpu = pc.data?.cpu_usage || 0;
                            const ram = pc.data?.ram_usage || 0;
                            const gpu = pc.data?.gpu_usage || 0;
                            const status = pc.status || 'offline';
                            const lastSeen = new Date(pc.last_heartbeat).toLocaleTimeString();
                            
                            const dotClass = status === 'online' ? 'online' : status === 'in_session' ? 'in_session' : status === 'locked' ? 'locked' : 'offline';
                            
                            const div = document.createElement('div');
                            div.className = 'pc-card' + (status === 'offline' ? ' offline' : '');
                            div.innerHTML = `
                                <div class="pc-name"><span class="dot ${dotClass}"></span>${hostname}<span style="font-size:13px;color:#888;font-weight:normal;margin-left:auto;">${status}</span></div>
                                <div class="stat-row"><div class="stat-label"><span>CPU</span><span>${cpu}%</span></div><div class="stat-bar"><div class="stat-fill cpu" style="width:${Math.min(cpu, 100)}%"></div></div></div>
                                <div class="stat-row"><div class="stat-label"><span>RAM</span><span>${ram}%</span></div><div class="stat-bar"><div class="stat-fill ram" style="width:${Math.min(ram, 100)}%"></div></div></div>
                                <div class="stat-row"><div class="stat-label"><span>GPU</span><span>${gpu}%</span></div><div class="stat-bar"><div class="stat-fill gpu" style="width:${Math.min(gpu, 100)}%"></div></div></div>
                                <div class="last-seen">Last seen: ${lastSeen}</div>
                                <div class="actions">
                                    <button class="btn lock" onclick="sendCommand('${hostname}','LOCK')">🔒 Lock</button>
                                    <button class="btn start" onclick="sendCommand('${hostname}','START_SESSION','Player')">▶ Start</button>
                                    <button class="btn end" onclick="sendCommand('${hostname}','END_SESSION')">⏹ End</button>
                                    <button class="btn restart" onclick="sendCommand('${hostname}','RESTART')">🔄 Restart</button>
                                    <button class="btn shutdown" onclick="sendCommand('${hostname}','SHUTDOWN')">⏻ Shutdown</button>
                                </div>
                            `;
                            container.appendChild(div);
                        }
                    })
                    .catch(err => console.error('Error:', err));
            }
            
            function sendCommand(hostname, command, parameter = '') {
                if (command === 'SHUTDOWN' && !confirm('⚠️ Shutdown ' + hostname + '?')) return;
                if (command === 'RESTART' && !confirm('⚠️ Restart ' + hostname + '?')) return;
                
                fetch('/api/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hostname, command, parameter })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                        showToast('✅ Command "' + command + '" sent', 'success');
                    } else {
                        showToast('❌ Error: ' + data.message, 'error');
                    }
                })
                .catch(err => showToast('❌ Error: ' + err.message, 'error'));
            }
            
            function showToast(message, type) {
                const toast = document.createElement('div');
                toast.style.cssText = `
                    position: fixed; bottom: 20px; right: 20px; 
                    padding: 15px 25px; border-radius: 10px; 
                    color: #fff; font-weight: 600; font-size: 14px;
                    z-index: 1000; max-width: 400px;
                    animation: slideIn 0.3s ease;
                    background: ${type === 'success' ? '#00cc66' : '#e94560'};
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                `;
                toast.textContent = message;
                document.body.appendChild(toast);
                setTimeout(() => {
                    toast.style.opacity = '0';
                    toast.style.transition = 'opacity 0.5s ease';
                    setTimeout(() => toast.remove(), 500);
                }, 3000);
            }
            
            const style = document.createElement('style');
            style.textContent = `@keyframes slideIn { from { transform: translateX(100px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`;
            document.head.appendChild(style);
            
            fetchPCs();
            setInterval(fetchPCs, 3000);
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("=" * 50)
    print("   GAMING AGENT SERVER")
    print("=" * 50)
    print("Server running at: http://localhost:8000")
    print("Wait for agents to connect...")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8000, debug=False)