"""Tabelas do sistema.

Importar este pacote registra todas as tabelas no metadata — é isso que permite
ao Alembic enxergar o schema completo.
"""

from app.models.audit import AuditLog
from app.models.base import Base
from app.models.document import DocumentKind, ReceiptDocument, ReceiptStatusHistory
from app.models.numbering import DocumentType, NumberSequence
from app.models.organization import Organization, User, UserRole
from app.models.party import (
    BankAccountType,
    Contractor,
    PersonType,
    Worker,
    WorkerBankAccount,
)
from app.models.receipt import (
    DeductionKind,
    DeductionOrigin,
    Receipt,
    ReceiptEntry,
    ReceiptService,
)
from app.models.tax_rule import TaxRuleBracket, TaxRuleSet

__all__ = [
    "AuditLog",
    "BankAccountType",
    "Base",
    "Contractor",
    "DeductionKind",
    "DeductionOrigin",
    "DocumentKind",
    "DocumentType",
    "NumberSequence",
    "Organization",
    "PersonType",
    "Receipt",
    "ReceiptDocument",
    "ReceiptEntry",
    "ReceiptService",
    "ReceiptStatusHistory",
    "TaxRuleBracket",
    "TaxRuleSet",
    "User",
    "UserRole",
    "Worker",
    "WorkerBankAccount",
]
