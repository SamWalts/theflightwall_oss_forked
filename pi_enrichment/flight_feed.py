"""Bounded, cached local readsb feed. No reference or cloud service is required."""
import json
import math
import re
import sqlite3
import threading
import time
import urllib.request

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


class FlightFeed:
    def __init__(self, store, aircraft_path=None, aircraft_url=None, clock=time.time):
        self.store = store
        self.aircraft_path = aircraft_path
        self.aircraft_url = aircraft_url
        self.clock = clock
        self._lock = threading.Lock()
        self._loaded_at = float('-inf')
        self._snapshot = None

    def _load(self):
        with self._lock:
            current = self.clock()
            if current - self._loaded_at < 1:
                return self._snapshot
            self._loaded_at = current
            try:
                if self.aircraft_path:
                    source = open(self.aircraft_path, 'rb')
                else:
                    source = urllib.request.urlopen(self.aircraft_url, timeout=2)
                with source:
                    raw = source.read(MAX_SNAPSHOT_BYTES + 1)
                if len(raw) > MAX_SNAPSHOT_BYTES:
                    raise ValueError('snapshot too large')
                payload = json.loads(raw)
                if not isinstance(payload, dict) or number(payload.get('now')) is None or not isinstance(payload.get('aircraft'), list):
                    raise ValueError('invalid snapshot')
                self._snapshot = payload
            except (OSError, ValueError):
                self._snapshot = None
            return self._snapshot

    def flights(self, limit=8):
        now = self.clock()
        snapshot = self._load()
        timestamp = snapshot['now'] if snapshot else None
        status = 'unavailable' if snapshot is None else ('ok' if -1 <= now - timestamp <= 5 else 'stale')
        result = dict(schema_version=1, generated_at=now, receiver_snapshot_at=timestamp,
                      receiver_status=status, flights=[])
        if status != 'ok':
            return result
        for aircraft in snapshot['aircraft']:
            if not isinstance(aircraft, dict):
                continue
            hex_value = aircraft.get('hex', '')
            if not isinstance(hex_value, str) or not re.fullmatch('[0-9a-fA-F]{6}', hex_value):
                continue
            seen = number(aircraft.get('seen'))
            seen_pos = number(aircraft.get('seen_pos'))
            lat, lon = number(aircraft.get('lat')), number(aircraft.get('lon'))
            if seen is None or seen_pos is None or min(seen, seen_pos) < 0:
                continue
            if now - timestamp + max(seen, seen_pos) > 15:
                continue
            if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            try:
                ref = self.store.get_aircraft(hex_value)
            except (OSError, sqlite3.Error):
                ref = {}
            callsign = aircraft.get('flight')
            rate = number(aircraft.get('baro_rate'))
            rate_source = 'barometric' if rate is not None else None
            if rate is None:
                rate = number(aircraft.get('geom_rate'))
                rate_source = 'geometric' if rate is not None else None
            def text(key):
                value = aircraft.get(key)
                return value.strip() if isinstance(value, str) else None
            result['flights'].append(dict(
                adsb_icao=hex_value.upper(), callsign=callsign.strip() if isinstance(callsign, str) else None,
                lat=lat, lon=lon, last_seen_at=timestamp-seen, position_seen_at=timestamp-seen_pos,
                on_ground=aircraft.get('alt_baro') == 'ground',
                altitude_baro_ft=number(aircraft.get('alt_baro')), altitude_geom_ft=number(aircraft.get('alt_geom')),
                ground_speed_kt=number(aircraft.get('gs')), airspeed_ias_kt=number(aircraft.get('ias')),
                airspeed_tas_kt=number(aircraft.get('tas')), vertical_speed_fpm=rate, vertical_speed_source=rate_source,
                registration=text('r') or ref.get('registration') or None,
                aircraft_type=text('t'), aircraft_model=text('desc') or ref.get('aircraft_model') or None,
                aircraft_reference_source='readsb' if text('t') or text('desc') else ('faa_registry' if ref.get('found') else None),
                # Registered owner is not evidence of the operating airline.
                operator_name=None, operator_icao=None, operator_resolution_source=None,
                origin=None, destination=None, logo_path=None))
            if len(result['flights']) >= max(1, min(limit, 8)):
                break
        return result
