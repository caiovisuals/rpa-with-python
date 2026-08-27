"""A trava que permite operar sem homologação fiscal sem produzir recibo inválido."""

from datetime import date

import pytest

from app.domain.calculation.approval import (
    ApprovalStatus,
    DocumentMode,
    ParameterApproval,
    assert_can_issue,
    document_mode,
    pending_homologation,
)
from app.domain.errors import NotHomologatedError, ValidationError

# Dados de homologação FICTÍCIOS. Não vieram de fonte oficial e não representam
# nenhum parâmetro real — servem só para exercitar a trava.
FONTE = "documento de homologação fictício (teste)"
RESPONSAVEL = "Contador de Teste"
DATA = date(2026, 1, 1)


def homologado(tax_type: str) -> ParameterApproval:
    return ParameterApproval.homologated(
        tax_type, source_reference=FONTE, approved_by=RESPONSAVEL, approved_at=DATA
    )


class TestConstrucao:
    def test_provisorio_dispensa_fonte_e_responsavel(self):
        approval = ParameterApproval.provisional("inss")
        assert approval.status is ApprovalStatus.PROVISORIO
        assert not approval.is_homologated

    def test_provisorio_aceita_fonte_opcional(self):
        approval = ParameterApproval.provisional("inss", source_reference="rascunho interno")
        assert approval.source_reference == "rascunho interno"

    def test_homologado_exige_tudo(self):
        approval = homologado("inss")
        assert approval.is_homologated
        assert approval.source_reference == FONTE
        assert approval.approved_by == RESPONSAVEL
        assert approval.approved_at == DATA

    @pytest.mark.parametrize(
        ("campos", "esperado"),
        [
            ({"source_reference": None}, "fonte"),
            ({"approved_by": None}, "responsável"),
            ({"approved_at": None}, "data"),
            ({"source_reference": "   "}, "fonte"),
            ({"approved_by": ""}, "responsável"),
        ],
    )
    def test_homologacao_incompleta_e_recusada(self, campos, esperado):
        base = {
            "tax_type": "inss",
            "status": ApprovalStatus.HOMOLOGADO,
            "source_reference": FONTE,
            "approved_by": RESPONSAVEL,
            "approved_at": DATA,
        }
        with pytest.raises(ValidationError, match=esperado):
            ParameterApproval(**{**base, **campos})

    def test_homologacao_sem_nenhum_campo_lista_todos(self):
        with pytest.raises(ValidationError) as exc:
            ParameterApproval(tax_type="inss", status=ApprovalStatus.HOMOLOGADO)
        mensagem = str(exc.value)
        assert "fonte" in mensagem
        assert "responsável" in mensagem
        assert "data" in mensagem

    @pytest.mark.parametrize("tax_type", ["", "   "])
    def test_tipo_de_parametro_e_obrigatorio(self, tax_type):
        with pytest.raises(ValidationError, match="tipo de parâmetro"):
            ParameterApproval.provisional(tax_type)


class TestModoDoDocumento:
    def test_sem_parametro_nenhum_e_simulacao(self):
        """Nenhum parâmetro não é 'nada a conferir': é cálculo não verificado."""
        assert document_mode([]) is DocumentMode.SIMULACAO

    def test_todos_homologados_produz_documento_oficial(self):
        assert document_mode([homologado("inss"), homologado("irrf")]) is DocumentMode.OFICIAL

    def test_um_provisorio_contamina_o_conjunto(self):
        approvals = [homologado("inss"), ParameterApproval.provisional("irrf")]
        assert document_mode(approvals) is DocumentMode.SIMULACAO

    def test_todos_provisorios_e_simulacao(self):
        approvals = [ParameterApproval.provisional("inss"), ParameterApproval.provisional("irrf")]
        assert document_mode(approvals) is DocumentMode.SIMULACAO


class TestPendencias:
    def test_lista_apenas_os_provisorios_em_ordem(self):
        approvals = [
            ParameterApproval.provisional("iss"),
            homologado("inss"),
            ParameterApproval.provisional("irrf"),
        ]
        assert pending_homologation(approvals) == ["irrf", "iss"]

    def test_lista_vazia_quando_tudo_homologado(self):
        assert pending_homologation([homologado("inss")]) == []


class TestTravaDeEmissao:
    def test_permite_emitir_com_tudo_homologado(self):
        assert_can_issue([homologado("inss"), homologado("irrf")])

    def test_barra_emissao_sem_nenhum_parametro(self):
        with pytest.raises(NotHomologatedError, match="nenhum parâmetro"):
            assert_can_issue([])

    def test_barra_emissao_com_parametro_provisorio(self):
        approvals = [homologado("inss"), ParameterApproval.provisional("irrf")]
        with pytest.raises(NotHomologatedError, match="ainda provisórios: irrf"):
            assert_can_issue(approvals)

    def test_mensagem_nomeia_todos_os_faltantes(self):
        approvals = [
            ParameterApproval.provisional("iss"),
            ParameterApproval.provisional("inss"),
        ]
        with pytest.raises(NotHomologatedError, match="inss, iss"):
            assert_can_issue(approvals)

    def test_mensagem_explica_o_que_o_sistema_faz_enquanto_isso(self):
        with pytest.raises(NotHomologatedError, match="simulação"):
            assert_can_issue([ParameterApproval.provisional("inss")])


class TestCoerencia:
    def test_trava_e_modo_do_documento_concordam_sempre(self):
        casos = [
            [],
            [homologado("inss")],
            [ParameterApproval.provisional("inss")],
            [homologado("inss"), ParameterApproval.provisional("irrf")],
        ]
        for approvals in casos:
            oficial = document_mode(approvals) is DocumentMode.OFICIAL
            try:
                assert_can_issue(approvals)
                permitiu = True
            except NotHomologatedError:
                permitiu = False
            assert permitiu is oficial

    def test_registro_e_imutavel(self):
        approval = homologado("inss")
        with pytest.raises(AttributeError):
            approval.tax_type = "irrf"  # type: ignore[misc]
