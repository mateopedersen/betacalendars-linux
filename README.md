# Beta Calendars Studio

Beta Calendars Studio is an offline calendar layout and civil-date utility for Linux. It combines a native GTK 4 desktop app with a command-line interface and a shared Gregorian date engine.

## Features

- Month and year views with Monday-first or Sunday-first weeks.
- Natural month grids with four, five, or six rows, plus an optional six-row presentation setting.
- Civil-date inspection for weekdays, day of year, ISO week and week-year, quarter, leap years, and month/year boundaries.
- Calendar Lab checks for date continuity, duplicates, missing days, month length, and row geometry.
- Blank calendar layouts for A4 and US Letter, in portrait or landscape, exported as SVG.
- A CLI for month and year views, date inspection, geometry diagnostics, yearly validation, and blank SVG export.
- An optional resource library. Online pages open only when a user selects a link.

Calendar calculations run locally. The app does not need an account, read personal calendars, or send calendar data.

## Screenshots

The CI workflow launches the GTK application on Ubuntu under a virtual display and captures five genuine app screenshots. The images are attached to each CI run as the `betacalendars-linux-screenshots` artifact.

## Calendar model

Dates are civil Gregorian dates. The arithmetic does not convert dates to timestamps or apply time zones. See [the calendar model](docs/CALENDAR_MODEL.md) for the month-grid formula and supported range.

## Month geometry

For a month with `D` days, first-day weekday `W` (Monday is zero), and configured week start `S` (Monday is zero or Sunday is six):

```text
leadingCells = (W - S + 7) mod 7
naturalRows  = ceil((leadingCells + D) / 7)
```

The calculation returns the natural four-, five-, or six-row grid. Normalizing a view to six rows is a presentation choice and does not change the arithmetic result.

## Blank Calendar Designer

The designer exports `month-grid`, `blank-month`, `weekly-planner`, or `notes-calendar` SVG layouts. It supports A4 and US Letter, portrait and landscape, weekday headers, week numbers, a notes margin, writing lines, minimal grid styling, and an optional fixed six-row layout.

## CLI

Install from a source checkout with Python 3.9 or later:

```sh
python3 -m pip install .
```

Examples:

```sh
betacalendars month 2027 2 --week-start monday
betacalendars year 2027 --week-start sunday
betacalendars inspect 2021-01-01
betacalendars grid 2027 8
betacalendars validate 2027
betacalendars blank --month 2027-02 --paper a4 --orientation portrait --output february.svg
```

Run the graphical application with `betacalendars-studio`. GTK 4 and PyGObject must be installed on the system. On Ubuntu, install `python3-gi` and `gir1.2-gtk-4.0` first.

## Build from source

```sh
python3 -m pip install .
betacalendars-studio
```

## Build the Snap

Snapcraft and a Linux build provider are required. The snap uses strict confinement and GTK's file chooser portal for user-selected SVG exports.

```sh
snapcraft
```

## Testing

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The regression suite checks leap years, month lengths, ISO week-year boundaries, December/January rollover, the full 2027 geometry matrix, and both week starts for each month from 1800 through 2200.

GitHub Actions also runs Ruff, Black, Python package builds, GTK screenshot capture, AppStream validation, and a Snap build. A version tag builds and tests a release candidate. Candidate publishing is enabled when the `STORE_LOGIN` Actions secret contains credentials exported with restricted Snap Store permissions. Stable release is a deliberate Store action after candidate QA.

See [the release guide](docs/RELEASING.md) for the restricted credential setup and candidate-to-stable procedure.

## Privacy

Core date calculations and SVG generation are local. The app has no analytics or telemetry and does not read personal calendars. It requests only desktop display interfaces. GTK's portal file chooser grants access only to the destination selected by the user. External resources are not opened until the user selects a link. See [Privacy](docs/PRIVACY.md).

## Online resources

Beta Calendars Studio works without the website. The application contains a resource library for optional, human-readable printable calendar pages at [Beta Calendars](https://www.betacalendars.com/).

## License

MIT. See [`LICENSE`](LICENSE).
