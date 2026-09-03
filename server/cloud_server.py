# server_cloud.py - Cloud Reservation Service
# Deploy this on Railway / VPS for public access

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import uuid
import requests

app = Flask(__name__)
CORS(app)

# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/cloud_db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ============================================================
# MODELS
# ============================================================

class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pc_id = db.Column(db.String(50), nullable=False)
    center_id = db.Column(db.String(50), default='main')
    
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(100), nullable=False)
    user_phone = db.Column(db.String(20))
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    
    # Sync tracking
    synced = db.Column(db.Boolean, default=False)  # Synced with local center
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
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'synced': self.synced,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

with app.app_context():
    db.create_all()
    print("[DB] ✅ Cloud database tables created")

# ============================================================
# PUBLIC ENDPOINTS (Clients from anywhere)
# ============================================================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'ok',
        'service': 'Ninety Gaming House - Cloud Reservation Service',
        'version': '1.0.0',
        'endpoints': {
            'GET /api/pcs': 'Get available PCs',
            'POST /api/reservations/create': 'Create a reservation',
            'GET /api/reservations/<id>': 'Get reservation details',
            'POST /api/reservations/cancel/<id>': 'Cancel a reservation',
            'GET /api/sync/center/<center_id>': 'Sync reservations with local center',
            'POST /api/sync/confirm': 'Confirm sync'
        }
    })

@app.route('/api/pcs', methods=['GET'])
def get_pcs():
    """Get all available PCs (public)"""
    # For now, return a list of available PCs
    # In production, you might want to sync this from local centers
    pcs = [
        {'id': 'PC-001', 'hostname': 'Gaming PC 1', 'status': 'online'},
        {'id': 'PC-002', 'hostname': 'Gaming PC 2', 'status': 'online'},
        {'id': 'PC-003', 'hostname': 'Gaming PC 3', 'status': 'online'},
        {'id': 'PC-004', 'hostname': 'Gaming PC 4', 'status': 'online'},
        {'id': 'PC-005', 'hostname': 'Gaming PC 5', 'status': 'online'},
    ]
    return jsonify({
        'status': 'ok',
        'pcs': pcs,
        'total': len(pcs)
    })

@app.route('/api/reservations/check-availability', methods=['POST'])
def check_availability():
    """Check if a PC is available at a given time"""
    data = request.json
    pc_id = data.get('pc_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not pc_id or not start_time or not end_time:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except:
        return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400
    
    # Check existing reservations
    existing = Reservation.query.filter_by(
        pc_id=pc_id,
        status='pending'
    ).filter(
        Reservation.start_time < end,
        Reservation.end_time > start
    ).all()
    
    return jsonify({
        'status': 'ok',
        'available': len(existing) == 0,
        'conflicts': len(existing)
    })

@app.route('/api/reservations/create', methods=['POST'])
def create_reservation():
    """Public endpoint - Clients book from home"""
    data = request.json
    
    pc_id = data.get('pc_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    user_name = data.get('user_name')
    user_email = data.get('user_email')
    user_phone = data.get('user_phone', '')
    center_id = data.get('center_id', 'main')
    
    # Validation
    if not all([pc_id, start_time, end_time, user_name, user_email]):
        return jsonify({
            'status': 'error', 
            'message': 'Missing required fields: pc_id, start_time, end_time, user_name, user_email'
        }), 400
    
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM:SS'}), 400
    
    if start >= end:
        return jsonify({'status': 'error', 'message': 'End time must be after start time'}), 400
    
    # Check availability
    existing = Reservation.query.filter_by(
        pc_id=pc_id,
        status='pending'
    ).filter(
        Reservation.start_time < end,
        Reservation.end_time > start
    ).all()
    
    if existing:
        return jsonify({
            'status': 'error', 
            'message': 'PC not available at this time',
            'conflicts': len(existing)
        }), 400
    
    # Create reservation
    reservation = Reservation(
        pc_id=pc_id,
        center_id=center_id,
        user_name=user_name,
        user_email=user_email,
        user_phone=user_phone,
        start_time=start,
        end_time=end,
        status='pending',
        synced=False
    )
    db.session.add(reservation)
    db.session.commit()
    
    print(f"[RESERVATION] New reservation: {reservation.id} - {user_name} - PC: {pc_id}")
    
    return jsonify({
        'status': 'ok',
        'message': 'Reservation created successfully! Please arrive 15 minutes before your session.',
        'reservation': {
            'id': reservation.id,
            'pc_id': reservation.pc_id,
            'user_name': reservation.user_name,
            'user_email': reservation.user_email,
            'start_time': reservation.start_time.isoformat(),
            'end_time': reservation.end_time.isoformat(),
            'status': reservation.status
        }
    }), 201

@app.route('/api/reservations/<reservation_id>', methods=['GET'])
def get_reservation(reservation_id):
    """Get reservation details"""
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({'status': 'error', 'message': 'Reservation not found'}), 404
    
    return jsonify({
        'status': 'ok',
        'reservation': reservation.to_dict()
    })

@app.route('/api/reservations/cancel/<reservation_id>', methods=['POST'])
def cancel_reservation(reservation_id):
    """Cancel a reservation"""
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({'status': 'error', 'message': 'Reservation not found'}), 404
    
    if reservation.status == 'cancelled':
        return jsonify({'status': 'error', 'message': 'Reservation already cancelled'}), 400
    
    reservation.status = 'cancelled'
    db.session.commit()
    
    print(f"[RESERVATION] Cancelled: {reservation_id}")
    
    return jsonify({
        'status': 'ok', 
        'message': 'Reservation cancelled successfully'
    })

@app.route('/api/reservations/center/<center_id>', methods=['GET'])
def get_center_reservations(center_id):
    """Get all reservations for a center (for local sync)"""
    reservations = Reservation.query.filter_by(
        center_id=center_id
    ).order_by(Reservation.start_time).all()
    
    return jsonify({
        'status': 'ok',
        'center_id': center_id,
        'reservations': [r.to_dict() for r in reservations],
        'total': len(reservations)
    })

# ============================================================
# SYNC ENDPOINTS (For Local Gaming Center)
# ============================================================

@app.route('/api/sync/center/<center_id>', methods=['GET'])
def sync_reservations(center_id):
    """Get all unsynced reservations for a center"""
    reservations = Reservation.query.filter_by(
        center_id=center_id,
        synced=False,
        status='pending'
    ).all()
    
    return jsonify({
        'status': 'ok',
        'center_id': center_id,
        'reservations': [r.to_dict() for r in reservations],
        'total': len(reservations)
    })

@app.route('/api/sync/confirm', methods=['POST'])
def confirm_sync():
    """Mark reservations as synced"""
    data = request.json
    reservation_ids = data.get('reservation_ids', [])
    
    if not reservation_ids:
        return jsonify({'status': 'error', 'message': 'No reservation IDs provided'}), 400
    
    synced_count = 0
    for rid in reservation_ids:
        reservation = Reservation.query.get(rid)
        if reservation and not reservation.synced:
            reservation.synced = True
            reservation.synced_at = datetime.utcnow()
            synced_count += 1
    
    db.session.commit()
    
    print(f"[SYNC] Confirmed {synced_count} reservations")
    
    return jsonify({
        'status': 'ok',
        'synced': synced_count,
        'message': f'Confirmed {synced_count} reservations'
    })

@app.route('/api/sync/all', methods=['POST'])
def sync_all():
    """Sync all reservations (full sync)"""
    data = request.json
    center_id = data.get('center_id', 'main')
    reservations = data.get('reservations', [])
    
    if not reservations:
        return jsonify({'status': 'error', 'message': 'No reservations provided'}), 400
    
    # Update or create reservations
    updated = 0
    for r in reservations:
        existing = Reservation.query.get(r.get('id'))
        if existing:
            # Update existing
            existing.status = r.get('status', existing.status)
            existing.synced = True
            existing.synced_at = datetime.utcnow()
        else:
            # Create new
            new_res = Reservation(
                id=r.get('id'),
                pc_id=r.get('pc_id'),
                center_id=center_id,
                user_name=r.get('user_name'),
                user_email=r.get('user_email'),
                user_phone=r.get('user_phone', ''),
                start_time=datetime.fromisoformat(r.get('start_time')),
                end_time=datetime.fromisoformat(r.get('end_time')),
                status=r.get('status', 'pending'),
                synced=True,
                synced_at=datetime.utcnow()
            )
            db.session.add(new_res)
        updated += 1
    
    db.session.commit()
    
    print(f"[SYNC] Full sync: {updated} reservations updated")
    
    return jsonify({
        'status': 'ok',
        'updated': updated,
        'message': f'Synced {updated} reservations'
    })

# ============================================================
# HEALTH CHECK
# ============================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'cloud-reservations',
        'timestamp': datetime.utcnow().isoformat()
    })

# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("   NINETY GAMING HOUSE - CLOUD RESERVATION SERVICE")
    print("=" * 60)
    print(f"🌐 Running on port: {port}")
    print("=" * 60)
    print("📋 Endpoints:")
    print("   POST /api/reservations/create  - Create reservation")
    print("   GET  /api/reservations/<id>    - Get reservation")
    print("   POST /api/reservations/cancel/<id> - Cancel")
    print("   GET  /api/sync/center/<id>     - Sync with local")
    print("   POST /api/sync/confirm         - Confirm sync")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)