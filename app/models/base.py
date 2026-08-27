"""Base declarativa e convenções compartilhadas pelas tabelas.

Duas decisões que valem para o schema inteiro estão aqui:

* **Convenção de nomes de constraint.** Sem ela, o PostgreSQL gera nomes
  automáticos e o Alembic não consegue referenciá-los numa migration de
  reversão. Nome estável é pré-requisito para migration reversível.
* **Timestamps em UTC.** Toda coluna de data e hora é ``timestamptz``. O fuso
  de exibição é problema da interface, não do banco.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def uuid_pk() -> Mapped[uuid.UUID]:
    """Chave primária UUID, gerada na aplicação.

    UUID em vez de inteiro sequencial: o identificador aparece em URL e em
    referência entre sistemas, e um inteiro sequencial revela volume de
    emissão para quem olhar de fora. A numeração do recibo, essa sim, é
    sequencial — e é controlada separadamente (ver `number_sequences`).
    """
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Registro de criação e última alteração, sempre em UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def enum_column(enum_cls: type[Enum], name: str) -> SAEnum:
    """Coluna de enumeração gravada como VARCHAR + CHECK.

    Tipo ENUM nativo do PostgreSQL exige ``ALTER TYPE`` para cada valor novo,
    o que é doloroso em migration e difícil de reverter. VARCHAR com CHECK
    evolui alterando a constraint, e o valor gravado é legível em qualquer
    consulta manual.

    Grava o **valor** do membro (``"em_revisao"``), não o nome (``EM_REVISAO``),
    para que o banco espelhe exatamente o vocabulário do domínio.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=lambda cls: [member.value for member in cls],
        length=32,
    )
