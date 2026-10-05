# Architecture

The application has four small layers:

1. `calendar_engine.py` owns date-only Gregorian arithmetic, month geometry, ISO inspection, and invariant checks.
2. `cli.py` formats engine results for terminals and routes SVG requests.
3. `svg_export.py` turns a selected month and layout options into a self-contained SVG document.
4. `gui.py` presents month, year, designer, inspector, print, lab, resource, and about views. It calls the same engine and exporter as the CLI.

The engine uses Python's proleptic Gregorian `date` model. It never converts an all-day civil date into a time or timezone. Layout code receives a `WeekStart` value and cannot modify the date calculations.

The GTK layer uses a portal-backed file picker for saving output. Optional website pages are exposed as user-clicked links; they are not fetched in the background.

