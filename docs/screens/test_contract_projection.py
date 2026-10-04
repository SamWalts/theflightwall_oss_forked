"""Exercise screen semantics against the shared canonical producer fixtures."""
import copy
import json
from pathlib import Path
import unittest

from render_mockups import canonical_view, departure_fallback, flight_lines

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/m1/envelopes'


def candidate(name):
    return json.loads((FIXTURES / (name + '.json')).read_text())['flights'][0]


class ProjectionTests(unittest.TestCase):
    def test_reference_pair_is_not_verified_and_city_falls_back_to_code(self):
        view = canonical_view(candidate('complete'))
        self.assertEqual(flight_lines(view, 'route')[1:], ['EGLL>KJFK', 'REFERENCE ROUTE'])
        self.assertEqual(flight_lines(view, 'cities')[:2], ['FROM LHR', 'TO JFK'])
        self.assertEqual(departure_fallback(view), 'route')

    def test_multi_stop_does_not_invent_a_leg(self):
        for name in ('multi-stop', 'long-route'):
            view = canonical_view(candidate(name))
            self.assertIsNone(view['origin'])
            self.assertIsNone(view['destination'])
            self.assertEqual(flight_lines(view, 'route')[2], 'MULTI-STOP ROUTE')
            self.assertEqual(departure_fallback(view), 'overview')

    def test_dated_verification_and_expiry(self):
        row = candidate('dated-override')
        self.assertEqual(flight_lines(canonical_view(row), 'route')[2], 'VERIFIED ROUTE')
        row['route_override']['flight_instance_verified'] = False
        self.assertEqual(flight_lines(canonical_view(row), 'route')[2], 'DATED ROUTE')
        row['route_override']['remaining_validity_ms'] = 0
        self.assertEqual(flight_lines(canonical_view(row), 'route')[2], 'ROUTE UNKNOWN')

    def test_geometric_rate_is_not_labeled_barometric(self):
        row = copy.deepcopy(candidate('complete'))
        row['telemetry']['vertical_speed_source'] = 'geometric'
        self.assertEqual(flight_lines(canonical_view(row), 'motion')[1], 'VS --FT/M')
        row['telemetry']['vertical_speed_source'] = 'barometric'
        row['telemetry']['vertical_speed_fpm'] = 0
        self.assertEqual(flight_lines(canonical_view(row), 'motion')[1], 'VS 0FT/M')

    def test_unknown_operator_and_ground_keep_telemetry(self):
        row = candidate('ground-and-zero')
        view = canonical_view(row)
        self.assertEqual(flight_lines(view, 'overview')[1:], ['ALT GROUND', 'GS 0KT'])
        row = candidate('unknown-references')
        view = canonical_view(row)
        self.assertIsNone(view['operator_icao'])
        self.assertTrue(flight_lines(view, 'overview')[0])


if __name__ == '__main__':
    unittest.main()
