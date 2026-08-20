from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from kpl_analytics.collector.client import KPLClient
from kpl_analytics.collector.leagues import selectable_leagues
from kpl_analytics.config import Settings


@dataclass
class BackfillSummary:
    selected_league_ids: list[str] = field(default_factory=list)
    selected_league_names: list[str] = field(default_factory=list)
    leagues: int = 0
    matches: int = 0
    battles: int = 0
    details: int = 0
    skipped: int = 0


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, collection: str, key: str) -> Path:
        return self.root / collection / f"{key}.json"

    def exists(self, collection: str, key: str) -> bool:
        return self.path(collection, key).exists()

    def write(self, collection: str, key: str, payload: Any) -> Path:
        target = self.path(collection, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
        return target


class BackfillPipeline:
    """Download selected supported competitions into immutable JSON files."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.store = RawStore(self.settings.raw_dir)

    @staticmethod
    def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = payload.get("results", payload.get("data", []))
        return rows if isinstance(rows, list) else []

    def backfill(
        self,
        league_ids: list[str],
        refresh: bool = False,
        progress: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> BackfillSummary:
        requested_ids = list(dict.fromkeys(league_ids))
        if not requested_ids:
            raise ValueError("请至少选择一个赛事。")
        summary = BackfillSummary(selected_league_ids=requested_ids)

        def emit(message: str, **extra: Any) -> None:
            if progress:
                progress(message, {**asdict(summary), **extra})

        emit("正在读取联赛列表")

        with KPLClient(self.settings) as client:
            leagues_payload = client.leagues()
            self.store.write("leagues", "index", leagues_payload)
            league_lookup = {
                row["league_id"]: row
                for row in selectable_leagues(leagues_payload)
                if row["selectable"]
            }
            invalid_ids = [
                league_id for league_id in requested_ids if league_id not in league_lookup
            ]
            if invalid_ids:
                raise ValueError(f"赛事不存在、尚未开始或不在支持范围内：{', '.join(invalid_ids)}")
            leagues = sorted(
                (league_lookup[league_id] for league_id in requested_ids),
                key=lambda item: item["start_date"],
            )
            summary.leagues = len(leagues)
            summary.selected_league_names = [row["league_name"] for row in leagues]

            emit("联赛列表读取完成，正在下载铭文字典", league_total=len(leagues))

            runes = client.rune_dictionary()
            self.store.write("dictionaries", "runes", runes)

            for league_index, league in enumerate(
                sorted(leagues, key=lambda item: str(item.get("start_time", ""))), start=1
            ):
                league_id = str(league["league_id"])
                emit(
                    f"正在处理联赛 {league_index}/{len(leagues)}",
                    league_index=league_index,
                    league_total=len(leagues),
                    league_id=league_id,
                )
                matches_payload = client.matches(league_id)
                self.store.write("matches", league_id, matches_payload)
                matches = [
                    match
                    for match in self._rows(matches_payload)
                    if int(match.get("status") or 0) == 2
                ]
                summary.matches += len(matches)

                for match_index, match in enumerate(matches, start=1):
                    match_id = str(match["match_id"])
                    should_refresh_match = refresh or league["availability"] == "in_progress"
                    if not should_refresh_match and self.store.exists("match_battles", match_id):
                        battles_payload = json.loads(
                            self.store.path("match_battles", match_id).read_text(encoding="utf-8")
                        )
                    else:
                        battles_payload = client.match_battles(match_id)
                        self.store.write("match_battles", match_id, battles_payload)

                    battles = self._rows(battles_payload)
                    summary.battles += len(battles)
                    for battle in battles:
                        battle_id = str(battle["battle_id"])
                        if not refresh and self.store.exists("details", battle_id):
                            summary.skipped += 1
                            continue
                        self.store.write("details", battle_id, client.battle(battle_id))
                        summary.details += 1

                    emit(
                        f"联赛 {league_index}/{len(leagues)}："
                        f"已处理比赛 {match_index}/{len(matches)}",
                        league_index=league_index,
                        league_total=len(leagues),
                        match_index=match_index,
                        match_total=len(matches),
                        match_id=match_id,
                    )

        self.store.write("manifests", "latest", asdict(summary))
        emit("回填完成")
        return summary
