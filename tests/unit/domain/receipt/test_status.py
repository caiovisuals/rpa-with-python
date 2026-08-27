"""Matriz completa da máquina de estados.

Todo par (origem, destino) é exercitado: os declarados devem passar, e **todos
os demais** devem ser recusados. Um teste que só verifica o caminho feliz
deixaria passar uma transição inventada por engano.
"""

import itertools

import pytest

from app.domain.errors import InvalidTransitionError, ReasonRequiredError
from app.domain.receipt.status import (
    IMMUTABLE_STATUSES,
    TERMINAL_STATUSES,
    TRANSITIONS,
    ReceiptStatus,
    allowed_targets,
    assert_editable,
    assert_transition,
    can_transition,
    find_transition,
    is_editable,
    is_terminal,
)

DECLARADAS = {(t.source, t.target) for t in TRANSITIONS}
TODOS_OS_PARES = list(itertools.product(ReceiptStatus, ReceiptStatus))
NAO_DECLARADAS = [par for par in TODOS_OS_PARES if par not in DECLARADAS]


class TestMatrizCompleta:
    @pytest.mark.parametrize(("source", "target"), sorted(DECLARADAS, key=str))
    def test_transicoes_declaradas_sao_permitidas(self, source, target):
        assert can_transition(source, target)
        transicao = assert_transition(source, target, reason="motivo informado")
        assert transicao.source is source
        assert transicao.target is target

    @pytest.mark.parametrize(("source", "target"), NAO_DECLARADAS)
    def test_todas_as_demais_sao_recusadas(self, source, target):
        assert not can_transition(source, target)
        assert find_transition(source, target) is None
        with pytest.raises(InvalidTransitionError):
            assert_transition(source, target, reason="motivo informado")

    def test_a_matriz_cobre_todos_os_pares(self):
        assert len(DECLARADAS) + len(NAO_DECLARADAS) == len(ReceiptStatus) ** 2


class TestRegrasDeFluxo:
    def test_rascunho_nao_vai_direto_para_emitido(self):
        """RN05: não existe atalho de rascunho para emitido."""
        with pytest.raises(InvalidTransitionError):
            assert_transition(ReceiptStatus.RASCUNHO, ReceiptStatus.EMITIDO)

    def test_emitido_nao_volta_para_rascunho(self):
        """RN09: recibo emitido é imutável."""
        with pytest.raises(InvalidTransitionError):
            assert_transition(ReceiptStatus.EMITIDO, ReceiptStatus.RASCUNHO)

    def test_nenhum_estado_transiciona_para_si_mesmo(self):
        for status in ReceiptStatus:
            assert not can_transition(status, status)

    @pytest.mark.parametrize("status", sorted(TERMINAL_STATUSES, key=str))
    def test_estados_terminais_nao_tem_saida(self, status):
        assert allowed_targets(status) == frozenset()
        assert is_terminal(status)

    def test_mensagem_de_erro_lista_os_destinos_possiveis(self):
        # A lista de destinos sai ordenada, portanto a mensagem é determinística.
        with pytest.raises(InvalidTransitionError, match=r"descartado, em_revisao"):
            assert_transition(ReceiptStatus.RASCUNHO, ReceiptStatus.PAGO)

    def test_mensagem_de_erro_em_estado_final(self):
        with pytest.raises(InvalidTransitionError, match="estado final"):
            assert_transition(ReceiptStatus.CANCELADO, ReceiptStatus.EMITIDO)


class TestJustificativa:
    @pytest.mark.parametrize(
        ("source", "target"),
        [
            (ReceiptStatus.EM_REVISAO, ReceiptStatus.RASCUNHO),
            (ReceiptStatus.EMITIDO, ReceiptStatus.CANCELADO),
        ],
    )
    def test_devolucao_e_cancelamento_exigem_motivo(self, source, target):
        with pytest.raises(ReasonRequiredError, match="exige justificativa"):
            assert_transition(source, target)

    @pytest.mark.parametrize("reason", [None, "", "   ", "\n\t"])
    def test_motivo_em_branco_nao_conta(self, reason):
        with pytest.raises(ReasonRequiredError):
            assert_transition(ReceiptStatus.EMITIDO, ReceiptStatus.CANCELADO, reason=reason)

    def test_motivo_valido_e_aceito(self):
        transicao = assert_transition(
            ReceiptStatus.EMITIDO, ReceiptStatus.CANCELADO, reason="valor bruto errado"
        )
        assert transicao.requires_reason

    def test_transicao_sem_exigencia_dispensa_motivo(self):
        assert_transition(ReceiptStatus.EM_REVISAO, ReceiptStatus.EMITIDO)


class TestEdicao:
    def test_apenas_rascunho_e_editavel(self):
        for status in ReceiptStatus:
            assert is_editable(status) is (status is ReceiptStatus.RASCUNHO)

    def test_assert_editable_passa_em_rascunho(self):
        assert_editable(ReceiptStatus.RASCUNHO)

    @pytest.mark.parametrize(
        "status", [s for s in ReceiptStatus if s is not ReceiptStatus.RASCUNHO]
    )
    def test_assert_editable_barra_os_demais(self, status):
        with pytest.raises(InvalidTransitionError, match="não pode ser alterado"):
            assert_editable(status)

    def test_estados_imutaveis_nao_sao_editaveis(self):
        for status in IMMUTABLE_STATUSES:
            assert not is_editable(status)


class TestEscopoDeclarado:
    def test_pago_nao_pode_ser_cancelado(self):
        """Decisão de escopo consciente: não foi confirmada e não foi inventada."""
        assert not can_transition(ReceiptStatus.PAGO, ReceiptStatus.CANCELADO)

    def test_toda_transicao_tem_descricao(self):
        for transicao in TRANSITIONS:
            assert transicao.description.strip()
