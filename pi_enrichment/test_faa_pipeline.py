import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

import faa_pipeline


class RegistrySyncTests(unittest.TestCase):
    def sync_and_check(self, source, directory):
        db = directory / "registry.sqlite3"
        count = faa_pipeline.run_sync(
            source.as_uri(), db, directory / "registry.csv", directory / "meta.json"
        )
        self.assertEqual(count, 1)
        with sqlite3.connect(db) as connection:
            row = connection.execute(
                "SELECT adsb_icao, registration, operator_name FROM aircraft_registry"
            ).fetchone()
        self.assertEqual(row, ("A1B2C3", "123AB", "EXAMPLE AIR"))
        self.assertEqual(json.loads((directory / "meta.json").read_text())["row_count"], 1)

    def test_faa_zip_imports_master_instead_of_reference_or_deregistered_data(self):
        for master_name in ("MASTER.txt", "data/master.csv"):
            with self.subTest(master_name=master_name), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                archive = directory / "faa.zip"
                with zipfile.ZipFile(archive, "w") as zipped:
                    zipped.writestr("ACFTREF.txt", "CODE,MFR,MODEL\n1,BOEING,737\n")
                    zipped.writestr("DEREG.txt", "N-NUMBER,NAME,MODE S CODE HEX\n999,OLD OWNER,FFFFFF\n")
                    zipped.writestr(master_name, "N-NUMBER,NAME,MODE S CODE HEX\n123AB,EXAMPLE AIR,A1B2C3\n")
                self.sync_and_check(archive, directory)

    def test_standalone_csv_still_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = directory / "custom.csv"
            source.write_text("registration,operator,hex\n123AB,EXAMPLE AIR,a1b2c3\n")
            self.sync_and_check(source, directory)

    def test_single_csv_zip_still_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive = directory / "custom.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("aircraft.csv", "registration,operator,hex\n123AB,EXAMPLE AIR,a1b2c3\n")
            self.sync_and_check(archive, directory)


if __name__ == "__main__":
    unittest.main()
