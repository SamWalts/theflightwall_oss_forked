# Initial local flight API (schema version 1)

The Pi service serves `GET /v1/flights` on its existing port (8080 by default).
All timestamps are Unix seconds in UTC, including fractional seconds. The
response has `schema_version: 1`, `generated_at`, `receiver_snapshot_at` (nullable),
`receiver_status` (`ok`, `stale`, or `unavailable`) and `flights` (at most eight).
An empty fresh receiver returns `ok` and `[]`. Missing/malformed input returns
`unavailable`; a snapshot older than five seconds or more than one second in the
future returns `stale`. All three states return HTTP 200 so clients can distinguish
them from a failed HTTP connection. `/health` also exposes `receiver_status`.

Each flight has:

| Fields | Meaning |
| --- | --- |
| `adsb_icao`, `callsign` | Six hexadecimal characters; received trimmed callsign or null |
| `lat`, `lon` | Fresh received position in degrees |
| `last_seen_at`, `position_seen_at` | Original readsb `now` minus `seen`/`seen_pos` |
| `on_ground` | True when `alt_baro` is `"ground"` |
| `altitude_baro_ft`, `altitude_geom_ft` | Nullable received altitudes in feet |
| `ground_speed_kt`, `airspeed_ias_kt`, `airspeed_tas_kt` | Nullable speeds in knots; never substitute GS for airspeed |
| `vertical_speed_fpm`, `vertical_speed_source` | Nullable signed rate; barometric preferred, otherwise geometric |
| `registration`, `aircraft_type`, `aircraft_model`, `aircraft_reference_source` | Optional local reference data; readsb `r`/`t`/`desc` preferred |
| `operator_name`, `operator_icao`, `operator_resolution_source` | Null until local operating-airline resolution is implemented |
| `origin`, `destination`, `logo_path` | Null until local routes/assets are implemented |

Aircraft must have a valid hex and position, and both reception and position ages
must be at most 15 seconds. Callsign and registry matches are optional. FAA
registered-owner names are not presented as operating airlines, and FAA numeric
classification codes are not presented as ICAO aircraft types. Missing/corrupt
registry data never suppresses live telemetry.

Snapshots are cached for one second. Reads are capped at 4 MiB; the firmware
requires a Content-Length and caps HTTP bodies at 16 KiB, eight flights and two
seconds of body reading. This initial version preserves receiver list order and
has no geographic/altitude filters or distance ordering. No external lookup
fallback is used.

## Receiver handoff

On the existing Pi, inspect `systemctl status readsb` and its configured service
command to find its JSON directory. Confirm the `now` timestamp in `aircraft.json`
advances and that the API service user can read the file. Do not install another
decoder or assume the path matches another installation.

Run the service with the confirmed path:

```sh
python3 pi_enrichment/server.py --aircraft-path /run/readsb/aircraft.json --port 8080
curl http://127.0.0.1:8080/v1/flights
```

`READSB_AIRCRAFT_PATH` is the equivalent environment setting. With no file path,
the existing `--tar1090-url`/`TAR1090_AIRCRAFT_URL` setting supplies the local HTTP
snapshot. Use an explicitly configured local receiver endpoint. File input wins
when both are set. Existing `/v1/aircraft/{hex}`, `/v1/meta`, and
`/v1/aircraft/live` endpoints remain compatible.

Tests: `python3 -m unittest discover -s pi_enrichment -v`. Follow-up work and
physical acceptance are tracked in [the implementation plan](flightwall-local-plan.md).
