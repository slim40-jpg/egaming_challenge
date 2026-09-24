"""
Background sync client — runs inside the local Flask process as a thread.
• Every SYNC_INTERVAL_STATUS seconds → push PC snapshots to the cloud.
• Every SYNC_INTERVAL_RESERVATIONS seconds → pull changed reservations.
"""
import os
import time
import threading
import logging
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
load_dotenv()
from models import db, PC, Reservation, SyncState
from state_machine import snapshot_pc

log = logging.getLogger('sync')
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')


CLOUD_API_URL = os.getenv('CLOUD_API_URL', '').rstrip('/')
CENTER_ID = os.getenv('CENTER_ID', 'main')
CENTER_API_KEY = os.getenv('CENTER_API_KEY', '')
SYNC_STATUS_INTERVAL = int(os.getenv('SYNC_INTERVAL_STATUS', '10'))
SYNC_RES_INTERVAL = int(os.getenv('SYNC_INTERVAL_RESERVATIONS', '5'))

HEADERS = {
    'Authorization': f'Bearer {CENTER_API_KEY}',
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
}


def _get_last_res_sync(app):
    with app.app_context():
        row = SyncState.query.get('last_reservation_sync')
        if not row:
            return None
        return row.value


def _set_last_res_sync(app, ts_iso):
    with app.app_context():
        row = SyncState.query.get('last_reservation_sync')
        if not row:
            row = SyncState(key='last_reservation_sync', value=ts_iso)
            db.session.add(row)
        else:
            row.value = ts_iso
        db.session.commit()


def push_status(app):
    """Send minimal PC snapshot to cloud."""
    with app.app_context():
        pcs = PC.query.all()
        payload = {
            'center_id': CENTER_ID,
            'pcs': [snapshot_pc(p) for p in pcs],
        }

    try:
        r = requests.post(
            f'{CLOUD_API_URL}/api/sync/center/{CENTER_ID}',
            json=payload, headers=HEADERS, timeout=8,
        )
        if r.status_code == 200:
            log.info(f'↑ status pushed ({len(payload["pcs"])} pcs)')
        else:
            log.warning(f'↑ status push failed: {r.status_code} {r.text[:200]}')
    except requests.RequestException as e:
        log.warning(f'↑ status push error: {e}')


def pull_reservations(app):
    """Fetch changed reservations from cloud and upsert locally."""
    since = _get_last_res_sync(app)
    url = f'{CLOUD_API_URL}/api/sync/center/{CENTER_ID}/reservations'
    params = {'since': since} if since else {}

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=8)
    except requests.RequestException as e:
        log.warning(f'↓ reservation pull error: {e}')
        return

    if r.status_code != 200:
        log.warning(f'↓ reservation pull failed: {r.status_code} {r.text[:200]}')
        return

    data = r.json()
    reservations = data.get('reservations') or []
    server_time = data.get('server_time')

    with app.app_context():
        for entry in reservations:
            row = Reservation.query.get(entry['id'])
            if not row:
                row = Reservation(id=entry['id'])
                db.session.add(row)
            row.pc_id = entry['pc_id']
            row.user_name = entry.get('username')
            row.start_time = datetime.fromisoformat(entry['start_time'])
            row.end_time = datetime.fromisoformat(entry['end_time'])
            row.status = entry['status']
            row.updated_at = datetime.utcnow()
        db.session.commit()

    if server_time:
        _set_last_res_sync(app, server_time)

    if reservations:
        log.info(f'↓ pulled {len(reservations)} reservation(s)')


def _status_loop(app):
    while True:
        try:
            push_status(app)
        except Exception as e:
            log.exception(f'status loop error: {e}')
        time.sleep(SYNC_STATUS_INTERVAL)


def _reservation_loop(app):
    while True:
        try:
            pull_reservations(app)
        except Exception as e:
            log.exception(f'reservation loop error: {e}')
        time.sleep(SYNC_RES_INTERVAL)


def start_sync_threads(app):
    threading.Thread(target=_status_loop, args=(app,), daemon=True).start()
    threading.Thread(target=_reservation_loop, args=(app,), daemon=True).start()
    log.info(f'sync threads started (status every {SYNC_STATUS_INTERVAL}s, '
             f'reservations every {SYNC_RES_INTERVAL}s)')