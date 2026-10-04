# Flight feed: Pi → ESP32

M1 draft **0.1**, 2026-10-03. Proposed `GET /v1/flights`, schema version 1.
The server and ESP32 implement [an initial prototype](../local-flight-api.md) at
this path, with a flat envelope, Unix-second timestamps and `ok` receiver status.
They do not implement this canonical M1 shape. Both currently use
`schema_version=1`; consumers must validate the envelope, and the wire
migration/version must be resolved before M1 freeze.
The [producer schema](flights-v1.schema.json) and
[synthetic fixtures](../../tests/fixtures/m1/README.md) define this draft together.
The human rules below cover relationships JSON Schema cannot express.

## 1. Request, response and purpose

The ESP32 requests `/v1/flights` from its configured Pi, normally every 1–2 s.
There are no flight-selection, coordinates, download-URL or airline query
parameters in this first production contract. The Pi's validated configuration
owns filtering. Selection/dwell belongs to the ESP32.

HTTP 200 supplies a complete current envelope, including when the receiver is
empty, stale or unavailable. Use `Content-Type: application/json`, identity
encoding and a compact UTF-8 body no larger than 16,384 bytes. The Pi reports
domain state inside the envelope. A failed HTTP request is not a replacement
envelope and cannot refresh any cached age or expiry deadline.

The feed is a snapshot, not an event log or a promise that all heard aircraft are
returned. At most eight eligible candidates are included. Every output row has a
valid strict ICAO address and fresh position/message information. Unknown
callsign, registration, model, operator, logo or route remains useful partial data.

## 2. Envelope dictionary

All keys below are required in a producer output. `null` is a deliberate unknown
value, not an empty string, zero or omitted field.

| Path | Type / bound | Meaning |
| --- | --- | --- |
| `schema_version` | Integer, exactly 1 | Feed major version. Reject unsupported versions before interpreting candidates. |
| `instance_id` | 32 lowercase hex characters | Random identifier for this API process lifetime; not a credential. Changes after API restart. |
| `sequence` | Unsigned 32-bit integer | Cached source/state revision. Advances on source progress or an actual receiver-state transition; not simply on each HTTP request. |
| `generated_at` | UTC `...Z` string ≤32 chars, or null | Serialization time when UTC is trusted. It never replaces receiver timestamps or establishes freshness. |
| `receiver` | Object, section 3 | Source liveness, age and clock interpretation. |
| `selection` | Object, section 5 | Eligibility, cap and byte-budget diagnostics. |
| `reference_sources` | Array, at most eight | Shared provenance for returned reference fields; avoids repeating revisions/manifests per aircraft. |
| `flights` | Array, at most eight | Complete bounded candidate rows, section 6. Non-ready receiver or unconfigured selection requires an empty array. |
| `diagnostics` | Object, section 8 | Bounded numeric counters from this sampled source/normalization, not cumulative evidence of a flight itinerary. |

Source IDs are unique within this response and are not stable array indexes or
identifiers to persist across polls. Every non-null source reference must resolve
to a row in `reference_sources`. Pin compatible reference generations for the
whole response. A route from one generation cannot cite another generation's
revision merely because activation happened during serialization.

The configured source families must also fit the eight-row provenance budget.
Group related tables under their actual generation; do not merge unrelated
sources or invent missing values to make IDs fit. If a configuration cannot
represent even one complete candidate within the source/body limits, report a
contract fault. A source row can describe a reference consulted for an unknown
result, such as an ambiguous alias; failed lookup is still provenance for that row.

| `reference_sources[]` field | Type | Meaning |
| --- | --- | --- |
| `id` | 1–8 lowercase letters/digits/underscore, starts with a letter | Response-local join key, e.g. `vrs`, `faa`, `logos`, `local`. |
| `kind` | `aircraft_reference`, `airline_route_reference`, `logo_manifest`, `local_overrides`, `receiver_reference` | Component supplying the value. |
| `source` | 1–32 lowercase identifier characters | Named provenance, e.g. `vrs_standing_data`. |
| `generation` | String ≤64 or null | Immutable reference generation or explicit version; mutable overrides may not have one. |
| `revision` | String ≤64 or null | Artifact/source revision, not the flight date. |
| `retrieved_at` | Trusted UTC string or null | Import/retrieval completion time when known. |
| `age_seconds` | Nonnegative 31-bit integer or null | Age of the reference import when UTC is trustworthy; not per-record accuracy. |
| `license_label` | String ≤32 or null | Brief manifest label. Full artifact terms/credits live on the Pi and in metadata. A label alone does not approve a logo. |

For example, aircraft field sources may all reference one FAA generation, while
the documented MASTER/ACFTREF column mappings distinguish the particular table.
VRS airline and route values cite the same imported VRS generation. Full source
URLs, credits, individual hashes and override evidence are diagnostics, not
repeated per-card display fields.

## 3. Receiver dictionary and states

| Path under `receiver` | Type | Meaning |
| --- | --- | --- |
| `status` | `initializing`, `ready`, `stale`, `unavailable`, `invalid` | Domain state, distinct from API health. |
| `reason` | Stable reason code | Specific state cause in the table below. Human text is not the protocol key. |
| `source` | `readsb_file` or `readsb_loopback_http` | One explicitly configured local input; no WAN fallback. |
| `source_timestamp` | Finite Unix seconds or null | Original numeric readsb `now`, preserved even if its absolute UTC cannot be trusted. |
| `snapshot_at` | UTC string or null | The original source timestamp formatted as UTC only when UTC is trusted. |
| `snapshot_age_ms` | Nonnegative 31-bit integer or null | Age of that source snapshot at serialization. Never age since an HTTP response. |
| `progress_age_ms` | Nonnegative 31-bit integer or null | Monotonic time since source timestamp last demonstrably advanced. |
| `clock_confidence` | `trusted_utc`, `same_host`, `uncertain` | What can be inferred from source/Pi time; see section 4. |
| `last_success_at` | UTC string or null | Last successfully parsed source read, when UTC is trusted; successful reading alone does not prove progress. |
| `last_success_age_ms` | Nonnegative 31-bit integer or null | Monotonic time since that successful read. It can be small while a frozen source is stale. |

| State | Reason | Flights / consumer action |
| --- | --- | --- |
| `initializing` | `startup` | No source read yet; no normal card. |
| `initializing` | `awaiting_progress` | First valid snapshot exists; require a later advancing source timestamp before ready. |
| `initializing` | `clock_recovery` | Clock epoch/jump needs re-established source progress; clear normal cards. |
| `ready` | `ok` | Source progressed, snapshot and progress ages are each <5,000 ms. Empty can be healthy. |
| `stale` | `source_frozen` | Source timestamp has not progressed for 5,000 ms. Re-reading/serving does not revive it. |
| `stale` | `source_too_old` | Source clock is interpretable but snapshot age is ≥5,000 ms. |
| `unavailable` | `source_missing` | No configured source file/resource. |
| `unavailable` | `source_unreadable` | Local I/O failure/timeout/permission problem. |
| `invalid` | `source_malformed` | Not an accepted JSON object/aircraft array or malformed source content. |
| `invalid` | `source_oversized` | Raw input exceeds the byte budget. |
| `invalid` | `source_aircraft_limit` | Input contains more than 512 rows. |
| `invalid` | `invalid_source_time` | Missing, non-finite, wrong-type or out-of-range `now`. |

Missing/malformed/oversized current input must not leave an old ready array in the
response. The Pi can retain bounded diagnostic facts, but all non-ready envelopes
contain `flights=[]`, zero eligible/returned counts and no truncation claim.
Reference failures are independent: telemetry can remain ready with unknown
enrichment. Missing filter coordinates are also separate from receiver health.

## 4. Clock, source progress and expiry

### 4.1 Pi rules

The configured input is local to the Pi, so readsb and FlightWall can use the
same system clock. Correct global UTC is not necessary to compare two stable
same-host timestamps. It is necessary for dated manual evidence and truthful
absolute timestamps.

- `trusted_utc`: system UTC has a verified basis, such as a usable local clock or
  synchronized OS time. Absolute timestamps and dated evidence can be evaluated.
- `same_host`: source and Pi clocks are comparable and stable, but absolute UTC
  has not been established. Return relative ages; absolute `generated_at`,
  `snapshot_at`, `last_success_at`, `last_seen_at`, and `position_seen_at` are null.
  Do not activate dated verified overrides solely from an apparently plausible year.
- `uncertain`: the source/Pi time relation is not established. Hold initializing
  or another applicable failure state; do not send normal candidates.

At startup require two successfully parsed snapshots with distinct increasing
source timestamps, observed within the freshness window. Healthy empty snapshots
qualify. File mtime, JSON-content changes, successful reads, message counters and
new HTTP response times cannot substitute for source timestamp progress.

Compare wall-clock movement with monotonic movement. A backward source jump or
a wall/source jump materially inconsistent with monotonic elapsed time resets
the progress baseline and holds `clock_recovery` until progress is re-established.
Draft tolerances are 250 ms for a slightly future source timestamp at read
completion and 2,000 ms for wall/source versus monotonic jump detection; validate
these against M0 cadence. A future timestamp outside tolerance is not a negative
age that can grant extra lifetime. Out-of-domain/missing time is invalid input.

For a stable same-host clock, define at source read completion:

```text
snapshot_age_at_read = max(0, read_completion_wall_time - source_now)
snapshot_age_at_serialize = snapshot_age_at_read + monotonic_elapsed_since_read
last_seen_age = snapshot_age_at_serialize + source_seen
position_seen_age = snapshot_age_at_serialize + source_seen_pos
```

Convert seconds to milliseconds and round positive ages **up**. Do not reset the
snapshot baseline on repeated reads of the same `now`; use the earlier progress
anchor and conservative age rather than reducing age after a clock adjustment.
If the clock relation breaks, reinitialize instead of repairing it by resetting
ages. `seen`/`seen_pos` must be finite nonnegative numbers; booleans and numeric
strings are not accepted as measurements. Expired/missing position or message
ages exclude that row from candidate eligibility.

When UTC is trusted, `last_seen_at = source_now - seen` and
`position_seen_at = source_now - seen_pos`. They describe the original source
updates; they are not computed from the later serialization timestamp. These
timestamps are diagnostic; ESP32 expiry uses supplied ages and its own clock.

### 4.2 ESP32 rules

Record local monotonic time before starting a request. At any later use:

```text
effective_age_ms = supplied_age_ms + elapsed_since_request_start_ms
remaining_ms = limit_ms - effective_age_ms
```

A normal card requires all three remaining lifetimes positive: receiver snapshot
5,000 ms, aircraft message 15,000 ms, and aircraft position 15,000 ms. Progress
age also must remain below 5,000 ms. Request/transfer/parse delay counts against
lifetime; a successful late response cannot restore an expired card.

For the same `instance_id` and `sequence`, repeated polls cannot extend previously
established expiry deadlines. Retain the earlier deadline for the same cached
sample. Accept a higher revision with freshly calculated ages; reject older
revisions from the same instance. A receiver failure state clears normal cards
immediately. A new instance clears cached sample/selection state before accepting
new ready data. If the counter would wrap, the producer begins a new instance ID.

The client makes at most one flight request in flight and tags work with its
local settings/configuration epoch. Late work from an earlier host/port is
discarded. After ESP32 reboot no aircraft cache/deadline is restored from NVS.
Use unsigned modular subtraction for local tick elapsed time; intervals must
stay below half the counter range. With millisecond 32-bit ticks this survives
wraparound because flight deadlines are seconds, not weeks. M3 must exercise
this behavior on shared timing fixtures; it has not been demonstrated by this draft.

## 5. Filtering, ordering and byte limits

| Path under `selection` | Meaning |
| --- | --- |
| `status` | `ready` means a validated geographic center/filter is available; `unconfigured` means no geographic candidates can be selected. |
| `eligible_count` | Valid, fresh, filter-passing candidates before count/body caps, ≤512. |
| `returned_count` | Exactly `len(flights)`, ≤8. |
| `truncated` | Whether count or body budgeting omitted otherwise eligible candidates. |
| `truncation_reason` | Null, `count_limit`, `byte_limit`, or `count_and_byte_limit`. |

Require explicitly verified/configured center coordinates; never silently adopt
sample coordinates. Require valid strict hex, usable `seen`, usable fresh
`seen_pos`, and decoded finite latitude/longitude. Do not promote `lastPosition`
or `rr_lat`/`rr_lon` into a fresh measured fix. Non-ICAO addresses are diagnostic
counts. Whether non-transponder vehicles/external sources are allowed must be
explicit in the installation's source/classification policy.

Apply configured radius, optional view-bearing sector and optional altitude
limits on the Pi. Radius boundaries are inclusive. Use measured position for
distance/bearing; ground speed or heading cannot substitute for position.
Missing altitude is included by default, even with an altitude range, unless the
Pi's explicit `require_known_altitude` option says to exclude it. Ground altitude
remains null; ground inclusion is an explicit filter setting, initially enabled
in synthetic examples. Unknown enrichment is never a filter reason.

Quantize emitted distance to 0.01 km, then order by that distance and uppercase
hex as tie breaker. Apply radius tests to the unrounded distance. Bearing is
degrees clockwise from true north, quantized to 0.1 degree and normalized into
[0,360). Coincident/undefined bearing is null; a coincident fix is not dropped
solely by a view-bearing filter. Latitude/longitude retain at most six decimals.

Take the nearest prefix of at most eight rows. Build only the needed bounded
source table, serialize compact UTF-8, then measure the actual body bytes. If it
does not fit 16,384 bytes, remove the farthest row, rebuild/remove unused source
entries and repeat. Report byte truncation. Do not replace reference fields with
invented empty values or send a partially serialized row. Field/source limits
must guarantee that at least one maximal row can fit. If an implementation
violates that guarantee, report a server/contract fault rather than healthy empty.

HTTP 200 body size is the bound, not pretty fixture-file length. JSON strings
can use multiple UTF-8 bytes per character; JSON escaping and numerical rendering
also count. Numeric formatting is bounded by the declared ranges and producer
rounding. A schema-valid eight-row object can still exceed the byte contract.

## 6. Candidate dictionary

### 6.1 Identity, timing and position

| Path under `flights[]` | Bound / meaning |
| --- | --- |
| `adsb_icao` | Exactly six uppercase hex digits. Stable address key for this card, not a unique worldwide flight instance. |
| `callsign_received` | Original printable ASCII up to eight characters, or null. Preserve padding/case as received. Oversized/control-character source text becomes unknown with a diagnostic. |
| `callsign_normalized` | VRS lookup key up to seven characters, or null; never replaces the original display identity. |
| `display_identifier` | Printable non-space ASCII up to eight characters: trimmed received identifier when usable, otherwise hex. Do not invent a marketing flight number. |
| `last_seen_at`, `position_seen_at` | UTC strings or null; original update times when clock confidence permits. |
| `last_seen_age_ms`, `position_seen_age_ms` | Integers 0–14,999 at serialization. Separate ages; source/message activity cannot refresh position. |
| `position.latitude`, `.longitude` | Finite degrees in [-90,90] / [-180,180]. Required and non-null for eligible wire candidates. |
| `position.distance_km` | Finite 0–20,100 km; computed from the validated viewing center. |
| `position.bearing_deg` | Finite [0,360), or null when undefined. Direction from viewing center, not aircraft heading. |
| `position.source` | `adsb`, `adsr`, `tisb`, `mlat`, `unknown`; label field provenance, not aircraft model. |

For an accepted measured fix, use readsb's field-origin arrays before its general
message `type`: a latitude/longitude listed in `mlat` is marked `mlat`; otherwise
a coordinate listed in `tisb` is marked `tisb`. Without those flags, map
`adsb_icao`/`adsb_icao_nt` to `adsb`, `adsr_icao` to `adsr`, `tisb_icao` to `tisb`
and `mlat` to `mlat`; other accepted inputs stay `unknown`. These labels do not
authorize source classes excluded by the installation policy. They also do not
claim that every optional metric in the same row has that position's origin.

The raw normalizer can hold unknown position fields, but cannot emit those rows
as geographic candidates. This is why the wire schema requires complete latitude
and longitude while other optional measurements remain nullable.

### 6.2 Telemetry

All telemetry keys are present; each numeric value can be null. The bounds are
draft input sanity/serialization bounds, not physical guarantees. Out-of-range
optional data becomes null with diagnostics; do not remove a fresh positioned
aircraft because one optional metric is bad.

| Path under `telemetry` | Unit / bound | Source rule |
| --- | --- | --- |
| `altitude_baro_ft` | Integer feet, -2,000…100,000 or null | Numeric `alt_baro`; `"ground"` produces null. |
| `altitude_geom_ft` | Integer feet, -2,000…150,000 or null | `alt_geom`; not pressure altitude or AGL. |
| `ground_speed_kt` | Knots, 0…3,000 or null | `gs`. |
| `ground_track_deg` | True degrees [0,360) or null | `track`; not magnetic/true heading. |
| `airspeed_ias_kt` | Knots, 0…2,000 or null | `ias` only. |
| `airspeed_tas_kt` | Knots, 0…3,000 or null | `tas` only. |
| `vertical_speed_fpm` | Signed integer feet/minute, ±30,000 or null | Valid `baro_rate`, else valid `geom_rate`, else null. Preserve zero/sign. |
| `vertical_speed_source` | `barometric`, `geometric`, or null | Must identify the chosen rate; null exactly when rate is null. |
| `ground_state` | `airborne`, `ground`, `unknown` | Use decoder surface/airborne evidence; do not infer from low speed/altitude. |

For the generic readsb JSON adapter, `alt_baro: "ground"` supplies explicit
surface evidence. Otherwise emit `ground_state="unknown"` unless the installed
exporter supplies a separately verified airborne-state signal. A numeric altitude
alone does not establish the current state. This is why the complete synthetic
example uses `unknown` despite a numeric barometric altitude.

Speeds round to 0.1 kt and track to 0.1 degree. Integer feet/rates remain integer;
do not cast booleans/strings to measurements. Do not synthesize IAS/TAS from GS.
Altitude is not terrain clearance or a promise of local altimeter correction.
The [receiver inventory](../adsb-receiver-data.md) explains per-field age limits.

### 6.3 Aircraft references, operator and logo

| Path | Meaning / bound |
| --- | --- |
| `aircraft.registration` | Nullable reference registration, ≤16 characters. |
| `aircraft.registered_owner` | Nullable owner, ≤64; never copied into the operator. |
| `aircraft.manufacturer` | Nullable manufacturer, ≤40. |
| `aircraft.model` | Nullable model text, ≤48; not automatically an ICAO designator. |
| `aircraft.icao_type_designator` | Nullable 2–4 uppercase alphanumeric designator from an applicable source. |
| `aircraft.faa_classification` | Nullable bounded classification code, ≤8; separate from model. |
| `aircraft.sources` | Same six keys, each source ID or null. Known values require applicable source provenance; unknown values have null source. |
| `abbreviated_fields` | Up to four unique paths naming abbreviated owner/manufacturer/model/operator text. Empty when none. Identity codes are never cropped into plausible keys. |
| `operator.id` | Nullable stable local identity `airline:{canonical_code}`. It identifies the resolved airline reference, not registration ownership. |
| `operator.name` | Nullable bounded name, ≤64. Long source text needs a documented display abbreviation; never silently merge two airline identities. |
| `operator.icao`, `.iata` | Nullable recognized 3-letter ICAO / 2-character IATA codes. An IATA alias can be ambiguous. |
| `operator.match_kind` | `unknown`, `callsign_reference`, `dated_override`. A prefix match remains reference attribution, not proven current operation. |
| `operator.source_id` | Response-local source ID or null. Unknown operator has null identity/name/codes/source. |
| `operator.valid_for_ms` | Positive remaining validity ≤24 h for dated overrides; null for ordinary references/unknowns. |
| `logo` | Null or the [logo descriptor](logos.md). `logo.operator_id` must equal the current resolved operator ID. |

The [join contract](enrichment-joins.md) defines source precedence, aliases,
owner/operator separation and the independent asset-manifest join. A recognized
airline does not guarantee an approved logo. Null logos use a text/neutral badge;
they never cause a new route/aircraft request to a cloud service.

Text values are bounded display projections of retained Pi reference records.
When shortening owner/manufacturer/model/operator names, retain source provenance
and list the field in `abbreviated_fields`; never use abbreviated text as a join
key. Reject control characters. An invalid/oversized registration, airline code
or ICAO type becomes unknown rather than a truncated different identity.

### 6.4 Compact route references and dated evidence

Keep `route_reference` and `route_override` independently nullable.
`preferred_route` is `route_override`, `route_reference`, or null, naming the
selected available value. `route_reason` uses the diagnostic resolver's stable
reason vocabulary; expiry or unavailable evidence can leave only a reference.

Both compact route objects share:

| Field | Rule |
| --- | --- |
| `source_id`, `matched_callsign` | Response source join and exact normalized callsign. |
| `stop_count` | Full ordered source-sequence length, 2–128. |
| `airport_codes` | Full sequence when ≤8 stops; otherwise null. Codes are VRS canonical airport codes, ICAO or IATA fallback. |
| `sequence_omitted` | True exactly when `stop_count>8`; complete sequence remains available in the Pi diagnostic endpoint/DB. |
| `departure_airport`, `destination_airport` | Canonical codes for exactly two stops; both null for a multi-stop sequence. |
| `departure_display_code`, `destination_display_code` | Prefer resolved airport IATA code, otherwise canonical code; null when leg ambiguous. Never use a guessed marketing airport code. |
| `current_leg_ambiguous` | False for an unambiguous two-airport reference; true for multi-stop source sequence. Position does not choose a leg. |
| `flight_instance_verified` | Always false for VRS reference; conditional dated human evidence for overrides. |

`route_reference` also has `kind="reference"` and `geography_check`:
`not_checked`, `plausible`, `rejected`, `unknown_airport_coordinates`. A rejected
reference is not a preferred route and normally projects as null with
`route_reason="route_geography_rejected"`. Dataset revision/retrieval age are in
the referenced shared source row, not repeated in every candidate.

`route_override` adds `kind="dated_override"`, `source_label` (≤64),
`flight_date`, `valid_from`, `valid_until`, `remaining_validity_ms`, nullable
`aircraft_hex`, `evidence_excerpt` (≤96), and `evidence_truncated`. Full evidence
can be inspected through the existing diagnostic route API. Remaining validity
is computed by the Pi with trusted UTC; the ESP32 subtracts request elapsed time.
At expiry remove the override/preference/verified label, use an available still
valid reference, or show Unknown. The flight's own telemetry expiry still applies.

Verification requires explicit human verification, exact callsign/date/aircraft
scope, matching active validity window, and trusted Pi UTC. Callsign/date-only
corrections can override reference values but remain unverified. Neither download
time, geographic plausibility nor airline-prefix recognition verifies this flight.
An actual diversion can still make a previously checked plan incorrect.

This is an explicit projection of [the implemented diagnostic route object](routes.md),
not a change to that endpoint. Diagnostic fields such as full airport descriptions,
128-stop arrays and repeated revision/age are reduced only in this new feed.
Never concatenate the whole diagnostic response into every candidate and assume
it fits the firmware budget.

### 6.5 Observed airport fields

`observed_departure_airport` and `observed_arrival_airport` are separate nullable
objects with `airport_code`, `event_id`, `source_id`, `observed_at` and
`confidence`. Their future event detector belongs to M8; current/first M2
implementation emits null. The draft schema reserves bounded objects, but does
not approve detector thresholds or establish continuity/leg evidence.
Do not fill these fields from a callsign route, airport proximity or heading.

## 7. Consumer selection and degraded display

Validate the envelope/version/state before accepting rows. Reject duplicate JSON
keys, non-finite numbers and malformed JSON,
oversized bodies or invalid required outer structure as a failed feed. With a
usable outer envelope, invalid individual identity/position/timing rows can be
discarded while valid rows survive. Malformed optional references/metrics become
unknown with a contract diagnostic; they do not invalidate fresh core telemetry.
A producer still fails conformance if it emits those malformed fields.

Keep the selected hex while it appears and remains eligible; response reordering
does not restart its five-second dwell. New reference text/assets do not reset
dwell. When selected hex disappears from a successful current candidate set,
expires, or receiver becomes non-ready, end its normal card immediately. Dwell
cannot override expiry. A failed poll retains only still-valid cached content.

| Condition | Display state |
| --- | --- |
| Unsupported/invalid feed or Pi transport failure | Pi/feed problem; cached normal card lasts only to its existing deadline. |
| Receiver initializing/unavailable/invalid | Explicit receiver state, no live card. |
| Receiver stale or local snapshot deadline expired | Stale receiver, no normal card. |
| Receiver ready but selection unconfigured | Viewing-location/filter setup state; no fake empty-sky claim. |
| Ready, configured, no eligible candidates | No nearby aircraft. Diagnostics distinguish input-empty and filtered-out. |
| Fresh partial candidate | Callsign or hex plus known metrics and neutral fallbacks. |
| Unknown operator/logo/route | Continue telemetry; use a badge/Unknown route. |
| Reference airport pair | Display as a reference/likely pair, never as an observed landing. |
| Verified dated override | Label only while evidence and aircraft scope remain valid. |

## 8. Diagnostic counters and pending proof

`diagnostics` contains `input_aircraft_count`, `invalid_address_count`,
`missing_position_count`, `expired_position_count`, `expired_message_count`,
`filtered_count`, `invalid_metric_count`, and `reference_error_count`.
They are nonnegative bounded 31-bit counters for the sampled cache/normalization.
They can overlap and are not a partition to sum into input count. Metric errors
can exceed aircraft count. Do not increment them simply because another client
requested the same cached sample.

Schemas/fixtures cover producer shape, byte cap and relationships; M2 must still
prove source normalization/progress/clock transitions, and M3 must prove parser
heap, asynchronous expiry, counter wrap and rendering behavior. Actual receiver
samples, toolchain/power/wiring details and hardware latency remain M0/M7 work.
