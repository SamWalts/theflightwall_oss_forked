#!/usr/bin/env python3
"""Verify the Docker fixture stack after Compose reports both services healthy."""
import json
import os
import unittest
import urllib.request

PI_URL = os.getenv("FLIGHTWALL_TEST_PI_URL", "http://localhost:8080").rstrip("/")
SIM_URL = os.getenv("FLIGHTWALL_TEST_SIM_URL", "http://localhost:8090").rstrip("/")


def get_json(base_url, path):
    with urllib.request.urlopen(base_url + path, timeout=5) as response:
        return json.load(response)


class DockerSmokeTests(unittest.TestCase):
    def test_registry_ready(self):
        health = get_json(PI_URL, "/health")
        self.assertEqual(health["status"], "ok")
        self.assertTrue(health["db_exists"])
        self.assertFalse(health["stale"])
        self.assertEqual(get_json(PI_URL, "/v1/meta")["row_count"], 3)

    def test_known_aircraft(self):
        aircraft = get_json(PI_URL, "/v1/aircraft/a1b2c3")
        self.assertTrue(aircraft["found"])
        self.assertEqual(aircraft["adsb_icao"], "A1B2C3")
        self.assertEqual(aircraft["registration"], "N123AB")
        self.assertEqual(aircraft["operator_name"], "TEST UNITED")
        self.assertEqual(aircraft["aircraft_model"], "737-800")

    def test_unknown_aircraft(self):
        aircraft = get_json(PI_URL, "/v1/aircraft/FFFFFF")
        self.assertFalse(aircraft["found"])
        self.assertEqual(aircraft["registration"], "")
        self.assertEqual(aircraft["aircraft_model"], "")

    def test_simulator_enriches_all_sample_flights(self):
        payload = get_json(SIM_URL, "/v1/flights")
        self.assertEqual(payload["source_count"], 3)
        self.assertEqual(len(payload["flights"]), 3)
        for flight in payload["flights"]:
            with self.subTest(icao=flight["adsb_icao"]):
                self.assertTrue(flight["found"])
                aircraft = get_json(PI_URL, "/v1/aircraft/" + flight["adsb_icao"])
                for field in ("registration", "operator_name", "aircraft_model"):
                    self.assertEqual(flight[field], aircraft[field])

    def test_display_card(self):
        card = get_json(SIM_URL, "/v1/display/current")
        self.assertEqual(card["line_1"], "UAL123")
        self.assertEqual(card["line_2"], "TEST UNITED")
        self.assertEqual(card["line_3"], "A1B2C3:737-800")


if __name__ == "__main__":
    unittest.main(verbosity=2)
