"""As constraints do banco funcionam de verdade?

Constraint que ninguém tentou violar é constraint que talvez não exista. Cada
teste aqui tenta gravar dado inválido e exige que o banco recuse — a aplicação
dá a mensagem boa, mas é aqui que está a garantia de que ninguém contorna,
nem por script.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.domain.calculation.approval import ApprovalStatus, DocumentMode
from app.domain.receipt.status import ReceiptStatus
from app.models import (
    AuditLog,
    DocumentType,
    NumberSequence,
    Organization,
    Receipt,
    TaxRuleSet,
    User,
    Worker,
)
from tests.integration.factories import (
    CNPJ_FICTICIO_2,
    CPF_FICTICIO,
    approved_fields,
    draft_receipt,
    issued_fields,
    make_contractor,
    make_organization,
    make_sequence,
    make_user,
    make_worker,
)


def rejeita(session: Session, obj: object, constraint: str) -> None:
    """Grava e exige recusa do banco, nomeando a constraint esperada."""
    with pytest.raises(IntegrityError) as exc, session.begin_nested():
        session.add(obj)
        session.flush()
    assert constraint in str(exc.value), f"esperava violar {constraint}, veio: {exc.value}"


class TestCadastros:
    def test_cpf_duplicado_na_mesma_organizacao_e_recusado(self, session: Session):
        org = make_organization(session)
        make_worker(session, org)
        rejeita(
            session,
            Worker(
                organization_id=org.id,
                cpf=CPF_FICTICIO,
                full_name="Outra Pessoa",
                municipality="Rio de Janeiro",
                uf="RJ",
            ),
            "uq_workers_organization_id_cpf",
        )

    def test_mesmo_cpf_em_organizacoes_diferentes_e_permitido(self, session: Session):
        org_a = make_organization(session)
        org_b = make_organization(session, document="11444777000161")
        make_worker(session, org_a)
        make_worker(session, org_b)
        assert session.query(Worker).filter_by(cpf=CPF_FICTICIO).count() == 2

    def test_cpf_com_formato_invalido_e_recusado(self, session: Session):
        org = make_organization(session)
        rejeita(
            session,
            Worker(
                organization_id=org.id,
                cpf="529982247",
                full_name="Pessoa",
                municipality="São Paulo",
                uf="SP",
            ),
            "ck_workers_cpf_format",
        )

    def test_dependentes_negativos_sao_recusados(self, session: Session):
        org = make_organization(session)
        rejeita(
            session,
            Worker(
                organization_id=org.id,
                cpf=CPF_FICTICIO,
                full_name="Pessoa",
                municipality="São Paulo",
                uf="SP",
                dependents_count=-1,
            ),
            "ck_workers_dependents_count_non_negative",
        )

    def test_cnpj_de_11_digitos_como_pessoa_juridica_e_recusado(self, session: Session):
        org = make_organization(session)
        with pytest.raises(IntegrityError) as exc, session.begin_nested():
            make_contractor(session, org, document=CPF_FICTICIO)
        assert "ck_contractors_document_length_matches_type" in str(exc.value)


class TestValoresDoRecibo:
    def test_liquido_incoerente_e_recusado(self, session: Session):
        """A RN03 gravada no banco: líquido = bruto - descontos + acréscimos."""
        org = make_organization(session)
        user = make_user(session, org)
        worker = make_worker(session, org)
        contractor = make_contractor(session, org)
        recibo = draft_receipt(
            session,
            org,
            worker,
            contractor,
            user,
            deductions_total=Decimal("110.00"),
            net_amount=Decimal("900.00"),  # deveria ser 890,00
        )
        rejeita(session, recibo, "ck_receipts_net_amount_matches_parts")

    def test_bruto_zero_e_recusado(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        recibo = draft_receipt(
            session,
            org,
            make_worker(session, org),
            make_contractor(session, org),
            user,
            gross_amount=Decimal("0.00"),
            net_amount=Decimal("0.00"),
        )
        rejeita(session, recibo, "ck_receipts_gross_amount_positive")

    def test_liquido_negativo_e_recusado(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        recibo = draft_receipt(
            session,
            org,
            make_worker(session, org),
            make_contractor(session, org),
            user,
            gross_amount=Decimal("100.00"),
            deductions_total=Decimal("150.00"),
            net_amount=Decimal("-50.00"),
        )
        rejeita(session, recibo, "ck_receipts_net_amount_non_negative")

    def test_mes_de_competencia_invalido_e_recusado(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        recibo = draft_receipt(
            session,
            org,
            make_worker(session, org),
            make_contractor(session, org),
            user,
            competence_month=13,
        )
        rejeita(session, recibo, "ck_receipts_competence_month_range")


class TestRegrasDeEstado:
    def test_emitido_sem_numero_e_recusado(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        campos = issued_fields(user)
        campos.pop("number")
        recibo = draft_receipt(
            session, org, make_worker(session, org), make_contractor(session, org), user, **campos
        )
        rejeita(session, recibo, "ck_receipts_numbered_requires_numbering")

    def test_emitido_sem_snapshot_e_recusado(self, session: Session):
        """Sem snapshot, reimprimir traria os dados de hoje, não os da emissão."""
        org = make_organization(session)
        user = make_user(session, org)
        campos = issued_fields(user)
        campos.pop("worker_cpf_snapshot")
        recibo = draft_receipt(
            session, org, make_worker(session, org), make_contractor(session, org), user, **campos
        )
        rejeita(session, recibo, "ck_receipts_numbered_requires_snapshot")

    def test_recibo_em_simulacao_nao_pode_ser_emitido(self, session: Session):
        """ADR-0004 gravado no banco: simulação não alcança estado numerado."""
        org = make_organization(session)
        user = make_user(session, org)
        campos = issued_fields(user)
        campos["document_mode"] = DocumentMode.SIMULACAO
        recibo = draft_receipt(
            session, org, make_worker(session, org), make_contractor(session, org), user, **campos
        )
        rejeita(session, recibo, "ck_receipts_numbered_requires_official_mode")

    def test_cancelado_sem_motivo_e_recusado(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        campos = issued_fields(user)
        campos["status"] = ReceiptStatus.CANCELADO
        campos["cancelled_at"] = datetime(2026, 8, 28, tzinfo=UTC)
        campos["cancelled_by_id"] = user.id
        recibo = draft_receipt(
            session, org, make_worker(session, org), make_contractor(session, org), user, **campos
        )
        rejeita(session, recibo, "ck_receipts_cancelled_requires_reason")

    def test_motivo_em_branco_nao_conta_como_motivo(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        campos = issued_fields(user)
        campos.update(
            status=ReceiptStatus.CANCELADO,
            cancelled_at=datetime(2026, 8, 28, tzinfo=UTC),
            cancelled_by_id=user.id,
            cancel_reason="   ",
        )
        recibo = draft_receipt(
            session, org, make_worker(session, org), make_contractor(session, org), user, **campos
        )
        rejeita(session, recibo, "ck_receipts_cancelled_requires_reason")

    def test_entregue_sem_data_de_entrega_e_recusado(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        campos = issued_fields(user)
        campos["status"] = ReceiptStatus.ENTREGUE
        recibo = draft_receipt(
            session, org, make_worker(session, org), make_contractor(session, org), user, **campos
        )
        rejeita(session, recibo, "ck_receipts_immutable_requires_delivery")

    def test_recibo_emitido_valido_e_aceito(self, session: Session):
        """Contraprova: o caminho correto passa."""
        org = make_organization(session)
        user = make_user(session, org)
        recibo = draft_receipt(
            session,
            org,
            make_worker(session, org),
            make_contractor(session, org),
            user,
            **issued_fields(user),
        )
        session.flush()
        assert recibo.number == 1

    def test_recibo_nao_pode_substituir_a_si_mesmo(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        recibo = draft_receipt(
            session, org, make_worker(session, org), make_contractor(session, org), user
        )
        session.flush()
        recibo.replaces_id = recibo.id
        with pytest.raises(IntegrityError) as exc, session.begin_nested():
            session.flush()
        assert "ck_receipts_does_not_replace_itself" in str(exc.value)


class TestNumeracao:
    def test_numero_repetido_na_mesma_serie_e_ano_e_recusado(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        worker = make_worker(session, org)
        contractor = make_contractor(session, org)
        draft_receipt(session, org, worker, contractor, user, **issued_fields(user, number=7))
        session.flush()
        segundo = draft_receipt(
            session, org, worker, contractor, user, **issued_fields(user, number=7)
        )
        rejeita(session, segundo, "uq_receipts_organization_id_series_year_number")

    def test_varios_rascunhos_sem_numero_convivem(self, session: Session):
        """O índice único é parcial: rascunho não consome número."""
        org = make_organization(session)
        user = make_user(session, org)
        worker = make_worker(session, org)
        contractor = make_contractor(session, org)
        for _ in range(3):
            draft_receipt(session, org, worker, contractor, user)
        session.flush()
        assert session.query(Receipt).filter(Receipt.number.is_(None)).count() == 3

    def test_mesmo_numero_em_anos_diferentes_e_permitido(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        worker = make_worker(session, org)
        contractor = make_contractor(session, org)
        draft_receipt(
            session, org, worker, contractor, user, **issued_fields(user, number=1, year=2026)
        )
        draft_receipt(
            session, org, worker, contractor, user, **issued_fields(user, number=1, year=2027)
        )
        session.flush()
        assert session.query(Receipt).count() == 2

    def test_sequencia_duplicada_e_recusada(self, session: Session):
        org = make_organization(session)
        make_sequence(session, org)
        rejeita(
            session,
            NumberSequence(
                organization_id=org.id, document_type=DocumentType.RPA, series="A", year=2026
            ),
            "uq_number_sequences_organization_id_document_type_series_year",
        )


class TestParametrosFiscais:
    def _rule_set(self, org: Organization, user: User, **kwargs: object) -> TaxRuleSet:
        campos: dict[str, object] = {
            "organization_id": org.id,
            "tax_type": "exemplo_ficticio",
            "valid_from": date(2026, 1, 1),
            "valid_to": date(2026, 12, 31),
            "loaded_by_id": user.id,
        }
        campos.update(kwargs)
        return TaxRuleSet(**campos)

    def test_vigencias_sobrepostas_do_mesmo_tributo_sao_recusadas(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        session.add(self._rule_set(org, user))
        session.flush()
        rejeita(
            session,
            self._rule_set(org, user, valid_from=date(2026, 6, 1), valid_to=date(2027, 6, 1)),
            "ex_tax_rule_sets_no_overlapping_validity",
        )

    def test_vigencias_encostadas_sem_sobrepor_sao_aceitas(self, session: Session):
        """O intervalo é fechado-aberto: 31/12 termina onde 01/01 começa."""
        org = make_organization(session)
        user = make_user(session, org)
        session.add(self._rule_set(org, user))
        session.add(
            self._rule_set(org, user, valid_from=date(2027, 1, 1), valid_to=date(2027, 12, 31))
        )
        session.flush()
        assert session.query(TaxRuleSet).count() == 2

    def test_tributos_diferentes_podem_ter_a_mesma_vigencia(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        session.add(self._rule_set(org, user))
        session.add(self._rule_set(org, user, tax_type="outro_ficticio"))
        session.flush()
        assert session.query(TaxRuleSet).count() == 2

    def test_homologado_sem_fonte_e_recusado(self, session: Session):
        """A mesma regra do domínio, agora no banco."""
        org = make_organization(session)
        user = make_user(session, org)
        rejeita(
            session,
            self._rule_set(org, user, approval_status=ApprovalStatus.HOMOLOGADO),
            "ck_tax_rule_sets_homologation_is_complete",
        )

    def test_homologado_completo_e_aceito(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        session.add(
            self._rule_set(
                org, user, approval_status=ApprovalStatus.HOMOLOGADO, **approved_fields()
            )
        )
        session.flush()
        assert session.query(TaxRuleSet).count() == 1

    def test_vigencia_invertida_e_recusada(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        rejeita(
            session,
            self._rule_set(org, user, valid_from=date(2026, 12, 1), valid_to=date(2026, 1, 1)),
            "ck_tax_rule_sets_valid_period",
        )


class TestAuditoriaAppendOnly:
    def _log(self, org, user) -> AuditLog:
        return AuditLog(
            organization_id=org.id,
            user_id=user.id,
            action="receipt.issued",
            entity_type="receipt",
            created_at=datetime(2026, 8, 27, tzinfo=UTC),
        )

    def test_insercao_e_permitida(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        session.add(self._log(org, user))
        session.flush()
        assert session.query(AuditLog).count() == 1

    def test_alteracao_e_bloqueada_pelo_banco(self, session: Session):
        """Trilha que a aplicação pode reescrever não prova nada (RNF05)."""
        org = make_organization(session)
        user = make_user(session, org)
        log = self._log(org, user)
        session.add(log)
        session.flush()
        with pytest.raises(DBAPIError, match="append-only"), session.begin_nested():
            log.action = "outra.coisa"
            session.flush()

    def test_exclusao_e_bloqueada_pelo_banco(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        log = self._log(org, user)
        session.add(log)
        session.flush()
        with pytest.raises(DBAPIError, match="append-only"), session.begin_nested():
            session.delete(log)
            session.flush()


class TestIntegridadeReferencial:
    def test_nao_se_apaga_autonomo_com_recibo(self, session: Session):
        org = make_organization(session)
        user = make_user(session, org)
        worker = make_worker(session, org)
        draft_receipt(session, org, worker, make_contractor(session, org), user)
        session.flush()
        with pytest.raises(IntegrityError) as exc, session.begin_nested():
            session.execute(delete(Worker).where(Worker.id == worker.id))
        assert "fk_receipts_worker_id_workers" in str(exc.value)

    def test_snapshot_sobrevive_a_mudanca_de_cadastro(self, session: Session):
        """O ponto do snapshot: o recibo guarda o dado da emissão, não o de hoje."""
        org = make_organization(session)
        user = make_user(session, org)
        worker = make_worker(session, org)
        recibo = draft_receipt(
            session,
            org,
            worker,
            make_contractor(session, org),
            user,
            **issued_fields(user),
        )
        session.flush()
        worker.full_name = "Nome Alterado Depois"
        session.flush()
        session.refresh(recibo)
        assert recibo.worker_name_snapshot == "Prestador de Teste"
        assert recibo.contractor_document_snapshot == CNPJ_FICTICIO_2
