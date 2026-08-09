#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

DEFAULT_FAA_URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"
DEFAULT_DATA_DIR = Path.home() / ".flightwall-pi"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "faa_registry.sqlite3"
DEFAULT_CSV_PATH = DEFAULT_DATA_DIR / "faa_registry.csv"
DEFAULT_META_PATH = DEFAULT_DATA_DIR / "faa_registry_meta.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def normalize_adsb_icao(value: str) -> str:
    clean = re.sub(r"[^0-9a-fA-F]", "", value or "").upper()
    if not clean:
        return ""
    return clean.zfill(6)


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_to_temp(url: str) -> Path:
    fd, temp_path = tempfile.mkstemp(prefix="faa_download_", suffix=".tmp")
    os.close(fd)
    temp = Path(temp_path)
    with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as output:
        shutil.copyfileobj(response, output)
    return temp


def extract_csv_or_txt(downloaded_path: Path) -> Path:
    if zipfile.is_zipfile(downloaded_path):
        with zipfile.ZipFile(downloaded_path) as zf:
            candidates = [
                n for n in zf.namelist()
                if n.lower().endswith(".csv") or n.lower().endswith(".txt")
            ]
            if not candidates:
                raise RuntimeError("ZIP did not contain CSV/TXT file")
            selected = sorted(candidates)[0]
            fd, out_path = tempfile.mkstemp(prefix="faa_extract_", suffix=Path(selected).suffix)
            os.close(fd)
            out = Path(out_path)
            with zf.open(selected) as src, out.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            return out
    return downloaded_path


def pick_column(row: Dict[str, str], *candidates: str) -> str:
    normalized = {normalize_key(k): v for k, v in row.items()}
    for candidate in candidates:
        key = normalize_key(candidate)
        if key in normalized and normalized[key] is not None:
            return str(normalized[key]).strip()
    return ""


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS aircraft_registry (
            adsb_icao TEXT PRIMARY KEY,
            registration TEXT NOT NULL DEFAULT '',
            operator_name TEXT NOT NULL DEFAULT '',
            operator_icao TEXT NOT NULL DEFAULT '',
            aircraft_model TEXT NOT NULL DEFAULT '',
            aircraft_type TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            raw_json TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_aircraft_operator_name ON aircraft_registry(operator_name)")


def upsert_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO metadata(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def import_registry(csv_path: Path, db_path: Path, checksum: str, source_url: str, synced_at: str) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        init_db(conn)
        conn.execute("BEGIN")
        conn.execute("DELETE FROM aircraft_registry")

        imported = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                adsb_icao = normalize_adsb_icao(
                    pick_column(
                        row,
                        "adsb_icao",
                        "icao24",
                        "mode s code hex",
                        "mode_s_code_hex",
                        "modescodehex",
                        "modes_code_hex",
                        "hex",
                    )
                )
                if not adsb_icao:
                    continue

                registration = pick_column(row, "n-number", "n number", "registration")
                operator_name = pick_column(
                    row,
                    "name",
                    "registered owner",
                    "owner",
                    "operator",
                    "owner name",
                )
                aircraft_model = pick_column(row, "model", "model name")
                aircraft_type = pick_column(
                    row,
                    "type aircraft",
                    "aircraft type",
                    "type",
                    "aircraft_code",
                )
                operator_icao = pick_column(row, "operator icao", "operator_icao", "icao")
                raw_json = json.dumps(row, separators=(",", ":"), ensure_ascii=False)

                conn.execute(
                    """
                    INSERT INTO aircraft_registry(
                        adsb_icao, registration, operator_name, operator_icao,
                        aircraft_model, aircraft_type, source, updated_at, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        adsb_icao,
                        registration,
                        operator_name,
                        operator_icao,
                        aircraft_model,
                        aircraft_type,
                        "faa_registry",
                        synced_at,
                        raw_json,
                    ),
                )
                imported += 1

        upsert_metadata(conn, "faa_csv_checksum", checksum)
        upsert_metadata(conn, "faa_source_url", source_url)
        upsert_metadata(conn, "last_sync_at", synced_at)
        upsert_metadata(conn, "row_count", str(imported))
        conn.commit()
        return imported
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def write_meta(path: Path, metadata: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def run_sync(faa_url: str, db_path: Path, csv_path: Path, meta_path: Path) -> int:
    synced_at = utc_now_iso()
    logging.info("Downloading FAA registry from %s", faa_url)
    downloaded = download_to_temp(faa_url)

    try:
        checksum = sha256_of_file(downloaded)
        extracted = extract_csv_or_txt(downloaded)
        try:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(extracted, csv_path)
            imported = import_registry(extracted, db_path, checksum, faa_url, synced_at)
            metadata = {
                "last_sync_at": synced_at,
                "faa_source_url": faa_url,
                "faa_csv_path": str(csv_path),
                "faa_csv_checksum": checksum,
                "sqlite_db_path": str(db_path),
                "row_count": imported,
            }
            write_meta(meta_path, metadata)
            logging.info("Imported %d rows into %s", imported, db_path)
            return imported
        finally:
            if extracted != downloaded and extracted.exists():
                extracted.unlink()
    finally:
        if downloaded.exists():
            downloaded.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and import FAA aircraft registry into SQLite")
    parser.add_argument("--faa-url", default=os.getenv("FAA_CSV_URL", DEFAULT_FAA_URL))
    parser.add_argument("--db-path", type=Path, default=Path(os.getenv("FAA_DB_PATH", str(DEFAULT_DB_PATH))))
    parser.add_argument("--csv-path", type=Path, default=Path(os.getenv("FAA_CSV_PATH", str(DEFAULT_CSV_PATH))))
    parser.add_argument("--meta-path", type=Path, default=Path(os.getenv("FAA_META_PATH", str(DEFAULT_META_PATH))))
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
    run_sync(args.faa_url, args.db_path, args.csv_path, args.meta_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
