"""Money — valor monetário exato.

Regras que este tipo existe para tornar impossíveis de violar:

* ``float`` **nunca** entra. Tentar construir a partir de ``float`` levanta erro.
* Nenhuma operação arredonda em silêncio. Multiplicação por alíquota produz um
  valor exato, possivelmente com muitas casas; transformá-lo em valor de moeda
  exige chamar :meth:`Money.quantized` com uma política explícita.
* Entrada digitada por pessoa (valor bruto do serviço) não pode ter mais de
  duas casas — :meth:`Money.from_input` recusa, em vez de arredondar por conta
  própria.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.domain.errors import ValidationError
from app.domain.rounding import CURRENCY_SCALE, RoundingPolicy, calculation_context, quantize

Numeric = Decimal | int | str


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """Quantia em reais, exata, sem arredondamento implícito."""

    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise ValidationError(
                f"Money exige Decimal, recebeu {type(self.amount).__name__}. "
                "Use Money.of() para converter."
            )
        if not self.amount.is_finite():
            raise ValidationError(f"valor monetário não finito: {self.amount}")

    # ------------------------------------------------------------ construção
    @classmethod
    def of(cls, value: Numeric) -> Money:
        """Constrói a partir de ``Decimal``, ``int`` ou ``str``, sem arredondar.

        ``float`` é recusado de propósito: 0.1 + 0.2 != 0.3 em binário, e um
        centavo perdido aqui vira divergência contábil depois.
        """
        if isinstance(value, float):
            raise ValidationError(
                "float não é aceito em valores monetários — use str, int ou Decimal."
            )
        if isinstance(value, Decimal):
            return cls(value)
        try:
            return cls(Decimal(str(value)))
        except InvalidOperation as exc:
            raise ValidationError(f"valor monetário inválido: {value!r}") from exc

    @classmethod
    def from_input(cls, value: Numeric) -> Money:
        """Constrói a partir de entrada informada por pessoa.

        Recusa mais de duas casas decimais em vez de arredondar: quem digitou
        precisa saber que o valor não cabe na moeda.
        """
        money = cls.of(value)
        if money.decimal_places > CURRENCY_SCALE:
            raise ValidationError(
                f"valor com {money.decimal_places} casas decimais: {money.amount}. "
                f"Valores informados devem ter no máximo {CURRENCY_SCALE}."
            )
        return money

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal(0))

    # ------------------------------------------------------------ propriedades
    @property
    def decimal_places(self) -> int:
        """Casas decimais efetivas do valor."""
        exponent = self.amount.as_tuple().exponent
        if not isinstance(exponent, int):  # pragma: no cover - inalcançável
            # Expoente não inteiro só ocorre em NaN/Infinity, que o __post_init__
            # já barra. A guarda fica para o caso de alguém contornar o construtor.
            raise ValidationError(f"valor monetário não finito: {self.amount}")
        return max(0, -exponent)

    @property
    def is_currency_scale(self) -> bool:
        """True se o valor já cabe na moeda (no máximo 2 casas)."""
        return self.decimal_places <= CURRENCY_SCALE

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    @property
    def is_positive(self) -> bool:
        return self.amount > 0

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    # ------------------------------------------------------------ aritmética
    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        ctx = calculation_context()
        return Money(ctx.add(self.amount, other.amount))

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        ctx = calculation_context()
        return Money(ctx.subtract(self.amount, other.amount))

    def __mul__(self, factor: Decimal | int) -> Money:
        """Multiplica por uma alíquota ou quantidade, **sem arredondar**.

        O resultado pode ter muitas casas decimais. Use :meth:`quantized` para
        levá-lo à moeda, com política explícita.
        """
        if isinstance(factor, float):
            raise ValidationError("float não é aceito como fator — use Decimal ou int.")
        if not isinstance(factor, Decimal | int):
            return NotImplemented
        ctx = calculation_context()
        return Money(ctx.multiply(self.amount, Decimal(factor)))

    __rmul__ = __mul__

    def __neg__(self) -> Money:
        return Money(-self.amount)

    def __abs__(self) -> Money:
        return Money(abs(self.amount))

    # ------------------------------------------------------------ arredondamento
    def quantized(self, policy: RoundingPolicy, *, places: int = CURRENCY_SCALE) -> Money:
        """Devolve o valor arredondado. A política é obrigatória — não há padrão."""
        return Money(quantize(self.amount, places=places, policy=policy))

    # ------------------------------------------------------------ apresentação
    def format_brl(self) -> str:
        """Formata como moeda brasileira. Exige valor já na escala da moeda."""
        if not self.is_currency_scale:
            raise ValidationError(
                f"valor com {self.decimal_places} casas não pode ser formatado como moeda; "
                "arredonde antes com quantized()."
            )
        fixed = self.amount.quantize(Decimal("0.01"))
        sign = "-" if fixed < 0 else ""
        integer, _, cents = str(abs(fixed)).partition(".")
        groups: list[str] = []
        while len(integer) > 3:
            groups.insert(0, integer[-3:])
            integer = integer[:-3]
        groups.insert(0, integer)
        return f"{sign}R$ {'.'.join(groups)},{cents}"

    def __str__(self) -> str:
        return str(self.amount)

    def __repr__(self) -> str:
        return f"Money('{self.amount}')"


def total(values: list[Money]) -> Money:
    """Soma exata de uma lista de valores. Lista vazia soma zero."""
    result = Money.zero()
    for value in values:
        result = result + value
    return result
