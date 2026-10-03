import json
from pathlib import Path
import tempfile
import unittest

from flight_feed import FlightFeed
from server import EnrichmentStore


class FlightFeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'aircraft.json'
        self.now = 1000
        self.feed = FlightFeed(EnrichmentStore(Path(self.tmp.name) / 'missing.db'), self.path,
                               clock=lambda: self.now)

    def snapshot(self, aircraft, timestamp=1000):
        self.path.write_text(json.dumps(dict(now=timestamp, aircraft=aircraft)))

    def aircraft(self, **changes):
        return dict(dict(hex='a1b2c3', lat=40, lon=-75, seen=0.2, seen_pos=1), **changes)

    def test_partial_aircraft_without_callsign_or_registry_is_retained(self):
        self.snapshot([self.aircraft()])
        record = self.feed.flights()['flights'][0]
        self.assertEqual(record['adsb_icao'], 'A1B2C3')
        self.assertIsNone(record['callsign'])
        self.assertIsNone(record['altitude_baro_ft'])
        self.assertIsNone(record['operator_name'])
        self.assertEqual(record['last_seen_at'], 999.8)

    def test_telemetry_units_and_ground_are_preserved(self):
        self.snapshot([self.aircraft(flight=' UAL123 ', alt_baro='ground', gs=12,
                                     ias=9, tas=10, geom_rate=-128, t='B738')])
        record = self.feed.flights()['flights'][0]
        self.assertEqual(record['callsign'], 'UAL123')
        self.assertTrue(record['on_ground'])
        self.assertIsNone(record['altitude_baro_ft'])
        self.assertEqual(record['ground_speed_kt'], 12)
        self.assertEqual(record['airspeed_ias_kt'], 9)
        self.assertEqual(record['vertical_speed_fpm'], -128)
        self.assertEqual(record['vertical_speed_source'], 'geometric')
        self.assertEqual(record['aircraft_type'], 'B738')

    def test_frozen_snapshot_expires_even_when_served_repeatedly(self):
        self.snapshot([self.aircraft()])
        self.assertEqual(self.feed.flights()['receiver_status'], 'ok')
        self.now += 6
        payload = self.feed.flights()
        self.assertEqual(payload['receiver_snapshot_at'], 1000)
        self.assertEqual(payload['receiver_status'], 'stale')
        self.assertEqual(payload['flights'], [])

    def test_empty_missing_and_malformed_are_distinct(self):
        self.assertEqual(self.feed.flights()['receiver_status'], 'unavailable')
        self.now += 1
        self.snapshot([], self.now)
        self.assertEqual(self.feed.flights()['receiver_status'], 'ok')
        self.now += 1
        self.path.write_text('{broken')
        self.assertEqual(self.feed.flights()['receiver_status'], 'unavailable')

    def test_invalid_hex_old_position_and_invalid_numbers_are_rejected(self):
        invalid = [self.aircraft(hex='~a1b2c3'), self.aircraft(seen_pos=16),
                   self.aircraft(lat=91), self.aircraft(lat=float('nan')),
                   self.aircraft(seen=-1), self.aircraft(lon=True)]
        self.snapshot(invalid + [self.aircraft(gs=float('inf'))])
        records = self.feed.flights()['flights']
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0]['ground_speed_kt'])

    def test_cache_and_candidate_cap(self):
        self.snapshot([self.aircraft(hex=f'{i:06x}') for i in range(20)])
        self.assertEqual(len(self.feed.flights()['flights']), 8)
        self.path.write_text('broken')
        self.assertEqual(self.feed.flights()['receiver_status'], 'ok')
        self.now += 1
        self.assertEqual(self.feed.flights()['receiver_status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
