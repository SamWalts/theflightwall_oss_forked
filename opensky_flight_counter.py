#!/usr/bin/env python3
"""Track the number of nearby flights from OpenSky and print CSV rows."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/"
    "openid-connect/token"
)
OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"
EARTH_RADIUS_KM = 6371.0088
TOKEN_REFRESH_SKEW_SECONDS = 60
DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_TIMEOUT_SECONDS = 30


class GracefulShutdown:
    def __init__(self) -> None:
        self.stop_requested = False
        signal.signal(signal.SIGINT, self._request_stop)
        signal.signal(signal.SIGTERM, self._request_stop)

    def _request_stop(self, _signum: int, _frame: Any) -> None:
        self.stop_requested = True


@dataclass
class OpenSkyToken:
    access_token: str
    expires_at_monotonic: float


class OpenSkyClient:
    def __init__(self, client_id: str, client_secret: str, timeout_seconds: int) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout_seconds = timeout_seconds
        self._token: OpenSkyToken | None = None

    def _request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request = urllib.request.Request(url=url, data=data, method=method)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.load(response)

    def _ensure_token(self, force_refresh: bool = False) -> str:
        now = time.monotonic()
        if (
            not force_refresh
            and self._token is not None
            and now + TOKEN_REFRESH_SKEW_SECONDS < self._token.expires_at_monotonic
        ):
            return self._token.access_token

        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode("utf-8")
        payload = self._request_json(
            OPENSKY_TOKEN_URL,
            method="POST",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 1800))
        if not access_token:
            raise RuntimeError("OpenSky token response did not include access_token")

        self._token = OpenSkyToken(
            access_token=access_token,
            expires_at_monotonic=time.monotonic() + expires_in,
        )
        return access_token

    def fetch_states(self, latitude: float, longitude: float, radius_km: float) -> list[list[Any]]:
        params = urllib.parse.urlencode(build_bounding_box(latitude, longitude, radius_km))
        url = f"{OPENSKY_STATES_URL}?{params}"

        for attempt in range(2):
            token = self._ensure_token(force_refresh=attempt == 1)
            try:
                payload = self._request_json(
                    url,
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                )
                return payload.get("states") or []
            except urllib.error.HTTPError as error:
                if error.code == 401 and attempt == 0:
                    continue
                raise

        return []


def build_bounding_box(latitude: float, longitude: float, radius_km: float) -> dict[str, str]:
    lat_delta_deg = math.degrees(radius_km / EARTH_RADIUS_KM)
    safe_cos_lat = max(math.cos(math.radians(latitude)), 0.01)
    lon_delta_deg = math.degrees(radius_km / (EARTH_RADIUS_KM * safe_cos_lat))
    return {
        "lamin": f"{latitude - lat_delta_deg:.6f}",
        "lamax": f"{latitude + lat_delta_deg:.6f}",
        "lomin": f"{longitude - lon_delta_deg:.6f}",
        "lomax": f"{longitude + lon_delta_deg:.6f}",
    }


def haversine_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    sin_lat = math.sin(delta_lat / 2.0)
    sin_lon = math.sin(delta_lon / 2.0)
    haversine = sin_lat**2 + math.cos(lat_a) * math.cos(lat_b) * sin_lon**2
    return 2.0 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(haversine)))


def count_flights_within_radius(
    states: list[list[Any]], latitude: float, longitude: float, radius_km: float
) -> int:
    flight_count = 0
    for state in states:
        if len(state) < 7:
            continue
        state_longitude = state[5]
        state_latitude = state[6]
        if state_latitude is None or state_longitude is None:
            continue
        if haversine_km(latitude, longitude, float(state_latitude), float(state_longitude)) <= radius_km:
            flight_count += 1
    return flight_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count nearby OpenSky flights and print CSV rows continuously."
    )
    parser.add_argument("--latitude", type=float, required=True, help="Center latitude in decimal degrees.")
    parser.add_argument("--longitude", type=float, required=True, help="Center longitude in decimal degrees.")
    parser.add_argument("--radius-km", type=float, required=True, help="Search radius in kilometers.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Seconds between polls. Default: {DEFAULT_INTERVAL_SECONDS}.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout in seconds. Default: {DEFAULT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Fetch one sample row and exit.",
    )
    parser.add_argument(
        "--client-id",
        default=None,
        help="OpenSky client_id. Prefer OPENSKY_CLIENT_ID for long-running use.",
    )
    parser.add_argument(
        "--client-secret",
        default=None,
        help="OpenSky client_secret. Prefer OPENSKY_CLIENT_SECRET for long-running use.",
    )
    return parser.parse_args()


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    client_id = (args.client_id or os.environ.get("OPENSKY_CLIENT_ID", "")).strip()
    client_secret = (args.client_secret or os.environ.get("OPENSKY_CLIENT_SECRET", "")).strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "OpenSky credentials are required. Set OPENSKY_CLIENT_ID and "
            "OPENSKY_CLIENT_SECRET, or pass --client-id and --client-secret."
        )
    return client_id, client_secret


def validate_args(args: argparse.Namespace) -> None:
    if not -90.0 <= args.latitude <= 90.0:
        raise SystemExit("--latitude must be between -90 and 90.")
    if not -180.0 <= args.longitude <= 180.0:
        raise SystemExit("--longitude must be between -180 and 180.")
    if args.radius_km <= 0:
        raise SystemExit("--radius-km must be greater than 0.")
    if args.interval_seconds <= 0:
        raise SystemExit("--interval-seconds must be greater than 0.")
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be greater than 0.")


def emit_csv_rows(args: argparse.Namespace, client: OpenSkyClient) -> int:
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(
        [
            "timestamp_utc",
            "center_latitude",
            "center_longitude",
            "radius_km",
            "flight_count",
            "poll_status",
        ]
    )
    sys.stdout.flush()

    shutdown = GracefulShutdown()

    while not shutdown.stop_requested:
        timestamp = datetime.now(timezone.utc).isoformat()
        status = "ok"
        flight_count: int | None = None
        try:
            states = client.fetch_states(args.latitude, args.longitude, args.radius_km)
            flight_count = count_flights_within_radius(
                states, args.latitude, args.longitude, args.radius_km
            )
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, RuntimeError) as error:
            status = f"error:{type(error).__name__}"
            print(f"# {timestamp} request failed: {error}", file=sys.stderr, flush=True)

        row = [
            timestamp,
            args.latitude,
            args.longitude,
            args.radius_km,
            "" if flight_count is None else flight_count,
            status,
        ]
        writer.writerow(row)
        sys.stdout.flush()

        if args.run_once:
            return 0 if status == "ok" else 1

        sleep_remaining = args.interval_seconds
        while sleep_remaining > 0 and not shutdown.stop_requested:
            step = min(1.0, sleep_remaining)
            time.sleep(step)
            sleep_remaining -= step

    return 0


def main() -> int:
    args = parse_args()
    validate_args(args)
    client_id, client_secret = resolve_credentials(args)
    client = OpenSkyClient(
        client_id=client_id,
        client_secret=client_secret,
        timeout_seconds=args.timeout_seconds,
    )
    return emit_csv_rows(args, client)


if __name__ == "__main__":
    raise SystemExit(main())
