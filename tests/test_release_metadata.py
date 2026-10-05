import re
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_store_description_contains_live_resource_directory(self):
        description = (ROOT / "snap/store/description.md").read_text(encoding="utf-8")
        resources = {
            "https://www.betacalendars.com/",
            "https://www.betacalendars.com/monthly-calendar",
            "https://www.betacalendars.com/blank-calendar",
            "https://www.betacalendars.com/monthly-planner",
        }
        resources.update(
            "https://www.betacalendars.com/" + month + "-calendar.html"
            for month in (
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            )
        )
        markdown_links = set(re.findall(r"\[[^]]+\]\((https://[^)]+)\)", description))
        for resource in resources:
            with self.subTest(resource=resource):
                self.assertIn(resource, markdown_links)
        self.assertFalse(any("utm_" in url.lower() for url in markdown_links))
        self.assertFalse(any("example.com" in url.lower() for url in markdown_links))

    def test_resource_screen_contains_the_verified_monthly_planner(self):
        gui = (ROOT / "src/betacalendars_studio/gui.py").read_text(encoding="utf-8")
        self.assertIn("https://www.betacalendars.com/monthly-planner", gui)

    def test_store_icon_is_a_512_square_png(self):
        icon = (ROOT / "snap/gui/betacalendars.png").read_bytes()
        self.assertEqual(icon[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", icon[16:24])
        self.assertEqual((width, height), (512, 512))

    def test_snap_metadata_uses_real_product_and_source_fields(self):
        snapcraft = (ROOT / "snap/snapcraft.yaml").read_text(encoding="utf-8")
        for required in (
            "name: betacalendars",
            "title: Beta Calendars Studio",
            "base: core24",
            "confinement: strict",
            "grade: stable",
            "website: https://www.betacalendars.com/",
            "source-code: https://github.com/mateopedersen/betacalendars-linux",
            "issues: https://github.com/mateopedersen/betacalendars-linux/issues",
        ):
            with self.subTest(field=required):
                self.assertIn(required, snapcraft)
        summary = re.search(r"^summary: (.+)$", snapcraft, re.MULTILINE).group(1)
        self.assertLessEqual(len(summary), 79)

    def test_appstream_metadata_is_well_formed_and_has_real_support_links(self):
        metadata = ET.parse(ROOT / "data/org.betacalendars.Studio.metainfo.xml").getroot()
        self.assertEqual(metadata.findtext("id"), "com.betacalendars.Studio")
        links = {item.attrib["type"]: item.text for item in metadata.findall("url")}
        self.assertEqual(links["homepage"], "https://www.betacalendars.com/")
        self.assertEqual(
            links["vcs-browser"], "https://github.com/mateopedersen/betacalendars-linux"
        )
        self.assertEqual(
            links["bugtracker"], "https://github.com/mateopedersen/betacalendars-linux/issues"
        )


if __name__ == "__main__":
    unittest.main()
