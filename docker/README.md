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

## 2) Start both services

From repository root:

```bash
cd /home/runner/work/theflightwall_oss_forked/theflightwall_oss_forked
docker compose up --build
```

What happens:
- `pi-enrichment` downloads FAA data (first start can take several minutes), imports SQLite data, then serves the API.
- `flightwall-sim` polls `pi-enrichment` and exposes test endpoints.

To run detached:

```bash
docker compose up --build -d
```

## 3) Verify the services

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

## 4) Edit test inputs for simulated flights

Edit:

`/home/runner/work/theflightwall_oss_forked/theflightwall_oss_forked/flightwall_sim/sample_aircraft.json`

Then rebuild/restart:

```bash
docker compose up --build -d
```

## 5) Persistent data location

FAA SQLite/CSV/meta files are stored in Docker volume `flightwall_data`.

Inspect:

```bash
docker volume ls
docker volume inspect flightwall_data
```

Reset data:

```bash
docker compose down -v
```

## 6) Useful operations

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

## 7) Troubleshooting

- If `pi-enrichment` startup is slow, FAA download/import is still running.
- If `flightwall-sim` returns empty/unknown records, your sample ICAO values may not exist in FAA data.
- If ports are in use, change port mappings in `docker-compose.yml`.
- If Docker Desktop is running but commands fail, restart Docker Desktop and rerun `docker compose up --build`.

## Notes

The real firmware runs on ESP32 and cannot execute directly inside a standard macOS Docker container. The `flightwall-sim` container is provided to test the FlightWall enrichment flow on one machine without hardware.
