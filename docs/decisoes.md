# Registro de decisões de escopo

Acompanha as decisões pendentes listadas na seção 19 de
[`PLANEJAMENTO.md`](PLANEJAMENTO.md). Cada resposta vira requisito e substitui a
hipótese correspondente.

| # | Pergunta | Resposta | Data | Efeito |
|---|---|---|---|---|
| D1 | Folha CLT está no escopo? | **Sim — folha de pagamento completa** | 2026-08-27 | Escopo ampliado. Alcance definido abaixo; construção depois do RPA. |
| D1a | O que o sistema faz com CLT? | Calcula a folha e emite holerite | 2026-08-27 | Segundo motor de cálculo, com homologação própria. **Sem** férias, 13º, rescisão e eSocial. |
| D1b | Em que ordem construir? | **RPA primeiro, CLT depois** | 2026-08-27 | Fase 2 destravada para o RPA, com o modelo desenhado para receber CLT de forma aditiva. Ver ADR-0005. |
| D2 | Onde o sistema roda? | Servidor, acesso pelo navegador | 2026-08-27 | Confirma H02: FastAPI + PostgreSQL + Docker + login por papéis. Docker e compose criados. |
| D3 | Existe modelo de recibo atual? | Não existe; layout do zero | 2026-08-27 | O layout do PDF será proposto e validado junto com a RV10. Mantém em aberto a escolha da biblioteca (TASK-080). |
| D9 | Recibo emitido pode ser editado? | **Só antes de entregar ao autônomo** | 2026-08-27 | Substitui a hipótese H09. Novo estado `ENTREGUE`; retificação com número preservado. Ver ADR-0003. |
| D4 | Assinatura manuscrita ou digital? | _pendente_ | — | — |
| D5 | Integrações no MVP? | _pendente_ | — | — |
| D6 | Login com papéis distintos? | _pendente_ | — | Implícito na resposta a D2, mas não confirmado formalmente. |
| D7 | Uma empresa ou várias? | _pendente_ | — | — |
| D8 | Objetivo: interno, produto ou estudo? | _pendente_ | — | — |
| D10 | Volume mensal esperado? | _pendente_ | — | — |
| D11 | Quem homologa RV01–RV11? | **Começar sem homologação, em simulação** | 2026-08-27 | Fase 4 destravada em modo simulação. Parâmetros provisórios calculam, mas não emitem documento oficial. Ver ADR-0004. |
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

### Alcance definido

**Entra:** cálculo da folha mensal (salário, horas, adicionais, faltas,
benefícios e descontos) e emissão de holerite.

**Não entra:** férias, 13º salário, rescisão e eSocial. Essa fronteira é
importante e precisa ser dita em voz alta — **uma empresa com funcionários CLT
tem essas obrigações de qualquer forma**. O que a decisão significa é que elas
continuam sendo tratadas fora deste sistema, provavelmente pela contabilidade.
Se em algum momento a expectativa virar "o sistema resolve a folha inteira",
isso é uma terceira ampliação de escopo, não um detalhe.

### Ordem de construção

RPA primeiro, até produção. CLT depois, como módulo adicional.

O modelo de dados do RPA será desenhado para **receber** o regime CLT de forma
aditiva — novas tabelas e novos tipos de regra —, sem precisar renomear ou
reaproveitar o que já existir. O que os dois regimes compartilham é a
infraestrutura e o motor de cálculo parametrizado; o que **não** compartilham é
a entidade do beneficiário e o documento. Ver
[ADR-0005](adr/0005-rpa-e-folha-clt-o-que-e-compartilhado.md).

**Deliberadamente não construído agora:** nenhuma abstração "Beneficiário" ou
"DocumentoDePagamento" genérica. A regra 7 do `CLAUDE.md` continua valendo —
abstração depois do segundo caso de uso **real**, não do segundo caso previsto.
Prever é diferente de ter.

**O que não foi afetado:** a fundação, o domínio puro (`Money`, arredondamento,
CPF/CNPJ, competência) e a infraestrutura. Valores em `Decimal` e validação de
documento valem para os dois regimes sem nenhuma alteração.


---

## D11 — Operar sem homologação fiscal

**Situação:** confirmado começar antes de a homologação existir, com o sistema
em modo simulação.

**Como isso funciona.** Parâmetros de cálculo podem ser carregados como
**provisórios**: o sistema calcula normalmente com eles, mas todo resultado que
dependa de um parâmetro provisório é marcado como simulação, sai com marca
d'água e **não pode virar recibo definitivo**. A trava é estrutural
(`app/domain/calculation/approval.py`), não uma lembrança do operador.

Basta **um** parâmetro provisório para o resultado inteiro ser simulação: um
recibo com o INSS homologado e o IRRF chutado não é meio válido.

**O que isso permite:** montar e testar todo o fluxo, conferir a interface,
validar o layout do documento e treinar quem vai operar — sem esperar o contador.

**O que isso não muda:** nenhum número fiscal entra no código, nem provisório.
Parâmetro provisório é *dado carregado por um administrador*, com registro de
quem carregou; não é constante em Python. A regra do `CLAUDE.md` continua
valendo integralmente.

**O que continua bloqueado:** a emissão de recibo com valor legal. Enquanto
`docs/parametros-fiscais.md` estiver incompleto, o sistema não produz documento
oficial — e essa é a única forma honesta de "começar sem homologação".
