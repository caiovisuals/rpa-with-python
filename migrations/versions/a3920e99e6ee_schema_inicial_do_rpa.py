"""Schema inicial do RPA.

Cobre TASK-020 a TASK-028: as 14 tabelas do modelo, com constraints e índices.

REVISÃO MANUAL DO AUTOGENERATE (CLAUDE.md, regra 13). O que o Alembic gerou
sozinho foi conferido linha a linha, e **duas coisas faltavam**:

1. ``CREATE EXTENSION btree_gist`` — a constraint de exclusão que impede
   vigências sobrepostas usa ``=`` sobre uuid e texto dentro de um índice GIST,
   o que exige a extensão. Sem ela a migration falha na criação de
   ``tax_rule_sets``. O autogenerate não enxerga extensões.
2. A garantia append-only de ``audit_logs`` — implementada aqui como gatilho,
   e não como ``REVOKE``, para não depender do nome do papel de aplicação em
   cada ambiente. Uma trilha que a própria aplicação pode reescrever não prova
   nada (RNF05).

A reversão foi testada: ``upgrade head`` seguido de ``downgrade base`` devolve
o banco ao estado vazio.

Revision ID: a3920e99e6ee
Revises:
Create Date: 2026-08-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a3920e99e6ee"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Gatilho que torna audit_logs append-only. Bloqueia UPDATE e DELETE para
# qualquer papel, inclusive o dono da tabela.
AUDIT_APPEND_ONLY_FUNCTION = """
CREATE OR REPLACE FUNCTION audit_logs_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs e append-only: % nao e permitido', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
"""

AUDIT_APPEND_ONLY_TRIGGER = """
CREATE TRIGGER trg_audit_logs_append_only
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION audit_logs_append_only();
"""


def upgrade() -> None:
    """Cria o schema inicial."""
    # Necessária para a constraint de exclusão de vigências em tax_rule_sets.
    # Acrescentada na revisão manual: o autogenerate não detecta extensões.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("legal_name", sa.String(length=200), nullable=False),
        sa.Column("document", sa.String(length=14), nullable=False),
        sa.Column(
            "settings", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("document", name="uq_organizations_document"),
    )
    op.create_table(
        "contractors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("legal_name", sa.String(length=200), nullable=False),
        sa.Column("trade_name", sa.String(length=200), nullable=True),
        sa.Column("document", sa.String(length=14), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "pessoa_fisica", "pessoa_juridica", name="person_type", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("municipal_registration", sa.String(length=30), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("street", sa.String(length=200), nullable=True),
        sa.Column("number", sa.String(length=20), nullable=True),
        sa.Column("complement", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=8), nullable=True),
        sa.Column("municipality", sa.String(length=100), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.CheckConstraint(
            "(document_type = 'pessoa_fisica' AND length(document) = 11) OR (document_type = 'pessoa_juridica' AND length(document) = 14)",
            name=op.f("ck_contractors_document_length_matches_type"),
        ),
        sa.CheckConstraint("document ~ '^[0-9]+$'", name=op.f("ck_contractors_document_format")),
        sa.CheckConstraint("length(uf) = 2", name=op.f("ck_contractors_uf_format")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_contractors_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contractors")),
        sa.UniqueConstraint(
            "organization_id", "document", name="uq_contractors_organization_id_document"
        ),
    )
    op.create_index(
        "ix_contractors_organization_id_legal_name",
        "contractors",
        ["organization_id", "legal_name"],
        unique=False,
    )
    op.create_table(
        "number_sequences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum("rpa", name="document_type", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("series", sa.String(length=10), server_default="A", nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "last_number >= 0", name=op.f("ck_number_sequences_last_number_non_negative")
        ),
        sa.CheckConstraint(
            "year BETWEEN 1900 AND 2199", name=op.f("ck_number_sequences_year_range")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_number_sequences_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_number_sequences")),
        sa.UniqueConstraint(
            "organization_id",
            "document_type",
            "series",
            "year",
            name="uq_number_sequences_organization_id_document_type_series_year",
        ),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "revisor",
                "operador",
                "consulta",
                name="user_role",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_users_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "workers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("pis_nit", sa.String(length=11), nullable=True),
        sa.Column("municipal_registration", sa.String(length=30), nullable=True),
        sa.Column("dependents_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("street", sa.String(length=200), nullable=True),
        sa.Column("number", sa.String(length=20), nullable=True),
        sa.Column("complement", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=8), nullable=True),
        sa.Column("municipality", sa.String(length=100), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.CheckConstraint(
            "length(cpf) = 11 AND cpf ~ '^[0-9]+$'", name=op.f("ck_workers_cpf_format")
        ),
        sa.CheckConstraint(
            "pis_nit IS NULL OR (length(pis_nit) = 11 AND pis_nit ~ '^[0-9]+$')",
            name=op.f("ck_workers_pis_nit_format"),
        ),
        sa.CheckConstraint(
            "dependents_count >= 0", name=op.f("ck_workers_dependents_count_non_negative")
        ),
        sa.CheckConstraint("length(uf) = 2", name=op.f("ck_workers_uf_format")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_workers_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workers")),
        sa.UniqueConstraint("organization_id", "cpf", name="uq_workers_organization_id_cpf"),
    )
    op.create_index(
        "ix_workers_organization_id_full_name",
        "workers",
        ["organization_id", "full_name"],
        unique=False,
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_audit_logs_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(
        "ix_audit_logs_organization_id_entity_type_entity_id_created_at",
        "audit_logs",
        ["organization_id", "entity_type", "entity_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_organization_id_user_id_created_at",
        "audit_logs",
        ["organization_id", "user_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("worker_id", sa.UUID(), nullable=False),
        sa.Column("contractor_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "rascunho",
                "em_revisao",
                "emitido",
                "entregue",
                "pago",
                "cancelado",
                "descartado",
                name="receipt_status",
                native_enum=False,
                length=32,
            ),
            server_default="rascunho",
            nullable=False,
        ),
        sa.Column(
            "document_mode",
            sa.Enum("simulacao", "oficial", name="document_mode", native_enum=False, length=32),
            server_default="simulacao",
            nullable=False,
        ),
        sa.Column("series", sa.String(length=10), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("competence_year", sa.Integer(), nullable=False),
        sa.Column("competence_month", sa.Integer(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("gross_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "deductions_total",
            sa.Numeric(precision=14, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "additions_total", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False
        ),
        sa.Column("net_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("worker_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("worker_cpf_snapshot", sa.String(length=11), nullable=True),
        sa.Column("worker_pis_nit_snapshot", sa.String(length=11), nullable=True),
        sa.Column("worker_address_snapshot", sa.Text(), nullable=True),
        sa.Column("contractor_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("contractor_document_snapshot", sa.String(length=14), nullable=True),
        sa.Column("contractor_address_snapshot", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column("issued_by_id", sa.UUID(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_by_id", sa.UUID(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_id", sa.UUID(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("replaces_id", sa.UUID(), nullable=True),
        sa.Column("paid_at", sa.Date(), nullable=True),
        sa.Column("payment_method", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status <> 'cancelado' OR (cancel_reason IS NOT NULL AND btrim(cancel_reason) <> '' AND cancelled_at IS NOT NULL AND cancelled_by_id IS NOT NULL)",
            name=op.f("ck_receipts_cancelled_requires_reason"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('cancelado', 'emitido', 'entregue', 'pago') OR (number IS NOT NULL AND series IS NOT NULL AND year IS NOT NULL AND issued_at IS NOT NULL AND issued_by_id IS NOT NULL)",
            name=op.f("ck_receipts_numbered_requires_numbering"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('cancelado', 'emitido', 'entregue', 'pago') OR (worker_name_snapshot IS NOT NULL AND worker_cpf_snapshot IS NOT NULL AND contractor_name_snapshot IS NOT NULL AND contractor_document_snapshot IS NOT NULL)",
            name=op.f("ck_receipts_numbered_requires_snapshot"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('cancelado', 'emitido', 'entregue', 'pago') OR document_mode = 'oficial'",
            name=op.f("ck_receipts_numbered_requires_official_mode"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('cancelado', 'entregue', 'pago') OR status = 'cancelado' OR delivered_at IS NOT NULL",
            name=op.f("ck_receipts_immutable_requires_delivery"),
        ),
        sa.CheckConstraint(
            "additions_total >= 0", name=op.f("ck_receipts_additions_total_non_negative")
        ),
        sa.CheckConstraint(
            "competence_month BETWEEN 1 AND 12", name=op.f("ck_receipts_competence_month_range")
        ),
        sa.CheckConstraint(
            "competence_year BETWEEN 1900 AND 2199", name=op.f("ck_receipts_competence_year_range")
        ),
        sa.CheckConstraint(
            "deductions_total >= 0", name=op.f("ck_receipts_deductions_total_non_negative")
        ),
        sa.CheckConstraint("gross_amount > 0", name=op.f("ck_receipts_gross_amount_positive")),
        sa.CheckConstraint(
            "net_amount = gross_amount - deductions_total + additions_total",
            name=op.f("ck_receipts_net_amount_matches_parts"),
        ),
        sa.CheckConstraint("net_amount >= 0", name=op.f("ck_receipts_net_amount_non_negative")),
        sa.CheckConstraint(
            "replaces_id IS NULL OR replaces_id <> id",
            name=op.f("ck_receipts_does_not_replace_itself"),
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_id"],
            ["users.id"],
            name=op.f("fk_receipts_cancelled_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contractor_id"],
            ["contractors.id"],
            name=op.f("fk_receipts_contractor_id_contractors"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_receipts_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["delivered_by_id"],
            ["users.id"],
            name=op.f("fk_receipts_delivered_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by_id"],
            ["users.id"],
            name=op.f("fk_receipts_issued_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_receipts_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["replaces_id"],
            ["receipts.id"],
            name=op.f("fk_receipts_replaces_id_receipts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["workers.id"],
            name=op.f("fk_receipts_worker_id_workers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipts")),
    )
    op.create_index(
        "ix_receipts_organization_id_contractor_id",
        "receipts",
        ["organization_id", "contractor_id"],
        unique=False,
    )
    op.create_index(
        "ix_receipts_organization_id_status_competence",
        "receipts",
        ["organization_id", "status", "competence_year", "competence_month"],
        unique=False,
    )
    op.create_index(
        "ix_receipts_organization_id_worker_id_competence",
        "receipts",
        ["organization_id", "worker_id", "competence_year", "competence_month"],
        unique=False,
    )
    op.create_index(
        "uq_receipts_organization_id_series_year_number",
        "receipts",
        ["organization_id", "series", "year", "number"],
        unique=True,
        postgresql_where="number IS NOT NULL",
    )
    op.create_table(
        "tax_rule_sets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("tax_type", sa.String(length=30), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column(
            "approval_status",
            sa.Enum(
                "provisorio", "homologado", name="approval_status", native_enum=False, length=32
            ),
            server_default="provisorio",
            nullable=False,
        ),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("approved_by", sa.String(length=200), nullable=True),
        sa.Column("approved_at", sa.Date(), nullable=True),
        sa.Column("loaded_by_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        postgresql.ExcludeConstraint(
            (sa.column("organization_id"), "="),
            (sa.column("tax_type"), "="),
            (sa.text("daterange(valid_from, valid_to, '[)')"), "&&"),
            using="gist",
            name="ex_tax_rule_sets_no_overlapping_validity",
        ),
        sa.CheckConstraint(
            "approval_status <> 'homologado' OR (source_reference IS NOT NULL AND approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name=op.f("ck_tax_rule_sets_homologation_is_complete"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from", name=op.f("ck_tax_rule_sets_valid_period")
        ),
        sa.ForeignKeyConstraint(
            ["loaded_by_id"],
            ["users.id"],
            name=op.f("fk_tax_rule_sets_loaded_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_tax_rule_sets_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tax_rule_sets")),
    )
    op.create_index(
        "ix_tax_rule_sets_organization_id_tax_type_valid_from",
        "tax_rule_sets",
        ["organization_id", "tax_type", "valid_from"],
        unique=False,
    )
    op.create_table(
        "worker_bank_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("worker_id", sa.UUID(), nullable=False),
        sa.Column(
            "account_type",
            sa.Enum(
                "corrente",
                "poupanca",
                "pix",
                name="bank_account_type",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("bank_code", sa.String(length=10), nullable=True),
        sa.Column("agency_encrypted", sa.String(length=512), nullable=True),
        sa.Column("account_encrypted", sa.String(length=512), nullable=True),
        sa.Column("pix_key_encrypted", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["workers.id"],
            name=op.f("fk_worker_bank_accounts_worker_id_workers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_worker_bank_accounts")),
    )
    op.create_index(
        "ix_worker_bank_accounts_worker_id", "worker_bank_accounts", ["worker_id"], unique=False
    )
    op.create_table(
        "receipt_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("rascunho", "oficial", name="document_kind", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("template_version", sa.String(length=20), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by_id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "length(sha256) = 64 AND sha256 ~ '^[0-9a-f]+$'",
            name=op.f("ck_receipt_documents_sha256_format"),
        ),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_receipt_documents_size_bytes_positive")),
        sa.ForeignKeyConstraint(
            ["generated_by_id"],
            ["users.id"],
            name=op.f("fk_receipt_documents_generated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name=op.f("fk_receipt_documents_receipt_id_receipts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipt_documents")),
        sa.UniqueConstraint("storage_path", name="uq_receipt_documents_storage_path"),
    )
    op.create_index(
        "ix_receipt_documents_receipt_id_generated_at",
        "receipt_documents",
        ["receipt_id", "generated_at"],
        unique=False,
    )
    op.create_table(
        "receipt_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "kind",
            sa.Enum("desconto", "acrescimo", name="deduction_kind", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column(
            "origin",
            sa.Enum("automatica", "manual", name="deduction_origin", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("base_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("rate_applied", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("calc_note", sa.Text(), nullable=True),
        sa.Column("rule_set_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(origin = 'automatica' AND rule_set_id IS NOT NULL) OR (origin = 'manual' AND calc_note IS NOT NULL AND btrim(calc_note) <> '')",
            name=op.f("ck_receipt_entries_entry_has_provenance"),
        ),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_receipt_entries_amount_non_negative")),
        sa.CheckConstraint(
            "base_amount IS NULL OR amount <= base_amount",
            name=op.f("ck_receipt_entries_amount_within_base"),
        ),
        sa.CheckConstraint(
            "rate_applied IS NULL OR (rate_applied >= 0 AND rate_applied <= 1)",
            name=op.f("ck_receipt_entries_rate_is_a_fraction"),
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name=op.f("fk_receipt_entries_receipt_id_receipts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["tax_rule_sets.id"],
            name=op.f("fk_receipt_entries_rule_set_id_tax_rule_sets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipt_entries")),
        sa.UniqueConstraint(
            "receipt_id", "position", name="uq_receipt_entries_receipt_id_position"
        ),
    )
    op.create_index(
        "ix_receipt_entries_receipt_id", "receipt_entries", ["receipt_id"], unique=False
    )
    op.create_table(
        "receipt_services",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("gross_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(description) <> ''", name=op.f("ck_receipt_services_description_not_blank")
        ),
        sa.CheckConstraint(
            "gross_amount > 0", name=op.f("ck_receipt_services_gross_amount_positive")
        ),
        sa.CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name=op.f("ck_receipt_services_period_order"),
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name=op.f("fk_receipt_services_receipt_id_receipts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipt_services")),
        sa.UniqueConstraint(
            "receipt_id", "position", name="uq_receipt_services_receipt_id_position"
        ),
    )
    op.create_table(
        "receipt_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "rascunho",
                "em_revisao",
                "emitido",
                "entregue",
                "pago",
                "cancelado",
                "descartado",
                name="receipt_status",
                native_enum=False,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "rascunho",
                "em_revisao",
                "emitido",
                "entregue",
                "pago",
                "cancelado",
                "descartado",
                name="receipt_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status <> to_status",
            name=op.f("ck_receipt_status_history_status_changed"),
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["receipts.id"],
            name=op.f("fk_receipt_status_history_receipt_id_receipts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_receipt_status_history_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipt_status_history")),
    )
    op.create_index(
        "ix_receipt_status_history_receipt_id_created_at",
        "receipt_status_history",
        ["receipt_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "tax_rule_brackets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("rule_set_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("min_base", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("max_base", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("rate", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column("deduction", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("cap", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column(
            "meta", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.CheckConstraint(
            "cap IS NULL OR cap >= 0", name=op.f("ck_tax_rule_brackets_cap_non_negative")
        ),
        sa.CheckConstraint(
            "deduction IS NULL OR deduction >= 0",
            name=op.f("ck_tax_rule_brackets_deduction_non_negative"),
        ),
        sa.CheckConstraint(
            "max_base IS NULL OR min_base IS NULL OR max_base > min_base",
            name=op.f("ck_tax_rule_brackets_base_range"),
        ),
        sa.CheckConstraint(
            "min_base IS NULL OR min_base >= 0",
            name=op.f("ck_tax_rule_brackets_min_base_non_negative"),
        ),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_tax_rule_brackets_position_non_negative")
        ),
        sa.CheckConstraint(
            "rate IS NULL OR (rate >= 0 AND rate <= 1)",
            name=op.f("ck_tax_rule_brackets_rate_is_a_fraction"),
        ),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["tax_rule_sets.id"],
            name=op.f("fk_tax_rule_brackets_rule_set_id_tax_rule_sets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tax_rule_brackets")),
        sa.UniqueConstraint(
            "rule_set_id", "position", name="uq_tax_rule_brackets_rule_set_id_position"
        ),
    )
    # ### end Alembic commands ###

    # Acrescentado na revisão manual (RNF05).
    op.execute(AUDIT_APPEND_ONLY_FUNCTION)
    op.execute(AUDIT_APPEND_ONLY_TRIGGER)


def downgrade() -> None:
    """Remove o schema inicial."""
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_append_only()")

    op.drop_table("tax_rule_brackets")
    op.drop_index(
        "ix_receipt_status_history_receipt_id_created_at", table_name="receipt_status_history"
    )
    op.drop_table("receipt_status_history")
    op.drop_table("receipt_services")
    op.drop_index("ix_receipt_entries_receipt_id", table_name="receipt_entries")
    op.drop_table("receipt_entries")
    op.drop_index("ix_receipt_documents_receipt_id_generated_at", table_name="receipt_documents")
    op.drop_table("receipt_documents")
    op.drop_index("ix_worker_bank_accounts_worker_id", table_name="worker_bank_accounts")
    op.drop_table("worker_bank_accounts")
    op.drop_index(
        "ix_tax_rule_sets_organization_id_tax_type_valid_from", table_name="tax_rule_sets"
    )
    op.drop_table("tax_rule_sets")
    op.drop_index(
        "uq_receipts_organization_id_series_year_number",
        table_name="receipts",
        postgresql_where="number IS NOT NULL",
    )
    op.drop_index("ix_receipts_organization_id_worker_id_competence", table_name="receipts")
    op.drop_index("ix_receipts_organization_id_status_competence", table_name="receipts")
    op.drop_index("ix_receipts_organization_id_contractor_id", table_name="receipts")
    op.drop_table("receipts")
    op.drop_index("ix_audit_logs_organization_id_user_id_created_at", table_name="audit_logs")
    op.drop_index(
        "ix_audit_logs_organization_id_entity_type_entity_id_created_at", table_name="audit_logs"
    )
    op.drop_table("audit_logs")
    op.drop_index("ix_workers_organization_id_full_name", table_name="workers")
    op.drop_table("workers")
    op.drop_table("users")
    op.drop_table("number_sequences")
    op.drop_index("ix_contractors_organization_id_legal_name", table_name="contractors")
    op.drop_table("contractors")
    op.drop_table("organizations")
    # ### end Alembic commands ###
    # btree_gist não é removida: outro objeto do banco pode depender dela,
    # e um downgrade não deve derrubar o que não criou sozinho.
