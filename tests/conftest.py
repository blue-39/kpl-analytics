from __future__ import annotations

import pytest

from kpl_analytics.config import Settings
from kpl_analytics.warehouse.database import Warehouse
from kpl_analytics.warehouse.demo import seed_demo


@pytest.fixture
def warehouse(tmp_path):
    instance = Warehouse(Settings(data_dir=tmp_path / "data"))
    seed_demo(instance, battle_count=18)
    return instance
