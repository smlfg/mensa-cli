from __future__ import annotations

import json
from pathlib import Path

import pytest

from mensa_cli.errors import UsageError
from mensa_cli.filters import FilterSpec, apply, parse_max_price
from mensa_cli.models import Meal

FIXTURES = Path(__file__).parent / "fixtures" / "ux"


def _meals() -> list[Meal]:
    data = json.loads(
        (FIXTURES / "meals_277_2026-11-02.json").read_text(encoding="utf-8")
    )
    return [Meal.from_api(entry) for entry in data]


def test_vegan_filter_nutzt_kategorie_name_und_hinweise() -> None:
    names = {meal.name for meal in apply(_meals(), FilterSpec(vegan=True))}
    assert names == {
        "Mandelpudding mit Granola",
        "Currywurst vegan mit fruchtiger Tomatensauce und Brot",
        "Gemüsebolognese mit hausgemachter Pasta",
    }


def test_vegetarisch_schliesst_vegan_ein() -> None:
    names = {meal.name for meal in apply(_meals(), FilterSpec(vegetarian=True))}
    assert "Spätzle-Pfanne mit Champignons und Blattspinat" in names
    assert "Gemüsebolognese mit hausgemachter Pasta" in names
    assert "Gebratenes Hechtfilet mit gebackenem Blumenkohl und Dinkelreis" not in names


def test_vegan_ist_strenger_als_vegetarisch() -> None:
    names = {
        meal.name
        for meal in apply(
            _meals(), FilterSpec(vegetarian=True, vegan=True)
        )
    }
    assert "Spätzle-Pfanne mit Champignons und Blattspinat" not in names
    assert "Gemüsebolognese mit hausgemachter Pasta" in names


def test_max_preis_und_rolle() -> None:
    students = apply(_meals(), FilterSpec(max_price=1.0))
    assert {meal.name for meal in students} == {
        "Pudding Creme mit Streusel",
        "Mandelpudding mit Granola",
        "Klare Gemüsebrühe mit Zartweizen",
        "Gebratenes Hechtfilet mit gebackenem Blumenkohl und Dinkelreis",
        "Gemüsebolognese mit hausgemachter Pasta",
    }
    guests = apply(_meals(), FilterSpec(max_price=2.0, role="gaeste"))
    assert "Klare Gemüsebrühe mit Zartweizen" in {meal.name for meal in guests}
    assert "Spätzle-Pfanne mit Champignons und Blattspinat" not in {
        meal.name for meal in guests
    }


def test_fehlender_preis_wird_ausgeschlossen() -> None:
    meal = Meal(
        id=1,
        name="Testgericht",
        category="Vegan",
        prices={"students": None, "employees": 1.0, "pupils": None, "others": 2.0},
        notes=[],
    )
    assert apply([meal], FilterSpec(max_price=5.0)) == []
    assert apply([meal], FilterSpec(max_price=5.0, role="bedienstete")) == [meal]


@pytest.mark.parametrize(("value", "expected"), [("3", 3.0), ("3,00", 3.0), (" 2.5 ", 2.5)])
def test_parse_max_preis(value: str, expected: float) -> None:
    assert parse_max_price(value) == expected


@pytest.mark.parametrize("value", ["", "abc", "-1", "nan", "inf"])
def test_ungueltiger_preis_ist_usage(value: str) -> None:
    with pytest.raises(UsageError):
        parse_max_price(value)
