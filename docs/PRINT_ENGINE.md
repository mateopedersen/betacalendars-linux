# Print engine

The SVG renderer works without network access or third-party Python packages. It uses point-sized page dimensions for A4 and US Letter, and produces portrait or landscape output.

The renderer consumes the same month-grid geometry as the GUI and CLI. The optional six-row setting pads the display rows only. It does not change leap-year or month calculations.

The current export format is SVG. Each document includes page dimensions, a title and description, and vector lines and text that remain sharp when printed or scaled. The GTK export dialog uses the desktop file chooser portal so the user selects the destination.

