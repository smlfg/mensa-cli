from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from fake_server import FakeServer  # noqa: E402
from ux_session import PtySession, strip_ansi  # noqa: E402
from ux_spec import parse  # noqa: E402

SPEC = parse(ROOT / "docs" / "UX.md")
PYTHONPATH = os.pathsep.join([str(ROOT / "src"), str(ROOT), str(HARNESS)])


def _env(base: Path, server: FakeServer) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(base),
            "XDG_CONFIG_HOME": str(base / "config"),
            "XDG_CACHE_HOME": str(base / "cache"),
            "MENSA_BASE_URL": server.base_url,
            "MENSA_HEUTE": "2026-11-02",
            "PYTHONPATH": PYTHONPATH,
            "PYTHONUNBUFFERED": "1",
            "NO_COLOR": "1",
            "LANG": "C.UTF-8",
        }
    )
    env.pop("PYTHONHOME", None)
    return env


def _run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mensa_cli", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )


def _pty(args: list[str], env: dict[str, str]) -> tuple[int, str]:
    session = PtySession(
        [sys.executable, "-m", "mensa_cli", *args], env=env, cwd=ROOT
    )
    try:
        code = session.wait_exit(30)
        text = strip_ansi(session.transcript)
    finally:
        session.close()
    return int(code if code is not None else -1), text


def _text(args: list[str], scratch_dir: Path) -> str:
    with FakeServer(SPEC, ROOT) as server:
        code, text = _pty(args, _env(scratch_dir, server))
    assert code == 0, text
    assert "Traceback (most recent call last)" not in text
    return text


def test_woche_text_und_json(scratch_dir: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        env = _env(scratch_dir, server)
        code, text = _pty(["woche"], env)
        as_json = _run(["woche", "--json"], env)
    assert code == 0, text
    assert "Woche: Montag, 02.11.2026 – Sonntag, 08.11.2026" in text
    assert "## Montag, 02.11.2026" in text
    assert "[Vegan] Gemüsebolognese mit hausgemachter Pasta" in text
    assert "## Sonntag, 01.11.2026" not in text
    assert "## Sonntag, 08.11.2026" in text
    assert "Kein Speiseplan veröffentlicht" in text
    data = json.loads(as_json.stdout)
    assert data["week"] == {"start": "2026-11-02", "end": "2026-11-08"}
    assert len(data["days"]) == 7
    monday = data["days"][0]
    assert monday["date"] == "2026-11-02"
    assert any(
        meal["name"] == "Gemüsebolognese mit hausgemachter Pasta"
        for meal in monday["meals"]
    )


def test_woche_geschlossener_sonntag(scratch_dir: Path) -> None:
    text = _text(["tag", "2026-11-01"], scratch_dir)
    assert "Geschlossen – kein Speiseplan veröffentlicht." in text


def test_gericht_findet_und_filtert(scratch_dir: Path) -> None:
    text = _text(["gericht", "Pasta"], scratch_dir)
    assert 'Treffer für "Pasta" (2):' in text
    assert "Gemüsebolognese mit hausgemachter Pasta" in text
    assert "Pasta Bolognese vom Rind" in text


def test_gericht_ohne_treffer_ist_erfolg(scratch_dir: Path) -> None:
    text = _text(["gericht", "Quark"], scratch_dir)
    assert 'Keine Treffer für "Quark" in den nächsten 7 Tagen.' in text


def test_filter_ohne_treffer_ist_erfolg(scratch_dir: Path) -> None:
    text = _text(["heute", "--vegan", "--max-preis", "0,50"], scratch_dir)
    assert "Keine Gerichte für den Filter." in text


def test_max_preis_rolle_filtert_clientseitig(scratch_dir: Path) -> None:
    text = _text(
        ["heute", "--max-preis", "2,00", "--rolle", "gaeste"], scratch_dir
    )
    assert "Gemüsebolognese mit hausgemachter Pasta" in text
    assert "Spätzle-Pfanne" not in text
    assert "Currywurst vegan" not in text


def test_suche_ohne_treffer_ist_erfolg(scratch_dir: Path) -> None:
    text = _text(["suche", "Nirgendwo"], scratch_dir)
    assert "Keine Mensen gefunden." in text


def test_tag_wochentag_und_morgen(scratch_dir: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        env = _env(scratch_dir, server)
        morgen_code, morgen = _pty(["tag", "morgen"], env)
        dienstag_code, dienstag = _pty(["tag", "dienstag"], env)
    assert morgen_code == 0
    assert dienstag_code == 0
    assert "Datum: Dienstag, 03.11.2026" in morgen
    assert "Datum: Dienstag, 03.11.2026" in dienstag


def test_unbekannte_canteen_id_in_config_ist_usage(scratch_dir: Path) -> None:
    config_dir = scratch_dir / "config" / "mensa-cli"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps({"canteen_id": 999999, "name": "Unbekannte Mensa"}),
        encoding="utf-8",
    )
    with FakeServer(SPEC, ROOT) as server:
        result = _run(["heute"], _env(scratch_dir, server))
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["exit_code"] == 2
    assert "unbekannte mensa" in data["error"].casefold()
    assert "mensa suche" in data["next"]
    assert "Traceback (most recent call last)" not in result.stdout
    assert "Traceback (most recent call last)" not in result.stderr
