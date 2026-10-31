"""HTTP-Client für die OpenMensa-API v2."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import requests

from . import __version__
from .errors import AuthError, SourceError
from .models import Canteen, DayPlan, Meal

DEFAULT_BASE_URL = "https://openmensa.org/api/v2"
DEFAULT_TIMEOUT = 15.0
USER_AGENT = f"mensa-cli/{__version__} (+https://github.com/smlfg/mensa-cli)"


def normalize_base_url(value: str | None) -> str:
    base = (value or DEFAULT_BASE_URL).strip()
    if not base:
        base = DEFAULT_BASE_URL
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise SourceError(
            f"MENSA_BASE_URL ist keine gültige http(s)-URL: {base!r}.",
            "MENSA_BASE_URL auf eine gültige URL setzen oder entfernen.",
        )
    return base.rstrip("/")


class OpenMensaClient:
    """Nur lesende GET-Anfragen mit klaren Fehlerklassen."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.session = session or requests.Session()
        self._owns_session = session is None

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> "OpenMensaClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _get_json(
        self,
        path: str,
        params: dict[str, object] | None = None,
        *,
        allow_404: bool = False,
    ) -> tuple[Any, requests.structures.CaseInsensitiveDict[str]] | None:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            )
        except requests.Timeout as exc:
            raise SourceError(
                "Zeitüberschreitung beim Abruf der OpenMensa-API.",
                "Später erneut versuchen oder MENSA_BASE_URL prüfen.",
            ) from exc
        except requests.RequestException as exc:
            raise SourceError(
                f"Netzwerkfehler beim Abruf der OpenMensa-API ({type(exc).__name__}).",
                "Internetverbindung und MENSA_BASE_URL prüfen und später erneut versuchen.",
            ) from exc
        if response.status_code in (401, 403):
            raise AuthError(
                f"Die OpenMensa-API verlangt Login oder Zustimmung (HTTP {response.status_code})."
            )
        if response.status_code == 404:
            if allow_404:
                return None
            raise SourceError(
                "Die OpenMensa-API meldet HTTP 404 für die angefragte Ressource.",
                "Mensa-Name prüfen oder mit `mensa suche SUCHBEGRIFF` suchen.",
            )
        if response.status_code >= 500:
            raise SourceError(
                f"Die OpenMensa-API meldet HTTP {response.status_code}.",
                "Später erneut versuchen.",
            )
        if response.status_code != 200:
            raise SourceError(
                f"Unerwarteter HTTP-Status der OpenMensa-API: {response.status_code}.",
                "Später erneut versuchen oder OpenMensa informieren.",
            )
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise SourceError(
                "Die OpenMensa-API liefert kein gültiges JSON.",
                "Später erneut versuchen.",
            ) from exc
        return data, response.headers

    def canteens(self) -> list[Canteen]:
        result: list[Canteen] = []
        page = 1
        while page <= 1000:
            payload = self._get_json("/canteens", {"page": page})
            assert payload is not None
            data, headers = payload
            if not isinstance(data, list):
                raise SourceError(
                    "Unerwartete Antwort der OpenMensa-API für /canteens.",
                    "Später erneut versuchen.",
                )
            if not data:
                break
            for entry in data:
                result.append(Canteen.from_api(entry))
            total = headers.get("X-Total-Pages") if headers else None
            if total:
                try:
                    if page >= int(total):
                        break
                except ValueError:
                    pass
            page += 1
        return result

    def day(self, canteen_id: int, date: str) -> DayPlan:
        payload = self._get_json(
            f"/canteens/{canteen_id}/days/{date}", allow_404=True
        )
        if payload is None:
            return DayPlan(date=date, no_plan=True)
        data, _ = payload
        if not isinstance(data, dict):
            raise SourceError(
                "Unerwartete Antwort der OpenMensa-API für einen Tagesplan.",
                "Später erneut versuchen.",
            )
        if bool(data.get("closed")):
            return DayPlan(date=date, closed=True)
        meals_payload = self._get_json(
            f"/canteens/{canteen_id}/days/{date}/meals", allow_404=True
        )
        if meals_payload is None:
            return DayPlan(date=date, no_plan=True)
        meals_data, _ = meals_payload
        if not isinstance(meals_data, list):
            raise SourceError(
                "Unerwartete Antwort der OpenMensa-API für Gerichte.",
                "Später erneut versuchen.",
            )
        meals = tuple(Meal.from_api(entry) for entry in meals_data)
        return DayPlan(date=date, meals=meals)
