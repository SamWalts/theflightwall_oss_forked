# Implementation checklist

Reviewed 2026-10-04. The architecture review/documentation is complete; all
implementation milestones below remain planned or partial. Existing enrichment features
are a baseline, not completion of the local wall migration.

Follow [architecture.md](../architecture.md). Record completion evidence and
handoffs in [project context](project-context.md). Commands are in
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Dependency order

`M0 → M1 → M2 → M3` establishes the minimal local path. Complete M4, M5, and M6
before M7 release acceptance. M4 and M5 may progress independently after their
prerequisites, but their changes must use the frozen M1 contract. M8 follows M7.
Do not start a later milestone by silently dropping earlier acceptance criteria.

## M0 — Establish the receiver and toolchain baseline

Status: planned. Original plan: preparation for steps 1, 2, and 9.

- [ ] Record actual Pi model/RAM, service user, readsb service, decoder JSON path,
  receiver coordinates, export cadence, and SDR ownership when access is available.
- [ ] Capture privacy-safe receiver samples for contract/replay work; use synthetic
  samples meanwhile so missing Pi access does not block independent development.
- [ ] Verify physical ESP32 board, matrix wiring, and available memory.
- [ ] Select and pin tested PlatformIO platform/library versions before introducing
  BLE dependencies; record the Arduino core and provisioning API compatibility.
- [ ] Establish the existing importer/Docker baseline and physical/mock firmware
  build status without changing unrelated source behavior.

Done when: baseline facts, unknowns, and tool versions are recorded. Real Pi/board
details may remain an explicitly pending integration prerequisite while M1 proceeds.

## M1 — Freeze the canonical contract and shared fixtures

Status: partial: detailed draft 0.1 contracts, three versioned producer schemas,
shared synthetic examples and offline documentation checks are present. The
diagnostic route object is implemented; the canonical feed and parser are not
implemented or frozen. Main's initial local feed/parser is integrated into dev
but uses [a different prototype shape](local-flight-api.md). Receiver and ESP32
measurements remain pending.
Depends on repository inspection in M0.
Original plan: step 1.

- [x] Add the versioned schema and human-readable contract under `docs/api/`.
  See the [contract index](api/README.md), [receiver inventory](adsb-receiver-data.md)
  and [join rules](api/enrichment-joins.md); all new runtime boundaries are drafts.
- [x] Add synthetic receiver and expected flight envelopes under `tests/fixtures/`.
  [Shared M1 examples](../tests/fixtures/m1/README.md) contain 40 producer examples,
  receiver/context inputs and seven timing cases. Large input cases have generator
  descriptions; executable normalizer/consumer replay remains M2/M3.
- [ ] Fix field names/types, null semantics, units, clock/age semantics, receiver
  statuses, stable error reasons, string limits, and bounded output behavior.
- [x] Specify same-port relative asset metadata and the compatibility strategy for
  existing lookup, health, metadata, and live-adapter responses.
- [x] Define optional callsign-route references with source/revision, airport
  sequence, verification status, unknowns, and multi-stop ambiguity; keep local
  observed airport events and dated manual route evidence distinct.
  The [diagnostic route contract](api/routes.md) is implemented. The new feed's
  [compact projection](api/flights.md#64-compact-route-references-and-dated-evidence)
  is drafted separately; existing diagnostic response fields remain compatible.
- [x] Cover complete, partial, no-callsign, ground, unknown, healthy-empty, stale,
  unavailable, invalid-source, future/changed-clock, and oversized cases.
  These are design examples, not runtime replay results.
- [x] Validate fixture/schema consistency and define consumer rejection behavior.
  [Offline checks](api/validation.md) validate three schemas and all 40 examples,
  including 12 intentional failures and byte/relationship rules. Seven timing
  examples check arithmetic only. No application/firmware/hardware ran for M1 docs.
- [ ] Review and freeze the first wire contract using the synthetic evidence.
  Record unmeasured receiver cadence, clock tolerances and parser memory as
  explicit M0/M2/M3 validation gates; those measurements may require a documented
  revision, but they do not make M1 depend on completing its runtime consumers.

Done when: Pi, simulator, and firmware implementers can use the same examples
without inventing field meanings. Proposed budgets in architecture.md are either
confirmed by fixtures or explicitly revised with rationale.

## M2 — Implement the cached readsb flight API

Status: partial prototype: cached file/HTTP input and a flat `/v1/flights` exist.
Canonical M1 normalization, progress/clock rules, filters, byte bounds and replay
remain pending; unchecked items below require that full contract.
Depends on M1. Original plan: step 3 and startup parts of step 9.

- [ ] Add local-file input plus an explicitly configured loopback adapter if needed.
- [ ] Cache bounded snapshots, normalize telemetry, and preserve source ages.
- [ ] Detect initialization, healthy empty, missing/malformed/frozen input, clock
  jumps, invalid addresses, and independently stale positions.
- [ ] Implement geographic/bearing/altitude filters and deterministic capped output.
- [ ] Add `/v1/flights` and independent receiver/reference diagnostics without
  breaking the legacy lookup contract.
- [ ] Keep API startup functional without a registry or WAN; remove production
  startup's dependency on a successful reference download.
- [ ] Make Docker/replay exercise this same API using M1 fixtures.

Done when: replay/HTTP checks prove units, nulls, freshness, filtering, limits,
compatibility, and operation without reference data. Compare with real readsb
when access is available; keep that hardware evidence separate.

## M3 — Prove the minimal ESP32 local flight path

Status: partial prototype: a bounded initial Pi adapter, nullable basic telemetry,
local cards and connection/stale/empty messages exist. Cloud adapters are excluded
from the build. Canonical parsing, expiry, selection, firmware builds and physical
acceptance remain pending. Depends on M1, M2, and the M0 toolchain baseline.
Original plan: step 7 and the minimal portion of step 8.

- [ ] Introduce a Pi feed adapter and extend the flight model for nullable telemetry,
  ages, provenance, and local asset metadata.
- [ ] Make the local production build unable to call cloud flight/CDN adapters.
- [ ] Bound HTTP/parsing memory, isolate networking from render/expiry behavior,
  and implement retry/backoff and schema rejection.
- [ ] Preserve selection by hex and minimum dwell across reordered candidate lists.
- [ ] Display partial records, basic telemetry, and Wi-Fi/Pi/receiver/empty states.
- [ ] Build physical and mock environments and test shared parsing/error fixtures.

Done when: deterministic fixtures drive the firmware correctly and, when hardware
is available, one real local aircraft appears on the wall without cloud requests.
Temporary integration configuration must not commit real Wi-Fi credentials.
Full runtime provisioning and final visuals are still required by M5/M6.

## M4 — Complete offline aircraft, operator, and route enrichment

Status: partial: independent Pi route slice implemented; full M1/M2 and remaining
aircraft enrichment/integration work are pending. Original plan: steps 4 and 5.

- [ ] Join FAA MASTER to ACFTREF and distinguish owner, model, classification,
  registration, and ICAO designator; retain the existing MASTER-selection regressions.
- [ ] Implement field-level source precedence, explicit local overrides, and provenance.
- [ ] Import a versioned, licensed local airline table and dated corrections.
- [ ] Resolve recognized callsign prefixes conservatively; cover regional,
  alphanumeric, registration-like, ambiguous, and unknown identifiers.
- [x] Import CC0 VRS standing-data route files and companion airport/airline tables
  at a pinned revision; follow documented normalization and file partitions.
- [x] Resolve matching callsigns into reference airport sequences with provenance;
  distinguish these from a dated verified flight plan or observed landing.
- [ ] Measure route match rate and correct airport pairs on actual overhead traffic
  using a dated manual Google/airline-status comparison sample. Handle aliases,
  unknowns, reused numbers, stale records, and ambiguous multi-stop legs.
- [ ] Stream imports; validate and atomically activate complete generations while
  retaining rollback and keeping overrides outside downloaded data.
  Implemented for the route/airline/airport generation; FAA/assets still pending.
- [ ] Cover missing joins, non-US/unknown aircraft, conflicting sources, failed
  updates, concurrent readers, and legacy compatibility with regression checks.

Done when: useful telemetry survives incomplete coverage; owner cannot masquerade
as operating airline; model/classification/type stay distinct; failed maintenance
leaves the active dataset/API usable. Matching route records remain explicitly
reference data and can be resolved offline; local coverage/correctness is recorded
separately. See [route lookup research](route-detection.md). Worldwide data remains
optional until licensed.

## M5 — Add persistent runtime settings and BLE provisioning

Status: planned. Depends on M0 toolchain, M1 settings semantics, and M3 integration.
Original plan: step 2.

- [ ] Implement versioned NVS settings with validation, staged writes, migration,
  last-working Wi-Fi recovery, and a documented reset path.
- [ ] Provision Wi-Fi and custom Pi host/port through authenticated BLE in a
  physical, time-limited setup window; enforce bounds/fragmentation handling.
- [ ] Supply an open-source local reference client and usage instructions.
- [ ] Keep setup usable without Wi-Fi or Pi availability; never read back/log secrets.
- [ ] Test pure configuration logic and record real-board BLE/coexistence results.

Done when: changes survive reboot, invalid settings recover, and Pi port changes
work without reflashing. Wokwi cannot satisfy the real BLE acceptance gate.

## M6 — Add approved logos and finish display validation

Status: planned. Depends on M3/M4; run coexistence checks after M5.
Original plan: steps 6 and 8.

- [ ] Create individually approved asset manifests and maintenance-time conversion.
- [ ] Generate and serve immutable 24×24 RGB565 assets with explicit byte order,
  background policy, hash/size checks, and a bounded firmware cache.
- [ ] Render logo/badge fallback, labeled telemetry, and detail pages as required.
- [ ] Show available reference airport pairs on a detail page with their verification
  meaning; no locally observed landing is required for a callsign-route match.
- [ ] Validate supported Wokwi parts/pins and independent simulated pixel mapping;
  retain 64×32 and add a 160×32 layout option.
- [ ] Add coordinate diagnostics and check corners, rows, tiles, colors, unknown
  values, long strings, error screens, missing/corrupt assets, and memory/refresh limits.

Done when: deterministic previews and physical mapping agree; asset failures remain
readable; power/brightness limits and actual frame timing have hardware evidence.
Insufficient approved logo coverage uses badges instead of delaying core operation.

## M7 — Deploy and prove the first release

Status: planned. Depends on M2–M6 and verified Pi/board facts. Original plan: step 9.

- [ ] Adapt systemd paths/users/permissions, restart policy, bounded logs, and
  separate maintenance timers for the existing receiver installation.
- [ ] Document installation, configuration backup, generation rollback, and recovery.
- [ ] Measure real flight latency, then run with WAN disconnected and LAN active.
- [ ] Verify absence of external runtime traffic with maintenance disabled.
- [ ] Exercise restarts, Wi-Fi loss, Pi loss, frozen/malformed JSON, empty sky,
  partial fields, BLE host/port updates, and reboot persistence.
- [ ] Record a 24-hour Pi RAM/swap/CPU/decoder/API and ESP32 heap/latency baseline.

Done when: the release acceptance in architecture.md is evidenced on hardware.
Deployment/flashing requires an explicit implementation-task request and access;
preparing reviewable deployment files and independent checks can proceed beforehand.

## M8 — Optional observed airport events and route overrides

Status: deferred until M7. Original plan: step 10.

The primary overhead-flight airport lookup is now part of M4/M6. This milestone
adds local observed events for the minority of aircraft taking off/landing within
reception. See [route lookup research](route-detection.md) for the distinction.

- [ ] Import approved local airport reference data and bounded received track history.
- [ ] Detect observed ground-to-air departures and air-to-ground arrivals using
  fresh, continuous tracks near a suitable airport/runway.
- [ ] Persist bounded airport-event history so a later local arrival can be paired
  with an earlier observation without retaining full trajectories.
- [ ] Keep observed departure/arrival events separate from reference routes,
  dated manual overrides, and unknown. Missing local ground evidence does not
  suppress a valid callsign-route reference.
- [x] Add dated callsign-and-aircraft route overrides with expiry and provenance
  for the Pi lookup. Multi-stop current legs remain unknown; observed-event integration
  is pending. This independent route feature was implemented with the M4 slice.
- [ ] Cover flybys, ambiguous airports, missed takeoffs, reused callsigns, missing
  history, and expired overrides. Label uncertain display values.

Done when: reliable local airport events explain their evidence. Heading/proximity
alone cannot produce a local observed landing; a callsign-route database match
remains reference metadata rather than a dated confirmation of the current flight.
