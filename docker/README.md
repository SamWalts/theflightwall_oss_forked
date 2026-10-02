# Docker setup for local FlightWall testing (macOS)

This setup lets you run both services on one machine without physical devices:

- `pi-enrichment`: FAA importer + local enrichment API (`:8080`)
- `flightwall-sim`: software simulator for the FlightWall hardware behavior (`:8090`)

## 1) Install Docker on macOS

1. Install **Docker Desktop for Mac**: https://www.docker.com/products/docker-desktop/
2. Open Docker Desktop and finish onboarding.
3. In Docker Desktop Settings:
   - **Resources**: keep at least 4 GB RAM.
   - **General**: keep "Use Docker Compose V2" enabled.
4. Verify from Terminal:

```bash
docker --version
docker compose version
```

## 2) Start repeatable Docker tests (no FAA download)

From the repository root (run `cd ..` first if your terminal is in `firmware/`):

```bash
docker compose -f docker-compose.yml -f docker/compose.test.yml up --build -d --wait
```

This mode imports three **synthetic** aircraft from
`docker/fixtures/aircraft_registry.csv`, matching the simulator's sample inputs.
It uses a separate `flightwall_test_data` volume and waits for both APIs to be
ready. No API keys, receiver, or FAA download are required. The override replaces
the normal stack's containers, so run one mode at a time.

Run the end-to-end smoke tests (requires Python 3 on the host):

```bash
python3 docker/smoke_test.py
```

These check registry readiness, known and unknown aircraft, simulator enrichment,
and the rendered display card. They expect the bundled fixture and sample inputs.

Check the results manually:

```bash
curl --fail http://localhost:8080/health
curl --fail http://localhost:8080/v1/meta
curl --fail http://localhost:8080/v1/aircraft/A1B2C3
curl --fail http://localhost:8090/v1/flights
curl --fail http://localhost:8090/v1/display/current
```

Expect `row_count: 3`, all three flights with `found: true`, and a display card
for `UAL123` / `TEST UNITED` / `A1B2C3:737-800`.

Stop the test stack (keeping its data):

```bash
docker compose -f docker-compose.yml -f docker/compose.test.yml down
```

Run importer regression tests locally from the repository root:

```bash
python3 -B -m unittest discover -s pi_enrichment -p 'test_*.py' -v
```

## 3) Start both services with live FAA data

From repository root:

```bash
docker compose up --build
```

If your terminal is in `firmware/`, run `cd ..` first.

What happens:
- `pi-enrichment` downloads FAA data (first start can take several minutes), imports SQLite data, then serves the API.
- `flightwall-sim` polls `pi-enrichment` and exposes test endpoints.

To run detached:

```bash
docker compose up --build -d
```

## 4) Verify the live services

### Pi enrichment

```bash
curl http://localhost:8080/health
curl http://localhost:8080/v1/meta
curl http://localhost:8080/v1/aircraft/A1B2C3
```

### FlightWall simulator

```bash
curl http://localhost:8090/health
curl http://localhost:8090/v1/flights
curl http://localhost:8090/v1/display/current
```

## 5) Edit test inputs for simulated flights

Edit:

`flightwall_sim/sample_aircraft.json` (relative to the repository root)

Then rebuild/restart (include `-f docker-compose.yml -f docker/compose.test.yml` when using test mode):

```bash
docker compose up --build -d
```

## 6) Persistent data location

FAA SQLite/CSV/meta files are stored in Docker volume `flightwall_data`.

Compose prefixes the volume name with the project name (normally
`theflightwall_oss_forked_flightwall_data`). Inspect it with:

```bash
docker volume ls --filter label=com.docker.compose.volume=flightwall_data
```

Reset data:

```bash
docker compose down -v
```

## 7) Useful operations

Show logs:

```bash
docker compose logs -f pi-enrichment
docker compose logs -f flightwall-sim
```

Stop services:

```bash
docker compose down
```

Run FAA sync manually inside container:

```bash
docker compose exec pi-enrichment python /app/faa_pipeline.py
```

## 8) Troubleshooting

- If `pi-enrichment` startup is slow, FAA download/import is still running.
- If the FAA download returns HTTP 403, use the repeatable test mode above. Live FAA sync still requires access to the FAA download server.
- If `flightwall-sim` returns empty/unknown records, your sample ICAO values may not exist in FAA data. Use a known registered ICAO hex from your data to test successful enrichment.
- `/v1/aircraft/live` requires a separately configured `readsb/tar1090` receiver; the Docker simulator uses `sample_aircraft.json` instead.
- If ports are in use, change port mappings in `docker-compose.yml`.
- If Docker Desktop is running but commands fail, restart Docker Desktop and rerun `docker compose up --build`.

## Notes

The real firmware runs on ESP32 and cannot execute directly inside a standard macOS Docker container. The `flightwall-sim` container is provided to test the FlightWall enrichment flow on one machine without hardware.
