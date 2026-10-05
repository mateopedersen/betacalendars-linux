"""Gregorian civil-date calculations shared by the UI, CLI, and exporters."""

import calendar
import math
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class WeekStart(str, Enum):
    MONDAY = "monday"
    SUNDAY = "sunday"

    @property
    def weekday_index(self) -> int:
        return 0 if self is WeekStart.MONDAY else 6

    @property
    def labels(self) -> Tuple[str, ...]:
        if self is WeekStart.MONDAY:
            return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        return ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


@dataclass(frozen=True)
class MonthGeometry:
    year: int
    month: int
    week_start: WeekStart
    first_weekday: int
    days: int
    leading_cells: int
    natural_rows: int

    @property
    def grid_size(self) -> int:
        return self.natural_rows * 7


def is_leap_year(year: int) -> bool:
    """Return whether *year* is leap under the proleptic Gregorian rule."""
    return year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)


def days_in_month(year: int, month: int) -> int:
    if year < 1 or year > 9999:
        raise ValueError("year must be between 1 and 9999")
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    return calendar.monthrange(year, month)[1]


def month_geometry(
    year: int, month: int, week_start: WeekStart = WeekStart.MONDAY
) -> MonthGeometry:
    """Calculate natural month-grid geometry without fixing the row count."""
    count = days_in_month(year, month)
    first = date(year, month, 1).weekday()
    leading = (first - week_start.weekday_index) % 7
    rows = int(math.ceil((leading + count) / 7.0))
    return MonthGeometry(year, month, week_start, first, count, leading, rows)


def month_grid(
    year: int,
    month: int,
    week_start: WeekStart = WeekStart.MONDAY,
    show_adjacent: bool = True,
    normalize_six: bool = False,
) -> List[List[Optional[date]]]:
    """Return presentation rows; a six-row option never changes natural geometry."""
    geometry = month_geometry(year, month, week_start)
    row_count = 6 if normalize_six else geometry.natural_rows
    first_day = date(year, month, 1)
    rows: List[List[Optional[date]]] = []
    for row_index in range(row_count):
        row: List[Optional[date]] = []
        for column_index in range(7):
            offset = row_index * 7 + column_index - geometry.leading_cells
            try:
                cell_date = first_day + timedelta(days=offset)
            except OverflowError:
                row.append(None)
                continue
            if show_adjacent or cell_date.month == month:
                row.append(cell_date)
            else:
                row.append(None)
        rows.append(row)
    return rows


def move_month(year: int, month: int, offset: int) -> Tuple[int, int]:
    """Move by *offset* months while keeping year/month in the civil range."""
    days_in_month(year, month)
    index = year * 12 + month - 1 + offset
    target_year, target_month_zero = divmod(index, 12)
    target_month = target_month_zero + 1
    if target_year < 1 or target_year > 9999:
        raise ValueError("month navigation would leave the supported year range")
    return target_year, target_month


def row_number(day: date, week_start: WeekStart) -> int:
    geometry = month_geometry(day.year, day.month, week_start)
    return (geometry.leading_cells + day.day - 1) // 7 + 1


def inspect_date(day: date) -> Dict[str, object]:
    """Return civil-date facts; no timestamp or timezone conversion is involved."""
    month_days = days_in_month(day.year, day.month)
    iso_year, iso_week, iso_weekday = day.isocalendar()
    end_of_year = date(day.year, 12, 31)
    return {
        "date": day,
        "weekday": day.strftime("%A"),
        "weekday_number_monday_first": day.weekday(),
        "day_of_year": day.timetuple().tm_yday,
        "iso_week": iso_week,
        "iso_week_year": iso_year,
        "iso_weekday": iso_weekday,
        "month": day.month,
        "quarter": (day.month - 1) // 3 + 1,
        "days_in_month": month_days,
        "is_leap_year": is_leap_year(day.year),
        "days_remaining_in_month": month_days - day.day,
        "days_remaining_in_year": (end_of_year - day).days,
        "monday_first_row": row_number(day, WeekStart.MONDAY),
        "sunday_first_row": row_number(day, WeekStart.SUNDAY),
    }


def validate_month(year: int, month: int, week_start: WeekStart) -> Dict[str, bool]:
    """Evaluate independent month-grid invariants for a chosen week start."""
    geometry = month_geometry(year, month, week_start)
    grid = month_grid(year, month, week_start, show_adjacent=True)
    flattened = [cell for row in grid for cell in row if cell is not None]
    actual_month_dates = [cell for cell in flattened if cell.year == year and cell.month == month]
    expected_dates = [date(year, month, day) for day in range(1, geometry.days + 1)]
    sequential = all((right - left).days == 1 for left, right in zip(flattened, flattened[1:]))
    weekday_continuity = all(
        (row[index + 1] - row[index]).days == 1
        for row in grid
        for index in range(6)
        if row[index] is not None and row[index + 1] is not None
    )
    return {
        "unique_dates": len(flattened) == len(set(flattened)),
        "sequential_dates": sequential,
        "correct_month_length": len(actual_month_dates) == geometry.days,
        "valid_row_count": 4 <= geometry.natural_rows <= 6 and len(grid) == geometry.natural_rows,
        "weekday_continuity": weekday_continuity,
        "no_missing_day": actual_month_dates == expected_dates,
        "no_duplicated_day": len(actual_month_dates) == len(set(actual_month_dates)),
    }


def validate_year(year: int) -> Dict[str, bool]:
    """Check all months under both supported week starts."""
    checks: Dict[str, bool] = {}
    for start in WeekStart:
        for month in range(1, 13):
            for name, passed in validate_month(year, month, start).items():
                checks["%s_%02d_%s" % (start.value, month, name)] = passed
    return checks
