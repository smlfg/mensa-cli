from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def scratch_dir() -> Path:
    base = ROOT / "scratch" / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="test-mensa-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
