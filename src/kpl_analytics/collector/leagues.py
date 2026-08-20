from __future__ import annotations

from datetime import date
from typing import Any

FIRST_SUPPORTED_DATE = date(2025, 2, 10)
SUPPORTED_NAME_SUFFIXES = ("KPL春季赛", "KPL夏季赛", "年度总决赛", "挑战者杯")


def selectable_leagues(
    payload: dict[str, Any], as_of: date | None = None
) -> list[dict[str, Any]]:
    """Normalize the supported KPL competitions shown in the local control center."""

    current_date = as_of or date.today()
    rows = payload.get("results", payload.get("data", []))
    if not isinstance(rows, list):
        return []

    leagues: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("league_name") or "")
        start_text = str(row.get("start_time") or "")[:10]
        end_text = str(row.get("end_time") or "")[:10]
        try:
            start_date = date.fromisoformat(start_text)
            end_date = date.fromisoformat(end_text)
        except ValueError:
            continue
        if start_date < FIRST_SUPPORTED_DATE or not name.endswith(SUPPORTED_NAME_SUFFIXES):
            continue

        upstream_status = int(row.get("status") or 0)
        if start_date > current_date:
            availability = "upcoming"
        elif upstream_status == 1:
            availability = "in_progress"
        elif upstream_status == 2:
            availability = "completed"
        elif current_date <= end_date:
            availability = "in_progress"
        else:
            availability = "completed"

        leagues.append(
            {
                "league_id": str(row.get("league_id") or ""),
                "league_name": name,
                "start_date": start_text,
                "end_date": end_text,
                "effective_end_date": (
                    current_date.isoformat() if availability == "in_progress" else end_text
                ),
                "availability": availability,
                "selectable": availability != "upcoming",
                "league_icon": row.get("league_icon"),
            }
        )
    return sorted(leagues, key=lambda item: item["start_date"])
