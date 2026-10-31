"""Datumsformate und deutsche Wochentage."""

from __future__ import annotations

import datetime as _dt
import os

from .errors import UsageError

WEEKDAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]

WEEKDAY_ALIASES = {
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonnabend": 5,
    "sonntag": 6,
}


def weekday_name(day: _dt.date) -> str:
    return WEEKDAYS[day.weekday()]


def today(environ: dict[str, str] | None = None) -> _dt.date:
    env = os.environ if environ is None else environ
    override = (env.get("MENSA_HEUTE") or "").strip()
    if not override:
        return _dt.date.today()
    try:
        return _dt.date.fromisoformat(override)
    except ValueError as exc:
        raise UsageError(
            f"MENSA_HEUTE ist kein gültiges Datum: {override!r}.",
            "MENSA_HEUTE als JJJJ-MM-TT setzen oder entfernen.",
        ) from exc


def parse_date(text: str, base: _dt.date) -> _dt.date:
    value = (text or "").strip()
    lowered = value.casefold()
    if lowered == "heute":
        return base
    if lowered == "morgen":
        return base + _dt.timedelta(days=1)
    if lowered in WEEKDAY_ALIASES:
        target = WEEKDAY_ALIASES[lowered]
        delta = (target - base.weekday()) % 7
        return base + _dt.timedelta(days=delta)
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return _dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise UsageError(
        f"Ungültiges Datum: {text!r}.",
        "Datum als heute, morgen, Wochentag, JJJJ-MM-TT oder TT.MM.JJJJ angeben.",
    )


def format_date(day: _dt.date) -> str:
    return f"{weekday_name(day)}, {day.strftime('%d.%m.%Y')}"


def week_bounds(day: _dt.date) -> tuple[_dt.date, _dt.date]:
    start = day - _dt.timedelta(days=day.weekday())
    return start, start + _dt.timedelta(days=6)


def week_dates(day: _dt.date) -> list[_dt.date]:
    start, _ = week_bounds(day)
    return [start + _dt.timedelta(days=offset) for offset in range(7)]
