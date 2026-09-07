from __future__ import annotations

from pathlib import Path

import pytest


def pytest_configure(config: Any) -> None:
    config.option.asyncio_mode = "auto"


@pytest.fixture
def tmp_routes_file(tmp_path: Path) -> Path:
    return tmp_path / "saved_routes.json"
