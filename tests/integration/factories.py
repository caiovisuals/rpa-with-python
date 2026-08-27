"""Construtores de dados para os testes de integração.

**Todos os dados aqui são fictícios.** Os CPFs e CNPJs são válidos apenas
quanto ao dígito verificador; não pertencem a ninguém (CLAUDE.md, regra 18).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.calculation.approval import DocumentMode
from app.domain.receipt.status import ReceiptStatus
from app.models import (
    Contractor,
    DocumentType,
    NumberSequence,
    Organization,
    PersonType,
    Receipt,
    User,
    UserRole,
    Worker,
)

CPF_FICTICIO = "52998224725"
CPF_FICTICIO_2 = "11144477735"
CNPJ_FICTICIO = "11222333000181"
CNPJ_FICTICIO_2 = "11444777000161"


def make_organization(session: Session, *, document: str = CNPJ_FICTICIO) -> Organization:
    org = Organization(
        name="Empresa de Teste", legal_name="Empresa de Teste LTDA", document=document
    )
    session.add(org)
    session.flush()
    return org


def make_user(
    session: Session,
    org: Organization,
    *,
    email: str = "operador@exemplo.invalid",
    role: UserRole = UserRole.OPERADOR,
) -> User:
    user = User(
        organization_id=org.id,
        email=email,
        password_hash="argon2-falso-para-teste",
        full_name="Pessoa Operadora",
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def make_worker(
    session: Session, org: Organization, *, cpf: str = CPF_FICTICIO, **kwargs: object
) -> Worker:
    defaults: dict[str, object] = {
        "full_name": "Prestador de Teste",
        "municipality": "São Paulo",
        "uf": "SP",
    }
    defaults.update(kwargs)
    worker = Worker(organization_id=org.id, cpf=cpf, **defaults)
    session.add(worker)
    session.flush()
    return worker


def make_contractor(
    session: Session, org: Organization, *, document: str = CNPJ_FICTICIO_2, **kwargs: object
) -> Contractor:
    defaults: dict[str, object] = {
        "legal_name": "Contratante de Teste LTDA",
        "document_type": PersonType.PESSOA_JURIDICA,
        "municipality": "São Paulo",
        "uf": "SP",
    }
    defaults.update(kwargs)
    contractor = Contractor(organization_id=org.id, document=document, **defaults)
    session.add(contractor)
    session.flush()
    return contractor


def make_sequence(session: Session, org: Organization, *, year: int = 2026) -> NumberSequence:
    sequence = NumberSequence(
        organization_id=org.id, document_type=DocumentType.RPA, series="A", year=year
    )
    session.add(sequence)
    session.flush()
    return sequence


def draft_receipt(
    session: Session,
    org: Organization,
    worker: Worker,
    contractor: Contractor,
    user: User,
    **kwargs: object,
) -> Receipt:
    """Rascunho coerente. Os valores são fictícios e não vieram de cálculo real."""
    defaults: dict[str, object] = {
        "competence_year": 2026,
        "competence_month": 8,
        "gross_amount": Decimal("1000.00"),
        "deductions_total": Decimal("0.00"),
        "additions_total": Decimal("0.00"),
        "net_amount": Decimal("1000.00"),
    }
    defaults.update(kwargs)
    receipt = Receipt(
        organization_id=org.id,
        worker_id=worker.id,
        contractor_id=contractor.id,
        created_by_id=user.id,
        **defaults,
    )
    session.add(receipt)
    return receipt


def issued_fields(user: User, *, number: int = 1, year: int = 2026) -> dict[str, object]:
    """Campos que a emissão obriga: numeração, autoria e snapshot congelado."""
    return {
        "status": ReceiptStatus.EMITIDO,
        "document_mode": DocumentMode.OFICIAL,
        "series": "A",
        "year": year,
        "number": number,
        "issued_at": datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
        "issued_by_id": user.id,
        "worker_name_snapshot": "Prestador de Teste",
        "worker_cpf_snapshot": CPF_FICTICIO,
        "contractor_name_snapshot": "Contratante de Teste LTDA",
        "contractor_document_snapshot": CNPJ_FICTICIO_2,
    }


def approved_fields() -> dict[str, object]:
    """Homologação fictícia, para exercitar a constraint — não é fonte oficial."""
    return {
        "source_reference": "documento fictício de teste",
        "approved_by": "Contador de Teste",
        "approved_at": date(2026, 1, 1),
    }
