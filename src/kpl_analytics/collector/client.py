from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx

from kpl_analytics.config import Settings


class KPLAPIError(RuntimeError):
    """Raised when the upstream public match API returns an invalid response."""


class KPLClient:
    """Small, rate-limited client for Tencent's public competition endpoints."""

    PATHS = {
        "leagues": "/leaguesite/leagues/open",
        "matches": "/leaguesite/matches/open",
        "match_battles": "/leaguesite/match/battles/open",
        "battle": "/leaguesite/battle/open",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._last_request_at = 0.0
        self._client = httpx.Client(
            base_url=self.settings.api_base,
            timeout=self.settings.request_timeout_seconds,
            follow_redirects=True,
            headers={
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "kpl-analytics/0.1 (+https://github.com/blue-39/kpl-analytics)",
            },
        )

    def __enter__(self) -> KPLClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        remaining = self.settings.request_delay_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        self._throttle()
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.get(path, params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise KPLAPIError(f"Unexpected JSON type from {path}: {type(payload).__name__}")
                if payload.get("code") not in (None, 0, 200):
                    code = payload.get("code")
                    message = payload.get("message", "")
                    raise KPLAPIError(f"Upstream error from {path}: {code} {message}")
                self._last_request_at = time.monotonic()
                return payload
            except (httpx.HTTPError, ValueError, KPLAPIError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.5 * (2**attempt))
        raise KPLAPIError(f"Unable to fetch {path}: {last_error}") from last_error

    @staticmethod
    def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = payload.get("results", payload.get("data", []))
        return rows if isinstance(rows, list) else []

    def leagues(self) -> dict[str, Any]:
        return self._get(self.PATHS["leagues"])

    def matches(self, league_id: str) -> dict[str, Any]:
        return self._get(self.PATHS["matches"], {"league_id": league_id})

    def match_battles(self, match_id: str) -> dict[str, Any]:
        return self._get(self.PATHS["match_battles"], {"match_id": match_id})

    def battle(self, battle_id: str) -> dict[str, Any]:
        return self._get(self.PATHS["battle"], {"battle_id": battle_id})

    def rune_dictionary(self) -> list[dict[str, Any]]:
        self._throttle()
        response = self._client.get(self.settings.rune_dictionary_url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise KPLAPIError("Rune dictionary did not return a list")
        self._last_request_at = time.monotonic()
        return payload

    def iter_recent_leagues(self, cutoff_date: str) -> Iterator[dict[str, Any]]:
        for league in self._rows(self.leagues()):
            end_time = str(league.get("end_time") or league.get("start_time") or "")
            if end_time[:10] >= cutoff_date:
                yield league
