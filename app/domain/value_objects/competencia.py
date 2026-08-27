"""Competência — o mês de referência do serviço prestado.

Competência é mês e ano, sem dia. Ela **não** é necessariamente a data que
seleciona a vigência dos parâmetros de cálculo: qual data cumpre esse papel é a
regra RV07, ainda pendente de validação (ver docs/PLANEJAMENTO.md, seção 4.3).
Por isso este tipo não decide nada sobre cálculo — apenas representa o período.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.domain.errors import ValidationError

_ISO = re.compile(r"^(\d{4})-(\d{2})$")
_BR = re.compile(r"^(\d{2})/(\d{4})$")

MIN_YEAR = 1900
MAX_YEAR = 2199


@dataclass(frozen=True, slots=True, order=True)
class Competencia:
    """Mês de competência, comparável e ordenável."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if not isinstance(self.year, int) or not isinstance(self.month, int):
            raise ValidationError("competência exige ano e mês inteiros")
        if not MIN_YEAR <= self.year <= MAX_YEAR:
            raise ValidationError(f"ano fora da faixa aceita ({MIN_YEAR}-{MAX_YEAR}): {self.year}")
        if not 1 <= self.month <= 12:
            raise ValidationError(f"mês inválido: {self.month}")

    @classmethod
    def parse(cls, raw: str) -> Competencia:
        """Aceita ``2026-08`` (ISO) ou ``08/2026`` (uso brasileiro)."""
        if not isinstance(raw, str):
            raise ValidationError(f"competência deve ser texto, recebeu {type(raw).__name__}")
        text = raw.strip()
        if match := _ISO.match(text):
            return cls(int(match.group(1)), int(match.group(2)))
        if match := _BR.match(text):
            return cls(int(match.group(2)), int(match.group(1)))
        raise ValidationError(f"competência inválida: {raw!r}. Use AAAA-MM ou MM/AAAA.")

    @classmethod
    def from_date(cls, moment: date) -> Competencia:
        return cls(moment.year, moment.month)

    def next(self) -> Competencia:
        if self.month == 12:
            return Competencia(self.year + 1, 1)
        return Competencia(self.year, self.month + 1)

    def previous(self) -> Competencia:
        if self.month == 1:
            return Competencia(self.year - 1, 12)
        return Competencia(self.year, self.month - 1)

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def iso(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    def __str__(self) -> str:
        return f"{self.month:02d}/{self.year:04d}"

    def __repr__(self) -> str:
        return f"Competencia('{self.iso}')"
