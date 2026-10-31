"""Lesbare Textausgabe."""

from __future__ import annotations

import datetime as _dt

from .dates import format_date
from .filters import FilterSpec, apply
from .models import Canteen, DayPlan, Meal

CLOSED_MESSAGE = "Geschlossen – kein Speiseplan veröffentlicht."
NO_PLAN_MESSAGE = (
    "Kein Speiseplan veröffentlicht (Datum außerhalb des veröffentlichten Zeitraums)."
)
NO_MEALS_MESSAGE = "Kein Speiseplan veröffentlicht."
NO_FILTER_MATCHES = "Keine Gerichte für den Filter."


def format_price(value: float | None) -> str:
    if value is None:
        return "–"
    return f"{value:.2f}".replace(".", ",")


def meal_line(meal: Meal) -> str:
    category = meal.category or "?"
    prices = " / ".join(
        format_price(meal.prices.get(key))
        for key in ("students", "employees", "others")
    )
    return f"  [{category}] {meal.name} — {prices} EUR"


def header_lines(canteen: Canteen, day: _dt.date, spec: FilterSpec) -> list[str]:
    lines = [
        f"Mensa: {canteen.name} ({canteen.id})",
        f"Datum: {format_date(day)}",
        "Preise: Studierende / Bedienstete / Gäste (EUR)",
    ]
    if spec.active:
        lines.append(f"Filter: {spec.description()}")
    return lines


def plan_body_lines(plan: DayPlan, spec: FilterSpec) -> list[str]:
    if plan.no_plan:
        return [NO_PLAN_MESSAGE]
    if plan.closed:
        return [CLOSED_MESSAGE]
    meals = apply(plan.meals, spec)
    if not meals:
        return [NO_FILTER_MATCHES if spec.active else NO_MEALS_MESSAGE]
    return [meal_line(meal) for meal in meals]
