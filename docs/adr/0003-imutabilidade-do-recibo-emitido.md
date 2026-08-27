# ADR-0003 — Recibo emitido é imutável

- **Status:** aceito, **sujeito a confirmação (decisão D9)**
- **Data:** 2026-08-27
- **Contexto do backlog:** TASK-042

## Contexto

O RPA é documento contábil. Depois de emitido e entregue ao autônomo, ele passa
a existir fora do sistema: impresso, arquivado, enviado ao contador.

A decisão D9 do planejamento — se recibo emitido pode ser editado ou apenas
cancelado e substituído — **ainda não foi confirmada**. Esta ADR registra a
hipótese H09 adotada e as suas consequências, para que a confirmação (ou a
correção) seja uma decisão informada.

## Decisão

Recibo em estado `EMITIDO` não pode ser alterado. Correção se faz por
**cancelamento com motivo obrigatório** seguido de **emissão de um recibo
substitutivo** que referencia o cancelado.

Implementado em `app/domain/receipt/status.py`:

- não existe transição `EMITIDO -> RASCUNHO`;
- `is_editable()` devolve verdadeiro apenas para `RASCUNHO`;
- `assert_editable()` barra qualquer alteração fora do rascunho;
- o cancelamento exige justificativa não vazia.

A mesma regra será espelhada por constraint no banco: a aplicação dá a mensagem
boa, o banco garante que ninguém contorna.

## Consequências

**A favor**

- O documento entregue e o registro no sistema nunca divergem.
- A trilha de auditoria fica completa por construção: todo erro corrigido deixa
  rastro de qual recibo foi cancelado, por quem e por quê.
- Numeração permanece confiável: número emitido nunca é reaproveitado.

**Contra**

- Corrigir um erro de digitação exige dois documentos (o cancelado e o novo).
  Operadores vão achar burocrático no começo.
- O modelo de dados precisa de auto-referência (`replaces` / `replaced_by`) e de
  snapshot dos dados na emissão.

## Se a decisão D9 for confirmada em sentido contrário

Se ficar decidido que recibo emitido pode ser editado, isso **não é ajuste de
uma regra**: cai o snapshot, cai a auto-referência de substituição, muda a
trilha de auditoria e muda a garantia do RNF02 (reimpressão fiel). Seria uma
revisão do modelo de dados inteiro, não uma alteração pontual.

## Nota de escopo registrada em código

Não existe transição `PAGO -> CANCELADO`. O fluxo confirmado (C03) não a prevê,
e criá-la seria inventar requisito. Se cancelar recibo já pago for necessário, é
decisão de negócio a confirmar antes de virar código.
