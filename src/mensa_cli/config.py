"""Lokale Konfiguration und Cache mit sicheren Rechten."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .models import Canteen

DEFAULT_CANTEEN_ID = 277
CACHE_TTL_SECONDS = 24 * 60 * 60


def _home(env: dict[str, str]) -> Path:
    return Path(env.get("HOME") or Path.home())


def config_path(env: dict[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    base = values.get("XDG_CONFIG_HOME")
    root = Path(base) if base else _home(values) / ".config"
    return root / "mensa-cli" / "config.json"


def cache_path(env: dict[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    base = values.get("XDG_CACHE_HOME")
    root = Path(base) if base else _home(values) / ".cache"
    return root / "mensa-cli" / "canteens.json"


def load_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    path = config_path(env)
    if not path.exists():
        return {"canteen_id": DEFAULT_CANTEEN_ID, "name": ""}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(
            f"Konfiguration nicht lesbar: {path}.",
            "Datei prüfen oder mit `mensa standard MENSA-NAME` neu schreiben.",
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Konfiguration ist kein gültiges JSON: {path}.",
            "Datei prüfen oder mit `mensa standard MENSA-NAME` neu schreiben.",
        ) from exc
    if not isinstance(data, dict):
        raise ConfigError(
            f"Konfiguration hat ein unerwartetes Format: {path}.",
            "Datei prüfen oder mit `mensa standard MENSA-NAME` neu schreiben.",
        )
    try:
        canteen_id = int(data.get("canteen_id", DEFAULT_CANTEEN_ID))
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            f"Konfiguration enthält keine gültige canteen_id: {path}.",
            "Datei prüfen oder mit `mensa standard MENSA-NAME` neu schreiben.",
        ) from exc
    return {"canteen_id": canteen_id, "name": str(data.get("name") or "")}


def _atomic_write(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        fd, temporary = tempfile.mkstemp(prefix=".config-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError as exc:
        raise ConfigError(
            f"Konfiguration konnte nicht geschrieben werden: {path}.",
            "Schreibrechte für das Config-Verzeichnis prüfen.",
        ) from exc


def save_config(canteen: Canteen, env: dict[str, str] | None = None) -> Path:
    path = config_path(env)
    text = json.dumps(
        {"canteen_id": canteen.id, "name": canteen.name},
        ensure_ascii=False,
        indent=2,
    )
    _atomic_write(path, text + "\n")
    return path


def load_cache(
    env: dict[str, str] | None = None, base_url: str | None = None
) -> list[Canteen] | None:
    path = cache_path(env)
    try:
        if not path.is_file():
            return None
        if time.time() - path.stat().st_mtime > CACHE_TTL_SECONDS:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if base_url is not None and data.get("base_url") not in (None, base_url):
        return None
    entries = data.get("canteens")
    if not isinstance(entries, list):
        return None
    try:
        return [Canteen.from_api(entry) for entry in entries]
    except Exception:
        return None


def save_cache(
    canteens: list[Canteen],
    env: dict[str, str] | None = None,
    base_url: str | None = None,
) -> None:
    path = cache_path(env)
    payload = {
        "base_url": base_url,
        "fetched_at": int(time.time()),
        "canteens": [canteen.to_dict() for canteen in canteens],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".cache-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError:
        return
