# API health and reference metadata contracts

M1 draft **0.1**, 2026-10-03. Existing FAA/route fields below are implemented.
The prototype also adds `receiver_status`; canonical receiver/capability and
general-manifest additions are proposed for M2/M4/M6 and
must not be advertised as present before their runtime exists. These endpoints
are diagnostics; the ESP32's normal card loop consumes the flight envelope.

## 1. `GET /health`

Purpose: distinguish an available API process, receiver condition and reference
condition. HTTP 200 with `status="ok"` means the API handled the health request;
it does not imply fresh aircraft, a working receiver, a registry match or logos.
Source outages can remain domain data while the API stays available.

Current response shape is illustrated by:

```json
{
  "status": "ok",
  "receiver_status": "unavailable",
  "db_exists": false,
  "last_sync_at": "",
  "stale": true,
  "updated_at": "2026-10-03T22:00:00Z",
  "route_reference": {
    "status": "ready",
    "source": "vrs_standing_data",
    "generation": "d856ef1ed0fc-00000000000000000000000000000001",
    "revision": "d856ef1ed0fc492e8a3933ff4a938448ed008f66",
    "retrieved_at": "2026-10-03T21:00:00Z",
    "dataset_age_seconds": 3600,
    "license": "CC0-1.0",
    "counts": {"routes": 11382, "airlines": 5965, "airports": 34128, "artifacts": 667}
  }
}
```

The times/generation here are illustrative. Reference counts correspond to the
researched BAW/UAL import, not live traffic.

| Existing field | Semantics |
| --- | --- |
| `status` | Process/API health, currently `ok` for a handled response. |
| `receiver_status` | Initial feed status: `ok`, `stale` or `unavailable`. This is not the canonical nested M1 receiver state. See [prototype API](../local-flight-api.md). |
| `db_exists` | Legacy FAA registry file presence; not reference-data validity. |
| `last_sync_at` | Legacy FAA sync timestamp string, empty when unknown. |
| `stale` | Legacy FAA age flag using `STALE_AFTER_HOURS`, default 72. It is not receiver expiry or route accuracy. |
| `updated_at` | Current API wall-clock timestamp; existing API does not express confidence. Do not use it to revive aircraft. |
| `route_reference` | Independent implemented route store summary described below. |

### Proposed additive fields

| Draft field | Bound / responsibility |
| --- | --- |
| `instance_id` | Same process ID as `/v1/flights`. |
| `supported_contracts` | At most eight entries `{name, version, path}` identifying actually implemented contracts. Names ≤32 ASCII, versions positive bounded integers, paths ≤96 relative characters. |
| `receiver` | Same receiver object/semantics as [flight contract](flights.md), when M2 is supported. No separate definition of freshness. |
| `selection_status` | `ready` / `unconfigured`, independent of radio state. |
| `references` | At most eight component summaries for aircraft, routes/airlines, logos and overrides; field rules below. |
| `clock_confidence` | Same global UTC interpretation used by the flight response. |

Retain existing top-level fields during migration. If a legacy DB file exists
but is malformed, the new reference summary can report `invalid`; do not change
the meaning of `db_exists` to hide the disagreement. Missing/old reference data
must not turn a ready receiver into a false unavailable receiver.

## 2. Route store summary already implemented

The same `route_reference` object is present in `/health` and `/v1/meta`:

| Field | Type / semantics |
| --- | --- |
| `status` | `missing`, `invalid`, `ready`; ready means a readable supported active generation, not a dated route guarantee. |
| `source` | `vrs_standing_data`. |
| `generation` | Active immutable generation ID or null. |
| `revision` | Full VRS revision or null. |
| `retrieved_at` | Import completion UTC string or null. |
| `dataset_age_seconds` | Time since import, clamped at zero by current implementation; null when no dataset. Not per-route verified age. |
| `license` | `CC0-1.0` or null. |
| `counts` | Empty when missing/invalid, otherwise route/airline/airport/artifact row counts. |

No metadata request downloads reference data, lists a worldwide table in RAM or
refreshes receiver state. The current summary reads a pinned local generation.
Its existing age calculation trusts the Pi's wall clock. The future canonical
source table must report null reference age when UTC is not trustworthy rather
than implying dated precision from this legacy diagnostic behavior.

## 3. `GET /v1/meta`

Purpose: show what local references are prepared and how they were obtained.
It is neither telemetry nor the API that serves binary logos.

| Current field | Meaning |
| --- | --- |
| `schema_version` | Legacy metadata shape version 1; not flight contract capability. |
| `row_count` | Legacy FAA aircraft row count. |
| `faa_csv_checksum` | Checksum of that imported FAA CSV snapshot. |
| `faa_source_url` | Configured FAA source URI, not an ESP32 fetch instruction. |
| `last_sync_at` | Legacy sync time or empty string. |
| `db_path` | Legacy diagnostic local path; retained for compatibility, not a firmware asset path. |
| `updated_at` | Legacy wall-clock serialization time. |
| `route_reference` | Independent local route summary above. |

### Proposed general reference manifest summary

Add `supported_contracts` and `references` without removing legacy fields.
`references` contains at most eight bounded component summaries:

| Draft summary field | Rule |
| --- | --- |
| `component` | Bounded identifier such as `aircraft`, `airline_routes`, `logos`, `overrides`. |
| `status` | `missing`, `invalid`, `ready`; optional age warning must remain distinct from record accuracy. |
| `storage_mode` | `immutable_generation`, `mutable_overrides`, or `legacy_mutable`. Do not invent atomic FAA generations before M4 implements them. |
| `source`, `source_uri` | Named provider and bounded credential-free source URI. A data-source URI is not approved artwork. |
| `generation`, `previous_generation`, `revision` | Actual version IDs or null where unavailable; component versions remain separate. |
| `retrieved_at`, `age_seconds`, `clock_confidence` | Import age with explicit trustworthy-time interpretation. |
| `database_sha256` | Prepared generation DB hash or null; hash of source CSV is a separate artifact. |
| `license_label`, `attribution_summary` | Bounded summary; full artifact terms/credits retained with prepared generation. |
| `counts` | Component/table/asset counts, bounded keys and nonnegative values. Counts are not local-traffic coverage. |
| `artifact_manifest_storage` | Identifier for local retained checksum records; no enormous inline worldwide artifact array. |
| `last_update` | Bounded `{state, attempted_at, completed_at, reason}`; state `never`, `running`, `succeeded`, `failed`. Describes maintenance, not receiver liveness. |

Draft metadata byte budget is 16 KiB, independent of the 16 KiB flight-feed
budget. Keep full artifact manifests/checksum rows on disk for explicit local
maintenance; do not stream every airline/airport/image row in a health poll.
Queries pin generations and remain readable while maintenance prepares new ones.

Individual logo artifact approval/source/hash/conversion records must exist in
the prepared asset manifest before any feed descriptor is emitted. Metadata can
summarize that generation, but a global label cannot grant all source images the
same license. Overrides keep their own scope/evidence and are not overwritten by
a downloaded generation.

## 4. HTTP and error interpretation

Health/meta JSON uses identity encoding and Content-Length. Target cache policy
is `Cache-Control: no-store` for health and revalidation for metadata; the current
legacy handler does not set these headers. Dynamic flight responses require
no-store and never use 304 in the first feed contract.

| Event | Meaning |
| --- | --- |
| `/health` 200, receiver stale/unavailable | API works; no valid live card. |
| `/health` 200, registry stale/missing, receiver ready | Continue fresh telemetry with available/null enrichment. |
| `/v1/meta` supported version but no logo component | No implemented/approved local logo service; do not construct a cloud image fallback. |
| HTTP 503 | Bounded API worker pool is full; retry with backoff while local expiry continues. |
| HTTP timeout/5xx/bad JSON | Diagnostic/request failure, not proof of healthy empty sky. |

Neither response should cause the wall to reset a card's age. The single
authoritative live state and data-age rules come from `/v1/flights` when implemented.
Deployment/pollers must not infer that endpoint exists merely from the current
metadata `schema_version=1`.

## 5. Pending work

M2 must add receiver/capability summaries and catch source/reference faults without
gating API startup. M4 must correct/version aircraft references, and M6 must add
approved asset generation summaries. Current route/FAA fields and their consumers
stay compatible until an explicit migration replaces them. Full diagnostic schemas
can be finalized once those additions are implemented; M1's strict producer schema
currently covers the flight feed, logo descriptor and implemented route object.
