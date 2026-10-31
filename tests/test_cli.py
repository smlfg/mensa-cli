from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from mensa_cli.cli import _prompt_choice
from mensa_cli.models import Canteen

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from fake_server import FakeServer  # noqa: E402
from ux_spec import parse  # noqa: E402

SPEC = parse(ROOT / "docs" / "UX.md")
PYTHONPATH = os.pathsep.join([str(ROOT / "src"), str(ROOT), str(HARNESS)])


def _env(base: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(base),
            "XDG_CONFIG_HOME": str(base / "config"),
            "XDG_CACHE_HOME": str(base / "cache"),
            "PYTHONPATH": PYTHONPATH,
            "PYTHONUNBUFFERED": "1",
            "NO_COLOR": "1",
            "LANG": "C.UTF-8",
        }
    )
    env.update(extra)
    env.pop("PYTHONHOME", None)
    return env


def _run(
    args: list[str], env: dict[str, str], timeout: float = 20.0
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mensa_cli", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )


def _assert_kein_traceback(result: subprocess.CompletedProcess[str]) -> None:
    assert "Traceback (most recent call last)" not in result.stdout
    assert "Traceback (most recent call last)" not in result.stderr


def test_version_und_help_mit_exit_null(scratch_dir: Path) -> None:
    env = _env(scratch_dir)
    for args in (
        ["--version"],
        ["--help"],
        [],
        ["heute", "--help"],
        ["morgen", "--help"],
        ["woche", "--help"],
        ["tag", "--help"],
        ["suche", "--help"],
        ["gericht", "--help"],
        ["standard", "--help"],
    ):
        result = _run(args, env)
        assert result.returncode == 0, (args, result.stderr)
        assert result.stdout.strip(), args
        _assert_kein_traceback(result)
    version = _run(["--version"], env)
    assert "mensa 0.1.0" in version.stdout


def test_ungueltiges_datum_ist_json_fehler(scratch_dir: Path) -> None:
    result = _run(["tag", "32.13.2026"], _env(scratch_dir))
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["exit_code"] == 2
    assert data["next"]
    _assert_kein_traceback(result)


def test_ungueltiges_mensa_heute_ist_usage(scratch_dir: Path) -> None:
    result = _run(["heute"], _env(scratch_dir, MENSA_HEUTE="02.11.2026"))
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["exit_code"] == 2
    assert "MENSA_HEUTE" in data["error"]
    _assert_kein_traceback(result)


def test_unbekannter_befehl_ist_usage_ohne_traceback(scratch_dir: Path) -> None:
    result = _run(["quatsch"], _env(scratch_dir))
    assert result.returncode == 2
    assert json.loads(result.stdout)["exit_code"] == 2
    _assert_kein_traceback(result)


def test_mehrere_treffer_ohne_tty_liste_und_exit_2(scratch_dir: Path) -> None:
    with FakeServer(SPEC, ROOT) as server:
        result = _run(
            ["heute", "Heilbronn"],
            _env(scratch_dir, MENSA_BASE_URL=server.base_url, MENSA_HEUTE="2026-11-02"),
        )
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["exit_code"] == 2
    assert [entry["id"] for entry in data["candidates"]] == [277, 278]
    assert "1) Heilbronn, Mensa Bildungscampus/Europaplatz (277)" in result.stderr
    _assert_kein_traceback(result)


def test_netzfehler_exit_3_ohne_traceback(scratch_dir: Path) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = _env(
        scratch_dir,
        MENSA_BASE_URL=f"http://127.0.0.1:{port}/api/v2",
        MENSA_HEUTE="2026-11-02",
    )
    result = _run(["heute"], env)
    assert result.returncode == 3
    assert json.loads(result.stdout)["exit_code"] == 3
    _assert_kein_traceback(result)


def test_prompt_wiederholt_bei_ungueltiger_eingabe(monkeypatch) -> None:
    import io

    canteens = [
        Canteen(id=277, name="Heilbronn, Mensa Bildungscampus/Europaplatz"),
        Canteen(id=278, name="Heilbronn, Mensa Sontheim"),
    ]
    monkeypatch.setattr(sys, "stdin", io.StringIO("abc\n0\n2\n"))
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    assert _prompt_choice(canteens).id == 278


def test_prompt_bei_eof_ist_eof(monkeypatch) -> None:
    import io

    import pytest

    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    with pytest.raises(EOFError):
        _prompt_choice([Canteen(id=277, name="Heilbronn")])
