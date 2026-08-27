"""Invariantes do recibo.

Funções puras, sem estado. São a versão executável das regras RN02, RN03 e RN08
do planejamento, e o mesmo conjunto que a constraint ``CHECK`` do banco vai
espelhar — a regra vive nos dois lugares de propósito: a aplicação dá a mensagem
boa, o banco garante que ninguém contorna.

Nada aqui calcula tributo. O que cada desconto vale é responsabilidade do motor
de cálculo, que só existirá quando as regras RV01-RV11 estiverem homologadas.
"""

from __future__ import annotations

from app.domain.errors import InvariantViolationError, ValidationError
from app.domain.value_objects.money import Money, total


def assert_gross_amount(gross: Money) -> None:
    """O valor bruto do serviço é sempre positivo (RN02)."""
    if not gross.is_positive:
        raise ValidationError(f"valor bruto deve ser maior que zero: {gross}")
    if not gross.is_currency_scale:
        raise ValidationError(
            f"valor bruto com {gross.decimal_places} casas decimais: {gross}. "
            "Valor informado deve caber na moeda."
        )


def assert_deduction_amount(amount: Money, *, base: Money | None = None) -> None:
    """Um desconto nunca é negativo, e nunca excede a base sobre a qual incide."""
    if amount.is_negative:
        raise ValidationError(f"desconto não pode ser negativo: {amount}")
    if base is not None and amount > base:
        raise ValidationError(f"desconto {amount} excede a base de incidência {base}")


def net_amount(*, gross: Money, deductions: list[Money], additions: list[Money]) -> Money:
    """Calcula o líquido (RN03): ``liquido = bruto - soma(descontos) + soma(acrescimos)``.

    Não arredonda: os valores que chegam aqui já vêm arredondados pelo motor de
    cálculo, com a política homologada. Arredondar de novo aqui esconderia erro.
    """
    return gross - total(deductions) + total(additions)


def assert_net_amount(
    *,
    gross: Money,
    deductions: list[Money],
    additions: list[Money],
    net: Money,
) -> None:
    """Verifica a identidade da RN03 e que o líquido não é negativo.

    Raises:
        InvariantViolationError: o líquido informado não fecha com as parcelas.
            Isso é bug, não erro de usuário.
        ValidationError: os descontos superam o bruto e o líquido ficaria negativo.
    """
    expected = net_amount(gross=gross, deductions=deductions, additions=additions)
    if net != expected:
        raise InvariantViolationError(
            f"líquido não fecha: informado {net}, esperado {expected} "
            f"(bruto {gross} - descontos {total(deductions)} + acréscimos {total(additions)})."
        )
    if net.is_negative:
        raise ValidationError(
            f"descontos ({total(deductions)}) superam o valor bruto ({gross}); "
            f"o líquido resultaria em {net}."
        )
