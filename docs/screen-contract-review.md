# FlightWall screen contract review

Reviewed 2026-10-04. Design branch: `design/flightwall-screens` at
`c1b274e41c7176556ccdae090c13262b4b6472ca`. Target: `dev` at
`61178bb3f4a52e3e0532d806db650c86f17989e1`.

Initial review held the merge under the user's instruction to merge only if
there are no issues. The original findings below describe that snapshot; the
resolution section records the completed corrections. The reviewed design commit
changed documentation and review artifacts, not Pi/firmware runtime code or the
maintained API schemas. Its gallery worked, but its proposed data and state rules
needed alignment with M1 before integration.

## Required changes

| Finding | Design evidence | Contract requirement and correction |
| --- | --- | --- |
| Overflight route references are excluded; inferred endpoints are accepted. | [Screen specification, route provenance](https://github.com/SamWalts/theflightwall_oss_forked/blob/c1b274e41c7176556ccdae090c13262b4b6472ca/docs/screens/README.md#L75) and [sourced_endpoint](https://github.com/SamWalts/theflightwall_oss_forked/blob/c1b274e41c7176556ccdae090c13262b4b6472ca/docs/screens/render_mockups.py#L221) accept only manual/observed/inferred values. | M1 uses `preferred_route`, `route_reference` and `route_override`. Display an available CC0 VRS reference as a reference/likely pair, with `flight_instance_verified=false`; handle dated evidence separately. Do not turn observations or heading/proximity inferences into an itinerary. This matters for the user's mostly overhead traffic. |
| Destination-only and inferred-departure examples lack a current M1 representation. | [N05](https://github.com/SamWalts/theflightwall_oss_forked/blob/c1b274e41c7176556ccdae090c13262b4b6472ca/docs/screens/README.md#L93), C05, and independent nullable endpoint rules. | A compact two-stop route has both endpoints; multi-stop routes have neither active-leg endpoint. No inferred-route field exists. Observed airport events are independent fields and first M2 emits null. Revise these examples, explicitly defer them, or propose a versioned contract change with updated schemas, fixtures and byte checks. A single manually supplied planned destination cannot silently use the observed-arrival field. |
| City labels require data absent from the compact flight feed. | [F05](https://github.com/SamWalts/theflightwall_oss_forked/blob/c1b274e41c7176556ccdae090c13262b4b6472ca/docs/screens/README.md#L55) and [city renderer](https://github.com/SamWalts/theflightwall_oss_forked/blob/c1b274e41c7176556ccdae090c13262b4b6472ca/docs/screens/render_mockups.py#L255) require endpoint `city`. | M1 supplies canonical airport codes and bounded departure/destination display codes, not city names. Use those codes, defer city names pending a documented offline catalogue, or explicitly extend the wire contract. Do not add per-aircraft diagnostic/WAN requests. |
| Missing-callsign identity differs from the canonical display identifier. | [identifier](https://github.com/SamWalts/theflightwall_oss_forked/blob/c1b274e41c7176556ccdae090c13262b4b6472ca/docs/screens/render_mockups.py#L195) selects registration before hex. | M1 `display_identifier` uses the received identifier or hex. Keep registration in the airframe/identity details and selection keyed by `adsb_icao`; use the documented identifier for default flight cards. |
| Unknown airline is shown as a resolved code badge. | [C01](https://github.com/SamWalts/theflightwall_oss_forked/blob/c1b274e41c7176556ccdae090c13262b4b6472ca/docs/screens/README.md#L112) calls the operator unknown but supplies an `XYZ` badge. | M1 unknown operator has null identity/name/codes/source. Use a neutral badge; only a recognized unambiguous airline reference or applicable dated evidence supplies an operator code. A callsign prefix alone is insufficient. |
| Receiver states and missing viewing configuration are not fully represented. | [S05/S06](https://github.com/SamWalts/theflightwall_oss_forked/blob/c1b274e41c7176556ccdae090c13262b4b6472ca/docs/screens/README.md#L131) call missing/invalid/stale data stale and do not specify selection-unconfigured handling. | Map M1 `initializing`, `unavailable`, `invalid`, `stale`, and `ready` explicitly, plus `selection.status=unconfigured`. Only ready/configured with zero eligible candidates is empty sky. Progress/relative-age deadlines must override page dwell. |
| No executable mapping connects the design examples to M1. | `fixtures.json` is explicitly a separate review model: flat fields, a string ground altitude and barometric-only rate. Existing gallery checks run those examples only. | Define the display projection from M1's nested candidate fields, including numeric-null altitude plus `ground_state`, labeled barometric/geometric rate, IAS/TAS, route evidence and nullable logo. Exercise representative shared M1 examples through that projection. The current prototype feed also differs from M1; its shared version number does not make it compatible. |

The maintained definitions are the [flight contract](api/flights.md),
[join rules](api/enrichment-joins.md),
[logo contract](api/logos.md), and
[contract index](api/README.md).
Keep those definitions authoritative; the October 1 source plan alone does not
include the later route and compact-feed decisions.

## Merge and validation evidence

- A non-mutating `git merge-tree --write-tree dev origin/design/flightwall-screens`
  reports a README content conflict. Preserve dev's correct legacy-photo caption
  and local-migration status, then add the screen-review links when integrating.
- `render_mockups.py --check` passed for all 34 native 160×32 screens, text bounds,
  unknown/zero/ground values, route labels, and no-departure selection examples.
- `verify_review.py --browser /usr/bin/chromium` passed export/pixel agreement,
  logo hashes, PDF presence, gallery controls, deep links, downloads, keyboard/demo
  navigation, 390/768/1440 px layouts, and no external browser requests.
- Inspected the flight, no-departure and system-state contact sheets visually.
  These checks prove the review gallery, not real LED wiring or runtime freshness.
- M1 checker passed three schemas, 40 expected outcomes (28 valid and 12 deliberate
  failures), and seven timing examples. The design branch changes none of these
  schemas or shared fixtures, and its own examples were not validated as M1 JSON.
- Review logos are 24×24 PNG pixel interpretations with
  `production_approved=false`. This is consistent with keeping production asset
  approval and RGB565 serving/cache in M6. Recognition of an operator alone cannot
  authorize those review images as production logos.
- The design branch has not been merged into dev; this document publishes
  review findings only.

## PlatformIO setup

PlatformIO Core 6.2.0 is installed in `/workspace/.venvs/flightwall-platformio`.
Activation/version and `pio project config --json-output` passed for both existing
environments. Use `/workspace/.cache/flightwall-platformio` as `PLATFORMIO_CORE_DIR`.

`pio run -e esp32dev -e wokwi` stopped during ESP32 platform installation, before
compilation. The running proxy rejects `api.registry.platformio.org` with HTTP
403; this is an environment prerequisite, not a confirmed firmware compiler bug.
Official platform metadata is reachable through GitHub, but its required binary
dependencies are registry packages. No alternate Arduino/toolchain stack was
substituted, and TLS/package verification remains enabled.

A saved environment draft preserves the previous fixture workflow and adds the
pinned Core installer, activation/build instructions and two custom domains:
`api.registry.platformio.org` and `dl.registry.platformio.org`. The tool confirmed
`status=saved` and `requires_publish=true`. Review/save the changes in environment
settings and publish the environment, then recheck actual access and resume both
builds. Draft saving does not apply runtime access or establish build success.

## Resolution, 2026-10-04

All seven contract findings and the README merge conflict are resolved in the
integration branch `review/flightwall-conflicts`. The newly published review
commit `2ce1328` is included; its project-context changes are reconciled with the
integration results. The original evidence above remains a record of the reviewed
snapshot, rather than a statement of the corrected code.

| Finding | Correction and validation |
| --- | --- |
| Reference routes / evidence | `canonical_view` uses the preferred reference/dated route; labels reference, dated and verified evidence separately. Multi-stop routes never select a leg. Expired overrides fall back to an available reference. Shared-fixture tests cover these paths. |
| Destination-only / inference | N05 and C05 are explicitly deferred, marked `FUTURE CONCEPT` in the gallery and captions in the exported review. The canonical projection does not emit them or consume observed airport fields as itinerary endpoints. |
| City data | F05 uses bounded airport display codes, falling back to canonical codes. No city catalogue or per-flight lookup is assumed. |
| Default identity | Default cards use canonical `display_identifier`; registration stays in airframe/identity details. Shared no-callsign fixture and refreshed private-aircraft examples verify this. |
| Unknown airline | C01 uses neutral AIR artwork; canonical unknown or expired operator evidence projects no operator code/name/logo. Received telemetry remains visible. |
| Receiver / viewing states | `canonical_display` maps initializing, unavailable, invalid and stale separately; ready/unconfigured is a view-configuration screen. Only ready/configured empty input is healthy empty sky. Elapsed snapshot/progress/candidate ages preempt dwell. Stable same-host clocks still permit live telemetry without trusted UTC. |
| Executable M1 mapping | The projection maps nested aircraft/telemetry/operator/logo/route data, ground state and IAS/TAS. VS is barometric; explicit GVS labels a geometric rate. Ten tests exercise shared canonical envelopes and expiry boundaries. |

The incompatible wire-version collision is separately resolved by
[D013](decisions.md#d013--separate-prototype-and-canonical-flight-versions): preserve
working `/v1/flights`/version 1 and reserve `/v2/flights`/version 2 for M1 flight
draft 0.2. Schemas and examples are updated together; canonical runtime adoption
remains M2/M3 work. Existing route and logo versions are unchanged.

Validation for the corrected integration: ten projection tests, three schemas,
40 expected fixture outcomes and seven timing cases pass. All 39 export sets
and gallery checks pass, including eleven system screens, future-concept markers,
390/768/1440 px layouts and no external browser requests. The 25 Pi regression
tests passed earlier in this same integration; subsequent edits only affect the
screen/documentation slice. Git whitespace and local documentation links pass.
Firmware builds and physical LED/receiver acceptance remain separate pending work;
no firmware or Pi runtime code changed in this screen integration.
