# Checking the M1 contract draft

Draft 0.1, 2026-10-04. These are offline documentation checks. They establish
that the proposed schemas/examples agree; they do not establish implementation
of `/v1/flights`, the receiver state machine, or an ESP32 consumer.

## 1. Reproducible commands

Run from the repository root. The Pi service still uses the Python standard
library. The following optional dependency belongs only to documentation tools:

```bash
python3 -m venv /tmp/flightwall-contract-docs
/tmp/flightwall-contract-docs/bin/python -m pip install -r docs/api/requirements.txt
/tmp/flightwall-contract-docs/bin/python -B docs/api/check_contracts.py
```

With `jsonschema==4.26.0` already installed, use:

```bash
python3 -B docs/api/check_contracts.py
```

Package installation may need network access. The checking command resolves all
schema URNs from local repository files and requires no internet, flight API
credentials, running services, receiver, or firmware build. It writes no runtime
state. An unknown schema reference fails; it is not downloaded from a website.

## 2. What is checked

| Layer | Check |
| --- | --- |
| JSON | Parse without duplicate keys or NaN/Infinity constants. |
| Schema definitions | Validate all three schemas against JSON Schema 2020-12. |
| Producer examples | Required keys, types, nulls, numeric/string bounds, explicit UTC formats, cardinalities and conditional route/receiver meanings. |
| Cross-field joins | Response source IDs exist; field/source nulls agree; logo operator matches the resolved operator; logo path matches its hash. |
| Route relationships | Matched callsign, ordered sequence/stop count/endpoints, preferred object, dated scope/window/remaining validity and reference verification semantics. |
| Counts and ordering | Unique aircraft/source IDs, returned array count, truncation reason, emitted distance/hex ordering and depth budget. |
| Body bytes | Compact UTF-8 JSON is at most 16,384 bytes; an intentional over-limit example fails this check despite passing the schema. |
| Timing arithmetic | Request elapsed time, source/message/position expiry, 32-bit counter wrap, reboot invalidation, same-sequence deadline retention and dated-evidence expiry. |

The checker measures compact serialization with `ensure_ascii=False`. Pretty
fixture files contain whitespace and are not literal HTTP bodies. A runtime
producer using different escaping or number formatting must measure its own
actual serialization; matching the candidate cap or character bounds is not a
substitute for a byte check.

The examples are hand-authored contract cases. The checker does not calculate
their expected output from receiver JSON. The context file specifies injected
clock/settings conditions for later replay work; large-input cases use small
generator descriptions rather than checked-in multi-megabyte JSON.

## 3. Byte-budget evidence

The maximal eight-row Unicode example contains both a reference route and dated
override, bounded display text, explicit field provenance and logo metadata.
It is deliberately too large. The valid companion returns a complete nearest
prefix and reports the omitted eligible rows. This proves the need to apply the
byte limit after enrichment and to preserve complete retained records.

One maximal row fits in the body budget. These examples do not exhaust every
permitted schema combination, prove total Pi memory use, or prove that an ESP32
JSON document uses only 16 KiB. M3 must measure input buffering, parse nodes,
copied strings, task stacks, BLE/Wi-Fi and the display buffer together.

Measured with the checker serialization:

| Example | Returned / eligible | Body bytes | Outcome |
| --- | --- | --- | --- |
| `complete` | 1 / 1 | 3,454 | Accepted. |
| `invalid-body-byte-limit` | 8 / 8 | 32,627 | Rejected by byte limit; schema alone passes. |
| `byte-budget-prefix` | 3 / 8 | 13,279 | Accepted with `byte_limit`. |
| `candidate-cap` | 7 / 9 | 15,300 | Accepted with `count_and_byte_limit`. |

## 4. Consumer behavior is a separate acceptance gate

The strict schemas describe correct producer output. A firmware consumer follows
the [flight rejection/degradation rules](flights.md): malformed envelopes and
unsupported versions fail the feed; invalid core identity/age/position drops the
row; invalid optional enrichment becomes unknown while useful core telemetry
survives. A negative producer fixture need not imply a whole-feed failure.

M2 needs executable receiver replay and HTTP checks using these cases, including
two advancing snapshots, read failures, frozen JSON, fresh reads of old source
time, clock changes, filtering, input limits and byte-prefix construction.
M3 needs the actual bounded firmware parser, expiry scheduler, selection/dwell,
out-of-order response handling and independent render/network tasks. M6 needs
actual approved bitmap bytes, conversion, headers, corruption/fallback and cache
checks. Physical receiver/LED/BLE/offline operation remains M0/M5/M7 evidence.

Keep these stages explicit in [project context](../project-context.md). A passing
documentation check does not complete those milestones.
