"""Clientseitige Filter für Gerichte."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import UsageError
from .models import Meal

ROLE_TO_PRICE = {
    "studierende": "students",
    "bedienstete": "employees",
    "gaeste": "others",
}


@dataclass(frozen=True)
class FilterSpec:
    vegetarian: bool = False
    vegan: bool = False
    max_price: float | None = None
    role: str = "studierende"

    @property
    def active(self) -> bool:
        return self.vegetarian or self.vegan or self.max_price is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "vegan": self.vegan,
            "vegetarian": self.vegetarian,
            "max_price": self.max_price,
            "role": self.role,
        }

    def description(self) -> str:
        parts: list[str] = []
        if self.vegan:
            parts.append("vegan")
        elif self.vegetarian:
            parts.append("vegetarisch")
        if self.max_price is not None:
            parts.append(
                f"max {self.max_price:.2f}".replace(".", ",")
                + f" EUR ({self.role.capitalize()})"
            )
        return ", ".join(parts)


def parse_max_price(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip().replace(",", ".")
    if not text:
        raise UsageError(
            "Leerer Preis bei --max-preis.",
            "Betrag angeben, z. B. --max-preis 3,00.",
        )
    try:
        parsed = float(text)
    except ValueError as exc:
        raise UsageError(
            f"Ungültiger Preis: {value!r}.",
            "Betrag mit Punkt oder Komma angeben, z. B. --max-preis 3,00.",
        ) from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise UsageError(
            f"Ungültiger Preis: {value!r}.",
            "Einen nicht-negativen endlichen Betrag angeben.",
        )
    return parsed


def _haystack(meal: Meal) -> str:
    return " ".join([meal.category, meal.name, *meal.notes]).casefold()


def matches(meal: Meal, spec: FilterSpec) -> bool:
    text = _haystack(meal)
    if spec.vegan:
        if "vegan" not in text:
            return False
    elif spec.vegetarian:
        if "vegan" not in text and "vegetarisch" not in text:
            return False
    if spec.max_price is not None:
        price = meal.prices.get(ROLE_TO_PRICE.get(spec.role, "students"))
        if price is None or price > spec.max_price:
            return False
    return True


def apply(meals: tuple[Meal, ...] | list[Meal], spec: FilterSpec) -> list[Meal]:
    return [meal for meal in meals if matches(meal, spec)]
