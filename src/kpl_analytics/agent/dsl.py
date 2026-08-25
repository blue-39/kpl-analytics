from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class EntityType(StrEnum):
    HERO = "hero"
    PLAYER = "player"
    GLOBAL = "global"


class AnalysisType(StrEnum):
    HERO_OVERVIEW = "hero_overview"
    MATCHUPS = "matchups"
    TEAMMATES = "teammates"
    BUILDS = "builds"
    RUNES = "runes"
    COMBINATIONS = "combinations"
    PLAYER_OVERVIEW = "player_overview"


class QueryPlan(BaseModel):
    entity_type: EntityType
    analysis: AnalysisType
    hero_id: int | None = None
    player_key: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    league_id: str | None = None
    role: str | None = None
    hero_ids: list[int] = Field(default_factory=list, max_length=3)
    focus_hero_id: int | None = None
    combination_size: int = Field(default=2, ge=2, le=3)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_entity(self) -> QueryPlan:
        hero_analyses = {
            AnalysisType.HERO_OVERVIEW,
            AnalysisType.MATCHUPS,
            AnalysisType.TEAMMATES,
            AnalysisType.BUILDS,
            AnalysisType.RUNES,
        }
        if self.analysis in hero_analyses and self.hero_id is None:
            raise ValueError("hero_id is required for a hero analysis")
        if self.analysis == AnalysisType.PLAYER_OVERVIEW and not self.player_key:
            raise ValueError("player_key is required for a player analysis")
        if self.analysis == AnalysisType.COMBINATIONS and self.hero_ids:
            if len(set(self.hero_ids)) != self.combination_size:
                raise ValueError(
                    "hero_ids must match combination_size and contain distinct heroes"
                )
        if self.hero_ids and self.focus_hero_id is not None:
            raise ValueError("hero_ids and focus_hero_id cannot be used together")
        return self


class NaturalLanguageQuery(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    start_date: str | None = None
    end_date: str | None = None
    league_id: str | None = None
    role: str | None = None
