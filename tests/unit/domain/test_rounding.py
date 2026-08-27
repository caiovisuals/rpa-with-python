"""Arredondamento é o ponto único onde centavos podem se perder. Testado à exaustão."""

from decimal import Decimal

import pytest

from app.domain.rounding import (
    CURRENCY_SCALE,
    RoundingPolicy,
    quantize,
    to_currency,
)


@pytest.mark.parametrize(
    ("value", "policy", "expected"),
    [
        # meio para cima
        ("0.005", RoundingPolicy.HALF_UP, "0.01"),
        ("0.015", RoundingPolicy.HALF_UP, "0.02"),
        ("-0.005", RoundingPolicy.HALF_UP, "-0.01"),
        # meio para o par (bancário): 0.005 vai para 0.00, 0.015 vai para 0.02
        ("0.005", RoundingPolicy.HALF_EVEN, "0.00"),
        ("0.015", RoundingPolicy.HALF_EVEN, "0.02"),
        ("0.025", RoundingPolicy.HALF_EVEN, "0.02"),
        # truncamento em direção a zero
        ("0.009", RoundingPolicy.DOWN, "0.00"),
        ("-0.009", RoundingPolicy.DOWN, "-0.00"),
        # afastando de zero
        ("0.001", RoundingPolicy.UP, "0.01"),
        ("-0.001", RoundingPolicy.UP, "-0.01"),
        # piso e teto
        ("0.001", RoundingPolicy.FLOOR, "0.00"),
        ("-0.001", RoundingPolicy.FLOOR, "-0.01"),
        ("0.001", RoundingPolicy.CEILING, "0.01"),
        ("-0.001", RoundingPolicy.CEILING, "-0.00"),
    ],
)
def test_politicas_produzem_o_resultado_declarado(value, policy, expected):
    assert quantize(Decimal(value), places=2, policy=policy) == Decimal(expected)


def test_politicas_divergem_no_meio_exato():
    """Se as políticas nunca divergissem, a RV05 não precisaria ser validada."""
    meio = Decimal("0.005")
    assert quantize(meio, places=2, policy=RoundingPolicy.HALF_UP) != quantize(
        meio, places=2, policy=RoundingPolicy.HALF_EVEN
    )


def test_todas_as_politicas_estao_mapeadas():
    for policy in RoundingPolicy:
        assert quantize(Decimal("1.005"), places=2, policy=policy) is not None


def test_quantize_preserva_a_escala_pedida():
    assert quantize(Decimal("1"), places=4, policy=RoundingPolicy.HALF_UP) == Decimal("1.0000")
    assert quantize(Decimal("1.23456"), places=0, policy=RoundingPolicy.DOWN) == Decimal("1")


def test_to_currency_usa_a_escala_da_moeda():
    resultado = to_currency(Decimal("10.9999"), policy=RoundingPolicy.HALF_UP)
    assert resultado == Decimal("11.00")
    assert -int(resultado.as_tuple().exponent) == CURRENCY_SCALE


def test_places_negativo_e_recusado():
    with pytest.raises(ValueError, match="negativo"):
        quantize(Decimal("1"), places=-1, policy=RoundingPolicy.HALF_UP)


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_valor_nao_finito_e_recusado(value):
    with pytest.raises(ValueError, match="não finito"):
        quantize(value, places=2, policy=RoundingPolicy.HALF_UP)
