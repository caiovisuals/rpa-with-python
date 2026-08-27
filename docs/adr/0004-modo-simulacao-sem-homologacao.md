# ADR-0004 — Operar em simulação enquanto não houver homologação fiscal

- **Status:** aceito — decisão D11 respondida em 2026-08-27
- **Contexto do backlog:** TASK-052, TASK-056

## Contexto

O planejamento previa que o motor de cálculo ficasse bloqueado até a
homologação fiscal (RV01–RV11) existir. Na prática isso trava o projeto inteiro
atrás de uma dependência externa que ninguém controla: enquanto o contador não
responde, não dá para testar o fluxo, conferir a interface, validar o layout do
documento nem treinar quem vai operar.

A decisão foi começar antes. O problema a resolver é **como fazer isso sem que
um recibo calculado com número não verificado saia como se fosse válido**.

## Decisão

Parâmetros de cálculo passam a ter uma situação explícita de homologação:

- **`PROVISORIO`** — carregado por um administrador para uso, sem aceite de
  profissional de contabilidade. Calcula normalmente.
- **`HOMOLOGADO`** — conferido e aceito, com fonte, responsável e data
  registrados. Os três campos são obrigatórios: um registro homologado sem
  fonte e sem responsável não é homologação, é um campo preenchido.

O que o sistema pode produzir sai disso:

| Parâmetros aplicados | Resultado |
|---|---|
| Todos homologados | Documento **oficial** |
| Algum provisório | **Simulação**, com marca d'água |
| Nenhum | **Simulação** |

Três regras que a implementação garante:

1. **Um parâmetro provisório contamina o conjunto.** Um recibo com o INSS
   homologado e o IRRF chutado não é meio válido — é simulação.
2. **Nenhum parâmetro também é simulação.** Ausência de parâmetro não é "nada a
   conferir": é cálculo que ninguém verificou.
3. **A trava é estrutural.** `assert_can_issue()` recusa a emissão e a mensagem
   nomeia o que falta, para o operador saber a quem cobrar. Não depende de
   alguém lembrar.

## O que isto não afeta

**Nenhum número fiscal entra no código, nem provisório.** Parâmetro provisório é
*dado carregado por um administrador*, com registro de quem carregou e quando —
não é constante em Python, nem `# TODO: conferir depois` numa tabela hard-coded.
A regra 11 do `CLAUDE.md` continua valendo integralmente.

A diferença entre "provisório" e "inventado no código" é toda: o primeiro é
visível, rastreável, substituível por um administrador e barra a emissão; o
segundo se esconde no meio da lógica e ninguém lembra que estava lá.

## Consequências

**A favor**

- O projeto avança em paralelo à homologação, em vez de esperar por ela.
- Todo o fluxo pode ser exercitado com dados realistas antes do primeiro recibo real.
- Quando a homologação chegar, muda um registro de aprovação — não o código.

**Contra**

- Alguém vai olhar um número em tela de simulação e tratá-lo como verdadeiro.
  Mitigação: marca d'água no documento, aviso na tela de conferência e a
  impossibilidade técnica de emitir. Mitiga, não elimina — vale dizer isso a
  quem for operar.
- Um estado a mais para explicar na interface e na documentação.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Esperar a homologação** (plano original) | Trava o projeto atrás de dependência externa sem data. Foi a razão da mudança. |
| **Carregar valores "de exemplo" no código para destravar** | É exatamente o que a regra 11 proíbe. Valor de exemplo vira valor de produção no dia em que alguém esquece de trocar — e ninguém esquece de propósito. |
| **Emitir normalmente e revisar depois** | Recibo é documento contábil entregue a terceiros. Emitir com número não verificado e corrigir depois significa recolher documento que já saiu. |
