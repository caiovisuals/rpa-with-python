"""Exceções do domínio.

O domínio não conhece HTTP. Estas exceções são traduzidas para respostas na
borda da aplicação (`app/core/exceptions.py`, ainda não escrito).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base de toda violação de regra de domínio."""


class ValidationError(DomainError):
    """Valor de entrada inválido para o domínio."""


class InvariantViolationError(DomainError):
    """Uma invariante do agregado foi quebrada. Indica bug, não erro do usuário."""


class InvalidTransitionError(DomainError):
    """Transição de status não permitida pela máquina de estados."""


class ReasonRequiredError(DomainError):
    """A transição exige justificativa e nenhuma foi informada."""


class NotHomologatedError(DomainError):
    """Operação exige parâmetros homologados e algum deles é provisório."""
