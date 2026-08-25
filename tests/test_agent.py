from __future__ import annotations

import pytest

from kpl_analytics.agent.dsl import AnalysisType, NaturalLanguageQuery
from kpl_analytics.agent.service import QueryAgent, QueryUnderstandingError
from kpl_analytics.config import Settings
from kpl_analytics.warehouse.metrics import MetricsService


def test_rule_planner_executes_a_hero_matchup_query(warehouse):
    agent = QueryAgent(MetricsService(warehouse), Settings(data_dir=warehouse.settings.data_dir))
    response = agent.ask(NaturalLanguageQuery(question="近两年镜在打野位的对位情况怎么样？"))

    assert response["planner"] == "rules"
    assert response["plan"]["analysis"] == AnalysisType.MATCHUPS
    assert response["plan"]["hero_id"] == 531
    assert response["plan"]["role"] == "打野"
    assert response["result"]["items"]


def test_rule_planner_rejects_an_unknown_entity(warehouse):
    agent = QueryAgent(MetricsService(warehouse), Settings(data_dir=warehouse.settings.data_dir))
    with pytest.raises(QueryUnderstandingError):
        agent.ask(NaturalLanguageQuery(question="一个不存在的英雄胜率是多少"))


def test_rule_planner_understands_league_and_three_hero_combo(warehouse):
    agent = QueryAgent(MetricsService(warehouse), Settings(data_dir=warehouse.settings.data_dir))

    league_query = agent.ask(NaturalLanguageQuery(question="KPL 本地演示赛季镜的胜率"))
    combo_query = agent.ask(
        NaturalLanguageQuery(question="镜、公孙离、鲁班大师三英雄组合表现")
    )
    focused_combo_query = agent.ask(NaturalLanguageQuery(question="镜的英雄组合表现"))

    assert league_query["plan"]["league_id"] == "demo-kpl"
    assert league_query["result"]["filters"]["league_id"] == "demo-kpl"
    assert combo_query["plan"]["analysis"] == AnalysisType.COMBINATIONS
    assert combo_query["plan"]["combination_size"] == 3
    assert len(combo_query["plan"]["hero_ids"]) == 3
    assert focused_combo_query["plan"]["focus_hero_id"] == 531
    assert all(
        531 in {row["hero1_id"], row["hero2_id"]}
        for row in focused_combo_query["result"]["items"]
    )
