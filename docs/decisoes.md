# Registro de decisões de escopo

Acompanha as decisões pendentes listadas na seção 19 de
[`PLANEJAMENTO.md`](PLANEJAMENTO.md). Cada resposta vira requisito e substitui a
hipótese correspondente.

| # | Pergunta | Resposta | Data | Efeito |
|---|---|---|---|---|
| D1 | Folha CLT está no escopo? | **Sim, funcionários CLT também** | 2026-08-27 | **Escopo ampliado. Replanejamento necessário** — ver abaixo. |
| D2 | Onde o sistema roda? | Servidor, acesso pelo navegador | 2026-08-27 | Confirma H02: FastAPI + PostgreSQL + Docker + login por papéis. Docker e compose criados. |
| D3 | Existe modelo de recibo atual? | Não existe; layout do zero | 2026-08-27 | O layout do PDF será proposto e validado junto com a RV10. Mantém em aberto a escolha da biblioteca (TASK-080). |
| D9 | Recibo emitido pode ser editado? | **Só antes de entregar ao autônomo** | 2026-08-27 | Substitui a hipótese H09. Novo estado `ENTREGUE`; retificação com número preservado. Ver ADR-0003. |
| D4 | Assinatura manuscrita ou digital? | _pendente_ | — | — |
| D5 | Integrações no MVP? | _pendente_ | — | — |
| D6 | Login com papéis distintos? | _pendente_ | — | Implícito na resposta a D2, mas não confirmado formalmente. |
| D7 | Uma empresa ou várias? | _pendente_ | — | — |
| D8 | Objetivo: interno, produto ou estudo? | _pendente_ | — | — |
| D10 | Volume mensal esperado? | _pendente_ | — | — |
| D11 | Quem homologa RV01–RV11? | _pendente_ | — | **Caminho crítico.** Bloqueia a Fase 4. |
| D12 | Orçamento e prazo? | _pendente_ | — | — |

---

## D1 — Ampliação de escopo para funcionários CLT

**Situação:** confirmado que o sistema deve atender também funcionários com
vínculo empregatício, e não apenas prestadores autônomos.

**Por que isso não é uma funcionalidade a mais.** RPA e folha de pagamento são
documentos diferentes, com regimes jurídicos diferentes, obrigações acessórias
diferentes e ciclos de vida diferentes:

| | RPA (autônomo) | Folha (CLT) |
|---|---|---|
| Vínculo | Nenhum | Contrato de trabalho |
| Documento | Recibo avulso por serviço | Holerite mensal recorrente |
| Cálculo | Descontos sobre o valor do serviço | Salário, horas, adicionais, faltas, benefícios |
| Eventos periódicos | Não existem | Férias, 13º, rescisão |
| Obrigações acessórias | — | eSocial, FGTS, guias mensais |
| Cadastro | Dados do prestador | Contrato, cargo, jornada, admissão, afastamentos |

**O que muda no planejamento:** o modelo de domínio, o modelo de dados, o motor
de cálculo (que passa a ter dois conjuntos de regras independentes), o backlog e
o roadmap. A homologação fiscal também dobra de tamanho: as regras RV01–RV11
cobrem apenas o lado do RPA.

**Status:** aguardando definição do que exatamente entra — folha de pagamento
completa com cálculo e eventos periódicos, ou apenas o registro dos pagamentos
feitos a funcionários, com o cálculo permanecendo na contabilidade.
**A Fase 2 (modelo de dados) está retida até essa definição**, porque começar
pelas tabelas antes de saber se existe a entidade `Funcionário` significaria
refazê-las.

**O que não é afetado e seguiu adiante:** a fundação do projeto, o domínio puro
(`Money`, arredondamento, CPF/CNPJ, competência) e a infraestrutura de
desenvolvimento. Nada disso muda com a ampliação — valores em `Decimal` e
validação de documento valem para os dois regimes.
