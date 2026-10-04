#!/usr/bin/env python3
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SimulatorState:
    def __init__(self):
        self._lock = threading.Lock()
        self._payload = {"updated_at": "", "source_count": 0, "flights": []}

    def set_payload(self, payload):
        with self._lock:
            self._payload = payload

    def get_payload(self):
        with self._lock:
            return self._payload


class Handler(BaseHTTPRequestHandler):
    state: SimulatorState = None

    def _write_json(self, payload, status=200):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            return self._write_json({"status": "ok", "updated_at": utc_now_iso()})

        if path == "/v1/flights":
            payload = self.state.get_payload()
            payload = {
                "source": "flightwall_sim",
                "updated_at": payload.get("updated_at", ""),
                "source_count": payload.get("source_count", 0),
                "flights": payload.get("flights", []),
            }
            return self._write_json(payload)

        if path == "/v1/display/current":
            payload = self.state.get_payload()
            flights = payload.get("flights", [])
            if not flights:
                return self._write_json(
                    {
                        "line_1": "NO FLIGHTS",
                        "line_2": "WAITING FOR",
                        "line_3": "ENRICHMENT",
                        "updated_at": payload.get("updated_at", ""),
                    }
                )

            card = flights[0]
            line_1 = card.get("flight", "UNKNOWN")[:16]
            line_2 = (card.get("operator_name") or card.get("registration") or "UNKNOWN")[:16]
            model = card.get("aircraft_model") or "UNKNOWN"
            line_3 = f"{card.get('adsb_icao', '')}:{model}"[:16]
            return self._write_json(
                {
                    "line_1": line_1,
                    "line_2": line_2,
                    "line_3": line_3,
                    "updated_at": payload.get("updated_at", ""),
                }
            )

        return self._write_json({"error": "not_found"}, status=404)

    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.address_string(), fmt % args)


def load_source_aircraft(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("SIM_INPUT_PATH must contain a JSON array")

    items = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        hex_value = str(item.get("hex", "")).strip()
        if not hex_value:
            continue
        items.append({"hex": hex_value, "flight": str(item.get("flight", "")).strip()})
    return items


def fetch_enrichment(base_url: str, hex_value: str):
    url = f"{base_url.rstrip('/')}/v1/aircraft/{hex_value}"
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def poll_loop(state: SimulatorState, base_url: str, source_path: Path, interval_seconds: int):
    while True:
        try:
            source = load_source_aircraft(source_path)
            flights = []
            for item in source:
                enrichment = fetch_enrichment(base_url, item["hex"])
                flights.append(
                    {
                        "adsb_icao": enrichment.get("adsb_icao", ""),
                        "flight": item.get("flight", ""),
                        "registration": enrichment.get("registration", ""),
                        "operator_name": enrichment.get("operator_name", ""),
                        "operator_icao": enrichment.get("operator_icao", ""),
                        "aircraft_model": enrichment.get("aircraft_model", ""),
                        "aircraft_type": enrichment.get("aircraft_type", ""),
                        "source": enrichment.get("source", ""),
                        "found": bool(enrichment.get("found", False)),
                    }
                )

            state.set_payload(
                {
                    "updated_at": utc_now_iso(),
                    "source_count": len(source),
                    "flights": flights,
                }
            )
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as err:
            logging.warning("poll failed: %s", err)
        time.sleep(interval_seconds)


def main() -> int:
    host = os.getenv("FLIGHTWALL_SIM_HOST", "0.0.0.0")
    port = int(os.getenv("FLIGHTWALL_SIM_PORT", "8090"))
    base_url = os.getenv("PI_ENRICHMENT_BASE_URL", "http://pi-enrichment:8080")
    source_path = Path(os.getenv("SIM_INPUT_PATH", "/app/sample_aircraft.json"))
    interval_seconds = int(os.getenv("SIM_POLL_SECONDS", "5"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="%(asctime)s %(levelname)s %(message)s")

    state = SimulatorState()
    Handler.state = state

    polling_thread = threading.Thread(
        target=poll_loop,
        args=(state, base_url, source_path, interval_seconds),
        daemon=True,
    )
    polling_thread.start()

    server = ThreadingHTTPServer((host, port), Handler)
    logging.info("Serving FlightWall simulator at http://%s:%d", host, port)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
