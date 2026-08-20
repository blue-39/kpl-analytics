from __future__ import annotations

from fastapi.testclient import TestClient

from kpl_analytics.api.main import create_app


def test_api_serves_dashboard_and_natural_language_query(warehouse):
    app = create_app(warehouse.settings)
    with TestClient(app) as client:
        health = client.get("/api/health")
        heroes = client.get("/api/heroes")
        overview = client.get("/api/heroes/531/overview")
        invalid_dates = client.get(
            "/api/heroes/531/overview?start_date=2026-01-01&end_date=2025-01-01"
        )
        player = client.get("/api/players/10005%3A钟意/overview")
        battle_list = client.get("/api/battles?hero_id=531")
        query = client.post("/api/query", json={"question": "镜的出装统计"})
        battle = client.get(f"/api/battles/{battle_list.json()['items'][0]['battle_id']}")

    assert health.status_code == 200
    assert heroes.status_code == 200
    assert any(row["hero_name"] == "镜" for row in heroes.json())
    assert overview.json()["summary"]["hero_name"] == "镜"
    assert invalid_dates.status_code == 422
    assert player.json()["summary"]["player_name"] == "钟意"
    assert len(battle.json()["players"]) == 10
    assert query.status_code == 200
    assert query.json()["plan"]["analysis"] == "builds"
