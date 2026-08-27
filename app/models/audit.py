"""Trilha de auditoria.

Append-only por concessão de privilégio, não por convenção: o usuário de
aplicação recebe apenas ``INSERT`` e ``SELECT`` nesta tabela. Uma trilha que a
própria aplicação pode reescrever não prova nada (RNF05).

Referência polimórfica sem chave estrangeira: o log precisa sobreviver ao
registro que descreve. Uma FK impediria justamente o caso mais importante —
saber o que foi apagado.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class AuditLog(Base):
    """Um registro imutável de operação relevante."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    # Anulável: ações do próprio sistema (rotina, migração) não têm autor humano.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    before: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "ix_audit_logs_organization_id_entity_type_entity_id_created_at",
            "organization_id",
            "entity_type",
            "entity_id",
            "created_at",
        ),
        Index(
            "ix_audit_logs_organization_id_user_id_created_at",
            "organization_id",
            "user_id",
            "created_at",
        ),
    )
