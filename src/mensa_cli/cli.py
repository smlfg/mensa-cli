"""Kommandozeile für mensa."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from typing import Callable, Sequence

from . import __version__
from .catalog import by_id, load_canteens, search
from .client import OpenMensaClient
from .config import load_config
from .dates import format_date, parse_date, today
from .errors import MensaError, UsageError
from .filters import FilterSpec, parse_max_price
from .formatting import header_lines, plan_body_lines
from .models import Canteen

ROLE_CHOICES = ("studierende", "bedienstete", "gaeste")


class MensaArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise UsageError(message, "`mensa --help` zeigt alle Befehle.")


def build_parser() -> argparse.ArgumentParser:
    parser = MensaArgumentParser(
        prog="mensa",
        description="Speiseplan deutscher Mensen über die OpenMensa-API v2.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="BEFEHL")

    heute = subparsers.add_parser(
        "heute", help="Speiseplan für heute", description="Speiseplan für heute."
    )
    _add_mensa_arg(heute)
    _add_filter_args(heute)
    _add_json_arg(heute)
    heute.set_defaults(handler=cmd_heute)

    return parser


def _add_mensa_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "mensa",
        nargs="?",
        metavar="MENSA-NAME",
        help="Mensa per Name, Stadt oder Adresse (sonst Standard-Mensa)",
    )


def _add_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--vegetarisch",
        action="store_true",
        help="nur vegetarische und vegane Gerichte",
    )
    parser.add_argument(
        "--vegan", action="store_true", help="nur vegane Gerichte"
    )
    parser.add_argument(
        "--max-preis",
        metavar="BETRAG",
        help="höchstens dieser Preis für die gewählte Rolle, z. B. 3,00",
    )
    parser.add_argument(
        "--rolle",
        choices=ROLE_CHOICES,
        default="studierende",
        metavar="ROLLE",
        help="Rolle für --max-preis: studierende, bedienstete oder gaeste",
    )


def _add_json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json", action="store_true", help="genau ein JSON-Objekt ausgeben"
    )


def _filter_spec(args: argparse.Namespace) -> FilterSpec:
    return FilterSpec(
        vegetarian=bool(getattr(args, "vegetarisch", False)),
        vegan=bool(getattr(args, "vegan", False)),
        max_price=parse_max_price(getattr(args, "max_preis", None)),
        role=getattr(args, "rolle", "studierende"),
    )


def _is_json(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False)) or not sys.stdout.isatty()


def _print_json(payload: object) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _print_lines(lines: Sequence[str]) -> None:
    sys.stdout.write("\n".join(lines) + "\n")


def _report_error(error: MensaError, json_mode: bool) -> int:
    if json_mode:
        _print_json(error.as_dict())
    else:
        sys.stderr.write(error.message + "\n")
        if error.next_step:
            sys.stderr.write(f"Nächster Schritt: {error.next_step}\n")
    return error.exit_code


def _load_canteens(client: OpenMensaClient) -> list[Canteen]:
    return load_canteens(client, os.environ)


def _numbered_lines(canteens: Sequence[Canteen]) -> list[str]:
    return [
        f"  {index}) {canteen.name} ({canteen.id})"
        for index, canteen in enumerate(canteens, start=1)
    ]


def _prompt_choice(canteens: Sequence[Canteen]) -> Canteen:
    sys.stderr.write("Mehrere Mensen gefunden:\n")
    for line in _numbered_lines(canteens):
        sys.stderr.write(line + "\n")
    while True:
        sys.stderr.write(f"Auswahl [1-{len(canteens)}]: ")
        sys.stderr.flush()
        answer = sys.stdin.readline()
        if answer == "":
            raise EOFError
        try:
            number = int(answer.strip())
        except ValueError:
            number = 0
        if 1 <= number <= len(canteens):
            return canteens[number - 1]
        sys.stderr.write(f"Bitte eine Zahl zwischen 1 und {len(canteens)} eingeben.\n")


def _resolve_canteen(
    name: str | None, canteens: Sequence[Canteen], env: dict[str, str]
) -> Canteen:
    if name:
        matches = search(canteens, name)
        if not matches:
            raise UsageError(
                f"Keine Mensa gefunden für {name!r}.",
                f"`mensa suche {name}` ausprobieren oder einen anderen Namen angeben.",
            )
        if len(matches) == 1:
            return matches[0]
        if sys.stdin.isatty() and sys.stdout.isatty():
            return _prompt_choice(matches)
        raise UsageError(
            f"Mehrere Mensen passen zu {name!r}.",
            "Einen genaueren Namen angeben; `mensa suche SUCHBEGRIFF` listet die Treffer.",
        )
    config = load_config(env)
    canteen_id = int(config["canteen_id"])
    known = by_id(canteens, canteen_id)
    if known is not None:
        return known
    return Canteen(id=canteen_id, name=str(config.get("name") or f"Mensa {canteen_id}"))


def _day_payload(
    canteen: Canteen, day: _dt.date, plan, spec: FilterSpec
) -> dict[str, object]:
    from .filters import apply

    meals = apply(plan.meals, spec) if not (plan.closed or plan.no_plan) else []
    return {
        "canteen": canteen.to_dict(),
        "date": day.isoformat(),
        "weekday": format_date(day).split(",", 1)[0],
        "closed": plan.closed,
        "no_plan": plan.no_plan,
        "filter": spec.to_dict(),
        "meals": [meal.to_dict() for meal in meals],
    }


def _run_day(args: argparse.Namespace, day: _dt.date) -> int:
    spec = _filter_spec(args)
    env = os.environ
    with OpenMensaClient(env.get("MENSA_BASE_URL")) as client:
        canteens = _load_canteens(client)
        canteen = _resolve_canteen(getattr(args, "mensa", None), canteens, env)
        plan = client.day(canteen.id, day.isoformat())
    if _is_json(args):
        _print_json(_day_payload(canteen, day, plan, spec))
        return 0
    lines = header_lines(canteen, day, spec)
    lines.extend(plan_body_lines(plan, spec))
    _print_lines(lines)
    return 0


def cmd_heute(args: argparse.Namespace) -> int:
    return _run_day(args, today())


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    fallback_json = "--json" in arguments or not sys.stdout.isatty()
    try:
        parser = build_parser()
        try:
            args = parser.parse_args(arguments)
        except UsageError as error:
            return _report_error(error, fallback_json)
        handler: Callable[[argparse.Namespace], int] | None = getattr(
            args, "handler", None
        )
        if handler is None:
            parser.print_help()
            return 0
        return int(handler(args))
    except MensaError as error:
        return _report_error(error, fallback_json)
    except KeyboardInterrupt:
        error = MensaError("Abgebrochen.")
        error.exit_code = 1
        return _report_error(error, fallback_json)
    except EOFError:
        error = UsageError(
            "Eingabe beendet.", "Auswahl im Terminal erneut starten."
        )
        return _report_error(error, fallback_json)
    except BrokenPipeError:
        return 1
    except Exception as error:  # noqa: BLE001 - nie Tracebacks ausgeben
        unexpected = MensaError(
            f"Unerwarteter Fehler ({type(error).__name__}).",
            "Erneut versuchen; bleibt der Fehler, ein Issue im Repo anlegen.",
        )
        unexpected.exit_code = 1
        return _report_error(unexpected, fallback_json)


if __name__ == "__main__":
    sys.exit(main())
