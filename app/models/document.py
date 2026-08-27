"""Documentos gerados e histórico de mudanças de estado."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.receipt.status import ReceiptStatus
from app.models.base import Base, enum_column, uuid_pk
from app.models.receipt import Receipt


class DocumentKind(Enum):
    RASCUNHO = "rascunho"
    """Simulação ou rascunho: sai com marca d'água, sem valor."""

    OFICIAL = "oficial"
    """Documento definitivo, gerado na emissão."""


class ReceiptDocument(Base):
    """Um PDF gerado para um recibo.

    Nunca se sobrescreve: cada geração cria uma linha nova. Reimpressão devolve
    o arquivo original (RF33), e não uma nova renderização — dois PDFs
    "equivalentes" mas com bytes diferentes seriam impossíveis de conciliar
    numa auditoria.

    O `sha256` permite provar que o arquivo entregue é o que o sistema gerou.
    """

    __tablename__ = "receipt_documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[DocumentKind] = mapped_column(
        enum_column(DocumentKind, "document_kind"), nullable=False
    )
    # Caminho não sequencial e não adivinhável: PDF não pode ser alcançável por
    # tentativa e erro, mesmo que a autorização falhe.
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    template_version: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    receipt: Mapped[Receipt] = relationship()

    __table_args__ = (
        UniqueConstraint("storage_path", name="uq_receipt_documents_storage_path"),
        CheckConstraint("length(sha256) = 64 AND sha256 ~ '^[0-9a-f]+$'", name="sha256_format"),
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
        Index("ix_receipt_documents_receipt_id_generated_at", "receipt_id", "generated_at"),
    )


class ReceiptStatusHistory(Base):
    """Cada transição de estado do recibo, com autor e motivo."""

    __tablename__ = "receipt_status_history"

    id: Mapped[uuid.UUID] = uuid_pk()
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[ReceiptStatus | None] = mapped_column(
        enum_column(ReceiptStatus, "receipt_status")
    )
    to_status: Mapped[ReceiptStatus] = mapped_column(
        enum_column(ReceiptStatus, "receipt_status"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    receipt: Mapped[Receipt] = relationship()

    __table_args__ = (
        CheckConstraint("from_status IS NULL OR from_status <> to_status", name="status_changed"),
        Index("ix_receipt_status_history_receipt_id_created_at", "receipt_id", "created_at"),
    )
