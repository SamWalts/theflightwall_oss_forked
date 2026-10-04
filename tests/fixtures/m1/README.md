# M1 shared contract examples

Draft 0.1, 2026-10-04. These are hand-authored examples for the proposed
[Pi-to-ESP32 contracts](../../../docs/api/README.md). They are not captured live
traffic, application regression results, or a working receiver replay harness.

## 1. Files and injected conditions

| File/directory | Meaning |
| --- | --- |
| `cases.json` | Index of examples, contract kind, expected validity and failure layer. |
| `receiver/` | Small synthetic readsb inputs associated with the examples. A missing file is not an implicit fresh/healthy input. |
| `envelopes/` | Proposed normalized `/v2/flights` output, including intentionally invalid producer output. |
| `contexts.json` | Per-flight-case Pi wall/monotonic clocks, established-progress state, filter settings and optional generator descriptions. |
| `reference-inputs.json` | Illustrative small join tables, route sequences, mock descriptor and dated evidence; not a complete importable SQL generation. |
| `routes/diagnostic-reference.json` | Existing diagnostic route response shape, distinct from the compact feed projection. |
| `logos/descriptor.json` | Placeholder descriptor only; no corresponding approved image exists. |
| `timing-cases.json` | Expected arithmetic for the proposed ESP32 expiry rules. |

Synthetic time is anchored to `2026-10-03T22:00:00Z`; it is an injected fixture
clock, not a claim that these aircraft were observed then. Uppercase hex values,
`TEST-REG`, owner/model text, aliases and evidence are invented. BAW117's
`EGLL → KJFK` pair and KAP48B's eleven-stop sequence follow the previously
inspected CC0 VRS revision `d856ef1ed0fc492e8a3933ff4a938448ed008f66`.
The three-stop BAW3YA example is synthetic. Route examples establish ordering and
ambiguity semantics; they do not establish a real flight itinerary on this date.

The repeated `f` logo hash is mock metadata. No bitmap with that hash is supplied,
approved, or expected to render. No airline artwork is licensed by these fixtures.

## 2. Coverage

| Examples | Contract purpose |
| --- | --- |
| `complete`, `partial` | Full and missing optional metrics; useful fresh position survives missing references/artwork. |
| `no-callsign`, `unknown-references`, `ambiguous-alias` | Hex fallback; unknown owner/operator/logo/route; reject ambiguous airline aliases. |
| `ground-and-zero`, `zero-coordinates` | Preserve numeric zero, explicit surface state, null barometric altitude for ground and null bearing at a coincident center. |
| `healthy-empty`, `filter-unconfigured` | Distinguish empty receiver output from a missing geographic configuration. |
| `expired-position`, `expired-aircraft` | Independent position/message expiry removes candidates. |
| `initializing`, `offline-clock` | Establish source progress before cards; relative freshness works without trusted UTC. |
| `source-missing`, `invalid-source` | Unavailable/malformed input clears flights without claiming empty sky. |
| `clock-future`, `clock-backward` | Reinitialize on clock discontinuity. |
| `frozen-source`, `old-snapshot` | Successful reads cannot revive frozen or old input. |
| `multi-stop`, `long-route` | No invented active leg; compact feed omits sequences over eight stops while retaining count and ambiguity. |
| `dated-override` | Synthetic date/hex-scoped evidence, source and monotonic remaining validity. |
| `source-byte-limit`, `source-row-limit` | Generate oversized input later; report invalid source rather than quietly truncate decoded rows. |
| `candidate-cap`, `byte-budget-prefix` | Deterministic complete nearest prefix with count/byte truncation reasons. |
| `invalid-body-byte-limit` | Schema-valid fields can still exceed the UTF-8 body budget. |
| Other `invalid-*` | Unsupported version, invalid address/required key/metric type/reference verification/multi-stop leg, control characters, counts, source ID and logo joins. |
| `diagnostic-reference`, `logo-descriptor` | Existing full diagnostic shape and proposed asset descriptor. |

## 3. How later implementations should use them

Start with the [offline documentation checker](../../../docs/api/validation.md).
Its schemas and relationship checks verify expected valid/invalid producer
examples. It does not run the Pi normalizer or ESP32 parser.

Build M2 replay by injecting the context's clocks, source inputs, local lookup
results and configuration. Some contexts deliberately disable geography checking
or inject an unresolved operator to illustrate partial reference output. The
maximal-byte examples use synthetic distance ordering to stress the output
contract; their generator is not a simulated aircraft movement model.

Large cases must be generated in the future replay harness: 4 MiB + 1 byte JSON,
513 rows, nine eligible candidates, and maximal bounded Unicode strings. The
small descriptions here avoid storing large files; they are not executable input
generators and are not evidence that the runtime rejects those sources yet.

Build M3 parser/selection/timing cases using the same envelopes. Preserve absolute
expiry deadlines for repeated instance/sequence responses, remove cards on
successful absence/non-ready receiver state, and test unsigned counter wrap.
Unknown optional metadata uses fallbacks according to the contract, even when a
producer example is deliberately invalid. Do not add a competing firmware schema.

Add real approved M6 bitmaps as a separate fixture slice with hashes and provenance.
The descriptor placeholder is not suitable for a successful asset-fetch check.
