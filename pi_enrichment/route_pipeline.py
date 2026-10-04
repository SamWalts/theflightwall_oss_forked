#!/usr/bin/env python3
"""Explicit VRS maintenance. CSV rows and archives stream; datasets stay on disk."""

import argparse
import csv
import fcntl
import gzip
import hashlib
import http.client
import json
import math
import os
import re
import shutil
import sqlite3
import tarfile
import urllib.request
import uuid
from contextlib import closing, contextmanager
from datetime import date
from pathlib import Path, PurePosixPath

from route_reference import (
    AIRPORT_RE, GENERATION_RE, HEX_RE, MAX_STOPS, SOURCE, SOURCE_URL,
    SQLITE_CACHE_KIB, RouteStore, connect_readonly, iso_utc, normalize_callsign,
    parse_time, read_pointer, read_small_json, split_callsign, utc_now,
)

DEFAULT_ROOT = Path.home() / ".flightwall-pi" / "routes"
CHUNK_BYTES = 64 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_LINE_BYTES = 16 * 1024
MAX_RECORD_CHARS = 64 * 1024
CODE_RE = re.compile(r"(?:[A-Z]{2,3}|[A-Z][0-9]|[0-9][A-Z])")
ROUTE_PATH_RE = re.compile(r"routes/schema-01/([A-Z0-9])/([A-Z0-9]{2,3})-(all|[0-9])\.csv")
AIRPORT_PATH_RE = re.compile(r"airports/schema-01/([A-Z0-9])/([A-Z0-9]{2})\.csv")
NOTICE_PATHS = (
    "LICENSE", "routes/schema-01/CREDITS.md", "routes/schema-01/README.md",
    "airlines/schema-01/CREDITS.md", "airlines/schema-01/README.md",
    "airports/schema-01/README.md",
)
SCHEMA = """
PRAGMA user_version = 1;
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE airlines(code TEXT PRIMARY KEY, name TEXT NOT NULL, icao TEXT, iata TEXT) WITHOUT ROWID;
CREATE UNIQUE INDEX airlines_icao ON airlines(icao) WHERE icao IS NOT NULL;
CREATE INDEX airlines_iata ON airlines(iata);
CREATE TABLE airports(code TEXT PRIMARY KEY, name TEXT NOT NULL, icao TEXT, iata TEXT,
                      latitude REAL, longitude REAL) WITHOUT ROWID;
CREATE TABLE routes(callsign TEXT PRIMARY KEY, airline_code TEXT NOT NULL,
                    airport_codes TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE route_airports(callsign TEXT NOT NULL, ordinal INTEGER NOT NULL, airport_code TEXT NOT NULL,
                           PRIMARY KEY(callsign, ordinal)) WITHOUT ROWID;
CREATE TABLE artifacts(path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL,
                       rows INTEGER NOT NULL, route_code TEXT, partition TEXT) WITHOUT ROWID;
"""


def writable_connection(path):
    conn = sqlite3.connect(path)
    try:
        conn.execute(f"PRAGMA cache_size = -{SQLITE_CACHE_KIB}")
        conn.execute("PRAGMA mmap_size = 0")
        conn.execute("PRAGMA temp_store = FILE")
        conn.execute("PRAGMA journal_mode = DELETE")
    except sqlite3.Error:
        conn.close()
        raise
    return conn


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_file(path):
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path, payload):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def maintenance_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".maintenance.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as err:
            raise ValueError("Another route maintenance command is running") from err
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class BoundedLines:
    def __init__(self, stream):
        self.stream = stream
        self.record_chars = 0

    def __iter__(self):
        return self

    def __next__(self):
        line = self.stream.readline(MAX_LINE_BYTES + 1)
        if not line:
            raise StopIteration
        self.record_chars += len(line)
        if len(line) > MAX_LINE_BYTES or self.record_chars > MAX_RECORD_CHARS:
            raise ValueError("CSV line or record exceeds import budget")
        return line


def csv_rows(path, headings):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        lines = BoundedLines(stream)
        reader = csv.reader(lines, strict=True)
        header = next(reader)
        if header[:len(headings)] != headings:
            raise ValueError(f"Unsupported CSV schema: {path.name}")
        while True:
            lines.record_chars = 0
            row = next(reader, None)
            if row is None:
                break
            if not row or not any(row):
                continue
            if len(row) < len(headings):
                raise ValueError(f"Incomplete CSV row: {path.name}")
            yield row


def text(value, maximum=256):
    value = value.strip()
    if len(value) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError("Reference string exceeds bounds or contains control characters")
    return value


def coordinate(value, limit):
    if not value.strip():
        return None
    value = float(value)
    if not math.isfinite(value) or not -limit <= value <= limit:
        raise ValueError("Invalid airport coordinate")
    return value


def import_csv(conn, path, relative):
    count = 0
    route_match = ROUTE_PATH_RE.fullmatch(relative)
    if relative == "airlines/schema-01/airlines.csv":
        rows = csv_rows(path, ["Code", "Name", "ICAO", "IATA", "PositioningFlightPattern", "CharterFlightPattern"])
        for code, name, icao, iata, *_ in rows:
            if not CODE_RE.fullmatch(code) or (icao and not re.fullmatch(r"[A-Z]{3}", icao)) or (iata and not re.fullmatch(r"[A-Z0-9]{2}", iata)):
                raise ValueError("Invalid airline code")
            if code != (icao or iata):
                raise ValueError("Airline code is not the canonical ICAO/IATA code")
            conn.execute("INSERT INTO airlines VALUES (?, ?, ?, ?)", (code, text(name), icao or None, iata or None))
            count += 1
    elif AIRPORT_PATH_RE.fullmatch(relative):
        rows = csv_rows(path, ["Code", "Name", "ICAO", "IATA", "Location", "CountryISO2", "Latitude", "Longitude", "AltitudeFeet"])
        for code, name, icao, iata, location, country, lat, lon, *_ in rows:
            if not AIRPORT_RE.fullmatch(code) or code != (icao or iata) or not relative.endswith(f"/{code[:2]}.csv") or relative.split("/")[2] != code[0]:
                raise ValueError("Invalid airport code or partition")
            conn.execute("INSERT INTO airports VALUES (?, ?, ?, ?, ?, ?)",
                         (code, text(name), text(icao, 4) or None, text(iata, 3) or None,
                          coordinate(lat, 90), coordinate(lon, 180)))
            count += 1
    elif route_match:
        folder, file_code, partition = route_match.groups()
        if folder != file_code[0]:
            raise ValueError("Invalid route partition folder")
        rows = csv_rows(path, ["Callsign", "Code", "Number", "AirlineCode", "AirportCodes"])
        for callsign, code, number, airline, airport_codes, *_ in rows:
            parts = split_callsign(callsign)
            airports = airport_codes.split("-")
            if (parts != (code, number) or callsign != code + number or code != file_code
                    or (partition != "all" and number[0] != partition)
                    or not 2 <= len(airports) <= MAX_STOPS or not all(AIRPORT_RE.fullmatch(a) for a in airports)
                    or not CODE_RE.fullmatch(airline)):
                raise ValueError(f"Invalid route row or airport sequence: {callsign}")
            conn.execute("INSERT INTO routes VALUES (?, ?, ?)", (callsign, airline, airport_codes))
            conn.executemany("INSERT INTO route_airports VALUES (?, ?, ?)",
                             ((callsign, ordinal, airport) for ordinal, airport in enumerate(airports)))
            count += 1
    else:
        raise ValueError(f"Unsupported reference file: {relative}")
    conn.commit()  # One CSV partition, not one transaction holding the whole dataset.
    return count


def selected_file(relative, codes):
    if relative in NOTICE_PATHS or relative == "airports/schema-01/CREDITS.md":
        return True
    if relative == "airlines/schema-01/airlines.csv" or AIRPORT_PATH_RE.fullmatch(relative):
        return True
    route = ROUTE_PATH_RE.fullmatch(relative)
    return bool(route and (codes is None or route[2] in codes))


def local_files(source, codes):
    for relative in (*NOTICE_PATHS, "airports/schema-01/CREDITS.md", "airlines/schema-01/airlines.csv"):
        path = source / relative
        if path.is_file():
            yield relative, path
    for path in (source / "airports/schema-01").glob("*/*.csv"):
        yield path.relative_to(source).as_posix(), path
    if codes is None:
        paths = (source / "routes/schema-01").glob("*/*.csv")
        for path in paths:
            yield path.relative_to(source).as_posix(), path
    else:
        for code in sorted(codes):
            # Discover -all and digit partitions. No -all-only assumption or giant file list.
            for partition in ("all", *map(str, range(10))):
                relative = f"routes/schema-01/{code[0]}/{code}-{partition}.csv"
                path = source / relative
                if path.is_file():
                    yield relative, path


class ArchiveBudget:
    def __init__(self, stream, limit=MAX_ARCHIVE_BYTES):
        self.stream = stream
        self.count = 0
        self.limit = limit

    def read(self, size=-1):
        if size < 0:
            raise ValueError("Unbounded archive reads are prohibited")
        body = self.stream.read(size)
        self.count += len(body)
        if self.count > self.limit:
            raise ValueError("Archive exceeds compressed/uncompressed byte budget")
        return body


def archive_files(stream, codes):
    # Streaming mode does not build a full archive index or extract arbitrary paths.
    with gzip.GzipFile(fileobj=ArchiveBudget(stream), mode="rb") as zipped:
        plain = ArchiveBudget(zipped, limit=2 * 1024 * 1024 * 1024)
        with tarfile.open(fileobj=plain, mode="r|", bufsize=CHUNK_BYTES) as archive:
            for member in archive:
                # tarfile otherwise retains every TarInfo even in streaming mode (Python 3.12).
                archive.members.clear()
                parts = PurePosixPath(member.name).parts
                if not parts or parts[0] in ("/", "..") or ".." in parts:
                    raise ValueError("Invalid archive path")
                relative = "/".join(parts[1:])
                if selected_file(relative, codes):
                    if not member.isfile() or member.size > MAX_FILE_BYTES:
                        raise ValueError("Selected archive entry is not a bounded regular file")
                    with archive.extractfile(member) as entry:
                        yield relative, entry
        # Verify gzip's trailer/CRC, even when tar's end marker was read earlier.
        # A truncated network stream must never activate a partial generation.
        while plain.read(CHUNK_BYTES):
            pass


def consume_files(conn, stage, files):
    for relative, source in files:
        temporary = stage / ".input"
        digest = hashlib.sha256()
        size = 0
        own_stream = isinstance(source, Path)
        stream = source.open("rb") if own_stream else source
        try:
            with temporary.open("wb") as output:
                while chunk := stream.read(CHUNK_BYTES):
                    size += len(chunk)
                    if size > MAX_FILE_BYTES:
                        raise ValueError(f"Reference file exceeds size limit: {relative}")
                    digest.update(chunk)
                    output.write(chunk)
        finally:
            if own_stream:
                stream.close()
        route = ROUTE_PATH_RE.fullmatch(relative)
        count = import_csv(conn, temporary, relative) if relative.endswith(".csv") else 0
        conn.execute("INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?)",
                     (relative, digest.hexdigest(), size, count, route[2] if route else None, route[3] if route else None))
        conn.commit()
        if not relative.endswith(".csv"):
            destination = stage / "notices" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temporary, destination)
            fsync_file(destination)
            fsync_directory(destination.parent)
        else:
            temporary.unlink()


def validate_import(conn, stage, codes):
    for path in NOTICE_PATHS:
        if not (stage / "notices" / path).is_file():
            raise ValueError(f"Missing license/schema/credits artifact: {path}")
    with (stage / "notices/LICENSE").open("rb") as stream:
        license_text = stream.read(CHUNK_BYTES + 1)
    if len(license_text) > CHUNK_BYTES or b"CC0 1.0 Universal" not in license_text:
        raise ValueError("Expected VRS CC0 license was not found")
    for code in codes or ():
        if not conn.execute("SELECT 1 FROM artifacts WHERE route_code = ? AND rows > 0", (code,)).fetchone():
            raise ValueError(f"No route partition found for requested code: {code}")
    if conn.execute("SELECT 1 FROM artifacts GROUP BY route_code HAVING COUNT(*) > 1 AND SUM(partition = 'all') > 0 LIMIT 1").fetchone():
        raise ValueError("Mixed -all and digit route partitions")
    checks = (
        "SELECT 1 FROM routes r LEFT JOIN airlines a ON r.airline_code = a.code WHERE a.code IS NULL LIMIT 1",
        "SELECT 1 FROM route_airports r LEFT JOIN airports a ON r.airport_code = a.code WHERE a.code IS NULL LIMIT 1",
    )
    for query in checks:
        if conn.execute(query).fetchone():
            raise ValueError("Route generation has an unresolved airline/airport join")
    # Key syntax/normal form was checked per CSV row. Ambiguous IATA prefixes can
    # legitimately exist in the source and remain unmatched at lookup time.
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Route SQLite integrity check failed")
    counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
              for table in ("routes", "airlines", "airports", "artifacts")}
    if any(counts[table] == 0 for table in ("routes", "airlines", "airports")):
        raise ValueError("Reference generation is empty")
    return counts


def validate_generation(root, generation):
    if not GENERATION_RE.fullmatch(generation):
        raise ValueError("Invalid generation ID")
    directory = root / "generations" / generation
    manifest = read_small_json(directory / "manifest.json")
    revision = manifest.get("revision", "")
    if (manifest.get("generation") != generation or manifest.get("schema_version") != 1
            or manifest.get("source") != SOURCE or manifest.get("license") != "CC0-1.0"
            or not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{40}", revision)
            or not generation.startswith(revision[:12] + "-")
            or digest_file(directory / "routes.sqlite3") != manifest.get("database_sha256")):
        raise ValueError("Generation metadata/checksum validation failed")
    parse_time(manifest.get("retrieved_at"))
    with closing(connect_readonly(directory / "routes.sqlite3")) as conn:
        if conn.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("Unsupported route database schema")
        if conn.execute("SELECT value FROM metadata WHERE key = 'revision'").fetchone() != (revision,):
            raise ValueError("Reference revision mismatch")
        counts = validate_import(conn, directory, None)
        if counts != manifest.get("counts"):
            raise ValueError("Generation row counts do not match manifest")
        for relative, checksum in conn.execute("SELECT path, sha256 FROM artifacts WHERE path NOT LIKE '%.csv'"):
            if digest_file(directory / "notices" / relative) != checksum:
                raise ValueError("Generation notice checksum failed")
    return manifest


def import_generation(root, revision, codes, source=None, archive=None):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Pin a full lowercase 40-character repository revision")
    if codes is not None and (not codes or len(codes) > 128 or any(not CODE_RE.fullmatch(c) for c in codes)):
        raise ValueError("Select 1–128 canonical airline codes, or explicitly select all routes")
    with maintenance_lock(root):
        generations = root / "generations"
        generations.mkdir(exist_ok=True)
        generation = revision[:12] + "-" + uuid.uuid4().hex
        stage = generations / (".staging-" + generation)
        stage.mkdir()
        conn = writable_connection(stage / "routes.sqlite3")
        try:
            conn.executescript(SCHEMA)
            if source is not None:
                consume_files(conn, stage, local_files(source, codes))
            elif archive is not None:
                with archive.open("rb") as stream:
                    consume_files(conn, stage, archive_files(stream, codes))
            else:
                url = f"https://codeload.github.com/vradarserver/standing-data/tar.gz/{revision}"
                with urllib.request.urlopen(url, timeout=30) as stream:
                    consume_files(conn, stage, archive_files(stream, codes))
            counts = validate_import(conn, stage, codes)
            retrieved = iso_utc(utc_now())
            conn.executemany("INSERT INTO metadata VALUES (?, ?)", (("revision", revision), ("retrieved_at", retrieved)))
            conn.commit()
            conn.close()
            conn = None
            database = stage / "routes.sqlite3"
            fsync_file(database)
            # Persist intermediate notice directories before publishing their parent.
            for directory, _, _ in os.walk(stage, topdown=False):
                fsync_directory(Path(directory))
            manifest = {
                "schema_version": 1, "generation": generation, "source": SOURCE,
                "source_url": SOURCE_URL + "/tree/" + revision, "revision": revision,
                "retrieved_at": retrieved, "license": "CC0-1.0", "counts": counts,
                "database_sha256": digest_file(database),
                "selected_airlines": sorted(codes) if codes is not None else "all",
                "input_kind": "local_checkout" if source is not None else "local_archive" if archive is not None else "pinned_https_archive",
                "revision_verification": "caller_asserted" if source is not None or archive is not None else "pinned_download_url",
                "artifact_checksums": "routes.sqlite3:artifacts", "sqlite_cache_kib": SQLITE_CACHE_KIB,
            }
            atomic_json(stage / "manifest.json", manifest)
            destination = generations / generation
            os.replace(stage, destination)
            fsync_directory(generations)
            previous = read_pointer(root)["active"] if (root / "active.json").exists() else None
            atomic_json(root / "active.json", {"active": generation, "previous": previous})
            return manifest
        finally:
            if conn is not None:
                conn.close()
            if stage.exists():
                shutil.rmtree(stage)


def rollback(root):
    with maintenance_lock(root):
        pointer = read_pointer(root)
        previous = pointer.get("previous")
        if previous is None:
            raise ValueError("No previous generation is available")
        manifest = validate_generation(root, previous)
        atomic_json(root / "active.json", {"active": previous, "previous": pointer["active"]})
        return manifest


def set_override(root, received, airport_codes, flight_date, valid_from, valid_until,
                 source, evidence, aircraft_hex=None, verified=False):
    if date.fromisoformat(flight_date).isoformat() != flight_date:
        raise ValueError("Flight date must use YYYY-MM-DD")
    start, end = parse_time(valid_from), parse_time(valid_until)
    if not 0 < (end - start).total_seconds() <= 86400:
        raise ValueError("Override validity must be positive and at most 24 hours")
    if start.date().isoformat() != flight_date:
        raise ValueError("Flight date must match the UTC start date")
    if aircraft_hex is not None:
        aircraft_hex = aircraft_hex.upper()
        if not HEX_RE.fullmatch(aircraft_hex):
            raise ValueError("Override aircraft hex must have six hexadecimal characters")
    if verified and not aircraft_hex:
        raise ValueError("Flight verification requires an aircraft hex and dated evidence")
    airports = airport_codes.split("-")
    if not 2 <= len(airports) <= MAX_STOPS or not all(AIRPORT_RE.fullmatch(a) for a in airports):
        raise ValueError(f"Override needs 2–{MAX_STOPS} valid airport codes")
    source, evidence = text(source, 64), text(evidence, 512)
    if not source or not evidence:
        raise ValueError("Override source and evidence are required")
    with maintenance_lock(root), RouteStore(root).session() as session:
        if session.conn is None:
            raise ValueError("Import reference companions before adding route overrides")
        key, reason = normalize_callsign(received, session.conn)
        if key is None:
            raise ValueError(reason)
        for airport in airports:
            if not session.conn.execute("SELECT 1 FROM airports WHERE code = ?", (airport,)).fetchone():
                raise ValueError(f"Unknown override airport: {airport}")
        conn = writable_connection(root / "overrides.sqlite3")
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS route_overrides(
                callsign TEXT NOT NULL, flight_date TEXT NOT NULL, aircraft_hex TEXT NOT NULL,
                airport_codes TEXT NOT NULL, source TEXT NOT NULL, evidence TEXT NOT NULL,
                valid_from TEXT NOT NULL, valid_until TEXT NOT NULL, verified INTEGER NOT NULL,
                PRIMARY KEY(callsign, flight_date, aircraft_hex)) WITHOUT ROWID""")
            # Expired evidence is not retained as unbounded track history.
            conn.execute("DELETE FROM route_overrides WHERE valid_until <= ?", (iso_utc(utc_now()),))
            conn.execute("INSERT OR REPLACE INTO route_overrides VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (key, flight_date, aircraft_hex or "", airport_codes, source, evidence,
                          iso_utc(start), iso_utc(end), int(verified)))
            conn.commit()
        finally:
            conn.close()
        return {"callsign": key, "flight_date": flight_date, "valid_until": iso_utc(end)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(os.getenv("ROUTE_DATA_DIR", str(DEFAULT_ROOT))))
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("import", help="Prepare and atomically activate a VRS generation")
    prepare.add_argument("--revision", required=True)
    scope = prepare.add_mutually_exclusive_group(required=True)
    scope.add_argument("--airlines", nargs="+", help="Canonical codes, e.g. BAW UAL EZY")
    scope.add_argument("--all-routes", action="store_true", help="Explicitly opt into worldwide route storage")
    inputs = prepare.add_mutually_exclusive_group()
    inputs.add_argument("--source-dir", type=Path, help="Already downloaded checkout at the specified revision")
    inputs.add_argument("--archive", type=Path, help="Already downloaded tar.gz at the specified revision")
    commands.add_parser("rollback", help="Validate and reactivate the previous generation")
    commands.add_parser("status", help="Show local reference health without network access")
    lookup = commands.add_parser("lookup", help="Resolve a received callsign locally")
    lookup.add_argument("callsign")
    lookup.add_argument("--aircraft-hex")
    lookup.add_argument("--flight-date")
    override = commands.add_parser("override", help="Record dated manual evidence separately")
    override.add_argument("callsign")
    override.add_argument("--airports", required=True, help="Ordered canonical airport codes separated by hyphens")
    override.add_argument("--flight-date", required=True)
    override.add_argument("--valid-from", required=True)
    override.add_argument("--valid-until", required=True)
    override.add_argument("--source", required=True)
    override.add_argument("--evidence", required=True)
    override.add_argument("--aircraft-hex")
    override.add_argument("--verified", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "import":
            result = import_generation(args.data_dir, args.revision,
                                       set(args.airlines) if args.airlines else None, args.source_dir, args.archive)
        elif args.command == "rollback":
            result = rollback(args.data_dir)
        elif args.command == "status":
            result = RouteStore(args.data_dir).metadata()
        elif args.command == "lookup":
            if args.flight_date and date.fromisoformat(args.flight_date).isoformat() != args.flight_date:
                raise ValueError("Flight date must use YYYY-MM-DD")
            result = RouteStore(args.data_dir).resolve(args.callsign, aircraft_hex=args.aircraft_hex, flight_date=args.flight_date)
        else:
            result = set_override(args.data_dir, args.callsign, args.airports, args.flight_date,
                                  args.valid_from, args.valid_until, args.source, args.evidence, args.aircraft_hex, args.verified)
    except (OSError, ValueError, sqlite3.Error, csv.Error, tarfile.TarError, http.client.HTTPException, EOFError, StopIteration) as err:
        parser.exit(1, f"Route maintenance failed: {err}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
