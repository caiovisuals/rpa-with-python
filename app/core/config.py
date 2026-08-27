"""Configuração por ambiente.

Falha rápido: se faltar variável obrigatória, o processo não sobe. Um sistema
que arranca com configuração pela metade descobre o problema em produção
(TASK-014).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


class ConfigError(RuntimeError):
    """Configuração ausente ou inválida."""


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"variável de ambiente obrigatória ausente: {name}. "
            "Veja .env.example para a lista completa."
        )
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuração da aplicação, lida do ambiente."""

    app_env: str
    database_url: str

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            app_env=os.environ.get("APP_ENV", "development").strip() or "development",
            database_url=_require("DATABASE_URL"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Configuração em cache. Use `get_settings.cache_clear()` em teste."""
    return Settings.from_environment()
