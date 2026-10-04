"""Exercise screen semantics against the shared canonical producer fixtures."""
import copy
import json
from pathlib import Path
import unittest

from render_mockups import canonical_display, canonical_view, departure_fallback, flight_lines, identifier

FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/m1/envelopes'


def envelope(name):
    return json.loads((FIXTURES / (name + '.json')).read_text())


def candidate(name):
    return envelope(name)['flights'][0]


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
        self.assertEqual(flight_lines(canonical_view(row), 'route')[2], 'REFERENCE ROUTE')
        row['route_reference'] = None
        self.assertEqual(flight_lines(canonical_view(row), 'route')[2], 'ROUTE UNKNOWN')

    def test_geometric_rate_is_not_labeled_barometric(self):
        row = copy.deepcopy(candidate('complete'))
        row['telemetry']['vertical_speed_source'] = 'geometric'
        self.assertEqual(flight_lines(canonical_view(row), 'motion')[1], 'GVS -640FT/M')
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
        self.assertIsNone(view['logo'])
        self.assertTrue(flight_lines(view, 'overview')[0])

    def test_hex_default_identity_keeps_registration_in_details(self):
        row = candidate('no-callsign')
        view = canonical_view(row)
        self.assertEqual(identifier(view), row['display_identifier'])
        self.assertEqual(flight_lines(view, 'airframe')[0], row['aircraft']['registration'])
        self.assertNotEqual(identifier(view), row['aircraft']['registration'])
        view['registration'] = 'ABCDEFGHIJKLMNOP'
        self.assertEqual(flight_lines(view, 'identity')[2], 'REG ABCDEFGHIJKLMNOP')

    def test_receiver_states_and_configuration_are_distinct(self):
        cases = {
            'initializing': 'initializing', 'clock-backward': 'initializing', 'clock-future': 'initializing',
            'frozen-source': 'receiver', 'old-snapshot': 'receiver',
            'source-missing': 'unavailable', 'invalid-source': 'invalid',
            'source-byte-limit': 'invalid', 'source-row-limit': 'invalid',
            'filter-unconfigured': 'config', 'healthy-empty': 'empty',
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                result = canonical_display(envelope(name))
                self.assertEqual(result, {'state': expected, 'flights': []})
        self.assertIsNone(canonical_display(envelope('complete'))['state'])
        self.assertIsNone(canonical_display(envelope('offline-clock'))['state'])

    def test_connection_priority_and_major_version(self):
        body = envelope('complete')
        for flags, expected in (
            ({'setup_active': True, 'wifi_connected': False}, 'setup'),
            ({'wifi_connected': False, 'pi_available': False}, 'wifi'),
            ({'pi_available': False}, 'pi'),
        ):
            self.assertEqual(canonical_display(body, **flags)['state'], expected)
        body['schema_version'] = 1
        self.assertEqual(canonical_display(body)['state'], 'pi')

    def test_expiry_preempts_dwell_without_claiming_empty_sky(self):
        body = envelope('complete')
        deadline = 5000 - max(body['receiver']['snapshot_age_ms'], body['receiver']['progress_age_ms'])
        self.assertIsNone(canonical_display(body, deadline - 1)['state'])
        self.assertEqual(canonical_display(body, deadline)['state'], 'receiver')
        row = body['flights'][0]
        row['position_seen_age_ms'] = 14999
        self.assertIsNone(canonical_display(body, 0)['state'])
        self.assertEqual(canonical_display(body, 1)['state'], 'expired')

    def test_dated_operator_and_logo_expire_independently(self):
        row = candidate('complete')
        row['operator']['match_kind'] = 'dated_override'
        row['operator']['valid_for_ms'] = 100
        self.assertIsNotNone(canonical_view(row, 99)['logo'])
        view = canonical_view(row, 100)
        self.assertIsNone(view['logo'])
        self.assertIsNone(view['operator_icao'])
        self.assertIsNone(view['airline_short'])
        self.assertEqual(view['ground_speed_kt'], 450)


if __name__ == '__main__':
    unittest.main()
