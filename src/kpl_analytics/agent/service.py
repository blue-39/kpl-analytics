from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import date, timedelta
from threading import RLock
from typing import Any

import httpx

from kpl_analytics.agent.dsl import (
    AnalysisType,
    EntityType,
    NaturalLanguageQuery,
    QueryPlan,
)
from kpl_analytics.config import Settings
from kpl_analytics.warehouse.metrics import MetricsService


class QueryUnderstandingError(ValueError):
    pass


class QueryAgent:
    """Turns natural language into a validated metric plan, then executes known queries."""

    def __init__(
        self,
        metrics: MetricsService,
        settings: Settings | None = None,
    ) -> None:
        self.metrics = metrics
        self.base_settings = settings or Settings.from_env()
        self.settings = self.base_settings
        self._settings_lock = RLock()
        self._settings_source = (
            "environment"
            if self.settings.llm_endpoint or self.settings.llm_model or self.settings.llm_api_key
            else "none"
        )

    def configure_llm(self, endpoint: str, api_key: str, model: str) -> dict[str, Any]:
        with self._settings_lock:
            self.settings = replace(
                self.base_settings,
                llm_endpoint=endpoint,
                llm_api_key=api_key,
                llm_model=model,
            )
            self._settings_source = "runtime"
            return self.llm_status()

    def clear_runtime_llm(self) -> dict[str, Any]:
        with self._settings_lock:
            self.settings = self.base_settings
            self._settings_source = (
                "environment"
                if self.settings.llm_endpoint
                or self.settings.llm_model
                or self.settings.llm_api_key
                else "none"
            )
            return self.llm_status()

    def llm_status(self) -> dict[str, Any]:
        with self._settings_lock:
            return {
                "configured": bool(self.settings.llm_endpoint and self.settings.llm_model),
                "endpoint": self.settings.llm_endpoint,
                "model": self.settings.llm_model,
                "has_api_key": bool(self.settings.llm_api_key),
                "source": self._settings_source,
            }

    def ask(self, request: NaturalLanguageQuery) -> dict[str, Any]:
        plan: QueryPlan
        planner = "rules"
        with self._settings_lock:
            active_settings = self.settings
        if active_settings.llm_endpoint and active_settings.llm_model:
            try:
                plan = self._plan_with_llm(request, active_settings)
                planner = "llm"
            except (httpx.HTTPError, ValueError, KeyError):
                plan = self._plan_with_rules(request)
                planner = "rules_fallback"
        else:
            plan = self._plan_with_rules(request)

        result = self.execute(plan)
        return {
            "question": request.question,
            "plan": plan.model_dump(mode="json"),
            "planner": planner,
            "answer": self._summarize(plan, result),
            "result": result,
        }

    def execute(self, plan: QueryPlan) -> dict[str, Any]:
        common = {
            "start_date": plan.start_date,
            "end_date": plan.end_date,
        }
        if plan.analysis == AnalysisType.HERO_OVERVIEW:
            return self.metrics.hero_overview(plan.hero_id or 0, role=plan.role, **common)
        if plan.analysis == AnalysisType.MATCHUPS:
            return self.metrics.hero_matchups(
                plan.hero_id or 0, role=plan.role, limit=plan.limit, **common
            )
        if plan.analysis == AnalysisType.TEAMMATES:
            return self.metrics.hero_teammates(
                plan.hero_id or 0, role=plan.role, limit=plan.limit, **common
            )
        if plan.analysis == AnalysisType.BUILDS:
            return self.metrics.hero_builds(
                plan.hero_id or 0, role=plan.role, limit=plan.limit, **common
            )
        if plan.analysis == AnalysisType.RUNES:
            return self.metrics.hero_runes(
                plan.hero_id or 0, role=plan.role, limit=plan.limit, **common
            )
        if plan.analysis == AnalysisType.COMBINATIONS:
            return self.metrics.combinations(limit=plan.limit, **common)
        if plan.analysis == AnalysisType.PLAYER_OVERVIEW:
            return self.metrics.player_overview(plan.player_key or "", **common)
        raise QueryUnderstandingError(f"Unsupported analysis: {plan.analysis}")

    def _plan_with_rules(self, request: NaturalLanguageQuery) -> QueryPlan:
        question = request.question.strip()
        start_date, end_date = self._extract_dates(question, request.start_date, request.end_date)
        role = request.role or next(
            (name for name in ("对抗路", "打野", "中路", "发育路", "游走") if name in question),
            None,
        )

        players = sorted(
            self.metrics.players(), key=lambda item: len(item["player_name"]), reverse=True
        )
        heroes = sorted(
            self.metrics.heroes(), key=lambda item: len(item["hero_name"]), reverse=True
        )
        player = next((item for item in players if item["player_name"] in question), None)
        hero = next((item for item in heroes if item["hero_name"] in question), None)

        if any(word in question for word in ("组合", "双人组", "体系")) and hero is None:
            return QueryPlan(
                entity_type=EntityType.GLOBAL,
                analysis=AnalysisType.COMBINATIONS,
                start_date=start_date,
                end_date=end_date,
                role=role,
            )
        if player and ("选手" in question or hero is None):
            return QueryPlan(
                entity_type=EntityType.PLAYER,
                analysis=AnalysisType.PLAYER_OVERVIEW,
                player_key=player["player_key"],
                start_date=start_date,
                end_date=end_date,
                role=role,
            )
        if not hero:
            raise QueryUnderstandingError("没有识别到英雄或选手，请在问题中写出完整名称。")

        analysis = AnalysisType.HERO_OVERVIEW
        if any(word in question for word in ("对位", "克制", "交手")):
            analysis = AnalysisType.MATCHUPS
        elif any(word in question for word in ("队友", "搭配", "一起上场")):
            analysis = AnalysisType.TEAMMATES
        elif any(word in question for word in ("出装", "装备")):
            analysis = AnalysisType.BUILDS
        elif any(word in question for word in ("铭文", "符文")):
            analysis = AnalysisType.RUNES
        return QueryPlan(
            entity_type=EntityType.HERO,
            analysis=analysis,
            hero_id=hero["hero_id"],
            start_date=start_date,
            end_date=end_date,
            role=role,
        )

    def _plan_with_llm(self, request: NaturalLanguageQuery, settings: Settings) -> QueryPlan:
        heroes = [{"id": row["hero_id"], "name": row["hero_name"]} for row in self.metrics.heroes()]
        players = [
            {"key": row["player_key"], "name": row["player_name"]} for row in self.metrics.players()
        ]
        schema = QueryPlan.model_json_schema()
        prompt = (
            "把用户问题转换为一个查询计划。只返回 JSON，不能返回 SQL。"
            f"\nQueryPlan JSON Schema: {json.dumps(schema, ensure_ascii=False)}"
            f"\n可用英雄: {json.dumps(heroes, ensure_ascii=False)}"
            f"\n可用选手: {json.dumps(players, ensure_ascii=False)}"
            f"\n用户问题: {request.question}"
        )
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        response = httpx.post(
            settings.llm_endpoint or "",
            headers=headers,
            timeout=settings.request_timeout_seconds,
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": "你是电竞统计查询规划器。"},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        plan_data = json.loads(content)
        plan_data.setdefault("start_date", request.start_date)
        plan_data.setdefault("end_date", request.end_date)
        plan_data.setdefault("role", request.role)
        return QueryPlan.model_validate(plan_data)

    @staticmethod
    def _extract_dates(
        question: str,
        explicit_start: str | None,
        explicit_end: str | None,
    ) -> tuple[str | None, str | None]:
        if explicit_start or explicit_end:
            return explicit_start, explicit_end
        dates = re.findall(r"20\d{2}[-/.年]\d{1,2}(?:[-/.月]\d{1,2}日?)?", question)
        normalized: list[str] = []
        for value in dates[:2]:
            parts = [part for part in re.split(r"[-/.年月日]", value) if part]
            if len(parts) == 2:
                parts.append("1")
            if len(parts) == 3:
                normalized.append(f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}")
        if normalized:
            return normalized[0], normalized[-1] if len(normalized) > 1 else None
        today = date.today()
        if "近两年" in question or "过去两年" in question:
            return (today - timedelta(days=730)).isoformat(), today.isoformat()
        if "近一年" in question or "过去一年" in question:
            return (today - timedelta(days=365)).isoformat(), today.isoformat()
        if "近半年" in question or "过去半年" in question:
            return (today - timedelta(days=183)).isoformat(), today.isoformat()
        if "近三个月" in question or "过去三个月" in question:
            return (today - timedelta(days=92)).isoformat(), today.isoformat()
        return None, None

    @staticmethod
    def _summarize(plan: QueryPlan, result: dict[str, Any]) -> str:
        if "summary" in result:
            summary = result["summary"]
            if plan.analysis == AnalysisType.PLAYER_OVERVIEW:
                return (
                    f"{summary.get('player_name', '该选手')} 样本 {summary.get('games', 0)} 局，"
                    f"胜率 {summary.get('win_rate', 0)}%，KDA {summary.get('kda', 0)}。"
                )
            return (
                f"{summary.get('hero_name', '该英雄')} 样本 {summary.get('picks', 0)} 局，"
                f"选取率 {summary.get('pick_rate', 0)}%，胜率 {summary.get('win_rate', 0)}%，"
                f"BP率 {summary.get('bp_rate', 0)}%。"
            )
        items = result.get("items", [])
        return f"查询完成，共返回 {len(items)} 条聚合结果，样本量 {result.get('sample_size', 0)}。"
