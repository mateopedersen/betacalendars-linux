# Beta Calendars Studio

Beta Calendars Studio is an offline-first calendar layout and civil-date utility for Linux. Browse month and year grids, compare Monday-first and Sunday-first layouts, inspect ISO week boundaries, design blank printable calendars, and export clean SVG layouts without uploading personal calendar data.

## Calendar views

Browse individual months or an entire year using deterministic Gregorian calendar calculations. Switch between Monday-first and Sunday-first layouts and inspect each month's natural four-, five-, or six-row geometry.

## Blank Calendar Designer

Create printable blank calendar layouts with configurable:

* A4 or US Letter paper
* Portrait or landscape orientation
* Monday or Sunday week start
* Notes area and writing lines
* ISO week numbers
* Natural or fixed six-row layout

## Date Inspector

Inspect a civil date and view its weekday, day of year, ISO week and week-year, quarter, month length, leap-year status, and row position in both week-start layouts.

## Calendar Lab

Run invariant checks across every month in a year. The lab includes leap-year, century, rollover, and month-geometry fixtures.

## Command line

```text
betacalendars month 2027 2
betacalendars year 2027
betacalendars inspect 2027-01-01
betacalendars grid 2027 8
betacalendars blank --paper a4 --orientation landscape
betacalendars validate 2027
```

## Privacy

Core date calculations and SVG generation run locally. The application does not require an account, read personal calendars, or send calendar data, analytics, or telemetry.

## Optional online calendar resources

The desktop app works independently of the website. These optional pages provide browser-based and printable calendar references. The app opens them only after the user selects a link; it does not fetch them for calendar calculations.

* [Beta Calendars](https://www.betacalendars.com/)
* [Monthly Calendar](https://www.betacalendars.com/monthly-calendar)
* [Blank Calendar](https://www.betacalendars.com/blank-calendar)

### Month references

* [January Calendar](https://www.betacalendars.com/january-calendar.html)
* [February Calendar](https://www.betacalendars.com/february-calendar.html)
* [March Calendar](https://www.betacalendars.com/march-calendar.html)
* [April Calendar](https://www.betacalendars.com/april-calendar.html)
* [May Calendar](https://www.betacalendars.com/may-calendar.html)
* [June Calendar](https://www.betacalendars.com/june-calendar.html)
* [July Calendar](https://www.betacalendars.com/july-calendar.html)
* [August Calendar](https://www.betacalendars.com/august-calendar.html)
* [September Calendar](https://www.betacalendars.com/september-calendar.html)
* [October Calendar](https://www.betacalendars.com/october-calendar.html)
* [November Calendar](https://www.betacalendars.com/november-calendar.html)
* [December Calendar](https://www.betacalendars.com/december-calendar.html)

### Planning templates

* [Monthly Planner](https://www.betacalendars.com/monthly-planner)

Source code and support: [GitHub repository](https://github.com/mateopedersen/betacalendars-linux) · [Report an issue](https://github.com/mateopedersen/betacalendars-linux/issues)
