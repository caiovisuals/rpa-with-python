"""Organização e usuários."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_column, uuid_pk


class UserRole(Enum):
    """Papéis de acesso (RF38).

    Quatro papéis fixos, como enum e não como tabela: não há requisito de
    criar papel novo em tempo de execução, e uma tabela de papéis com
    permissões editáveis é complexidade que ninguém pediu.
    """

    ADMIN = "admin"
    REVISOR = "revisor"
    OPERADOR = "operador"
    CONSULTA = "consulta"


class Organization(Base, TimestampMixin):
    """A empresa dona dos dados.

    Existe desde a primeira migration mesmo com um único registro: adicionar
    `organization_id` depois, com dados em produção, é migration de dados em
    todas as tabelas ao mesmo tempo.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    document: Mapped[str] = mapped_column(String(14), nullable=False)
    settings: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default="{}")

    __table_args__ = (UniqueConstraint("document", name="uq_organizations_document"),)


class User(Base, TimestampMixin):
    """Quem acessa o sistema."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole, "user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Organization] = relationship()

    # E-mail é único no sistema inteiro, não por organização: o login acontece
    # antes de o sistema saber de qual organização a pessoa é.
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)
