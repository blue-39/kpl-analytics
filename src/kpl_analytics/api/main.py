from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from shutil import copy2
from threading import Lock
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, SecretStr, field_validator

from kpl_analytics.agent.dsl import NaturalLanguageQuery
from kpl_analytics.agent.service import QueryAgent, QueryUnderstandingError
from kpl_analytics.api.admin import JobBusyError, JobManager
from kpl_analytics.collector.client import KPLAPIError, KPLClient
from kpl_analytics.collector.leagues import selectable_leagues
from kpl_analytics.collector.pipeline import BackfillPipeline
from kpl_analytics.config import Settings
from kpl_analytics.warehouse.audit import audit_warehouse
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


class BackfillRequest(BaseModel):
    league_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("league_ids")
    @classmethod
    def valid_league_ids(cls, values: list[str]) -> list[str]:
        if any(not value.isdigit() or len(value) > 20 for value in values):
            raise ValueError("赛事 ID 格式不正确。")
        return list(dict.fromkeys(values))


class LLMConfiguration(BaseModel):
    endpoint: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr = Field(min_length=1, max_length=2000)


def _validated_llm_endpoint(value: str) -> str:
    endpoint = value.strip()
    parsed = urlparse(endpoint)
    is_local_http = parsed.scheme == "http" and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }
    if not parsed.hostname or (parsed.scheme != "https" and not is_local_http):
        raise HTTPException(
            status_code=422,
            detail="模型 Endpoint 必须使用 HTTPS；本机 localhost/127.0.0.1 可使用 HTTP。",
        )
    return endpoint


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    warehouse = Warehouse(active_settings)
    metrics = MetricsService(warehouse)
    agent = QueryAgent(metrics, active_settings)
    jobs = JobManager()
    data_lock = Lock()

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

    def get_metrics() -> Iterator[MetricsService]:
        data_lock.acquire()
        try:
            yield metrics
        finally:
            data_lock.release()

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
            with data_lock:
                return agent.ask(request)
        except QueryUnderstandingError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @api.get("/api/admin/status")
    def admin_status() -> dict:
        raw_dir = active_settings.raw_dir
        with data_lock:
            current_meta = metrics.metadata()
        return {
            "raw_archive_exists": (raw_dir / "leagues" / "index.json").exists(),
            "raw_detail_files": sum(1 for _ in (raw_dir / "details").glob("*.json")),
            "raw_match_files": sum(1 for _ in (raw_dir / "matches").glob("*.json")),
            "database_exists": active_settings.database_path.exists(),
            "meta": current_meta,
        }

    @api.get("/api/admin/job")
    def current_job() -> dict:
        return jobs.snapshot()

    @api.get("/api/admin/leagues")
    def available_leagues() -> dict:
        try:
            with KPLClient(active_settings) as client:
                items = selectable_leagues(client.leagues())
        except KPLAPIError as exc:
            raise HTTPException(status_code=502, detail="暂时无法读取公开赛事列表。") from exc
        return {"items": items}

    @api.post("/api/admin/backfill", status_code=202)
    def start_backfill(request: BackfillRequest) -> dict:
        def operation(update) -> dict:
            summary = BackfillPipeline(active_settings).backfill(
                league_ids=request.league_ids,
                progress=update,
            )
            return asdict(summary)

        try:
            return jobs.start("backfill", operation)
        except JobBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/admin/build", status_code=202)
    def start_build() -> dict:
        if not (active_settings.raw_dir / "leagues" / "index.json").exists():
            raise HTTPException(status_code=409, detail="尚无原始归档，请先执行比赛回填。")

        def operation(update) -> dict:
            update("正在从原始 JSON 构建 DuckDB", {"stage": "build"})
            database_path = active_settings.database_path
            backup_path = database_path.with_suffix(".duckdb.before-build.bak")
            with data_lock:
                if database_path.exists():
                    copy2(database_path, backup_path)
                try:
                    result = warehouse.rebuild_from_raw()
                except Exception:
                    if backup_path.exists():
                        backup_path.replace(database_path)
                    raise
                finally:
                    if backup_path.exists():
                        backup_path.unlink()
            return result

        try:
            return jobs.start("build", operation)
        except JobBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/admin/audit", status_code=202)
    def start_audit() -> dict:
        def operation(update) -> dict:
            update("正在检查小局、队伍、BP 与英雄完整性", {"stage": "audit"})
            with data_lock:
                return audit_warehouse(warehouse)

        try:
            return jobs.start("audit", operation)
        except JobBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/settings/llm")
    def llm_status() -> dict:
        return agent.llm_status()

    @api.post("/api/settings/llm")
    def configure_llm(request: LLMConfiguration) -> dict:
        endpoint = _validated_llm_endpoint(request.endpoint)
        model = request.model.strip()
        if not model:
            raise HTTPException(status_code=422, detail="模型名称不能为空。")
        return agent.configure_llm(
            endpoint=endpoint,
            api_key=request.api_key.get_secret_value(),
            model=model,
        )

    @api.post("/api/settings/llm/clear")
    def clear_llm() -> dict:
        return agent.clear_runtime_llm()

    return api


app = create_app()
