"""Local, bounded VRS lookups. This module never opens a network connection."""

import json
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "vrs_standing_data"
SOURCE_URL = "https://github.com/vradarserver/standing-data"
MAX_STOPS = 128
MAX_AIRPORT_DETAILS = 8
MAX_AIRPORT_NAME = 96
SQLITE_CACHE_KIB = 1024
GENERATION_RE = re.compile(r"[a-f0-9]{12}-[a-f0-9]{32}")
PREFIX_RE = re.compile(r"([A-Z]{2,3}|[A-Z][0-9]|[0-9][A-Z])(\d[A-Z0-9]*)")
NUMBER_RE = re.compile(r"(?:\d{1,4}|\d{1,3}[A-Z]|\d{1,2}[A-Z]{2})")
AIRPORT_RE = re.compile(r"[A-Z0-9]{3,4}")
HEX_RE = re.compile(r"[A-F0-9]{6}")


def utc_now():
    return datetime.now(timezone.utc)


def iso_utc(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def split_callsign(value):
    if not isinstance(value, str) or len(value) > 16:
        return None
    match = PREFIX_RE.fullmatch(value.strip().upper())
    if not match:
        return None
    prefix, number = match.groups()
    number = number.lstrip("0")
    if not number or number.isalpha():
        number = "0" + number
    if not NUMBER_RE.fullmatch(number):
        return None
    return prefix, number


def normalize_callsign(value, conn):
    """Return (key, reason); reject ambiguous IATA aliases, including collisions."""
    parts = split_callsign(value)
    if parts is None:
        return None, "invalid_or_registration_callsign"
    prefix, number = parts
    # ICAO is unique; an IATA prefix is not. Count distinct target codes in SQLite.
    if len(prefix) == 3:
        airline = conn.execute("SELECT code FROM airlines WHERE icao = ?", (prefix,)).fetchone()
        if airline:
            return airline[0] + number, "normalized"
        # An exact licensed route can identify a prefix absent from the airline
        # table; its owning AirlineCode was separately validated during import.
        if conn.execute("SELECT 1 FROM routes WHERE callsign = ?", (prefix + number,)).fetchone():
            return prefix + number, "normalized"
    count, target = conn.execute(
        "SELECT COUNT(DISTINCT code), MIN(code) FROM airlines WHERE iata = ?", (prefix,)
    ).fetchone()
    if count > 1:
        return None, "ambiguous_airline_alias"
    if count == 1:
        return target + number, "normalized"
    # An exact canonical prefix can include an IATA-only airline.
    if conn.execute("SELECT 1 FROM airlines WHERE code = ?", (prefix,)).fetchone():
        return prefix + number, "normalized"
    return None, "unknown_airline_prefix"


def connect_readonly(path):
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        conn.execute(f"PRAGMA cache_size = -{SQLITE_CACHE_KIB}")
        conn.execute("PRAGMA mmap_size = 0")
        conn.execute("PRAGMA temp_store = FILE")
    except sqlite3.Error:
        conn.close()
        raise
    return conn


def read_small_json(path, limit=8192):
    with path.open("rb") as stream:
        body = stream.read(limit + 1)
    if len(body) > limit:
        raise ValueError("Reference metadata exceeds size limit")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("Reference metadata must be an object")
    return value


def read_pointer(root):
    pointer = read_small_json(root / "active.json", 4096)
    for field in ("active", "previous"):
        value = pointer.get(field)
        if value is not None and not GENERATION_RE.fullmatch(str(value)):
            raise ValueError("Invalid reference generation pointer")
    if not pointer.get("active"):
        raise ValueError("Missing active reference generation")
    return pointer


def airport_sequence(conn, codes):
    result = []
    for code in codes:
        row = conn.execute(
            "SELECT code, name, icao, iata, latitude, longitude FROM airports WHERE code = ?",
            (code,),
        ).fetchone()
        if row is None:
            return None
        airport = dict(zip(("code", "name", "icao", "iata", "latitude", "longitude"), row))
        airport["name"] = airport["name"][:MAX_AIRPORT_NAME]
        airport["name_truncated"] = len(row[1]) > MAX_AIRPORT_NAME
        result.append(airport)
    return result


def route_fields(airports):
    # Order identifies recorded origin/destination only for an unambiguous pair.
    return {
        "airport_codes": [airport["code"] for airport in airports],
        "airports": airports if len(airports) <= MAX_AIRPORT_DETAILS else None,
        "airport_details_omitted": len(airports) > MAX_AIRPORT_DETAILS,
        "departure_airport": airports[0]["code"] if len(airports) == 2 else None,
        "destination_airport": airports[1]["code"] if len(airports) == 2 else None,
        "current_leg_ambiguous": len(airports) != 2,
    }


def great_circle_km(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    delta_lat, delta_lon = lat2 - lat1, math.radians(b[1] - a[1])
    hav = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 12742 * math.asin(math.sqrt(min(1, max(0, hav))))


def geography_check(airports, position, max_excess_km):
    if position is None or max_excess_km is None:
        return "not_checked"
    if len(position) != 2 or not all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) for x in position):
        raise ValueError("Position must be a finite latitude/longitude pair")
    if not -90 <= position[0] <= 90 or not -180 <= position[1] <= 180:
        raise ValueError("Position is outside latitude/longitude bounds")
    excess = []  # At most MAX_STOPS - 1 floats; never a track history.
    for origin, destination in zip(airports, airports[1:]):
        if any(p[axis] is None for p in (origin, destination) for axis in ("latitude", "longitude")):
            return "unknown_airport_coordinates"
        start = origin["latitude"], origin["longitude"]
        end = destination["latitude"], destination["longitude"]
        excess.append(great_circle_km(start, position) + great_circle_km(position, end) - great_circle_km(start, end))
    return "rejected" if min(excess) > max_excess_km else "plausible"


class RouteSession:
    def __init__(self, conn=None, manifest=None, status="missing", overrides_path=None):
        self.conn = conn
        self.manifest = manifest or {}
        self.status = status
        self.overrides_path = overrides_path

    def metadata(self, now=None):
        now = now or utc_now()
        retrieved = self.manifest.get("retrieved_at")
        age = max(0, int((now - parse_time(retrieved)).total_seconds())) if retrieved else None
        return {
            "status": self.status,
            "source": SOURCE,
            "generation": self.manifest.get("generation"),
            "revision": self.manifest.get("revision"),
            "retrieved_at": retrieved,
            "dataset_age_seconds": age,
            "license": self.manifest.get("license"),
            "counts": self.manifest.get("counts", {}),
        }

    def _override(self, key, aircraft_hex, flight_date, now):
        if self.overrides_path is None or not self.overrides_path.exists():
            return None
        # Overrides are mutable: never use immutable=1 or cache their contents.
        conn = sqlite3.connect(self.overrides_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.25)
        try:
            conn.execute(f"PRAGMA cache_size = -{SQLITE_CACHE_KIB}")
            conn.execute("PRAGMA mmap_size = 0")
            conn.execute("PRAGMA temp_store = FILE")
            row = conn.execute(
                """SELECT airport_codes, source, evidence, valid_from, valid_until, verified, aircraft_hex
                   FROM route_overrides WHERE callsign = ? AND flight_date = ?
                   AND (aircraft_hex = '' OR aircraft_hex = ?)
                   ORDER BY length(aircraft_hex) DESC LIMIT 2""",
                (key, flight_date, aircraft_hex or ""),
            )
            for codes, source, evidence, start, end, verified, scoped_hex in row:
                if parse_time(start) <= now < parse_time(end):
                    airports = airport_sequence(self.conn, codes.split("-"))
                    if airports is None:
                        continue
                    return {
                        **route_fields(airports), "kind": "dated_override", "source": source,
                        "matched_callsign": key, "evidence": evidence, "flight_date": flight_date,
                        "valid_from": start, "valid_until": end,
                        "aircraft_hex": scoped_hex or None,
                        "flight_instance_verified": bool(verified and scoped_hex and aircraft_hex == scoped_hex),
                    }
        finally:
            conn.close()
        return None

    def resolve(self, received, aircraft_hex=None, flight_date=None, position=None, max_excess_km=2000, now=None):
        now = now or utc_now()
        if aircraft_hex is not None:
            if not isinstance(aircraft_hex, str) or not HEX_RE.fullmatch(aircraft_hex.upper()):
                raise ValueError("Aircraft hex must have six hexadecimal characters")
            aircraft_hex = aircraft_hex.upper()
        result = {
            "callsign_received": received if isinstance(received, str) and len(received) <= 16 else None,
            "normalized_callsign": None, "route_reference": None, "route_override": None,
            "preferred_route": None, "reason": "reference_" + self.status,
            "geography_check": "not_checked",
        }
        if self.conn is None:
            return result
        key, reason = normalize_callsign(received, self.conn)
        result["normalized_callsign"] = key
        result["reason"] = reason
        if key is None:
            return result
        row = self.conn.execute("SELECT airport_codes FROM routes WHERE callsign = ?", (key,)).fetchone()
        result["reason"] = "no_route_match"
        if row:
            airports = airport_sequence(self.conn, row[0].split("-"))
            if airports is not None:
                check = geography_check(airports, position, max_excess_km)
                result["geography_check"] = check
                result["reason"] = "route_geography_rejected" if check == "rejected" else "reference_match"
                if check != "rejected":
                    meta = self.metadata(now)
                    result["route_reference"] = {
                        **route_fields(airports), "kind": "reference", "source": SOURCE,
                        "matched_callsign": key, "dataset_revision": meta["revision"],
                        "retrieved_at": meta["retrieved_at"], "dataset_age_seconds": meta["dataset_age_seconds"],
                        "flight_instance_verified": False,
                    }
            else:
                result["reason"] = "missing_airport_reference"
        try:
            result["route_override"] = self._override(key, aircraft_hex, flight_date or now.date().isoformat(), now)
        except (sqlite3.Error, ValueError, OSError):
            # An unreadable override must not suppress telemetry or a valid reference.
            result["override_status"] = "invalid"
        if result["route_override"] is not None:
            result["preferred_route"] = "route_override"
            result["reason"] = "dated_override_match"
        elif result["route_reference"] is not None:
            result["preferred_route"] = "route_reference"
        return result


class RouteStore:
    def __init__(self, root: Path, overrides_path=None):
        self.root = root
        self.overrides_path = overrides_path or root / "overrides.sqlite3"

    @contextmanager
    def session(self):
        """Pin one immutable generation for an entire request, then close it."""
        conn = None
        status = "missing"
        try:
            pointer = read_pointer(self.root)
            directory = self.root / "generations" / pointer["active"]
            manifest = read_small_json(directory / "manifest.json")
            if (manifest.get("schema_version") != 1 or manifest.get("generation") != pointer["active"]
                    or manifest.get("license") != "CC0-1.0" or manifest.get("source") != SOURCE
                    or not re.fullmatch(r"[a-f0-9]{40}", manifest.get("revision", ""))):
                raise ValueError("Invalid route generation manifest")
            parse_time(manifest["retrieved_at"])
            conn = connect_readonly(directory / "routes.sqlite3")
            if conn.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("Unsupported route database schema")
            # Cheap validation at runtime; full hash/integrity validation belongs to maintenance.
            revision = conn.execute("SELECT value FROM metadata WHERE key = 'revision'").fetchone()
            if revision is None or revision[0] != manifest["revision"]:
                raise ValueError("Reference revision mismatch")
            status = "ready"
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, AttributeError):
            if conn is not None:
                conn.close()
                conn = None
            status = "invalid" if (self.root / "active.json").exists() else "missing"
            manifest = {}
        try:
            yield RouteSession(conn, manifest, status, self.overrides_path)
        finally:
            if conn is not None:
                conn.close()

    def metadata(self):
        with self.session() as session:
            return session.metadata()

    def resolve(self, received, **kwargs):
        with self.session() as session:
            try:
                return session.resolve(received, **kwargs)
            except sqlite3.Error:
                return RouteSession(status="invalid").resolve(received)
