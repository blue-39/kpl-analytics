from __future__ import annotations

from kpl_analytics.warehouse.audit import audit_warehouse
from kpl_analytics.warehouse.metrics import MetricsService


def test_hero_metrics_cover_requested_dimensions(warehouse):
    metrics = MetricsService(warehouse)

    overview = metrics.hero_overview(531)
    matchups = metrics.hero_matchups(531)
    teammates = metrics.hero_teammates(531)
    builds = metrics.hero_builds(531)
    runes = metrics.hero_runes(531)

    assert overview["summary"]["hero_name"] == "镜"
    assert 0 <= overview["summary"]["win_rate"] <= 100
    assert overview["summary"]["picks"] == overview["sample_size"]
    assert overview["draft_slots"]
    assert overview["trend"]
    assert matchups["items"][0]["role_name"] == "打野"
    assert teammates["items"]
    assert "→" in builds["items"][0]["build"]
    assert runes["items"][0]["usage_rate"] == 100


def test_player_combinations_and_integrity_audit(warehouse):
    metrics = MetricsService(warehouse)
    player = metrics.player_overview("10005:钟意")
    combinations = metrics.combinations(min_games=1)
    battles = metrics.recent_battles(hero_id=531)
    detail = metrics.battle_detail(battles["items"][0]["battle_id"])
    audit = audit_warehouse(warehouse)

    assert player["summary"]["player_name"] == "钟意"
    assert player["heroes"]
    assert combinations["items"]
    assert len(detail["players"]) == 10
    assert sum(action["action_type"] == "pick" for action in detail["draft"]) == 10
    assert detail["players"][0]["items"]
    assert detail["players"][0]["runes"]
    assert audit["ok"] is True
    assert all(check["failures"] == 0 for check in audit["checks"])
