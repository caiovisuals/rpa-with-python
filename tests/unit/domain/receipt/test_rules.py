import pytest

from app.domain.errors import InvariantViolationError, ValidationError
from app.domain.receipt.rules import (
    assert_deduction_amount,
    assert_gross_amount,
    assert_net_amount,
    net_amount,
)
from app.domain.value_objects.money import Money


class TestValorBruto:
    def test_aceita_valor_positivo_na_moeda(self):
        assert_gross_amount(Money.of("1500.00"))

    @pytest.mark.parametrize("valor", ["0", "-1.00"])
    def test_recusa_zero_e_negativo(self, valor):
        with pytest.raises(ValidationError, match="maior que zero"):
            assert_gross_amount(Money.of(valor))

    def test_recusa_valor_fora_da_escala_da_moeda(self):
        with pytest.raises(ValidationError, match="casas decimais"):
            assert_gross_amount(Money.of("1500.005"))


class TestDescontos:
    def test_aceita_desconto_dentro_da_base(self):
        assert_deduction_amount(Money.of("165.00"), base=Money.of("1500.00"))

    def test_aceita_desconto_zero(self):
        assert_deduction_amount(Money.zero())

    def test_recusa_desconto_negativo(self):
        with pytest.raises(ValidationError, match="não pode ser negativo"):
            assert_deduction_amount(Money.of("-1.00"))

    def test_recusa_desconto_maior_que_a_base(self):
        with pytest.raises(ValidationError, match="excede a base"):
            assert_deduction_amount(Money.of("1500.01"), base=Money.of("1500.00"))

    def test_desconto_igual_a_base_e_aceito(self):
        assert_deduction_amount(Money.of("1500.00"), base=Money.of("1500.00"))


class TestLiquido:
    def test_identidade_da_rn03(self):
        liquido = net_amount(
            gross=Money.of("1000.00"),
            deductions=[Money.of("110.00"), Money.of("50.00")],
            additions=[Money.of("20.00")],
        )
        assert liquido == Money.of("860.00")

    def test_sem_descontos_nem_acrescimos_o_liquido_e_o_bruto(self):
        assert net_amount(gross=Money.of("1000.00"), deductions=[], additions=[]) == Money.of(
            "1000.00"
        )

    def test_assert_aceita_liquido_coerente(self):
        assert_net_amount(
            gross=Money.of("1000.00"),
            deductions=[Money.of("110.00")],
            additions=[],
            net=Money.of("890.00"),
        )

    def test_assert_detecta_liquido_incoerente(self):
        with pytest.raises(InvariantViolationError, match="não fecha"):
            assert_net_amount(
                gross=Money.of("1000.00"),
                deductions=[Money.of("110.00")],
                additions=[],
                net=Money.of("900.00"),
            )

    def test_assert_recusa_liquido_negativo(self):
        with pytest.raises(ValidationError, match="superam o valor bruto"):
            assert_net_amount(
                gross=Money.of("100.00"),
                deductions=[Money.of("150.00")],
                additions=[],
                net=Money.of("-50.00"),
            )

    def test_liquido_zero_e_valido(self):
        assert_net_amount(
            gross=Money.of("100.00"),
            deductions=[Money.of("100.00")],
            additions=[],
            net=Money.zero(),
        )
