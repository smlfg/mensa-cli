from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from mensa_cli.config import (
    DEFAULT_CANTEEN_ID,
    cache_path,
    config_path,
    load_cache,
    load_config,
    save_cache,
    save_config,
)
from mensa_cli.errors import ConfigError
from mensa_cli.models import Canteen

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ux"


def _env(base: Path) -> dict[str, str]:
    return {
        "HOME": str(base),
        "XDG_CONFIG_HOME": str(base / "config"),
        "XDG_CACHE_HOME": str(base / "cache"),
    }


def test_fehlende_config_liefert_heilbronn(scratch_dir: Path) -> None:
    config = load_config(_env(scratch_dir))
    assert config["canteen_id"] == DEFAULT_CANTEEN_ID
    assert config_path(_env(scratch_dir)).name == "config.json"


def test_standard_wird_atomar_mit_0600_gespeichert(scratch_dir: Path) -> None:
    env = _env(scratch_dir)
    canteen = Canteen(id=277, name="Heilbronn, Mensa Bildungscampus/Europaplatz")
    path = save_config(canteen, env)
    assert path == config_path(env)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text(encoding="utf-8"))["canteen_id"] == 277
    assert load_config(env)["name"] == canteen.name


def test_kaputte_config_ist_lokaler_fehler(scratch_dir: Path) -> None:
    env = _env(scratch_dir)
    path = config_path(env)
    path.parent.mkdir(parents=True)
    path.write_text("{kaputt", encoding="utf-8")
    with pytest.raises(ConfigError) as excinfo:
        load_config(env)
    assert excinfo.value.exit_code == 1
    assert "mensa standard" in (excinfo.value.next_step or "")


def test_cache_speichert_und_liest_canteens(scratch_dir: Path) -> None:
    env = _env(scratch_dir)
    data = json.loads((FIXTURES / "canteens_page1.json").read_text(encoding="utf-8"))
    canteens = [Canteen.from_api(entry) for entry in data]
    save_cache(canteens, env, base_url="http://example.invalid/api/v2")
    loaded = load_cache(env, base_url="http://example.invalid/api/v2")
    assert loaded == canteens
    assert cache_path(env).is_file()
    assert load_cache(env, base_url="http://other.invalid") is None


def test_kaputter_cache_wird_ignoriert(scratch_dir: Path) -> None:
    env = _env(scratch_dir)
    path = cache_path(env)
    path.parent.mkdir(parents=True)
    path.write_text("kein json", encoding="utf-8")
    assert load_cache(env) is None
