# Free departure and destination lookup for overhead flights

Research and Pi implementation, updated 2026-10-03. The main use case is aircraft
passing overhead: the user estimates about 95% will not land locally. Airport
ground-transition detection therefore has limited value for this requirement.

## Finding and recommendation

Use the received callsign to look up an airport pair in a callsign-route reference
database. This works for overflights when a suitable record exists; the receiver
does not need to observe takeoff or landing. Although ordinary ADS-B does not
broadcast the airport pair, a separate database can associate it with the callsign.

A suitable free downloadable source exists: **Virtual Radar Server standing data**.
It publishes actual callsign-to-airport records under **CC0 1.0 Universal**. Import
these into the Pi's local reference storage, join them to the received callsign,
and return the resulting route with its source. Updates need internet; routine
lookups can run locally with no API key, subscription, or per-flight WAN request.

This corrects the earlier recommendation, which focused too narrowly on observed
local takeoffs/landings. Google/manual flight-status lookup is also a valid way to
find or check a route. The local database is the recommended first automated path.

The dataset contains a **reference route**, not a dated confirmation of this
specific flight's plan. Display a matching airport pair as a reference route;
measure both match rate and correctness on actual overhead flights before claiming
coverage or current-flight accuracy. Keep unknowns when there is no suitable match.

## Verified data and primary sources

The following files were read directly during research:

- [VRS standing-data project](https://github.com/vradarserver/standing-data):
  aviation CSV data contributed by Virtual Radar Server users.
- [Route schema](https://github.com/vradarserver/standing-data/blob/main/routes/schema-01/README.md):
  documents callsign normalization, CSV layout, and ordered airport codes.
- [Dataset license](https://github.com/vradarserver/standing-data/blob/main/LICENSE):
  CC0 1.0 Universal; the dedication applies to this published data repository.
- [Route contributor credits](https://github.com/vradarserver/standing-data/blob/main/routes/schema-01/CREDITS.md):
  retain the source/license/credits with the import manifest.
- [Airline schema](https://github.com/vradarserver/standing-data/blob/main/airlines/schema-01/README.md)
  and [airport schema](https://github.com/vradarserver/standing-data/blob/main/airports/schema-01/README.md):
  describe the companion tables used to resolve codes/names.

At dataset revision `d856ef1ed0fc492e8a3933ff4a938448ed008f66`, the
[BAW route file](https://github.com/vradarserver/standing-data/blob/d856ef1ed0fc492e8a3933ff4a938448ed008f66/routes/schema-01/B/BAW-all.csv)
contains this real reference record:

```csv
Callsign,Code,Number,AirlineCode,AirportCodes
BAW117,BAW,117,BAW,EGLL-KJFK
```

The companion airport tables identify `EGLL` as London Heathrow (`LHR`) and
`KJFK` as John F Kennedy International (`JFK`). Thus the Pi can look up
`BAW117` and supply `LHR → JFK` while that aircraft is overhead. This is a
verified dataset example, not evidence of today's particular BA117 flight.

The sampled BAW file contained 4,388 records and the
[UAL file](https://github.com/vradarserver/standing-data/blob/d856ef1ed0fc492e8a3933ff4a938448ed008f66/routes/schema-01/U/UAL-all.csv)
contained 6,994. These counts describe those files at that revision; they do not
measure the user's traffic coverage. Files have no per-route flight date or
last-confirmed timestamp in schema 1. Download time or repository commit time must
not be presented as the time a particular route was verified.

## How to use the callsign

readsb's `flight` field is the transmitted identifier, often an airline ICAO
callsign such as `BAW117` or `UAL932`. A traveler may search for the IATA
marketing form, such as `BA117` or `UA932`. Keep the received value separately.

1. Trim padding and uppercase the lookup value; preserve the original identifier.
2. Apply the documented VRS normalization only to the lookup key. Use a known
   airline mapping for IATA-to-ICAO normalization and handle ambiguous mappings.
3. Preserve alphanumeric suffixes; do not turn an operational callsign such as
   `BAW3YA` into an invented passenger flight number.
4. Query the exact normalized callsign. A registration-only identifier or a
   missing/unaccepted pattern stays unmatched.
5. Read the ordered `AirportCodes` and resolve them through the companion
   airport table. Do not assume every code is ICAO: the schema permits IATA
   fallback when ICAO is unavailable.

The VRS schema describes leading-zero handling and limits on the number/suffix.
For example, it normalizes `EZY0001` to `EZY1`; do not change the displayed
received callsign merely to match the database.

ICAO/IATA prefix substitution helps a manual search for many scheduled flights,
but it is not proof of a marketing number. Codeshares, operational callsigns,
positioning flights, and reused numbers need conservative handling.

## Local import and route resolution plan

Add this to M4's reference enrichment; define its optional fields in M1 and render
available pairs in M6. Ground observations remain a separate later M8 feature.

1. Select a repository revision and download the route files plus companion airline
   and airport tables during explicit reference maintenance. Initially prepare
   common local airlines, then expand after measuring coverage.
2. Routes are partitioned under `routes/schema-01/{first-code-character}/`.
   Codes with up to 10,000 routes use `{code}-all.csv`; larger codes use
   `{code}-{first-number-digit}.csv`. Discover files at the selected revision;
   an absent `-all.csv` does not establish that the airline has no route data.
3. Stream CSVs into a staging SQLite reference generation. Index normalized
   callsign and airport code. Store source, revision, checksums, retrieval time,
   schema and license; retain credits. Do not load a worldwide dataset into RAM.
4. Join the current received callsign to the indexed route table. An explicit,
   dated route override can take precedence; record that source independently.
5. Return nullable route metadata: airport sequence, matching callsign,
   `source=vrs_standing_data`, `kind=reference`, dataset revision/retrieval
   time, and `flight_instance_verified=false`.
6. Activate validated generations using the existing staging/rollback design.
   Missing data or failed updates leave telemetry and the last good generation usable.

For a two-airport reference, the ordered pair gives its recorded origin and
destination. Some records have intermediate airports. Preserve the whole sequence;
do not automatically label the first/last airport as the current leg's endpoints.
If the active leg cannot be distinguished, expose an ambiguous/reference sequence
and keep current-leg fields unknown.

Compare position against route geography to reject obviously unrelated matches,
but a plausible location does not confirm the schedule, day, or intended landing
airport. Routes change, callsigns are reused, and diversions occur. Useful labels
are `Reference route`, `Verified for this flight` (only with dated evidence),
and `Unknown`; do not label a database match as an observed landing.

## Google and other online options

Manual Google search is useful for flight information and checking current routes.
Search the received callsign, airline, and relevant date; optionally use a known
IATA marketing alias. Example queries:

- `BAW117 flight October 3 2026`
- `British Airways BA117 October 3 2026`

A search result may show a flight card or link to airline/flight-status pages.
Check date, airline, direction, and leg before using its airport pair. A manual
finding can become a dated, sourced override. Do not copy an undated search snippet
into a permanent callsign rule.

This research did not verify a supported free API for Google's flight card.
A manual search link can be offered in diagnostic information. Automatic scraping
of search-result HTML would introduce an unstable interface; the recommended
automated approach uses the documented dataset or a provider API with suitable terms.

| Option | What was verified | Assessment |
| --- | --- | --- |
| VRS standing data | Callsign schema, CC0 license, contributor credits, and actual airport-pair rows. | Recommended free local source for reference routes. Current-flight correctness needs measurement. |
| [ADSBDB](https://github.com/mrjackwills/adsbdb) | Documents `GET https://api.adsbdb.com/v0/callsign/{callsign}` returning `response.flightroute.origin` and `destination`, with ICAO/IATA codes. Public GET examples show no API key. | A relevant hosted route lookup, but the README explicitly restricts copying/publishing/incorporating its route data without permission. Its software's MIT license does not remove that restriction; do not assume local caching/republication is permitted. |
| [ADSB.lol route service](https://github.com/adsblol/api/blob/main/src/adsb_api/utils/api_routes.py) | Source implements `POST /api/0/routeset` and describes VRS standing data as its route source. Includes a geographic plausibility flag. README says limits depend on load and keys may be required in future. | Another way to query reference routes; it does not establish a dated live itinerary. Prefer the licensed source files for the offline path. |
| [aviationstack](https://github.com/apilayer/aviationstack) | Provider README advertises a limited free plan and links to its terms/pricing. | Potential dated online option, subject to account/key, actual current quota, accessible endpoints and terms. The README's quoted quota is not verified current pricing or enough capacity for every overhead flight. |
| Google / airline flight-status pages | Manual lookup is the user's established workflow; no programmatic flight-card API was verified here. | Useful human verification/fallback, not evidence that an arbitrary automated query is supported. |

Hosted ADSBDB, ADSB.lol, HexDB, Google documentation, and aviationstack pages
returned proxy/network HTTP 403 from this environment. Their live responses or
current pricing were not verified. This is not evidence that a callsign is unknown
or that those services are down. GitHub documentation, source and VRS data were
accessible. No Google scraping, accounts, keys, or runtime route service were added.

## Optional local takeoff/landing observations

OurAirports' [airport/runway data](https://github.com/davidmegginson/ourairports-data)
can still support observed airport events. A fresh, continuous ground-to-air
transition near one suitable airport is departure evidence; an approach followed
by an air-to-ground transition is arrival evidence. Require more than a single
nearby position/ground flag and reject ambiguity or gaps.

Keep `observed_departure_airport` and `observed_arrival_airport` separate from
reference or verified itinerary fields. Bound track memory and persistent event
retention; the earlier 48-hour event window remains a provisional M8 budget.
This feature covers local events and does not solve most overhead-flight routes.

## Validation before implementation claims

- [ ] Record actual overhead callsigns and evaluate dataset match rate over several
  days; report unknown/registration-only/alphanumeric cases.
- [ ] Manually verify a representative set against dated Google/airline flight-status
  results. Measure correct airport pairs separately from merely finding a row.
- [x] Cover normalization, airport joins, missing files, partitioned airlines,
  multiple-stop routes, ambiguity, expiry, and dataset activation/rollback.
- [x] Verify provenance and licensing for the chosen VRS artifacts at the pinned revision;
  record checksums and retain license/schema/credits in each generation.
- [x] Keep reference routes distinct from flight-instance verification and observed events.
- [x] Demonstrate local route lookups after preparation with application WAN calls forbidden.
  Also verified `BAW117 → EGLL-KJFK` in a read-only-mounted Docker container
  with `--network none`.
- [ ] Confirm workload/storage/lookup latency on the Pi before expanding the dataset.

## Implemented Pi route slice

[route_pipeline.py](../pi_enrichment/route_pipeline.py) prepares selected airline
partitions or, with explicit `--all-routes`, a complete reference generation.
CSV and gzip archives stream through fixed buffers into disk-backed SQLite.
Companion airport/airline tables also stay on disk. No runtime whole-dataset
dictionary or archive index is loaded. A 1 MiB SQLite cache and disabled mmap
apply to imports and read-only lookups. Failed imports preserve the active
generation; gzip trailer/CRC, joins, counts and integrity are checked before
atomic activation. Previous generations remain available for rollback/readers.

[route_reference.py](../pi_enrichment/route_reference.py) implements conservative
aliases, exact callsign matches, airport order, complete code sequences, leg
ambiguity, provenance, and optional geographic rejection. Full airport details
are omitted for sequences longer than eight stops while all codes are retained
up to the 128-stop input bound. Dated manual evidence is maintained separately
with a validity window and optional aircraft scope; it cannot silently turn a
VRS reference into a verified current itinerary.

The existing Pi server exposes `/v1/routes/{callsign}`, adds `route_resolution`
to legacy live aircraft, and reports route-reference health independently of the
FAA registry. It has eight bounded request workers; no route download/import
runs during startup or lookup. See the [shared route contract](api/routes.md)
and [Pi commands](../pi_enrichment/README.md#offline-departuredestination-lookup).
The canonical flight feed and firmware detail page remain later integration work;
optional local ground-event detection remains deferred in M8.

On this Linux cloud runner at the researched revision, the BAW/UAL import stored
11,382 routes, 5,965 airlines and 34,128 airports in about 3.4 MiB SQLite, with
22.4 MiB peak process RSS. Importing all 620,396 routes used about 44.9 MiB SQLite
and 22.1 MiB peak RSS in 7.46 seconds. These are process measurements here, not
Pi/decoder/OS-cache or 24-hour hardware results. Actual traffic match rate and
dated correctness still need the user's receiver samples and manual comparisons.
