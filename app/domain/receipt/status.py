"""Máquina de estados do RPA.

Implementa a regra RN05 (ordem obrigatória rascunho -> revisão -> emitido) e a
RN09 (imutabilidade). A janela de correção fecha na **entrega ao autônomo**, não
na emissão: enquanto o recibo não saiu das mãos da empresa, ele pode voltar para
rascunho por retificação, preservando o número. Ver ADR-0003.

Toda transição que não estiver declarada em :data:`TRANSITIONS` é proibida — a
lista é a especificação, não uma sugestão.
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
    """Numerado, com documento oficial gerado, **ainda não entregue ao autônomo**.

    É o único estado em que uma correção ainda é possível sem cancelar: o recibo
    volta para rascunho por retificação, preservando o número já atribuído.
    """

    ENTREGUE = "entregue"
    """Entregue ao autônomo. A partir daqui o recibo é imutável (RN09)."""

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
        ReceiptStatus.RASCUNHO,
        requires_reason=True,
        description=(
            "Retificação antes da entrega. Só é possível enquanto o recibo não foi "
            "entregue ao autônomo. Preserva o número já atribuído e invalida o "
            "documento gerado, que precisa ser refeito na reemissão."
        ),
    ),
    Transition(
        ReceiptStatus.EMITIDO,
        ReceiptStatus.ENTREGUE,
        requires_reason=False,
        description=(
            "Entrega registrada por ação explícita do operador. É o ponto sem volta: "
            "a partir daqui o recibo é imutável."
        ),
    ),
    Transition(
        ReceiptStatus.EMITIDO,
        ReceiptStatus.CANCELADO,
        requires_reason=True,
        description="Cancelamento com motivo obrigatório. Preserva dados e documento.",
    ),
    Transition(
        ReceiptStatus.ENTREGUE,
        ReceiptStatus.PAGO,
        requires_reason=False,
        description="Pagamento registrado.",
    ),
    Transition(
        ReceiptStatus.ENTREGUE,
        ReceiptStatus.CANCELADO,
        requires_reason=True,
        description="Cancelamento com motivo obrigatório. Correção exige substitutivo.",
    ),
)
# NOTAS DE ESCOPO — decisões conscientes, não esquecimentos:
#
# 1. Não existe PAGO -> CANCELADO. O fluxo confirmado não a prevê, e inventá-la
#    seria criar requisito.
# 2. Não existe EMITIDO -> PAGO. O pagamento é registrado depois da entrega,
#    para que nenhum recibo alcance um estado final sem passar pelo ponto em
#    que se torna imutável. Se registrar pagamento antes da entrega for
#    necessário na prática, é decisão de negócio a confirmar.
# 3. Quem marca a entrega é o operador, por ação explícita. A alternativa seria
#    inferir a entrega do download ou do envio do PDF; ação explícita foi
#    preferida por ser auditável e deliberada — baixar o PDF para conferir não
#    é entregar. A confirmar (ver ADR-0003).

_INDEX: dict[tuple[ReceiptStatus, ReceiptStatus], Transition] = {
    (t.source, t.target): t for t in TRANSITIONS
}

#: Estados a partir dos quais não há saída.
TERMINAL_STATUSES = frozenset(
    {ReceiptStatus.PAGO, ReceiptStatus.CANCELADO, ReceiptStatus.DESCARTADO}
)

#: Estados em que o recibo já saiu das mãos da empresa e não pode mais mudar (RN09).
IMMUTABLE_STATUSES = frozenset(
    {ReceiptStatus.ENTREGUE, ReceiptStatus.PAGO, ReceiptStatus.CANCELADO}
)

#: Estados em que o recibo já consumiu um número de série. Um recibo que volta
#: para rascunho por retificação **mantém** o número: devolvê-lo à sequência
#: abriria lacuna na numeração (RN10).
NUMBERED_STATUSES = frozenset(
    {
        ReceiptStatus.EMITIDO,
        ReceiptStatus.ENTREGUE,
        ReceiptStatus.PAGO,
        ReceiptStatus.CANCELADO,
    }
)


def allowed_targets(source: ReceiptStatus) -> frozenset[ReceiptStatus]:
    """Estados alcançáveis a partir de ``source``."""
    return frozenset(t.target for t in TRANSITIONS if t.source is source)


def find_transition(source: ReceiptStatus, target: ReceiptStatus) -> Transition | None:
    """A transição declarada entre dois estados, ou ``None`` se não existir."""
    return _INDEX.get((source, target))


def can_transition(source: ReceiptStatus, target: ReceiptStatus) -> bool:
    return (source, target) in _INDEX


def is_editable(status: ReceiptStatus) -> bool:
    """Só o rascunho aceita edição direta (RF16).

    Um recibo emitido e ainda não entregue não é editado no lugar: ele volta
    para rascunho por retificação, o que deixa rastro na trilha de auditoria.
    """
    return status is ReceiptStatus.RASCUNHO


def can_be_retified(status: ReceiptStatus) -> bool:
    """Verdadeiro enquanto ainda dá para corrigir sem cancelar.

    A janela de correção fecha na entrega ao autônomo: depois disso o documento
    existe fora do sistema e corrigir vira cancelar e emitir substitutivo.
    """
    return can_transition(status, ReceiptStatus.RASCUNHO)


def is_immutable(status: ReceiptStatus) -> bool:
    """Verdadeiro quando nada mais no recibo pode mudar (RN09)."""
    return status in IMMUTABLE_STATUSES


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
    if is_editable(status):
        return
    if can_be_retified(status):
        raise InvalidTransitionError(
            f"recibo em {status.value} não é editado diretamente. "
            "Devolva-o para rascunho, com justificativa, antes de alterar."
        )
    raise InvalidTransitionError(
        f"recibo em {status.value} não pode ser alterado. "
        "A janela de correção fecha na entrega: cancele e emita um substitutivo."
    )
