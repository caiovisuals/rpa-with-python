"""O schema aplicado pela migration confere com os modelos?

Se este teste falhar, alguém alterou um modelo sem gerar a migration
correspondente — e o banco de produção ficaria diferente do código.
"""

from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect

from app.models import Base

TABELAS_ESPERADAS = {
    "audit_logs",
    "contractors",
    "number_sequences",
    "organizations",
    "receipt_documents",
    "receipt_entries",
    "receipt_services",
    "receipt_status_history",
    "receipts",
    "tax_rule_brackets",
    "tax_rule_sets",
    "users",
    "worker_bank_accounts",
    "workers",
}


def test_migration_cria_todas_as_tabelas(engine: Engine):
    tabelas = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert tabelas == TABELAS_ESPERADAS


def test_nao_ha_diferenca_entre_modelos_e_banco(engine: Engine, alembic_config: Config):
    """Nenhuma alteração de modelo ficou sem migration."""
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection, opts={"compare_type": True, "compare_server_default": True}
        )
        diferencas = compare_metadata(context, Base.metadata)
    assert diferencas == [], f"modelos e banco divergem: {diferencas}"


def test_extensao_btree_gist_instalada(engine: Engine):
    """A constraint de vigências depende dela; sem ela a migration teria falhado."""
    from sqlalchemy import text

    with engine.connect() as connection:
        instalada = connection.execute(
            text("SELECT count(*) FROM pg_extension WHERE extname = 'btree_gist'")
        ).scalar()
    assert instalada == 1


def test_indice_unico_de_numeracao_e_parcial(engine: Engine):
    """Rascunho não tem número; o índice único precisa ignorá-los."""
    indices = inspect(engine).get_indexes("receipts")
    numeracao = next(
        i for i in indices if i["name"] == "uq_receipts_organization_id_series_year_number"
    )
    assert numeracao["unique"] is True
    assert "number IS NOT NULL" in str(numeracao.get("dialect_options", {}))
