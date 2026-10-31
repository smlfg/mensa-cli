"""Canteen-Liste laden, cachen und lokal durchsuchen."""

from __future__ import annotations

import os
from typing import Iterable

from .client import OpenMensaClient
from .config import load_cache, save_cache
from .models import Canteen


def _normalize(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def search(canteens: Iterable[Canteen], query: str) -> list[Canteen]:
    needle = _normalize(query)
    if not needle:
        return []
    return [
        canteen
        for canteen in canteens
        if needle in _normalize(canteen.name)
        or needle in _normalize(canteen.city)
        or needle in _normalize(canteen.address)
    ]


def by_id(canteens: Iterable[Canteen], canteen_id: int) -> Canteen | None:
    for canteen in canteens:
        if canteen.id == canteen_id:
            return canteen
    return None


def load_canteens(
    client: OpenMensaClient, env: dict[str, str] | None = None
) -> list[Canteen]:
    values = os.environ if env is None else env
    cached = load_cache(values, base_url=client.base_url)
    if cached is not None:
        return cached
    canteens = client.canteens()
    save_cache(canteens, values, base_url=client.base_url)
    return canteens
