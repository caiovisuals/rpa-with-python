# Parâmetros fiscais — documento de homologação

> **STATUS: VAZIO. NADA HOMOLOGADO.**
>
> Este documento é a **única** fonte autorizada de valores fiscais do sistema.
> Enquanto ele estiver incompleto, o motor de cálculo não pode ser implementado
> e o sistema não emite recibo definitivo.
>
> Não preencher por estimativa, por memória, por busca na internet sem fonte
> primária, nem por analogia com outro sistema. Cada linha precisa de **fonte
> oficial** e **aceite de profissional de contabilidade**.

## Como preencher

Para cada regra abaixo:

| Campo | O que registrar |
|---|---|
| Fonte | Norma, artigo, portaria ou página oficial, com data de consulta |
| Vigência | Data de início e, se houver, de fim |
| Valores | Faixas, alíquotas, tetos, deduções |
| Homologado por | Nome e registro do profissional |
| Homologado em | Data |

Depois de preenchido, este documento vira o *seed* das tabelas
`tax_rule_sets` / `tax_rule_brackets` (TASK-053) e a base dos casos de teste
(TASK-005).

---

## RV01 — INSS

Alíquotas e faixas; teto de contribuição; tratamento do contribuinte individual
em serviço prestado a pessoa jurídica versus a pessoa física.

- **Fonte:** _pendente_
- **Vigência:** _pendente_
- **Valores:** _pendente_
- **Homologado por / em:** _pendente_

## RV02 — IRRF

Tabela progressiva vigente; deduções aplicáveis; dedução por dependente;
existência e condições de desconto simplificado.

- **Fonte:** _pendente_
- **Vigência:** _pendente_
- **Valores:** _pendente_
- **Homologado por / em:** _pendente_

## RV03 — ISS

Se há retenção; qual município define a alíquota (o do prestador ou o da
prestação); alíquota aplicável; efeito de o autônomo possuir inscrição municipal.

- **Fonte:** _pendente_
- **Município(s) aplicável(is):** _pendente_
- **Vigência:** _pendente_
- **Valores:** _pendente_
- **Homologado por / em:** _pendente_

## RV04 — Ordem de cálculo e composição das bases

O que entra e o que sai da base de cada tributo, e em que sequência.
**A ordem altera o resultado final.**

- **Fonte:** _pendente_
- **Sequência definida:** _pendente_
- **Homologado por / em:** _pendente_

## RV05 — Arredondamento

Número de casas; momento do arredondamento (por parcela ou no total); critério
(para cima, meio para cima, meio para o par, truncamento).

As políticas disponíveis estão em `app/domain/rounding.py::RoundingPolicy`.
**O módulo não escolhe nenhuma por padrão — a escolha vem daqui.**

- **Fonte:** _pendente_
- **Política por tributo:** _pendente_
- **Homologado por / em:** _pendente_

## RV06 — Teto e múltiplas fontes

O que fazer quando o autônomo já atingiu limite mensal em outra fonte no mesmo
mês; se o sistema acumula por competência ou trata cada recibo isoladamente.

> Se a resposta exigir acumulação, isso **muda o modelo de dados** (acumulador
> mensal por autônomo) e habilita a TASK-057.

- **Fonte:** _pendente_
- **Regra:** _pendente_
- **Homologado por / em:** _pendente_

## RV07 — Data de referência

Regime de competência ou de caixa para selecionar a vigência dos parâmetros.
Afeta diretamente recibos na virada do ano.

- **Fonte:** _pendente_
- **Regra:** _pendente_
- **Homologado por / em:** _pendente_

## RV08 — Quem retém

Obrigações do tomador pessoa jurídica versus pessoa física; se o tipo de
contratante muda o conjunto de descontos aplicáveis.

- **Fonte:** _pendente_
- **Regra:** _pendente_
- **Homologado por / em:** _pendente_

## RV09 — Outras retenções

Retenções contratuais, sindicais ou de terceiros aplicáveis no contexto da
empresa.

- **Fonte:** _pendente_
- **Regra:** _pendente_
- **Homologado por / em:** _pendente_

## RV10 — Campos obrigatórios do recibo e prazo de guarda

Quais campos o documento precisa conter; por quanto tempo recibo e PDF devem
ser mantidos.

- **Fonte:** _pendente_
- **Campos:** _pendente_
- **Prazo de guarda:** _pendente_
- **Homologado por / em:** _pendente_

## RV11 — Dados cadastrais exigidos pelo cálculo

Quais atributos do autônomo o cálculo consome: número de dependentes,
obrigatoriedade do PIS/NIT, inscrição municipal, condição de contribuinte.

- **Fonte:** _pendente_
- **Lista final:** _pendente_
- **Homologado por / em:** _pendente_

---

## Casos de teste homologados

Meta: **≥ 20 casos** entrada → saída esperada, conferidos pelo contador,
cobrindo fronteiras de faixa, teto e arredondamento.

Destino: `tests/unit/fixtures/casos_fiscais/*.yaml` (TASK-005).

**Nenhum caso registrado até o momento.**
