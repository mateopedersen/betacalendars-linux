"""Dependency-free, print-sized SVG calendar layouts."""

from datetime import date
from html import escape
from typing import List, Optional, Tuple

from .calendar_engine import WeekStart, month_geometry, month_grid

PAPER_SIZES = {
    "a4": (595.28, 841.89),
    "letter": (612.0, 792.0),
}
LAYOUTS = ("month-grid", "blank-month", "weekly-planner", "notes-calendar")


def _page_size(paper: str, orientation: str) -> Tuple[float, float]:
    key = paper.lower()
    if key not in PAPER_SIZES:
        raise ValueError("paper must be a4 or letter")
    width, height = PAPER_SIZES[key]
    if orientation == "landscape":
        return height, width
    if orientation != "portrait":
        raise ValueError("orientation must be portrait or landscape")
    return width, height


def render_month_svg(
    year: int,
    month: int,
    week_start: WeekStart = WeekStart.MONDAY,
    paper: str = "a4",
    orientation: str = "portrait",
    layout: str = "month-grid",
    show_month_title: bool = True,
    show_weekday_headers: bool = True,
    notes_margin: bool = False,
    writing_lines: bool = False,
    show_week_numbers: bool = False,
    fixed_six_rows: bool = False,
    minimal_grid: bool = False,
    focus_date: Optional[date] = None,
) -> str:
    """Create an SVG suitable for printing on A4 or US Letter paper."""
    if layout not in LAYOUTS:
        raise ValueError("layout must be one of: " + ", ".join(LAYOUTS))
    width, height = _page_size(paper, orientation)
    normalized = fixed_six_rows or layout == "weekly-planner"
    geometry = month_geometry(year, month, week_start)
    rows = month_grid(year, month, week_start, True, normalized)
    if layout == "weekly-planner" and focus_date is not None:
        if (focus_date.year, focus_date.month) != (year, month):
            raise ValueError("focus_date must be inside the displayed month")
        focus_row = (geometry.leading_cells + focus_date.day - 1) // 7
        rows = rows[focus_row : focus_row + 1]
    row_count = len(rows)

    margin = 34.0
    notes_width = 112.0 if notes_margin else 0.0
    week_column = 32.0 if show_week_numbers else 0.0
    usable_width = width - margin * 2 - notes_width - (12.0 if notes_margin else 0.0)
    grid_x = margin
    grid_width = usable_width - week_column
    col_width = grid_width / 7.0
    title_height = 38.0 if show_month_title else 12.0
    header_height = 30.0 if show_weekday_headers else 0.0
    grid_y = margin + title_height + header_height
    grid_bottom = height - margin
    grid_height = grid_bottom - grid_y
    row_height = grid_height / row_count
    line_color = "#c8d2e0" if not minimal_grid else "#e7ebf0"
    text_color = "#1e293b"
    muted_color = "#8a94a4"
    parts: List[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fpt" height="%.2fpt" viewBox="0 0 %.2f %.2f" role="img">'
        % (width, height, width, height),
        "<title>%s %d calendar</title>" % (escape(date(year, month, 1).strftime("%B")), year),
        "<desc>Printable %s calendar using a %s-first week on %s paper.</desc>"
        % (escape(layout.replace("-", " ")), week_start.value, paper.upper()),
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    if show_month_title:
        parts.append(
            '<text x="%.2f" y="%.2f" fill="%s" font-family="sans-serif" font-size="25" font-weight="700">%s %d</text>'
            % (margin, margin + 27, text_color, escape(date(year, month, 1).strftime("%B")), year)
        )
    if show_weekday_headers:
        for index, label in enumerate(week_start.labels):
            x = grid_x + week_column + col_width * (index + 0.5)
            parts.append(
                '<text x="%.2f" y="%.2f" text-anchor="middle" fill="#526174" font-family="sans-serif" font-size="10" font-weight="700">%s</text>'
                % (x, grid_y - 9, label)
            )

    grid_x2 = grid_x + week_column
    if show_week_numbers:
        parts.append(
            '<text x="%.2f" y="%.2f" text-anchor="middle" fill="#667085" font-family="sans-serif" font-size="8" font-weight="700">WK</text>'
            % (grid_x + week_column / 2, grid_y - 9)
        )

    for row_index, row in enumerate(rows):
        top = grid_y + row_index * row_height
        bottom = top + row_height
        if show_week_numbers:
            visible = [item for item in row if item is not None]
            week_date = visible[0] if visible else date(year, month, 1)
            iso_week = week_date.isocalendar()[1]
            parts.append(
                '<text x="%.2f" y="%.2f" text-anchor="middle" fill="#667085" font-family="sans-serif" font-size="9">%02d</text>'
                % (grid_x + week_column / 2, top + 16, iso_week)
            )
        parts.append(
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%.2f"/>'
            % (
                grid_x,
                top,
                grid_x + week_column + grid_width,
                top,
                line_color,
                0.55 if minimal_grid else 0.9,
            )
        )
        for column_index, cell in enumerate(row):
            x = grid_x2 + col_width * column_index
            parts.append(
                '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%.2f"/>'
                % (x, top, x, bottom, line_color, 0.55 if minimal_grid else 0.9)
            )
            if cell is None:
                continue
            is_current = cell.month == month
            is_blank = layout == "blank-month"
            if not is_blank:
                parts.append(
                    '<text x="%.2f" y="%.2f" fill="%s" font-family="sans-serif" font-size="10" font-weight="%s">%d</text>'
                    % (
                        x + 7,
                        top + 16,
                        text_color if is_current else muted_color,
                        "600" if is_current else "400",
                        cell.day,
                    )
                )
            if writing_lines or layout in ("weekly-planner", "notes-calendar"):
                line_start = top + 27.0
                line_gap = 13.5 if row_height > 64 else 9.5
                count = max(0, int((row_height - 7 - line_start + top) / line_gap))
                for line_index in range(count):
                    line_y = line_start + line_index * line_gap
                    parts.append(
                        '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#e5eaf0" stroke-width="0.5"/>'
                        % (x + 7, line_y, x + col_width - 7, line_y)
                    )
        parts.append(
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%.2f"/>'
            % (
                grid_x + week_column + grid_width,
                top,
                grid_x + week_column + grid_width,
                bottom,
                line_color,
                0.55 if minimal_grid else 0.9,
            )
        )
    parts.append(
        '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%.2f"/>'
        % (
            grid_x,
            grid_bottom,
            grid_x + week_column + grid_width,
            grid_bottom,
            line_color,
            0.55 if minimal_grid else 0.9,
        )
    )

    if notes_margin:
        notes_x = grid_x + week_column + grid_width + 12
        notes_top = grid_y
        notes_bottom = grid_bottom
        parts.append(
            '<text x="%.2f" y="%.2f" fill="#526174" font-family="sans-serif" font-size="10" font-weight="700">NOTES</text>'
            % (notes_x, notes_top - 9)
        )
        parts.append(
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%.2f"/>'
            % (notes_x, notes_top, notes_x, notes_bottom, line_color, 0.7)
        )
        if writing_lines or layout == "notes-calendar":
            line_y = notes_top + 22
            while line_y < notes_bottom:
                parts.append(
                    '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#e5eaf0" stroke-width="0.5"/>'
                    % (notes_x + 8, line_y, width - margin, line_y)
                )
                line_y += 22

    parts.append("</svg>")
    return "\n".join(parts)
