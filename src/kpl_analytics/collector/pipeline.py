from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from kpl_analytics.collector.client import KPLClient
from kpl_analytics.config import Settings


@dataclass
class BackfillSummary:
    cutoff_date: str
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
    """Download a bounded window of completed competitions into immutable JSON files."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.store = RawStore(self.settings.raw_dir)

    @staticmethod
    def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = payload.get("results", payload.get("data", []))
        return rows if isinstance(rows, list) else []

    def backfill(self, days: int = 730, refresh: bool = False) -> BackfillSummary:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        summary = BackfillSummary(cutoff_date=cutoff)

        with KPLClient(self.settings) as client:
            leagues_payload = client.leagues()
            self.store.write("leagues", "index", leagues_payload)
            leagues = [
                row
                for row in self._rows(leagues_payload)
                if str(row.get("end_time") or row.get("start_time") or "")[:10] >= cutoff
            ]
            summary.leagues = len(leagues)

            runes = client.rune_dictionary()
            self.store.write("dictionaries", "runes", runes)

            for league in sorted(leagues, key=lambda item: str(item.get("start_time", ""))):
                league_id = str(league["league_id"])
                matches_payload = client.matches(league_id)
                self.store.write("matches", league_id, matches_payload)
                matches = self._rows(matches_payload)
                summary.matches += len(matches)

                for match in matches:
                    match_id = str(match["match_id"])
                    if not refresh and self.store.exists("match_battles", match_id):
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

        self.store.write("manifests", "latest", asdict(summary))
        return summary
