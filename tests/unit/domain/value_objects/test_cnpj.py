import pytest

from app.domain.errors import ValidationError
from app.domain.value_objects.cnpj import CNPJ

# CNPJs válidos quanto ao dígito verificador, gerados para teste. FICTÍCIOS.
VALIDOS = ["11222333000181", "11444777000161"]


@pytest.mark.parametrize("numero", VALIDOS)
def test_aceita_cnpj_com_digito_valido(numero):
    assert CNPJ.parse(numero).digits == numero


@pytest.mark.parametrize("entrada", ["11.222.333/0001-81", " 11222333000181 ", "11222333/000181"])
def test_ignora_pontuacao(entrada):
    assert CNPJ.parse(entrada).digits == "11222333000181"


@pytest.mark.parametrize("numero", ["11222333000182", "11444777000160"])
def test_recusa_digito_verificador_errado(numero):
    with pytest.raises(ValidationError, match="dígito verificador"):
        CNPJ.parse(numero)


@pytest.mark.parametrize("numero", [f"{d}" * 14 for d in range(10)])
def test_recusa_todos_os_digitos_iguais(numero):
    with pytest.raises(ValidationError, match="dígitos iguais"):
        CNPJ.parse(numero)


@pytest.mark.parametrize("entrada", ["", "112223330001", "112223330001812"])
def test_recusa_tamanho_errado(entrada):
    with pytest.raises(ValidationError, match="14 dígitos"):
        CNPJ.parse(entrada)


def test_recusa_tipo_errado():
    with pytest.raises(ValidationError, match="deve ser texto"):
        CNPJ.parse(11222333000181)  # type: ignore[arg-type]


def test_formatado():
    assert CNPJ.parse("11222333000181").formatted == "11.222.333/0001-81"


def test_e_comparavel_e_hashavel():
    assert CNPJ.parse("11.222.333/0001-81") == CNPJ.parse("11222333000181")
    assert len({CNPJ.parse("11222333000181"), CNPJ.parse("11.222.333/0001-81")}) == 1


def test_str_e_repr():
    cnpj = CNPJ.parse("11222333000181")
    assert str(cnpj) == "11.222.333/0001-81"
    assert repr(cnpj) == "CNPJ('11.222.333/0001-81')"
