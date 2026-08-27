# ADR-0005 — RPA e folha CLT: o que é compartilhado e o que não é

- **Status:** aceito — decisões D1, D1a e D1b respondidas em 2026-08-27
- **Contexto do backlog:** afeta a Fase 2 (modelo de dados) em diante

## Contexto

O escopo foi ampliado: além do RPA para prestadores autônomos, o sistema deve
calcular a **folha de pagamento** de funcionários CLT e emitir holerite. Não
entram, por ora, férias, 13º, rescisão e eSocial.

A ordem definida é RPA primeiro, até produção; CLT depois. Isso cria uma
armadilha conhecida: desenhar agora um modelo genérico "para os dois" produz
abstração especulativa; desenhar um modelo cego ao segundo regime produz
retrabalho destrutivo quando ele chegar.

## Decisão

**Compartilhar a infraestrutura e o motor. Não compartilhar as entidades.**

### Compartilhado desde já

| O quê | Por quê |
|---|---|
| `Money`, arredondamento, CPF/CNPJ, competência | Dinheiro e documento se comportam igual nos dois regimes |
| Motor de cálculo parametrizado por vigência | A mecânica de "faixa, alíquota, teto, ordem" é a mesma; o que muda são os parâmetros |
| Homologação de parâmetros (ADR-0004) | A folha precisa da mesma trava, com as suas próprias regras a validar |
| `organizations`, `users`, papéis, `audit_logs` | Mesma empresa, mesmas pessoas, mesma trilha |
| Armazenamento e versionamento de documentos | Holerite e recibo são PDFs com as mesmas exigências de integridade |
| `number_sequences` | **Com uma dimensão a mais**: o tipo de documento, para que RPA e holerite tenham sequências independentes |

### Não compartilhado

| O quê | Por quê |
|---|---|
| `workers` (autônomo) e o futuro `employees` (CLT) | Atributos incompatíveis: contrato, cargo, jornada, admissão e afastamento não existem no autônomo |
| `receipts` (RPA) e a futura tabela de holerite | Recibo é avulso por serviço; holerite é mensal recorrente com composição de proventos e descontos |
| As regras de cálculo | Regimes jurídicos diferentes, bases diferentes, obrigações diferentes |

### O ajuste que isso exige agora

Um só, e é barato: **`number_sequences` ganha a coluna do tipo de documento**
desde a primeira migration. Adicioná-la depois exigiria migrar dados de
numeração em produção — a pior categoria de migration que existe.

Todo o resto é aditivo: a chegada do CLT cria tabelas novas e tipos de regra
novos, sem renomear nem reaproveitar nada.

## O que foi deliberadamente não feito

**Nenhuma abstração `Beneficiario` ou `DocumentoDePagamento` genérica.** A regra
7 do `CLAUDE.md` — não criar abstração antes do segundo caso de uso real —
continua valendo, e um caso de uso *previsto* não é um caso de uso *real*.

O risco de generalizar agora é concreto: uma tabela `beneficiarios` com colunas
nulas para metade dos casos, e uma tabela `documentos` com um campo `tipo` que
todo `if` do sistema precisa consultar. Quando o CLT chegar de fato, com os seus
requisitos escritos, a abstração certa — se houver — vai estar visível. Hoje
seria adivinhação.

## Consequências

**A favor**

- O RPA é entregue sem carregar peso de um regime que ainda não existe.
- A chegada do CLT não obriga a mexer no que já estiver em produção.
- O motor de cálculo, que é a parte cara, é escrito uma vez.

**Contra**

- Haverá duplicação entre autônomo e funcionário — endereço, dados bancários,
  contato. É duplicação aceita: os dois cadastros divergem com o tempo, e
  unificá-los à força acopla dois domínios que mudam por motivos diferentes.
- O planejamento (roadmap, backlog, requisitos) cobre hoje só o RPA. Precisará
  de uma segunda rodada de descoberta para a folha, com perguntas próprias e
  homologação fiscal própria.
