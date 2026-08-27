from decimal import Decimal

import pytest

from app.domain.errors import ValidationError
from app.domain.rounding import RoundingPolicy
from app.domain.value_objects.money import Money, total


class TestConstrucao:
    @pytest.mark.parametrize("value", ["10.50", 10, Decimal("10.50"), "0", "-3.25"])
    def test_aceita_str_int_e_decimal(self, value):
        assert isinstance(Money.of(value).amount, Decimal)

    def test_recusa_float(self):
        with pytest.raises(ValidationError, match="float não é aceito"):
            Money.of(10.5)  # type: ignore[arg-type]

    @pytest.mark.parametrize("value", ["abc", "", "1,50"])
    def test_recusa_texto_invalido(self, value):
        with pytest.raises(ValidationError, match="inválido"):
            Money.of(value)

    @pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
    def test_recusa_valor_nao_finito(self, value):
        with pytest.raises(ValidationError, match="não finito"):
            Money.of(value)

    def test_recusa_tipo_errado_no_construtor_direto(self):
        with pytest.raises(ValidationError, match="exige Decimal"):
            Money("10.50")  # type: ignore[arg-type]

    def test_zero(self):
        assert Money.zero().is_zero


class TestEntradaDigitada:
    @pytest.mark.parametrize("value", ["1500", "1500.0", "1500.75"])
    def test_aceita_ate_duas_casas(self, value):
        assert Money.from_input(value).is_currency_scale

    def test_recusa_mais_de_duas_casas_em_vez_de_arredondar(self):
        with pytest.raises(ValidationError, match="3 casas decimais"):
            Money.from_input("1500.755")


class TestAritmetica:
    def test_soma_e_subtracao_sao_exatas(self):
        assert Money.of("0.1") + Money.of("0.2") == Money.of("0.3")
        assert Money.of("1000.00") - Money.of("0.01") == Money.of("999.99")

    def test_multiplicacao_por_aliquota_nao_arredonda(self):
        resultado = Money.of("1000.00") * Decimal("0.075")
        assert resultado.amount == Decimal("75.00000")
        assert not resultado.is_currency_scale
        assert resultado.decimal_places == 5

    def test_multiplicacao_e_comutativa(self):
        assert Decimal("2") * Money.of("10.00") == Money.of("10.00") * Decimal("2")

    def test_multiplicacao_recusa_float(self):
        with pytest.raises(ValidationError, match="float não é aceito"):
            Money.of("10.00") * 1.5  # type: ignore[operator]

    def test_soma_com_tipo_errado(self):
        with pytest.raises(TypeError):
            Money.of("10.00") + 5  # type: ignore[operator]

    def test_negacao_e_modulo(self):
        assert -Money.of("10.00") == Money.of("-10.00")
        assert abs(Money.of("-10.00")) == Money.of("10.00")

    def test_total_de_lista_vazia_e_zero(self):
        assert total([]) == Money.zero()

    def test_total_soma_exatamente(self):
        assert total([Money.of("0.01")] * 100) == Money.of("1.00")


class TestOrdenacao:
    def test_compara_por_valor(self):
        assert Money.of("5.00") < Money.of("5.01")
        assert Money.of("5.00") == Money.of("5")
        assert max([Money.of("1"), Money.of("9"), Money.of("3")]) == Money.of("9")


class TestArredondamento:
    def test_quantized_exige_politica_explicita(self):
        bruto = Money.of("1000.00") * Decimal("0.11")
        assert bruto.quantized(RoundingPolicy.HALF_UP) == Money.of("110.00")

    def test_quantized_aceita_outra_escala(self):
        valor = Money.of("1.23456")
        assert valor.quantized(RoundingPolicy.DOWN, places=4) == Money.of("1.2345")


class TestApresentacao:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("0", "R$ 0,00"),
            ("5", "R$ 5,00"),
            ("1234.5", "R$ 1.234,50"),
            ("1234567.89", "R$ 1.234.567,89"),
            ("-1234.56", "-R$ 1.234,56"),
        ],
    )
    def test_formata_como_moeda_brasileira(self, value, expected):
        assert Money.of(value).format_brl() == expected

    def test_recusa_formatar_valor_fora_da_escala(self):
        with pytest.raises(ValidationError, match="arredonde antes"):
            (Money.of("1000.00") * Decimal("0.075")).format_brl()

    def test_repr_e_reversivel(self):
        valor = Money.of("1234.56")
        assert repr(valor) == "Money('1234.56')"
        assert Money.of(str(valor)) == valor


class TestPropriedades:
    def test_sinal(self):
        assert Money.of("1").is_positive
        assert Money.of("-1").is_negative
        assert Money.zero().is_zero
        assert not Money.zero().is_positive


class TestOperacoesComTiposIncompativeis:
    """Operadores devolvem NotImplemented, deixando o Python levantar TypeError."""

    def test_subtracao_com_tipo_errado(self):
        with pytest.raises(TypeError):
            Money.of("10.00") - "5"  # type: ignore[operator]

    def test_multiplicacao_com_tipo_errado(self):
        with pytest.raises(TypeError):
            Money.of("10.00") * "2"  # type: ignore[operator]

    def test_str_devolve_o_valor_cru(self):
        assert str(Money.of("1234.56")) == "1234.56"
