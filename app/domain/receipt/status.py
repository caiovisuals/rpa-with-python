"""Máquina de estados do RPA.

Implementa a regra RN05 (ordem obrigatória rascunho → revisão → emitido) e a
RN09 (recibo emitido é imutável). Toda transição que não estiver declarada em
:data:`TRANSITIONS` é proibida — a lista é a especificação, não uma sugestão.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.errors import InvalidTransitionError, ReasonRequiredError


class ReceiptStatus(Enum):
    """Estados possíveis de um RPA."""

    RASCUNHO = "rascunho"
    """Em preenchimento. É o único estado em que o recibo pode ser editado."""

    EM_REVISAO = "em_revisao"
    """Conferido pelo operador, aguardando confirmação do revisor."""

    EMITIDO = "emitido"
    """Numerado e imutável. O PDF gerado a partir daqui é o documento oficial."""

    PAGO = "pago"
    """Pagamento registrado."""

    CANCELADO = "cancelado"
    """Cancelado com motivo. Os dados e o PDF são preservados (RN11)."""

    DESCARTADO = "descartado"
    """Rascunho abandonado. Não consome número de série (RN10)."""


@dataclass(frozen=True, slots=True)
class Transition:
    """Uma transição permitida."""

    source: ReceiptStatus
    target: ReceiptStatus
    requires_reason: bool
    description: str


TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        ReceiptStatus.RASCUNHO,
        ReceiptStatus.EM_REVISAO,
        requires_reason=False,
        description="Operador conferiu os valores e enviou para revisão.",
    ),
    Transition(
        ReceiptStatus.RASCUNHO,
        ReceiptStatus.DESCARTADO,
        requires_reason=False,
        description="Rascunho abandonado antes de qualquer emissão.",
    ),
    Transition(
        ReceiptStatus.EM_REVISAO,
        ReceiptStatus.RASCUNHO,
        requires_reason=True,
        description="Revisor devolveu para correção, com justificativa.",
    ),
    Transition(
        ReceiptStatus.EM_REVISAO,
        ReceiptStatus.EMITIDO,
        requires_reason=False,
        description="Revisor confirmou. Numera, congela os dados e gera o documento.",
    ),
    Transition(
        ReceiptStatus.EMITIDO,
        ReceiptStatus.PAGO,
        requires_reason=False,
        description="Pagamento registrado.",
    ),
    Transition(
        ReceiptStatus.EMITIDO,
        ReceiptStatus.CANCELADO,
        requires_reason=True,
        description="Cancelamento com motivo obrigatório. Preserva dados e PDF.",
    ),
)
# NOTA DE ESCOPO: não existe transição PAGO -> CANCELADO. O fluxo confirmado
# (C03) e o diagrama do planejamento não a preveem, e inventá-la seria criar
# requisito. Se cancelar recibo já pago for necessário, isso é uma decisão de
# negócio a confirmar antes de virar código.

_INDEX: dict[tuple[ReceiptStatus, ReceiptStatus], Transition] = {
    (t.source, t.target): t for t in TRANSITIONS
}

#: Estados a partir dos quais não há saída.
TERMINAL_STATUSES = frozenset(
    {ReceiptStatus.PAGO, ReceiptStatus.CANCELADO, ReceiptStatus.DESCARTADO}
)

#: Estados em que o recibo já é documento oficial e não pode mais ser alterado (RN09).
IMMUTABLE_STATUSES = frozenset({ReceiptStatus.EMITIDO, ReceiptStatus.PAGO, ReceiptStatus.CANCELADO})


def allowed_targets(source: ReceiptStatus) -> frozenset[ReceiptStatus]:
    """Estados alcançáveis a partir de ``source``."""
    return frozenset(t.target for t in TRANSITIONS if t.source is source)


def find_transition(source: ReceiptStatus, target: ReceiptStatus) -> Transition | None:
    """A transição declarada entre dois estados, ou ``None`` se não existir."""
    return _INDEX.get((source, target))


def can_transition(source: ReceiptStatus, target: ReceiptStatus) -> bool:
    return (source, target) in _INDEX


def is_editable(status: ReceiptStatus) -> bool:
    """Só o rascunho pode ser editado (RN09, RF16)."""
    return status is ReceiptStatus.RASCUNHO


def is_terminal(status: ReceiptStatus) -> bool:
    return status in TERMINAL_STATUSES


def assert_transition(
    source: ReceiptStatus,
    target: ReceiptStatus,
    *,
    reason: str | None = None,
) -> Transition:
    """Valida a transição e devolve a regra aplicada.

    Raises:
        InvalidTransitionError: a transição não está declarada.
        ReasonRequiredError: a transição exige justificativa e nenhuma foi dada.
    """
    transition = _INDEX.get((source, target))
    if transition is None:
        permitted = sorted(s.value for s in allowed_targets(source))
        allowed = ", ".join(permitted) if permitted else "nenhum (estado final)"
        raise InvalidTransitionError(
            f"transição não permitida: {source.value} -> {target.value}. "
            f"A partir de {source.value} só é possível ir para: {allowed}."
        )
    if transition.requires_reason and not (reason or "").strip():
        raise ReasonRequiredError(
            f"a transição {source.value} -> {target.value} exige justificativa."
        )
    return transition


def assert_editable(status: ReceiptStatus) -> None:
    """Barra qualquer alteração fora do rascunho (RN09)."""
    if not is_editable(status):
        raise InvalidTransitionError(
            f"recibo em {status.value} não pode ser alterado. "
            "Recibo emitido é imutável: cancele e emita um substitutivo."
        )
