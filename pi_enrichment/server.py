#!/usr/bin/env python3
import argparse
import json
import logging
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List

DEFAULT_DATA_DIR = Path.home() / ".flightwall-pi"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "faa_registry.sqlite3"
DEFAULT_TAR1090_URL = "http://127.0.0.1/tar1090/data/aircraft.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso_utc(value: str):
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_adsb_icao(value: str) -> str:
    clean = re.sub(r"[^0-9a-fA-F]", "", value or "").upper()
    if not clean:
        return ""
    return clean.zfill(6)


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class EnrichmentStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = dict_factory
        return conn

    def get_aircraft(self, adsb_icao: str) -> Dict[str, str]:
        normalized = normalize_adsb_icao(adsb_icao)
        response = {
            "adsb_icao": normalized,
            "registration": "",
            "operator_name": "",
            "operator_icao": "",
            "aircraft_model": "",
            "aircraft_type": "",
            "source": "faa_registry",
            "updated_at": "",
            "found": False,
        }
        if not normalized or not self.db_path.exists():
            return response

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT adsb_icao, registration, operator_name, operator_icao,
                       aircraft_model, aircraft_type, source, updated_at
                FROM aircraft_registry
                WHERE adsb_icao = ?
                """,
                (normalized,),
            ).fetchone()
        if not row:
            return response

        row["found"] = True
        return row

    def get_aircraft_map(self, adsb_icaos: List[str]) -> Dict[str, Dict[str, str]]:
        normalized = sorted({normalize_adsb_icao(x) for x in adsb_icaos if normalize_adsb_icao(x)})
        if not normalized or not self.db_path.exists():
            return {}

        placeholders = ",".join("?" for _ in normalized)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT adsb_icao, registration, operator_name, operator_icao,
                       aircraft_model, aircraft_type, source, updated_at
                FROM aircraft_registry
                WHERE adsb_icao IN ({placeholders})
                """,
                normalized,
            ).fetchall()
        result = {}
        for row in rows:
            row["found"] = True
            result[row["adsb_icao"]] = row
        return result

    def get_metadata(self) -> Dict[str, str]:
        meta = {
            "db_exists": self.db_path.exists(),
            "db_path": str(self.db_path),
            "row_count": "0",
            "faa_csv_checksum": "",
            "faa_source_url": "",
            "last_sync_at": "",
        }
        if not self.db_path.exists():
            return meta

        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM metadata").fetchall()
        for row in rows:
            meta[row["key"]] = row["value"]
        return meta


class EnrichmentRequestHandler(BaseHTTPRequestHandler):
    store: EnrichmentStore = None
    tar1090_url: str = DEFAULT_TAR1090_URL
    stale_after_hours: int = 72

    def _write_json(self, payload: Dict, status: int = 200):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            return self._handle_health()
        if path == "/v1/meta":
            return self._handle_meta()
        if path == "/v1/aircraft/live":
            return self._handle_live()
        if path.startswith("/v1/aircraft/"):
            adsb_icao = path[len("/v1/aircraft/"):]
            return self._handle_aircraft_lookup(adsb_icao)
        return self._write_json({"error": "not_found"}, status=404)

    def _handle_health(self):
        meta = self.store.get_metadata()
        last_sync = parse_iso_utc(meta.get("last_sync_at", ""))
        stale = True
        if last_sync is not None:
            stale = datetime.now(timezone.utc) - last_sync > timedelta(hours=self.stale_after_hours)
        self._write_json(
            {
                "status": "ok",
                "db_exists": meta.get("db_exists", False),
                "last_sync_at": meta.get("last_sync_at", ""),
                "stale": stale,
                "updated_at": utc_now_iso(),
            }
        )

    def _handle_meta(self):
        meta = self.store.get_metadata()
        self._write_json(
            {
                "schema_version": 1,
                "row_count": int(meta.get("row_count", "0") or 0),
                "faa_csv_checksum": meta.get("faa_csv_checksum", ""),
                "faa_source_url": meta.get("faa_source_url", ""),
                "last_sync_at": meta.get("last_sync_at", ""),
                "db_path": meta.get("db_path", ""),
                "updated_at": utc_now_iso(),
            }
        )

    def _handle_aircraft_lookup(self, adsb_icao: str):
        self._write_json(self.store.get_aircraft(adsb_icao))

    def _fetch_live_aircraft(self) -> List[Dict]:
        with urllib.request.urlopen(self.tar1090_url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        aircraft = payload.get("aircraft", []) if isinstance(payload, dict) else []
        if not isinstance(aircraft, list):
            return []
        return [a for a in aircraft if isinstance(a, dict)]

    def _handle_live(self):
        try:
            live = self._fetch_live_aircraft()
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            return self._write_json(
                {
                    "source": "readsb_tar1090",
                    "aircraft": [],
                    "count": 0,
                    "updated_at": utc_now_iso(),
                    "error": str(err),
                },
                status=502,
            )

        icaos = [str(item.get("hex", "")) for item in live if item.get("hex")]
        enrichment_map = self.store.get_aircraft_map(icaos)

        out = []
        for item in live:
            hex_value = normalize_adsb_icao(str(item.get("hex", "")))
            enrichment = enrichment_map.get(
                hex_value,
                {
                    "adsb_icao": hex_value,
                    "registration": "",
                    "operator_name": "",
                    "operator_icao": "",
                    "aircraft_model": "",
                    "aircraft_type": "",
                    "source": "faa_registry",
                    "updated_at": "",
                    "found": False,
                },
            )
            out.append(
                {
                    "adsb_icao": enrichment["adsb_icao"],
                    "flight": item.get("flight", "").strip() if isinstance(item.get("flight"), str) else "",
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "registration": enrichment["registration"],
                    "operator_name": enrichment["operator_name"],
                    "operator_icao": enrichment["operator_icao"],
                    "aircraft_model": enrichment["aircraft_model"],
                    "aircraft_type": enrichment["aircraft_type"],
                    "source": enrichment["source"],
                    "updated_at": enrichment["updated_at"],
                    "found": enrichment["found"],
                }
            )

        self._write_json(
            {
                "source": "readsb_tar1090",
                "tar1090_url": self.tar1090_url,
                "count": len(out),
                "aircraft": out,
                "updated_at": utc_now_iso(),
            }
        )

    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.address_string(), fmt % args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FlightWall local enrichment server")
    parser.add_argument("--host", default=os.getenv("FLIGHTWALL_PI_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("FLIGHTWALL_PI_PORT", "8080")))
    parser.add_argument("--db-path", type=Path, default=Path(os.getenv("FAA_DB_PATH", str(DEFAULT_DB_PATH))))
    parser.add_argument("--tar1090-url", default=os.getenv("TAR1090_AIRCRAFT_URL", DEFAULT_TAR1090_URL))
    parser.add_argument("--stale-after-hours", type=int, default=int(os.getenv("STALE_AFTER_HOURS", "72")))
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(message)s")

    EnrichmentRequestHandler.store = EnrichmentStore(args.db_path)
    EnrichmentRequestHandler.tar1090_url = args.tar1090_url
    EnrichmentRequestHandler.stale_after_hours = args.stale_after_hours

    server = ThreadingHTTPServer((args.host, args.port), EnrichmentRequestHandler)
    logging.info("Serving FlightWall enrichment API at http://%s:%d", args.host, args.port)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
