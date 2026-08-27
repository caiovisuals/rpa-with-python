"""Infraestrutura dos testes de integração.

Estes testes rodam contra um **PostgreSQL de verdade**. SQLite não serviria:
metade do que se quer verificar aqui — constraint de exclusão sobre intervalo,
índice único parcial, gatilho, `jsonb` — só existe no PostgreSQL. Testar o
schema contra outro banco provaria a coisa errada.

O schema é criado pela **migration**, não por `create_all`. Assim o que os
testes exercitam é exatamente o que vai para produção; se a migration divergir
dos modelos, os testes quebram — que é o ponto.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

REQUIRED_ENV = "DATABASE_URL"
STRICT_ENV = "RPA_REQUIRE_DB"


def _database_url() -> str:
    url = os.environ.get(REQUIRED_ENV, "").strip()
    if url:
        return url
    mensagem = (
        f"{REQUIRED_ENV} não definida: os testes de integração precisam de um "
        "PostgreSQL. Suba um com `docker compose up db` e exporte a URL."
    )
    if os.environ.get(STRICT_ENV):
        # No CI o banco é obrigatório. Pular aqui esconderia uma suíte inteira
        # atrás de um build verde.
        pytest.fail(mensagem)
    pytest.skip(mensagem, allow_module_level=True)


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", _database_url())
    return config


@pytest.fixture(scope="session")
def engine(alembic_config: Config) -> Iterator[Engine]:
    """Banco limpo, com o schema aplicado pela migration."""
    url = _database_url()
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Sessão isolada: tudo o que o teste escreve é desfeito no fim.

    A transação externa nunca é confirmada, então os testes não interferem uns
    nos outros nem deixam resíduo.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        # Um erro dentro de savepoint pode ter desfeito a transação externa.
        # Reverter uma transação já inativa dispara aviso do SQLAlchemy — e
        # aviso ignorado hoje é bug escondido amanhã.
        if transaction.is_active:
            transaction.rollback()
        connection.close()
