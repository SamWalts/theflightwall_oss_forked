# FlightWall Pi Enrichment Service

Local Raspberry Pi service that:
- Downloads FAA registry data and imports it into SQLite.
- Serves a local HTTP API for ADS-B ICAO (`hex`) enrichment.
- Optionally enriches `readsb/tar1090` live `aircraft.json` output.

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

## FAA sync pipeline

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
