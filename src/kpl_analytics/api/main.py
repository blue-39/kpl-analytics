from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from kpl_analytics.agent.dsl import NaturalLanguageQuery
from kpl_analytics.agent.service import QueryAgent, QueryUnderstandingError
from kpl_analytics.config import Settings
from kpl_analytics.warehouse.database import Warehouse
from kpl_analytics.warehouse.demo import seed_demo
from kpl_analytics.warehouse.metrics import MetricsService


def _ensure_database(warehouse: Warehouse) -> None:
    first_run = not Path(warehouse.settings.database_path).exists()
    warehouse.initialize()
    with warehouse.connect(read_only=True) as connection:
        has_data = connection.execute("SELECT count(*) FROM metadata").fetchone()[0] > 0
    if first_run or not has_data:
        seed_demo(warehouse)


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    warehouse = Warehouse(active_settings)
    metrics = MetricsService(warehouse)
    agent = QueryAgent(metrics, active_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        _ensure_database(warehouse)
        yield

    api = FastAPI(
        title="KPL Analytics API",
        version="0.1.0",
        description="Local-first KPL battle analytics over a DuckDB warehouse.",
        lifespan=lifespan,
    )
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @api.exception_handler(ValueError)
    async def invalid_query_parameter(_, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    def get_metrics() -> MetricsService:
        return metrics

    Metrics = Annotated[MetricsService, Depends(get_metrics)]

    @api.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": str(active_settings.database_path)}

    @api.get("/api/meta")
    def meta(service: Metrics) -> dict:
        return service.metadata()

    @api.get("/api/heroes")
    def heroes(service: Metrics) -> list[dict]:
        return service.heroes()

    @api.get("/api/players")
    def players(service: Metrics) -> list[dict]:
        return service.players()

    @api.get("/api/battles")
    def battles(
        service: Metrics,
        start_date: str | None = None,
        end_date: str | None = None,
        hero_id: int | None = None,
        player_key: str | None = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict:
        return service.recent_battles(start_date, end_date, hero_id, player_key, limit)

    @api.get("/api/battles/{battle_id}")
    def battle_detail(battle_id: str, service: Metrics) -> dict:
        result = service.battle_detail(battle_id)
        if not result:
            raise HTTPException(status_code=404, detail="battle not found")
        return result

    @api.get("/api/heroes/{hero_id}/overview")
    def hero_overview(
        hero_id: int,
        service: Metrics,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
    ) -> dict:
        return service.hero_overview(hero_id, start_date, end_date, role)

    @api.get("/api/heroes/{hero_id}/matchups")
    def hero_matchups(
        hero_id: int,
        service: Metrics,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> dict:
        return service.hero_matchups(hero_id, start_date, end_date, role, limit)

    @api.get("/api/heroes/{hero_id}/teammates")
    def hero_teammates(
        hero_id: int,
        service: Metrics,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> dict:
        return service.hero_teammates(hero_id, start_date, end_date, role, limit)

    @api.get("/api/heroes/{hero_id}/builds")
    def hero_builds(
        hero_id: int,
        service: Metrics,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 12,
    ) -> dict:
        return service.hero_builds(hero_id, start_date, end_date, role, limit)

    @api.get("/api/heroes/{hero_id}/runes")
    def hero_runes(
        hero_id: int,
        service: Metrics,
        start_date: str | None = None,
        end_date: str | None = None,
        role: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> dict:
        return service.hero_runes(hero_id, start_date, end_date, role, limit)

    @api.get("/api/combinations")
    def combinations(
        service: Metrics,
        start_date: str | None = None,
        end_date: str | None = None,
        min_games: Annotated[int, Query(ge=1)] = 2,
        limit: Annotated[int, Query(ge=1, le=100)] = 30,
    ) -> dict:
        return service.combinations(start_date, end_date, min_games, limit)

    @api.get("/api/players/{player_key:path}/overview")
    def player_overview(
        player_key: str,
        service: Metrics,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        return service.player_overview(player_key, start_date, end_date)

    @api.post("/api/query")
    def natural_language_query(request: NaturalLanguageQuery) -> dict:
        try:
            return agent.ask(request)
        except QueryUnderstandingError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return api


app = create_app()
