# Planejamento — Sistema de RPA (Recibo de Pagamento Autônomo)

> **Status:** Fase 0 — Discovery. Nenhum código foi escrito.
> **Data:** 2026-08-27
> **Regra mestra deste documento:** nenhuma regra tributária foi inventada. Toda alíquota, faixa,
> teto, dedução ou ordem de cálculo aparece como **parâmetro a preencher** ou **regra a validar**,
> nunca como número afirmado.

---

## 0. Base do planejamento: o que é requisito e o que é hipótese

### 0.1 Requisitos confirmados por você

| # | Confirmado |
|---|---|
| C01 | O sistema será usado por **uma empresa** que paga vários prestadores. |
| C02 | Existe o papel de **operador**, que cadastra dados e confere valores. |
| C03 | Fluxo: cadastrar autônomo -> cadastrar contratante (se não existir) -> registrar serviço -> informar valor bruto -> **sistema calcula descontos** -> operador confere -> RPA disponível para revisão -> após confirmação, **emitido** -> gera PDF -> PDF baixado e enviado ao autônomo. |
| C04 | O sistema deve tratar "os principais descontos e retenções aplicáveis ao RPA", **sem assumir regras tributárias sem validação**. |
| C05 | Dados do autônomo: nome, CPF, PIS/NIT (se necessário), endereço, município/UF, dados bancários/PIX (se necessários), dados necessários aos cálculos. |
| C06 | Dados do contratante: razão social/nome, CNPJ/CPF, endereço, município/UF, inscrição municipal (se necessária). |
| C07 | Dados do serviço: descrição, data/período, competência, valor bruto, dados necessários aos cálculos. |

### 0.2 Hipóteses adotadas (perguntas 5–10 não respondidas)

Estas **não são requisitos**. São premissas explícitas para destravar o planejamento.
Cada uma tem um item correspondente na seção 19 (Decisões pendentes).

| # | Hipótese | Impacto se estiver errada |
|---|---|---|
| H01 | **Escopo é apenas autônomos/prestadores sem vínculo.** Folha CLT (funcionários) está **fora**. | Alto. Folha CLT é outro sistema (eSocial, FGTS, férias, 13º, rescisão). Replanejamento total. |
| H02 | Aplicação **web multiusuário**, rodando em servidor/container, acessada pelo navegador. | Alto. Se for uso local monousuário, troca-se PostgreSQL por SQLite e some metade da infraestrutura. |
| H03 | **PDF é obrigatório**; layout único inicialmente, com logotipo e dados da empresa configuráveis. | Médio. Se houver um modelo em Word/papel timbrado atual, ele vira a especificação exata. |
| H04 | Assinatura no MVP é **campo em branco para assinatura manuscrita**. Sem assinatura digital ICP-Brasil. | Médio. Assinatura digital com validade jurídica é um épico próprio. |
| H05 | **Sem integrações externas no MVP.** Envio de e-mail entra na Fase 2. | Baixo/Médio. |
| H06 | **Login obrigatório**, com perfis distintos (admin / operador / revisor / consulta). | Médio. |
| H07 | **Uma organização** (single-tenant) no MVP, mas o modelo já carrega `organization_id` para permitir multi-tenant depois sem migração dolorosa. | Baixo. Barato agora, caro depois. |
| H08 | **Uso interno profissional**, não SaaS comercial — mas com qualidade de produção (dados pessoais + financeiros reais). | Médio. |
| H09 | **RPA emitido é imutável.** Correção se faz por cancelamento + emissão substitutiva, não por edição. | Alto no modelo de dados. É a premissa mais importante da seção 5. |
| H10 | Volume estimado: **dezenas a poucas centenas de recibos/mês**. Não há requisito de alta escala. | Baixo. Se forem milhares/dia, revisar geração de PDF assíncrona. |
| H11 | Existe **emissão em lote** como necessidade futura (fechamento mensal), não no MVP. | Baixo. |
| H12 | Retenção de dados/documentos por **prazo legal contábil**, a confirmar com o contador. | Médio (LGPD + storage). |

### 0.3 Postura sobre tributos — inegociável

O sistema **não terá regra tributária codificada em Python**. Terá um **motor de cálculo genérico**
que lê **tabelas de parâmetros versionadas por vigência**, preenchidas a partir de fonte oficial e
homologadas por um profissional de contabilidade. Consequências:

1. Nenhum número (alíquota, faixa, teto, dedução) no código-fonte.
2. Toda tabela tem `vigencia_inicio` / `vigencia_fim` e é imutável após uso em um recibo emitido.
3. Todo recibo emitido guarda um **snapshot** de quais parâmetros usou — reimpressão de um recibo
   antigo devolve exatamente os mesmos valores, para sempre.
4. Nenhuma tabela vai para produção sem: fonte documentada (URL/norma) + aprovação registrada.
5. Enquanto não houver homologação, o sistema opera em **modo rascunho/simulação**, com marca
   d'água no PDF e bloqueio de emissão definitiva.

---

## 1. Resumo do produto

**O que é.** Um sistema web interno para uma empresa emitir, controlar e arquivar Recibos de
Pagamento Autônomo dos prestadores de serviço que ela contrata.

**Quem usa.** Operadores do financeiro/RH da empresa (cadastro e digitação), um revisor/aprovador
(confere e emite) e um administrador (configura empresa, usuários e tabelas de cálculo). O autônomo
não acessa o sistema no MVP — ele recebe o PDF.

**Problema que resolve.**
- Hoje o recibo é feito à mão (planilha/Word), com risco de erro de cálculo e de digitação;
- Não há histórico consultável, numeração confiável nem rastro de quem alterou o quê;
- Reemitir ou localizar um recibo antigo é trabalhoso;
- Os parâmetros de cálculo mudam de ano para ano e ficam espalhados em versões de planilha.

**Fluxo principal (o C03, formalizado como máquina de estados):**

```
[cadastros]  Autônomo + Contratante
                    |
                    v
RASCUNHO --(operador preenche serviço e valor bruto)--> RASCUNHO (calculado)
   |                                                        |
   | descarta                                    envia para revisão
   v                                                        v
DESCARTADO                                            EM_REVISAO
                                                       |        |
                                       revisor devolve |        | revisor confirma
                                                       v        v
                                                  RASCUNHO    EMITIDO  (imutável, numerado, PDF gerado)
                                                                  |
                                                    +-------------+-------------+
                                                    v                           v
                                                  PAGO                      CANCELADO
                                                                                |
                                                                    (opcional) SUBSTITUIDO_POR -> novo RPA
```

**Não-objetivos declarados (MVP):** folha de pagamento CLT, emissão de NFS-e, integração com
eSocial/DIRF, portal do autônomo, app mobile, assinatura digital ICP-Brasil, cobrança/SaaS.

---

## 2. Requisitos funcionais

Classificação: **[E]** Essencial (MVP) · **[I]** Importante (pós-MVP próximo) · **[F]** Futuro.
Origem: **C** = confirmado por você · **H** = derivado de hipótese.

### Cadastros
| ID | Requisito | Cls. | Origem |
|---|---|---|---|
| RF01 | Cadastrar, editar, inativar e consultar **autônomo** (nome, CPF, PIS/NIT, endereço, município/UF). | E | C05 |
| RF02 | Cadastrar dados bancários/PIX do autônomo, como dado opcional e sensível. | I | C05 |
| RF03 | Cadastrar, editar, inativar e consultar **contratante** (razão social/nome, CNPJ/CPF, endereço, município/UF, inscrição municipal). | E | C06 |
| RF04 | Registrar atributos do autônomo exigidos pelo cálculo (ex.: nº de dependentes, condição de contribuinte, inscrição municipal). **Lista exata definida na homologação fiscal.** | E | C04/C05 |
| RF05 | Impedir CPF/CNPJ duplicado na mesma organização. | E | H |
| RF06 | Validar dígito verificador de CPF e CNPJ. | E | H |
| RF07 | Importar cadastros em massa via CSV. | F | H |

### Serviço e recibo
| ID | Requisito | Cls. | Origem |
|---|---|---|---|
| RF08 | Registrar **serviço prestado**: descrição, data ou período de execução, competência, valor bruto. | E | C07 |
| RF09 | Criar RPA em **RASCUNHO** vinculando autônomo + contratante + serviço. | E | C03 |
| RF10 | **Calcular automaticamente** descontos/retenções e valor líquido a partir do bruto. | E | C03/C04 |
| RF11 | Exibir **memória de cálculo** detalhada (base, parâmetro aplicado, valor de cada desconto). | E | C03 (o operador precisa conferir) |
| RF12 | Permitir **recálculo** enquanto em rascunho, a cada alteração. | E | C03 |
| RF13 | Enviar RPA para **revisão**. | E | C03 |
| RF14 | Revisor **confirmar e emitir**, ou devolver para rascunho com justificativa. | E | C03 |
| RF15 | **Numeração sequencial** automática e sem lacunas, atribuída no momento da emissão. | E | H |
| RF16 | Bloquear edição após emissão (imutabilidade). | E | H09 |
| RF17 | **Cancelar** RPA emitido com motivo obrigatório. | E | H09 |
| RF18 | Emitir RPA **substitutivo** referenciando o cancelado. | I | H09 |
| RF19 | Marcar RPA como **pago**, com data e forma de pagamento. | I | H |
| RF20 | Lançar **descontos/acréscimos manuais** (adiantamento, material, multa) com descrição. | I | H |
| RF21 | Emissão **em lote** por competência. | F | H11 |
| RF22 | RPA com múltiplos itens de serviço (várias linhas). | F | H |

### Documento
| ID | Requisito | Cls. | Origem |
|---|---|---|---|
| RF23 | Gerar **PDF** do RPA com todos os campos, memória de descontos e campo de assinatura. | E | C03 |
| RF24 | Baixar o PDF. | E | C03 |
| RF25 | PDF de rascunho sai com **marca d'água "SEM VALIDADE / RASCUNHO"**. | E | H |
| RF26 | Configurar logotipo e dados da empresa emissora no documento. | I | H03 |
| RF27 | PDF com **código/hash de verificação** de autenticidade. | I | H |
| RF28 | Enviar PDF por **e-mail** ao autônomo. | I | H05 |
| RF29 | Personalização de layout / múltiplos modelos. | F | H03 |
| RF30 | Assinatura digital com validade jurídica (ICP-Brasil). | F | H04 |

### Consulta, histórico e exportação
| ID | Requisito | Cls. | Origem |
|---|---|---|---|
| RF31 | Listar RPAs com filtro por período, competência, status, autônomo, contratante, número. | E | — |
| RF32 | Visualizar RPA completo com memória de cálculo e histórico de status. | E | — |
| RF33 | Reimprimir/rebaixar o PDF original de um RPA emitido (idêntico ao gerado). | E | H |
| RF34 | Exportar listagem filtrada em **CSV/XLSX**. | I | — |
| RF35 | Relatório por autônomo/competência (totais brutos, descontos, líquidos). | I | — |
| RF36 | Exportar em layout de sistema contábil específico. | F | — |

### Administração, acesso e auditoria
| ID | Requisito | Cls. | Origem |
|---|---|---|---|
| RF37 | Autenticação por usuário e senha. | E | H06 |
| RF38 | Perfis de acesso: **admin, revisor, operador, consulta**. | E | H06 |
| RF39 | Gerenciar usuários (criar, desativar, redefinir senha). | E | H06 |
| RF40 | **Log de auditoria** imutável de toda operação sobre recibos, cadastros e parâmetros. | E | H |
| RF41 | Cadastrar/versionar **tabelas de parâmetros de cálculo** por vigência, com fonte e responsável pela homologação. | E | C04 |
| RF42 | Bloquear emissão definitiva enquanto a vigência aplicável não estiver homologada. | E | C04 |
| RF43 | Simulador de cálculo (calcula sem criar recibo). | I | — |
| RF44 | Registro de consentimento/base legal LGPD e atendimento a titular. | I | H |
| RF45 | 2FA para administradores. | F | — |

---

## 3. Requisitos não funcionais

| ID | Categoria | Requisito |
|---|---|---|
| RNF01 | **Corretude financeira** | Todo valor monetário usa `Decimal`, nunca `float`. Regra de arredondamento única, explícita e documentada, definida na homologação fiscal. Cálculo **determinístico**: mesma entrada + mesma vigência = mesmo resultado, sempre. |
| RNF02 | **Rastreabilidade** | Todo recibo emitido guarda snapshot de dados e parâmetros. Reimpressão 5 anos depois produz valores idênticos. |
| RNF03 | **Segurança** | Senhas com Argon2id. Sessões/tokens com expiração. Autorização verificada no servidor em toda rota. Segredos fora do repositório. HTTPS obrigatório em produção. |
| RNF04 | **Privacidade / LGPD** | Minimização de dados; dados bancários criptografados em repouso; logs sem PII e sem CPF completo; política de retenção documentada; procedimento de atendimento ao titular. |
| RNF05 | **Auditoria** | Trilha append-only com autor, timestamp UTC, ação, entidade, valores antes/depois. Não editável pela aplicação. |
| RNF06 | **Performance** | Listagem paginada < 500 ms p95 com 100k recibos. Geração de PDF < 3 s p95 (síncrona no MVP). |
| RNF07 | **Disponibilidade** | Uso em horário comercial. Sem requisito de alta disponibilidade no MVP. RTO 4h / RPO 24h como ponto de partida (a confirmar). |
| RNF08 | **Backup** | Backup diário automatizado do banco + storage de PDFs, com **teste de restauração periódico documentado**. Backup que nunca foi restaurado não conta como backup. |
| RNF09 | **Escalabilidade** | Arquitetura modular monolítica; escala vertical suficiente para H10. Multi-tenant preparado no schema, não ativado. |
| RNF10 | **Manutenibilidade** | Domínio isolado de framework e de banco. Type hints obrigatórios; `mypy`/`ruff` no CI. Sem abstração criada antes do segundo caso de uso real. |
| RNF11 | **Testabilidade** | Motor de cálculo é função pura, testável sem banco, sem HTTP e sem I/O. |
| RNF12 | **Observabilidade** | Logs estruturados em JSON com `request_id`; healthcheck; métricas básicas (recibos emitidos, erros de cálculo, falhas de PDF). |
| RNF13 | **Portabilidade** | Sobe com `docker compose up` em uma máquina limpa. Setup de dev documentado e reproduzível. |
| RNF14 | **Internacionalização** | Não. Sistema em pt-BR, moeda BRL, fuso America/Sao_Paulo (armazenar UTC, exibir local). |

---

## 4. Regras de negócio

### 4.1 Regras confirmadas (derivadas das suas respostas)

| ID | Regra |
|---|---|
| RN01 | Um RPA relaciona **um autônomo**, **um contratante** e **um serviço prestado**. |
| RN02 | O operador informa o **valor bruto**; o sistema calcula os descontos. O bruto nunca é calculado a partir do líquido (no MVP). |
| RN03 | `valor_liquido = valor_bruto - soma(descontos) + soma(acrescimos)`. Esta identidade é invariante e será testada. |
| RN04 | O RPA só é emitido após conferência do operador e confirmação na etapa de revisão. |
| RN05 | Ordem obrigatória de estados: RASCUNHO -> EM_REVISAO -> EMITIDO. Não existe atalho de rascunho para emitido. |
| RN06 | O PDF só é o documento oficial quando o RPA está EMITIDO; antes disso sai como rascunho sem validade. |
| RN07 | Todo cálculo exibido ao operador vem acompanhado da memória de cálculo (base, parâmetro, resultado). |
| RN08 | Nenhum desconto é aplicado sem uma regra parametrizada correspondente e homologada. |

### 4.2 Regras estruturais (decisões de projeto, não tributárias)

| ID | Regra |
|---|---|
| RN09 | RPA emitido é **imutável**. Correção = cancelar (com motivo) + emitir substitutivo. |
| RN10 | Numeração é atribuída **na emissão**, é sequencial por (organização, série, ano) e não tem lacunas. Rascunho descartado não consome número. |
| RN11 | Cancelamento **não apaga** o recibo nem o PDF; apenas muda o status e registra motivo e autor. |
| RN12 | Cadastro nunca é apagado fisicamente; é inativado. Recibos históricos preservam os dados como estavam na emissão. |
| RN13 | A vigência de parâmetros aplicada a um recibo é escolhida por uma **data de referência** — e **qual data** (competência, execução ou pagamento) é uma **regra tributária a validar** (ver RV07). |
| RN14 | Tabela de parâmetros já usada em recibo emitido não pode ser editada; só sucedida por nova vigência. |

### 4.3 Regras que precisam de validação — NÃO IMPLEMENTAR ANTES DE VALIDAR

Cada item abaixo é uma **lacuna deliberada**. Preciso, para cada um, de: a fonte oficial (norma/URL),
o valor vigente, e o aceite de um contador. Nenhum valor foi presumido.

| ID | Regra a validar | Por que importa | Bloqueia |
|---|---|---|---|
| RV01 | **INSS** — quais alíquotas/faixas, teto máximo de contribuição, e como se aplica a contribuinte individual em serviço prestado a PJ vs. a PF. | Define um dos principais descontos. | RF10 |
| RV02 | **IRRF** — tabela progressiva vigente, deduções aplicáveis, dedução por dependente, e se há opção de desconto simplificado. | Segundo principal desconto. | RF10 |
| RV03 | **ISS** — se há retenção, qual município define a alíquota (o do prestador ou o da prestação), a alíquota aplicável, e o efeito de o autônomo ter inscrição municipal. | Varia por município; muda o campo "município" de decorativo para determinante. | RF10, RF03 |
| RV04 | **Ordem de cálculo e composição das bases** — o que entra e o que sai da base de cada tributo, e em que sequência. | A ordem muda o resultado final. **Não vou assumir a sequência.** | RF10 |
| RV05 | **Arredondamento** — número de casas, momento do arredondamento (por parcela ou no total) e critério (para cima / meio para cima / bancário). | Diferenças de centavos viram divergência contábil. | RNF01 |
| RV06 | **Teto e múltiplas fontes** — o que fazer quando o autônomo já atingiu limite mensal em outra fonte no mesmo mês; se o sistema acumula por competência ou trata cada recibo isoladamente. | Muda o modelo de dados (precisa de acumulador mensal por autônomo). | RF10, modelo |
| RV07 | **Data de referência** — regime de competência ou de caixa para escolher a vigência de cada tributo. | Recibos no fim/início de ano ficam errados se isso for chutado. | RN13 |
| RV08 | **Quem retém** — obrigações do tomador PJ vs. PF; se muda o conjunto de descontos aplicáveis. | Determina se o tipo de contratante é variável de cálculo. | RF10, RF03 |
| RV09 | **Outras retenções** possíveis no contexto da empresa (contratuais, sindicais, terceiros). | Escopo do motor. | RF10 |
| RV10 | **Campos obrigatórios legais do recibo** e prazo de guarda do documento. | Layout do PDF e política de retenção. | RF23, RNF04 |
| RV11 | **Dados cadastrais exigidos pelo cálculo** (dependentes, PIS/NIT obrigatório ou não, inscrição municipal). | Fecha a lista final do RF04. | RF04 |

**Produto de saída desta validação:** uma planilha `docs/parametros-fiscais.md` com, para cada regra,
a fonte, a vigência, o valor e a assinatura de quem homologou — que vira o *seed* das tabelas do
sistema. **Enquanto esse documento não existir, o motor roda com tabelas vazias e o sistema não
emite recibo definitivo.**

---

## 5. Modelo de domínio

Só entidades que os requisitos justificam. Cortei deliberadamente `Payment` como entidade própria
(vira campos em `Receipt` até existir baixa parcial) e `Tax` como entidade global (vira parâmetro
versionado).

### 5.1 Entidades

| Entidade | Responsabilidade | Justificativa |
|---|---|---|
| `Organization` | A empresa dona dos dados. | H07 — presente desde o início como chave de escopo, mesmo com um único registro. |
| `User` | Quem acessa o sistema. Tem `role`. | RF37–RF39 |
| `Worker` (autônomo) | Prestador sem vínculo. Dados cadastrais + atributos fiscais. | C05 |
| `WorkerBankAccount` | Dados bancários/PIX. Tabela separada por ser o dado mais sensível. | RF02, RNF04 — separar facilita criptografia e acesso restrito. |
| `Contractor` | Tomador do serviço. | C06 |
| `Receipt` (RPA) | Agregado raiz. Status, número, datas, valores totais, snapshots. | C03 |
| `ReceiptService` | O serviço prestado: descrição, período, competência, valor bruto. | C07. Tabela separada já prepara o RF22 (múltiplos itens) sem refatoração dolorosa. |
| `ReceiptDeduction` | Cada desconto/acréscimo do recibo: tipo, base, parâmetro aplicado, valor, origem (automática/manual). | RF11, RF20 — é a memória de cálculo persistida. |
| `TaxRuleSet` | Conjunto de parâmetros com vigência: `tipo`, `vigencia_inicio`, `vigencia_fim`, `fonte`, `homologado_por`, `homologado_em`. | C04, RN14 |
| `TaxRuleBracket` | Faixa/linha de um `TaxRuleSet`: limites, alíquota, parcela a deduzir, teto. Campos genéricos o bastante para representar tabela progressiva ou alíquota única — **sem nenhum valor embutido**. | C04 |
| `ReceiptDocument` | O PDF gerado: caminho/blob, `sha256`, tamanho, versão do template, quando e por quem. | RF23, RF33, RNF02 |
| `ReceiptStatusHistory` | Cada transição de status: de, para, autor, motivo, quando. | RF32, RN11 |
| `AuditLog` | Trilha append-only de toda operação relevante. | RF40, RNF05 |
| `NumberSequence` | Controle de numeração por (org, série, ano). | RF15, RN10 |

**Descartadas por ora (e por quê):** `Payment` (sem requisito de baixa parcial — vira `paid_at` +
`payment_method` em `Receipt`); `Address` como entidade (é value object embutido — endereço não é
consultado independentemente); `Municipality` como tabela (só vira tabela se RV03 exigir alíquota por
município); `Role` como tabela (enum basta para 4 perfis fixos).

### 5.2 Relacionamentos

```
Organization 1---N User
Organization 1---N Worker 1---0..N WorkerBankAccount
Organization 1---N Contractor
Organization 1---N Receipt
Organization 1---N TaxRuleSet 1---N TaxRuleBracket
Organization 1---N NumberSequence

Worker      1---N Receipt        (RESTRICT: não se apaga autônomo com recibo)
Contractor  1---N Receipt        (RESTRICT)
User        1---N Receipt        (created_by, issued_by, cancelled_by)

Receipt     1---N ReceiptService
Receipt     1---N ReceiptDeduction
Receipt     1---N ReceiptStatusHistory
Receipt     1---0..N ReceiptDocument     (rascunho + definitivo + reemissões)
Receipt     0..1--0..1 Receipt           (auto-referência: replaced_by / replaces)

AuditLog    N---1 User          (ator; nullable para ações do sistema)
AuditLog    ~ polimórfico       (entity_type + entity_id, sem FK)
```

### 5.3 A decisão de modelagem mais importante: snapshot na emissão

No momento da emissão, `Receipt` copia para dentro de si:
- nome, CPF, PIS/NIT e endereço do autônomo **como estavam naquele instante**;
- razão social, CNPJ/CPF e endereço do contratante;
- o `tax_rule_set_id` (+ hash dos parâmetros) usado em cada `ReceiptDeduction`.

**Por quê:** o autônomo muda de endereço, o contratante muda de razão social, a tabela do ano vira.
Sem snapshot, a reimpressão de um recibo de 2024 sairia com dados de 2026 — documento contábil
falsificado por acidente. Com snapshot, RNF02 é garantido por construção.

**Custo:** duplicação de dados. **Aceito conscientemente** — é o padrão de documentos fiscais.

---

## 6. Arquitetura recomendada

### 6.1 Forma geral

**Monólito modular em camadas, com o domínio isolado.**

```
   HTTP (FastAPI routers)         <- valida entrada, autentica, autoriza, serializa
            |
   Services / Use cases           <- orquestra: transação, regras de fluxo, chama domínio
            |
   Domain (puro Python)           <- motor de cálculo, máquina de estados, invariantes
            |
   Repositories (SQLAlchemy)      <- acesso a dados
            |
   PostgreSQL                     Storage de PDFs
```

**Por que monólito e não microsserviços:** um time (você), volume baixo (H10), transações que
precisam ser atômicas (numerar + emitir + gravar). Microsserviço aqui só adiciona latência, falha
distribuída e complexidade operacional sem resolver nenhum problema real. **Isso é overengineering
e está descartado.**

**Por que camadas e não tudo no router:** o motor de cálculo é o ativo crítico do sistema (RNF01,
RNF11). Ele precisa ser testável com `pytest` puro, sem subir servidor nem banco. Se ele depender de
`Session` do SQLAlchemy ou de `Request` do FastAPI, os testes de cálculo — que são os mais
importantes do projeto — ficam lentos e frágeis.

### 6.2 Tecnologias, com justificativa e alternativa

| Tecnologia | Por que | Problema que resolve | Necessária no MVP? | Alternativas consideradas |
|---|---|---|---|---|
| **Python 3.12+** | Pedido seu. Ecossistema maduro para o domínio. | — | Sim | — |
| **FastAPI** | Validação de entrada acoplada ao tipo, OpenAPI automático, async quando precisar. | Entrada não validada é a origem de metade dos bugs e das vulnerabilidades. | Sim (sob H02) | **Django** — traria admin, auth e ORM prontos, o que aceleraria muito; perde-se controle do domínio e o admin vira uma porta de fuga das regras de negócio. **Flask** — mínimo demais, você reescreve validação. **Se H02 cair para "app local"**, a resposta muda para CLI/Textual + SQLite e o FastAPI sai. |
| **Pydantic v2** | Vem com FastAPI; valida e serializa nas bordas; `Decimal` nativo. | Garante que CPF, valores e datas nunca entram malformados. | Sim | `dataclasses` + validação manual — mais código, menos garantia. |
| **SQLAlchemy 2.0** | ORM maduro, tipado, com controle explícito de transação e SQL parametrizado por padrão. | Transação atômica na emissão; proteção contra SQL injection. | Sim | SQL puro (`psycopg`) — mais controle, muito mais código repetitivo e risco de string interpolada. |
| **PostgreSQL** | `NUMERIC` exato para dinheiro, constraints reais, transações fortes, concorrência para numeração. | Precisão financeira e integridade. | Sim, **sob H02** | **SQLite** — se H02 for "uso local monousuário", SQLite é a escolha certa e mais simples; `NUMERIC` porém é fraco no SQLite (precisa `TEXT`+`Decimal` na aplicação). **MySQL** — sem vantagem aqui. |
| **Alembic** | Migrations versionadas e revisáveis. | Evolução de schema com dados reais em produção. | Sim | Recriar banco — inaceitável com dados fiscais. |
| **`decimal.Decimal`** | Aritmética decimal exata. | `float` erra centavos. Não negociável. | Sim | Inteiros em centavos — válido e às vezes superior; `Decimal` com contexto fixo é mais legível para tabela progressiva. Decisão a revisar na Fase 4. |
| **WeasyPrint** (HTML+CSS -> PDF) | O layout do recibo é um documento textual tabular; escrever em HTML/CSS é muito mais rápido de iterar do que posicionar coordenadas. | Geração e manutenção do layout (RF23, RF26, RF29). | Sim | **ReportLab** — controle absoluto de posicionamento, ideal se houver um formulário pré-impresso a preencher milimetricamente; mais trabalhoso. **wkhtmltopdf** — depreciado. **Escolha final depende da resposta sobre o modelo atual do recibo (H03).** |
| **Jinja2 + HTMX** (UI do MVP) | Renderiza o template do PDF **e** a interface, num único stack. | Evita manter um front-end SPA separado para um sistema interno de formulários. | Sim (sob H02) | **React/Vue SPA** — melhor UX em telas ricas, mas dobra o projeto (build, auth no cliente, CORS, deploy). Não se justifica para CRUD interno. Rever se surgir requisito de UI rica. |
| **Argon2id** (`argon2-cffi`) | Hash de senha resistente a GPU. | RNF03. | Sim | `bcrypt` — aceitável; Argon2id é a recomendação atual. |
| **pytest + Hypothesis** | Testes tabulares para cálculo; property-based para invariantes (RN03). | O ativo mais crítico do projeto. | Sim | `unittest` — mais verboso, sem fixtures ricas. |
| **Docker + docker compose** | Ambiente reproduzível; Postgres sem instalar na máquina. | RNF13. | Sim | Instalação nativa — funciona, mas quebra a reprodutibilidade. |
| **ruff + mypy** | Lint e tipos no CI. | RNF10. | Sim | — |
| **structlog** | Logs JSON com contexto. | RNF12, auditoria. | Sim | `logging` puro + formatter — viável, mais boilerplate. |
| ~~Redis~~ | — | — | **NÃO** | Não há cache com problema real nem fila necessária. Entra só se RF21 (lote) ou RF28 (e-mail) exigirem processamento assíncrono. |
| ~~Celery / RQ~~ | — | — | **NÃO** | PDF em < 3 s síncrono atende H10. Adicionar worker agora é infraestrutura sem demanda. Reavaliar na Fase de lote. |
| ~~Elasticsearch, GraphQL, Kafka~~ | — | — | **NÃO** | Nenhum requisito os justifica. |

### 6.3 Decisão que quero que você questione

Se a resposta à pergunta 6 for **"uso local, uma pessoa, sem servidor"**, então FastAPI + PostgreSQL
+ Docker é **excesso**, e a arquitetura correta seria: aplicação Python local (CLI ou desktop) +
SQLite + mesmo motor de cálculo + mesmo gerador de PDF. **O motor de cálculo, o modelo de domínio, as
regras de negócio, o pipeline de geração e a estratégia de testes deste documento valem nos dois
cenários** — muda a casca (transporte e persistência), não o miolo. Por isso o roadmap coloca o
domínio antes da API.

---

## 7. Estrutura do projeto

```text
rpa-with-python/
├── app/
│   ├── main.py                     # criação do app FastAPI, middlewares, routers
│   ├── core/
│   │   ├── config.py               # settings via env (pydantic-settings)
│   │   ├── security.py             # hash de senha, tokens, dependências de auth
│   │   ├── logging.py              # structlog
│   │   ├── money.py                # Decimal, contexto, arredondamento centralizado
│   │   └── exceptions.py           # exceções de domínio -> HTTP
│   ├── domain/                     # PURO. sem SQLAlchemy, sem FastAPI, sem I/O
│   │   ├── value_objects/          # CPF, CNPJ, Money, Competencia
│   │   ├── receipt/
│   │   │   ├── status.py           # máquina de estados e transições válidas
│   │   │   └── rules.py            # invariantes (RN03, RN05)
│   │   └── calculation/
│   │       ├── engine.py           # orquestra a pipeline de deduções
│   │       ├── rule.py             # contrato de uma regra parametrizada
│   │       └── result.py           # resultado + memória de cálculo
│   ├── models/                     # tabelas SQLAlchemy
│   ├── schemas/                    # DTOs Pydantic de entrada/saída
│   ├── repositories/               # acesso a dados, um por agregado
│   ├── services/                   # casos de uso, transações
│   │   ├── receipt_service.py
│   │   ├── numbering_service.py
│   │   ├── tax_ruleset_service.py
│   │   ├── pdf_service.py
│   │   └── audit_service.py
│   ├── api/
│   │   ├── deps.py                 # sessão, usuário atual, checagem de papel
│   │   └── v1/                     # routers: auth, workers, contractors, receipts, ...
│   ├── web/                        # UI Jinja2 + HTMX (se H02)
│   │   ├── templates/
│   │   └── static/
│   └── documents/
│       ├── templates/rpa/v1/       # template do PDF, versionado por pasta
│       └── renderer.py
├── tests/
│   ├── unit/
│   │   ├── calculation/            # PRIORIDADE MÁXIMA
│   │   ├── domain/
│   │   └── fixtures/casos_fiscais/ # casos homologados pelo contador (YAML/CSV)
│   ├── integration/                # repositórios + banco real
│   ├── api/                        # rotas, auth, permissões
│   ├── documents/                  # geração de PDF
│   └── e2e/                        # fluxo completo do C03
├── migrations/                     # Alembic
├── scripts/                        # seed, backup, restore, import de parâmetros
├── docs/
│   ├── PLANEJAMENTO.md             # este arquivo
│   ├── parametros-fiscais.md       # RV01–RV11: fonte, vigência, homologação
│   ├── adr/                        # decisões de arquitetura (ADR-0001...)
│   ├── modelo-dados.md
│   └── seguranca-lgpd.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── CLAUDE.md                       # regras de trabalho com IA (seção 17)
└── README.md
```

**Regra de dependência (verificável em teste):** `domain/` não importa nada de `models/`, `api/`,
`repositories/` ou de bibliotecas de framework. Um teste de arquitetura vai garantir isso — é a
salvaguarda que impede o motor de cálculo de apodrecer.

---

## 8. Banco de dados

**Escolha:** PostgreSQL (sob H02). Se H02 cair, SQLite com `Decimal` na aplicação.

### 8.1 Tabelas principais

| Tabela | Campos-chave | Observações |
|---|---|---|
| `organizations` | `id`, `name`, `document`, `settings jsonb` | Escopo de tudo. |
| `users` | `id`, `org_id`, `email UNIQUE`, `password_hash`, `role`, `is_active`, `last_login_at` | `role` como enum. |
| `workers` | `id`, `org_id`, `full_name`, `cpf`, `pis_nit`, endereço, `municipality`, `uf`, `dependents_count`, `municipal_registration`, `is_active` | `UNIQUE(org_id, cpf)`. Campos fiscais só existem após RV11. |
| `worker_bank_accounts` | `id`, `worker_id`, `type`, `bank`, `agency_enc`, `account_enc`, `pix_key_enc` | Colunas cifradas na aplicação. |
| `contractors` | `id`, `org_id`, `legal_name`, `document`, `document_type`, endereço, `municipality`, `uf`, `municipal_registration`, `is_active` | `UNIQUE(org_id, document)`. `document_type` é entrada de cálculo (RV08). |
| `tax_rule_sets` | `id`, `org_id`, `tax_type`, `valid_from`, `valid_to`, `source_reference`, `approved_by`, `approved_at`, `is_active` | Sem sobreposição de vigência por `tax_type`. Imutável após uso. |
| `tax_rule_brackets` | `id`, `rule_set_id`, `order`, `min_base`, `max_base`, `rate`, `deduction`, `cap`, `meta jsonb` | Genérico: representa progressiva ou alíquota única. **Sem valores no código.** |
| `number_sequences` | `id`, `org_id`, `series`, `year`, `last_number` | `UNIQUE(org_id, series, year)`. Incremento com lock. |
| `receipts` | `id`, `org_id`, `number`, `series`, `year`, `status`, `worker_id`, `contractor_id`, `competence`, `reference_date`, `gross_amount`, `deductions_total`, `additions_total`, `net_amount`, snapshots, `created_by`, `issued_by`, `issued_at`, `cancelled_by`, `cancelled_at`, `cancel_reason`, `replaces_id`, `paid_at`, `payment_method` | `UNIQUE(org_id, series, year, number)` (parcial: só onde `number IS NOT NULL`). |
| `receipt_services` | `id`, `receipt_id`, `description`, `period_start`, `period_end`, `gross_amount` | Um por recibo no MVP; a tabela já suporta N. |
| `receipt_deductions` | `id`, `receipt_id`, `kind`, `label`, `origin`, `base_amount`, `rate_applied`, `amount`, `rule_set_id`, `calc_note` | **É a memória de cálculo persistida.** |
| `receipt_documents` | `id`, `receipt_id`, `kind` (draft/official), `storage_path`, `sha256`, `size`, `template_version`, `generated_at`, `generated_by` | Nunca sobrescrever: nova geração cria nova linha. |
| `receipt_status_history` | `id`, `receipt_id`, `from_status`, `to_status`, `reason`, `user_id`, `created_at` | |
| `audit_logs` | `id`, `org_id`, `user_id`, `action`, `entity_type`, `entity_id`, `before jsonb`, `after jsonb`, `ip`, `user_agent`, `created_at` | Append-only. Sem UPDATE/DELETE concedido ao usuário da aplicação. |

### 8.2 Constraints e índices

**Constraints (o banco é a última linha de defesa, não a única):**
- `NUMERIC(14,2)` para todo valor monetário; `NUMERIC(7,6)` para alíquotas.
- `CHECK (gross_amount > 0)`, `CHECK (net_amount >= 0)`, `CHECK (amount >= 0)` em deduções.
- `CHECK (net_amount = gross_amount - deductions_total + additions_total)` — a RN03 gravada no banco.
- `CHECK (status IN (...))` ou tipo enum.
- `CHECK ((status = 'EMITIDO' AND number IS NOT NULL) OR (status <> 'EMITIDO'))` — emitido sem número é impossível.
- `EXCLUDE` com `daterange` em `tax_rule_sets` para impedir vigências sobrepostas do mesmo tributo.
- `ON DELETE RESTRICT` em `worker_id` / `contractor_id` de `receipts`.
- Todo `created_at` / `updated_at` em `timestamptz`, sempre UTC.

**Índices:**
- `receipts(org_id, status, competence)` — a listagem padrão;
- `receipts(org_id, worker_id, competence)` — relatório por autônomo (RF35) e acumulador do RV06;
- `receipts(org_id, series, year, number)` UNIQUE;
- `workers(org_id, cpf)` UNIQUE; índice `gin trgm` em `full_name` se a busca por nome for lenta (medir antes);
- `audit_logs(org_id, entity_type, entity_id, created_at DESC)`;
- `tax_rule_sets(org_id, tax_type, valid_from)`.

### 8.3 Decisões explicadas

- **Numeração sem lacunas:** contador de sequência com `SELECT ... FOR UPDATE` (ou `UPDATE ... RETURNING`) dentro da **mesma transação** da emissão. Sequences do Postgres **não servem**, porque não fazem rollback — deixariam buracos. Custo: serialização das emissões concorrentes. Aceitável em H10.
- **Snapshot como colunas, não JSON:** os campos do documento são fixos e consultáveis; JSON dificultaria relatório e índice. `jsonb` fica para `audit_logs` e `settings`, onde o schema é realmente variável.
- **Soft delete via `is_active`, nunca `DELETE`:** documentos fiscais e trilha de auditoria não se apagam (RN12).
- **Migrations:** toda alteração via Alembic, uma migration por mudança lógica, revisada manualmente após `autogenerate` (ele erra em enums, constraints e índices parciais). Migration com transformação de dados precisa de teste de ida e volta antes de rodar em produção.

---

## 9. API — proposta inicial

Prefixo `/api/v1`. Autenticação em tudo, exceto `/auth/login` e `/health`.

```text
# Autenticação
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me

# Autônomos
GET    /api/v1/workers                 ?search=&active=&page=&size=
POST   /api/v1/workers
GET    /api/v1/workers/{id}
PATCH  /api/v1/workers/{id}
POST   /api/v1/workers/{id}/deactivate
GET    /api/v1/workers/{id}/bank-account        (papel restrito)
PUT    /api/v1/workers/{id}/bank-account        (papel restrito)

# Contratantes
GET    /api/v1/contractors
POST   /api/v1/contractors
GET    /api/v1/contractors/{id}
PATCH  /api/v1/contractors/{id}
POST   /api/v1/contractors/{id}/deactivate

# Recibos
GET    /api/v1/receipts                ?status=&competence=&worker_id=&contractor_id=&from=&to=&number=
POST   /api/v1/receipts                          -> cria RASCUNHO
GET    /api/v1/receipts/{id}                     -> inclui memória de cálculo e histórico
PATCH  /api/v1/receipts/{id}                     -> só em RASCUNHO (409 caso contrário)
POST   /api/v1/receipts/{id}/recalculate
POST   /api/v1/receipts/{id}/submit-for-review   -> RASCUNHO  -> EM_REVISAO
POST   /api/v1/receipts/{id}/return-to-draft     -> EM_REVISAO -> RASCUNHO   (motivo obrigatório)
POST   /api/v1/receipts/{id}/issue               -> EM_REVISAO -> EMITIDO    (numera + gera PDF)
POST   /api/v1/receipts/{id}/cancel              -> EMITIDO -> CANCELADO     (motivo obrigatório)
POST   /api/v1/receipts/{id}/mark-paid
POST   /api/v1/receipts/{id}/replace             -> cria substitutivo
DELETE /api/v1/receipts/{id}                     -> só descarta RASCUNHO

# Documento
GET    /api/v1/receipts/{id}/pdf                 -> baixa o PDF vigente
POST   /api/v1/receipts/{id}/pdf                 -> regera (rascunho) / reemite cópia
GET    /api/v1/receipts/{id}/documents           -> histórico de PDFs gerados

# Cálculo
POST   /api/v1/calculations/simulate             -> simula sem persistir (RF43)

# Parâmetros fiscais (admin)
GET    /api/v1/tax-rule-sets            ?tax_type=&on_date=
POST   /api/v1/tax-rule-sets
GET    /api/v1/tax-rule-sets/{id}
POST   /api/v1/tax-rule-sets/{id}/approve        -> homologação (RF42)

# Exportação e relatórios
GET    /api/v1/reports/receipts.csv
GET    /api/v1/reports/by-worker         ?competence=

# Usuários (admin) / Auditoria / Saúde
GET|POST /api/v1/users ; POST /api/v1/users/{id}/deactivate
GET    /api/v1/audit-logs               ?entity_type=&entity_id=&user_id=&from=&to=
GET    /health   ;  GET /health/ready
```

**Convenções:** transições de estado são **verbos em sub-recurso** (`/issue`, `/cancel`), não
`PATCH status` — a transição tem pré-condições e efeitos colaterais (numerar, gerar PDF, auditar),
e o verbo explícito torna isso óbvio e autorizável separadamente. `PATCH` para edição parcial.
Erros em formato único (`{code, message, details}`). `409 Conflict` para transição inválida.
`422` para validação. Paginação por `page`/`size` com envelope `{items, total, page, size}`.
Idempotência: `POST /issue` aceita `Idempotency-Key` para não emitir dois recibos num duplo clique.

---

## 10. Segurança

| Frente | Medida |
|---|---|
| **Autenticação** | Argon2id para senhas; política mínima de senha; bloqueio temporário após N tentativas; sessão por cookie `HttpOnly; Secure; SameSite=Lax` (para a UI web) ou JWT curto + refresh (para API pura). 2FA para admin fica como RF45. |
| **Autorização** | Verificada **no servidor**, em toda rota, por dependência do FastAPI. Matriz explícita: só `revisor`/`admin` emitem ou cancelam; só `admin` gerencia usuários e homologa parâmetros; `consulta` é somente leitura; dados bancários exigem papel específico. Toda query filtra por `org_id` do usuário — nunca confiar no `org_id` que vem do cliente. |
| **Validação de entrada** | Pydantic em todas as bordas; CPF/CNPJ com dígito verificador; valores como `Decimal` com limites; tamanho máximo de campos de texto; whitelist de valores em enums. |
| **SQL Injection** | SQLAlchemy com parâmetros ligados. **Proibido** montar SQL por f-string/concatenação; regra checável no CI (`ruff` + revisão). |
| **XSS** | Jinja2 com autoescape ligado; nada de `\|safe` em conteúdo vindo do usuário; CSP restritiva; o mesmo cuidado no template do PDF (descrição de serviço é texto livre do usuário). |
| **CSRF** | Aplicável se a UI usar cookie de sessão: token anti-CSRF por formulário + `SameSite`. Não aplicável a API com `Authorization: Bearer`. |
| **Rate limiting** | No login (por IP e por conta) e nas rotas de geração de PDF. |
| **Secrets** | Só por variável de ambiente / gerenciador de segredos. `.env` no `.gitignore`, `.env.example` sem valores. Chave de criptografia dos dados bancários separada da senha do banco, com procedimento de rotação documentado. `git-secrets`/scan no CI. |
| **Criptografia** | TLS em trânsito. Dados bancários/PIX cifrados em repouso na aplicação (AES-GCM com chave gerenciada). Banco em disco cifrado quando o ambiente permitir. |
| **Logs** | JSON estruturado com `request_id` e `user_id`. **Nunca** logar senha, token, CPF completo, chave PIX ou conta bancária — CPF mascarado (`***.***.789-**`). Erros com stack trace só no servidor, nunca no corpo da resposta. |
| **Auditoria** | `audit_logs` append-only: o usuário de aplicação recebe apenas `INSERT`/`SELECT`. Registra emissão, cancelamento, alteração de cadastro, mudança e homologação de parâmetros, login e falha de login, e acesso a dados bancários. |
| **LGPD** | Base legal documentada (execução de contrato + obrigação legal); minimização (não coletar o que o cálculo e o documento não exigem); retenção definida pelo prazo legal (RV10) com rotina de expurgo/anonimização; procedimento para requisição de titular; controle de quem acessa dado sensível via auditoria; registro das operações de tratamento em `docs/seguranca-lgpd.md`. |
| **Backup** | `pg_dump` diário + storage de PDFs; retenção definida; cópia fora do servidor de produção; **restauração testada em ambiente separado, com data do último teste registrada**. |
| **Dependências** | Versões travadas em lockfile; `pip-audit` no CI; atualização revisada, não automática. |
| **Cabeçalhos** | HSTS, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, CSP. |

**Ameaças específicas deste domínio, mapeadas:**
1. *Emissão duplicada por duplo clique* -> idempotência + transição de estado transacional.
2. *Recibo alterado após emissão* -> imutabilidade em serviço + `CHECK` + auditoria.
3. *Lacuna na numeração* -> contador transacional (8.3).
4. *Cálculo com tabela errada/não homologada* -> RF42 bloqueia emissão; snapshot registra o que foi usado.
5. *Vazamento de PII em massa* -> exportação (RF34) restrita por papel e registrada em auditoria.
6. *PDF acessível sem autenticação* -> PDF nunca servido por URL pública adivinhável; download passa por autorização; `storage_path` com nome não sequencial.

---

## 11. Geração do RPA — o pipeline

```
   Entrada (operador)
        |
   [1] VALIDAÇÃO SINTÁTICA        Pydantic: tipos, formatos, CPF/CNPJ, valores > 0
        |
   [2] VALIDAÇÃO DE NEGÓCIO       autônomo/contratante ativos, cadastro completo para o cálculo,
        |                          competência coerente, status permite a operação
   [3] RESOLUÇÃO DE VIGÊNCIA      escolhe o TaxRuleSet de cada tributo pela data de referência (RV07)
        |                          -> se não houver vigência homologada: ERRO, não emite (RF42)
   [4] CÁLCULO                    motor puro: bruto -> pipeline ordenada de regras -> deduções
        |                          Decimal, arredondamento único (RV05), produz memória de cálculo
   [5] CONFERÊNCIA (humano)       operador vê bruto, cada desconto com base+alíquota, e o líquido
        |                          pode corrigir e voltar a [1]  (C03 passos 6-7)
   [6] REVISÃO (humano)           revisor confirma  (C03 passo 8)
        |
   [7] PERSISTÊNCIA               UMA transação: numerar + status EMITIDO + gravar deduções
        |                          + snapshots + histórico + auditoria
   [8] RENDERIZAÇÃO               template versionado + dados do snapshot -> HTML
        |
   [9] PDF                        HTML -> PDF, calcula sha256, grava ReceiptDocument
        |
  [10] ENTREGA                    download (RF24); e-mail depois (RF28)
```

**Detalhamento das etapas críticas:**

- **[3] Resolução de vigência.** É aqui que o sistema se recusa a inventar. Sem `TaxRuleSet` homologado cobrindo a data de referência, a emissão falha com mensagem clara. Rascunho ainda pode ser simulado, mas sai com marca d'água.
- **[4] Cálculo.** Função pura: `calcular(entrada, conjunto_de_regras) -> ResultadoCalculo`. Sem banco, sem relógio (`data` é parâmetro, nunca `date.today()` interno — senão o teste não é determinístico), sem aleatoriedade. Cada regra é declarativa: base de incidência, faixas, teto, arredondamento. A **ordem** vem da configuração (RV04), não do código.
- **[7] Persistência.** Ordem correta: **primeiro numerar dentro da transação, depois marcar emitido**. Se o PDF falhar em [9], o recibo **continua emitido** e o PDF pode ser regerado — o documento é derivado, não a fonte da verdade. O inverso (gerar PDF e depois emitir) criaria PDFs órfãos com número consumido.
- **[8]/[9] Renderização.** O template é versionado por pasta (`v1`, `v2`) e o `ReceiptDocument` guarda qual versão usou, para reimpressão fiel. O `sha256` permite provar que o PDF não foi adulterado e sustenta o RF27.

---

## 12. Estratégia de testes

**Prioridade absoluta: cálculo.** Se o orçamento de testes fosse de uma coisa só, seria essa.

| Camada | O que cobre | Ferramenta | Meta |
|---|---|---|---|
| **Unitário — cálculo** | Cada regra isolada; faixas; limites exatos; teto; arredondamento; valores de fronteira; entrada zero/negativa. Casos vindos da homologação em arquivo YAML (`entrada -> saída esperada`), versionados e assinados pelo contador. | pytest, tabular (`parametrize`) | **Cobertura ~100% do módulo `domain/calculation`.** |
| **Property-based** | Invariantes que valem sempre: `líquido = bruto - descontos + acréscimos`; nenhum desconto negativo; nenhum desconto maior que a base; monotonicidade (bruto maior nunca gera líquido menor... **se** o contador confirmar que vale); determinismo (mesma entrada, mesmo resultado, 1000 vezes). | Hypothesis | Invariantes RN03 e determinismo cobertos. |
| **Unitário — domínio** | Máquina de estados: toda transição válida permitida, **toda inválida rejeitada** (matriz completa); regras de imutabilidade. | pytest | 100% das transições. |
| **Integração — banco** | Repositórios; constraints realmente ativas (tentar violar e esperar erro); **numeração concorrente** (N emissões simultâneas -> N números únicos sem lacuna); migrations aplicam e revertem. | pytest + Postgres em container (testcontainers ou compose) | — |
| **API** | Contratos de entrada/saída; códigos de erro; **matriz de autorização** (cada papel x cada rota, esperando 403 onde deve); paginação e filtros. | pytest + httpx `AsyncClient` | Toda rota com ao menos um teste de permissão negada. |
| **Documento/PDF** | PDF é gerado; contém os campos obrigatórios (extração de texto); valores batem com o recibo; rascunho tem marca d'água e emitido não tem; `sha256` estável para a mesma entrada. | pytest + `pypdf` | — |
| **Segurança** | Sem SQL injection nos filtros; XSS em descrição de serviço escapado no HTML e no PDF; rota autenticada retorna 401 sem credencial; rate limit no login; nenhum segredo em log. | pytest + `pip-audit` | — |
| **E2E** | O fluxo C03 inteiro, do cadastro ao PDF baixado, incluindo o caminho de devolução para rascunho e o de cancelamento + substituição. | pytest | Ao menos 3 cenários. |
| **Arquitetura** | `domain/` não importa framework nem ORM. | teste de import | 1 teste, sempre verde. |

**Regras de teste:**
- Nada de `date.today()` dentro do domínio — data sempre injetada, para o teste ser reproduzível em qualquer dia.
- Fixtures de cálculo vivem em arquivo de dados, não hard-coded no teste — assim o contador consegue revisar sem ler Python.
- CI roda: `ruff` + `mypy` + testes + `pip-audit`. Build vermelho não faz merge.
- Bug de cálculo **sempre** vira teste de regressão antes da correção.

---

## 13. Roadmap

| Fase | Objetivo | Tarefas | Dependências | Critério de conclusão |
|---|---|---|---|---|
| **F0 — Discovery** | Fechar escopo e requisitos. | Responder às perguntas 5–10; confirmar/corrigir H01–H12; aprovar este documento. | — | Documento aprovado; hipóteses viraram requisitos ou foram descartadas. |
| **F0.5 — Homologação fiscal** | Eliminar RV01–RV11. | Levantar fontes oficiais; montar `docs/parametros-fiscais.md`; obter aceite do contador; produzir **casos de teste homologados**. | F0 | Todo RV respondido com fonte + aceite; ≥ 20 casos de teste aprovados. **Roda em paralelo a F1–F3.** |
| **F1 — Fundação** | Projeto executável e disciplinado. | Repo, `pyproject`, ruff/mypy, pytest, Docker + compose, config por env, logging estruturado, CI, `CLAUDE.md`, ADR-0001. | F0 | `docker compose up` sobe; CI verde num teste trivial. |
| **F2 — Banco e modelo** | Schema fiel à seção 8. | Models SQLAlchemy, Alembic inicial, constraints e índices, repositórios base, seed de dev, testes de integração. | F1 | Migrations sobem e revertem; constraints testadas. |
| **F3 — Domínio** | Núcleo puro. | Value objects (CPF/CNPJ/Money/Competência), máquina de estados, invariantes, contrato de regra de cálculo, teste de arquitetura. | F1 | Domínio 100% testado, zero import de framework. |
| **F4 — Motor de cálculo** | Cálculo correto e auditável. | Engine parametrizado, resolução de vigência, memória de cálculo, arredondamento centralizado, carga dos parâmetros homologados, bateria de testes tabulares + property-based. | F3 + **F0.5** | Todos os casos homologados passam; cobertura ~100% no módulo. |
| **F5 — Casos de uso e API** | Fluxo C03 servido por HTTP. | Serviços (criar, recalcular, submeter, emitir, cancelar), numeração transacional, auth + RBAC, routers, auditoria, tratamento de erros. | F2, F4 | Fluxo completo via API; matriz de autorização testada; numeração concorrente validada. |
| **F6 — Documento** | PDF confiável. | Template versionado, renderer, marca d'água de rascunho, storage + sha256, download, reimpressão fiel. | F5 | PDF com todos os campos do RV10; reimpressão idêntica; testes de PDF verdes. |
| **F7 — Interface** | Operador consegue usar. | Telas de cadastro, criação de RPA com cálculo ao vivo, tela de conferência com memória, listagem com filtros, revisão/emissão, download. | F5, F6 | Fluxo C03 executável por um operador sem tocar em `curl`. |
| **F8 — Segurança e LGPD** | Endurecimento. | Rate limit, cabeçalhos, CSP, criptografia dos dados bancários, mascaramento em log, retenção, `docs/seguranca-lgpd.md`, revisão de dependências. | F5–F7 | Checklist da seção 10 completo; sem segredo no repositório. |
| **F9 — Qualidade e homologação** | Confiança para uso real. | E2E, testes de segurança, revisão do cálculo pelo contador **no sistema rodando**, comparação contra recibos reais já emitidos à mão. | F4–F8 | ≥ 10 recibos reais reproduzidos com valores idênticos aos conferidos pelo contador. |
| **F10 — Deploy** | Ambiente de produção. | Container de produção, TLS, backup automatizado **com restauração testada**, healthcheck, logs persistidos, runbook. | F9 | Restauração de backup executada com sucesso; runbook escrito. |
| **F11 — Operação e evolução** | Uso real e backlog seguinte. | Piloto com um subconjunto de recibos, coleta de feedback, então: e-mail (RF28), exportações (RF34/35), lote (RF21), pagamento (RF19). | F10 | Primeiro mês em produção sem divergência de cálculo. |

**Caminho crítico:** F0 -> F0.5 -> F4. A homologação fiscal é a dependência mais lenta e a mais
externa. Ela deve começar **imediatamente**, em paralelo com F1–F3.

---

## 14. MVP

### Entra
- Login com papéis admin/revisor/operador (RF37–RF39);
- Cadastro de autônomo e contratante com validação de CPF/CNPJ (RF01, RF03–RF06);
- Registro do serviço e criação do RPA (RF08, RF09);
- Cálculo automático parametrizado + memória de cálculo (RF10, RF11, RF12);
- Fluxo rascunho -> revisão -> emitido, com numeração e imutabilidade (RF13–RF16);
- Cancelamento com motivo (RF17);
- PDF com marca d'água em rascunho e definitivo na emissão + download (RF23–RF25);
- Listagem com filtros e visualização detalhada (RF31, RF32, RF33);
- Auditoria (RF40);
- Parâmetros versionados por vigência com homologação obrigatória (RF41, RF42);
- Backup com restauração testada.

### NÃO entra (e por quê)
| Fora do MVP | Motivo |
|---|---|
| Envio por e-mail/WhatsApp | Download resolve; integração adiciona fila, credenciais e falha externa. |
| Emissão em lote | Sem volume que justifique (H10). |
| Múltiplos itens por recibo | Nenhum requisito atual pede. Modelo já preparado. |
| Substitutivo automático | Cancelar + criar novo manualmente resolve no início. |
| Controle de pagamento | O RPA é o documento; baixa financeira é outro domínio. |
| Exportação contábil / relatórios | Sem definição de formato de destino. |
| Dashboard, gráficos | Zero valor no dia 1. |
| Assinatura digital ICP-Brasil | Épico próprio, alto custo, sem requisito confirmado. |
| Multi-tenant ativo | `org_id` existe; ativação sem cliente real é especulação. |
| Portal do autônomo | Dobra a superfície de segurança. |
| Import CSV, 2FA, personalização de layout | Melhorias, não fundação. |
| **Folha CLT** | Fora do domínio de RPA (H01). |

---

## 15. Backlog

Prioridade: **P0** bloqueia o MVP · **P1** necessário para produção · **P2** pós-MVP.
Formato: objetivo / descrição / dependências / aceite / prioridade.

### Fase 0 — Discovery e homologação

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-001 | Fechar escopo | Responder perguntas 5–10; confirmar ou corrigir H01–H12. | — | Cada hipótese vira requisito ou é descartada por escrito. | P0 |
| TASK-002 | Confirmar exclusão de folha CLT | Decidir H01 explicitamente. | 001 | Decisão registrada; se CLT entrar, replanejar. | P0 |
| TASK-003 | Levantar fontes fiscais | Reunir normas/tabelas oficiais para RV01–RV11. | 001 | `docs/parametros-fiscais.md` com fonte para cada RV. | P0 |
| TASK-004 | Homologar regras com contador | Obter aceite formal de alíquotas, bases, ordem e arredondamento. | 003 | Documento assinado/aprovado; RV01–RV11 sem lacuna. | P0 |
| TASK-005 | Casos de teste homologados | ≥ 20 casos `entrada -> saída` conferidos pelo contador, incluindo fronteiras e teto. | 004 | Arquivo YAML em `tests/unit/fixtures/casos_fiscais/`. | P0 |
| TASK-006 | Obter modelo atual do recibo | Coletar o layout usado hoje (Word/planilha/papel). | 001 | Modelo anexado; campos obrigatórios listados (RV10). | P0 |
| TASK-007 | Definir política de retenção | Prazo de guarda de recibos e PDFs; regra de expurgo/anonimização. | 004 | Registrado em `docs/seguranca-lgpd.md`. | P1 |

### Fase 1 — Fundação

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-010 | Esqueleto do projeto | `pyproject.toml`, estrutura de pastas da seção 7, `.gitignore`, `.env.example`. | 001 | `pip install -e .` funciona. | P0 |
| TASK-011 | Qualidade estática | ruff + mypy configurados em modo estrito. | 010 | Comandos passam limpos. | P0 |
| TASK-012 | Base de testes | pytest, cobertura, `conftest`, um teste trivial. | 010 | `pytest` verde. | P0 |
| TASK-013 | Docker | `Dockerfile` (não-root, multi-stage) e `docker-compose.yml` com app + Postgres. | 010 | `docker compose up` sobe app e banco. | P0 |
| TASK-014 | Configuração por ambiente | `pydantic-settings`; falha rápida se faltar variável obrigatória. | 010 | App não sobe sem config válida; nenhum segredo no repo. | P0 |
| TASK-015 | Logging estruturado | structlog JSON com `request_id` e mascaramento de PII. | 010 | Log de exemplo sem CPF completo. | P1 |
| TASK-016 | CI | Pipeline: lint, tipos, testes, `pip-audit`. | 011,012 | CI verde; vermelho bloqueia merge. | P0 |
| TASK-017 | CLAUDE.md | Regras da seção 17 no repositório. | 010 | Arquivo presente e seguido. | P0 |
| TASK-018 | ADR-0001 | Registrar escolha de arquitetura e alternativas. | 001 | ADR em `docs/adr/`. | P1 |

### Fase 2 — Banco

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-020 | Alembic | Configurar migrations. | 013 | `alembic upgrade head` funciona. | P0 |
| TASK-021 | Organization + User | Models e migration. | 020 | Tabelas criadas; UNIQUE de e-mail testado. | P0 |
| TASK-022 | Worker | Model, constraints, `UNIQUE(org_id,cpf)`. | 021 | Duplicata rejeitada pelo banco. | P0 |
| TASK-023 | Contractor | Idem para contratante. | 021 | Idem. | P0 |
| TASK-024 | TaxRuleSet + Brackets | Estrutura genérica de parâmetros; `EXCLUDE` de vigências sobrepostas. | 021 | Vigência sobreposta rejeitada. | P0 |
| TASK-025 | Receipt + Service + Deduction | Tabelas centrais com todos os `CHECK` da seção 8.2. | 022,023 | `CHECK` da RN03 rejeita valor incoerente. | P0 |
| TASK-026 | NumberSequence | Tabela + `UNIQUE(org,série,ano)`. | 021 | Constraint testada. | P0 |
| TASK-027 | Documents, StatusHistory, AuditLog | Tabelas de apoio; auditoria append-only. | 025 | UPDATE em `audit_logs` negado ao usuário da app. | P0 |
| TASK-028 | Índices | Índices da seção 8.2. | 025 | `EXPLAIN` usa índice na listagem padrão. | P1 |
| TASK-029 | Repositórios base | CRUD + paginação + filtro por `org_id`. | 022–027 | Testes de integração verdes. | P0 |
| TASK-030 | Seed de desenvolvimento | Script com dados fictícios (nunca dados reais). | 029 | `scripts/seed.py` popula ambiente limpo. | P1 |

### Fase 3 — Domínio

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-040 | Value objects | CPF, CNPJ (com DV), Money (Decimal), Competência. | 010 | 100% de cobertura; casos inválidos rejeitados. | P0 |
| TASK-041 | Módulo de arredondamento | Ponto único de arredondamento, configurado por RV05. | 040,004 | Comportamento igual ao homologado. | P0 |
| TASK-042 | Máquina de estados | Transições válidas e proibidas do C03. | 010 | Matriz completa testada; transição inválida levanta erro. | P0 |
| TASK-043 | Invariantes do recibo | RN03 e afins como funções puras. | 040 | Property-based verde. | P0 |
| TASK-044 | Teste de arquitetura | `domain/` sem import de framework/ORM. | 010 | Teste falha se alguém violar. | P1 |

### Fase 4 — Cálculo (crítica)

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-050 | Contrato de regra | Interface declarativa: base, faixas, teto, arredondamento, ordem. **Sem número no código.** | 043 | Regra construída só a partir de parâmetros. | P0 |
| TASK-051 | Engine | Pipeline ordenada; produz deduções + memória de cálculo. | 050 | Resultado inclui base, alíquota e valor por dedução. | P0 |
| TASK-052 | Resolução de vigência | Escolhe o `TaxRuleSet` pela data de referência (RV07). | 024,051 | Sem vigência homologada -> erro explícito. | P0 |
| TASK-053 | Carga dos parâmetros | Importar `parametros-fiscais.md` para as tabelas, com fonte e homologação. | 004,024 | Import reproduzível; valores conferem com o documento. | P0 |
| TASK-054 | Bateria de testes fiscais | Executar todos os casos de TASK-005. | 005,051 | 100% passam; cobertura ~100% do módulo. | P0 |
| TASK-055 | Property-based | Invariantes e determinismo. | 051 | Hypothesis sem contraexemplo. | P0 |
| TASK-056 | Bloqueio sem homologação | Emissão barrada se a vigência não estiver aprovada (RF42). | 052 | Teste cobre o bloqueio. | P0 |
| TASK-057 | Acumulador mensal | **Só se RV06 exigir.** Somatório por autônomo/competência para tratar teto. | 004,051 | Conforme regra homologada. | P0* |

### Fase 5 — Casos de uso, API e segurança de acesso

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-060 | Auth | Login, hash Argon2id, sessão/token, logout. | 021 | Credencial inválida não vaza qual campo errou. | P0 |
| TASK-061 | RBAC | Matriz papel x rota como dependência do FastAPI. | 060 | Cada rota tem teste de 403 para papel indevido. | P0 |
| TASK-062 | Auditoria transversal | Serviço de auditoria chamado em toda operação relevante. | 027,060 | Emissão e cancelamento sempre auditados. | P0 |
| TASK-063 | CRUD de autônomo | Serviço + rotas + validação. | 029,061 | Testes de API verdes. | P0 |
| TASK-064 | CRUD de contratante | Idem. | 029,061 | Idem. | P0 |
| TASK-065 | Criar RPA rascunho | Cria com serviço e valor bruto; dispara cálculo. | 051,063,064 | Rascunho traz memória de cálculo. | P0 |
| TASK-066 | Recalcular | Recalcula ao alterar dados em rascunho. | 065 | Alteração de bruto muda deduções. | P0 |
| TASK-067 | Numeração transacional | Contador com lock, dentro da transação da emissão. | 026 | Teste de concorrência: N emissões, N números, zero lacuna. | P0 |
| TASK-068 | Submeter para revisão | Transição rascunho -> em revisão. | 042,065 | Transição inválida -> 409. | P0 |
| TASK-069 | Emitir | Transação única: numera, congela snapshots, grava deduções, muda status, audita. | 067,068 | Recibo emitido não pode ser editado (409). | P0 |
| TASK-070 | Devolver para rascunho | Com motivo obrigatório. | 068 | Motivo obrigatório validado. | P1 |
| TASK-071 | Cancelar | Com motivo; preserva dados e PDF. | 069 | Cancelado continua consultável. | P0 |
| TASK-072 | Idempotência na emissão | `Idempotency-Key` em `/issue`. | 069 | Requisição repetida não gera segundo recibo. | P1 |
| TASK-073 | Listagem e filtros | Paginação + filtros da RF31. | 029,061 | Filtros combinados testados. | P0 |
| TASK-074 | Detalhe do recibo | Inclui deduções e histórico de status. | 069 | Memória de cálculo visível. | P0 |
| TASK-075 | Simulador | Cálculo sem persistir. | 051,061 | Não cria registro. | P2 |
| TASK-076 | Erros padronizados | Formato único; sem stack trace na resposta. | 060 | Teste de formato de erro. | P1 |

### Fase 6 — Documento

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-080 | Escolher a biblioteca de PDF | Decidir WeasyPrint vs. ReportLab com base em TASK-006. | 006 | ADR registrando a decisão. | P0 |
| TASK-081 | Template v1 | Layout com todos os campos do RV10 e área de assinatura. | 080,006 | Contador aprova o layout. | P0 |
| TASK-082 | Renderer | Snapshot -> HTML -> PDF; escape rigoroso do texto do usuário. | 081 | XSS na descrição não quebra o PDF. | P0 |
| TASK-083 | Marca d'água de rascunho | Rascunho sai marcado; emitido, não. | 082 | Teste distingue os dois. | P0 |
| TASK-084 | Storage + hash | Grava arquivo, `sha256`, `ReceiptDocument`. | 082,027 | Hash estável para a mesma entrada. | P0 |
| TASK-085 | Download autorizado | `GET /pdf` com verificação de permissão e auditoria. | 084,061 | Sem permissão -> 403; caminho não adivinhável. | P0 |
| TASK-086 | Reimpressão fiel | Rebaixa o documento original, não regera. | 084 | Bytes idênticos aos da emissão. | P0 |
| TASK-087 | Identidade visual | Logotipo e dados da empresa configuráveis. | 081 | Configuração reflete no PDF. | P2 |
| TASK-088 | Código de verificação | Hash/código impresso para conferência. | 084 | RF27 atendido. | P2 |

### Fase 7 — Interface

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-090 | Layout base + login | Telas base, sessão, mensagens de erro. | 060 | Login funcional pelo navegador. | P0 |
| TASK-091 | Telas de cadastro | Autônomo e contratante, com validação no cliente e no servidor. | 063,064 | CRUD completo pela UI. | P0 |
| TASK-092 | Tela de criação do RPA | Formulário com cálculo ao vivo. | 065,066 | Valor bruto alterado atualiza os descontos. | P0 |
| TASK-093 | Tela de conferência | Memória de cálculo legível para o operador (C03 passo 6). | 092 | Cada desconto mostra base e parâmetro. | P0 |
| TASK-094 | Revisão e emissão | Ações de submeter, devolver, emitir, cancelar conforme papel. | 068–071 | Operador não vê o botão de emitir. | P0 |
| TASK-095 | Listagem e busca | Filtros da RF31 na UI. | 073 | Busca por número e por competência. | P0 |
| TASK-096 | Download do PDF | Botão de download e histórico de documentos. | 085 | C03 passo 10 completo. | P0 |

### Fase 8 — Segurança, LGPD e operação

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-100 | Cabeçalhos + CSP | HSTS, CSP, anti-clickjacking. | 090 | Verificado em resposta real. | P1 |
| TASK-101 | Rate limiting | Login e geração de PDF. | 060 | Excesso -> 429. | P1 |
| TASK-102 | Criptografia bancária | Cifrar campos de `worker_bank_accounts`; documentar rotação de chave. | 022 | Dado ilegível direto no banco. | P1 |
| TASK-103 | Mascaramento em log | Nenhum CPF completo, token ou chave PIX em log. | 015 | Teste de log verde. | P1 |
| TASK-104 | CSRF | Se a UI usar cookie de sessão. | 090 | Requisição sem token rejeitada. | P1 |
| TASK-105 | Backup + restauração | Rotina de dump + PDFs; **restauração testada e documentada**. | 013 | Restore executado com sucesso em ambiente limpo. | P1 |
| TASK-106 | Retenção e expurgo | Implementar TASK-007. | 007 | Rotina documentada. | P2 |
| TASK-107 | Doc de LGPD | `docs/seguranca-lgpd.md` com bases legais e fluxo de titular. | 007 | Documento revisado. | P1 |
| TASK-108 | Healthcheck e métricas | `/health`, `/health/ready`, métricas básicas. | 010 | Endpoint responde. | P1 |
| TASK-109 | Runbook | Como subir, restaurar, girar chave, investigar erro. | 105 | Alguém que não é você consegue seguir. | P1 |

### Fase 9 — Homologação e produção

| ID | Objetivo | Descrição | Dep. | Critério de aceite | P |
|---|---|---|---|---|---|
| TASK-110 | E2E | Fluxo C03 completo + devolução + cancelamento. | Fases 5–7 | 3 cenários verdes. | P0 |
| TASK-111 | Testes de segurança | SQLi, XSS, autorização, exposição de PDF. | 100–104 | Suíte verde. | P1 |
| TASK-112 | Validação contra recibos reais | Reproduzir ≥ 10 recibos já emitidos manualmente. | 054 | Valores idênticos aos conferidos pelo contador. | P0 |
| TASK-113 | Deploy | Ambiente de produção com TLS e backup ativo. | 105,109 | Sistema acessível e monitorado. | P1 |
| TASK-114 | Piloto | Emitir os primeiros recibos reais sob supervisão. | 113 | Primeiro mês sem divergência de cálculo. | P1 |

### Backlog pós-MVP (P2)
`TASK-120` e-mail do PDF · `TASK-121` exportação CSV/XLSX · `TASK-122` relatório por autônomo ·
`TASK-123` marcar como pago · `TASK-124` descontos manuais · `TASK-125` recibo substitutivo
automático · `TASK-126` emissão em lote · `TASK-127` múltiplos itens de serviço ·
`TASK-128` import CSV de cadastros · `TASK-129` 2FA para admin · `TASK-130` múltiplos templates ·
`TASK-131` consulta de CEP/CNPJ · `TASK-132` multi-tenant ativo.

---

## 16. Ordem de implementação

```
 1. TASK-001..007   Discovery + início da homologação fiscal      [BLOQUEANTE]
 2. TASK-010..018   Fundação do projeto
 3. TASK-020..030   Banco e repositórios
 4. TASK-040..044   Domínio puro
 5. TASK-050..057   MOTOR DE CÁLCULO                              [depende de 004/005]
 6. TASK-060..062   Auth, RBAC, auditoria
 7. TASK-063..067   Cadastros, rascunho, numeração
 8. TASK-068..076   Fluxo de estados, emissão, listagem
 9. TASK-080..086   PDF
10. TASK-090..096   Interface
11. TASK-100..109   Segurança, LGPD, operação
12. TASK-110..114   Homologação, deploy, piloto
```

**Justificativa da ordem:**
- **Domínio e cálculo antes da API** porque o cálculo é o núcleo de valor e o maior risco; se ele estiver errado, nada mais importa. E porque ele é a parte que sobrevive intacta se H02 mudar (seção 6.3).
- **Banco antes do domínio?** Não: o domínio não depende do banco. As duas frentes são paralelizáveis; a ordem acima só reflete um desenvolvedor trabalhando sozinho.
- **Auth e auditoria antes das rotas de negócio** porque colocar segurança depois significa reescrever todas as rotas.
- **PDF depois da emissão** porque o documento é derivado do recibo, não o contrário.
- **Interface por último dentro do MVP** porque a API já prova o fluxo, e a UI muda muito com feedback.
- **A homologação fiscal começa no dia 1** e é a única atividade que não posso acelerar sozinho.

---

## 17. Estratégia de trabalho com Claude Code

Estas regras vão para o `CLAUDE.md` na raiz do repositório.

### Regras de processo
1. **Não implementar sem entender o contexto.** Antes de alterar, ler o código existente e as regras envolvidas. Em dúvida sobre requisito, perguntar — não deduzir.
2. **Uma tarefa por vez.** Trabalhar sempre com um `TASK-XXX` explícito. Nada de "e já aproveitei para arrumar isso aqui".
3. **Mudanças pequenas e revisáveis.** Se o diff passa de algumas centenas de linhas, quebrar.
4. **Nunca alterar arquivo fora do escopo da tarefa.** Formatação em massa e refatoração oportunista são proibidas dentro de uma tarefa funcional.
5. **Rodar lint, tipos e testes após cada alteração** e relatar o resultado real. Sem "deve funcionar".
6. **Nunca ignorar, silenciar ou contornar erro.** Nada de `except: pass`, `# type: ignore` sem justificativa escrita, ou teste marcado como skip para ficar verde.
7. **Não criar abstração antes do segundo caso de uso real.** Nada de "interface para caso um dia troquemos de banco".
8. **Nenhuma dependência nova sem justificativa** — problema que resolve, alternativa considerada, custo de manutenção — registrada no PR ou em ADR.
9. **Documentação junto com a mudança**, não depois: README, ADR e este planejamento acompanham o código.
10. **Não marcar tarefa como concluída sem o critério de aceite atendido.** Se algo ficou de fora, dizer explicitamente o quê.

### Regras específicas deste domínio
11. **Regra tributária:** nenhum número fiscal entra no código, nunca, por nenhum motivo — nem "de exemplo", nem "temporário", nem em teste que pareça oficial. Fixture de teste não homologada é marcada como fictícia.
12. **Cálculo:** toda alteração no motor exige teste antes da mudança; nenhum resultado é alterado sem apontar a fonte que justifica. Bug de cálculo vira teste de regressão primeiro.
13. **Migrations:** sempre revisar o `autogenerate` manualmente; nunca editar uma migration já aplicada em produção; migration com dados precisa de plano de reversão.
14. **Segurança:** toda rota nova declara autenticação e papel exigido no mesmo commit. Nenhuma query com string interpolada. Nenhum segredo em código, log ou teste.
15. **Dinheiro:** `Decimal` sempre, `float` nunca. Arredondamento só pelo módulo central.
16. **Imutabilidade:** nenhum código que altere recibo emitido é aceito, nem "só para corrigir um errinho".
17. **Dados reais:** nunca usar dados pessoais reais em seed, teste, fixture ou exemplo.
18. **Antes de "pronto":** rodar a suíte inteira, reler o próprio diff de forma adversarial e listar o que foi deixado de fora.

### Como vamos conversar
- Toda sessão começa com o `TASK-XXX` alvo e termina com: o que mudou, testes rodados e resultado, o que ficou pendente.
- Quando houver mais de uma solução válida, comparar as alternativas antes de escolher.
- Discordar quando eu achar a decisão ruim — inclusive das suas. Concordância silenciosa é o pior resultado possível aqui.
- Nada de implementar antecipando fases futuras.

---

## 18. Critérios de qualidade — checklist de produção

**Código**
- [ ] `ruff` e `mypy` limpos, sem supressão sem justificativa
- [ ] `domain/` sem dependência de framework (teste de arquitetura verde)
- [ ] Nenhum TODO/FIXME em caminho crítico
- [ ] Nenhum valor fiscal hard-coded (verificado por busca)

**Testes**
- [ ] Módulo de cálculo com cobertura ~100% e todos os casos homologados passando
- [ ] Matriz completa de transições de estado testada
- [ ] Matriz de autorização (papel x rota) testada
- [ ] Property-based sem contraexemplo para RN03 e determinismo
- [ ] E2E do fluxo C03 verde
- [ ] Teste de numeração concorrente sem lacuna
- [ ] ≥ 10 recibos reais reproduzidos com valores conferidos pelo contador

**Segurança**
- [ ] Toda rota autenticada e autorizada no servidor
- [ ] Senhas em Argon2id; rate limit no login
- [ ] Zero segredo no repositório; `.env.example` sem valores
- [ ] Dados bancários cifrados em repouso
- [ ] CSP, HSTS e demais cabeçalhos ativos
- [ ] `pip-audit` sem vulnerabilidade conhecida de severidade alta
- [ ] PDF inacessível sem autorização

**Banco**
- [ ] Migrations aplicam e revertem em ambiente limpo
- [ ] Constraints da seção 8.2 ativas e testadas
- [ ] Índices cobrindo as consultas frequentes
- [ ] Usuário da aplicação sem privilégio de DDL nem UPDATE em `audit_logs`

**Logs e observabilidade**
- [ ] Log JSON com `request_id`, sem PII
- [ ] Erros de cálculo e falhas de PDF registrados e visíveis
- [ ] Healthcheck respondendo
- [ ] Auditoria cobrindo emissão, cancelamento, alteração de cadastro e de parâmetros

**Backup**
- [ ] Backup diário automatizado de banco e PDFs
- [ ] **Restauração executada com sucesso e com data registrada**
- [ ] Cópia fora do servidor de produção

**Deploy**
- [ ] Container não-root, imagem sem ferramenta de build
- [ ] TLS ativo
- [ ] Rollback possível e documentado
- [ ] Variáveis de ambiente conferidas

**Documentação**
- [ ] README com setup reproduzível em máquina limpa
- [ ] `docs/parametros-fiscais.md` completo, com fonte e homologação
- [ ] ADRs das decisões relevantes
- [ ] Runbook operacional

**LGPD**
- [ ] Base legal e finalidades documentadas
- [ ] Minimização revisada (nenhum campo coletado sem uso)
- [ ] Retenção e expurgo definidos
- [ ] Procedimento de atendimento a titular
- [ ] Acesso a dado sensível auditado

**Erros e performance**
- [ ] Nenhum stack trace exposto ao usuário
- [ ] Mensagens acionáveis, especialmente "vigência não homologada"
- [ ] Listagem < 500 ms p95 no volume esperado
- [ ] PDF < 3 s p95

---

## 19. Decisões pendentes — preciso da sua resposta

| # | Pergunta | Hipótese atual | Por que trava |
|---|---|---|---|
| D1 | Folha CLT está no escopo? | Não (H01) | Muda o projeto inteiro. |
| D2 | Onde roda: servidor/navegador, ou local monousuário? | Web multiusuário (H02) | Define FastAPI+Postgres vs. app local+SQLite. |
| D3 | Existe modelo de recibo usado hoje? Pode compartilhar? | Não há (H03) | Define o layout do PDF e a biblioteca (TASK-080). |
| D4 | Assinatura: manuscrita ou digital com validade jurídica? | Manuscrita (H04) | ICP-Brasil é épico próprio. |
| D5 | Integrações no MVP (e-mail, contábil, banco)? | Nenhuma (H05) | Define se entra fila/worker. |
| D6 | Login com papéis distintos é necessário? | Sim, 4 papéis (H06) | Define RBAC. |
| D7 | Uma empresa ou várias no mesmo sistema? | Uma (H07) | Multi-tenant. |
| D8 | Objetivo: interno, produto ou estudo? | Interno profissional (H08) | Define nível de rigor. |
| D9 | Recibo emitido pode ser editado ou só cancelado/substituído? | Só cancelado/substituído (H09) | **É a decisão que mais afeta o modelo de dados.** |
| D10 | Volume mensal esperado? | Dezenas a centenas (H10) | Define se PDF é síncrono. |
| D11 | Quem é o contador/fonte que vai homologar RV01–RV11? | Indefinido | **Caminho crítico do projeto.** |
| D12 | Orçamento de infraestrutura e prazo? | Indefinido | Define opções de deploy. |
