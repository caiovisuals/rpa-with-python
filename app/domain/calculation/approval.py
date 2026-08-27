"""Homologação dos parâmetros de cálculo.

Este módulo é o que torna seguro operar o sistema **antes** de a homologação
fiscal existir (decisão D11, respondida em 2026-08-27).

A ideia: parâmetros podem ser carregados como **provisórios** e o sistema
calcula normalmente com eles — mas todo resultado que dependa de um parâmetro
provisório fica marcado como **simulação** e não pode virar documento oficial.
A trava é estrutural, não uma lembrança do operador.

O que este módulo **não** faz: não contém alíquota, faixa nem teto, e não
decide se um parâmetro está correto. Ele só registra se alguém competente
assinou embaixo, e recusa a emissão quando ninguém assinou.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.domain.errors import NotHomologatedError, ValidationError


class ApprovalStatus(Enum):
    """Situação de um conjunto de parâmetros quanto à homologação."""

    PROVISORIO = "provisorio"
    """Carregado para uso, sem aceite de profissional de contabilidade.

    Serve para operar em simulação: o cálculo roda, o documento sai com marca
    d'água, e nada disso vale como recibo.
    """

    HOMOLOGADO = "homologado"
    """Conferido e aceito por profissional de contabilidade, com fonte registrada."""


class DocumentMode(Enum):
    """O que o sistema pode produzir com os parâmetros de que dispõe."""

    SIMULACAO = "simulacao"
    """Documento sem validade, com marca d'água. Não consome número de série."""

    OFICIAL = "oficial"
    """Documento válido. Exige que todos os parâmetros estejam homologados."""


@dataclass(frozen=True, slots=True)
class ParameterApproval:
    """Registro de homologação de um conjunto de parâmetros.

    Construído pelas fábricas :meth:`provisional` e :meth:`homologated`, que
    garantem que um registro homologado nunca fique com campos pela metade.
    """

    tax_type: str
    status: ApprovalStatus
    source_reference: str | None = None
    approved_by: str | None = None
    approved_at: date | None = None

    def __post_init__(self) -> None:
        if not self.tax_type.strip():
            raise ValidationError("o tipo de parâmetro é obrigatório")
        if self.status is ApprovalStatus.HOMOLOGADO:
            faltando = [
                nome
                for nome, valor in (
                    ("fonte", self.source_reference),
                    ("responsável pela homologação", self.approved_by),
                    ("data da homologação", self.approved_at),
                )
                if valor is None or (isinstance(valor, str) and not valor.strip())
            ]
            if faltando:
                raise ValidationError(
                    f"homologação de '{self.tax_type}' incompleta: falta "
                    + ", ".join(faltando)
                    + ". Parâmetro homologado sem fonte e sem responsável não é homologação."
                )

    @classmethod
    def provisional(
        cls, tax_type: str, *, source_reference: str | None = None
    ) -> ParameterApproval:
        """Parâmetro carregado para simulação, sem aceite contábil."""
        return cls(
            tax_type=tax_type,
            status=ApprovalStatus.PROVISORIO,
            source_reference=source_reference,
        )

    @classmethod
    def homologated(
        cls,
        tax_type: str,
        *,
        source_reference: str,
        approved_by: str,
        approved_at: date,
    ) -> ParameterApproval:
        """Parâmetro conferido e aceito. Todos os campos são obrigatórios."""
        return cls(
            tax_type=tax_type,
            status=ApprovalStatus.HOMOLOGADO,
            source_reference=source_reference,
            approved_by=approved_by,
            approved_at=approved_at,
        )

    @property
    def is_homologated(self) -> bool:
        return self.status is ApprovalStatus.HOMOLOGADO


def document_mode(approvals: list[ParameterApproval]) -> DocumentMode:
    """Decide o que o sistema pode produzir com os parâmetros informados.

    Basta **um** parâmetro provisório para o resultado inteiro ser simulação:
    um recibo com o INSS homologado e o IRRF chutado não é meio válido.

    Lista vazia também é simulação. Nenhum parâmetro não significa "nada a
    conferir" — significa que o cálculo não foi verificado por ninguém.
    """
    if not approvals:
        return DocumentMode.SIMULACAO
    if all(approval.is_homologated for approval in approvals):
        return DocumentMode.OFICIAL
    return DocumentMode.SIMULACAO


def pending_homologation(approvals: list[ParameterApproval]) -> list[str]:
    """Tipos de parâmetro que ainda faltam homologar, em ordem alfabética."""
    return sorted(a.tax_type for a in approvals if not a.is_homologated)


def assert_can_issue(approvals: list[ParameterApproval]) -> None:
    """Barra a emissão de documento oficial com parâmetro não homologado (RF42).

    Raises:
        NotHomologatedError: sempre que houver parâmetro provisório ou nenhum
            parâmetro. A mensagem nomeia o que falta, para o operador saber a
            quem cobrar.
    """
    if document_mode(approvals) is DocumentMode.OFICIAL:
        return
    if not approvals:
        raise NotHomologatedError(
            "nenhum parâmetro de cálculo aplicado: não é possível emitir recibo "
            "definitivo. O sistema opera em simulação até a homologação fiscal."
        )
    faltantes = ", ".join(pending_homologation(approvals))
    raise NotHomologatedError(
        f"parâmetros ainda provisórios: {faltantes}. "
        "Enquanto não houver homologação com fonte e responsável, o sistema "
        "só produz documento de simulação, com marca d'água."
    )
