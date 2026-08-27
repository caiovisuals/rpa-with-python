import pytest

from app.domain.errors import ValidationError
from app.domain.value_objects.cpf import CPF

# CPFs válidos quanto ao dígito verificador, gerados para teste. FICTÍCIOS.
VALIDOS = ["52998224725", "11144477735", "12345678909"]


@pytest.mark.parametrize("numero", VALIDOS)
def test_aceita_cpf_com_digito_valido(numero):
    assert CPF.parse(numero).digits == numero


@pytest.mark.parametrize(
    "entrada",
    ["529.982.247-25", "529 982 247 25", "  52998224725  ", "529982247-25"],
)
def test_ignora_pontuacao_e_espacos(entrada):
    assert CPF.parse(entrada).digits == "52998224725"


@pytest.mark.parametrize("numero", ["52998224726", "11144477734", "12345678900"])
def test_recusa_digito_verificador_errado(numero):
    with pytest.raises(ValidationError, match="dígito verificador"):
        CPF.parse(numero)


@pytest.mark.parametrize("numero", [f"{d}" * 11 for d in range(10)])
def test_recusa_todos_os_digitos_iguais(numero):
    with pytest.raises(ValidationError, match="dígitos iguais"):
        CPF.parse(numero)


@pytest.mark.parametrize("entrada", ["", "123", "5299822472555", "abcdefghijk"])
def test_recusa_tamanho_errado(entrada):
    with pytest.raises(ValidationError, match="11 dígitos"):
        CPF.parse(entrada)


def test_recusa_tipo_errado():
    with pytest.raises(ValidationError, match="deve ser texto"):
        CPF.parse(52998224725)  # type: ignore[arg-type]


def test_formatado():
    assert CPF.parse("52998224725").formatted == "529.982.247-25"


def test_mascara_nao_expoe_o_numero():
    """RNF04: log e stack trace nunca podem levar CPF completo."""
    cpf = CPF.parse("52998224725")
    assert cpf.masked == "***.***.247-**"
    assert "52998224725" not in repr(cpf)
    assert "529.982.247-25" not in repr(cpf)


def test_e_comparavel_e_hashavel():
    assert CPF.parse("529.982.247-25") == CPF.parse("52998224725")
    assert len({CPF.parse("52998224725"), CPF.parse("529.982.247-25")}) == 1


def test_str_usa_a_forma_pontuada():
    assert str(CPF.parse("52998224725")) == "529.982.247-25"
