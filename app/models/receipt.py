"""O RPA e suas partes.

Duas decisões estruturais estão gravadas aqui como constraint, não como
comentário:

* **Snapshot na emissão.** O recibo copia para dentro de si os dados do
  autônomo e do contratante no instante da emissão. Sem isso, reimprimir um
  recibo de dois anos atrás traria o endereço de hoje — documento contábil
  falsificado por acidente (RNF02).
* **A invariante do líquido.** ``líquido = bruto - descontos + acréscimos`` é
  verificada pelo domínio *e* pelo banco. A aplicação dá a mensagem boa; o
  banco garante que ninguém contorna, nem por script.

As listas de status usadas nas constraints são derivadas do próprio domínio
(`app.domain.receipt.status`), para que banco e código não possam divergir.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.calculation.approval import DocumentMode
from app.domain.receipt.status import IMMUTABLE_STATUSES, NUMBERED_STATUSES, ReceiptStatus
from app.models.base import Base, TimestampMixin, enum_column, uuid_pk


def _sql_list(statuses: frozenset[ReceiptStatus]) -> str:
    """Lista SQL de status, derivada do domínio para não divergir dele."""
    return ", ".join(f"'{status.value}'" for status in sorted(statuses, key=lambda s: s.value))


NUMBERED_SQL = _sql_list(NUMBERED_STATUSES)
IMMUTABLE_SQL = _sql_list(IMMUTABLE_STATUSES)


class DeductionOrigin(Enum):
    """De onde veio um lançamento."""

    AUTOMATICA = "automatica"
    """Calculada pelo motor a partir de parâmetros homologados ou provisórios."""

    MANUAL = "manual"
    """Lançada pelo operador (adiantamento, material, multa). Exige descrição."""


class DeductionKind(Enum):
    """Se o lançamento diminui ou aumenta o valor a receber."""

    DESCONTO = "desconto"
    ACRESCIMO = "acrescimo"


class Receipt(Base, TimestampMixin):
    """Recibo de Pagamento Autônomo. Agregado raiz."""

    __tablename__ = "receipts"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )

    # RESTRICT: não se apaga cadastro que tem recibo. O histórico manda.
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="RESTRICT"), nullable=False
    )
    contractor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contractors.id", ondelete="RESTRICT"), nullable=False
    )

    status: Mapped[ReceiptStatus] = mapped_column(
        enum_column(ReceiptStatus, "receipt_status"),
        nullable=False,
        default=ReceiptStatus.RASCUNHO,
        server_default=ReceiptStatus.RASCUNHO.value,
    )
    document_mode: Mapped[DocumentMode] = mapped_column(
        enum_column(DocumentMode, "document_mode"),
        nullable=False,
        default=DocumentMode.SIMULACAO,
        server_default=DocumentMode.SIMULACAO.value,
    )

    # Numeração: nula até a emissão. Preservada na retificação (ADR-0003).
    series: Mapped[str | None] = mapped_column(String(10))
    year: Mapped[int | None] = mapped_column()
    number: Mapped[int | None] = mapped_column()

    competence_year: Mapped[int] = mapped_column(nullable=False)
    competence_month: Mapped[int] = mapped_column(nullable=False)

    # Data que seleciona a vigência dos parâmetros. **Qual** data cumpre esse
    # papel é a regra RV07, pendente de homologação — por isso é anulável.
    reference_date: Mapped[date | None] = mapped_column(Date)

    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    deductions_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    additions_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # --- snapshot congelado na emissão (RNF02) ------------------------------
    worker_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    worker_cpf_snapshot: Mapped[str | None] = mapped_column(String(11))
    worker_pis_nit_snapshot: Mapped[str | None] = mapped_column(String(11))
    worker_address_snapshot: Mapped[str | None] = mapped_column(Text)
    contractor_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    contractor_document_snapshot: Mapped[str | None] = mapped_column(String(14))
    contractor_address_snapshot: Mapped[str | None] = mapped_column(Text)

    # --- autoria de cada etapa ----------------------------------------------
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    issued_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)

    replaces_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="RESTRICT")
    )

    paid_at: Mapped[date | None] = mapped_column(Date)
    payment_method: Mapped[str | None] = mapped_column(String(50))

    services: Mapped[list[ReceiptService]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )
    entries: Mapped[list[ReceiptEntry]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("gross_amount > 0", name="gross_amount_positive"),
        CheckConstraint("deductions_total >= 0", name="deductions_total_non_negative"),
        CheckConstraint("additions_total >= 0", name="additions_total_non_negative"),
        CheckConstraint("net_amount >= 0", name="net_amount_non_negative"),
        # A RN03 gravada no banco.
        CheckConstraint(
            "net_amount = gross_amount - deductions_total + additions_total",
            name="net_amount_matches_parts",
        ),
        CheckConstraint("competence_month BETWEEN 1 AND 12", name="competence_month_range"),
        CheckConstraint("competence_year BETWEEN 1900 AND 2199", name="competence_year_range"),
        # Status numerado exige numeração completa e autoria da emissão.
        CheckConstraint(
            f"status NOT IN ({NUMBERED_SQL})"
            " OR (number IS NOT NULL AND series IS NOT NULL AND year IS NOT NULL"
            " AND issued_at IS NOT NULL AND issued_by_id IS NOT NULL)",
            name="numbered_requires_numbering",
        ),
        # Status numerado exige o snapshot congelado.
        CheckConstraint(
            f"status NOT IN ({NUMBERED_SQL})"
            " OR (worker_name_snapshot IS NOT NULL AND worker_cpf_snapshot IS NOT NULL"
            " AND contractor_name_snapshot IS NOT NULL"
            " AND contractor_document_snapshot IS NOT NULL)",
            name="numbered_requires_snapshot",
        ),
        # ADR-0004 no banco: documento em simulação nunca alcança estado numerado.
        CheckConstraint(
            f"status NOT IN ({NUMBERED_SQL}) OR document_mode = 'oficial'",
            name="numbered_requires_official_mode",
        ),
        CheckConstraint(
            "status <> 'cancelado'"
            " OR (cancel_reason IS NOT NULL AND btrim(cancel_reason) <> ''"
            " AND cancelled_at IS NOT NULL AND cancelled_by_id IS NOT NULL)",
            name="cancelled_requires_reason",
        ),
        CheckConstraint(
            f"status NOT IN ({IMMUTABLE_SQL}) OR status = 'cancelado' OR delivered_at IS NOT NULL",
            name="immutable_requires_delivery",
        ),
        CheckConstraint("replaces_id IS NULL OR replaces_id <> id", name="does_not_replace_itself"),
        # Numeração única — parcial, porque rascunho não tem número.
        Index(
            "uq_receipts_organization_id_series_year_number",
            "organization_id",
            "series",
            "year",
            "number",
            unique=True,
            postgresql_where="number IS NOT NULL",
        ),
        Index(
            "ix_receipts_organization_id_status_competence",
            "organization_id",
            "status",
            "competence_year",
            "competence_month",
        ),
        Index(
            "ix_receipts_organization_id_worker_id_competence",
            "organization_id",
            "worker_id",
            "competence_year",
            "competence_month",
        ),
        Index("ix_receipts_organization_id_contractor_id", "organization_id", "contractor_id"),
    )


class ReceiptService(Base, TimestampMixin):
    """O serviço prestado.

    Tabela separada, com um registro por recibo no MVP. Já suporta N linhas
    (RF22) sem refatoração: a separação custa um JOIN hoje e evita uma
    migration de dados amanhã.
    """

    __tablename__ = "receipt_services"

    id: Mapped[uuid.UUID] = uuid_pk()
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    receipt: Mapped[Receipt] = relationship(back_populates="services")

    __table_args__ = (
        UniqueConstraint("receipt_id", "position", name="uq_receipt_services_receipt_id_position"),
        CheckConstraint("gross_amount > 0", name="gross_amount_positive"),
        CheckConstraint("btrim(description) <> ''", name="description_not_blank"),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="period_order",
        ),
    )


class ReceiptEntry(Base, TimestampMixin):
    """Um desconto ou acréscimo do recibo. **É a memória de cálculo persistida.**

    Guarda a base, a alíquota aplicada e o conjunto de parâmetros usado, para
    que a conferência do operador (RF11) e a auditoria futura possam reconstruir
    exatamente como se chegou ao valor.
    """

    __tablename__ = "receipt_entries"

    id: Mapped[uuid.UUID] = uuid_pk()
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    kind: Mapped[DeductionKind] = mapped_column(
        enum_column(DeductionKind, "deduction_kind"), nullable=False
    )
    origin: Mapped[DeductionOrigin] = mapped_column(
        enum_column(DeductionOrigin, "deduction_origin"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    rate_applied: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    calc_note: Mapped[str | None] = mapped_column(Text)

    # Qual conjunto de parâmetros produziu este valor. SET NULL nunca: se o
    # conjunto sumisse, a memória de cálculo viraria um número sem procedência.
    rule_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_rule_sets.id", ondelete="RESTRICT")
    )

    receipt: Mapped[Receipt] = relationship(back_populates="entries")

    __table_args__ = (
        UniqueConstraint("receipt_id", "position", name="uq_receipt_entries_receipt_id_position"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("base_amount IS NULL OR amount <= base_amount", name="amount_within_base"),
        CheckConstraint(
            "rate_applied IS NULL OR (rate_applied >= 0 AND rate_applied <= 1)",
            name="rate_is_a_fraction",
        ),
        # Lançamento automático tem de apontar de onde veio; manual tem de dizer
        # o motivo. Nenhum dos dois pode ser um valor sem explicação.
        CheckConstraint(
            "(origin = 'automatica' AND rule_set_id IS NOT NULL)"
            " OR (origin = 'manual' AND calc_note IS NOT NULL AND btrim(calc_note) <> '')",
            name="entry_has_provenance",
        ),
        Index("ix_receipt_entries_receipt_id", "receipt_id"),
    )
