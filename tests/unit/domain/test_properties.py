"""Testes baseados em propriedade.

Um teste tabular prova que os casos escolhidos funcionam. Estes provam que a
regra vale para qualquer entrada — é a diferença entre "os exemplos passam" e
"a invariante se sustenta".
"""

from decimal import Decimal

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.domain.receipt.rules import assert_net_amount, net_amount
from app.domain.rounding import RoundingPolicy, quantize
from app.domain.value_objects.competencia import Competencia
from app.domain.value_objects.money import Money, total

valores = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("9999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
).map(Money.of)

listas_de_valores = st.lists(valores, max_size=8)

politicas = st.sampled_from(list(RoundingPolicy))


@given(gross=valores, deductions=listas_de_valores, additions=listas_de_valores)
def test_rn03_vale_para_qualquer_entrada(gross, deductions, additions):
    """liquido = bruto - soma(descontos) + soma(acrescimos), sempre."""
    liquido = net_amount(gross=gross, deductions=deductions, additions=additions)
    assert liquido + total(deductions) - total(additions) == gross


@given(gross=valores, deductions=listas_de_valores, additions=listas_de_valores)
def test_assert_net_amount_aceita_o_proprio_calculo(gross, deductions, additions):
    liquido = net_amount(gross=gross, deductions=deductions, additions=additions)
    assume(not liquido.is_negative)
    assert_net_amount(gross=gross, deductions=deductions, additions=additions, net=liquido)


@given(gross=valores, deductions=listas_de_valores, additions=listas_de_valores)
def test_calculo_do_liquido_e_deterministico(gross, deductions, additions):
    """RNF01: mesma entrada, mesmo resultado. Sempre."""
    primeiro = net_amount(gross=gross, deductions=deductions, additions=additions)
    for _ in range(5):
        assert net_amount(gross=gross, deductions=deductions, additions=additions) == primeiro


@given(a=valores, b=valores, c=valores)
def test_soma_e_associativa_e_comutativa(a, b, c):
    assert (a + b) + c == a + (b + c)
    assert a + b == b + a


@given(a=valores, b=valores)
def test_subtracao_desfaz_a_soma(a, b):
    assert (a + b) - b == a


@given(valores=listas_de_valores)
def test_total_equivale_a_somar_um_a_um(valores):
    acumulado = Money.zero()
    for valor in valores:
        acumulado = acumulado + valor
    assert total(valores) == acumulado


@given(valor=valores, fator=st.decimals(min_value=0, max_value=1, places=6, allow_nan=False))
def test_multiplicacao_por_aliquota_nunca_supera_a_base(valor, fator):
    """Uma alíquota entre 0 e 1 nunca produz desconto maior que a base."""
    assert (valor * fator).amount <= valor.amount


@given(
    valor=st.decimals(
        min_value=Decimal("-99999.999999"),
        max_value=Decimal("99999.999999"),
        places=6,
        allow_nan=False,
        allow_infinity=False,
    ),
    policy=politicas,
    places=st.integers(min_value=0, max_value=6),
)
def test_arredondamento_nunca_desloca_mais_que_uma_casa(valor, policy, places):
    arredondado = quantize(valor, places=places, policy=policy)
    assert abs(arredondado - valor) < Decimal(1).scaleb(-places)


@given(
    valor=st.decimals(min_value=0, max_value=1000, places=6, allow_nan=False),
    policy=politicas,
)
def test_arredondamento_e_idempotente(valor, policy):
    uma_vez = quantize(valor, places=2, policy=policy)
    assert quantize(uma_vez, places=2, policy=policy) == uma_vez


@given(
    valor=st.decimals(min_value=0, max_value=1000, places=6, allow_nan=False),
    policy=politicas,
)
def test_arredondamento_e_deterministico(valor, policy):
    primeiro = quantize(valor, places=2, policy=policy)
    for _ in range(5):
        assert quantize(valor, places=2, policy=policy) == primeiro


@given(valor=valores)
def test_money_faz_round_trip_por_texto(valor):
    assert Money.of(str(valor)) == valor


@given(ano=st.integers(min_value=1900, max_value=2199), mes=st.integers(min_value=1, max_value=12))
@settings(max_examples=200)
def test_competencia_avanca_e_volta(ano, mes):
    competencia = Competencia(ano, mes)
    assume(competencia != Competencia(2199, 12))
    assert competencia.next().previous() == competencia


@given(ano=st.integers(min_value=1900, max_value=2199), mes=st.integers(min_value=1, max_value=12))
def test_competencia_faz_round_trip_pelos_dois_formatos(ano, mes):
    competencia = Competencia(ano, mes)
    assert Competencia.parse(competencia.iso) == competencia
    assert Competencia.parse(str(competencia)) == competencia
