"""Controle de numeração dos documentos.

O contador é uma linha em tabela, incrementada dentro da **mesma transação** da
emissão. Não é `SEQUENCE` do PostgreSQL: sequence não faz rollback, então uma
emissão que falhasse depois de pegar o número deixaria uma lacuna — e numeração
de documento contábil não pode ter buraco (RN10).

O custo é serializar emissões concorrentes da mesma série. No volume esperado
isso é irrelevante; a alternativa tem um defeito que não se conserta depois.
"""

from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, enum_column, uuid_pk


class DocumentType(Enum):
    """Tipo de documento numerado.

    Hoje só existe o RPA. A **coluna** é o que foi antecipado, não o valor:
    quando a folha CLT chegar (ADR-0005), o holerite entra como novo membro
    deste enum e ganha a sua própria sequência, sem tocar na numeração já
    emitida. Adicionar essa dimensão depois exigiria migrar dados de numeração
    em produção — a pior categoria de migration que existe.
    """

    RPA = "rpa"


class NumberSequence(Base, TimestampMixin):
    """Último número usado por (organização, tipo de documento, série, ano)."""

    __tablename__ = "number_sequences"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    document_type: Mapped[DocumentType] = mapped_column(
        enum_column(DocumentType, "document_type"), nullable=False
    )
    series: Mapped[str] = mapped_column(String(10), nullable=False, server_default="A")
    year: Mapped[int] = mapped_column(nullable=False)
    last_number: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "document_type",
            "series",
            "year",
            name="uq_number_sequences_organization_id_document_type_series_year",
        ),
        CheckConstraint("last_number >= 0", name="last_number_non_negative"),
        CheckConstraint("year BETWEEN 1900 AND 2199", name="year_range"),
    )
