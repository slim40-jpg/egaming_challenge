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
from models import db, PC, Reservation, SyncState, User
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

def _get_last_users_sync(app):
    with app.app_context():
        row = SyncState.query.get('last_users_sync')
        if not row:
            return None
        return row.value

def _get_last_pcs_sync(app):
    with app.app_context():
        row = SyncState.query.get('last_pcs_sync')
        if not row:
            return None
        return row.value


def _set_last_pcs_sync(app, ts_iso):
    with app.app_context():
        row = SyncState.query.get('last_pcs_sync')
        if not row:
            row = SyncState(key='last_pcs_sync', value=ts_iso)
            db.session.add(row)
        else:
            row.value = ts_iso
        db.session.commit()


def _set_last_users_sync(app, ts_iso):
    with app.app_context():
        row = SyncState.query.get('last_users_sync')
        if not row:
            row = SyncState(key='last_users_sync', value=ts_iso)
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
        # Cache local users by username to avoid N+1 lookups
        users_by_name = {u.username: u for u in User.query.all()}

        pulled = 0
        skipped = 0
        for entry in reservations:
            # Find the local user by username
            username = entry.get('user_name')
            user = users_by_name.get(username)

            if not user:
                # Try by email as fallback
                email = entry.get('user_email')
                if email:
                    user = next(
                        (u for u in users_by_name.values() if u.email == email),
                        None,
                    )

            if not user:
                log.warning(
                    f'↓ skipping reservation {entry["id"][:8]} — '
                    f'user "{username}" not found locally'
                )
                skipped += 1
                continue

            row = Reservation.query.get(entry['id'])
            if not row:
                row = Reservation(id=entry['id'])
                db.session.add(row)

            row.pc_id = entry['pc_id']
            row.user_id = user.id
            row.user_name = username or user.username
            row.start_time = datetime.fromisoformat(entry['start_time'])
            row.end_time = datetime.fromisoformat(entry['end_time'])
            row.status = entry['status']
            if entry.get('created_at'):
                row.created_at = datetime.fromisoformat(entry['created_at'])
            pulled += 1

        db.session.commit()

    if server_time:
        _set_last_res_sync(app, server_time)

    if pulled or skipped:
        log.info(f'↓ pulled {pulled} reservation(s), skipped {skipped}')

def pull_users(app):
    """Fetch users from cloud and upsert them locally (needed for reservation sync)."""
    since = _get_last_users_sync(app)
    url = f'{CLOUD_API_URL}/api/sync/center/{CENTER_ID}/users'
    params = {'since': since} if since else {}

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=8)
    except requests.RequestException as e:
        log.warning(f'↓ user pull error: {e}')
        return

    if r.status_code != 200:
        log.warning(f'↓ user pull failed: {r.status_code} {r.text[:200]}')
        return

    data = r.json()
    users = data.get('users') or []
    server_time = data.get('server_time')

    with app.app_context():
        created = 0
        updated = 0
        for entry in users:
            username = entry.get('username')
            if not username:
                continue

            row = User.query.filter_by(username=username).first()
            if not row:
                row = User(
                    id=entry['id'],
                    username=username,
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                db.session.add(row)
                created += 1
            else:
                updated += 1

            row.email = entry.get('email')
            # password_hash: only overwrite if the cloud has one
            if entry.get('password_hash'):
                row.password_hash = entry['password_hash']
            row.role = entry.get('role', 'player')

        db.session.commit()

    if server_time:
        _set_last_users_sync(app, server_time)

    if created or updated:
        log.info(f'↓ pulled {created} new, {updated} updated user(s)')

def pull_pcs(app):
    """Fetch PCs from cloud and upsert them locally (needed for reservation FK)."""
    url = f'{CLOUD_API_URL}/api/sync/center/{CENTER_ID}/pcs'

    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
    except requests.RequestException as e:
        log.warning(f'↓ PC pull error: {e}')
        return

    if r.status_code != 200:
        log.warning(f'↓ PC pull failed: {r.status_code} {r.text[:200]}')
        return

    data = r.json()
    pcs = data.get('pcs') or []

    with app.app_context():
        created = 0
        updated = 0
        for entry in pcs:
            pc_id = entry.get('pc_id')
            if not pc_id:
                continue

            row = PC.query.get(pc_id)
            if not row:
                row = PC(id=pc_id)
                db.session.add(row)
                created += 1
            else:
                updated += 1

            # Only update non-telemetry fields — telemetry comes from the agent
            if entry.get('hostname'):
                row.hostname = entry['hostname']
            if entry.get('installed_games') is not None:
                row.installed_games = entry['installed_games']

        db.session.commit()

    if created or updated:
        log.info(f'↓ pulled {created} new, {updated} updated PC(s)')


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

def _user_loop(app):
    while True:
        try:
            pull_users(app)
        except Exception as e:
            log.exception(f'user loop error: {e}')
        time.sleep(30)  # users change rarely — check every 30 seconds

def _pc_loop(app):
    while True:
        try:
            pull_pcs(app)
        except Exception as e:
            log.exception(f'pc loop error: {e}')
        time.sleep(30)

def start_sync_threads(app):
    threading.Thread(target=_user_loop, args=(app,), daemon=True).start()
    threading.Thread(target=_pc_loop, args=(app,), daemon=True).start()
    threading.Thread(target=_status_loop, args=(app,), daemon=True).start()
    threading.Thread(target=_reservation_loop, args=(app,), daemon=True).start()
    log.info(f'sync threads started (users every 30s, PCs every 30s, '
             f'status every {SYNC_STATUS_INTERVAL}s, '
             f'reservations every {SYNC_RES_INTERVAL}s)')