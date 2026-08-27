from datetime import date

import pytest

from app.domain.errors import ValidationError
from app.domain.value_objects.competencia import MAX_YEAR, MIN_YEAR, Competencia


@pytest.mark.parametrize(("entrada", "esperado"), [("2026-08", (2026, 8)), ("08/2026", (2026, 8))])
def test_aceita_os_dois_formatos(entrada, esperado):
    competencia = Competencia.parse(entrada)
    assert (competencia.year, competencia.month) == esperado


def test_ignora_espacos_em_volta():
    assert Competencia.parse("  2026-08  ") == Competencia(2026, 8)


@pytest.mark.parametrize("entrada", ["2026-13", "00/2026", "2026/08", "agosto", "", "2026-8"])
def test_recusa_formato_ou_mes_invalido(entrada):
    with pytest.raises(ValidationError):
        Competencia.parse(entrada)


def test_recusa_tipo_errado():
    with pytest.raises(ValidationError, match="deve ser texto"):
        Competencia.parse(202608)  # type: ignore[arg-type]


@pytest.mark.parametrize("mes", [0, 13, -1])
def test_recusa_mes_fora_da_faixa(mes):
    with pytest.raises(ValidationError, match="mês inválido"):
        Competencia(2026, mes)


@pytest.mark.parametrize("ano", [MIN_YEAR - 1, MAX_YEAR + 1])
def test_recusa_ano_fora_da_faixa(ano):
    with pytest.raises(ValidationError, match="ano fora da faixa"):
        Competencia(ano, 1)


def test_virada_de_ano():
    assert Competencia(2026, 12).next() == Competencia(2027, 1)
    assert Competencia(2026, 1).previous() == Competencia(2025, 12)


def test_avanca_e_volta_dentro_do_ano():
    assert Competencia(2026, 8).next() == Competencia(2026, 9)
    assert Competencia(2026, 8).previous() == Competencia(2026, 7)


def test_ordenacao_respeita_ano_antes_do_mes():
    assert Competencia(2025, 12) < Competencia(2026, 1)
    assert sorted([Competencia(2026, 3), Competencia(2025, 9)])[0] == Competencia(2025, 9)


def test_a_partir_de_data():
    assert Competencia.from_date(date(2026, 8, 27)) == Competencia(2026, 8)


def test_primeiro_dia():
    assert Competencia(2026, 8).first_day == date(2026, 8, 1)


def test_representacoes():
    competencia = Competencia(2026, 8)
    assert str(competencia) == "08/2026"
    assert competencia.iso == "2026-08"
    assert repr(competencia) == "Competencia('2026-08')"


def test_round_trip_iso():
    competencia = Competencia(2026, 8)
    assert Competencia.parse(competencia.iso) == competencia
    assert Competencia.parse(str(competencia)) == competencia


@pytest.mark.parametrize(("ano", "mes"), [("2026", 8), (2026, "08"), (2026.0, 8)])
def test_recusa_ano_ou_mes_que_nao_sao_inteiros(ano, mes):
    with pytest.raises(ValidationError, match="inteiros"):
        Competencia(ano, mes)
