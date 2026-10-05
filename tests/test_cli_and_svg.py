import tempfile
import unittest
from datetime import date
from pathlib import Path

from betacalendars_studio.calendar_engine import WeekStart
from betacalendars_studio.cli import main
from betacalendars_studio.svg_export import render_month_svg


class SvgExportTests(unittest.TestCase):
    def test_svg_has_print_dimensions_and_grid(self):
        svg = render_month_svg(2027, 2, WeekStart.MONDAY, paper="a4")
        self.assertIn('width="595.28pt"', svg)
        self.assertIn('height="841.89pt"', svg)
        self.assertIn("February 2027", svg)
        self.assertEqual(svg.count('<line '), 37)

    def test_blank_designer_options(self):
        svg = render_month_svg(
            2027,
            8,
            WeekStart.SUNDAY,
            paper="letter",
            orientation="landscape",
            layout="notes-calendar",
            notes_margin=True,
            writing_lines=True,
            show_week_numbers=True,
            fixed_six_rows=True,
        )
        self.assertIn('width="792.00pt"', svg)
        self.assertIn('height="612.00pt"', svg)
        self.assertIn("NOTES", svg)
        self.assertIn("WK", svg)
        self.assertIn('stroke="#e5eaf0"', svg)

    def test_weekly_layout_focuses_one_week_and_validates_date(self):
        svg = render_month_svg(
            2027,
            2,
            layout="weekly-planner",
            focus_date=date(2027, 2, 10),
        )
        self.assertIn("weekly planner", svg)
        self.assertIn(">10</text>", svg)
        self.assertNotIn(">1</text>", svg)
        with self.assertRaises(ValueError):
            render_month_svg(2027, 2, layout="weekly-planner", focus_date=date(2027, 3, 1))

    def test_cli_month_and_date_inspector(self):
        self.assertEqual(main(["month", "2027", "2", "--week-start", "monday"]), 0)
        self.assertEqual(main(["inspect", "2021-01-01"]), 0)

    def test_cli_blank_writes_svg_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "calendar.svg"
            self.assertEqual(main(["blank", "--month", "2027-02", "--output", str(target)]), 0)
            self.assertTrue(target.exists())
            self.assertIn("February 2027", target.read_text(encoding="utf-8"))
