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
from .config import load_config, save_config
from .dates import format_date, parse_date, today, week_bounds, week_dates
from .errors import MensaError, UsageError
from .filters import FilterSpec, parse_max_price
from .formatting import header_lines, meal_line, plan_body_lines
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

    morgen = subparsers.add_parser(
        "morgen", help="Speiseplan für morgen", description="Speiseplan für morgen."
    )
    _add_mensa_arg(morgen)
    _add_filter_args(morgen)
    _add_json_arg(morgen)
    morgen.set_defaults(handler=cmd_morgen)

    woche = subparsers.add_parser(
        "woche",
        help="Speiseplan von Montag bis Sonntag",
        description="Speiseplan von Montag bis Sonntag.",
    )
    _add_mensa_arg(woche)
    _add_filter_args(woche)
    _add_json_arg(woche)
    woche.set_defaults(handler=cmd_woche)

    tag = subparsers.add_parser(
        "tag",
        help="Speiseplan für einen einzelnen Tag",
        description="Speiseplan für einen einzelnen Tag.",
    )
    tag.add_argument(
        "datum",
        metavar="DATUM",
        help="heute, morgen, Wochentag, JJJJ-MM-TT oder TT.MM.JJJJ",
    )
    _add_mensa_arg(tag)
    _add_filter_args(tag)
    _add_json_arg(tag)
    tag.set_defaults(handler=cmd_tag)

    suche = subparsers.add_parser(
        "suche",
        help="Mensen nach Stadt oder Name suchen",
        description="Mensen nach Stadt oder Name suchen.",
    )
    suche.add_argument(
        "suchbegriff",
        metavar="SUCHBEGRIFF",
        help="Teilstring in Name, Stadt oder Adresse",
    )
    _add_json_arg(suche)
    suche.set_defaults(handler=cmd_suche)

    gericht = subparsers.add_parser(
        "gericht",
        help="kommende Tage nach einem Gericht durchsuchen",
        description="Die nächsten 7 Tage nach einem Gericht durchsuchen.",
    )
    gericht.add_argument(
        "stichwort", metavar="STICHWORT", help="Teilstring im Gericht, Kategorie oder Hinweis"
    )
    gericht.add_argument(
        "--mensa",
        metavar="MENSA-NAME",
        help="Mensa per Name, Stadt oder Adresse (sonst Standard-Mensa)",
    )
    _add_filter_args(gericht)
    _add_json_arg(gericht)
    gericht.set_defaults(handler=cmd_gericht)

    standard = subparsers.add_parser(
        "standard",
        help="Standard-Mensa lokal speichern",
        description="Eine Mensa als Standard-Mensa speichern.",
    )
    standard.add_argument(
        "mensa",
        metavar="MENSA-NAME",
        help="Mensa per Name, Stadt oder Adresse",
    )
    _add_json_arg(standard)
    standard.set_defaults(handler=cmd_standard)

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
        sys.stderr.write("Mehrere Mensen gefunden:\n")
        for line in _numbered_lines(matches):
            sys.stderr.write(line + "\n")
        raise UsageError(
            f"Mehrere Mensen passen zu {name!r}.",
            "Einen genaueren Namen angeben; `mensa suche SUCHBEGRIFF` listet die Treffer.",
            {"candidates": [canteen.to_dict() for canteen in matches]},
        )
    config = load_config(env)
    canteen_id = int(config["canteen_id"])
    known = by_id(canteens, canteen_id)
    if known is not None:
        return known
    stored_name = str(config.get("name") or f"Mensa {canteen_id}")
    raise UsageError(
        f"Unbekannte Mensa in der Konfiguration: {stored_name} ({canteen_id}).",
        "`mensa suche SUCHBEGRIFF` ausprobieren oder mit "
        "`mensa standard MENSA-NAME` eine andere Mensa speichern.",
    )


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


def cmd_morgen(args: argparse.Namespace) -> int:
    return _run_day(args, today() + _dt.timedelta(days=1))


def cmd_standard(args: argparse.Namespace) -> int:
    env = os.environ
    with OpenMensaClient(env.get("MENSA_BASE_URL")) as client:
        canteens = _load_canteens(client)
        canteen = _resolve_canteen(args.mensa, canteens, env)
    path = save_config(canteen, env)
    if _is_json(args):
        _print_json(
            {
                "standard": {"id": canteen.id, "name": canteen.name},
                "config_path": str(path),
            }
        )
        return 0
    _print_lines([f"Standard-Mensa gespeichert: {canteen.name} ({canteen.id})"])
    return 0


def cmd_gericht(args: argparse.Namespace) -> int:
    from .filters import apply

    spec = _filter_spec(args)
    env = os.environ
    base = today()
    days = [base + _dt.timedelta(days=offset) for offset in range(7)]
    query = args.stichwort
    needle = query.casefold()
    with OpenMensaClient(env.get("MENSA_BASE_URL")) as client:
        canteens = _load_canteens(client)
        canteen = _resolve_canteen(args.mensa, canteens, env)
        plans = [(day, client.day(canteen.id, day.isoformat())) for day in days]
    matches: list[tuple[_dt.date, object]] = []
    for day, plan in plans:
        if plan.closed or plan.no_plan:
            continue
        for meal in apply(plan.meals, spec):
            haystack = " ".join([meal.name, meal.category, *meal.notes]).casefold()
            if needle in haystack:
                matches.append((day, meal))
    if _is_json(args):
        _print_json(
            {
                "query": query,
                "canteen": canteen.to_dict(),
                "days": 7,
                "filter": spec.to_dict(),
                "matches": [
                    {
                        "date": day.isoformat(),
                        "weekday": format_date(day).split(",", 1)[0],
                        "canteen": canteen.to_dict(),
                        "meal": meal.to_dict(),
                    }
                    for day, meal in matches
                ],
            }
        )
        return 0
    if not matches:
        _print_lines(
            [f'Keine Treffer für "{query}" in den nächsten 7 Tagen.']
        )
        return 0
    lines = [f'Treffer für "{query}" ({len(matches)}):']
    for day, meal in matches:
        lines.append(f"  {format_date(day)} – {canteen.name} ({canteen.id})")
        lines.append(f"    {meal_line(meal).lstrip()}")
    _print_lines(lines)
    return 0


def cmd_suche(args: argparse.Namespace) -> int:
    env = os.environ
    with OpenMensaClient(env.get("MENSA_BASE_URL")) as client:
        canteens = _load_canteens(client)
    results = search(canteens, args.suchbegriff)
    if _is_json(args):
        _print_json(
            {
                "query": args.suchbegriff,
                "results": [canteen.to_dict() for canteen in results],
            }
        )
        return 0
    if not results:
        _print_lines(["Keine Mensen gefunden."])
        return 0
    lines = [f"Mensen gefunden ({len(results)}):"]
    for index, canteen in enumerate(results, start=1):
        suffix = f" – {canteen.address}" if canteen.address else ""
        lines.append(f"  {index}) {canteen.name} ({canteen.id}){suffix}")
    _print_lines(lines)
    return 0


def cmd_tag(args: argparse.Namespace) -> int:
    day = parse_date(args.datum, today())
    return _run_day(args, day)


def cmd_woche(args: argparse.Namespace) -> int:
    spec = _filter_spec(args)
    env = os.environ
    base = today()
    days = week_dates(base)
    with OpenMensaClient(env.get("MENSA_BASE_URL")) as client:
        canteens = _load_canteens(client)
        canteen = _resolve_canteen(getattr(args, "mensa", None), canteens, env)
        plans = [(day, client.day(canteen.id, day.isoformat())) for day in days]
    start, end = week_bounds(base)
    if _is_json(args):
        from .filters import apply

        _print_json(
            {
                "canteen": canteen.to_dict(),
                "week": {"start": start.isoformat(), "end": end.isoformat()},
                "filter": spec.to_dict(),
                "days": [
                    {
                        "date": day.isoformat(),
                        "weekday": format_date(day).split(",", 1)[0],
                        "closed": plan.closed,
                        "no_plan": plan.no_plan,
                        "meals": [
                            meal.to_dict()
                            for meal in (
                                apply(plan.meals, spec)
                                if not (plan.closed or plan.no_plan)
                                else []
                            )
                        ],
                    }
                    for day, plan in plans
                ],
            }
        )
        return 0
    lines = [
        f"Mensa: {canteen.name} ({canteen.id})",
        f"Woche: {format_date(start)} – {format_date(end)}",
    ]
    for day, plan in plans:
        lines.append(f"## {format_date(day)}")
        lines.extend(plan_body_lines(plan, spec))
    _print_lines(lines)
    return 0


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
