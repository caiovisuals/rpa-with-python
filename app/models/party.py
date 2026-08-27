"""Cadastros: autônomo (prestador) e contratante (tomador).

Endereço fica embutido como colunas, não como tabela própria: endereço não é
consultado de forma independente e uma tabela só para ele adicionaria um JOIN
a toda leitura sem nenhum ganho.

**Nota de escopo (ADR-0005):** `workers` é o cadastro de prestadores **sem
vínculo**. Funcionários CLT terão tabela própria quando a folha for construída
— os atributos não se sobrepõem (contrato, cargo, jornada, admissão), e forçar
os dois numa tabela só produziria metade das colunas nulas em cada linha.
"""

from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_column, uuid_pk


class PersonType(Enum):
    """Natureza do contratante. É entrada de cálculo, não decoração (RV08)."""

    PESSOA_FISICA = "pessoa_fisica"
    PESSOA_JURIDICA = "pessoa_juridica"


class BankAccountType(Enum):
    CORRENTE = "corrente"
    POUPANCA = "poupanca"
    PIX = "pix"


class AddressMixin:
    """Endereço, embutido em quem precisa dele."""

    street: Mapped[str | None] = mapped_column(String(200))
    number: Mapped[str | None] = mapped_column(String(20))
    complement: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(8))
    municipality: Mapped[str] = mapped_column(String(100), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)


class Worker(Base, TimestampMixin, AddressMixin):
    """Prestador de serviço sem vínculo empregatício."""

    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), nullable=False)
    pis_nit: Mapped[str | None] = mapped_column(String(11))
    municipal_registration: Mapped[str | None] = mapped_column(String(30))

    # Atributo consumido pelo cálculo. Se ele participa, e como, é a regra RV11,
    # ainda pendente de homologação. A coluna existe; nada a usa ainda.
    dependents_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    bank_accounts: Mapped[list[WorkerBankAccount]] = relationship(
        back_populates="worker", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "cpf", name="uq_workers_organization_id_cpf"),
        CheckConstraint("length(cpf) = 11 AND cpf ~ '^[0-9]+$'", name="cpf_format"),
        CheckConstraint(
            "pis_nit IS NULL OR (length(pis_nit) = 11 AND pis_nit ~ '^[0-9]+$')",
            name="pis_nit_format",
        ),
        CheckConstraint("dependents_count >= 0", name="dependents_count_non_negative"),
        CheckConstraint("length(uf) = 2", name="uf_format"),
        Index("ix_workers_organization_id_full_name", "organization_id", "full_name"),
    )


class WorkerBankAccount(Base, TimestampMixin):
    """Dados bancários do autônomo.

    Tabela separada de propósito: é o dado mais sensível do cadastro (RNF04).
    Separá-lo permite restringir o acesso por papel e auditar a leitura sem
    disparar auditoria a cada consulta de nome.

    As colunas terminadas em ``_encrypted`` guardam o valor cifrado pela
    aplicação (TASK-102, Fase 8). Enquanto a criptografia não existir, esta
    tabela não deve receber dado real.
    """

    __tablename__ = "worker_bank_accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="CASCADE"), nullable=False
    )
    account_type: Mapped[BankAccountType] = mapped_column(
        enum_column(BankAccountType, "bank_account_type"), nullable=False
    )
    bank_code: Mapped[str | None] = mapped_column(String(10))
    agency_encrypted: Mapped[str | None] = mapped_column(String(512))
    account_encrypted: Mapped[str | None] = mapped_column(String(512))
    pix_key_encrypted: Mapped[str | None] = mapped_column(String(512))

    worker: Mapped[Worker] = relationship(back_populates="bank_accounts")

    __table_args__ = (Index("ix_worker_bank_accounts_worker_id", "worker_id"),)


class Contractor(Base, TimestampMixin, AddressMixin):
    """Tomador do serviço."""

    __tablename__ = "contractors"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(200))
    document: Mapped[str] = mapped_column(String(14), nullable=False)
    document_type: Mapped[PersonType] = mapped_column(
        enum_column(PersonType, "person_type"), nullable=False
    )
    municipal_registration: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "document", name="uq_contractors_organization_id_document"
        ),
        CheckConstraint(
            "(document_type = 'pessoa_fisica' AND length(document) = 11)"
            " OR (document_type = 'pessoa_juridica' AND length(document) = 14)",
            name="document_length_matches_type",
        ),
        CheckConstraint("document ~ '^[0-9]+$'", name="document_format"),
        CheckConstraint("length(uf) = 2", name="uf_format"),
        Index("ix_contractors_organization_id_legal_name", "organization_id", "legal_name"),
    )
