# Architecture decisions and open questions

Updated 2026-10-04. These decisions define the planned target. They do not imply
that the current code already implements it. See [architecture.md](../architecture.md)
and the [implementation checklist](implementation-plan.md).

For a new decision, record its ID, date, status, rationale, consequence, and the
superseded decision if applicable. Distinguish a design choice from an unverified
hardware or dataset fact.

## D001 — Local flight operation

Status: accepted for target design. Date: 2026-10-03.

Use the existing readsb receiver and a local Pi→ESP32 path. WAN access is confined
to installation and explicit reference maintenance. The wall must operate with
WAN disconnected and LAN active. Cloud adapter failure is never a reason to
introduce an external fallback into the local production build.

Consequence: current OpenSky/AeroAPI/CDN orchestration must be replaced. Missing
local reference coverage produces partial cards, not remote queries.

## D002 — One Pi API and a shared contract

Status: accepted for target design. Date: 2026-10-03.

Extend `pi_enrichment/` with a versioned `/v1/flights` contract and same-origin logo
assets, initially on port 8080. Retain the existing lookup API during migration.
Use polling and the current Python HTTP/SQLite foundation initially. The port-8090
simulator becomes a consumer/preview of the same contract.

Consequence: contract/schema/fixtures precede consumer implementations. A separate
broker, WebSocket service, or competing simulator schema needs a new decision with
evidence of a requirement the simpler boundary cannot meet.

## D003 — Pi candidate selection; ESP32 card selection

Status: accepted for target design. Date: 2026-10-03.

The Pi validates, filters, enriches, and deterministically orders a bounded set.
The ESP32 retains a selected hex, enforces dwell, changes pages, and expires cards.
This assigns one owner to display selection and avoids resets when order changes.

Consequence: the API does not drive a second competing dwell scheduler. Unknown
callsign/reference fields remain eligible when position and source data are fresh.

## D004 — Freshness is independent of response time and ESP32 wall clock

Status: accepted for target design; exact schema/clock rules finalize in M1.
Date: 2026-10-03.

Keep original receiver timestamps, explicit relative ages, and monotonic progress
tracking. A successful file read/HTTP response does not refresh the source. The
ESP32 uses local monotonic elapsed time to expire data without requiring WAN NTP.

Consequence: startup, frozen files, empty snapshots, future/backward clock changes,
slow requests, counter wraparound, and failed polling need distinct fixtures.
API, receiver, and reference-data health must remain independent.

## D005 — Immutable validated reference generations

Status: accepted for target design. Date: 2026-10-03.

Stage and validate DB/manifests/assets, then atomically change an active-generation
pointer. Requests pin a generation and updates retain the previous valid one.
Overrides remain separate. Maintenance does not run in the API startup path.

Consequence: the current transaction protects DB writes but does not activate CSV,
DB, manifest, and assets as one generation. Promotion and cleanup must account for
open readers and SQLite WAL state; failure must preserve rollback.

## D006 — Explicit source semantics and provenance

Status: accepted for target design. Date: 2026-10-03.

Keep registered owner, operating airline, FAA classification, ICAO type, telemetry
units, and route evidence separate. Resolve fields from dated overrides, applicable
readsb metadata, then approved reference data. Airline resolution uses recognized
callsign mappings, not registered owner. Unknown values remain null.

Consequence: the new flight contract cannot treat legacy `operator_name` as proof
of airline identity. FAA MASTER/ACFTREF joins and compatibility behavior need tests.

## D007 — Runtime provisioning includes Pi settings

Status: accepted requirement; BLE library/protocol selection pending M0/M5.
Date: 2026-10-03.

Versioned NVS settings and authenticated, physically enabled, time-limited BLE
must support Wi-Fi and custom Pi host/port changes. Preserve working Wi-Fi on a
failed change and distinguish Pi unavailability. Supply a usable local client.

Consequence: stock Wi-Fi-only provisioning is insufficient. Pin/test the actual
Arduino/PlatformIO stack before choosing APIs. BLE and coexistence require hardware
evidence; Docker and Wokwi cannot establish them.

## D008 — Approved assets converted before runtime

Status: accepted for target design. Date: 2026-10-03.

Keep artifact-specific provenance, licenses, attribution, and hashes. Convert
approved images to 24×24 row-major RGB565, most-significant byte first, composited
onto black. Use immutable relative paths and bounded firmware caching.

Consequence: arbitrary external URLs and runtime image conversion are excluded
from the flight path. Missing/unapproved/corrupt logos render a badge; global
coverage is not a prerequisite for useful local telemetry.

## D009 — Separate first proof from release acceptance

Status: accepted for execution plan. Date: 2026-10-03.

Establish a contract and minimal local Pi→ESP32 path before extensive enrichment
and visual work. BLE, approved-logo handling, final telemetry cards, failure
recovery, and physical offline/24-hour checks remain release requirements.

Consequence: Docker lookup checks, firmware builds, Wokwi visuals, and physical
acceptance are recorded separately. Milestones require evidence before completion.

## D010 — Keep observed airport events distinct from itinerary references

Status: accepted for optional M8 observations; superseded as the primary route
recommendation by D011. Detector thresholds require local samples.
Date: 2026-10-03.

Use the existing readsb track and a locally imported, public-domain airport/runway
catalogue to detect observed takeoff and landing transitions. Preserve event type,
confidence, source, and time. Keep observed event fields unknown without suitable
ground-transition evidence. A licensed callsign-route reference can still provide
an airport pair for an overflight; it is independent of local observation and
does not confirm a dated flight plan.

Consequence: M8 includes track replay, bounded persistent event history, and
receiver-specific validation. Refer to [route detection](route-detection.md) for
the researched inputs, detector policy, and coverage limits. There is no per-flight
WAN lookup or required API key.

## D011 — Use licensed callsign-route data for overhead-flight airport pairs

Status: accepted; Pi import/resolution and route contract implemented. Canonical
feed/display integration and local coverage validation remain pending.
Date: 2026-10-03.

The user's primary use case is overflights; about 95% will not land locally.
Use received callsigns to join CC0 VRS standing-data route records with their
companion airport and airline tables. Its published route schema and actual
BAW/UAL records were inspected, including `BAW117 → EGLL-KJFK`. This supplies
a free reference airport pair without waiting for a locally observed landing.
Import files during maintenance and resolve locally during operation.

Consequence: schema work in M1 must distinguish reference routes, dated verified
or manual routes, observed airport events, and unknown. M4 owns streamed imports,
normalization, provenance, and a coverage/correctness sample; M6 owns route display.
VRS schema 1 supplies no flight date or per-record verification time. Do not turn
a data-download timestamp or geographically plausible match into a current-flight
confirmation, and handle multi-stop leg ambiguity explicitly.

Manual Google/airline flight-status searches are useful for date-specific checks.
ADSBDB also documents a callsign endpoint returning origin/destination, but its
README restricts copying/publishing/incorporating route data without permission;
the API software's MIT license does not license that data. Prefer the verified
CC0 source for local imports. See [route lookup research](route-detection.md).

## D012 — Bounded route generations within the existing Pi service

Status: implemented for the independent route slice. Date: 2026-10-03.

Keep route maintenance in a separate CLI, and integrate indexed local resolution
into the existing Python API. Define the shared route object before consumer
adoption. This user-requested slice prepares M1/M4 route work without claiming
completion of the canonical flight feed, firmware migration, or full M4 release.

Use immutable route generations containing the route, airline, airport, manifest
and notice artifacts, with an atomic pointer and retained previous generations.
Keep the existing FAA registry migration separate until its semantics and staged
activation are implemented. Dated route overrides stay in a separate mutable
SQLite DB and survive import/rollback.

Memory remains independent of total route count: 64 KiB I/O, bounded CSV records,
streamed gzip/tar without a member index, 1 MiB SQLite caches, disk temporary
storage, no mmap, and eight API workers. Metadata stores per-file checksums in
SQLite rather than a worldwide artifact array. No automatic generation cleanup
races open readers; documented cleanup requires stopped processes.

The source contains routes longer than eight stops and historical ambiguous
IATA prefixes. Preserve full sequences up to 128 stops, omit airport descriptions
above eight stops, and leave current-leg endpoints unknown. Accept valid source
rows with ambiguous aliases, then return unknown for an ambiguous received alias.
Reject malformed rows, missing joins, corrupt/truncated archives, or empty requested
partitions before activation. A 2,000 km great-circle excess check can conservatively
reject references when fresh position is available; it cannot verify a flight.
All these limits/thresholds remain subject to real Pi/traffic measurements.

Evidence: the pinned worldwide source imports 620,396 routes with about 22.1 MiB
peak process RSS on this cloud runner. This supports the storage approach, not
the 1 GB Pi's complete receiver/API workload or a dated route-accuracy guarantee.

## D013 — Explicit compact flight projection and bounded contract draft

Status: M1 draft 0.1; runtime adoption and final bounds pending. Date: 2026-10-04.

Publish [detailed Pi-to-ESP32 contracts](api/README.md), producer schemas and
shared synthetic examples before M2/M3 integration. The feed identifies a Pi
process and source/state sequence, carries receiver and position/message ages,
and lets the ESP32 preserve absolute monotonic deadlines across repeated responses.
UTC timestamps and dated evidence require clock confidence; relative freshness
can work on a stable same-host clock without internet time.

Keep decoded measurements, calculated receiver values and external references
separate. Ground speed is not airspeed; a numeric altitude does not prove airborne
state; JSON does not provide independent freshness for every optional metric.
Aircraft ownership, callsign airline attribution, reference routes, dated evidence
and approved logo identity use independent documented joins.

Use response-local source IDs to avoid repeating generation provenance for every
field. The implemented diagnostic route object retains its full airport sequence
and evidence. `/v1/flights` explicitly projects it into bounded codes and display
values; sequences over eight stops are omitted whole with count/ambiguity flags,
and multi-stop current legs remain unknown. Neither source download time nor
geographic plausibility establishes today's itinerary.

Bound candidates by both count and actual serialized UTF-8 bytes. Retain the
nearest complete prefix, removing farthest rows and unused source entries until
the body fits 16,384 bytes. An eight-row maximal Unicode example exceeds the
budget even though its fields conform to the schema. Text abbreviations are
flagged; identity keys are never shortened into different plausible identities.

Integration note, 2026-10-04: main's initial local feed/parser was merged into dev.
It follows [the prototype API](local-flight-api.md), with flat fields and
Unix-second timestamps, rather than this draft. At integration both used `schema_version=1`; D013 now separates their versions. This integration
does not change the canonical draft or establish M2/M3 acceptance.

Consequence: schema checks provide reviewable M1 design evidence, not receiver,
HTTP or firmware implementation. M2 proves normalization/source progress and M3
proves memory, expiry and rendering. Same-origin 1,152-byte bitmap delivery and
approved assets remain M6. See [validation scope](api/validation.md).

## Provisional budgets

The 5 s receiver expiry, 15 s aircraft/position ages, eight-candidate cap, 16 KiB
flight-response bound, polling/dwell/timeouts, and four-logo cache are initial
design budgets from [architecture.md](../architecture.md). Freeze or revise them
using fixtures, actual readsb cadence, and ESP32 memory/latency measurements. They
are not measured guarantees. Draft 0.1 proposes 4 MiB/512 decoder rows, 4 KiB
HTTP headers and consumer JSON depth 16; actual samples and parser memory must
confirm or revise them. Existing diagnostic worker limits are implementation
facts, not proof of the full decoder/API workload on the target Pi.

## Open questions

| Question | Required evidence / milestone |
| --- | --- |
| Actual readsb path, service user, SDR ownership, receiver coordinates and cadence? | Read-only inspection of the existing Pi in M0. |
| ESP32 board variant, available heap, physical tile order, supply/brightness limit? | Board/wiring identification in M0; measured validation in M6. |
| Supported Arduino core, PlatformIO versions, BLE security/custom-endpoint APIs? | Pin and build the toolchain in M0; hardware proof in M5. |
| Can draft 0.1 schema, bounds, status/reason codes and clock recovery rules be frozen? | Review shared fixtures in M1 and record unmeasured installation/consumer budgets. Confirm cadence/clock/memory in M0/M2/M3, revising the contract explicitly if needed. |
| Exact airline/aircraft artifacts and individually approved logos? | Version/license/attribution manifests in M4/M6. |
| Do unknown-altitude and ground-inclusion settings behave as drafted? | Policy is in the flight contract; executable filter replay remains M2. |
| Is the Pi 5 with 1 GB sufficient alongside the actual decoder/services? | Memory/swap/decoder and latency baseline in M7. |
| Can the receiver hear ground/taxi messages well enough to capture airport events? | Record real samples and detection/miss rate near the intended airport in M8. |
| How many actual overhead callsigns match VRS, and how many airport pairs are correct for the current date/leg? | Measure match rate and dated Google/airline verification separately in M4; dataset samples are not local-coverage evidence. |

Resolve independent repository work with synthetic inputs while access is absent.
Never replace an unknown installation fact with the repository's sample value.

## D013 — Separate prototype and canonical flight versions

2026-10-04, screen/dev integration. Preserve the implemented flat `/v1/flights`
and schema version 1. Reserve `/v2/flights` and schema version 2 for the nested
M1 draft 0.2. Update the draft schema and shared envelopes together; logo and
route diagnostic versions remain 1. Do not reinterpret v1 in place or detect
versions by guessing field shape. M2 must implement v2 and M3 must explicitly
switch its parser/endpoint before canonical acceptance. This resolves the wire
identity collision without claiming the canonical runtime exists.

Screen views consume a validated canonical projection. Reference routes are
labeled `REFERENCE ROUTE`; applicable dated overrides use `DATED ROUTE`, or
`VERIFIED ROUTE` only with current aircraft-specific evidence. Multi-stop routes
never invent an active pair. City labels and observed/inferred airport events
remain optional future enrichment, with airport-code fallbacks today. Review
artwork remains unapproved for production.
