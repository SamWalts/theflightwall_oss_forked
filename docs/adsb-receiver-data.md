# What the ADS-B receiver can provide

M1 reference inventory, 2026-10-03. This describes the input boundary; it does not
claim that the owner's installed receiver has been inspected. The SDR, readsb
version, enabled feeds and output directory still need M0 verification.

## 1. From radio signal to usable data

```mermaid
flowchart LR
    Aircraft[Aircraft transponder] -->|1090 MHz radio messages| Antenna[Antenna]
    Antenna --> SDR[Existing SDR: sampled radio signal]
    SDR --> Decoder[Existing readsb: decode and maintain tracks]
    Decoder --> JSON[Local aircraft.json snapshot]
    JSON --> Pi[FlightWall: normalize, filter, join references]
    Pi -->|LAN flight contract| ESP[ESP32: expire, select and render]
```

An antenna receives radio energy. The SDR samples it; readsb decodes messages and
combines updates into an aircraft record. The FlightWall API reads that record,
not individual RF samples. Different messages update identity, position and
velocity at different times; an `aircraft.json` row is not one simultaneous
measurement of every field.

A conventional 1090 MHz setup can decode 1090ES ADS-B and supported Mode S replies.
Some additional avionics values come from Mode S Comm-B replies rather than the
ordinary ADS-B position broadcast. Reception/decoding of each value is conditional
on the aircraft, nearby interrogations, decoder capability, and reception quality.
A 1090 MHz receiver does not directly receive 978 MHz UAT. An ADS-R rebroadcast of
UAT traffic may be heard on 1090 MHz, but it is a separately identified source.
ADS-C/satellite data or externally calculated MLAT can appear in readsb when
separate inputs are configured; they are not created by this single antenna.

The useful received categories are:

- Aircraft identity: ICAO address, transmitted callsign and emitter category.
- Position: decoded latitude/longitude, airborne/surface indication and altitude.
- Motion: ground speed, track and vertical speed; sometimes airspeed/heading/roll.
- Operational status: squawk, emergency/priority, alert/ident and selected settings.
- Data quality: ADS-B version, accuracy/integrity categories and related flags.

Availability is optional. Ordinary aircraft ADS-B messages do **not** contain
airline artwork, aircraft ownership records, a scheduled itinerary, or airport endpoints.
These need independent joins described in [enrichment joins](api/enrichment-joins.md).

## 2. Four kinds of values in decoder output

| Kind | Examples | Meaning for FlightWall |
| --- | --- | --- |
| Decoded aircraft information | `flight`, altitude, velocity, status bits | Received avionics information, subject to decoder validity and message availability. |
| Receiver/decoder bookkeeping | `now`, `seen`, `seen_pos`, `messages`, `rssi` | Created by the receiver, not transmitted by the aircraft as JSON. |
| Calculated or externally supplied values | CPR-decoded position, wind estimates, MLAT, range/bearing | Calculation/source must be identified; a field's presence is not proof of direct transmission. |
| Reference annotations | `r`, `t`, `desc`, `dbFlags` | Values from a configured local database; retain its provenance and reuse terms. |

`type` describes the decoder's best/current source, not the aircraft model.
`category` is a broad emitter category, not an ICAO type designator such as `B738`.
`flight` is a transmitted identifier, not a guaranteed passenger flight number.

## 3. Identity and position inventory

| readsb field | Format / unit | Origin and interpretation | Canonical feed use |
| --- | --- | --- | --- |
| `hex` | Six hexadecimal characters; sometimes prefixed `~` | 24-bit address or marked non-ICAO/pseudo-address. Valid-looking addresses can still be misconfigured/reassigned. | Validate exact six hex digits, uppercase; reject `~` and malformed values rather than stripping/padding them. Join aircraft references by this key. |
| `flight` | Up to eight transmitted characters, often space padded | Aircraft identification/callsign; can be airline operational code, registration, blank, mistyped or alphanumeric. | Preserve received string; normalize a separate lookup key. Missing callsign does not remove a fresh positioned aircraft. |
| `category` | `A0`–`D7` categories | Broad aircraft/vehicle class, not make/model. | Receiver diagnostics initially; never copy into `icao_type_designator`. |
| `lat`, `lon` | Decimal degrees | Usually decoded from Compact Position Reporting messages, with reference/even-odd pairing; could instead be MLAT/TIS-B. | Fresh, valid coordinates are required for geographic candidate eligibility. |
| `alt_baro` | Feet or literal `"ground"` | Barometric altitude, usually pressure altitude. Ground marker is a state, not altitude zero. | Numeric value → `altitude_baro_ft`; `"ground"` → numeric null and `ground_state="ground"`. |
| `alt_geom` | Feet | Geometric GNSS/INS altitude referenced to WGS84 ellipsoid. | `altitude_geom_ft`; never substitute into a field labeled barometric altitude. |
| Surface/airborne message context | Decoder-dependent | Surface reports and airborne reports carry different information. | Ground state may be known independently of numeric altitude. Unknown state remains `unknown`; do not infer ground solely from low altitude/zero speed. |

Latitude/longitude are the decoder's resolved position; the aircraft transmits
encoded CPR position information rather than a JSON latitude/longitude pair.
CPR decoding must remain with readsb. FlightWall must not start a second decoder.
At latitude/longitude zero, the position is valid; truthiness tests must not drop it.

## 4. Motion and avionics inventory

These values can be absent or expire independently in the decoder. Some come
from suitable ADS-B velocity messages; others commonly require decoded Comm-B
replies. Do not promise that every aircraft supplies them.

| readsb field | Unit / domain | Interpretation | Canonical v1 use |
| --- | --- | --- | --- |
| `gs` | Knots | Speed over ground. A valid zero is meaningful. | `ground_speed_kt`. |
| `track` | Degrees clockwise from true north | Direction of travel over ground. Track is not the direction the aircraft's nose points. | `ground_track_deg`; keep separate from receiver-to-aircraft bearing. |
| `baro_rate` | Feet/minute, signed | Barometric climb/descent rate. | Prefer for `vertical_speed_fpm`, label source `barometric`. |
| `geom_rate` | Feet/minute, signed | Geometric climb/descent rate. | Use when barometric rate is absent; label source `geometric`. |
| `ias` | Knots | Indicated airspeed when suitable messages are decoded. | `airspeed_ias_kt`; unknown otherwise. |
| `tas` | Knots | True airspeed when available. | `airspeed_tas_kt`; never copy GS here. |
| `mach` | Dimensionless | Mach number from available avionics data. | Retain Pi diagnostics; outside first display contract. |
| `mag_heading` | Degrees from magnetic north | Aircraft heading; not ground track. | Pi diagnostics initially. |
| `true_heading` | Degrees from true north | May be transmitted in some contexts; airborne value is often calculated using a magnetic model. | Pi diagnostics initially; not assumed to be received directly. |
| `track_rate` | Degrees/second | Turn rate in the decoder's track representation. | Pi diagnostics initially. |
| `roll` | Degrees; negative left | Bank angle where decoded. | Pi diagnostics initially. |
| `nav_qnh` | hPa | Reported altimeter setting; can represent QFE/QNH/QNE. | Diagnostic; do not treat it as measured local weather or silently correct displayed pressure altitude. |
| `nav_altitude_mcp` | Feet | Selected MCP/FCU altitude. | Diagnostic; selected altitude is not current altitude. |
| `nav_altitude_fms` | Feet | Selected FMS altitude. | Diagnostic; it does not reveal destination airport. |
| `nav_heading` | Degrees | Selected heading; reference can be ambiguous. | Diagnostic; cannot establish arrival airport or current route leg. |
| `nav_modes` | String set | Decoded autopilot/VNAV/altitude-hold/approach/LNAV/TCAS modes. | Diagnostic; approach mode is not proof of an observed landing. |

There is no universal per-metric timestamp in `aircraft.json`. `seen` is time
since **any** aircraft message; it is not the age of IAS, altitude, or heading
individually. M2 can use currently exported decoder-valid values, while documenting
the installed decoder's expiry behavior. It must not invent per-metric reception
times from `seen`. A stricter metric-age policy needs a richer source adapter.

## 5. Operational and integrity inventory

| readsb field | Meaning | Treatment |
| --- | --- | --- |
| `squawk` | Four octal digits, Mode A code | Diagnostic string, preserving leading zeros; not a flight or airline key. |
| `emergency` | ADS-B emergency/priority category | Diagnostic; possible labels include none/general/lifeguard/minfuel/nordo/unlawful/downed/reserved. |
| `alert`, `spi` | Flight-status alert and special-position-identification flags | Diagnostic; do not infer airline or airport. |
| `version` | ADS-B protocol version | Decoder/protocol diagnostic; unrelated to FlightWall `schema_version`. |
| `nic`, `nic_baro` | Navigation integrity categories | Data-quality context; not absolute guarantees of this particular fix. |
| `nac_p`, `nac_v` | Position and velocity accuracy categories | Diagnostic; missing categories do not fabricate accuracy. |
| `sil`, `sil_type` | Source integrity level and its interpretation | Keep interpretation with the level if exported later. |
| `sda` | System design assurance | Diagnostic. |
| `gva` | Geometric vertical accuracy category | Diagnostic; not a replacement for altitude value. |
| `rc` | Radius of containment in meters | Calculated from integrity information; not receiver range. |
| `acas_ra` | Experimental decoded ACAS advisory representation | Version-dependent diagnostic; excluded from v1 wall feed. |
| `gpsOkBefore` | Experimental decoder indicator of earlier usable GPS | Version-dependent diagnostic; not a scheduled flight timestamp. |

Raw emergency/status information could support a later display feature, but M1
does not turn it into an alerting product or a reliability claim.

## 6. Receiver and calculated inventory

| Field / file | What creates it | Important behavior |
| --- | --- | --- |
| Top-level `now` | Decoder snapshot generation time, Unix seconds | This is the source timestamp. A later HTTP response must not refresh it. |
| Top-level `messages` | Decoder message counter | May reset after decoder restart; counts all processed messages, not aircraft. |
| Per-aircraft `seen` | Decoder track bookkeeping, seconds before `now` | Used for aircraft message age; preserve separately from position age. |
| `seen_pos` | Decoder position bookkeeping, seconds before `now` | Required to prove position freshness. A recent non-position message does not refresh coordinates. |
| Per-aircraft `messages` | Receiver's accumulated count for this address | Diagnostic only; not a flight-instance identifier. |
| `rssi` | Receiver estimate, dBFS | Signal power relative to full scale, usually negative; not distance or confidence in an airport match. |
| `mlat`, `tisb` arrays | Decoder field-level provenance | Identify particular fields originating in MLAT/TIS-B; do not relabel them direct ADS-B. |
| `lastPosition` | Decoder's old stored fix with its original age | Historical fallback; never eligible as fresh position solely because this object exists. |
| `rr_lat`, `rr_lon` | Rough receiver-coordinate-based estimate | Not a measured aircraft fix; excluded from geographic candidate eligibility. |
| `wd`, `ws` | Calculated wind direction/speed from air/ground vectors | Not a direct weather observation from this antenna. |
| `oat`, `tat` | Calculated temperatures from Mach/TAS | Conditional approximation; outside v1 wall feed. |
| `receiver.json` | Decoder version/cadence and optionally configured receiver coordinates | Installation metadata, not aircraft transmissions. Verify coordinates before geographic filtering. |
| `stats.json` | Decoder/SDR performance statistics | Diagnostic CPU/drop/CPR counts; never copy into aircraft motion fields. |
| readsb API `dst`, `dir` | Query-center calculation | Nautical miles and direction from supplied center. FlightWall uses km and explicitly named bearing; convert rather than relabel. |

`type` can be `adsb_icao`, `adsb_icao_nt`, `adsr_icao`, `tisb_icao`, `adsc`,
`mlat`, `other`, `mode_s`, `adsb_other`, `adsr_other`, `tisb_other` or
`tisb_trackfile`. Non-ICAO addresses cannot join the registry as ordinary ICAO
keys. Ground vehicles/non-transponder emitters also need classification policy
before being presented as normal aircraft. The actual source allow-list belongs
to the verified Pi receiver configuration, not an ESP32 request parameter.

## 7. Reference fields and information absent from ordinary broadcasts

| Value | How it can become available | What must not be assumed |
| --- | --- | --- |
| Registration (`r`) | Configured readsb database or hex→registry join; occasionally a registration appears as the transmitted callsign | A transmitted registration-like string is not evidence that every row broadcasts registration. |
| ICAO model (`t`), description (`desc`) | Configured readsb database or approved aircraft reference | Emitter category and FAA numeric classification are not the model designator. |
| Owner | Registry MASTER record | Registered owner is not proof of the airline operating this flight. |
| Airline name/code | Recognized callsign prefix/alias plus airline table, or dated explicit evidence | Any arbitrary three-letter prefix and a marketing/codeshare label are insufficient. |
| Airline logo | Separately approved asset manifest joined by resolved airline identity | VRS airline CSV contains names/codes, not logo images or image licenses. |
| Departure/destination airports | Callsign→VRS ordered route→airport companion joins, or dated evidence | Heading, proximity, selected altitude and ADS-B position do not identify the intended airport by themselves. |
| Actual airport arrival/departure event | Later bounded local track/ground-transition detector | Passing near an airport is not an observed landing. |
| Scheduled/estimated arrival, itinerary date, gates, delays, diversion status | Separate suitable dated source/manual evidence | None are supplied by ordinary local ADS-B position telemetry or VRS schema 1. |

Some broader communications systems can carry flight plans, but that is outside
this existing receiver contract. The first offline route implementation uses the
documented VRS reference; it does not claim access to aircraft FMS itinerary data.

## 8. Sources and remaining installation checks

Field names/units and calculated/reference distinctions were checked against
[readsb README-json.md at revision 094720939c01943de82b14df6f42f67fff1cd514](https://github.com/wiedehopf/readsb/blob/094720939c01943de82b14df6f42f67fff1cd514/README-json.md).
The inspected document SHA-256 is
`abb581d94e5c12e52d45cd8f9096a250ee99cb4f84926e3217f5003c8d242b30`.
This is upstream documentation evidence, not the installed decoder's version.
Route-source schemas/license/revision are recorded in [route research](route-detection.md).

Before deploying M2, record the actual readsb version, local JSON path/cadence,
receiver coordinates, which external/rebroadcast inputs are enabled, individual
field expiry behavior, typical/worst snapshot size, and the observed source types.
Use synthetic fixtures until privacy-safe real receiver samples are available.
