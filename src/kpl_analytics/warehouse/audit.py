from __future__ import annotations

from typing import Any

from kpl_analytics.warehouse.database import Warehouse


def audit_warehouse(warehouse: Warehouse) -> dict[str, Any]:
    """Run inexpensive integrity checks and return machine-readable findings."""

    checks: list[dict[str, Any]] = []
    with warehouse.connect(read_only=True) as connection:
        rules = [
            (
                "battle_has_ten_players",
                """
                SELECT count(*) FROM (
                  SELECT battle_id FROM player_battles GROUP BY battle_id HAVING count(*) != 10
                ) bad
                """,
            ),
            (
                "battle_has_two_teams",
                """
                SELECT count(*) FROM (
                  SELECT battle_id FROM team_battles GROUP BY battle_id HAVING count(*) != 2
                ) bad
                """,
            ),
            (
                "one_winner_per_battle",
                """
                SELECT count(*) FROM (
                  SELECT battle_id FROM team_battles
                  GROUP BY battle_id HAVING sum(is_win::INTEGER) != 1
                ) bad
                """,
            ),
            (
                "picked_heroes_match_players",
                """
                SELECT count(*) FROM (
                  SELECT battle_id,
                         count(*) FILTER (WHERE action_type = 'pick') AS bp_picks
                  FROM bp_actions GROUP BY battle_id HAVING bp_picks != 10
                ) bad
                """,
            ),
            (
                "no_unknown_hero",
                "SELECT count(*) FROM player_battles WHERE hero_id IS NULL OR hero_name IS NULL",
            ),
        ]
        for name, sql in rules:
            failures = int(connection.execute(sql).fetchone()[0])
            checks.append(
                {"name": name, "status": "pass" if failures == 0 else "fail", "failures": failures}
            )

        coverage_row = connection.execute(
            """
            SELECT count(*) AS battles, min(game_date)::VARCHAR, max(game_date)::VARCHAR
            FROM battles
            """
        ).fetchone()
    return {
        "ok": all(check["status"] == "pass" for check in checks),
        "checks": checks,
        "coverage": {
            "battles": coverage_row[0],
            "start_date": coverage_row[1],
            "end_date": coverage_row[2],
        },
    }
