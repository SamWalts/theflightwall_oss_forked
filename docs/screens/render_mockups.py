#!/usr/bin/env python3
"""Export deterministic 160x32 FlightWall design mockups (Pillow required)."""

import argparse
import copy
import hashlib
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 160, 32
COLORS = {
    "black": "#000000", "white": "#eaf4ff", "cyan": "#54d9fa",
    "amber": "#ffbf69", "muted": "#91a5b9", "border": "#334351",
    "red": "#e53848", "dark_red": "#941f34", "blue": "#2876ee",
    "yellow": "#ffd347", "navy": "#1f52b8"
}

# Five columns, seven rows; all visible display type uses whole LED pixels.
# Glyphs are original patterns, not a downloaded font or an antialiased overlay.
GLYPH_ROWS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    " ": ["00000"] * 7,
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ">": ["10000", "01000", "00100", "00010", "00100", "01000", "10000"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00110", "00110"],
    ":": ["00000", "00110", "00110", "00000", "00110", "00110", "00000"],
    "/": ["00001", "00001", "00010", "00100", "01000", "10000", "10000"]
}

PAGE_INFO = {
    "overview": ("F01", "Flight overview", "Default: callsign and type, barometric altitude, ground speed."),
    "motion": ("F02", "Motion details", "Barometric VS or geometric GVS; decoded IAS or TAS keeps its own label."),
    "identity": ("F03", "Airline and airframe", "Resolved reference airline, canonical identifier, aircraft type and registration."),
    "route": ("F04", "Airport route", "Optional local route; its source stays visible."),
    "cities": ("F05", "From / to airports", "Airport display codes with reference/dated provenance; no invented city names.")
}
STATE_NOTES = {
    "boot": "Before a usable feed is available. Do not imply that an empty receiver is still loading.",
    "setup": "Provisioning concept: Wi-Fi and Pi address/port. BLE implementation remains separate work.",
    "wifi": "ESP32 disconnected from Wi-Fi. Replace the flight card and retry using bounded backoff.",
    "pi": "Wi-Fi is connected, but the configured Pi service cannot be reached or its response is unusable.",
    "receiver": "Pi is reachable, but the receiver snapshot or source progress is stale. Clear previous flight data.",
    "empty": "Fresh, configured receiver with zero eligible nearby aircraft. This is a normal state.",
    "initializing": "Receiver startup, awaiting progress, or clock recovery. Clear flights until source progress is established.",
    "unavailable": "Pi reachable, but receiver input is missing or unreadable. Clear flight details.",
    "invalid": "Pi reachable, but receiver JSON/time/size/row bounds are invalid. Clear flight details.",
    "config": "Receiver ready, but viewing coordinates/filters are unconfigured. This is not an empty sky.",
    "expired": "Receiver still fresh, but all retained aircraft have expired. Await a new live candidate."
}


def text_width(value):
    return max(0, len(value) * 6 - 1)


def fit(value, columns=20):
    text = str(value or "").upper()
    # Normalize to the display's deliberately limited character set.
    text = "".join(c if c in GLYPH_ROWS else "?" for c in text)
    return text if len(text) <= columns else text[:columns - 3] + "..."


def draw_text(image, value, x, y, color, columns=20):
    value = fit(value, columns)
    for n, character in enumerate(value):
        for row, pattern in enumerate(GLYPH_ROWS[character]):
            for column, bit in enumerate(pattern):
                if bit == "1":
                    px, py = x + n * 6 + column, y + row
                    if not (0 <= px < image.width and 0 <= py < image.height):
                        raise ValueError(f"Text out of bounds: {value!r} at {px},{py}")
                    image.putpixel((px, py), ImageColor(color))
    return value


def ImageColor(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def airline_logo(operator):
    """Original low-resolution interpretations for design review, on black."""
    logo = Image.new("RGB", (24, 24), COLORS["black"])
    d = ImageDraw.Draw(logo)
    if operator == "DAL":
        d.polygon([(12, 2), (2, 19), (12, 15)], fill=COLORS["red"])
        d.polygon([(12, 2), (22, 19), (12, 15)], fill=COLORS["dark_red"])
        d.polygon([(2, 21), (12, 17), (22, 21)], fill=COLORS["red"])
    elif operator == "UAL":
        d.ellipse((1, 1, 22, 22), outline=COLORS["cyan"], width=1)
        d.ellipse((5, 1, 18, 22), outline=COLORS["blue"], width=1)
        d.ellipse((9, 1, 14, 22), outline=COLORS["cyan"], width=1)
        for y, left, right in [(5, 4, 19), (9, 2, 21), (13, 2, 21), (17, 3, 20)]:
            d.line((left, y, right, y), fill=COLORS["cyan"])
    elif operator == "SWA":
        mask = Image.new("1", (24, 24))
        m = ImageDraw.Draw(mask)
        m.polygon([(12, 6), (9, 3), (5, 3), (2, 6), (2, 11), (12, 22),
                   (22, 11), (22, 6), (19, 3), (15, 3)], fill=1)
        for y in range(24):
            for x in range(24):
                if mask.getpixel((x, y)):
                    color = COLORS["blue"] if x < 9 else COLORS["red"] if x < 16 else COLORS["yellow"]
                    logo.putpixel((x, y), ImageColor(color))
        m_points = [(12, 6), (9, 3), (5, 3), (2, 6), (2, 11), (12, 22),
                    (22, 11), (22, 6), (19, 3), (15, 3), (12, 6)]
        d.line(m_points, fill=COLORS["yellow"], width=1)
    else:
        d.rectangle((1, 3, 22, 20), outline=COLORS["muted"])
        badge = fit(operator or "AIR", 3)
        draw_text(logo, badge, (24 - text_width(badge)) // 2, 8, COLORS["muted"], 3)
    return logo


def status_icon(name, accent):
    icon = Image.new("RGB", (24, 24), COLORS["black"])
    d = ImageDraw.Draw(icon)
    if name == "bluetooth":
        d.line([(11, 2), (11, 21), (18, 15), (5, 5)], fill=accent, width=2)
        d.line([(11, 2), (18, 8), (5, 18)], fill=accent, width=2)
    elif name == "wifi":
        for bounds in [(1, 3, 22, 23), (5, 7, 18, 21), (9, 11, 14, 18)]:
            d.arc(bounds, 220, 320, fill=accent, width=2)
        d.rectangle((11, 18, 12, 19), fill=accent)
        d.line((3, 22, 22, 3), fill=accent, width=1)
    elif name == "server":
        for y in (3, 11):
            d.rectangle((2, y, 21, y + 7), outline=accent)
            d.point((5, y + 3), fill=accent)
            d.line((10, y + 3, 18, y + 3), fill=accent)
    elif name == "warning":
        d.polygon([(12, 2), (1, 21), (22, 21)], outline=accent)
        d.rectangle((11, 8, 12, 14), fill=accent)
        d.rectangle((11, 17, 12, 18), fill=accent)
    elif name == "radar":
        d.ellipse((1, 1, 22, 22), outline=accent)
        d.ellipse((6, 6, 17, 17), outline=COLORS["border"])
        d.line((12, 12, 19, 4), fill=accent)
        d.line((12, 1, 12, 22), fill=COLORS["border"])
        d.line((1, 12, 22, 12), fill=COLORS["border"])
        d.point((12, 12), fill=accent)
    else:
        d.polygon([(12, 2), (14, 9), (22, 14), (22, 16), (14, 13),
                   (14, 19), (17, 21), (17, 22), (12, 20), (7, 22),
                   (7, 21), (10, 19), (10, 13), (2, 16), (2, 14), (10, 9)], fill=accent)
    return icon


def metric(label, value, unit, signed=False):
    # Zero is a received value; only None is unknown.
    if value is None:
        return f"{label} --{unit}"
    number = round(value)
    token = f"{number:+d}" if signed and number != 0 else str(number)
    return f"{label} {token}{unit}"


def identifier(flight):
    return flight.get("display_identifier") or (flight.get("callsign") or "").strip() or flight["hex"]


def header(flight):
    return fit(identifier(flight), 14) + " " + fit(flight.get("aircraft_type") or "--", 4)


def route_label(flight):
    if flight.get("route_status"):
        return flight["route_status"]
    origin, destination = flight.get("origin"), flight.get("destination")
    sources = {a.get("source", "unknown") for a in (origin, destination) if a}
    if "inferred" in sources:
        return "INFERRED ROUTE" if origin and destination else "INFERRED FROM" if origin else "INFERRED TO"
    if sources == {"reference"}:
        return "REFERENCE ROUTE"
    if sources == {"dated_override"}:
        return "DATED ROUTE"
    if sources == {"manual"}:
        return "MANUAL ROUTE" if origin and destination else "MANUAL FROM" if origin else "MANUAL TO"
    if sources == {"observed"}:
        return "OBSERVED ROUTE" if origin and destination else "OBSERVED FROM" if origin else "OBSERVED TO"
    return "MIXED SOURCES" if origin and destination else "ROUTE UNKNOWN"


def airport_token(airport):
    if not airport:
        return "----"
    return fit(airport.get("code") or airport.get("icao") or "----", 4) + ("?" if airport.get("source") == "inferred" else "")


def sourced_endpoint(endpoint):
    return bool(endpoint and (endpoint.get("code") or endpoint.get("icao")) and endpoint.get("source") in {"manual", "observed", "inferred", "reference", "dated_override"})


def canonical_view(flight, elapsed_ms=0):
    """Project a validated v2 candidate; elapsed is from its original request start.

    Used after receiver/candidate expiry checks in canonical_display. No HTTP,
    firmware cache, asset validation, or invented city/observed-event data.
    """
    if elapsed_ms < 0:
        raise ValueError("Elapsed request time cannot be negative")
    telemetry, aircraft, operator = flight["telemetry"], flight["aircraft"], flight["operator"]
    operator_active = operator["valid_for_ms"] is None or operator["valid_for_ms"] > elapsed_ms
    logo = flight["logo"] if operator_active else None
    if logo and logo["operator_id"] != operator["id"]:
        logo = None
    view = {
        "hex": flight["adsb_icao"], "callsign": (flight["callsign_received"] or "").strip() or None,
        "display_identifier": flight["display_identifier"],
        "registration": aircraft["registration"], "aircraft_type": aircraft["icao_type_designator"],
        "aircraft_model": aircraft["model"], "operator_icao": operator["icao"] if operator_active else None,
        "airline_short": operator["name"] if operator_active else None, "logo": logo,
        "altitude_baro_ft": "ground" if telemetry["ground_state"] == "ground" else telemetry["altitude_baro_ft"],
        "ground_speed_kt": telemetry["ground_speed_kt"],
        "vertical_rate_baro_fpm": telemetry["vertical_speed_fpm"] if telemetry["vertical_speed_source"] == "barometric" else None,
        "vertical_rate_geom_fpm": telemetry["vertical_speed_fpm"] if telemetry["vertical_speed_source"] == "geometric" else None,
        "indicated_airspeed_kt": telemetry["airspeed_ias_kt"], "true_airspeed_kt": telemetry["airspeed_tas_kt"],
        "distance_km": flight["position"]["distance_km"], "ground_track_deg": telemetry["ground_track_deg"],
        "origin": None, "destination": None,
    }
    preferred = flight["preferred_route"]
    route = flight.get(preferred) if preferred in {"route_reference", "route_override"} else None
    if route and preferred == "route_override" and route["remaining_validity_ms"] <= elapsed_ms:
        preferred, route = "route_reference", flight["route_reference"]
    if route:
        if route["current_leg_ambiguous"]:
            view["route_status"] = "MULTI-STOP ROUTE"
            return view
        source = "reference" if preferred == "route_reference" else "dated_override"
        for target, field in (("origin", "departure"), ("destination", "destination")):
            code = route[field + "_airport"]
            if code:
                view[target] = {"code": code, "display_code": route[field + "_display_code"] or code, "source": source}
        view["route_status"] = "REFERENCE ROUTE" if source == "reference" else "VERIFIED ROUTE" if route["flight_instance_verified"] else "DATED ROUTE"
    return view


def canonical_display(envelope, elapsed_ms=0, *, setup_active=False, wifi_connected=True, pi_available=True):
    """Map a validated v2 envelope to a state or still-live views for design review.

    The consumer retains the original request-start baseline for repeated
    instance/sequence responses. This helper does not implement that cache.
    """
    if elapsed_ms < 0:
        raise ValueError("Elapsed request time cannot be negative")
    def state(key):
        return {"state": key, "flights": []}
    if setup_active:
        return state("setup")
    if not wifi_connected:
        return state("wifi")
    if not pi_available or envelope is None or envelope.get("schema_version") != 2:
        return state("pi")
    receiver = envelope["receiver"]
    states = {"initializing": "initializing", "stale": "receiver", "unavailable": "unavailable", "invalid": "invalid"}
    if receiver["status"] in states:
        return state(states[receiver["status"]])
    if receiver["status"] != "ready":
        return state("pi")
    if receiver["clock_confidence"] == "uncertain":
        return state("initializing")
    for field in ("snapshot_age_ms", "progress_age_ms"):
        age = receiver[field]
        if age is None or age + elapsed_ms >= 5000:
            return state("receiver")
    if envelope["selection"]["status"] == "unconfigured":
        return state("config")
    if not envelope["flights"]:
        return state("empty")
    live = [row for row in envelope["flights"]
            if row["last_seen_age_ms"] + elapsed_ms < 15000
            and row["position_seen_age_ms"] + elapsed_ms < 15000]
    if not live:
        return state("expired")
    return {"state": None, "flights": [canonical_view(row, elapsed_ms) for row in live]}


def departure_fallback(flight, mode="telemetry", keep_destination=True):
    """Design selection rule for a requested route page; not live firmware logic."""
    choices = {"telemetry": "overview", "identity": "airframe", "nearby": "nearby", "explicit": "departure-unknown"}
    if mode not in choices:
        raise ValueError(f"Unknown departure fallback option: {mode}")
    if sourced_endpoint(flight.get("origin")):
        return "route"
    if keep_destination and sourced_endpoint(flight.get("destination")):
        return "destination-only"
    if mode == "nearby" and flight.get("distance_km") is None and flight.get("ground_track_deg") is None:
        return "overview"
    if mode == "identity" and not any(flight.get(field) for field in ("registration", "aircraft_model", "aircraft_type")):
        return "overview"
    return choices[mode]


def flight_lines(flight, page):
    if page == "overview":
        altitude = flight.get("altitude_baro_ft")
        return [header(flight), "ALT GROUND" if altitude == "ground" else metric("ALT", altitude, "FT"),
                metric("GS", flight.get("ground_speed_kt"), "KT")]
    if page == "motion":
        ias, tas = flight.get("indicated_airspeed_kt"), flight.get("true_airspeed_kt")
        airspeed = metric("IAS", ias, "KT") if ias is not None or tas is None else metric("TAS", tas, "KT")
        rate = metric("VS", flight.get("vertical_rate_baro_fpm"), "FT/M", signed=True)
        if flight.get("vertical_rate_baro_fpm") is None and flight.get("vertical_rate_geom_fpm") is not None:
            rate = metric("GVS", flight["vertical_rate_geom_fpm"], "FT/M", signed=True)
        return [header(flight), rate, airspeed]
    if page == "identity":
        detail = (flight.get("aircraft_type") or "TYPE --") + " " + (flight.get("registration") or "REG --")
        if len(detail) > 20:
            detail = "REG " + flight["registration"]
        return [flight.get("airline_short") or flight.get("operator_icao") or "UNKNOWN OPERATOR",
                identifier(flight), detail]
    if page == "route":
        return [header(flight), airport_token(flight.get("origin")) + ">" + airport_token(flight.get("destination")), route_label(flight)]
    if page == "cities":
        origin, destination = flight.get("origin"), flight.get("destination")
        def city(airport):
            return ((airport.get("display_code") or airport.get("code") or airport.get("icao") or "--") +
                    ("?" if airport.get("source") == "inferred" else "")) if airport else "--"
        return ["FROM " + city(origin), "TO " + city(destination), route_label(flight)]
    if page == "airframe":
        return [flight.get("registration") or identifier(flight), flight.get("aircraft_model") or flight.get("aircraft_type") or "TYPE --", "HEX " + flight["hex"]]
    if page == "nearby":
        distance, track = flight.get("distance_km"), flight.get("ground_track_deg")
        return [header(flight), "DIST --KM" if distance is None else f"DIST {distance:.1f}KM",
                "TRK --DEG" if track is None else f"TRK {round(track) % 360:03d}DEG"]
    if page == "departure-unknown":
        return [header(flight), "FROM UNKNOWN", "ALT GROUND" if flight.get("altitude_baro_ft") == "ground" else metric("ALT", flight.get("altitude_baro_ft"), "FT")]
    if page == "destination-only":
        destination = flight.get("destination") if sourced_endpoint(flight.get("destination")) else None
        token = airport_token(destination) if destination else "--"
        source = route_label({"origin": None, "destination": destination})
        return [header(flight), "FROM -- TO " + token, source]
    raise ValueError(f"Unknown page: {page}")


def render(lines, logo, accents):
    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["black"])
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, 159, 31), outline=COLORS["border"])
    d.line((32, 3, 32, 28), fill=COLORS["border"])
    image.paste(logo, (4, 4))
    visible = [draw_text(image, line, 37, y, COLORS[color]) for line, y, color in zip(lines, (3, 12, 21), accents)]
    return image, visible


def led_view(native, scale=8):
    image = Image.new("RGB", (native.width * scale, native.height * scale), "#080c12")
    d = ImageDraw.Draw(image)
    for y in range(native.height):
        for x in range(native.width):
            color = native.getpixel((x, y))
            d.ellipse((x * scale + 1, y * scale + 1, x * scale + scale - 2, y * scale + scale - 2),
                      fill=color if color != (0, 0, 0) else "#111820")
    return image


def svg_image(native, label):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="256" viewBox="0 0 160 32" shape-rendering="crispEdges" role="img">',
             f'<title>{html.escape(label)}</title>', '<rect width="160" height="32" fill="#000000"/>']
    # Export filled rectangles, never SVG font glyphs.
    for y in range(native.height):
        x = 0
        while x < native.width:
            color = native.getpixel((x, y))
            end = x + 1
            while end < native.width and native.getpixel((end, y)) == color:
                end += 1
            if color != (0, 0, 0):
                token = "#" + "".join(f"{c:02x}" for c in color)
                parts.append(f'<rect x="{x}" y="{y}" width="{end - x}" height="1" fill="{token}"/>')
            x = end
    return "\n".join(parts + ["</svg>", ""])


def font(size, bold=False):
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(filename, size)


def contact_sheet(scenes, title, subtitle, columns=2):
    margin, gap, card_w, card_h = 48, 24, 664, 224
    width = margin * 2 + card_w * columns + gap * (columns - 1)
    rows = (len(scenes) + columns - 1) // columns
    image = Image.new("RGB", (width, 196 + rows * (card_h + gap) + 40), "#0b1018")
    d = ImageDraw.Draw(image)
    d.text((margin, 34), "THE FLIGHT WALL   /   SCREEN STUDY 01", font=font(15, True), fill="#58d8ee")
    d.text((margin, 67), title, font=font(36, True), fill="#f0f4fa")
    d.text((margin, 123), subtitle, font=font(17), fill="#a0aec0")
    d.text((margin, 153), "160 x 32 LEDs  /  Synthetic flight data  /  Pixel artwork for review", font=font(14), fill="#73869b")
    for i, scene in enumerate(scenes):
        x = margin + (i % columns) * (card_w + gap)
        y = 196 + (i // columns) * (card_h + gap)
        d.rounded_rectangle((x, y, x + card_w, y + card_h), radius=12, fill="#111a26", outline="#283443")
        d.text((x + 16, y + 13), scene["code"], font=font(13, True), fill="#58d8ee")
        d.text((x + 67, y + 10), scene["title"], font=font(18, True), fill="#f0f4fa")
        image.paste(led_view(scene["image"], 4), (x + 12, y + 48))
        d.text((x + 16, y + 191), scene["caption"], font=font(13), fill="#a0aec0")
    return image


def serialize_image(native):
    palette = ["#000000"]
    indices = {"#000000": 0}
    pixels = []
    for y in range(native.height):
        row = []
        for x in range(native.width):
            token = "#" + "".join(f"{c:02x}" for c in native.getpixel((x, y)))
            if token not in indices:
                indices[token] = len(palette)
                palette.append(token)
            row.append(indices[token])
        pixels.append(row)
    return {"palette": palette, "pixels": pixels}


def build_scenes(fixtures):
    scenes = []
    for key in ("delta", "united", "southwest"):
        for page, (code, title, note) in PAGE_INFO.items():
            f = fixtures["flights"][key]
            colors = ["white", "cyan", "cyan"]
            if page in ("route", "cities"):
                colors[2] = "amber"
            if page == "identity":
                colors[1] = "cyan"
                colors[2] = "muted"
            native, lines = render(flight_lines(f, page), airline_logo(f["operator_icao"]), colors)
            scenes.append({"id": f"{page}-{key}", "code": code, "title": title,
                           "group": "flight", "airline": key, "page": page, "lines": lines,
                           "note": note, "caption": "Reference route / not dated verification" if page in ("route", "cities") else f["callsign"] + " / " + f["aircraft_type"],
                           "image": native})
    cases = [
        ("partial", "overview", "C01", "Unknown airline / partial data", "Neutral AIR badge; an unrecognized callsign prefix does not resolve an airline."),
        ("anonymous", "overview", "C02", "No callsign / zero speed", "Hex identity is usable; received zero is displayed as zero."),
        ("ground", "overview", "C03", "Aircraft on the ground", "Ground is a state, never coerced into an altitude of zero."),
        ("no_route", "route", "C04", "Route unavailable", "Ordinary ADS-B does not include the itinerary. Do not invent it."),
        ("inferred_route", "route", "C05", "Departure inferred", "Deferred future concept: no inferred-departure field exists in M1; excluded from canonical projection."),
        ("no_route", "motion", "C06", "Airspeed / vertical rate absent", "GS is not substituted for IAS/TAS; missing readings remain unknown.")
    ]
    for key, page, code, title, note in cases:
        f = fixtures["flights"][key]
        colors = ["white", "amber" if key == "inferred_route" else "cyan", "amber" if page == "route" else "cyan"]
        native, lines = render(flight_lines(f, page), airline_logo(f.get("operator_icao")), colors)
        scenes.append({"id": f"case-{key}", "code": code, "title": title, "group": "case", "airline": "delta" if key in ("ground", "no_route", "inferred_route") else None,
                       "deferred": bool(f.get("deferred")), "page": page, "lines": lines, "note": note, "caption": "Unknown values stay explicit" if key != "ground" else "ALT GROUND / GS 0KT", "image": native})
    # The same no-route flight appears in two distinct cases; include the page in its ID.
    scenes[-1]["id"] = "case-missing-motion"
    departure_options = [
        ("no-departure-telemetry", "private_piston", "overview", "N01", "Aircraft + telemetry", "Recommended default: registration/type, altitude, and ground speed replace an unavailable route.", "Light aircraft / no route required"),
        ("no-departure-airframe", "private_piston", "airframe", "N02", "Registration + model", "Optional identity page: show the registration and locally known aircraft model, without naming an airline or guessing an airport.", "N123AB / Cessna 172"),
        ("no-departure-nearby", "private_piston", "nearby", "N03", "Nearby distance + track", "Optional position page: horizontal distance from the confirmed receiver/home location and decoded ground track. Neither identifies departure.", "Fresh position / local telemetry"),
        ("no-departure-explicit", "private_piston", "departure-unknown", "N04", "Departure unavailable", "Optional explicit treatment: FROM UNKNOWN with the aircraft identity and useful altitude, instead of an empty airport route.", "Missing departure is a normal flight state"),
        ("no-departure-business-jet", "private_jet", "overview", "N01", "Business jet + telemetry", "The same recommended layout works for a private jet. Use a neutral aircraft icon when no operating airline is known.", "N456CJ / Citation CJ3"),
        ("no-departure-destination", "destination_only", "destination-only", "N05", "Known destination only", "Deferred future concept: M1 has no independently planned destination field. Never map this to an observed arrival.", "Unknown departure / manually supplied destination"),
        ("no-departure-unidentified", "unidentified_overhead", "overview", "N01", "Unidentified aircraft", "A received hex address and telemetry remain useful when callsign, registration, type, operator, and departure are all unknown.", "HEX AD56EF / no guessed identity")
    ]
    for scene_id, key, page, code, title, note, caption in departure_options:
        f = fixtures["flights"][key]
        emblem = airline_logo(f["operator_icao"]) if f.get("operator_icao") else status_icon("plane", COLORS["muted"])
        colors = ["white", "muted" if page == "departure-unknown" else "cyan", "amber" if page == "destination-only" else "muted" if page == "airframe" else "cyan"]
        native, lines = render(flight_lines(f, page), emblem, colors)
        scenes.append({"id": scene_id, "code": code, "title": title, "group": "departure", "airline": "united" if key == "destination_only" else None,
                       "deferred": bool(f.get("deferred")), "page": page, "lines": lines, "note": note, "caption": caption, "image": native})
    for i, (key, state) in enumerate(fixtures["states"].items(), 1):
        native, lines = render(state["lines"], status_icon(state["icon"], COLORS[state["accent"]]), [state["accent"], "white", "muted"])
        scenes.append({"id": f"state-{key}", "code": f"S{i:02}", "title": state["title"].title(), "group": "state", "airline": None,
                       "page": key, "lines": lines, "note": STATE_NOTES[key], "caption": "Status replaces stale flight data", "image": native})
    for scene in scenes:
        if scene.get("deferred"):
            scene["caption"] = "Future concept / excluded from M1"
            scene["title"] += " (future)"
    return scenes


def validate(fixtures, scenes):
    ids = [s["id"] for s in scenes]
    assert len(ids) == len(set(ids)), "Scene IDs must be unique"
    for scene in scenes:
        assert scene["image"].size == (WIDTH, HEIGHT)
        assert len(scene["lines"]) == 3
        assert all(text_width(line) <= 119 for line in scene["lines"])
        assert all(c in GLYPH_ROWS for line in scene["lines"] for c in line)
    f = copy.deepcopy(fixtures["flights"]["delta"])
    f["ground_speed_kt"] = 0
    assert flight_lines(f, "overview")[2] == "GS 0KT"
    f["ground_speed_kt"] = None
    assert flight_lines(f, "overview")[2] == "GS --KT"
    f["indicated_airspeed_kt"], f["true_airspeed_kt"] = None, 470
    assert flight_lines(f, "motion")[2] == "TAS 470KT"
    f["true_airspeed_kt"] = None
    assert flight_lines(f, "motion")[2] == "IAS --KT"
    f["indicated_airspeed_kt"] = 0
    assert flight_lines(f, "motion")[2] == "IAS 0KT"
    f["altitude_baro_ft"] = "ground"
    assert flight_lines(f, "overview")[1] == "ALT GROUND"
    f["callsign"], f["registration"] = None, None
    assert identifier(f) == "A4B5C6"
    assert "?" in flight_lines(fixtures["flights"]["inferred_route"], "route")[1]
    assert "--" in flight_lines(fixtures["flights"]["no_route"], "route")[1]
    # Exercise signed telemetry and long labels without relying on only the examples.
    for value, expected in [(-1500, "VS -1500FT/M"), (0, "VS 0FT/M"), (1200, "VS +1200FT/M")]:
        assert metric("VS", value, "FT/M", True) == expected
    assert fit("A VERY LONG AIRLINE NAME") == "A VERY LONG AIRLI..."
    private = fixtures["flights"]["private_piston"]
    assert identifier(private) == "AB12CD"
    assert departure_fallback(private) == "overview"
    assert departure_fallback(private, "identity") == "airframe"
    assert departure_fallback(private, "nearby") == "nearby"
    assert departure_fallback(private, "explicit") == "departure-unknown"
    assert flight_lines(private, "nearby") == ["AB12CD C172", "DIST 1.8KM", "TRK 090DEG"]
    unknown = fixtures["flights"]["unidentified_overhead"]
    assert departure_fallback(unknown, "nearby") == "overview"
    assert departure_fallback(unknown, "identity") == "overview"
    assert flight_lines(unknown, "nearby")[1:] == ["DIST --KM", "TRK --DEG"]
    positioned = copy.deepcopy(private)
    positioned["distance_km"], positioned["ground_track_deg"] = 0, 0
    assert flight_lines(positioned, "nearby")[1:] == ["DIST 0.0KM", "TRK 000DEG"]
    assert departure_fallback(fixtures["flights"]["delta"]) == "route"
    assert departure_fallback(fixtures["flights"]["destination_only"]) == "destination-only"
    assert departure_fallback(fixtures["flights"]["destination_only"], keep_destination=False) == "overview"
    unverified = copy.deepcopy(fixtures["flights"]["destination_only"])
    unverified["destination"]["source"] = "unknown"
    assert departure_fallback(unverified) == "overview"
    assert "EGLL" not in " ".join(flight_lines(unverified, "destination-only"))
    for scene in scenes:
        if scene["group"] == "departure" and scene["id"] != "no-departure-destination":
            assert not any(word in " ".join(scene["lines"]) for word in ("KATL", "EGLL", "PRIVATE", "UNKNOWN OPERATOR"))
    print(f"Validated {len(scenes)} native 160x32 screens, text bounds, fallback values, route provenance, and units.")


def export(scenes):
    exports, assets = ROOT / "mockups", ROOT / "assets"
    exports.mkdir(exist_ok=True)
    assets.mkdir(exist_ok=True)
    serialized = []
    for scene in scenes:
        native = scene["image"]
        native.save(exports / (scene["id"] + "-native.png"))
        led_view(native).save(exports / (scene["id"] + ".png"))
        (exports / (scene["id"] + ".svg")).write_text(svg_image(native, scene["title"] + ": " + " / ".join(scene["lines"])))
        entry = {key: value for key, value in scene.items() if key != "image"}
        entry.update(serialize_image(native))
        serialized.append(entry)
    # Only one representative airline per page on the overview; all airline variants remain in the gallery.
    design_scenes = [next(s for s in scenes if s["id"] == f"{page}-delta") for page in PAGE_INFO]
    case_scenes = [s for s in scenes if s["group"] == "case"]
    departure_scenes = [s for s in scenes if s["group"] == "departure"]
    state_scenes = [s for s in scenes if s["group"] == "state"]
    sheets = [
        contact_sheet(design_scenes, "Flight screens", "A logo stays anchored at left. Three lines carry one clear idea."),
        contact_sheet(departure_scenes, "When departure is unknown", "Useful options for private, unidentified, and route-incomplete flights."),
        contact_sheet(case_scenes, "Partial data & honest fallbacks", "A useful aircraft remains visible when enrichment or routes are missing."),
        contact_sheet(state_scenes, "System states", "Distinct setup, connection, receiver, and quiet-sky messages."),
        contact_sheet([s for s in scenes if s["page"] == "overview" and s["group"] == "flight"],
                      "Airline logo study", "Delta widget, United globe, and Southwest heart: 24 x 24 pixel interpretations.")
    ]
    for name, sheet in zip(("flight-screens", "no-departure-options", "data-fallbacks", "system-states", "airline-logos"), sheets):
        sheet.save(exports / (name + ".png"))
    sheets[0].save(ROOT / "flightwall-screen-review.pdf", "PDF", resolution=144, save_all=True, append_images=sheets[1:])
    manifest = {"purpose": "Design-review pixel interpretations only; production asset approval is not established.", "assets": []}
    for code, name, url in [("DAL", "Delta widget", "https://www.delta.com/"),
                            ("UAL", "United globe", "https://www.united.com/"),
                            ("SWA", "Southwest heart", "https://www.southwest.com/")]:
        path = assets / (code.lower() + "-24.png")
        airline_logo(code).save(path)
        manifest["assets"].append({"operator_icao": code, "name": name, "file": path.name,
                                   "width": 24, "height": 24, "format": "RGB PNG", "background": "black",
                                   "reference_url": url, "source": "Original hand-drawn pixel interpretation in render_mockups.py",
                                   "source_license": None, "attribution": "Brand identity belongs to the named airline.",
                                   "production_approved": False, "version": "review-1", "date": "2026-10-03",
                                   "modifications": "Simplified to a 24x24 emblem for legibility on the LED wall.",
                                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (assets / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "screens.json").write_text(json.dumps(serialized, separators=(",", ":")) + "\n")
    template = (ROOT / "review-template.html").read_text()
    payload = json.dumps(serialized, separators=(",", ":")).replace("<", "\\u003c")
    (ROOT / "review.html").write_text(template.replace("__SCREEN_DATA__", payload))
    print(f"Exported {len(scenes)} screen variants, five contact sheets, PDF, SVGs, logo assets, and self-contained review.html.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate without overwriting exports.")
    args = parser.parse_args()
    fixtures = json.loads((ROOT / "fixtures.json").read_text())
    scenes = build_scenes(fixtures)
    validate(fixtures, scenes)
    if not args.check:
        export(scenes)


if __name__ == "__main__":
    main()
