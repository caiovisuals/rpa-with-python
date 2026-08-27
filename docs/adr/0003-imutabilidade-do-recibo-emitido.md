# ADR-0003 — A janela de correção fecha na entrega, não na emissão

- **Status:** aceito — decisão D9 respondida em 2026-08-27
- **Substitui:** a versão anterior desta ADR, que assumia imutabilidade a partir da emissão (hipótese H09)
- **Contexto do backlog:** TASK-042

## Contexto

O RPA é documento contábil. Depois de entregue ao autônomo, ele passa a existir
fora do sistema: impresso, arquivado, enviado ao contador. A partir daí,
qualquer divergência entre o papel na mão da pessoa e o registro no sistema é um
problema real.

A hipótese original (H09) era mais rígida: imutável já na emissão, correção
apenas por cancelamento e substituição. A resposta à decisão D9 foi diferente:
**editar é permitido enquanto o recibo não tiver sido entregue ao autônomo.**

O raciocínio da resposta é sólido. Um erro de digitação percebido trinta
segundos depois de emitir, com o PDF ainda na tela, não justifica um par de
documentos — cancelado e substitutivo — na contabilidade. O que torna o recibo
irreversível não é a emissão: é ele sair das mãos da empresa.

## Decisão

Um estado a mais entre a emissão e o fim do fluxo:

```
EM_REVISAO ──▶ EMITIDO ──▶ ENTREGUE ──▶ PAGO
                  │            │
                  │            └──▶ CANCELADO  (motivo obrigatório)
                  │
                  ├──▶ RASCUNHO   retificação, motivo obrigatório
                  └──▶ CANCELADO  (motivo obrigatório)
```

- **`EMITIDO`** — numerado, documento oficial gerado, ainda não entregue.
  Corrigível: volta para rascunho por **retificação**, com justificativa.
- **`ENTREGUE`** — registrado por **ação explícita do operador**. Ponto sem
  volta: a partir daqui vale a imutabilidade integral, e correção é cancelar e
  emitir substitutivo.

Três consequências que não são opcionais:

1. **O número é preservado na retificação.** Um recibo que volta para rascunho
   mantém o número que já consumiu. Devolvê-lo à sequência abriria lacuna na
   numeração e quebraria a RN10.
2. **O documento gerado é invalidado.** Retificar torna obsoleto o PDF emitido;
   a reemissão gera um novo, e o histórico de documentos guarda os dois.
3. **Retificação exige justificativa.** É a única coisa que separa "corrigi um
   erro de digitação" de "mudei o valor depois de emitido" na auditoria.

## Consequências

**A favor**

- Corrigir um erro percebido na hora custa uma retificação, não dois documentos.
- A auditoria continua completa: toda retificação deixa autor, motivo e horário.
- A regra fica ancorada em um evento verificável — a entrega — e não em um
  estado técnico interno.

**Contra**

- A imutabilidade agora depende de uma ação humana estar correta. Se ninguém
  marcar a entrega, o recibo fica corrigível indefinidamente. Mitigação prevista:
  alerta na listagem para recibos emitidos há muito tempo e não entregues.
- Um estado a mais na máquina, na interface e no relatório.

## O ponto que ainda precisa de confirmação

**Quem marca a entrega, e como.** A escolha implementada é *ação explícita do
operador*: existe um comando "marcar como entregue", e nada mais dispara a
transição.

A alternativa seria inferir a entrega de um evento do sistema — baixar o PDF ou
enviá-lo por e-mail. Foi descartada por ser frágil no sentido perigoso: **baixar
o PDF para conferir não é entregar**, e um download acidental fecharia a janela
de correção sem que ninguém tivesse decidido isso. Quando o envio por e-mail
existir (RF28), ele pode virar um gatilho automático legítimo — aí o sistema
sabe que o documento saiu.

## Notas de escopo registradas em código

- Não existe `EMITIDO -> PAGO`: o pagamento é registrado depois da entrega, para
  que nenhum recibo chegue a um estado final sem passar pelo ponto em que se
  torna imutável.
- Não existe `PAGO -> CANCELADO`: o fluxo confirmado não a prevê, e criá-la
  seria inventar requisito.

Ambas são decisões conscientes, não esquecimentos, e ambas são reversíveis se o
uso real mostrar que atrapalham.
