from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import duckdb

from kpl_analytics.warehouse.database import Warehouse


def _rows(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _row(cursor: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    rows = _rows(cursor)
    return rows[0] if rows else {}


class MetricsService:
    """Parameterized analytics queries over normalized battle-level data."""

    def __init__(self, warehouse: Warehouse | None = None) -> None:
        self.warehouse = warehouse or Warehouse()

    @staticmethod
    def _date_filter(
        alias: str, start_date: str | None, end_date: str | None
    ) -> tuple[str, list[str]]:
        try:
            normalized_start = date.fromisoformat(start_date).isoformat() if start_date else None
            normalized_end = date.fromisoformat(end_date).isoformat() if end_date else None
        except ValueError as exc:
            raise ValueError("dates must use YYYY-MM-DD format") from exc
        if normalized_start and normalized_end and normalized_start > normalized_end:
            raise ValueError("start_date cannot be later than end_date")
        clauses: list[str] = []
        params: list[str] = []
        if normalized_start:
            clauses.append(f"{alias}.game_date >= ?::DATE")
            params.append(normalized_start)
        if normalized_end:
            clauses.append(f"{alias}.game_date <= ?::DATE")
            params.append(normalized_end)
        return (" AND ".join(clauses) or "TRUE", params)

    @staticmethod
    def _number(value: Any, digits: int = 2) -> float:
        return round(float(value or 0), digits)

    def metadata(self) -> dict[str, Any]:
        with self.warehouse.connect(read_only=True) as connection:
            metadata = {
                row[0]: row[1]
                for row in connection.execute("SELECT key, value FROM metadata").fetchall()
            }
            coverage = _row(
                connection.execute(
                    """
                    SELECT min(game_date)::VARCHAR AS start_date,
                           max(game_date)::VARCHAR AS end_date,
                           count(*) AS battles,
                           count(DISTINCT match_id) AS matches
                    FROM battles
                    """
                )
            )
            counts = _row(
                connection.execute(
                    """
                    SELECT count(DISTINCT hero_id) AS heroes,
                           count(DISTINCT player_key) AS players,
                           count(DISTINCT team_id) AS teams
                    FROM player_battles
                    """
                )
            )
        return {
            "data_mode": metadata.get("data_mode", "unknown"),
            "built_at": metadata.get("built_at"),
            "coverage": {**coverage, **counts},
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def heroes(self) -> list[dict[str, Any]]:
        with self.warehouse.connect(read_only=True) as connection:
            return _rows(
                connection.execute(
                    """
                    SELECT hero_id, any_value(hero_name) AS hero_name,
                           count(*) AS games,
                           round(100.0 * avg(is_win::INTEGER), 2) AS win_rate
                    FROM player_battles
                    GROUP BY hero_id
                    ORDER BY games DESC, hero_name
                    """
                )
            )

    def players(self) -> list[dict[str, Any]]:
        with self.warehouse.connect(read_only=True) as connection:
            return _rows(
                connection.execute(
                    """
                    SELECT player_key, any_value(player_name) AS player_name,
                           any_value(team_name) AS team_name,
                           any_value(role_name) AS role_name,
                           count(*) AS games,
                           round(100.0 * avg(is_win::INTEGER), 2) AS win_rate
                    FROM player_battles
                    GROUP BY player_key
                    ORDER BY games DESC, player_name
                    """
                )
            )

    def recent_battles(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        hero_id: int | None = None,
        player_key: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        date_sql, params = self._date_filter("b", start_date, end_date)
        clauses = [date_sql]
        if hero_id is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM player_battles p "
                "WHERE p.battle_id = b.battle_id AND p.hero_id = ?)"
            )
            params.append(hero_id)
        if player_key:
            clauses.append(
                "EXISTS (SELECT 1 FROM player_battles p "
                "WHERE p.battle_id = b.battle_id AND p.player_key = ?)"
            )
            params.append(player_key)
        params.append(limit)
        with self.warehouse.connect(read_only=True) as connection:
            rows = _rows(
                connection.execute(
                    f"""
                    SELECT b.battle_id, b.match_id, b.battle_seq,
                           b.game_date::VARCHAR AS game_date, b.duration_ms,
                           winner.team_name AS winner,
                           m.team1_name, m.team2_name, m.stage,
                           l.league_name
                    FROM battles b
                    LEFT JOIN matches m USING (match_id)
                    LEFT JOIN leagues l USING (league_id)
                    LEFT JOIN team_battles winner
                      ON winner.battle_id = b.battle_id AND winner.is_win
                    WHERE {" AND ".join(clauses)}
                    ORDER BY b.game_date DESC, b.match_id DESC, b.battle_seq DESC
                    LIMIT ?
                    """,
                    params,
                )
            )
        return self._envelope({"items": rows}, start_date, end_date, None, len(rows))

    def battle_detail(self, battle_id: str) -> dict[str, Any]:
        with self.warehouse.connect(read_only=True) as connection:
            battle = _row(
                connection.execute(
                    """
                    SELECT b.*, m.stage, m.bo, m.team1_name, m.team2_name,
                           l.league_name
                    FROM battles b
                    LEFT JOIN matches m USING (match_id)
                    LEFT JOIN leagues l USING (league_id)
                    WHERE b.battle_id = ?
                    """,
                    [battle_id],
                )
            )
            if not battle:
                return {}
            teams = _rows(
                connection.execute(
                    "SELECT * FROM team_battles WHERE battle_id = ? ORDER BY camp",
                    [battle_id],
                )
            )
            players = _rows(
                connection.execute(
                    "SELECT * FROM player_battles WHERE battle_id = ? ORDER BY camp, role_id",
                    [battle_id],
                )
            )
            items = _rows(
                connection.execute(
                    "SELECT player_key, slot, item_id, item_name FROM player_items "
                    "WHERE battle_id = ? ORDER BY player_key, slot",
                    [battle_id],
                )
            )
            runes = _rows(
                connection.execute(
                    "SELECT player_key, rune_id, rune_name, count FROM player_runes "
                    "WHERE battle_id = ? ORDER BY player_key, rune_id",
                    [battle_id],
                )
            )
            draft = _rows(
                connection.execute(
                    "SELECT * FROM bp_actions WHERE battle_id = ? ORDER BY action_index",
                    [battle_id],
                )
            )
        items_by_player: dict[str, list[dict[str, Any]]] = {}
        runes_by_player: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            items_by_player.setdefault(item.pop("player_key"), []).append(item)
        for rune in runes:
            runes_by_player.setdefault(rune.pop("player_key"), []).append(rune)
        for player in players:
            key = player["player_key"]
            player["items"] = items_by_player.get(key, [])
            player["runes"] = runes_by_player.get(key, [])
        return {
            "battle": battle,
            "teams": teams,
            "players": players,
            "draft": draft,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def hero_overview(
        self,
        hero_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        date_sql, date_params = self._date_filter("b", start_date, end_date)
        role_sql = " AND p.role_name = ?" if role else ""
        hero_params: list[Any] = [*date_params, hero_id]
        if role:
            hero_params.append(role)
        ban_params: list[Any] = [*date_params, hero_id]

        with self.warehouse.connect(read_only=True) as connection:
            total = _row(
                connection.execute(
                    f"SELECT count(*) AS games FROM battles b WHERE {date_sql}", date_params
                )
            ).get("games", 0)
            summary = _row(
                connection.execute(
                    f"""
                    SELECT any_value(p.hero_name) AS hero_name,
                           count(*) AS picks,
                           sum(p.is_win::INTEGER) AS wins,
                           round(100.0 * avg(p.is_win::INTEGER), 2) AS win_rate,
                           round((sum(p.kills) + sum(p.assists)) /
                                 greatest(sum(p.deaths), 1), 2) AS kda,
                           round(avg(p.kills), 2) AS kills,
                           round(avg(p.deaths), 2) AS deaths,
                           round(avg(p.assists), 2) AS assists,
                           round(avg(p.gold), 0) AS gold,
                           round(avg(p.damage_to_heroes), 0) AS damage_to_heroes
                    FROM player_battles p
                    JOIN battles b USING (battle_id)
                    WHERE {date_sql} AND p.hero_id = ? {role_sql}
                    """,
                    hero_params,
                )
            )
            bans = _row(
                connection.execute(
                    f"""
                    SELECT count(DISTINCT a.battle_id) AS bans
                    FROM bp_actions a
                    JOIN battles b USING (battle_id)
                    WHERE {date_sql} AND a.hero_id = ? AND a.action_type = 'ban'
                    """,
                    ban_params,
                )
            ).get("bans", 0)
            roles = _rows(
                connection.execute(
                    f"""
                    SELECT p.role_name, count(*) AS games,
                           round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS share,
                           round(100.0 * avg(p.is_win::INTEGER), 2) AS win_rate
                    FROM player_battles p JOIN battles b USING (battle_id)
                    WHERE {date_sql} AND p.hero_id = ?
                    GROUP BY p.role_name ORDER BY games DESC
                    """,
                    [*date_params, hero_id],
                )
            )
            draft_slots = _rows(
                connection.execute(
                    f"""
                    SELECT a.pick_index AS slot, count(*) AS games,
                           round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS share
                    FROM bp_actions a JOIN battles b USING (battle_id)
                    WHERE {date_sql} AND a.hero_id = ? AND a.action_type = 'pick'
                    GROUP BY a.pick_index ORDER BY a.pick_index
                    """,
                    [*date_params, hero_id],
                )
            )
            trend = _rows(
                connection.execute(
                    f"""
                    WITH months AS (
                      SELECT date_trunc('month', b.game_date) AS month, count(*) AS total_games
                      FROM battles b WHERE {date_sql} GROUP BY 1
                    ), picks AS (
                      SELECT date_trunc('month', b.game_date) AS month, count(*) AS picks,
                             sum(p.is_win::INTEGER) AS wins
                      FROM player_battles p JOIN battles b USING (battle_id)
                      WHERE {date_sql} AND p.hero_id = ? {role_sql} GROUP BY 1
                    ), bans AS (
                      SELECT date_trunc('month', b.game_date) AS month,
                             count(DISTINCT a.battle_id) AS bans
                      FROM bp_actions a JOIN battles b USING (battle_id)
                      WHERE {date_sql} AND a.hero_id = ? AND a.action_type = 'ban' GROUP BY 1
                    )
                    SELECT months.month::DATE::VARCHAR AS month, total_games,
                           coalesce(picks, 0) AS picks, coalesce(wins, 0) AS wins,
                           coalesce(bans, 0) AS bans,
                           round(100.0 * coalesce(picks, 0) / total_games, 2) AS pick_rate,
                           round(100.0 * coalesce(wins, 0) /
                                 greatest(coalesce(picks, 0), 1), 2) AS win_rate,
                           round(100.0 * (coalesce(picks, 0) + coalesce(bans, 0)) /
                                 total_games, 2) AS bp_rate
                    FROM months LEFT JOIN picks USING (month) LEFT JOIN bans USING (month)
                    ORDER BY months.month
                    """,
                    [
                        *date_params,
                        *date_params,
                        hero_id,
                        *([role] if role else []),
                        *date_params,
                        hero_id,
                    ],
                )
            )

        picks = int(summary.get("picks") or 0)
        summary.update(
            {
                "hero_id": hero_id,
                "picks": picks,
                "bans": int(bans or 0),
                "total_games": int(total or 0),
                "pick_rate": self._number(100 * picks / total if total else 0),
                "ban_rate": self._number(100 * bans / total if total else 0),
                "bp_rate": self._number(100 * (picks + bans) / total if total else 0),
            }
        )
        return self._envelope(
            {"summary": summary, "roles": roles, "draft_slots": draft_slots, "trend": trend},
            start_date,
            end_date,
            role,
            picks,
        )

    def hero_matchups(
        self,
        hero_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        date_sql, params = self._date_filter("b", start_date, end_date)
        same_role_sql = " AND opponent.role_name = hero.role_name"
        role_sql = " AND hero.role_name = ?" if role else ""
        query_params: list[Any] = [*params, hero_id]
        if role:
            query_params.append(role)
        query_params.append(limit)
        with self.warehouse.connect(read_only=True) as connection:
            rows = _rows(
                connection.execute(
                    f"""
                    SELECT opponent.hero_id, any_value(opponent.hero_name) AS hero_name,
                           any_value(opponent.role_name) AS role_name,
                           count(*) AS games, sum(hero.is_win::INTEGER) AS wins,
                           round(100.0 * avg(hero.is_win::INTEGER), 2) AS win_rate,
                           round(avg((hero.kills + hero.assists) /
                                     greatest(hero.deaths, 1)), 2) AS kda
                    FROM player_battles hero
                    JOIN battles b USING (battle_id)
                    JOIN player_battles opponent
                      ON opponent.battle_id = hero.battle_id AND opponent.camp != hero.camp
                      {same_role_sql}
                    WHERE {date_sql} AND hero.hero_id = ? {role_sql}
                    GROUP BY opponent.hero_id ORDER BY games DESC, win_rate DESC LIMIT ?
                    """,
                    query_params,
                )
            )
        return self._envelope(
            {"items": rows}, start_date, end_date, role, sum(r["games"] for r in rows)
        )

    def hero_teammates(
        self,
        hero_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        date_sql, params = self._date_filter("b", start_date, end_date)
        role_sql = " AND hero.role_name = ?" if role else ""
        query_params: list[Any] = [*params, hero_id]
        if role:
            query_params.append(role)
        query_params.append(limit)
        with self.warehouse.connect(read_only=True) as connection:
            rows = _rows(
                connection.execute(
                    f"""
                    SELECT mate.hero_id, any_value(mate.hero_name) AS hero_name,
                           any_value(mate.role_name) AS role_name,
                           count(*) AS games, sum(hero.is_win::INTEGER) AS wins,
                           round(100.0 * avg(hero.is_win::INTEGER), 2) AS win_rate
                    FROM player_battles hero
                    JOIN battles b USING (battle_id)
                    JOIN player_battles mate
                      ON mate.battle_id = hero.battle_id AND mate.camp = hero.camp
                         AND mate.hero_id != hero.hero_id
                    WHERE {date_sql} AND hero.hero_id = ? {role_sql}
                    GROUP BY mate.hero_id ORDER BY games DESC, win_rate DESC LIMIT ?
                    """,
                    query_params,
                )
            )
        return self._envelope(
            {"items": rows}, start_date, end_date, role, sum(r["games"] for r in rows)
        )

    def hero_builds(
        self,
        hero_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
        limit: int = 12,
    ) -> dict[str, Any]:
        date_sql, params = self._date_filter("b", start_date, end_date)
        role_sql = " AND p.role_name = ?" if role else ""
        query_params: list[Any] = [*params, hero_id]
        if role:
            query_params.append(role)
        query_params.append(limit)
        with self.warehouse.connect(read_only=True) as connection:
            rows = _rows(
                connection.execute(
                    f"""
                    WITH builds AS (
                      SELECT p.battle_id, p.player_key, p.is_win,
                             string_agg(i.item_name, ' → ' ORDER BY i.slot) AS build
                      FROM player_battles p JOIN battles b USING (battle_id)
                      JOIN player_items i ON i.battle_id = p.battle_id
                        AND i.player_key = p.player_key
                      WHERE {date_sql} AND p.hero_id = ? {role_sql}
                      GROUP BY p.battle_id, p.player_key, p.is_win
                    )
                    SELECT build, count(*) AS games,
                           round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS share,
                           round(100.0 * avg(is_win::INTEGER), 2) AS win_rate
                    FROM builds GROUP BY build ORDER BY games DESC, win_rate DESC LIMIT ?
                    """,
                    query_params,
                )
            )
        return self._envelope(
            {"items": rows}, start_date, end_date, role, sum(r["games"] for r in rows)
        )

    def hero_runes(
        self,
        hero_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        date_sql, params = self._date_filter("b", start_date, end_date)
        role_sql = " AND p.role_name = ?" if role else ""
        query_params: list[Any] = [*params, hero_id]
        if role:
            query_params.append(role)
        query_params.append(limit)
        with self.warehouse.connect(read_only=True) as connection:
            rows = _rows(
                connection.execute(
                    f"""
                    WITH selected AS (
                      SELECT p.battle_id, p.player_key
                      FROM player_battles p JOIN battles b USING (battle_id)
                      WHERE {date_sql} AND p.hero_id = ? {role_sql}
                    ), total AS (
                      SELECT count(*) AS games FROM selected
                    )
                    SELECT r.rune_id, any_value(r.rune_name) AS rune_name,
                           sum(r.count) AS copies, count(*) AS games,
                           round(100.0 * count(*) / greatest(any_value(total.games), 1), 2)
                             AS usage_rate
                    FROM selected
                    JOIN player_runes r USING (battle_id, player_key)
                    CROSS JOIN total
                    GROUP BY r.rune_id ORDER BY games DESC, copies DESC LIMIT ?
                    """,
                    query_params,
                )
            )
        return self._envelope(
            {"items": rows}, start_date, end_date, role, sum(r["games"] for r in rows)
        )

    def combinations(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        min_games: int = 2,
        limit: int = 30,
    ) -> dict[str, Any]:
        date_sql, params = self._date_filter("b", start_date, end_date)
        with self.warehouse.connect(read_only=True) as connection:
            rows = _rows(
                connection.execute(
                    f"""
                    SELECT left_pick.hero_id AS hero1_id,
                           any_value(left_pick.hero_name) AS hero1_name,
                           right_pick.hero_id AS hero2_id,
                           any_value(right_pick.hero_name) AS hero2_name,
                           count(*) AS games,
                           round(100.0 * avg(left_pick.is_win::INTEGER), 2) AS win_rate
                    FROM player_battles left_pick
                    JOIN battles b USING (battle_id)
                    JOIN player_battles right_pick
                      ON right_pick.battle_id = left_pick.battle_id
                      AND right_pick.camp = left_pick.camp
                      AND right_pick.hero_id > left_pick.hero_id
                    WHERE {date_sql}
                    GROUP BY left_pick.hero_id, right_pick.hero_id
                    HAVING count(*) >= ?
                    ORDER BY games DESC, win_rate DESC LIMIT ?
                    """,
                    [*params, min_games, limit],
                )
            )
        return self._envelope(
            {"items": rows}, start_date, end_date, None, sum(r["games"] for r in rows)
        )

    def player_overview(
        self,
        player_key: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        date_sql, params = self._date_filter("b", start_date, end_date)
        with self.warehouse.connect(read_only=True) as connection:
            summary = _row(
                connection.execute(
                    f"""
                    SELECT any_value(p.player_name) AS player_name,
                           any_value(p.team_name) AS team_name,
                           any_value(p.role_name) AS role_name,
                           count(*) AS games, sum(p.is_win::INTEGER) AS wins,
                           round(100.0 * avg(p.is_win::INTEGER), 2) AS win_rate,
                           round((sum(p.kills) + sum(p.assists)) /
                                 greatest(sum(p.deaths), 1), 2) AS kda,
                           round(avg(p.kills), 2) AS kills,
                           round(avg(p.deaths), 2) AS deaths,
                           round(avg(p.assists), 2) AS assists,
                           sum(p.is_mvp::INTEGER) AS mvp_count
                    FROM player_battles p JOIN battles b USING (battle_id)
                    WHERE {date_sql} AND p.player_key = ?
                    """,
                    [*params, player_key],
                )
            )
            heroes = _rows(
                connection.execute(
                    f"""
                    SELECT p.hero_id, any_value(p.hero_name) AS hero_name,
                           count(*) AS games, sum(p.is_win::INTEGER) AS wins,
                           round(100.0 * avg(p.is_win::INTEGER), 2) AS win_rate,
                           round((sum(p.kills) + sum(p.assists)) /
                                 greatest(sum(p.deaths), 1), 2) AS kda
                    FROM player_battles p JOIN battles b USING (battle_id)
                    WHERE {date_sql} AND p.player_key = ?
                    GROUP BY p.hero_id ORDER BY games DESC, win_rate DESC
                    """,
                    [*params, player_key],
                )
            )
            trend = _rows(
                connection.execute(
                    f"""
                    SELECT date_trunc('month', b.game_date)::DATE::VARCHAR AS month,
                           count(*) AS games,
                           round(100.0 * avg(p.is_win::INTEGER), 2) AS win_rate,
                           round((sum(p.kills) + sum(p.assists)) /
                                 greatest(sum(p.deaths), 1), 2) AS kda
                    FROM player_battles p JOIN battles b USING (battle_id)
                    WHERE {date_sql} AND p.player_key = ?
                    GROUP BY 1 ORDER BY 1
                    """,
                    [*params, player_key],
                )
            )
        summary["player_key"] = player_key
        return self._envelope(
            {"summary": summary, "heroes": heroes, "trend": trend},
            start_date,
            end_date,
            None,
            int(summary.get("games") or 0),
        )

    @staticmethod
    def _envelope(
        data: dict[str, Any],
        start_date: str | None,
        end_date: str | None,
        role: str | None,
        sample_size: int,
    ) -> dict[str, Any]:
        return {
            **data,
            "filters": {"start_date": start_date, "end_date": end_date, "role": role},
            "sample_size": sample_size,
            "generated_at": datetime.now(UTC).isoformat(),
        }
