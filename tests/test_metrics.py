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
    assert overview["team_draft_slots"]
    assert {row["slot"] for row in overview["team_draft_slots"]} <= {1, 2, 3, 4, 5}
    assert overview["trend"]
    assert matchups["items"][0]["role_name"] == "打野"
    assert teammates["items"]
    assert builds["items"][0]["item_name"]
    assert builds["items"][0]["usage_rate"] == 100
    assert " · " in runes["items"][0]["rune_set"]
    assert runes["items"][0]["rune_count"] == 30
    assert runes["items"][0]["rune_level"] == 150
    assert runes["items"][0]["usage_rate"] == 100


def test_player_combinations_and_integrity_audit(warehouse):
    metrics = MetricsService(warehouse)
    player = metrics.player_overview("10005:钟意")
    combinations = metrics.combinations(min_games=1)
    triples = metrics.combinations(min_games=1, size=3)
    win_sorted = metrics.combinations(min_games=1, sort_by="win_rate")
    duo_ids = [
        combinations["items"][0]["hero1_id"],
        combinations["items"][0]["hero2_id"],
    ]
    exact_duo = metrics.combinations(min_games=1, hero_ids=duo_ids)
    triple_ids = [
        triples["items"][0]["hero1_id"],
        triples["items"][0]["hero2_id"],
        triples["items"][0]["hero3_id"],
    ]
    exact_triple = metrics.combinations(min_games=1, size=3, hero_ids=triple_ids)
    focus_hero_id = combinations["items"][0]["hero1_id"]
    focused_duos = metrics.combinations(min_games=1, hero_id=focus_hero_id)
    focused_trios = metrics.combinations(min_games=1, size=3, hero_id=focus_hero_id)
    battles = metrics.recent_battles(hero_id=531)
    detail = metrics.battle_detail(battles["items"][0]["battle_id"])
    audit = audit_warehouse(warehouse)

    assert player["summary"]["player_name"] == "钟意"
    assert player["heroes"]
    assert combinations["items"]
    assert triples["items"]
    assert exact_duo["items"][0]["games"] == combinations["items"][0]["games"]
    assert exact_triple["items"][0]["games"] == triples["items"][0]["games"]
    assert 0 <= exact_triple["items"][0]["appearance_rate"] <= 100
    assert [(row["win_rate"], row["games"]) for row in win_sorted["items"]] == sorted(
        [(row["win_rate"], row["games"]) for row in win_sorted["items"]],
        reverse=True,
    )
    assert all(
        focus_hero_id in {row["hero1_id"], row["hero2_id"]}
        for row in focused_duos["items"]
    )
    assert all(
        focus_hero_id in {row["hero1_id"], row["hero2_id"], row["hero3_id"]}
        for row in focused_trios["items"]
    )
    assert len(detail["players"]) == 10
    assert sum(action["action_type"] == "pick" for action in detail["draft"]) == 10
    assert detail["players"][0]["items"]
    assert detail["players"][0]["runes"]
    assert audit["ok"] is True
    assert all(check["failures"] == 0 for check in audit["checks"])


def test_league_and_role_scope(warehouse):
    metrics = MetricsService(warehouse)

    leagues = metrics.leagues()
    junglers = metrics.heroes(role="打野", league_id="demo-kpl")
    missing = metrics.hero_overview(531, league_id="missing-league")

    assert leagues[0]["league_id"] == "demo-kpl"
    assert leagues[0]["battles"] == 18
    assert junglers
    assert all("打野" in hero["roles"] for hero in junglers)
    assert missing["sample_size"] == 0
