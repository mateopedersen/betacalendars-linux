"""Command-line entry point for Beta Calendars Studio."""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from . import __version__
from .calendar_engine import (
    WeekStart,
    inspect_date,
    is_leap_year,
    month_geometry,
    month_grid,
    validate_month,
    validate_year,
)
from .svg_export import LAYOUTS, render_month_svg


def _month_grid_text(year: int, month: int, start: WeekStart, adjacent: bool = False, normalize_six: bool = False) -> str:
    geometry = month_geometry(year, month, start)
    rows = month_grid(year, month, start, show_adjacent=adjacent, normalize_six=normalize_six)
    lines = [date(year, month, 1).strftime("%B %Y"), " ".join(start.labels)]
    lines.extend(" ".join("%3d" % cell.day if cell and cell.month == month else ("%3d" % cell.day if cell else "   ") for cell in row) for row in rows)
    lines.extend(("Natural rows: %d" % geometry.natural_rows, "Days: %d" % geometry.days))
    return "\n".join(lines)


def _year_text(year: int, start: WeekStart) -> str:
    blocks: List[List[str]] = []
    for month in range(1, 13):
        grid = month_grid(year, month, start, show_adjacent=False, normalize_six=True)
        label = date(year, month, 1).strftime("%B")
        block = [label.center(23), " ".join(start.labels)]
        for row in grid:
            block.append(" ".join("%2d" % cell.day if cell else "  " for cell in row))
        blocks.append(block)
    lines = [str(year)]
    for group_start in range(0, 12, 3):
        group = blocks[group_start:group_start + 3]
        for line_index in range(8):
            lines.append("   ".join(block[line_index] for block in group))
        lines.append("")
    return "\n".join(lines).rstrip()


def _inspect_text(iso_date: str) -> str:
    facts = inspect_date(date.fromisoformat(iso_date))
    output = [
        "Date: %s" % facts["date"],
        "Weekday: %s" % facts["weekday"],
        "Day of year: %s" % facts["day_of_year"],
        "ISO week: %s-W%02d" % (facts["iso_week_year"], facts["iso_week"]),
        "Month: %d" % facts["month"],
        "Quarter: Q%d" % facts["quarter"],
        "Days in month: %d" % facts["days_in_month"],
        "Leap year: %s" % ("yes" if facts["is_leap_year"] else "no"),
        "Days remaining in month: %d" % facts["days_remaining_in_month"],
        "Days remaining in year: %d" % facts["days_remaining_in_year"],
        "Natural row: Monday-first %d, Sunday-first %d"
        % (facts["monday_first_row"], facts["sunday_first_row"]),
    ]
    return "\n".join(output)


def _geometry_text(year: int, month: int) -> str:
    lines = ["%s %d" % (date(year, month, 1).strftime("%B"), year)]
    for start in WeekStart:
        geometry = month_geometry(year, month, start)
        checks = validate_month(year, month, start)
        lines.extend([
            "",
            "%s-first" % start.value.title(),
            "  First weekday: %s" % date(year, month, 1).strftime("%A"),
            "  Days in month: %d" % geometry.days,
            "  Leading cells: %d" % geometry.leading_cells,
            "  Natural rows: %d" % geometry.natural_rows,
            "  Grid size: %d" % geometry.grid_size,
            "  Invariants: %s" % ("PASS" if all(checks.values()) else "FAIL"),
        ])
    return "\n".join(lines)


def _week_start(value: str) -> WeekStart:
    try:
        return WeekStart(value.lower())
    except ValueError as error:
        raise argparse.ArgumentTypeError("week start must be monday or sunday") from error


def _write_svg(svg: str, output: Optional[str]) -> None:
    if output:
        Path(output).write_text(svg, encoding="utf-8")
        print("Wrote %s" % output)
    else:
        sys.stdout.write(svg)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="betacalendars", description="Offline calendar tools")
    commands = parser.add_subparsers(dest="command", required=True)

    month_parser = commands.add_parser("month", help="print one month")
    month_parser.add_argument("year", type=int)
    month_parser.add_argument("month", type=int)
    month_parser.add_argument("--week-start", type=_week_start, default=WeekStart.MONDAY)
    month_parser.add_argument("--show-adjacent", action="store_true")
    month_parser.add_argument("--fixed-six", action="store_true")
    month_parser.add_argument("--export-svg", metavar="PATH")

    year_parser = commands.add_parser("year", help="print a compact twelve-month view")
    year_parser.add_argument("year", type=int)
    year_parser.add_argument("--week-start", type=_week_start, default=WeekStart.MONDAY)

    inspect_parser = commands.add_parser("inspect", help="inspect a Gregorian civil date")
    inspect_parser.add_argument("date", help="date in YYYY-MM-DD form")

    grid_parser = commands.add_parser("grid", help="show month geometry and diagnostics")
    grid_parser.add_argument("year", type=int)
    grid_parser.add_argument("month", type=int)

    validate_parser = commands.add_parser("validate", help="validate all months in a year")
    validate_parser.add_argument("year", type=int)

    blank_parser = commands.add_parser("blank", help="create a printable blank calendar SVG")
    blank_parser.add_argument("--month", help="month in YYYY-MM form; defaults to the current month")
    blank_parser.add_argument("--layout", choices=LAYOUTS, default="blank-month")
    blank_parser.add_argument("--paper", choices=("a4", "letter"), default="a4")
    blank_parser.add_argument("--orientation", choices=("portrait", "landscape"), default="portrait")
    blank_parser.add_argument("--week-start", type=_week_start, default=WeekStart.MONDAY)
    blank_parser.add_argument("--hide-title", action="store_true")
    blank_parser.add_argument("--hide-weekdays", action="store_true")
    blank_parser.add_argument("--notes-margin", action="store_true")
    blank_parser.add_argument("--writing-lines", action="store_true")
    blank_parser.add_argument("--week-numbers", action="store_true")
    blank_parser.add_argument("--fixed-six", action="store_true")
    blank_parser.add_argument("--minimal-grid", action="store_true")
    blank_parser.add_argument("--output", metavar="PATH")

    commands.add_parser("version", help="show version")
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "month":
        output = _month_grid_text(args.year, args.month, args.week_start, args.show_adjacent, args.fixed_six)
        if args.export_svg:
            _write_svg(render_month_svg(args.year, args.month, args.week_start), args.export_svg)
        print(output)
        return 0
    if args.command == "year":
        print(_year_text(args.year, args.week_start))
        return 0
    if args.command == "inspect":
        print(_inspect_text(args.date))
        return 0
    if args.command == "grid":
        print(_geometry_text(args.year, args.month))
        return 0
    if args.command == "validate":
        if args.year < 1 or args.year > 9999:
            raise ValueError("year must be between 1 and 9999")
        checks = validate_year(args.year)
        failures = [name for name, passed in checks.items() if not passed]
        if failures:
            print("FAIL %d checks; %d failed" % (len(checks), len(failures)))
            for name in failures:
                print("  FAIL %s" % name)
            return 1
        print("PASS %d month-layout checks for %d" % (len(checks), args.year))
        return 0
    if args.command == "blank":
        if args.month:
            year_text, month_text = args.month.split("-", 1)
            year, month = int(year_text), int(month_text)
        else:
            today = date.today()
            year, month = today.year, today.month
        svg = render_month_svg(
            year,
            month,
            week_start=args.week_start,
            paper=args.paper,
            orientation=args.orientation,
            layout=args.layout,
            show_month_title=not args.hide_title,
            show_weekday_headers=not args.hide_weekdays,
            notes_margin=args.notes_margin,
            writing_lines=args.writing_lines,
            show_week_numbers=args.week_numbers,
            fixed_six_rows=args.fixed_six,
            minimal_grid=args.minimal_grid,
        )
        _write_svg(svg, args.output)
        return 0
    parser = build_parser()
    parser.error("unknown command")
    return 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
