# Local callsign-route contract

Implemented by [route_reference.py](../../pi_enrichment/route_reference.py).
This is the full diagnostic route contract for the existing Pi API and legacy
live enrichment. The proposed [canonical flight feed](flights.md) uses an explicit
compact projection with shared source IDs; it does not repeat this entire object
inside every candidate. That feed has an M1 draft schema/examples but no M2 runtime.
The simulator does not define this contract. A [producer schema](route-resolution-v1.schema.json)
describes the existing response without adding a version field to that endpoint.

## Requests

`GET /v1/routes/{callsign}` returns HTTP 200 for matches and unknowns. The received
identifier is preserved; trim/uppercase/leading-zero and known airline alias
normalization affect only the lookup key. Input is limited to 16 characters.

Optional query parameters:

| Parameter | Meaning |
| --- | --- |
| `hex` | Strict six-character aircraft ICAO hex; required to match an aircraft-specific override. |
| `flight_date` | `YYYY-MM-DD`, the flight's UTC start date; defaults to today's UTC date. This selects manual evidence and does not establish a flight's real date. |
| `lat`, `lon` | Both finite coordinates, within ±90/±180 degrees. Used only to reject geographically unrelated references. |

Malformed, repeated, or unsupported parameters return HTTP 400 with
`error=invalid_route_query`. Airport codes in route data are canonical VRS `Code`
values; a code may be ICAO or an IATA fallback.

The existing `/v1/aircraft/live` adds this object under `route_resolution` for
every aircraft, including aircraft without callsigns or route matches. It pins
one generation for the request. Geographic checks require a same-host source
`now` no more than five seconds old, and `seen_pos` plus snapshot age no more than
15 seconds; unknown/old/future snapshot times skip this check. This does not fix
that adapter's pending snapshot
freshness/caching migration. `/v1/aircraft/{hex}` retains its existing fields.
`/health` and `/v1/meta` add independent `route_reference` diagnostics.

## Resolution object

```json
{
  "callsign_received": " BAW117 ",
  "normalized_callsign": "BAW117",
  "route_reference": {
    "kind": "reference",
    "source": "vrs_standing_data",
    "matched_callsign": "BAW117",
    "airport_codes": ["EGLL", "KJFK"],
    "airports": [
      {"code": "EGLL", "name": "London Heathrow Airport", "name_truncated": false, "icao": "EGLL", "iata": "LHR", "latitude": 51.4706, "longitude": -0.461941},
      {"code": "KJFK", "name": "John F Kennedy International Airport", "name_truncated": false, "icao": "KJFK", "iata": "JFK", "latitude": 40.639801, "longitude": -73.7789}
    ],
    "airport_details_omitted": false,
    "departure_airport": "EGLL",
    "destination_airport": "KJFK",
    "current_leg_ambiguous": false,
    "dataset_revision": "d856ef1ed0fc492e8a3933ff4a938448ed008f66",
    "retrieved_at": "2026-10-03T22:13:12Z",
    "dataset_age_seconds": 60,
    "flight_instance_verified": false
  },
  "route_override": null,
  "preferred_route": "route_reference",
  "reason": "reference_match",
  "geography_check": "not_checked"
}
```

This is an illustrative serialization of the verified dataset row, not dated
verification of BA117. `retrieved_at` records import completion, not the time
someone confirmed an individual route. Age is measured on the Pi's wall clock
and clamped at zero after a backward clock change; it is not receiver freshness.

`route_reference` and `route_override` are independently nullable.
`preferred_route` names the chosen field, with an applicable override taking
precedence, or is null. Clients should label a reference **Reference route**;
only explicit, scoped, verified manual evidence supports **Verified for this
flight**. Missing references never exclude received aircraft.

An override has `kind=dated_override`, `source`, `evidence`, `matched_callsign`,
`flight_date`, `valid_from`, `valid_until`, nullable `aircraft_hex`, and the same
airport/leg fields. It has no VRS revision or import-age claim. Verification is
true only when the maintainer explicitly recorded dated verification and the
request matches its aircraft hex, callsign, flight date, and active validity
window. Callsign/date-only corrections remain unverified. This is recorded human
evidence, not a live status feed; diversions can still happen.

For two airports the first is the recorded departure and the second the recorded
destination. For longer sequences, both endpoint fields are null and
`current_leg_ambiguous=true`. The full ordered `airport_codes` is retained, with
a budget of 128 stops. For more than eight stops `airports=null` and
`airport_details_omitted=true`; clients can show the codes without allocating
hundreds of airport descriptions. Airport names are limited to 96 characters,
with `name_truncated` indicating abbreviation. Long valid sequences are never
silently reduced to a supposed active leg.

Geographic plausibility uses the minimum of
`distance(origin, position) + distance(position, destination) - distance(origin, destination)`
over consecutive legs, with great-circle distances. References exceeding the
default 2,000 km excess are rejected. This provisional, conservative threshold
is configurable through `--route-max-excess-km` / `ROUTE_MAX_EXCESS_KM`; zero
disables it. `geography_check` is `not_checked`, `plausible`, `rejected`, or
`unknown_airport_coordinates`. Plausibility never verifies the date/destination
and never chooses the current leg. Dated overrides are explicit human evidence
and are not silently removed by this reference check.

## Unknowns and health

Typical resolution reasons are `reference_missing`, `reference_invalid`,
`invalid_or_registration_callsign`, `unknown_airline_prefix`,
`ambiguous_airline_alias`, `no_route_match`, `reference_match`,
`route_geography_rejected`, `missing_airport_reference`, and
`dated_override_match`. An unreadable overrides database adds
`override_status=invalid`, retaining usable reference results.

Route diagnostics contain `status` (`missing`, `invalid`, or `ready`), `source`,
`generation`, `revision`, `retrieved_at`, `dataset_age_seconds`, `license`, and
table `counts`. Missing fields are null or empty counts. An old reference can
still supply a reference route; import age does not certify record accuracy.
Receiver health and the legacy FAA `stale` flag retain their separate meanings.

## Resource boundaries

Lookups use indexed queries and a read-only immutable SQLite connection with a
1 MiB page cache, memory mapping disabled, and no in-memory dataset cache.
Connections close after each request. The Pi HTTP server permits eight concurrent
request workers and returns HTTP 503 when full, with ten-second socket timeouts.
The legacy adapter rejects snapshots larger than 4 MiB or 512 aircraft with HTTP
502, preserving partial enrichment within those limits. Its response is not the
canonical eight-candidate/16 KiB flight feed. M1 drafts that feed's compact
representation; M2/M3 must prove normalization, encoded byte limiting and parser
memory before firmware adoption.
