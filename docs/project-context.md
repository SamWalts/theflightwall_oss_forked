# Project context and handoff

Last updated: 2026-10-04. Original architecture-review baseline:
`500a49c67a73bb4d9ea3da131115bdaf4db84dec`. Dev now includes main's initial
local-feed commit `8418bdc974a15c813f567ef136ac1126e12e35e8` alongside its route
implementation and M1 draft. Consult Git history for the resulting merge commit.
Recheck the checkout and runtime before relying on this snapshot.

## Goal

Migrate the existing FlightWall from cloud flight lookups to received aircraft
from the owner's existing readsb installation. The Pi supplies telemetry and
offline reference/assets over LAN. The ESP32 displays useful partial records and
supports persistent Wi-Fi/Pi endpoint changes over BLE. First release acceptance
includes a physical WAN-disconnected run and documented recovery.

Airport-pair lookup must serve overhead traffic: the user estimates about 95% of
these aircraft will not land locally and already looks up flights by number in
Google. The recommended free automated path is a CC0 callsign-route reference
import on the Pi; local landing observations are a separate optional feature.

## Read next

| Document | Purpose |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Entry point and working conventions for AI agents. |
| [architecture.md](../architecture.md) | Maintained target design, current-code review, boundaries, and budgets. |
| [Implementation checklist](implementation-plan.md) | Milestones, dependencies, acceptance criteria, and status. |
| [Decisions](decisions.md) | Design rationale, provisional choices, and unresolved facts. |
| [Pi-to-ESP32 contracts](api/README.md) | M1 draft feed/asset/health/meta/legacy contracts, schemas and status map. |
| [Screen contract review](screen-contract-review.md) | Reviewed design snapshot, M1 mismatches, merge blockers, and PlatformIO setup status. |
| [Receiver inventory](adsb-receiver-data.md) | What aircraft radio messages, readsb calculations/bookkeeping and external annotations can provide. |
| [Enrichment joins](api/enrichment-joins.md) | Hex-to-aircraft, callsign-to-airline/ordered-route and operator-to-approved-logo keys and failure rules. |
| [Route lookup research](route-detection.md) | Verified free callsign-route data for overflights, Google/manual verification, API alternatives, and current-flight limits. |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Reproducible development commands and evidence requirements. |
| [Original plan](flightwall-local-plan.md) | October 1 source plan, reference links, and detailed task prompts. |

The README retains legacy cloud/hardware instructions and links the initial local
setup. The complete target architecture is still pending. Maintain the architecture and
milestones when implementation changes; do not erase the source plan's history.

## Current code

- Pi API: aircraft lookup, registry metadata/health, and a loopback readsb/tar1090
  enrichment endpoint exist. Local `/v1/routes/{callsign}` and legacy live
  `route_resolution` are implemented, with independent reference diagnostics.
  Initial `/v1/flights` now uses a one-second-cached local file/HTTP snapshot and
  emits partial flat telemetry. It has no route/logo join, geographic ordering,
  producer byte bound or canonical progress/clock state machine. See
  [prototype contract](local-flight-api.md); its `schema_version=1` remains distinct
  from the nested M1 draft at `/v2/flights`, schema version 2 (D013).
- Route maintenance: `route_pipeline.py` streams selected or explicitly worldwide
  VRS tables into immutable SQLite generations, retains notices/checksums, and
  atomically activates/rolls back. `route_reference.py` handles exact/alias
  lookup, airport order, long sequence ambiguity, geographic rejection, and
  separately stored dated overrides. Neither runtime lookup nor startup downloads
  route data. See [route contract](api/routes.md) and [Pi commands](../pi_enrichment/README.md).
- FAA importer: MASTER-selection regression fix is present; ACFTREF joining,
  correct owner/operator separation, and generation activation remain planned.
- Simulator: synthetic lookup consumer exposes its own `/v1/flights` on 8090;
  it does not exercise the full planned receiver/telemetry contract.
- Standalone OpenSky CSV logger: `opensky_flight_counter.py` and its existing
  checks are preserved from `dev`; usage remains in the root README.
- Firmware: the live path polls the initial Pi feed and displays nullable altitude,
  GS and vertical rate plus connection/stale/empty messages. Cloud adapters remain
  legacy source excluded from the build. Configuration is compiled in; canonical
  parsing, monotonic expiry, selection by hex, BLE/NVS and local bitmaps are pending.
- Toolchain: `espressif32` is unpinned; libraries use version ranges. Existing
  physical `esp32dev` and display-only `wokwi` environments are configured.
  The active 64×32 Wokwi diagram matches the mock environment. The previous
  `dev` 160×32 diagram is retained as `firmware/diagram-160x32-reference.json`;
  its GPIO 13 wiring differs from the current mock's GPIO 5. The existing local
  port-forward configuration is retained with the mock's firmware/ELF paths.
- Receiver/physical hardware: details reported by the source plan have not been
  directly verified in this workspace. No deployment or flashing was performed.

## Evidence so far

| Evidence | Scope and limitation |
| --- | --- |
| Earlier cloud onboarding: three importer unit tests passed. | MASTER selection and supported CSV/archive inputs; not ACFTREF correctness. |
| Earlier cloud onboarding: fixture stack built, both containers healthy, five HTTP smoke checks passed. | Synthetic registry lookup/enrichment/display JSON; not real receiver, ESP32, BLE, or offline hardware acceptance. |
| Route-source research: readsb's published JSON reference and OurAirports' maintained GitHub data/README/license were reachable. | Confirms useful local aircraft/airport inputs and a public-domain airport-data source; it does not prove local ground reception or detection accuracy. The OurAirports website download page returned HTTP 403 in this research environment. |
| Overflight-route follow-up: inspected VRS schema/license/credits and actual route/airline/airport CSVs at revision `d856ef1ed0fc492e8a3933ff4a938448ed008f66`; `BAW117` maps to `EGLL-KJFK`. | Verifies a CC0 callsign-to-airport-pair source usable without local landing. Match rate and dated correctness on the user's traffic are unmeasured; route schema has no flight date/per-row verification time. |
| API alternative review: ADSBDB documents a callsign endpoint with origin/destination; ADSB.lol source implements VRS route queries. | Hosted services were blocked by the environment proxy, so live response/availability is unverified. ADSBDB publishes separate route-copy restrictions; do not assume its MIT software license permits local route-data caching. |
| Architecture review: inspected Pi server/importer/startup, simulator, firmware models/fetch/display, toolchain, and systemd templates. | Source review against the baseline above; the route slice was subsequently implemented as recorded below. |
| Documentation task: created the maintained architecture, milestone, decision, agent, and contributor docs. | Documentation consistency/link checks only; application tests were not rerun for these docs. |
| Route implementation: streamed HTTPS import at the researched revision, including both the BAW/UAL subset and all source partitions. | BAW/UAL: 11,382 routes, 5,965 airlines, 34,128 airports, approximately 3.4 MiB DB and 22.4 MiB peak RSS. Worldwide: 620,396 routes, 44.9 MiB DB, 22.1 MiB peak RSS in 7.46 s. These Linux cloud process measurements do not cover decoder/OS-cache/Pi hardware. |
| Route behavior: 19 unit/HTTP checks passed (three existing FAA checks and sixteen route checks), including unknowns, aliases, airport joins/order, partitions, long sequences, source failures, gzip CRC/truncation, overrides/expiry, updates/rollback, bounded caches/workers and offline lookup. | Application WAN calls are forbidden during HTTP lookup checks; local HTTP remains available. No real receiver traffic, dated correctness sample, firmware display, or hardware deployment was available. |
| Indexed runtime measurement: 1,000 independently opened `BAW117` lookups against the worldwide DB averaged 0.378 ms, with 10.5 MiB peak process RSS. | Single-thread cloud microbenchmark with warm filesystem cache, not LAN end-to-end latency or Pi/ESP32 memory evidence. |
| Packaging and static checks: enrichment Docker image built with the new modules; a read-only-mounted BAW117 lookup returned EGLL→KJFK in a container with `--network none`; documentation links/fences, Python syntax and `git diff --check` passed. | Existing container services were not restarted and the earlier five-test Docker smoke result remains prior evidence. |
| M1 documentation: detailed draft 0.1 receiver/feed/logo/health/meta/legacy contracts, join rules, three producer schemas and shared examples created. | No `/v1/flights` implementation, local-file reader, ESP32 parser, approved bitmap or hardware integration was added. Existing diagnostic route response is unchanged. |
| Receiver inventory: inspected readsb's JSON reference at revision `094720939c01943de82b14df6f42f67fff1cd514`. | Distinguishes transmitted data from decoder calculations and references; this is upstream source research, not identification of the installed Pi version. |
| M1 static validation: three schemas valid; 40 examples match expected outcomes (28 valid, 12 intentionally invalid); seven timing examples consistent. | Offline documentation checker validates producer shape, source/route/logo relationships, control-character rejection and compact body bytes. It does not run normalizer, HTTP, firmware or application tests. |
| M1 byte and documentation checks: maximal eight-row Unicode output is 32,627 bytes; complete three-row prefix is 13,279 bytes; largest accepted example is 15,300 bytes. 130 local links/anchors, JSON code examples, balanced fences, new-file whitespace and `git diff --check` passed. | Serialized example measurements explain byte truncation; they do not prove ESP32 parser allocation or real receiver/hardware behavior. |
| Main-to-dev integration: all 25 Pi tests passed (three FAA, six prototype-feed, sixteen route), including the combined flight/route/health HTTP check with application WAN calls forbidden. M1 documentation checker again passed three schemas, 40 examples and seven timing cases. | Synthetic prototype behavior and legacy compatibility; the prototype is not M1-conformant. No firmware build or hardware acceptance was performed. |
| Packaging integration: added the new feed module to the Dockerfile; started the API from exactly its copied Python modules and checked five HTTP endpoints with a local receiver file and missing FAA/route data. | Native temporary-directory startup check, not a Docker rebuild. Default Docker FAA sync still blocks offline startup until separately changed. |
| Merge static review: 169 local Markdown links/anchors, four JSON examples, balanced fences, changed Python syntax, both wiring JSON files, Wokwi TOML and Git whitespace checks passed. | Source/documentation checks only; firmware compilation and physical display mapping remain unverified. |

Docker CLI/Buildx state needed `DOCKER_CONFIG=/tmp/flightwall-docker-config` during
onboarding because the cloud home directory was read-only. Python 3.12 and Docker
Compose are available in this workspace. PlatformIO Core 6.2.0 is now installed
as recorded in the screen review below; firmware compilation remains blocked.
Live processes and temporary state must not be assumed to survive restoration.

## Next useful task

Review/freeze M1 flight draft 0.2 and continue M0's actual receiver/toolchain baseline.
Receiver access is needed to confirm path/coordinates/export cadence and draft
4 MiB/512-row input limits. The wire version collision is resolved by D013; implement v2 explicitly, then extend the cached reader with M2's clock/progress state machine,
filters and byte-bounded feed using the shared schemas/examples. Migrate the M3
Pi consumer to those envelopes and measure its complete memory footprint. The
implemented full diagnostic route object needs the documented compact projection,
not repeated copies inside every candidate. Render available pairs in M6.
Google/airline-status results can check a dated sample; API/dataset
matches must not silently claim live itinerary verification. M8 retains optional
observed airport events. Read the M1 checklist before coding; keep
existing lookup responses compatible and do not extend the simulator's separate
schema as a substitute for the production contract.

M1 is a detailed checked draft, awaiting final freeze/runtime evidence. M2/M3 have
initial prototypes, M4 has its independent route slice, and all remain partial.
Other migration milestones remain planned, with observed-event work deferred in M8. Pi access,
actual board/wiring, pinned provisioning support, and approved data/asset artifacts
remain integration prerequisites, not reasons to request flight API secrets.

Reference files prepared during validation live only under `/tmp/flightwall-vrs-validation`
and `/tmp/flightwall-vrs-world-validation`; they are not tracked, deployed, or
guaranteed to survive workspace restoration. API clients should import into their
own persistent configured state directory. The accumulated work was committed on
`feature/m1-contract-and-offline-routes` and merged into `dev`; main's initial
local feed was subsequently integrated. Consult Git history for current
publication/merge status. No hardware deployment or firmware
flashing was performed.

M1 draft artifacts live in the repository, including receiver inputs, envelope
examples and the optional offline checker in `docs/api/`. Logo hashes are mock
metadata with no corresponding approved images. Large-input descriptions are
not executable replay generators. Earlier Docker results remain prior evidence;
the new Pi tests and native packaging check above cover this source merge.
PlatformIO Core 6.2.0 is installed in `/workspace/.venvs/flightwall-platformio`.
Project configuration checks passed, but ESP32 platform installation received
HTTP 403 from the environment proxy before compilation. The saved environment
draft needs publication and registry access verification before builds can resume.

## Screen/dev integration review, 2026-10-04

Reviewed dev `61178bb` and design/flightwall-screens `c1b274e`. Combined them on
`review/flightwall-conflicts`; resolved the README conflict by retaining current
local-feed status and adding the gallery links. The design branch is based on
`500a49c`; its absence of newer dev files is branch divergence, not an instruction
to remove route implementation, contracts, or the working Pi firmware path.

Resolved the flight wire-version collision: canonical flight draft 0.2 is now
`/v2/flights`, `schema_version=2`, with a renamed producer schema and updated shared
envelopes. Working v1 runtime/firmware and v1 route/logo contracts remain compatible.
D013 records migration and screen semantics. The screen projection uses canonical
fields, reference/dated/verified route labels, ambiguous-leg protection, city-code
fallbacks and distinct VS/GVS rate labels, canonical identifiers, neutral unknown-operator
badges and receiver/viewing state mapping. Regenerated the gallery, PNG/SVGs and PDF.

New evidence: all 25 Pi regression tests and ten shared-fixture screen projection
tests pass. Contract checker passes three schemas, 40 expected example outcomes
and seven timing cases. All 39 screen sets pass native/serialized pixel and logo
checksum checks; Chromium verifies gallery controls, downloads, navigation and
390/768/1440px layouts without external requests or browser errors. No hardware,
firmware build, deployment, or canonical runtime acceptance is claimed.

The review report was published on dev as [screen-contract-review.md](screen-contract-review.md)
in commit `2ce1328`. All seven findings are reconciled; the report now records each
correction and its verification. The integration includes that review commit and
resolves the project-context conflict by preserving its PlatformIO setup evidence.
Destination-only/inferred-departure concepts are explicitly deferred in the gallery
and exports. Next: implement M2/M3 v2 and continue receiver/hardware acceptance.


## Handoff maintenance

After each substantive task, replace stale status rather than appending a chat log.
Record the commit/files affected, completed milestone criteria, checks actually
run and their limits, unresolved blockers, and the next concrete action. Keep
stable design rationale in the decision log and executable commands in the
contributor guide. Never include credentials or private receiver captures here.
