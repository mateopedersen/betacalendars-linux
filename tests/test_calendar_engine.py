import unittest
from datetime import date

from betacalendars_studio.calendar_engine import (
    WeekStart,
    days_in_month,
    inspect_date,
    is_leap_year,
    month_geometry,
    month_grid,
    move_month,
    validate_month,
)


class LeapYearTests(unittest.TestCase):
    def test_century_and_leap_year_rules(self):
        expected = {1900: False, 2000: True, 2027: False, 2028: True, 2100: False, 2400: True}
        for year, leap in expected.items():
            with self.subTest(year=year):
                self.assertEqual(is_leap_year(year), leap)

    def test_month_lengths(self):
        self.assertEqual(days_in_month(2000, 2), 29)
        self.assertEqual(days_in_month(1900, 2), 28)
        self.assertEqual(days_in_month(2027, 2), 28)
        self.assertEqual(days_in_month(2028, 2), 29)
        self.assertEqual(days_in_month(2027, 5), 31)


class GeometryTests(unittest.TestCase):
    def test_2027_first_weekdays(self):
        expected = [4, 0, 0, 3, 5, 1, 3, 6, 2, 4, 0, 2]
        self.assertEqual([date(2027, month, 1).weekday() for month in range(1, 13)], expected)

    def test_2027_row_matrix(self):
        monday = [5, 4, 5, 5, 6, 5, 5, 6, 5, 5, 5, 5]
        sunday = [6, 5, 5, 5, 6, 5, 5, 5, 5, 6, 5, 5]
        for month, expected in enumerate(monday, 1):
            self.assertEqual(month_geometry(2027, month, WeekStart.MONDAY).natural_rows, expected)
        for month, expected in enumerate(sunday, 1):
            self.assertEqual(month_geometry(2027, month, WeekStart.SUNDAY).natural_rows, expected)

    def test_natural_rows_are_not_normalized(self):
        self.assertEqual(len(month_grid(2027, 2, WeekStart.MONDAY)), 4)
        self.assertEqual(len(month_grid(2027, 2, WeekStart.MONDAY, normalize_six=True)), 6)
        self.assertEqual(month_geometry(2027, 2, WeekStart.MONDAY).natural_rows, 4)

    def test_month_content_for_each_start(self):
        for year in range(1800, 2201):
            for month in range(1, 13):
                for start in WeekStart:
                    with self.subTest(year=year, month=month, week_start=start.value):
                        geometry = month_geometry(year, month, start)
                        rows = month_grid(year, month, start, show_adjacent=True)
                        flat = [cell for row in rows for cell in row]
                        in_month = [
                            cell for cell in flat if cell.year == year and cell.month == month
                        ]
                        expected = [date(year, month, day) for day in range(1, geometry.days + 1)]
                        self.assertEqual(in_month, expected)
                        self.assertEqual(len(flat), geometry.natural_rows * 7)
                        self.assertEqual(len(set(flat)), len(flat))
                        self.assertTrue(4 <= geometry.natural_rows <= 6)
                        self.assertTrue(all((b - a).days == 1 for a, b in zip(flat, flat[1:])))
                        self.assertTrue(all(validate_month(year, month, start).values()))

    def test_month_navigation_rollover(self):
        self.assertEqual(move_month(2027, 12, 1), (2028, 1))
        self.assertEqual(move_month(2028, 1, -1), (2027, 12))

    def test_month_navigation_stays_in_supported_range(self):
        with self.assertRaises(ValueError):
            move_month(1, 1, -1)
        with self.assertRaises(ValueError):
            move_month(9999, 12, 1)

    def test_calendar_grids_handle_supported_range_edges(self):
        january = month_grid(1, 1, WeekStart.SUNDAY, show_adjacent=True)
        december = month_grid(9999, 12, WeekStart.SUNDAY, show_adjacent=True)
        self.assertTrue(any(cell is None for cell in january[0]))
        self.assertTrue(any(cell is None for cell in december[-1]))
        self.assertTrue(all(validate_month(1, 1, WeekStart.SUNDAY).values()))
        self.assertTrue(all(validate_month(9999, 12, WeekStart.SUNDAY).values()))

    def test_iso_week_year_boundary(self):
        facts = inspect_date(date(2021, 1, 1))
        self.assertEqual((facts["iso_week_year"], facts["iso_week"]), (2020, 53))

    def test_august_and_october_2027_regressions(self):
        self.assertEqual(month_geometry(2027, 8, WeekStart.MONDAY).natural_rows, 6)
        self.assertEqual(month_geometry(2027, 8, WeekStart.SUNDAY).natural_rows, 5)
        self.assertEqual(month_geometry(2027, 10, WeekStart.MONDAY).natural_rows, 5)
        self.assertEqual(month_geometry(2027, 10, WeekStart.SUNDAY).natural_rows, 6)
