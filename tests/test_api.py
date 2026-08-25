from __future__ import annotations

from fastapi.testclient import TestClient

from kpl_analytics.api.main import create_app


def test_api_serves_dashboard_and_natural_language_query(warehouse):
    app = create_app(warehouse.settings)
    with TestClient(app) as client:
        health = client.get("/api/health")
        leagues = client.get("/api/leagues")
        heroes = client.get("/api/heroes")
        overview = client.get("/api/heroes/531/overview?league_id=demo-kpl&role=打野")
        invalid_dates = client.get(
            "/api/heroes/531/overview?start_date=2026-01-01&end_date=2025-01-01"
        )
        player = client.get("/api/players/10005%3A钟意/overview")
        trio = client.get("/api/combinations?size=3&min_games=1")
        focused_combos = client.get(
            "/api/combinations?size=2&hero_id=531&sort_by=win_rate&min_games=1"
        )
        invalid_combo_sort = client.get("/api/combinations?sort_by=unknown")
        battle_list = client.get("/api/battles?hero_id=531")
        query = client.post("/api/query", json={"question": "镜的出装统计"})
        battle = client.get(f"/api/battles/{battle_list.json()['items'][0]['battle_id']}")

    assert health.status_code == 200
    assert leagues.json()[0]["league_name"] == "KPL 本地演示赛季"
    assert heroes.status_code == 200
    assert any(row["hero_name"] == "镜" for row in heroes.json())
    assert overview.json()["summary"]["hero_name"] == "镜"
    assert invalid_dates.status_code == 422
    assert player.json()["summary"]["player_name"] == "钟意"
    assert trio.status_code == 200
    assert trio.json()["items"][0]["hero3_name"]
    assert focused_combos.status_code == 200
    assert all(
        531 in {row["hero1_id"], row["hero2_id"]}
        for row in focused_combos.json()["items"]
    )
    assert invalid_combo_sort.status_code == 422
    assert len(battle.json()["players"]) == 10
    assert query.status_code == 200
    assert query.json()["plan"]["analysis"] == "builds"
