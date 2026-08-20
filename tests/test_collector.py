from __future__ import annotations

import json
from datetime import date

from kpl_analytics.collector.leagues import selectable_leagues
from kpl_analytics.collector.pipeline import BackfillPipeline, RawStore
from kpl_analytics.config import Settings


def test_raw_store_writes_utf8_json_atomically(tmp_path):
    store = RawStore(tmp_path)
    target = store.write("details", "battle-1", {"hero": "公孙离"})

    assert json.loads(target.read_text(encoding="utf-8")) == {"hero": "公孙离"}
    assert not target.with_suffix(".json.tmp").exists()


def test_selectable_leagues_starts_at_2025_spring_and_labels_active_event():
    payload = {
        "results": [
            {
                "league_id": "20240004",
                "league_name": "2024年王者荣耀挑战者杯",
                "start_time": "2024-12-01 00:00:00",
                "end_time": "2025-02-01 00:00:05",
                "status": 2,
            },
            {
                "league_id": "20250001",
                "league_name": "2025年KPL春季赛",
                "start_time": "2025-02-10 00:00:00",
                "end_time": "2025-06-06 00:00:05",
                "status": 2,
            },
            {
                "league_id": "20250002",
                "league_name": "2025年KPL夏季赛",
                "start_time": "2025-06-04 00:00:00",
                "end_time": "2025-09-08 00:00:05",
                "status": 1,
            },
            {
                "league_id": "ignored",
                "league_name": "2025世界冠军杯",
                "start_time": "2025-07-01 00:00:00",
                "end_time": "2025-08-01 00:00:00",
                "status": 2,
            },
        ]
    }

    items = selectable_leagues(payload, as_of=date(2025, 7, 1))

    assert [item["league_id"] for item in items] == ["20250001", "20250002"]
    assert items[1]["availability"] == "in_progress"
    assert items[1]["effective_end_date"] == "2025-07-01"


def test_backfill_uses_only_selected_completed_matches_and_refreshes_active_league(
    tmp_path, monkeypatch
):
    class FakeClient:
        match_battle_calls: list[str] = []

        def __init__(self, _settings):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def leagues(self):
            return {
                "results": [
                    {
                        "league_id": "20260003",
                        "league_name": "2026年KPL夏季赛",
                        "start_time": "2026-06-17 00:00:00",
                        "end_time": "2026-09-12 23:59:59",
                        "status": 1,
                    }
                ]
            }

        def rune_dictionary(self):
            return []

        def matches(self, _league_id):
            return {
                "results": [
                    {"match_id": "finished", "status": 2},
                    {"match_id": "scheduled", "status": 0},
                ]
            }

        def match_battles(self, match_id):
            self.match_battle_calls.append(match_id)
            return {"results": [{"battle_id": "battle-1"}]}

        def battle(self, battle_id):
            return {"data": {"battle_id": battle_id}}

    monkeypatch.setattr("kpl_analytics.collector.pipeline.KPLClient", FakeClient)
    pipeline = BackfillPipeline(Settings(data_dir=tmp_path / "data"))
    pipeline.store.write("match_battles", "finished", {"results": []})

    summary = pipeline.backfill(["20260003"])

    assert summary.selected_league_names == ["2026年KPL夏季赛"]
    assert summary.matches == 1
    assert summary.battles == 1
    assert summary.details == 1
    assert FakeClient.match_battle_calls == ["finished"]
    assert not pipeline.store.exists("match_battles", "scheduled")
