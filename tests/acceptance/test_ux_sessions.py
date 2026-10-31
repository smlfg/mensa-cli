"""Akzeptanztests aus den Sitzungen in docs/UX.md.

Das Tool läuft als Subprozess gegen tests/harness/fake_server.py. Die
Sitzungen aus der Spec werden im PTY gefahren, damit die menschliche
Textausgabe geprüft wird. Der JSON-Pfad wird zusätzlich über eine Pipe
getestet. Fehlt der Code noch, sind diese Tests absichtlich rot.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from fake_server import FakeServer  # noqa: E402
from ux_session import PtySession, strip_ansi  # noqa: E402
from ux_spec import parse  # noqa: E402

SPEC = parse(ROOT / "docs" / "UX.md")
HEUTE = str((SPEC.meta.get("env") or {}).get("MENSA_HEUTE", "2026-11-02"))
PYTHONPATH = os.pathsep.join([str(ROOT / "src"), str(ROOT), str(HARNESS)])


@pytest.fixture()
def home() -> Path:
    base = ROOT / "scratch" / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="accept-mensa-", dir=base))
    for relative in (".config", ".cache", ".local/share", ".local/state"):
        (path / relative).mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def _env(server: FakeServer, home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            "MENSA_BASE_URL": server.base_url,
            "MENSA_HEUTE": HEUTE,
            "PYTHONPATH": PYTHONPATH,
            "PYTHONUNBUFFERED": "1",
            "TERM": "xterm",
            "LANG": "C.UTF-8",
            "NO_COLOR": "1",
            "ACCEPTANCE_SANDBOX": "1",
            "ACCEPTANCE_NET_LOG": str(home / "net.log"),
        }
    )
    env.pop("PYTHONHOME", None)
    return env


def _command(*args: str) -> list[str]:
    return [sys.executable, "-m", "mensa_cli", *args]


def _run_pty(args: list[str], env: dict[str, str], timeout: float = 30.0) -> tuple[int, str]:
    proc = PtySession(_command(*args), env=env, cwd=ROOT)
    try:
        code = proc.wait_exit(timeout)
        text = strip_ansi(proc.transcript)
    finally:
        proc.close()
    return int(code if code is not None else -1), text


def _run_pty_answer(
    args: list[str],
    env: dict[str, str],
    prompt: str,
    answer: str,
    timeout: float = 30.0,
) -> tuple[int, str]:
    proc = PtySession(_command(*args), env=env, cwd=ROOT)
    try:
        found = proc.expect(prompt, timeout=timeout)
        text = strip_ansi(proc.transcript)
        assert found, f"Prompt {prompt!r} nicht gefunden. Bisher:\n{text}"
        proc.send_line(answer)
        code = proc.wait_exit(timeout)
        text = strip_ansi(proc.transcript)
    finally:
        proc.close()
    return int(code if code is not None else -1), text


def _run_pipe(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        _command(*args),
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )


def _assert_ausgabe(code: int, text: str, expected: list[str]) -> None:
    assert code == 0, text
    for line in expected:
        assert line in text, f"fehlt: {line!r}\nAusgabe:\n{text}"


def test_session_installation_und_erster_speiseplan(home: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        code, text = _run_pty(["heute"], _env(server, home))
    _assert_ausgabe(
        code,
        text,
        [
            "Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)",
            "Datum: Montag, 02.11.2026",
            "Preise: Studierende / Bedienstete / Gäste (EUR)",
            "[Dessert] Pudding Creme mit Streusel — 0,90 / 1,40 / 2,00 EUR",
            "[Vegan] Gemüsebolognese mit hausgemachter Pasta — 0,99 / 1,35 / 2,00 EUR",
        ],
    )


def test_session_mensen_suchen(home: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        code, text = _run_pty(["suche", "Heilbronn"], _env(server, home))
    _assert_ausgabe(
        code,
        text,
        [
            "Mensen gefunden (2):",
            "1) Heilbronn, Mensa Bildungscampus/Europaplatz (277) – Bildungscampus 8, 74076 Heilbronn",
            "2) Heilbronn, Mensa Sontheim (278) – Max-Planck-Straße 39, 74081 Heilbronn",
        ],
    )


def test_session_heute_mit_filter(home: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        code, text = _run_pty(["heute", "Bildungscampus", "--vegan"], _env(server, home))
    _assert_ausgabe(
        code,
        text,
        [
            "Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)",
            "Datum: Montag, 02.11.2026",
            "Filter: vegan",
            "[Dessert vegan] Mandelpudding mit Granola — 0,90 / 1,40 / 2,00 EUR",
            "[Foodtruck] Currywurst vegan mit fruchtiger Tomatensauce und Brot — 2,60 / 3,10 / 4,70 EUR",
            "[Vegan] Gemüsebolognese mit hausgemachter Pasta — 0,99 / 1,35 / 2,00 EUR",
        ],
    )
    assert "vom Kalb" not in text
    assert "Pommes Frites" not in text


def test_session_mehrere_treffer_auswahl(home: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        code, text = _run_pty_answer(
            ["morgen", "Heilbronn"],
            _env(server, home),
            "Auswahl [1-2]:",
            "1",
        )
    _assert_ausgabe(
        code,
        text,
        [
            "Mehrere Mensen gefunden:",
            "1) Heilbronn, Mensa Bildungscampus/Europaplatz (277)",
            "2) Heilbronn, Mensa Sontheim (278)",
            "Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)",
            "Datum: Dienstag, 03.11.2026",
        ],
    )


def test_session_standard_mensa_speichern(home: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        env = _env(server, home)
        code, text = _run_pty(["standard", "Bildungscampus"], env)
        _assert_ausgabe(
            code,
            text,
            ["Standard-Mensa gespeichert: Heilbronn, Mensa Bildungscampus/Europaplatz (277)"],
        )
        config = home / ".config" / "mensa-cli" / "config.json"
        assert config.is_file(), f"Config fehlt: {config}"
        data = json.loads(config.read_text(encoding="utf-8"))
        assert data["canteen_id"] == 277
        assert stat.S_IMODE(config.stat().st_mode) == 0o600
        code, text = _run_pty(["heute"], env)
    _assert_ausgabe(code, text, ["Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)"])


def test_session_geschlossener_tag(home: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        code, text = _run_pty(["tag", "2026-11-01"], _env(server, home))
    _assert_ausgabe(
        code,
        text,
        [
            "Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)",
            "Datum: Sonntag, 01.11.2026",
            "Geschlossen – kein Speiseplan veröffentlicht.",
        ],
    )


def test_heute_json_bei_pipe(home: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        result = _run_pipe(["heute", "--json"], _env(server, home))
    assert result.returncode == 0, result.stderr or result.stdout
    data = json.loads(result.stdout)
    assert data["date"] == HEUTE
    assert data["closed"] is False
    assert data["canteen"]["id"] == 277
    names = {meal["name"] for meal in data["meals"]}
    assert "Gemüsebolognese mit hausgemachter Pasta" in names
