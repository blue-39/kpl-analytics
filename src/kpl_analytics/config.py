from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_base: str = "https://prod.comp.smoba.qq.com"
    rune_dictionary_url: str = "https://pvp.qq.com/web201605/js/ming.json"
    request_delay_seconds: float = 0.2
    request_timeout_seconds: float = 20.0
    llm_endpoint: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "processed" / "kpl.duckdb"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(os.getenv("KPL_DATA_DIR", _default_data_dir())).expanduser(),
            request_delay_seconds=float(os.getenv("KPL_REQUEST_DELAY", "0.2")),
            request_timeout_seconds=float(os.getenv("KPL_REQUEST_TIMEOUT", "20")),
            llm_endpoint=os.getenv("KPL_LLM_ENDPOINT"),
            llm_api_key=os.getenv("KPL_LLM_API_KEY"),
            llm_model=os.getenv("KPL_LLM_MODEL"),
        )
