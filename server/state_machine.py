from datetime import datetime, timedelta
from models import PC, Session, Reservation


RESERVATION_BUFFER_MIN = 10  # show "reserved" 10 min before slot


def compute_state(pc: PC) -> str:
    """Return one of: offline | in_session | reserved | available | maintenance."""
    if not pc.online:
        return 'offline'

    # Active session?
    active = Session.query.filter(Session.pc_id == pc.pc_id, Session.status == 'active').first()
    if active:
        return 'in_session'

    # Reserved now (or within buffer)?
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=RESERVATION_BUFFER_MIN)
    res = Reservation.query.filter(
        Reservation.pc_id == pc.pc_id,
        Reservation.status == 'accepted',
        Reservation.start_time <= now,
        Reservation.end_time >= now,
    ).first()
    if res:
        return 'reserved'

    return 'available'


def snapshot_pc(pc: PC) -> dict:
    raw_games = pc.installed_games or []
    game_names = []
    for g in raw_games:
        if isinstance(g, str):
            game_names.append(g)
        elif isinstance(g, dict) and g.get('name'):
            game_names.append(g['name'])

    return {
        'pc_id': pc.pc_id,
        'name': pc.hostname or 'PC',
        'online': bool(pc.online),
        'state': compute_state(pc),
        'installed_games': game_names,
    }