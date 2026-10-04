#!/usr/bin/env python3
"""Check M1 documentation artifacts offline; this does not exercise application code."""

import json
import math
import sys
from datetime import datetime
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
except ImportError:
    sys.exit("Install the optional documentation dependencies in docs/api/requirements.txt.")

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "docs" / "api"
FIXTURES = ROOT / "tests" / "fixtures" / "m1"
BODY_LIMIT = 16384
TICK_MODULUS = 1 << 32
SCHEMAS = {
    "flights": "flights-v1.schema.json",
    "routes": "route-resolution-v1.schema.json",
    "logo": "logo-v1.schema.json",
}


def reject_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=reject_constant, object_pairs_hook=unique_keys)


def body_bytes(body):
    return len(json.dumps(body, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False).encode("utf-8"))


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def nesting(value):
    if isinstance(value, dict):
        return 1 + max((nesting(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((nesting(item) for item in value), default=0)
    return 0


def flight_relationships(body):
    """Relationships that JSON Schema cannot express without custom extensions."""
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    flights = body["flights"]
    selection = body["selection"]
    source_rows = body["reference_sources"]
    sources = {row["id"]: row for row in source_rows}
    require(len(sources) == len(source_rows), "reference source IDs must be unique")
    require(selection["returned_count"] == len(flights), "returned_count differs from array length")
    require(selection["eligible_count"] >= len(flights), "returned count exceeds eligible count")
    require(selection["eligible_count"] <= body["diagnostics"]["input_aircraft_count"],
            "eligible count exceeds input count")
    require(selection["truncated"] == (selection["returned_count"] < selection["eligible_count"]),
            "truncation flag differs from counts")
    require(selection["eligible_count"] == 0 or len(flights) > 0,
            "eligible input must retain at least one bounded candidate")
    if selection["truncated"]:
        count_limited = selection["eligible_count"] > 8
        require(count_limited == (selection["truncation_reason"] in
                                  ("count_limit", "count_and_byte_limit")),
                "count-limit reason differs from eligible count")
    addresses = [flight["adsb_icao"] for flight in flights]
    require(len(addresses) == len(set(addresses)), "candidate addresses must be unique")
    order = [(flight["position"]["distance_km"], flight["adsb_icao"]) for flight in flights]
    require(order == sorted(order), "candidates must sort by emitted distance then hex")
    require(nesting(body) <= 16, "body exceeds draft nesting depth")
    trusted = body["receiver"]["clock_confidence"] == "trusted_utc"
    if not trusted:
        require(body["generated_at"] is None, "untrusted UTC must not have generated_at")
        require(all(row["age_seconds"] is None for row in source_rows),
                "untrusted UTC must not have dataset wall-clock ages")

    def source_exists(source_id, label):
        require(source_id in sources, f"{label}: unresolved source ID {source_id}")

    for flight in flights:
        label = flight["adsb_icao"]
        aircraft = flight["aircraft"]
        for field, source_id in aircraft["sources"].items():
            require((aircraft[field] is None) == (source_id is None),
                    f"{label}: {field} value/source nulls disagree")
            if source_id is not None:
                source_exists(source_id, label)
        operator = flight["operator"]
        if operator["source_id"] is not None:
            source_exists(operator["source_id"], label)
        if operator["match_kind"] == "dated_override":
            require(trusted, f"{label}: dated operator needs trusted UTC")
        logo = flight["logo"]
        if logo is not None:
            source_exists(logo["source_id"], label)
            require(logo["operator_id"] == operator["id"], f"{label}: logo/operator mismatch")
            require(logo["path"] == f"/assets/logos/{logo['sha256']}.rgb565",
                    f"{label}: logo path/hash mismatch")
            if logo["source_id"] in sources:
                require(sources[logo["source_id"]]["kind"] == "logo_manifest",
                        f"{label}: logo source is not a manifest")
        for route_key in ("route_reference", "route_override"):
            route = flight[route_key]
            if route is None:
                continue
            source_exists(route["source_id"], label)
            require(route["matched_callsign"] == flight["callsign_normalized"],
                    f"{label}: route callsign mismatch")
            codes = route["airport_codes"]
            if codes is not None:
                require(len(codes) == route["stop_count"], f"{label}: route stop count mismatch")
                if route["stop_count"] == 2:
                    require(route["departure_airport"] == codes[0] and
                            route["destination_airport"] == codes[1],
                            f"{label}: route endpoints differ from ordered sequence")
            if route_key == "route_reference":
                require(route["geography_check"] != "rejected",
                        f"{label}: rejected reference must not be returned as a match")
            else:
                require(trusted, f"{label}: dated route needs trusted UTC")
                require(route["aircraft_hex"] in (None, label), f"{label}: override hex mismatch")
                start, end = instant(route["valid_from"]), instant(route["valid_until"])
                require(0 < (end - start).total_seconds() <= 86400,
                        f"{label}: override window is invalid")
                if body["generated_at"] is not None:
                    generated = instant(body["generated_at"])
                    require(start <= generated < end, f"{label}: override is outside date window")
                    require(route["flight_date"] == generated.date().isoformat(),
                            f"{label}: override flight date differs from UTC date")
                    remaining = math.floor((end - generated).total_seconds() * 1000)
                    require(route["remaining_validity_ms"] <= remaining,
                            f"{label}: override remaining validity extends past evidence")
        expected_preferred = ("route_override" if flight["route_override"] is not None else
                              "route_reference" if flight["route_reference"] is not None else None)
        require(flight["preferred_route"] == expected_preferred, f"{label}: preferred route mismatch")
        expected_reason = {"route_override": "dated_override_match", "route_reference": "reference_match"}
        if expected_preferred is not None:
            require(flight["route_reason"] == expected_reason[expected_preferred],
                    f"{label}: route reason differs from selected match")
        if not trusted:
            require(flight["last_seen_at"] is None and flight["position_seen_at"] is None,
                    f"{label}: untrusted UTC must not have aircraft timestamps")
        for field in ("observed_departure_airport", "observed_arrival_airport"):
            require(flight[field] is None, f"{label}: observed events remain reserved until M8")
    return errors


def check_timing(case):
    elapsed = (case["use_tick_ms"] - case["request_tick_ms"]) % TICK_MODULUS
    ages = case["ages_ms"]
    live = (not case["boot_changed"] and elapsed < TICK_MODULUS // 2 and
            ages["snapshot"] + elapsed < 5000 and ages["progress"] + elapsed < 5000 and
            ages["message"] + elapsed < 15000 and ages["position"] + elapsed < 15000)
    previous = case["previous_snapshot_deadline_tick_ms"]
    if previous is not None:
        until_previous = (previous - case["use_tick_ms"]) % TICK_MODULUS
        live = live and 0 < until_previous < TICK_MODULUS // 2
    remaining = case["override_remaining_ms"]
    override_active = live and remaining is not None and elapsed < remaining
    return (elapsed == case["expected_elapsed_ms"] and live == case["expected_live"] and
            override_active == case["expected_override_active"])


def main():
    schemas = {kind: read_json(API / name) for kind, name in SCHEMAS.items()}
    registry = Registry()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    validators = {kind: Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
                  for kind, schema in schemas.items()}
    failures = []
    sizes = []
    cases = read_json(FIXTURES / "cases.json")["cases"]
    for case in cases:
        body = read_json(FIXTURES / case["file"])
        errors = list(validators[case["contract"]].iter_errors(body))
        category = "schema" if errors else None
        details = [f"{list(error.absolute_path)}: {error.message}" for error in errors[:3]]
        if category is None and case["contract"] == "flights":
            size = body_bytes(body)
            if size > BODY_LIMIT:
                category, details = "bytes", [f"body is {size} bytes"]
            else:
                details = flight_relationships(body)
                if details:
                    category = "semantics"
                elif case["expected_valid"]:
                    sizes.append((size, case["name"]))
        expected = None if case["expected_valid"] else case["expected_failure"]
        if category != expected:
            failures.append(f"{case['name']}: expected {expected or 'valid'}, got {category or 'valid'}; "
                            + "; ".join(details))
    timing = read_json(FIXTURES / "timing-cases.json")["cases"]
    for case in timing:
        if not check_timing(case):
            failures.append(f"{case['name']}: timing arithmetic differs from documented expectation")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    valid_count = sum(case["expected_valid"] for case in cases)
    print(f"3 schemas valid; {len(cases)} examples match expectations "
          f"({valid_count} valid, {len(cases) - valid_count} intentionally invalid); "
          f"{len(timing)} timing examples consistent.")
    largest, name = max(sizes)
    print(f"Largest accepted compact UTF-8 flight example: {largest} bytes ({name}).")
    print("Documentation checks only; no receiver reader, HTTP server, firmware parser or hardware exercised.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
