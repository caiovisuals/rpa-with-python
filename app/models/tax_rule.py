"""Parâmetros de cálculo, versionados por vigência.

Este é o lugar onde alíquotas, faixas e tetos vivem — **em dados, nunca em
código**. Nenhum valor fiscal aparece neste arquivo: ele define apenas a
estrutura capaz de representá-los.

A tabela de faixas é genérica de propósito. A mesma estrutura representa uma
alíquota única (uma linha, sem limites) e uma tabela progressiva (várias linhas
com faixa e parcela a deduzir). Qual formato cada tributo usa é a regra RV01-RV04,
ainda pendente de homologação.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.calculation.approval import ApprovalStatus
from app.models.base import Base, TimestampMixin, enum_column, uuid_pk


class TaxRuleSet(Base, TimestampMixin):
    """Um conjunto de parâmetros de um tributo, válido num intervalo de datas."""

    __tablename__ = "tax_rule_sets"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    tax_type: Mapped[str] = mapped_column(String(30), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)

    # Homologação (ADR-0004). Provisório calcula, mas não emite.
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        enum_column(ApprovalStatus, "approval_status"),
        nullable=False,
        default=ApprovalStatus.PROVISORIO,
        server_default=ApprovalStatus.PROVISORIO.value,
    )
    source_reference: Mapped[str | None] = mapped_column(String(500))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[date | None] = mapped_column(Date)

    # Quem carregou os parâmetros. Obrigatório também no provisório: parâmetro
    # sem dono é exatamente o que a regra "nada de número fiscal escondido"
    # existe para impedir.
    loaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    brackets: Mapped[list[TaxRuleBracket]] = relationship(
        back_populates="rule_set",
        cascade="all, delete-orphan",
        order_by="TaxRuleBracket.position",
    )

    __table_args__ = (
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="valid_period"),
        # Homologado sem fonte, sem responsável ou sem data não é homologação.
        # A mesma regra do domínio, gravada no banco: a aplicação dá a mensagem
        # boa, o banco garante que ninguém contorna.
        CheckConstraint(
            "approval_status <> 'homologado'"
            " OR (source_reference IS NOT NULL AND approved_by IS NOT NULL"
            " AND approved_at IS NOT NULL)",
            name="homologation_is_complete",
        ),
        Index(
            "ix_tax_rule_sets_organization_id_tax_type_valid_from",
            "organization_id",
            "tax_type",
            "valid_from",
        ),
        # Duas vigências do mesmo tributo não podem se sobrepor: se pudessem, o
        # sistema teria de escolher entre elas, e essa escolha seria arbitrária.
        # Exige a extensão btree_gist, criada na migration inicial.
        ExcludeConstraint(
            ("organization_id", "="),
            ("tax_type", "="),
            (func.daterange(valid_from, valid_to, "[)"), "&&"),
            name="ex_tax_rule_sets_no_overlapping_validity",
            using="gist",
        ),
    )


class TaxRuleBracket(Base):
    """Uma linha de um conjunto de parâmetros.

    Todos os campos numéricos são opcionais porque a forma da regra varia:
    alíquota única não tem faixa, faixa progressiva não tem teto, e assim por
    diante. O que cada tributo preenche vem da homologação (RV01-RV04).
    """

    __tablename__ = "tax_rule_brackets"

    id: Mapped[uuid.UUID] = uuid_pk()
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_rule_sets.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(nullable=False)
    min_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    max_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    deduction: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    cap: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    meta: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default="{}")

    rule_set: Mapped[TaxRuleSet] = relationship(back_populates="brackets")

    __table_args__ = (
        UniqueConstraint(
            "rule_set_id", "position", name="uq_tax_rule_brackets_rule_set_id_position"
        ),
        CheckConstraint("position >= 0", name="position_non_negative"),
        CheckConstraint("min_base IS NULL OR min_base >= 0", name="min_base_non_negative"),
        CheckConstraint(
            "max_base IS NULL OR min_base IS NULL OR max_base > min_base", name="base_range"
        ),
        CheckConstraint("rate IS NULL OR (rate >= 0 AND rate <= 1)", name="rate_is_a_fraction"),
        CheckConstraint("deduction IS NULL OR deduction >= 0", name="deduction_non_negative"),
        CheckConstraint("cap IS NULL OR cap >= 0", name="cap_non_negative"),
    )
