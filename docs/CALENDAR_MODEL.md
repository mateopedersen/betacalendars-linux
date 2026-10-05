# Calendar model

## Date range

The engine accepts Gregorian years 1 through 9999 and months 1 through 12. A date is a civil day represented by year, month, and day. No timezone or instant is involved.

## Leap years

A year is leap when it is divisible by 400, or divisible by 4 but not by 100. This makes 1900, 2027, and 2100 common years; 2000, 2028, and 2400 are leap years.

## Month geometry

Python's weekday numbering is used: Monday is 0 and Sunday is 6. For `W`, the weekday of the first day, and `S`, the configured week start:

```text
leadingCells = (W - S + 7) mod 7
naturalRows  = ceil((leadingCells + daysInMonth) / 7)
```

The geometry result reports natural rows. A six-row grid can be requested from `month_grid` for display or print consistency; this only pads the presentation rows.

## ISO week boundaries

`inspect_date` reports both the ISO week number and ISO week-based year. These can differ from the civil year. For example, 2021-01-01 is in ISO week 53 of ISO year 2020.

