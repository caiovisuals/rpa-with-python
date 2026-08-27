"""Arredondamento — ponto único do sistema.

Nenhum outro módulo pode chamar ``Decimal.quantize`` diretamente. Todo
arredondamento passa por aqui, para que a regra seja auditável em um só lugar.

.. warning::
   **A política de arredondamento aplicável aos tributos é a regra RV05 e ainda
   NÃO foi validada.** Este módulo oferece as políticas possíveis; ele não
   escolhe nenhuma. Não existe política padrão de propósito: todo chamador é
   obrigado a informar qual usar, e essa informação virá das tabelas de
   parâmetros homologadas (ver docs/PLANEJAMENTO.md, seções 0.3 e 4.3).
"""

from __future__ import annotations

import decimal
from decimal import Decimal
from enum import Enum

#: Casas decimais da moeda corrente (BRL). Convenção monetária, não regra fiscal.
#: O número de casas usado em *cálculos intermediários* é parte da RV05 e é
#: sempre informado explicitamente pelo chamador.
CURRENCY_SCALE = 2

#: Precisão do contexto decimal. Alta o bastante para que nenhum cálculo
#: intermediário perca dígitos antes do arredondamento explícito.
CALCULATION_PRECISION = 28


class RoundingPolicy(Enum):
    """Políticas de arredondamento disponíveis.

    Qual delas se aplica a cada tributo é a RV05, pendente de homologação.
    """

    HALF_UP = "half_up"
    """Meio para cima: 0,005 -> 0,01."""

    HALF_EVEN = "half_even"
    """Meio para o par (bancário): 0,005 -> 0,00; 0,015 -> 0,02."""

    DOWN = "down"
    """Trunca em direção a zero: 0,009 -> 0,00."""

    UP = "up"
    """Afasta de zero: 0,001 -> 0,01."""

    FLOOR = "floor"
    """Em direção a menos infinito."""

    CEILING = "ceiling"
    """Em direção a mais infinito."""


_DECIMAL_MODES: dict[RoundingPolicy, str] = {
    RoundingPolicy.HALF_UP: decimal.ROUND_HALF_UP,
    RoundingPolicy.HALF_EVEN: decimal.ROUND_HALF_EVEN,
    RoundingPolicy.DOWN: decimal.ROUND_DOWN,
    RoundingPolicy.UP: decimal.ROUND_UP,
    RoundingPolicy.FLOOR: decimal.ROUND_FLOOR,
    RoundingPolicy.CEILING: decimal.ROUND_CEILING,
}


def calculation_context() -> decimal.Context:
    """Contexto decimal usado em todo cálculo do domínio.

    ``traps`` desligados para inexatidão e arredondamento (esperados), ligados
    para divisão por zero e overflow (que são bugs).
    """
    return decimal.Context(
        prec=CALCULATION_PRECISION,
        traps=[decimal.DivisionByZero, decimal.Overflow, decimal.InvalidOperation],
    )


def quantize(value: Decimal, *, places: int, policy: RoundingPolicy) -> Decimal:
    """Arredonda ``value`` para ``places`` casas usando ``policy``.

    Args:
        value: valor exato a arredondar.
        places: número de casas decimais do resultado. Não pode ser negativo.
        policy: política a aplicar. **Obrigatória — não há padrão.**

    Raises:
        ValueError: se ``places`` for negativo ou ``value`` não for finito.
    """
    if places < 0:
        raise ValueError(f"places não pode ser negativo: {places}")
    if not value.is_finite():
        raise ValueError(f"valor não finito não pode ser arredondado: {value}")
    exponent = Decimal(1).scaleb(-places)
    return value.quantize(exponent, rounding=_DECIMAL_MODES[policy], context=calculation_context())


def to_currency(value: Decimal, *, policy: RoundingPolicy) -> Decimal:
    """Arredonda para a escala da moeda (2 casas), com política explícita."""
    return quantize(value, places=CURRENCY_SCALE, policy=policy)
