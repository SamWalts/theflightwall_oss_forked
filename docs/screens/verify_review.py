#!/usr/bin/env python3
"""Check the offline screen gallery and exported design assets in Chromium."""

import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
from threading import Thread
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check_exports():
    scenes = json.loads((ROOT / "screens.json").read_text())
    assert len(scenes) == 34
    assert len([s for s in scenes if s["group"] == "departure"]) == 7
    for scene in scenes:
        for suffix in ("-native.png", ".png", ".svg"):
            assert (ROOT / "mockups" / (scene["id"] + suffix)).is_file()
        with Image.open(ROOT / "mockups" / (scene["id"] + "-native.png")) as native:
            assert native.size == (160, 32)
            for y, row in enumerate(scene["pixels"]):
                for x, index in enumerate(row):
                    color = "#" + "".join(f"{c:02x}" for c in native.getpixel((x, y)))
                    assert color == scene["palette"][index], scene["id"]
        with Image.open(ROOT / "mockups" / (scene["id"] + ".png")) as enlarged:
            assert enlarged.size == (1280, 256)
    manifest = json.loads((ROOT / "assets/manifest.json").read_text())
    for asset in manifest["assets"]:
        assert asset["production_approved"] is False
        path = ROOT / "assets" / asset["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]
        with Image.open(path) as logo:
            assert logo.size == (24, 24)
    assert (ROOT / "flightwall-screen-review.pdf").read_bytes().startswith(b"%PDF-")
    print("PASS: 34 export sets, serialized/native pixel agreement, logo checksums, and review PDF.")


def check_browser(executable, screenshots):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/review.html"
    errors, outside_requests, failed_responses = [], [], []
    try:
        with sync_playwright() as p:
            options = {"headless": True, "args": ["--no-sandbox", "--disable-crash-reporter", "--disable-breakpad"]}
            if executable:
                options["executable_path"] = executable
            browser = p.chromium.launch(**options)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1150}, device_scale_factor=1)
                page.set_default_timeout(8000)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: outside_requests.append(request.url)
                        if urlparse(request.url).scheme in ("http", "https") and urlparse(request.url).hostname != "127.0.0.1" else None)
                page.on("response", lambda response: failed_responses.append((response.status, response.url)) if response.status >= 400 else None)
                page.goto(url)
                assert page.locator(".thumb").count() == 5
                assert page.locator("#stage-title").inner_text() == "F01 · Flight overview / Delta"
                assert "ALT 35000FT" in page.locator("#display").get_attribute("aria-label")

                page.select_option("#airline", "united")
                page.locator('[data-page="motion"]').click()
                assert "TAS 470KT" in page.locator("#display").get_attribute("aria-label")
                assert "VS 0FT/M" in page.locator("#display").get_attribute("aria-label")
                page.select_option("#airline", "southwest")
                assert "VS -1500FT/M" in page.locator("#display").get_attribute("aria-label")

                page.select_option("#scenario", "no-departure-telemetry")
                assert page.locator(".thumb").count() == 7
                assert page.locator('[data-filter="departure"]').get_attribute("aria-pressed") == "true"
                assert "N123AB C172; ALT 4500FT; GS 112KT" in page.locator("#display").get_attribute("aria-label")
                assert page.locator("#counter").inner_text() == "01 / 07"
                assert "No-departure display option" == page.locator("#scene-category").text_content()
                page.locator("#next").click()
                assert "N123AB; CESSNA 172; HEX AB12CD" in page.locator("#display").get_attribute("aria-label")
                page.locator("#next").click()
                assert "DIST 1.8KM; TRK 090DEG" in page.locator("#display").get_attribute("aria-label")
                page.select_option("#scenario", "no-departure-explicit")
                assert "FROM UNKNOWN" in page.locator("#display").get_attribute("aria-label")
                page.select_option("#scenario", "no-departure-business-jet")
                assert "N456CJ C25B; ALT 31000FT; GS 410KT" in page.locator("#display").get_attribute("aria-label")
                page.select_option("#scenario", "no-departure-destination")
                assert "FROM -- TO EGLL; MANUAL TO" in page.locator("#display").get_attribute("aria-label")
                assert page.locator("#airline").input_value() == "united"
                page.select_option("#scenario", "no-departure-unidentified")
                assert "HEX AD56EF --" in page.locator("#display").get_attribute("aria-label")
                page.locator("#next").click()
                assert "Aircraft + telemetry" in page.locator("#stage-title").inner_text()
                page.goto(url + "#no-departure-nearby")
                page.reload()
                assert page.locator(".thumb").count() == 7
                assert page.locator("#counter").inner_text() == "03 / 07"
                assert "DIST 1.8KM; TRK 090DEG" in page.locator("#display").get_attribute("aria-label")
                for selector in ("#png-link", "#svg-link", "#native-link"):
                    assert (ROOT / page.locator(selector).get_attribute("href")).is_file()
                if screenshots:
                    screenshots.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshots / "no-departure.png"), full_page=True)

                page.select_option("#scenario", "case-partial")
                assert "ALT --FT" in page.locator("#display").get_attribute("aria-label")
                assert page.locator(".thumb").count() == 6
                assert page.locator('[data-filter="case"]').get_attribute("aria-pressed") == "true"
                page.select_option("#scenario", "case-anonymous")
                assert "HEX ABC123 C172" in page.locator("#display").get_attribute("aria-label")
                assert "GS 0KT" in page.locator("#display").get_attribute("aria-label")
                page.select_option("#scenario", "case-ground")
                assert "ALT GROUND" in page.locator("#display").get_attribute("aria-label")
                assert page.locator("#airline").input_value() == "delta"

                page.select_option("#scenario", "state-pi")
                assert page.locator('[data-filter="state"]').get_attribute("aria-pressed") == "true"
                assert page.locator(".thumb").count() == 6
                assert "PI UNAVAILABLE; WIFI CONNECTED" in page.locator("#display").get_attribute("aria-label")
                assert "DAL456" not in page.locator("#display").get_attribute("aria-label")
                page.locator('[data-filter="all"]').click()
                assert page.locator(".thumb").count() == 24
                page.locator('[data-id="case-inferred_route"]').click()
                assert "KATL?>----" in page.locator("#display").get_attribute("aria-label")

                page.goto(url + "#motion-united")
                page.reload()
                assert page.locator("#airline").input_value() == "united"
                assert "Motion details / United" in page.locator("#stage-title").inner_text()
                page.goto(url + "#state-receiver")
                page.reload()
                assert "RECEIVER STALE" in page.locator("#display").get_attribute("aria-label")
                assert page.locator(".thumb").count() == 6

                # Compare the flat canvas at known LED coordinates with the actual exported pixels.
                page.goto(url + "#overview-delta")
                page.uncheck("#dots")
                rgb = page.locator("#display").evaluate("canvas => Array.from(canvas.getContext('2d').getImageData(37 * 8 + 4, 3 * 8 + 4, 1, 1).data)")
                with Image.open(ROOT / "mockups/overview-delta-native.png") as native:
                    assert tuple(rgb[:3]) == native.getpixel((37, 3))
                page.check("#zones")
                assert "zones" in page.locator("#wall").get_attribute("class")
                page.locator("#brightness").focus()
                page.locator("#brightness").press("Home")
                assert page.locator("#brightness-value").inner_text() == "25%"
                page.locator("#brightness").press("End")
                page.uncheck("#zones")
                page.check("#dots")

                for selector in ("#png-link", "#svg-link", "#native-link"):
                    target = page.locator(selector).get_attribute("href")
                    assert (ROOT / target).is_file(), target
                    assert page.request.get(url.rsplit("/", 1)[0] + "/" + target).ok
                assert page.request.get(url.rsplit("/", 1)[0] + "/flightwall-screen-review.pdf").ok
                assert page.request.get(url.rsplit("/", 1)[0] + "/README.md").ok

                page.locator("#next").click()
                assert "Motion details" in page.locator("#stage-title").inner_text()
                page.locator("#previous").click()
                assert "Flight overview" in page.locator("#stage-title").inner_text()
                page.locator("#display").click()
                page.keyboard.press("ArrowRight")
                assert "Motion details" in page.locator("#stage-title").inner_text()
                page.keyboard.press("ArrowLeft")
                page.clock.install()
                page.locator("#play").click()
                page.clock.fast_forward(3100)
                assert "Motion details" in page.locator("#stage-title").inner_text()
                page.keyboard.press("Escape")
                assert page.locator("#play").get_attribute("aria-pressed") == "false"

                page.goto(url + "#overview-delta")
                if screenshots:
                    screenshots.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                for width in (390, 768, 1440):
                    page.set_viewport_size({"width": width, "height": 844})
                    assert page.evaluate("document.documentElement.scrollWidth") <= width
                page.set_viewport_size({"width": 390, "height": 844})
                if screenshots:
                    page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                page.emulate_media(reduced_motion="reduce")
                page.goto(url + "#overview-delta")
                assert page.locator("#play").get_attribute("aria-pressed") == "false"

                assert not errors, errors
                assert not outside_requests, outside_requests
                assert not failed_responses, failed_responses
                print("PASS: no-departure/private-aircraft options and cycle, airline/page selection, partial-data and status cases, deep links, filters, canvas controls, downloads, keyboard navigation, and demo playback.")
                print("PASS: 390/768/1440px layouts, no JavaScript errors or failed responses, and no external browser requests.")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", default=shutil.which("chromium") or shutil.which("google-chrome"), help="Installed Chromium executable; otherwise use Playwright's browser.")
    parser.add_argument("--screenshots", type=Path, help="Optional directory for desktop/mobile inspection screenshots.")
    args = parser.parse_args()
    check_exports()
    check_browser(args.browser, args.screenshots)


if __name__ == "__main__":
    main()
