from __future__ import annotations

import datetime as dt

import pytest

from mensa_cli.dates import format_date, parse_date, today, week_dates
from mensa_cli.errors import UsageError

BASE = dt.date(2026, 11, 2)


def test_relative_und_iso_und_deutsch() -> None:
    assert parse_date("heute", BASE) == BASE
    assert parse_date("MORGEN", BASE) == dt.date(2026, 11, 3)
    assert parse_date("2026-11-08", BASE) == dt.date(2026, 11, 8)
    assert parse_date("08.11.2026", BASE) == dt.date(2026, 11, 8)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("montag", dt.date(2026, 11, 2)),
        ("dienstag", dt.date(2026, 11, 3)),
        ("sonntag", dt.date(2026, 11, 8)),
        ("Montag", dt.date(2026, 11, 2)),
    ],
)
def test_wochentag_ist_naechster_termin_ab_heute(name: str, expected: dt.date) -> None:
    assert parse_date(name, BASE) == expected


@pytest.mark.parametrize("value", ["", "31.02.2026", "2026-13-01", "irgendwann"])
def test_ungueltiges_datum_ist_usage(value: str) -> None:
    with pytest.raises(UsageError) as excinfo:
        parse_date(value, BASE)
    assert excinfo.value.exit_code == 2


def test_format_date_deutsch() -> None:
    assert format_date(BASE) == "Montag, 02.11.2026"


def test_woche_montag_bis_sonntag() -> None:
    days = week_dates(dt.date(2026, 11, 4))
    assert days[0] == dt.date(2026, 11, 2)
    assert days[-1] == dt.date(2026, 11, 8)


def test_mensa_heute_override_und_fehler() -> None:
    assert today({"MENSA_HEUTE": "2026-11-02"}) == BASE
    with pytest.raises(UsageError):
        today({"MENSA_HEUTE": "02.11.2026"})
