"""Datenmodelle für Canteens, Tage und Gerichte."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import SourceError


@dataclass(frozen=True)
class Canteen:
    id: int
    name: str
    city: str = ""
    address: str = ""

    @classmethod
    def from_api(cls, data: Any) -> "Canteen":
        if not isinstance(data, dict):
            raise SourceError("Unerwartete Canteen-Antwort der OpenMensa-API.")
        try:
            canteen_id = int(data["id"])
            name = str(data["name"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceError(
                "Canteen-Eintrag ohne gültige ID oder Namen.",
                "Später erneut versuchen; die API liefert unerwartete Daten.",
            ) from exc
        return cls(
            id=canteen_id,
            name=name,
            city=str(data.get("city") or ""),
            address=str(data.get("address") or ""),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "address": self.address,
        }


@dataclass(frozen=True)
class Meal:
    id: int | None
    name: str
    category: str
    prices: dict[str, float | None] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: Any) -> "Meal":
        if not isinstance(data, dict):
            raise SourceError("Unerwarteter Gericht-Eintrag der OpenMensa-API.")
        name = data.get("name")
        if not isinstance(name, str):
            raise SourceError(
                "Gericht ohne Namen in der OpenMensa-Antwort.",
                "Später erneut versuchen; die API liefert unerwartete Daten.",
            )
        raw_id = data.get("id")
        try:
            meal_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            meal_id = None
        raw_prices = data.get("prices")
        prices: dict[str, float | None] = {}
        if isinstance(raw_prices, dict):
            for key, value in raw_prices.items():
                if value is None:
                    prices[str(key)] = None
                    continue
                try:
                    prices[str(key)] = float(value)
                except (TypeError, ValueError):
                    prices[str(key)] = None
        raw_notes = data.get("notes")
        notes = [str(note) for note in raw_notes] if isinstance(raw_notes, list) else []
        return cls(
            id=meal_id,
            name=name,
            category=str(data.get("category") or ""),
            prices=prices,
            notes=notes,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "prices": {
                "students": self.prices.get("students"),
                "employees": self.prices.get("employees"),
                "pupils": self.prices.get("pupils"),
                "others": self.prices.get("others"),
            },
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class DayPlan:
    date: str
    closed: bool = False
    meals: tuple[Meal, ...] = ()
    no_plan: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "closed": self.closed,
            "no_plan": self.no_plan,
            "meals": [meal.to_dict() for meal in self.meals],
        }
