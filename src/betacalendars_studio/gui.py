"""GTK 4 desktop interface. Calendar calculations come from calendar_engine."""

import argparse
import os
import sys
import sysconfig
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .calendar_engine import (
    WeekStart,
    inspect_date,
    month_geometry,
    month_grid,
    move_month,
    validate_month,
    validate_year,
)
from .svg_export import render_month_svg

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
WEEK_STARTS = (WeekStart.MONDAY, WeekStart.SUNDAY)
PRESETS = (
    ("February 1900", 1900, 2),
    ("February 2000", 2000, 2),
    ("February 2027", 2027, 2),
    ("February 2028", 2028, 2),
    ("February 2100", 2100, 2),
    ("August 2027", 2027, 8),
    ("October 2027", 2027, 10),
    ("December / January", 2027, 12),
)


def _gtk():
    try:
        # The Snap Python plugin runs the application from a private virtual
        # environment. Debian's PyGObject packages and their typelibs are staged
        # beside it, so add those paths before importing gi.
        snap_root = os.environ.get("SNAP")
        if snap_root:
            version = sysconfig.get_python_version()
            multiarch = sysconfig.get_config_var("MULTIARCH")
            staged_paths = [
                Path(snap_root) / "usr/lib/python3/dist-packages",
                Path(snap_root) / ("usr/lib/python%s/dist-packages" % version),
            ]
            for staged_path in staged_paths:
                if staged_path.is_dir() and str(staged_path) not in sys.path:
                    sys.path.insert(0, str(staged_path))
            typelib_paths = []
            if multiarch:
                typelib_paths.append(Path(snap_root) / "usr/lib" / multiarch / "girepository-1.0")
            typelib_paths.append(Path(snap_root) / "usr/lib/girepository-1.0")
            existing = [str(path) for path in typelib_paths if path.is_dir()]
            if existing:
                prior = os.environ.get("GI_TYPELIB_PATH")
                os.environ["GI_TYPELIB_PATH"] = os.pathsep.join(
                    existing + ([prior] if prior else [])
                )
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gio, GLib, Gtk
    except (ImportError, ValueError) as error:
        raise RuntimeError("GTK 4 and PyGObject are required to launch the desktop app") from error
    return Gio, GLib, Gtk


def _drop_down(Gtk, values: Sequence[str]):
    return Gtk.DropDown.new_from_strings(list(values))


class StudioWindow:
    def __init__(self, app, Gio, GLib, Gtk):
        self.app = app
        self.Gio = Gio
        self.GLib = GLib
        self.Gtk = Gtk
        self.today = date.today()
        self.year = self.today.year
        self.month = self.today.month
        self.week_start = WeekStart.MONDAY
        self._updating = False
        self._preview_counter = 0

        self.window = Gtk.ApplicationWindow(application=app, title="Beta Calendars Studio")
        self.window.set_default_size(1120, 760)
        self.window.set_size_request(900, 620)
        self._install_style()

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.set_child(outer)
        header = Gtk.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Beta Calendars Studio"))
        about_button = Gtk.Button(label="About")
        about_button.connect("clicked", lambda *_: self.stack.set_visible_child_name("about"))
        header.pack_end(about_button)
        outer.append(header)

        body = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_position(220)
        body.set_wide_handle(True)
        outer.append(body)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(140)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(self.stack)
        sidebar.set_size_request(205, -1)
        body.set_start_child(sidebar)
        body.set_end_child(self.stack)
        body.set_resize_start_child(False)
        body.set_shrink_start_child(False)
        body.set_shrink_end_child(False)

        self._build_calendar_page()
        self._build_year_page()
        self._build_designer_page()
        self._build_inspector_page()
        self._build_print_page()
        self._build_lab_page()
        self._build_resources_page()
        self._build_about_page()
        self._refresh_all()

    def _install_style(self):
        css = b"""
        .page { padding: 22px; }
        .page-title { font-size: 25px; font-weight: 700; color: #172b4d; }
        .page-subtitle { color: #64748b; }
        .toolbar { padding: 10px 0; }
        .calendar-day { min-width: 62px; min-height: 54px; padding: 5px; }
        .calendar-adjacent { color: #98a2b3; }
        .calendar-today { border: 2px solid #5b5bd6; border-radius: 8px; }
        .month-card { padding: 9px; border: 1px solid #d9e1ec; border-radius: 10px; background: #fff; }
        .year-card { padding: 5px; border: 1px solid #d9e1ec; border-radius: 8px; background: #fff; }
        .year-day { min-width: 20px; min-height: 20px; padding: 1px; font-size: 11px; }
        .metric-card { padding: 12px; border: 1px solid #d9e1ec; border-radius: 10px; }
        .muted { color: #64748b; }
        """
        provider = self.Gtk.CssProvider()
        provider.load_from_data(css)
        self.Gtk.StyleContext.add_provider_for_display(
            self.Gtk.Widget.get_display(self.window),
            provider,
            self.Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _page(self, name: str, title: str, subtitle: str):
        root = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=12)
        root.add_css_class("page")
        heading = self.Gtk.Label(label=title, xalign=0)
        heading.add_css_class("page-title")
        root.append(heading)
        if subtitle:
            detail = self.Gtk.Label(label=subtitle, xalign=0, wrap=True)
            detail.add_css_class("page-subtitle")
            root.append(detail)
        self.stack.add_titled(root, name, title)
        return root

    def _spin_year(self, year: int):
        adjustment = self.Gtk.Adjustment(
            value=year, lower=1, upper=9999, step_increment=1, page_increment=10
        )
        spin = self.Gtk.SpinButton(adjustment=adjustment, climb_rate=1, digits=0)
        spin.set_numeric(True)
        return spin

    def _selected_week_start(self, dropdown) -> WeekStart:
        return WEEK_STARTS[dropdown.get_selected()]

    def _current_start(self) -> WeekStart:
        return self._selected_week_start(self.calendar_week_dropdown)

    def _control_row(self, *widgets):
        row = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=8)
        row.add_css_class("toolbar")
        for widget in widgets:
            row.append(widget)
        return row

    def _build_calendar_page(self):
        page = self._page(
            "calendar",
            "Calendar",
            "Browse a month with deterministic Gregorian dates and natural four to six week rows.",
        )
        self.calendar_month_dropdown = _drop_down(self.Gtk, MONTH_NAMES)
        self.calendar_month_dropdown.set_selected(self.month - 1)
        self.calendar_year_spin = self._spin_year(self.year)
        self.calendar_week_dropdown = _drop_down(self.Gtk, ("Monday first", "Sunday first"))
        self.calendar_week_dropdown.set_selected(0)
        previous = self.Gtk.Button(label="‹ Previous")
        today = self.Gtk.Button(label="Today")
        next_button = self.Gtk.Button(label="Next ›")
        previous.connect("clicked", lambda *_: self._move_month(-1))
        today.connect("clicked", lambda *_: self._set_month(self.today.year, self.today.month))
        next_button.connect("clicked", lambda *_: self._move_month(1))
        self.show_weeks = self.Gtk.CheckButton(label="Week numbers")
        self.show_adjacent = self.Gtk.CheckButton(label="Adjacent dates")
        self.normalize_six = self.Gtk.CheckButton(label="Normalize to six rows")
        self.calendar_month_dropdown.connect("notify::selected", self._calendar_selection_changed)
        self.calendar_year_spin.connect("value-changed", self._calendar_selection_changed)
        self.calendar_week_dropdown.connect("notify::selected", self._calendar_selection_changed)
        self.show_weeks.connect("toggled", self._refresh_month)
        self.show_adjacent.connect("toggled", self._refresh_month)
        self.normalize_six.connect("toggled", self._refresh_month)
        page.append(
            self._control_row(
                previous, today, next_button, self.calendar_month_dropdown, self.calendar_year_spin
            )
        )
        page.append(
            self._control_row(
                self.Gtk.Label(label="Week starts:"),
                self.calendar_week_dropdown,
                self.show_weeks,
                self.show_adjacent,
                self.normalize_six,
            )
        )
        self.calendar_grid_holder = self.Gtk.Box(
            orientation=self.Gtk.Orientation.VERTICAL, spacing=5
        )
        self.calendar_grid_holder.set_vexpand(True)
        self.calendar_grid_holder.set_valign(self.Gtk.Align.FILL)
        page.append(self.calendar_grid_holder)

    def _calendar_selection_changed(self, *_):
        if self._updating:
            return
        month = self.calendar_month_dropdown.get_selected() + 1
        year = self.calendar_year_spin.get_value_as_int()
        self.year, self.month = year, month
        self._refresh_all()

    def _move_month(self, amount: int):
        try:
            year, month = move_month(self.year, self.month, amount)
        except ValueError:
            return
        self._set_month(year, month)

    def _set_month(self, year: int, month: int):
        self.year, self.month = year, month
        self._updating = True
        self.calendar_year_spin.set_value(year)
        self.calendar_month_dropdown.set_selected(month - 1)
        self._updating = False
        self._refresh_all()

    def _clear_box(self, box):
        child = box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            box.remove(child)
            child = next_child

    def _open_inspector(self, day: date):
        self._update_inspector(day)
        self.stack.set_visible_child_name("inspector")

    def _refresh_month(self, *_):
        if not hasattr(self, "calendar_grid_holder"):
            return
        Gtk = self.Gtk
        self._clear_box(self.calendar_grid_holder)
        start = self._current_start()
        grid = month_grid(
            self.year,
            self.month,
            start,
            show_adjacent=self.show_adjacent.get_active(),
            normalize_six=self.normalize_six.get_active(),
        )
        table = Gtk.Grid(column_spacing=4, row_spacing=4)
        table.set_column_homogeneous(True)
        col_offset = 1 if self.show_weeks.get_active() else 0
        if col_offset:
            label = Gtk.Label(label="WK")
            label.add_css_class("muted")
            table.attach(label, 0, 0, 1, 1)
        for index, label_text in enumerate(start.labels):
            label = Gtk.Label(label=label_text)
            label.set_margin_bottom(5)
            label.add_css_class("muted")
            table.attach(label, index + col_offset, 0, 1, 1)
        for row_index, row in enumerate(grid, 1):
            if col_offset:
                visible = [cell for cell in row if cell is not None]
                row_date = visible[0]
                week = self.GLib.DateTime.new_local(
                    row_date.year, row_date.month, row_date.day, 12, 0, 0
                ).get_week_of_year()
                number = Gtk.Label(label="%02d" % week)
                number.add_css_class("muted")
                table.attach(number, 0, row_index, 1, 1)
            for column_index, cell in enumerate(row):
                if cell is None:
                    table.attach(Gtk.Label(label=""), column_index + col_offset, row_index, 1, 1)
                    continue
                button = Gtk.Button()
                button.add_css_class("calendar-day")
                content = Gtk.Label(label=str(cell.day))
                button.set_child(content)
                if cell.month != self.month:
                    content.add_css_class("calendar-adjacent")
                if cell == self.today:
                    button.add_css_class("calendar-today")
                button.set_tooltip_text(cell.strftime("%A, %B %d, %Y"))
                button.connect(
                    "clicked", lambda _button, selected=cell: self._open_inspector(selected)
                )
                table.attach(button, column_index + col_offset, row_index, 1, 1)
        self.calendar_grid_holder.append(table)
        geometry = month_geometry(self.year, self.month, start)
        footer = Gtk.Label(
            label="%d days · %d natural rows · %s-first"
            % (geometry.days, geometry.natural_rows, start.value.title()),
            xalign=0,
        )
        footer.add_css_class("muted")
        self.calendar_grid_holder.append(footer)

    def _build_year_page(self):
        page = self._page(
            "year", "Year", "Twelve compact month grids. Select any date to inspect it."
        )
        self.year_view_spin = self._spin_year(self.year)
        self.year_view_week_dropdown = _drop_down(self.Gtk, ("Monday first", "Sunday first"))
        self.year_view_spin.connect("value-changed", self._refresh_year)
        self.year_view_week_dropdown.connect("notify::selected", self._refresh_year)
        page.append(
            self._control_row(
                GtkLabel(self.Gtk, "Year:"), self.year_view_spin, self.year_view_week_dropdown
            )
        )
        self.year_grid_holder = self.Gtk.Grid(column_spacing=12, row_spacing=12)
        self.year_grid_holder.set_column_homogeneous(True)
        self.year_grid_holder.set_row_homogeneous(True)
        scroll = self.Gtk.ScrolledWindow()
        scroll.set_child(self.year_grid_holder)
        scroll.set_vexpand(True)
        page.append(scroll)

    def _refresh_year(self, *_):
        if not hasattr(self, "year_grid_holder"):
            return
        Gtk = self.Gtk
        holder = self.year_grid_holder
        child = holder.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            holder.remove(child)
            child = next_child
        year = self.year_view_spin.get_value_as_int()
        start = self._selected_week_start(self.year_view_week_dropdown)
        for month in range(1, 13):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            card.add_css_class("year-card")
            title = Gtk.Button(label=MONTH_NAMES[month - 1])
            title.connect("clicked", lambda _button, y=year, m=month: self._set_month(y, m))
            card.append(title)
            table = Gtk.Grid(column_spacing=1, row_spacing=1)
            table.set_column_homogeneous(True)
            for index, label_text in enumerate(start.labels):
                label = Gtk.Label(label=label_text[0])
                label.add_css_class("muted")
                table.attach(label, index, 0, 1, 1)
            for row_index, row in enumerate(month_grid(year, month, start, False, True), 1):
                for column_index, cell in enumerate(row):
                    day_button = Gtk.Button(label=str(cell.day) if cell else "")
                    day_button.add_css_class("year-day")
                    day_button.set_sensitive(cell is not None)
                    day_button.set_has_frame(False)
                    if cell:
                        day_button.connect(
                            "clicked", lambda _button, d=cell: self._open_inspector(d)
                        )
                    table.attach(day_button, column_index, row_index, 1, 1)
            card.append(table)
            self.year_grid_holder.attach(card, (month - 1) % 4, (month - 1) // 4, 1, 1)

    def _build_designer_page(self):
        page = self._page(
            "designer",
            "Blank Designer",
            "Create an empty print layout. No personal events or schedule data are added.",
        )
        self.design_layout = _drop_down(
            self.Gtk, ("Month Grid", "Blank Month", "Weekly Planner", "Notes Calendar")
        )
        self.design_paper = _drop_down(self.Gtk, ("A4", "US Letter"))
        self.design_orientation = _drop_down(self.Gtk, ("Portrait", "Landscape"))
        self.design_week = _drop_down(self.Gtk, ("Monday first", "Sunday first"))
        self.design_title = self.Gtk.CheckButton(label="Show month title")
        self.design_title.set_active(True)
        self.design_headers = self.Gtk.CheckButton(label="Show weekday headers")
        self.design_headers.set_active(True)
        self.design_notes = self.Gtk.CheckButton(label="Notes margin")
        self.design_lines = self.Gtk.CheckButton(label="Writing lines")
        self.design_weeks = self.Gtk.CheckButton(label="Week numbers")
        self.design_fixed = self.Gtk.CheckButton(label="Fixed six rows")
        self.design_minimal = self.Gtk.CheckButton(label="Minimal grid")
        controls = GtkBox(self.Gtk, self.Gtk.Orientation.VERTICAL, 7)
        controls.append(self._control_row(GtkLabel(self.Gtk, "Layout:"), self.design_layout))
        controls.append(
            self._control_row(
                GtkLabel(self.Gtk, "Paper:"),
                self.design_paper,
                GtkLabel(self.Gtk, "Orientation:"),
                self.design_orientation,
            )
        )
        controls.append(self._control_row(GtkLabel(self.Gtk, "Week start:"), self.design_week))
        for row in (
            (self.design_title, self.design_headers),
            (self.design_notes, self.design_lines),
            (self.design_weeks, self.design_fixed, self.design_minimal),
        ):
            controls.append(self._control_row(*row))
        for widget in (
            self.design_layout,
            self.design_paper,
            self.design_orientation,
            self.design_week,
            self.design_title,
            self.design_headers,
            self.design_notes,
            self.design_lines,
            self.design_weeks,
            self.design_fixed,
            self.design_minimal,
        ):
            (
                widget.connect("notify::selected", self._refresh_previews)
                if isinstance(widget, self.Gtk.DropDown)
                else widget.connect("toggled", self._refresh_previews)
            )
        body = self.Gtk.Paned(orientation=self.Gtk.Orientation.HORIZONTAL)
        body.set_position(430)
        body.set_start_child(controls)
        self.designer_preview = self.Gtk.Picture()
        self.designer_preview.set_content_fit(self.Gtk.ContentFit.CONTAIN)
        self.designer_preview.set_size_request(300, 420)
        body.set_end_child(self.designer_preview)
        body.set_vexpand(True)
        page.append(body)
        save = self.Gtk.Button(label="Export SVG…")
        save.connect("clicked", lambda *_: self._choose_save(self._designer_options()))
        page.append(self._control_row(save))

    def _designer_options(self):
        layouts = ("month-grid", "blank-month", "weekly-planner", "notes-calendar")
        return {
            "layout": layouts[self.design_layout.get_selected()],
            "paper": ("a4", "letter")[self.design_paper.get_selected()],
            "orientation": ("portrait", "landscape")[self.design_orientation.get_selected()],
            "week_start": WEEK_STARTS[self.design_week.get_selected()],
            "show_month_title": self.design_title.get_active(),
            "show_weekday_headers": self.design_headers.get_active(),
            "notes_margin": self.design_notes.get_active(),
            "writing_lines": self.design_lines.get_active(),
            "show_week_numbers": self.design_weeks.get_active(),
            "fixed_six_rows": self.design_fixed.get_active(),
            "minimal_grid": self.design_minimal.get_active(),
            "focus_date": (
                self.today
                if (self.year, self.month) == (self.today.year, self.today.month)
                else date(self.year, self.month, 1)
            ),
        }

    def _build_inspector_page(self):
        page = self._page(
            "inspector",
            "Date Inspector",
            "Inspect a civil date, its ISO week, and its position in both month layouts.",
        )
        self.date_picker = self.Gtk.Calendar()
        self.date_picker.connect("day-selected", self._calendar_date_selected)
        page.append(self.date_picker)
        self.inspector_facts = self.Gtk.Label(xalign=0, selectable=True)
        self.inspector_facts.set_wrap(True)
        self.inspector_facts.add_css_class("metric-card")
        page.append(self.inspector_facts)
        self._update_inspector(self.today)

    def _calendar_date_selected(self, calendar_widget):
        if getattr(self, "_inspector_updating", False):
            return
        selected = calendar_widget.get_date()
        self._update_inspector(
            date(selected.get_year(), selected.get_month(), selected.get_day_of_month())
        )

    def _update_inspector(self, day: date):
        if not hasattr(self, "inspector_facts"):
            return
        facts = inspect_date(day)
        text = (
            "%s, %s\nDay of year: %d · ISO week: %d-W%02d · Quarter: Q%d\n"
            "Month %d has %d days · Leap year: %s\n"
            "Days remaining: %d in month, %d in year\n"
            "Natural grid row: %d Monday-first · %d Sunday-first"
            % (
                day.strftime("%A, %B %d, %Y"),
                day.isoformat(),
                facts["day_of_year"],
                facts["iso_week_year"],
                facts["iso_week"],
                facts["quarter"],
                day.month,
                facts["days_in_month"],
                "yes" if facts["is_leap_year"] else "no",
                facts["days_remaining_in_month"],
                facts["days_remaining_in_year"],
                facts["monday_first_row"],
                facts["sunday_first_row"],
            )
        )
        self.inspector_facts.set_text(text)
        if not getattr(self, "_inspector_updating", False):
            self._inspector_updating = True
            selected = self.GLib.DateTime.new_local(day.year, day.month, day.day, 12, 0, 0)
            self.date_picker.select_day(selected)
            self._inspector_updating = False

    def _build_print_page(self):
        page = self._page(
            "print", "Print Studio", "Export a clean, print-sized SVG for A4 or US Letter paper."
        )
        self.print_month_label = self.Gtk.Label(label="", xalign=0)
        page.append(self.print_month_label)
        self.print_preview = self.Gtk.Picture()
        self.print_preview.set_content_fit(self.Gtk.ContentFit.CONTAIN)
        self.print_preview.set_size_request(380, 480)
        self.print_preview.set_vexpand(True)
        page.append(self.print_preview)
        controls = self._control_row(
            self.Gtk.Button(label="Previous Month"),
            self.Gtk.Button(label="Today"),
            self.Gtk.Button(label="Next Month"),
            self.Gtk.Button(label="Export SVG…"),
        )
        children = []
        child = controls.get_first_child()
        while child is not None:
            children.append(child)
            child = child.get_next_sibling()
        children[0].connect("clicked", lambda *_: self._move_month(-1))
        children[1].connect(
            "clicked", lambda *_: self._set_month(self.today.year, self.today.month)
        )
        children[2].connect("clicked", lambda *_: self._move_month(1))
        children[3].connect(
            "clicked",
            lambda *_: self._choose_save(
                {
                    "layout": "month-grid",
                    "paper": "a4",
                    "orientation": "portrait",
                    "week_start": self._current_start(),
                }
            ),
        )
        page.append(controls)

    def _build_lab_page(self):
        page = self._page(
            "lab",
            "Calendar Lab",
            "Run geometry checks and inspect leap-year, century, and rollover fixtures.",
        )
        self.lab_year = self._spin_year(2027)
        self.lab_month = _drop_down(self.Gtk, MONTH_NAMES)
        self.lab_month.set_selected(1)
        self.lab_result = self.Gtk.Label(xalign=0, yalign=0, selectable=True)
        self.lab_result.set_wrap(True)
        self.lab_result.set_vexpand(True)
        self.lab_result.add_css_class("metric-card")
        run = self.Gtk.Button(label="Run year checks")
        run.connect("clicked", self._run_lab)
        page.append(
            self._control_row(
                GtkLabel(self.Gtk, "Year:"),
                self.lab_year,
                GtkLabel(self.Gtk, "Month:"),
                self.lab_month,
                run,
            )
        )
        preset_row = self.Gtk.FlowBox()
        preset_row.set_selection_mode(self.Gtk.SelectionMode.NONE)
        for label, year, month in PRESETS:
            button = self.Gtk.Button(label=label)
            button.connect("clicked", lambda _button, y=year, m=month: self._set_lab_fixture(y, m))
            preset_row.insert(button, -1)
        page.append(preset_row)
        scroll = self.Gtk.ScrolledWindow()
        scroll.set_child(self.lab_result)
        scroll.set_vexpand(True)
        page.append(scroll)
        self._run_lab()

    def _set_lab_fixture(self, year: int, month: int):
        self.lab_year.set_value(year)
        self.lab_month.set_selected(month - 1)
        self._run_lab()

    def _run_lab(self, *_):
        if not hasattr(self, "lab_result"):
            return
        year = self.lab_year.get_value_as_int()
        month = self.lab_month.get_selected() + 1
        lines = ["%s %d" % (MONTH_NAMES[month - 1], year)]
        year_checks = validate_year(year)
        lines.append(
            "Full-year invariants: %s (%d checks)"
            % ("PASS" if all(year_checks.values()) else "FAIL", len(year_checks))
        )
        for start in WeekStart:
            geometry = month_geometry(year, month, start)
            checks = validate_month(year, month, start)
            status = "PASS" if all(checks.values()) else "FAIL"
            first = date(year, month, 1).strftime("%A")
            lines.extend(
                [
                    "",
                    "%s-first: %s" % (start.value.title(), status),
                    "  First weekday: %s · days: %d · leading cells: %d"
                    % (first, geometry.days, geometry.leading_cells),
                    "  Natural rows: %d · grid size: %d"
                    % (geometry.natural_rows, geometry.grid_size),
                ]
            )
            lines.extend(
                "  %s: %s" % (name.replace("_", " "), "PASS" if passed else "FAIL")
                for name, passed in checks.items()
            )
        try:
            next_year, next_month = move_month(year, month, 1)
            lines.extend(["", "Next month: %s %d" % (MONTH_NAMES[next_month - 1], next_year)])
            if month == 12:
                lines.append(
                    "December-to-January rollover: PASS"
                    if next_month == 1 and next_year == year + 1
                    else "December-to-January rollover: FAIL"
                )
        except ValueError:
            lines.extend(["", "Next month: outside supported year range"])
        self.lab_result.set_text("\n".join(lines))

    def _build_resources_page(self):
        page = self._page(
            "resources",
            "Resources",
            "Optional online Beta Calendars pages. The app never loads a resource unless you open it.",
        )
        groups = (
            ("Official Site", (("Beta Calendars", "https://www.betacalendars.com/"),)),
            (
                "Monthly Calendars",
                (
                    ("Monthly Calendar", "https://www.betacalendars.com/monthly-calendar"),
                    ("Blank Calendar", "https://www.betacalendars.com/blank-calendar"),
                ),
            ),
            (
                "Planning Templates",
                (
                    ("Monthly Planner", "https://www.betacalendars.com/monthly-planner"),
                    *(
                        (
                            month + " Calendar",
                            "https://www.betacalendars.com/" + month.lower() + "-calendar.html",
                        )
                        for month in MONTH_NAMES
                    ),
                ),
            ),
        )
        for heading_text, links in groups:
            heading = self.Gtk.Label(label=heading_text, xalign=0)
            heading.add_css_class("heading")
            page.append(heading)
            list_box = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=4)
            for label, uri in links:
                link = self.Gtk.LinkButton.new_with_label(uri, label)
                link.set_halign(self.Gtk.Align.START)
                list_box.append(link)
            page.append(list_box)

    def _build_about_page(self):
        page = self._page(
            "about", "About", "Offline calendar calculations and print layouts for Linux."
        )
        details = self.Gtk.Label(
            label=(
                "Beta Calendars Studio %s\n\n"
                "Calendar arithmetic, month grids, ISO-week inspection, diagnostics, and SVG layout generation run locally.\n\n"
                "The app does not require an account and does not send personal calendar data, analytics, or telemetry. Online resources open only after you choose a link.\n\n"
                "License: MIT"
            )
            % __version__,
            xalign=0,
            yalign=0,
            wrap=True,
        )
        page.append(details)

    def _refresh_previews(self, *_):
        if not hasattr(self, "designer_preview"):
            return
        options = self._designer_options()
        svg = render_month_svg(self.year, self.month, **options)
        self._set_svg_picture(self.designer_preview, svg)
        self._update_print_preview()

    def _update_print_preview(self):
        if not hasattr(self, "print_preview"):
            return
        svg = render_month_svg(self.year, self.month, week_start=self._current_start())
        self._set_svg_picture(self.print_preview, svg)
        self.print_month_label.set_text("%s %d" % (MONTH_NAMES[self.month - 1], self.year))

    def _set_svg_picture(self, picture, svg: str):
        self._preview_counter += 1
        path = Path(tempfile.gettempdir()) / (
            "betacalendars-preview-%d.svg" % self._preview_counter
        )
        path.write_text(svg, encoding="utf-8")
        picture.set_filename(str(path))

    def _choose_save(self, options):
        dialog = self.Gtk.FileDialog()
        dialog.set_title("Export calendar SVG")
        dialog.set_initial_name("calendar.svg")
        dialog.save(self.window, None, self._save_finished, options)

    def _save_finished(self, dialog, result, options):
        try:
            destination = dialog.save_finish(result)
        except self.Gio.Error:
            return
        path = destination.get_path()
        if not path:
            return
        svg = render_month_svg(self.year, self.month, **options)
        Path(path).write_text(svg, encoding="utf-8")

    def _refresh_all(self):
        self._refresh_month()
        self._refresh_year()
        self._refresh_previews()
        self._run_lab()

    def present(self):
        self.window.present()


def GtkLabel(Gtk, text: str):
    return Gtk.Label(label=text)


def GtkBox(Gtk, orientation, spacing: int):
    return Gtk.Box(orientation=orientation, spacing=spacing)


def main(argv: Optional[Sequence[str]] = None) -> int:
    Gio, GLib, Gtk = _gtk()
    parser = argparse.ArgumentParser(prog="betacalendars-studio")
    parser.add_argument(
        "--page",
        choices=("calendar", "year", "designer", "inspector", "print", "lab", "resources", "about"),
        default="calendar",
        help="open directly to a view",
    )
    args = parser.parse_args(argv)
    app = Gtk.Application(
        application_id="com.betacalendars.Studio",
        flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
    )
    holders = []

    def activate(application):
        if not holders:
            holders.append(StudioWindow(application, Gio, GLib, Gtk))
            holders[0].stack.set_visible_child_name(args.page)
        holders[0].present()

    app.connect("activate", activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
