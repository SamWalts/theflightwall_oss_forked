"""Synthetic checks for the offline architecture and bounded import behavior."""

import json
import sqlite3
import tarfile
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import route_pipeline as pipeline
from route_reference import RouteStore, normalize_callsign, read_pointer
from server import BoundedHTTPServer, EnrichmentRequestHandler, EnrichmentStore

REVISION = "a" * 40
AIRLINE_HEADER = "Code,Name,ICAO,IATA,PositioningFlightPattern,CharterFlightPattern\n"
AIRPORT_HEADER = "Code,Name,ICAO,IATA,Location,CountryISO2,Latitude,Longitude,AltitudeFeet\n"
ROUTE_HEADER = "Callsign,Code,Number,AirlineCode,AirportCodes\n"


def write_source(directory):
    files = {
        "LICENSE": "Synthetic test data dedicated under CC0 1.0 Universal\n",
        "airlines/schema-01/airlines.csv": AIRLINE_HEADER +
        "BAW,British Airways,BAW,BA,,\nUAL,United,UAL,UA,,\nEZY,easyJet,EZY,U2,,\n"
        "ABC,Alias one,ABC,XY,,\nDEF,Alias two,DEF,XY,,\nZZ,IATA only,,ZZ,,\n",
        "airports/schema-01/E/EG.csv": AIRPORT_HEADER + "EGLL,Heathrow,EGLL,LHR,London,GB,51.47,-0.45,83\n",
        "airports/schema-01/K/KJ.csv": AIRPORT_HEADER + "KJFK,JFK,KJFK,JFK,New York,US,40.64,-73.78,13\n",
        "airports/schema-01/K/KL.csv": AIRPORT_HEADER + "KLAX,LAX,KLAX,LAX,Los Angeles,US,33.94,-118.4,125\n",
        "airports/schema-01/N/NR.csv": AIRPORT_HEADER + "NRT,Narita,,NRT,Tokyo,JP,35.76,140.38,141\n",
        "routes/schema-01/B/BAW-all.csv": ROUTE_HEADER +
        "BAW117,BAW,117,BAW,EGLL-KJFK\nBAW3YA,BAW,3YA,BAW,EGLL-KJFK-KLAX\n"
        "BAW9,BAW,9,BAW,EGLL-NRT\n",
        "routes/schema-01/U/UAL-1.csv": ROUTE_HEADER + "UAL123,UAL,123,UAL,EGLL-KJFK\n",
        "routes/schema-01/U/UAL-9.csv": ROUTE_HEADER + "UAL932,UAL,932,UAL,KJFK-EGLL\n",
        "routes/schema-01/E/EZY-all.csv": ROUTE_HEADER + "EZY1,EZY,1,EZY,EGLL-KJFK\nEZY0AB,EZY,0AB,EZY,EGLL-KJFK\n",
        "routes/schema-01/Z/ZZ-all.csv": ROUTE_HEADER + "ZZ1,ZZ,1,ZZ,EGLL-KJFK\n",
    }
    for relative in pipeline.NOTICE_PATHS:
        files.setdefault(relative, "Synthetic schema/credits fixture\n")
    for relative, content in files.items():
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class RouteReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        directory = Path(self.temporary.name)
        self.source = directory / "source"
        self.root = directory / "routes"
        write_source(self.source)
        self.manifest = self.prepare()
        self.store = RouteStore(self.root)

    def prepare(self, codes=None):
        return pipeline.import_generation(self.root, REVISION, codes or {"BAW", "UAL", "EZY", "ZZ"}, self.source)

    def test_known_overflight_order_provenance_and_original_identifier(self):
        value = self.store.resolve(" baw0117 ")
        route = value["route_reference"]
        self.assertEqual(value["callsign_received"], " baw0117 ")
        self.assertEqual(value["normalized_callsign"], "BAW117")
        self.assertEqual((route["departure_airport"], route["destination_airport"]), ("EGLL", "KJFK"))
        self.assertEqual(route["airports"][1]["iata"], "JFK")
        self.assertEqual(route["dataset_revision"], REVISION)
        self.assertEqual(route["kind"], "reference")
        self.assertFalse(route["flight_instance_verified"])

    def test_normalization_alias_ambiguity_and_unknowns(self):
        with self.store.session() as session:
            for original, key in (("EZY0001", "EZY1"), ("EZY0000", "EZY0"), ("EZY00AB", "EZY0AB"),
                                  ("U21234", "EZY1234"), ("BA117", "BAW117"), ("ZZ1", "ZZ1"), ("BAW3YA", "BAW3YA")):
                self.assertEqual(normalize_callsign(original, session.conn)[0], key)
        for callsign in (None, "", "N123AB", "BAW12345", "BAW1A2", "XY123", "XXX12", "BAW" + "0" * 20):
            self.assertIsNone(self.store.resolve(callsign)["route_reference"])
        self.assertEqual(self.store.resolve("XY123")["reason"], "ambiguous_airline_alias")
        self.assertEqual(self.store.resolve("BAW999")["reason"], "no_route_match")

    def test_source_can_contain_ambiguous_iata_routes_without_guessing(self):
        path = self.source / "airlines/schema-01/airlines.csv"
        with path.open("a") as stream:
            stream.write("XY,IATA legacy,,XY,,\n")
        path = self.source / "routes/schema-01/X/XY-all.csv"
        path.parent.mkdir(parents=True)
        path.write_text(ROUTE_HEADER + "XY123,XY,123,XY,EGLL-KJFK\n")
        self.prepare({"BAW", "XY"})
        self.assertEqual(self.store.resolve("XY123")["reason"], "ambiguous_airline_alias")
        self.assertIsNotNone(self.store.resolve("BAW117")["route_reference"])

    def test_partition_discovery_multi_stop_and_iata_airport(self):
        self.assertIsNotNone(self.store.resolve("UAL932")["route_reference"])
        route = self.store.resolve("BAW3YA")["route_reference"]
        self.assertEqual([a["code"] for a in route["airports"]], ["EGLL", "KJFK", "KLAX"])
        self.assertTrue(route["current_leg_ambiguous"])
        self.assertIsNone(route["departure_airport"])
        self.assertIsNone(route["destination_airport"])
        self.assertIsNone(self.store.resolve("BAW9")["route_reference"]["airports"][1]["icao"])

    def test_long_sequence_is_preserved_without_unbounded_airport_details(self):
        sequence = "-".join(["EGLL", "KJFK"] * 6)
        path = self.source / "routes/schema-01/B/BAW-all.csv"
        path.write_text(ROUTE_HEADER + f"BAW117,BAW,117,BAW,{sequence}\n")
        self.prepare()
        route = self.store.resolve("BAW117")["route_reference"]
        self.assertEqual(route["airport_codes"], sequence.split("-"))
        self.assertTrue(route["airport_details_omitted"])
        self.assertIsNone(route["airports"])
        self.assertIsNone(route["destination_airport"])

    def test_failed_imports_preserve_active_generation(self):
        original = read_pointer(self.root)
        for broken in ("BAW117,BAW,117,BAW,EGLL-ZZZZ\n", "BAW117,BAW,117,BAW,EGLL-KJFK\n" * 2,
                       "BAW117,BAW,117,BAW," + "X" * 70000 + "\n"):
            path = self.source / "routes/schema-01/B/BAW-all.csv"
            path.write_text(ROUTE_HEADER + broken)
            with self.assertRaises((ValueError, sqlite3.Error)):
                self.prepare()
            self.assertEqual(read_pointer(self.root), original)
            self.assertIsNotNone(self.store.resolve("BAW117")["route_reference"])
        self.assertEqual(list((self.root / "generations").glob(".staging-*")), [])

    def test_missing_partition_and_notice_fail_safely(self):
        with self.assertRaises(ValueError):
            self.prepare({"NOS"})
        (self.source / "routes/schema-01/CREDITS.md").unlink()
        with self.assertRaises(ValueError):
            self.prepare()

    def test_request_pins_generation_across_activation_and_rollback(self):
        with self.store.session() as pinned:
            path = self.source / "routes/schema-01/B/BAW-all.csv"
            path.write_text(ROUTE_HEADER + "BAW117,BAW,117,BAW,EGLL-KLAX\n")
            second = self.prepare()
            self.assertEqual(pinned.resolve("BAW117")["route_reference"]["destination_airport"], "KJFK")
            self.assertEqual(self.store.resolve("BAW117")["route_reference"]["destination_airport"], "KLAX")
            rolled = pipeline.rollback(self.root)
            self.assertEqual(rolled["generation"], self.manifest["generation"])
            self.assertEqual(read_pointer(self.root)["previous"], second["generation"])

    def test_override_is_separate_scoped_expiring_and_survives_import(self):
        now = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        pipeline.set_override(self.root, "BA117", "EGLL-KLAX", now.date().isoformat(),
                              start.isoformat(), end.isoformat(), "manual_airline", "Dated airline flight status",
                              "A1B2C3", verified=True)
        self.prepare()
        value = self.store.resolve("BAW117", aircraft_hex="a1b2c3", now=now)
        self.assertEqual(value["preferred_route"], "route_override")
        self.assertTrue(value["route_override"]["flight_instance_verified"])
        self.assertEqual(value["route_reference"]["destination_airport"], "KJFK")
        self.assertIsNone(self.store.resolve("BAW117", aircraft_hex="FFFFFF", now=now)["route_override"])
        self.assertIsNone(self.store.resolve("BAW117", aircraft_hex="A1B2C3", now=end)["route_override"])
        with self.assertRaises(ValueError):
            pipeline.set_override(self.root, "BAW117", "EGLL-KJFK", now.date().isoformat(),
                                  start.isoformat(), end.isoformat(), "manual", "Evidence", verified=True)

    def test_geography_can_reject_but_never_verify_a_flight(self):
        value = self.store.resolve("BAW117", position=(48, -35))
        self.assertEqual(value["geography_check"], "plausible")
        self.assertFalse(value["route_reference"]["flight_instance_verified"])
        value = self.store.resolve("BAW117", position=(-40, 130))
        self.assertEqual(value["reason"], "route_geography_rejected")
        self.assertIsNone(value["route_reference"])
        self.assertIsNotNone(self.store.resolve("BAW117", position=(-40, 130), max_excess_km=None)["route_reference"])

    def test_missing_invalid_generation_and_corrupt_rollback_are_safe(self):
        self.assertEqual(RouteStore(self.root / "missing").metadata()["status"], "missing")
        self.prepare()
        previous = self.root / "generations" / self.manifest["generation"] / "routes.sqlite3"
        previous.write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            pipeline.rollback(self.root)
        (self.root / "active.json").write_text('{"active":"../escape"}')
        self.assertEqual(self.store.metadata()["status"], "invalid")
        self.assertIsNone(self.store.resolve("BAW117")["route_reference"])

    def test_archive_import_streams_selected_partitions(self):
        archive_path = self.root.parent / "source.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            for path in self.source.rglob("*"):
                if path.is_file():
                    archive.add(path, arcname="standing-data/" + path.relative_to(self.source).as_posix())
        manifest = pipeline.import_generation(self.root, REVISION, {"UAL"}, archive=archive_path)
        self.assertEqual(manifest["counts"]["routes"], 2)
        self.assertIsNone(self.store.resolve("BAW117")["route_reference"])
        self.assertIsNotNone(self.store.resolve("UAL123")["route_reference"])

    def test_truncated_or_corrupt_gzip_preserves_active_generation(self):
        archive_path = self.root.parent / "source.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            for path in self.source.rglob("*"):
                if path.is_file():
                    archive.add(path, arcname="standing-data/" + path.relative_to(self.source).as_posix())
        complete = archive_path.read_bytes()  # Tiny synthetic archive, not production loading.
        pointer = read_pointer(self.root)
        for body in (complete[:-8], complete[:-8] + b"\x00" * 8):
            archive_path.write_bytes(body)
            with self.assertRaises((EOFError, OSError)):
                pipeline.import_generation(self.root, REVISION, {"UAL"}, archive=archive_path)
            self.assertEqual(read_pointer(self.root), pointer)

    def test_maintenance_lock_and_readonly_bounded_connection(self):
        with pipeline.maintenance_lock(self.root):
            with self.assertRaises(ValueError):
                self.prepare()
        with self.store.session() as session:
            self.assertEqual(session.conn.execute("PRAGMA cache_size").fetchone()[0], -1024)
            self.assertEqual(session.conn.execute("PRAGMA mmap_size").fetchone()[0], 0)
            with self.assertRaises(sqlite3.OperationalError):
                session.conn.execute("DELETE FROM routes")

    def test_api_works_without_wan_or_faa_and_exposes_unknowns(self):
        class Handler(EnrichmentRequestHandler):
            store = EnrichmentStore(self.root / "missing-faa.sqlite3")
            route_store = self.store

            def _fetch_live_aircraft(handler):
                return [{"hex": "A1B2C3", "flight": " BAW117 "}, {"hex": "FFFFFF"}]

            def log_message(handler, *args):
                pass

        server = BoundedHTTPServer(("127.0.0.1", 0), Handler, max_workers=2)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        # Save the local client before forbidding any application urllib WAN call.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        base = f"http://127.0.0.1:{server.server_port}"
        with patch("urllib.request.urlopen", side_effect=AssertionError("Runtime WAN is forbidden")):
            with opener.open(base + "/v1/routes/BAW117") as response:
                value = json.load(response)
            self.assertIsNotNone(value["route_reference"])
            with opener.open(base + "/v1/aircraft/live") as response:
                live = json.load(response)
            self.assertEqual(live["count"], 2)
            self.assertIsNone(live["aircraft"][1]["route_resolution"]["route_reference"])
            for endpoint in ("/health", "/v1/meta"):
                with opener.open(base + endpoint) as response:
                    self.assertEqual(json.load(response)["route_reference"]["status"], "ready")
            for query in ("?lat=nan&lon=0", "?lat=0", "?hex=INVALID", "?hex=A1B2C3&hex=FFFFFF"):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    opener.open(base + "/v1/routes/BAW117" + query)
                self.assertEqual(error.exception.code, 400)

    def test_http_worker_limit_returns_503_and_recovers(self):
        entered, release = threading.Event(), threading.Event()

        class Handler(EnrichmentRequestHandler):
            route_store = self.store

            def _handle_route_lookup(handler, callsign):
                entered.set()
                release.wait(2)
                super()._handle_route_lookup(callsign)

            def log_message(handler, *args):
                pass

        server = BoundedHTTPServer(("127.0.0.1", 0), Handler, max_workers=1)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        url = f"http://127.0.0.1:{server.server_port}/v1/routes/BAW117"
        failures = []

        def first_request():
            try:
                with opener.open(url, timeout=3) as response:
                    response.read()
            except Exception as err:
                failures.append(err)

        first = threading.Thread(target=first_request)
        first.start()
        try:
            self.assertTrue(entered.wait(2))
            with self.assertRaises(urllib.error.HTTPError) as error:
                opener.open(url, timeout=3)
            self.assertEqual(error.exception.code, 503)
        finally:
            release.set()
            first.join(3)
        self.assertEqual(failures, [])
        with opener.open(url, timeout=3) as response:
            self.assertEqual(response.status, 200)


if __name__ == "__main__":
    unittest.main()
