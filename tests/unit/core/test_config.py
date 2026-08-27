"""Configuração falha rápido, ou descobre o problema em produção."""

import pytest

from app.core.config import ConfigError, Settings, get_settings


class TestSettings:
    def test_le_do_ambiente(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u@h/db")
        settings = Settings.from_environment()
        assert settings.app_env == "production"
        assert settings.database_url == "postgresql+psycopg://u@h/db"

    def test_app_env_tem_padrao_de_desenvolvimento(self, monkeypatch):
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u@h/db")
        assert Settings.from_environment().app_env == "development"

    @pytest.mark.parametrize("valor", [None, "", "   "])
    def test_database_url_ausente_impede_a_partida(self, monkeypatch, valor):
        """Variável obrigatória vazia é o mesmo que ausente."""
        if valor is None:
            monkeypatch.delenv("DATABASE_URL", raising=False)
        else:
            monkeypatch.setenv("DATABASE_URL", valor)
        with pytest.raises(ConfigError, match="DATABASE_URL"):
            Settings.from_environment()

    def test_is_production(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u@h/db")
        monkeypatch.setenv("APP_ENV", "production")
        assert Settings.from_environment().is_production
        monkeypatch.setenv("APP_ENV", "development")
        assert not Settings.from_environment().is_production

    def test_settings_e_imutavel(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u@h/db")
        settings = Settings.from_environment()
        with pytest.raises(AttributeError):
            settings.app_env = "outro"  # type: ignore[misc]


class TestCache:
    def test_get_settings_devolve_a_mesma_instancia(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u@h/db")
        get_settings.cache_clear()
        try:
            assert get_settings() is get_settings()
        finally:
            get_settings.cache_clear()
