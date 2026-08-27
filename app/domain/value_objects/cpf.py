"""CPF — Cadastro de Pessoa Física.

O dígito verificador é um *checksum* público do formato do documento, não uma
regra tributária: validá-lo apenas impede que um número digitado errado entre
no sistema. Ele **não** prova que o CPF existe ou pertence a alguém.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.errors import ValidationError

_NON_DIGITS = re.compile(r"\D")
_LENGTH = 11


def _check_digit(digits: str, weight: int) -> int:
    total = sum(int(d) * (weight - i) for i, d in enumerate(digits))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


@dataclass(frozen=True, slots=True)
class CPF:
    """CPF válido quanto ao formato e ao dígito verificador."""

    digits: str

    def __post_init__(self) -> None:
        if len(self.digits) != _LENGTH or not self.digits.isdigit():
            raise ValidationError(f"CPF deve ter {_LENGTH} dígitos: {self.digits!r}")
        if self.digits == self.digits[0] * _LENGTH:
            raise ValidationError("CPF com todos os dígitos iguais é inválido")
        expected = f"{_check_digit(self.digits[:9], 10)}{_check_digit(self.digits[:10], 11)}"
        if self.digits[9:] != expected:
            raise ValidationError("dígito verificador do CPF não confere")

    @classmethod
    def parse(cls, raw: str) -> CPF:
        """Aceita com ou sem pontuação: ``123.456.789-09`` ou ``12345678909``."""
        if not isinstance(raw, str):
            raise ValidationError(f"CPF deve ser texto, recebeu {type(raw).__name__}")
        return cls(_NON_DIGITS.sub("", raw))

    @property
    def formatted(self) -> str:
        d = self.digits
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"

    @property
    def masked(self) -> str:
        """Forma segura para log e tela. Ver RNF04: log nunca leva CPF completo."""
        return f"***.***.{self.digits[6:9]}-**"

    def __str__(self) -> str:
        return self.formatted

    def __repr__(self) -> str:
        # repr também é mascarado: repr vaza para stack trace e log de erro.
        return f"CPF('{self.masked}')"
