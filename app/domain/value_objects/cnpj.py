"""CNPJ — Cadastro Nacional da Pessoa Jurídica.

Mesma observação do CPF: o dígito verificador confere o formato, não a
existência do cadastro.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.errors import ValidationError

_NON_DIGITS = re.compile(r"\D")
_LENGTH = 14
_FIRST_WEIGHTS = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_SECOND_WEIGHTS = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _check_digit(digits: str, weights: tuple[int, ...]) -> int:
    total = sum(int(d) * w for d, w in zip(digits, weights, strict=True))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


@dataclass(frozen=True, slots=True)
class CNPJ:
    """CNPJ válido quanto ao formato e ao dígito verificador."""

    digits: str

    def __post_init__(self) -> None:
        if len(self.digits) != _LENGTH or not self.digits.isdigit():
            raise ValidationError(f"CNPJ deve ter {_LENGTH} dígitos: {self.digits!r}")
        if self.digits == self.digits[0] * _LENGTH:
            raise ValidationError("CNPJ com todos os dígitos iguais é inválido")
        first = _check_digit(self.digits[:12], _FIRST_WEIGHTS)
        second = _check_digit(self.digits[:13], _SECOND_WEIGHTS)
        if self.digits[12:] != f"{first}{second}":
            raise ValidationError("dígito verificador do CNPJ não confere")

    @classmethod
    def parse(cls, raw: str) -> CNPJ:
        """Aceita com ou sem pontuação: ``11.222.333/0001-81`` ou ``11222333000181``."""
        if not isinstance(raw, str):
            raise ValidationError(f"CNPJ deve ser texto, recebeu {type(raw).__name__}")
        return cls(_NON_DIGITS.sub("", raw))

    @property
    def formatted(self) -> str:
        d = self.digits
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"

    def __str__(self) -> str:
        return self.formatted

    def __repr__(self) -> str:
        return f"CNPJ('{self.formatted}')"
