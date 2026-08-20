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
