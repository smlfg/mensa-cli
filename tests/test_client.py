from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from mensa_cli.client import OpenMensaClient, normalize_base_url
from mensa_cli.errors import AuthError, SourceError
from mensa_cli.models import Canteen, Meal

FIXTURES = Path(__file__).parent / "fixtures" / "ux"


def _response(
    payload: Any,
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = (
        payload
        if isinstance(payload, bytes)
        else json.dumps(payload).encode("utf-8")
    )
    response.headers.update(headers or {})
    return response


class FakeSession:
    def __init__(self, responses: dict[tuple[str, str], Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, object] | None]] = []

    def get(self, url: str, params=None, timeout=None, headers=None):
        self.calls.append((url, "GET", params))
        path = "/" + url.split("/", 3)[3] if "://" in url else url
        page = (params or {}).get("page")
        key = (path, str(page)) if page is not None else (path, "")
        if key not in self.responses:
            return _response({"error": "not found"}, status=404)
        return self.responses[key]

    def close(self) -> None:
        return None


def _client(session: FakeSession) -> OpenMensaClient:
    return OpenMensaClient(base_url="http://127.0.0.1:1", session=session)


def test_pagination_und_canteen_parser() -> None:
    session = FakeSession(
        {
            ("/canteens", "1"): _response(
                json.loads((FIXTURES / "canteens_page1.json").read_text())
            ),
            ("/canteens", "2"): _response([]),
        }
    )
    canteens = _client(session).canteens()
    assert [canteen.id for canteen in canteens] == [1, 2, 277, 278]
    assert canteens[2] == Canteen(
        id=277,
        name="Heilbronn, Mensa Bildungscampus/Europaplatz",
        city="Heilbronn",
        address="Bildungscampus 8, 74076 Heilbronn",
    )
    assert [call[2]["page"] for call in session.calls] == [1, 2]


def test_meals_parser_gegen_fixture() -> None:
    data = json.loads(
        (FIXTURES / "meals_277_2026-11-02.json").read_text(encoding="utf-8")
    )
    meals = [Meal.from_api(entry) for entry in data]
    assert len(meals) == 9
    assert meals[0].id == 29313650
    assert meals[0].prices["students"] == 0.9
    assert meals[0].prices["pupils"] is None
    assert meals[0].notes == ["Pudding Creme mit Streusel"]


def test_geschlossener_tag_ohne_meals_request() -> None:
    session = FakeSession(
        {
            ("/canteens/277/days/2026-11-01", ""): _response(
                {"date": "2026-11-01", "closed": True}
            )
        }
    )
    plan = _client(session).day(277, "2026-11-01")
    assert plan.closed is True
    assert plan.meals == ()
    assert len(session.calls) == 1


def test_tag_ausserhalb_ist_kein_plan() -> None:
    session = FakeSession({})
    plan = _client(session).day(277, "2026-12-24")
    assert plan.no_plan is True
    assert plan.closed is False


def test_offener_tag_laedt_meals() -> None:
    session = FakeSession(
        {
            ("/canteens/277/days/2026-11-02", ""): _response(
                {"date": "2026-11-02", "closed": False}
            ),
            ("/canteens/277/days/2026-11-02/meals", ""): _response(
                json.loads((FIXTURES / "meals_277_2026-11-02.json").read_text())
            ),
        }
    )
    plan = _client(session).day(277, "2026-11-02")
    assert plan.closed is False
    assert len(plan.meals) == 9


@pytest.mark.parametrize(
    ("status", "error"),
    [(401, AuthError), (403, AuthError), (500, SourceError), (418, SourceError)],
)
def test_http_fehlerklassen(status: int, error: type[Exception]) -> None:
    session = FakeSession({("/canteens", "1"): _response({}, status=status)})
    with pytest.raises(error) as excinfo:
        _client(session).canteens()
    assert getattr(excinfo.value, "exit_code") in (3, 4)


def test_kaputtes_json_ist_source_error() -> None:
    session = FakeSession({("/canteens", "1"): _response(b"{kaputt")})
    with pytest.raises(SourceError):
        _client(session).canteens()


def test_timeout_ist_source_error() -> None:
    class TimeoutSession(FakeSession):
        def get(self, url, params=None, timeout=None, headers=None):
            raise requests.Timeout("zu spät")

    with pytest.raises(SourceError) as excinfo:
        _client(TimeoutSession({})).canteens()
    assert excinfo.value.exit_code == 3


def test_basis_url_wird_normalisiert_und_validiert() -> None:
    assert normalize_base_url("http://localhost:8000/") == "http://localhost:8000"
    assert normalize_base_url(None).startswith("https://openmensa.org/api/v2")
    with pytest.raises(SourceError):
        normalize_base_url("ftp://example.invalid")
