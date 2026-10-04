# Agent guide

## Start each task

1. Read [project context](docs/project-context.md) for implementation status,
   recent evidence, and the next useful task.
2. Read [architecture.md](architecture.md) and the relevant item in the
   [implementation checklist](docs/implementation-plan.md).
3. Consult [decisions](docs/decisions.md) before changing a component boundary,
   data source, protocol, or release requirement.
   For M1/M2/M3/M6, read the [contract index](docs/api/README.md), relevant schema,
   [shared examples](tests/fixtures/m1/README.md) and [join rules](docs/api/enrichment-joins.md).
   Draft 0.1 is checked documentation. The implemented prototype feed/parser
   follows [the initial local API](docs/local-flight-api.md), not this draft.
4. Run `git status --short --branch` and preserve unrelated user changes.
5. Use [CONTRIBUTING.md](CONTRIBUTING.md) for setup and validation commands.

Cloud tasks already have an isolated checkout; use the existing repository rather
than creating a worktree unless the user requests one.

## Project rules

- Current firmware uses the initial local Pi feed; cloud adapters remain legacy
  source excluded from the build. The prototype is incompatible with the M1
  draft, now reserved at `/v2/flights` with `schema_version=2`. Keep the v1
  prototype compatible. Canonical migration remains M2/M3.
- Keep flight operation independent of WAN, cloud APIs, and reference downloads.
  New local production code must not silently fall back to external adapters.
- Reuse the existing readsb/SDR installation. Discover real paths and coordinates;
  sample configuration is not deployment evidence.
- Keep the existing lookup API compatible during migration. The simulator must
  adopt the canonical production flight contract rather than inventing another.
- Preserve partial telemetry. Unknown operator/model/logo/airspeed/route/callsign
  must not suppress an otherwise eligible aircraft. Position freshness still
  governs geographic eligibility.
- Use the [receiver inventory](docs/adsb-receiver-data.md) when mapping fields;
  do not describe calculated/bookkeeping/reference values as radio broadcasts.
- Preserve complete retained candidates under both the count and byte budgets.
  Apply the documented compact route/source projection and measure actual encoded
  body bytes; eight rows are not guaranteed to fit the 16 KiB limit.
- Keep registered owner separate from operator, FAA classification separate from
  ICAO type, and GS separate from IAS/TAS. Preserve units, ground state, and nulls.
- Resolve overhead-flight airport pairs using licensed callsign-route references,
  beginning with CC0 VRS standing data. A reference match does not require a locally
  observed landing. Preserve source/revision and distinguish reference routes,
  dated verification, observed airport events, and unknown. See D011 and
  [route lookup research](docs/route-detection.md).
- Track original receiver freshness and monotonic expiry. A new HTTP response must
  not revive stale aircraft.
- Maintenance activates validated generations and retains the last good data.
  API startup must not wait for a download/import.
- Stream all dataset preparation with bounded records/chunks and disk-backed
  SQLite. The implemented route path uses 1 MiB caches, disabled mmap, immutable
  generations, and separate overrides. Preserve those limits; do not load full
  CSV tables, archives, or artifact lists into Python containers.
- Never place credentials in source, fixtures, documentation, logs, or handoffs.
  Inspect configuration names/presence rather than dumping values.
- Keep dataset and asset provenance, checksums, licenses, and attribution with
  imported artifacts. Unknown artwork uses a text fallback.
- Deployment and flashing need an explicit task request and available access.
  Wokwi/Docker results do not prove real BLE, receiver, or LED behavior.

## Repository map

| Path | Role |
| --- | --- |
| `pi_enrichment/` | Python HTTP API, SQLite lookups, FAA importer, streamed VRS importer/resolver, systemd templates. |
| `flightwall_sim/` | Current synthetic lookup consumer and JSON display preview. |
| `firmware/` | ESP32 Arduino/PlatformIO code, adapters, models, display, Wokwi wiring. |
| `docker/` | Fixture registry, repeatable Compose override, HTTP smoke checks. |
| `docs/flightwall-local-plan.md` | Original detailed plan and implementation prompts; retained as source history. |

## Finish each task

Use meaningful checks for the changed behavior. For documentation-only changes,
check links, commands against source, and consistency; application tests are not
needed. Record exactly what ran and distinguish previous evidence from new results.

Update milestone status only when its acceptance criteria have evidence. Update
project context with completed work, current blockers, and the next concrete step.
Record changed architectural decisions in the decision log, and keep commands in
the contributor guide aligned with the implementation. Preserve the original plan;
use the new documents as the maintained working set. Avoid duplicating the API
contract or copying temporary chat transcripts into durable context.
