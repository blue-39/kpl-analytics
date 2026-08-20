from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from kpl_analytics.config import Settings


class Warehouse:
    """Owns the local DuckDB schema and normalization of archived API payloads."""

    TABLES = (
        "player_runes",
        "player_items",
        "bp_actions",
        "player_battles",
        "team_battles",
        "battles",
        "matches",
        "leagues",
        "metadata",
    )

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.settings.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.settings.database_path), read_only=read_only)

    @staticmethod
    def _schema_path() -> Path:
        return Path(__file__).with_name("schema.sql")

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(self._schema_path().read_text(encoding="utf-8"))

    def clear(self) -> None:
        self.initialize()
        with self.connect() as connection:
            for table in self.TABLES:
                connection.execute(f"DELETE FROM {table}")

    @staticmethod
    def _read_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = payload.get("results", payload.get("data", []))
        return rows if isinstance(rows, list) else []

    @staticmethod
    def _player_key(player: dict[str, Any]) -> str:
        team_id = str(player.get("team_id", "unknown"))
        name = str(player.get("player_name") or player.get("actual_player_name") or "unknown")
        return f"{team_id}:{name}".lower()

    def rebuild_from_raw(self) -> dict[str, int]:
        raw = self.settings.raw_dir
        if not (raw / "leagues" / "index.json").exists():
            raise FileNotFoundError("No archived data found. Run `kpl-analytics backfill` first.")

        self.clear()
        counts = {"leagues": 0, "matches": 0, "battles": 0, "players": 0}
        rune_lookup: dict[str, str] = {}
        rune_path = raw / "dictionaries" / "runes.json"
        if rune_path.exists():
            rune_lookup = {
                str(row.get("ming_id")): str(row.get("ming_name", row.get("ming_id")))
                for row in self._read_json(rune_path)
            }

        league_payload = self._read_json(raw / "leagues" / "index.json")
        leagues = self._rows(league_payload)
        match_lookup: dict[str, dict[str, Any]] = {}
        battle_lookup: dict[str, dict[str, Any]] = {}

        with self.connect() as connection:
            for league in leagues:
                connection.execute(
                    "INSERT OR REPLACE INTO leagues VALUES (?, ?, ?, ?, ?)",
                    [
                        str(league.get("league_id")),
                        league.get("league_name"),
                        league.get("league_type_name"),
                        league.get("start_time"),
                        league.get("end_time"),
                    ],
                )
                counts["leagues"] += 1

            for path in sorted((raw / "matches").glob("*.json")):
                for match in self._rows(self._read_json(path)):
                    match_id = str(match["match_id"])
                    camp1, camp2 = match.get("camp1") or {}, match.get("camp2") or {}
                    match_lookup[match_id] = match
                    connection.execute(
                        """INSERT OR REPLACE INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [
                            match_id,
                            str(match.get("league_id", path.stem)),
                            match.get("cc_match_id"),
                            match.get("match_stage_desc") or match.get("match_stage_name"),
                            match.get("bo"),
                            match.get("start_time"),
                            str(camp1.get("team_id", "")),
                            camp1.get("team_name"),
                            str(camp2.get("team_id", "")),
                            camp2.get("team_name"),
                        ],
                    )
                    counts["matches"] += 1

            for path in sorted((raw / "match_battles").glob("*.json")):
                for battle in self._rows(self._read_json(path)):
                    battle_lookup[str(battle["battle_id"])] = {**battle, "match_id": path.stem}

            for path in sorted((raw / "details").glob("*.json")):
                envelope = self._read_json(path)
                detail = envelope.get("data", envelope)
                if not isinstance(detail, dict) or not detail.get("battle_id"):
                    continue
                battle_id = str(detail["battle_id"])
                battle_meta = battle_lookup.get(battle_id, {})
                match_id = str(battle_meta.get("match_id", ""))
                match = match_lookup.get(match_id, {})
                game_date = str(match.get("start_time", ""))[:10] or None
                connection.execute(
                    "INSERT OR REPLACE INTO battles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        battle_id,
                        match_id,
                        detail.get("battle_seq", battle_meta.get("battle_seq")),
                        game_date,
                        detail.get("game_duration", battle_meta.get("game_duration")),
                        detail.get("win_camp"),
                        detail.get("status"),
                        True,
                    ],
                )
                counts["battles"] += 1

                for camp in (1, 2):
                    team = detail.get(f"camp{camp}") or {}
                    dragons = sum(
                        int(team.get(key) or 0)
                        for key in (
                            "kill_big_dragon_num",
                            "kill_dark_tyrant_num",
                            "kill_tyrant_num",
                            "kill_prophet_dragon_num",
                            "kill_shadow_dragon_num",
                            "kill_storm_dragon_king_num",
                        )
                    )
                    connection.execute(
                        """INSERT OR REPLACE INTO team_battles
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [
                            battle_id,
                            camp,
                            str(team.get("team_id", "")),
                            team.get("team_name"),
                            bool(team.get("is_win", detail.get("win_camp") == camp)),
                            team.get("kill_num", 0),
                            team.get("death_num", 0),
                            team.get("assist_num", 0),
                            team.get("gold", 0),
                            team.get("push_tower_num", 0),
                            dragons,
                        ],
                    )

                pick_index = 0
                for action_index, action in enumerate(detail.get("bp_list") or [], start=1):
                    action_type = "pick" if int(action.get("is_ban_or_pick", 0)) == 1 else "ban"
                    if action_type == "pick":
                        pick_index += 1
                    connection.execute(
                        "INSERT OR REPLACE INTO bp_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        [
                            battle_id,
                            action_index,
                            action.get("camp"),
                            action_type,
                            action.get("hero_id"),
                            action.get("hero_name"),
                            action.get("position"),
                            pick_index if action_type == "pick" else None,
                        ],
                    )

                for player in detail.get("battle_player_list") or []:
                    player_key = self._player_key(player)
                    camp = int(player.get("camp") or 0)
                    connection.execute(
                        """INSERT OR REPLACE INTO player_battles VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [
                            battle_id,
                            player_key,
                            player.get("player_name"),
                            player.get("actual_player_name"),
                            str(player.get("team_id", "")),
                            player.get("team_name"),
                            camp,
                            player.get("position"),
                            player.get("position_desc"),
                            player.get("hero_id"),
                            player.get("hero_name"),
                            detail.get("win_camp") == camp,
                            player.get("kill_num", 0),
                            player.get("death_num", 0),
                            player.get("assist_num", 0),
                            player.get("gold", 0),
                            player.get("hurt_total", 0),
                            player.get("hurt_to_hero_total", 0),
                            player.get("be_hurt_total", 0),
                            player.get("participation_rate", 0),
                            player.get("mvp_score", 0),
                            bool(player.get("is_mvp", 0)),
                        ],
                    )
                    counts["players"] += 1
                    for slot, item in enumerate(player.get("BriefEquipList") or [], start=1):
                        connection.execute(
                            "INSERT OR REPLACE INTO player_items VALUES (?, ?, ?, ?, ?)",
                            [
                                battle_id,
                                player_key,
                                slot,
                                item.get("equip_id"),
                                item.get("equip_name"),
                            ],
                        )
                    rune_counts = Counter(
                        rune_id
                        for rune_id in str(player.get("symbol_ids") or "").split("+")
                        if rune_id
                    )
                    for rune_id, count in rune_counts.items():
                        connection.execute(
                            "INSERT OR REPLACE INTO player_runes VALUES (?, ?, ?, ?, ?)",
                            [
                                battle_id,
                                player_key,
                                rune_id,
                                rune_lookup.get(rune_id, rune_id),
                                count,
                            ],
                        )

            connection.execute("INSERT OR REPLACE INTO metadata VALUES ('data_mode', 'real')")
            connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('built_at', ?)",
                [datetime.now(UTC).isoformat()],
            )
        return counts
