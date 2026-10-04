# Existing Pi endpoints and migration boundaries

M1 draft **0.1**, 2026-10-03. This records current interfaces and how the proposed
flight feed coexists with them. No legacy response meanings are changed by M1
documentation or schemas. Implementation sources are
[server.py](../../pi_enrichment/server.py) and
[route_reference.py](../../pi_enrichment/route_reference.py).

## 1. `GET /v1/aircraft/{adsb_icao}`

Ordinary known and unknown lookups return HTTP 200. Current fields:

| Field | Existing representation / meaning |
| --- | --- |
| `adsb_icao` | Uppercased legacy-normalized address. Current normalizer strips non-hex/pads; canonical feed must use strict validation instead. |
| `registration` | Registry string or empty string. |
| `operator_name` | Legacy imported value; can be registered owner. Not proof of an operating airline. |
| `operator_icao` | Imported string when supplied by the source; usually unknown in the FAA data. |
| `aircraft_model` | Existing source text; no completed ACFTREF join. |
| `aircraft_type` | Existing source text/classification; not guaranteed ICAO designator. |
| `source` | Generally `faa_registry`. |
| `updated_at` | Registry row/import timestamp string, not a telemetry timestamp. |
| `found` | Registry row found, not flight/route/logo found. |

Missing values are empty strings in this legacy API. The canonical feed uses
nulls, separates owner/operator/type/classification, and identifies field sources.
Do not reinterpret existing keys silently or use this legacy normalizer to make
malformed source addresses look valid. Any stored reference failure must remain
independent of canonical telemetry eligibility; ordinary source/schema faults
are not covered by the legacy known/unknown response guarantee.

This lookup stays available for existing simulator/other clients while migration
proceeds. The ESP32's new production feed must not perform one aircraft lookup
per candidate; the Pi performs bounded indexed joins before building `/v2/flights`.

## 2. `GET /v1/aircraft/live`

Current source adapter fetches configured tar1090/readsb JSON per request, not
the proposed cached snapshot reader. It returns an envelope with:

| Field | Meaning |
| --- | --- |
| `source` | `readsb_tar1090`. |
| `tar1090_url` | Configured source URI on successful response. |
| `count` | Number of legacy enriched aircraft. |
| `aircraft` | Legacy records below. |
| `updated_at` | HTTP handling time; not source progress or a freshness guarantee. |
| `error` | Error string on handled source failure. |

Aircraft rows include `adsb_icao`, trimmed `flight`, `lat`, `lon`, the legacy
registry reference fields and `found`, plus the implemented `route_resolution`
object. A missing callsign/route/registry match does not remove a row in this
adapter. Partial records can still lack the data needed for canonical geographic
eligibility.

The raw source read is capped at 4 MiB / 512 rows; exceeded limits and handled
source-fetch/JSON failures return HTTP 502 with an empty aircraft array. Route
lookups pin one immutable generation per request. Geographic route rejection
requires recent same-host source time and fresh `seen_pos`; unknown/future/old
snapshot times skip that check. This does not implement the complete cached
receiver/freshness state machine.

This endpoint lacks the normalized telemetry/relative-age contract, source
progress proofs, geographic candidate cap and 16 KiB feed guarantee. It must not
be plugged into the new ESP32 parser by renaming its `aircraft` array `flights`.

## 3. `GET /v1/routes/{callsign}`

The [implemented route contract](routes.md) and
[producer schema](route-resolution-v1.schema.json) describe this diagnostic
response. It preserves original callsign (within 16 chars), normalization/reason,
reference/override separation, up to 128 full ordered airport codes, up to eight
airport descriptions, source revision/retrieval age and dated evidence.

Unlike the canonical radio callsign, a diagnostic input can include a manually
entered IATA alias and padding. Input/query bounds and malformed-query HTTP 400
remain as implemented. No JSON `schema_version` is added to this existing object
by documenting its schema.

The canonical feed uses an explicit compact projection: shared provenance,
at most eight route codes or an omission flag/count, short airport display codes,
bounded evidence excerpt and remaining override validity. This reduces response
size without modifying the diagnostic endpoint or guessing multi-stop current legs.
Canonical dated verification also requires explicit trusted-clock handling;
the current diagnostic resolver uses the Pi wall clock without that new signal.

## 4. Health/meta and simulator

Existing `/health` and `/v1/meta` fields retain their legacy FAA meanings.
`/health` additionally exposes the prototype `receiver_status` (`ok`, `stale`,
`unavailable`); that field differs from M1's nested receiver object.
Additive receiver/capability/general-manifest summaries are described in
[health/meta](health-and-metadata.md). The legacy `stale` flag never becomes
a receiver/card expiry signal.

The implemented [initial local feed](../local-flight-api.md) on port 8080 is also
distinct from the canonical M1 draft. The prototype retains `/v1/flights` and version 1; canonical M1 reserves
`/v2/flights` and version 2 (D013). Neither endpoint may silently change shape.

Port 8090 belongs to the development simulator/preview. Its existing synthetic
`/v1/flights` is not the production contract on port 8080. M2/M3 migration must
make the preview a consumer of the canonical feed, with source fixtures supplying
that same producer contract. Until then, its current display/lookup smoke results
prove only the baseline synthetic enrichment flow.

## 5. Error and transition rules

- Keep legacy known/unknown lookup and route response shapes compatible.
- New production `/v2/flights` returns domain receiver states with HTTP 200;
  malformed requests use 400, unsupported methods 405, internal faults 500 and
  busy worker pools 503. These new target rules do not rewrite older handlers.
- Unknown paths return 404. Canonical error JSON is bounded
  `{error: <stable code>, message: <optional <=128 character detail>}`; consumers
  do not need to parse its text to expire live cards.
- Use structured reasons/diagnostic counts for source faults, not raw source
  dumps or credentials. Neither an error response nor a legacy timestamp revives
  a cached aircraft.
- Do not delete cloud firmware adapters as part of M1. M3 introduces a Pi-only
  production path and verifies that its runtime cannot call those adapters. The
  prototype now uses the Pi and excludes legacy adapters from its build; firmware
  build/physical acceptance and the rest of M3 remain pending.

Source/API migration acceptance still requires actual compatibility checks when
M2/M3 code changes. M1 provides definitions and fixtures, not deployed replacements.
