# Development guide

Begin with [architecture.md](architecture.md), [AGENTS.md](AGENTS.md), and the
[implementation checklist](docs/implementation-plan.md). The current Docker flow
tests synthetic enrichment. An initial local telemetry API/parser exists, but
adoption of the [M1 contract](docs/api/README.md) remains pending; the current
prototype is documented in [the initial local API](docs/local-flight-api.md).
The [route lookup research](docs/route-detection.md) documents the CC0 source and
the implemented route slice of M4. See the [route contract](docs/api/routes.md)
and [Pi operating guide](pi_enrichment/README.md) for import/lookup/rollback
commands. Route regression checks use synthetic data and require no WAN.

## Prerequisites

- Python 3; the cloud machine and Docker images use Python 3.12. The Pi scripts
  currently use only the Python standard library, so there is no pip install step.
- Docker Engine/Desktop and a recent Compose version supporting `up --wait`.
- For firmware work, PlatformIO and the dependencies in
  [firmware/platformio.ini](firmware/platformio.ini). Versions are not fully pinned
  yet. See the [firmware guide](firmware/README.md) for Wokwi usage.
- Hardware/Pi access only for integration, provisioning, deployment, and physical
  acceptance. Fixture development needs no flight API credentials.

Run commands below from the repository root. Check `git status --short --branch`
first and preserve unrelated files. Keep secrets out of tracked configuration.

## Repeatable fixture stack

Use bundled synthetic aircraft instead of a live FAA download:

```bash
docker info
docker compose version
python3 --version
docker compose -f docker-compose.yml -f docker/compose.test.yml up --build -d --wait
python3 docker/smoke_test.py
```

In a cloud machine with a read-only home directory, set this before Compose:

```bash
export DOCKER_CONFIG=/tmp/flightwall-docker-config
mkdir -p "$DOCKER_CONFIG"
```

Expected smoke result at the reviewed baseline: **five tests pass**. The enrichment
API is on port 8080; the simulator preview is on 8090. The fixture contains three
synthetic aircraft, including `UAL123` / `TEST UNITED` / `A1B2C3:737-800`.
This proves existing enrichment JSON behavior, not the target local wall.

```bash
docker compose -f docker-compose.yml -f docker/compose.test.yml ps
docker compose -f docker-compose.yml -f docker/compose.test.yml logs --tail=50
curl --fail http://localhost:8080/health
curl --fail http://localhost:8090/v1/display/current
```

Stop while retaining test data:

```bash
docker compose -f docker-compose.yml -f docker/compose.test.yml down
```

The fixture uses `flightwall_test_data`; live mode uses `flightwall_data`. Both
modes share container names/ports, so do not start them concurrently. The base
Compose mode downloads FAA data before API startup; it does not yet meet the target
offline startup requirement. See [Docker operations](docker/README.md) and the
[Pi guide](pi_enrichment/README.md) for current live/native commands.

## M1 documentation/schema checks

The [contract index](docs/api/README.md) links draft field definitions and
[shared synthetic examples](tests/fixtures/m1/README.md). Run the optional offline
checker when changing their schemas/examples:

```bash
python3 -m venv /tmp/flightwall-contract-docs
/tmp/flightwall-contract-docs/bin/python -m pip install -r docs/api/requirements.txt
/tmp/flightwall-contract-docs/bin/python -B docs/api/check_contracts.py
```

If `jsonschema==4.26.0` is already installed, `python3 -B docs/api/check_contracts.py`
is sufficient. This is a documentation dependency, not a Pi runtime dependency.
The checker needs no WAN after installation, resolves local schemas and verifies
expected valid/invalid shapes, relationships, bytes and timing arithmetic.
See [validation scope](docs/api/validation.md): it does not execute receiver,
HTTP, simulator or firmware behavior. Application tests are unnecessary for a
documentation-only task.

## Pi regression checks

```bash
python3 -B -m unittest discover -s pi_enrichment -p 'test_*.py' -v
```

Current result: **25 tests pass**: three FAA tests, six initial flight-feed tests
and sixteen route checks. Feed checks cover partial telemetry, units, frozen and
malformed snapshots, invalid values, caching and the candidate cap. Route checks
cover normalization, ambiguity, partitions, long sequences, missing
joins/files, failed updates, pinned readers, rollback, overrides/expiry, geography,
read-only cache limits, gzip truncation/CRC failures, HTTP worker limits, and the
combined flight/route HTTP API with application WAN calls forbidden.
Real receiver freshness, route correctness for today's traffic, and Pi hardware
resource use remain separate acceptance work.

## Firmware build and visual checks

With PlatformIO installed, build from `firmware/`:

```bash
cd firmware
pio run -e esp32dev
pio run -e wokwi
```

Builds produce outputs under ignored `.pio/`. The `wokwi` environment is currently
a display mock; it bypasses the live fetch path and does not validate BLE. Use the
serial commands and simulator instructions in the firmware guide. Inspect/pin
the toolchain and verify the diagram's matrix part before claiming simulator
compatibility. Do not upload firmware as part of a build-only task.

## Change and context workflow

Implement one reviewable milestone slice at a time. Keep the shared contract,
source semantics, and legacy compatibility consistent across components. Use
focused replay/parser/HTTP tests for behavior changes and existing regressions
where affected. Documentation-only changes need link and consistency checks;
they do not require launching services or running application tests.

Before handoff, inspect `git diff --check` and the final Git status. Update
[project context](docs/project-context.md) with actual results and next steps,
the milestone checklist with evidence-backed status, and
[decisions](docs/decisions.md) when design choices change. Record unavailable
hardware checks explicitly rather than treating fixture/build success as release
acceptance. Apply deployment or flash commands only for an explicitly requested
task with the necessary access.
