# FlightWall Pi Enrichment Service

Local Raspberry Pi service that:
- Downloads FAA registry data and imports it into SQLite.
- Serves a local HTTP API for ADS-B ICAO (`hex`) enrichment.
- Optionally enriches `readsb/tar1090` live `aircraft.json` output.
- Resolves received callsigns into offline reference airport sequences using CC0
  VRS standing data, with separately stored dated manual overrides.

## Offline departure/destination lookup

Route maintenance is an explicit command, separate from API startup. From the
repository root, import a pinned VRS revision for the airlines of interest:

```bash
python3 pi_enrichment/route_pipeline.py --data-dir /tmp/flightwall-routes import \
  --revision d856ef1ed0fc492e8a3933ff4a938448ed008f66 --airlines BAW UAL
python3 pi_enrichment/route_pipeline.py --data-dir /tmp/flightwall-routes lookup ' BAW117 '
python3 pi_enrichment/server.py --route-data-dir /tmp/flightwall-routes --host 127.0.0.1
```

The revision above is the researched example, not an assertion that it is the
latest. Select a new full 40-character revision for later maintenance. Airline
selection uses canonical VRS codes; IATA aliases apply to lookup, not import
selection. The importer discovers both `-all.csv` and digit partitions. All
companion airports/airlines are stored in SQLite so aliases can be checked for
ambiguity and ordered airport codes can be resolved without runtime downloads.

The default state root is `~/.flightwall-pi/routes`, configurable with
`--data-dir` for maintenance and `--route-data-dir` for the API. Both honor
`ROUTE_DATA_DIR`; the Docker image defaults to `/data/routes` on its persistent
volume. The `/tmp` examples are for development, not persistent Pi deployment.

```bash
curl --fail http://127.0.0.1:8080/v1/routes/BAW117
python3 pi_enrichment/route_pipeline.py --data-dir /tmp/flightwall-routes status
python3 pi_enrichment/route_pipeline.py --data-dir /tmp/flightwall-routes rollback
```

Lookup/status/rollback use local files only. Rollback requires a successful
second import and validates the previous generation before switching. Failed
maintenance leaves the active pointer unchanged. Requests pin an immutable DB;
old generations are retained so open readers and rollback remain safe. Automatic
cleanup is intentionally absent: to reclaim storage, stop the API and maintenance,
retain the `active` and `previous` IDs in `active.json`, and remove only older
generation directories. Overrides live outside the generations.

For a predownloaded checkout or GitHub tar.gz, add `--source-dir /path/to/standing-data`
or `--archive /path/to/standing-data.tar.gz` to `import`. The caller must ensure
these inputs are from the supplied revision; the manifest records that the
revision is caller asserted. HTTPS imports record the pinned download URL.
Neither path runs arbitrary repository code. To prepare all routes, explicitly
replace `--airlines BAW UAL` with `--all-routes`; measure storage/coverage before
using that scope on the Pi.

Imports stream 64 KiB chunks and one CSV record at a time into a 1 MiB SQLite
cache. They cap compressed archives at 512 MiB, expanded archives at 2 GiB,
individual source files at 16 MiB, physical CSV lines at 16,384 characters, and
CSV records at 65,536 characters. SQLite uses disk temporary storage, no mmap,
and DELETE journaling; committed generations do not depend on WAL files. Gzip
CRC/trailer, headers, duplicate keys, joins, license/credits, integrity, counts,
and artifact checksums are validated before activation. License inspection is
bounded at 64 KiB. The small JSON manifest points to per-artifact checksums in
SQLite instead of loading an artifact list into memory.

Each generation contains `routes.sqlite3`, `manifest.json`, and retained notices.
Only `active.json` is atomically replaced. Maintenance takes an exclusive local
lock and does not block runtime reads. Budget storage for the staging, active,
and previous generations during an update; no worldwide CSV dictionary or archive
index is kept in RAM. API lookups use indexed read-only connections with a 1 MiB
cache each, and the HTTP server caps concurrency at eight request workers.

### Dated manual corrections

Record a Google/airline finding with the actual flight date, source, evidence and
short validity window. This example is illustrative; use independently checked
values rather than treating its airports as verified for that date:

```bash
python3 pi_enrichment/route_pipeline.py --data-dir /tmp/flightwall-routes override BAW117 \
  --airports EGLL-KJFK --flight-date 2026-10-03 \
  --valid-from 2026-10-03T10:00:00Z --valid-until 2026-10-03T23:00:00Z \
  --source manual_airline --evidence 'Dated airline flight-status result'
```

Corrections are separate from the downloaded DB, expire, and take precedence
when their callsign/date/window match. `--aircraft-hex` scopes evidence to one
aircraft. Add `--verified` only after checking that particular flight; it requires
the hex and dated evidence. Callsign/date-only overrides stay unverified. Windows
must be at most 24 hours; the flight date is the UTC start date. Expired records
are removed on subsequent override maintenance. Overnight evidence may require
an explicit `flight_date` lookup parameter after midnight UTC.

See the [route contract](../docs/api/routes.md) for normalization, query parameters,
unknowns, geography checks, two-airport direction, long sequences, and verification
semantics. VRS airport order gives a reference departure/destination pair; it
does not confirm today's itinerary or actual landing. Aircraft without a route
remain in the live response. Firmware display adoption follows M1/M2/M3/M6.

## Test locally with Docker

Run the enrichment API and FlightWall simulator on your local machine using
three synthetic aircraft records. This mode requires no API keys, Raspberry Pi,
receiver, or FAA registry download. Docker downloads the base image on the first
build, so internet access is needed initially.

### Prerequisites

- Install and start Docker Desktop on macOS or Windows, or Docker Engine with
  the Compose plugin on Linux.
- Use a recent `docker compose` version that supports `up --wait`.
- Install Python 3 on your machine to run the smoke tests below.
- Make sure local ports `8080` and `8090` are available.

Check your installation:

```bash
docker info
docker compose version
python3 --version
```

### Start the test stack

Open a terminal at the repository root, the directory containing
`docker-compose.yml`. If your terminal is in `pi_enrichment/` or `firmware/`, run
`cd ..` first. Run all commands in this section from the repository root.

```bash
docker compose -f docker-compose.yml -f docker/compose.test.yml up --build -d --wait
```

This builds both services, imports
[`docker/fixtures/aircraft_registry.csv`](../docker/fixtures/aircraft_registry.csv),
and waits until both services are healthy. Test data is stored in a separate
`flightwall_test_data` Docker volume; live FAA data uses `flightwall_data`.
The test and live modes share container names and ports, so run one mode at a time.

### Verify the results

Run the five end-to-end smoke tests:

```bash
python3 docker/smoke_test.py
```

Expected result: `Ran 5 tests` followed by `OK`. These tests check registry
readiness, known and unknown aircraft, enrichment of all three sample flights,
and the simulator's display card. They expect the bundled fixture and
[`flightwall_sim/sample_aircraft.json`](../flightwall_sim/sample_aircraft.json).

You can also open these URLs in a browser or check them with `curl`:

| URL | Expected result in test mode |
| --- | --- |
| <http://localhost:8080/health> | `status: "ok"`, `db_exists: true`, `stale: false` |
| <http://localhost:8080/v1/meta> | `row_count: 3` |
| <http://localhost:8080/v1/aircraft/A1B2C3> | `found: true`, operator `TEST UNITED`, model `737-800` |
| <http://localhost:8080/v1/aircraft/FFFFFF> | `found: false` |
| <http://localhost:8090/v1/flights> | Three enriched flights with `found: true` |
| <http://localhost:8090/v1/display/current> | `UAL123` / `TEST UNITED` / `A1B2C3:737-800` |

```bash
curl --fail http://localhost:8080/v1/aircraft/A1B2C3
curl --fail http://localhost:8090/v1/display/current
```

The simulator exposes JSON display output. For ESP32 builds and LED display
simulation, see the [firmware guide](../firmware/README.md). `/v1/aircraft/live` requires
a configured `readsb/tar1090` receiver and is not used by this Docker test mode.

### Logs, stop, and restart

Inspect status and recent logs:

```bash
docker compose -f docker-compose.yml -f docker/compose.test.yml ps
docker compose -f docker-compose.yml -f docker/compose.test.yml logs --tail=50
```

Stop the stack while keeping test data:

```bash
docker compose -f docker-compose.yml -f docker/compose.test.yml down
```

Restart with the same `up --build -d --wait` command above. To delete the test
volume as well, use `down -v` with the same two Compose files; the next start
imports the fixture again.

If startup fails, confirm Docker is running, check the logs, and make sure
another application is not using ports `8080` or `8090`. If you change the sample
flights or fixture, rebuild/restart the stack; the bundled smoke tests still
expect the original sample records.

### Optional: test with live FAA registry data

Stop the fixture stack first, then start the base configuration:

```bash
docker compose -f docker-compose.yml -f docker/compose.test.yml down
docker compose -f docker-compose.yml up --build -d
docker compose -f docker-compose.yml logs -f pi-enrichment
```

This downloads and imports the FAA registry before starting the enrichment API,
which can take several minutes. If the download returns HTTP 403 or another
network error, use the fixture mode above for local tests. The fixture smoke
tests are intended for test mode; live FAA records may not match the sample
ICAO values or synthetic operator/model names.

Stop live mode with `docker compose -f docker-compose.yml down`.
See the [Docker guide](../docker/README.md) for more operations.

## JSON contract

### `GET /v1/aircraft/{adsb_icao}`
Always returns `200`.

```json
{
  "adsb_icao": "A1B2C3",
  "registration": "N123AB",
  "operator_name": "EXAMPLE AIR",
  "operator_icao": "EXM",
  "aircraft_model": "737-800",
  "aircraft_type": "L",
  "source": "faa_registry",
  "updated_at": "2026-08-03T00:00:00Z",
  "found": true
}
```

Unknown ICAO example:

```json
{
  "adsb_icao": "FFFFFF",
  "registration": "",
  "operator_name": "",
  "operator_icao": "",
  "aircraft_model": "",
  "aircraft_type": "",
  "source": "faa_registry",
  "updated_at": "",
  "found": false
}
```

### Other endpoints
- `GET /health`: service health + stale flag.
- `GET /v1/meta`: schema/version/checksum/row count sync metadata.
- `GET /v1/aircraft/live`: reads `tar1090/data/aircraft.json` and enriches each aircraft by `hex`.
- `GET /v1/routes/{callsign}`: local route reference/override lookup; see the
  [route contract](../docs/api/routes.md). The live adapter includes this object
  as `route_resolution`; health/meta include independent route diagnostics.

## FAA sync pipeline

The following manual Python and systemd commands assume the repository root.

Script: `faa_pipeline.py`

Default source URL:
- `https://registry.faa.gov/database/ReleasableAircraft.zip`

Default output:
- DB: `~/.flightwall-pi/faa_registry.sqlite3`
- CSV snapshot: `~/.flightwall-pi/faa_registry.csv`
- Metadata: `~/.flightwall-pi/faa_registry_meta.json`

Run manually:

```bash
python3 pi_enrichment/faa_pipeline.py
```

## Run API server

```bash
python3 pi_enrichment/server.py --host 0.0.0.0 --port 8080
```

## systemd setup (recommended)

Templates are in `pi_enrichment/systemd/`:
- `flightwall-enrichment.service`
- `flightwall-faa-sync.service`
- `flightwall-faa-sync.timer`

Suggested install:

```bash
sudo cp pi_enrichment/systemd/*.service /etc/systemd/system/
sudo cp pi_enrichment/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flightwall-enrichment.service
sudo systemctl enable --now flightwall-faa-sync.timer
```

## Stale-data behavior

`/health` returns `stale: true` when `last_sync_at` is older than `STALE_AFTER_HOURS` (default `72`).

## Notes

- FAA feed column names can vary; the importer maps multiple likely header names.
- If operator ICAO is not present in FAA source, `operator_icao` will be empty.
- API is local-network oriented and intentionally simple for Pi 4 devices.
