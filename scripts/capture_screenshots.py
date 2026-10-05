"""Capture genuine screenshots of the GTK application for the Snap listing."""

import argparse
from datetime import date
from pathlib import Path

from betacalendars_studio.gui import StudioWindow, _gtk


def capture(output: Path) -> None:
    Gio, GLib, Gtk = _gtk()
    app = Gtk.Application(
        application_id="com.betacalendars.Studio.Screenshot",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    state = {"window": None, "page": "calendar"}

    def activate(application):
        if state["window"] is None:
            window = StudioWindow(application, Gio, GLib, Gtk)
            state["window"] = window
            window.window.set_default_size(1280, 900)
            window._set_month(2027, 2)
            window._updating = True
            window.calendar_week_dropdown.set_selected(0)
            window.year_view_spin.set_value(2027)
            window.year_view_week_dropdown.set_selected(0)
            window.design_paper.set_selected(0)
            window.design_orientation.set_selected(1)
            window._updating = False
            window._refresh_all()
        state["window"].stack.set_visible_child_name(state["page"])
        state["window"].present()

    def render_to_png(window, destination: Path):
        native = window.window.get_native()
        renderer = native.get_renderer()
        paintable = Gtk.WidgetPaintable.new(window.window)
        snapshot = Gtk.Snapshot.new()
        paintable.snapshot(snapshot, window.window.get_width(), window.window.get_height())
        node = snapshot.to_node()
        texture = renderer.render_texture(node, None)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not texture.save_to_png(str(destination)):
            raise RuntimeError("GTK could not save screenshot: %s" % destination)

    fixtures = (
        ("01-month-february-2027.png", "calendar"),
        ("02-year-2027.png", "year"),
        ("03-blank-designer.png", "designer"),
        ("04-date-inspector.png", "inspector"),
        ("05-calendar-lab.png", "lab"),
    )
    index = {"value": 0}

    def select_fixture():
        window = state["window"]
        filename, page = fixtures[index["value"]]
        if page == "inspector":
            window._update_inspector(date(2027, 1, 1))
        elif page == "lab":
            window.lab_year.set_value(2027)
            window.lab_month.set_selected(7)
            window._run_lab()
        state["page"] = page
        window.stack.set_visible_child_name(page)
        GLib.timeout_add(450, capture_current, filename)
        return GLib.SOURCE_REMOVE

    def capture_current(filename):
        window = state["window"]
        render_to_png(window, output / filename)
        index["value"] += 1
        if index["value"] == len(fixtures):
            app.quit()
            return GLib.SOURCE_REMOVE
        GLib.timeout_add(350, select_fixture)
        return GLib.SOURCE_REMOVE

    def activate_and_schedule(application):
        activate(application)
        GLib.timeout_add(700, select_fixture)

    app.connect("activate", activate_and_schedule)
    app.run(None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
