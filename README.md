# RPA COM PYTHON

Sistema de geração e gerenciamento de **Recibo de Pagamento Autônomo (RPA)**
para uma empresa que contrata prestadores de serviço sem vínculo empregatício.

## Estado atual

| Fase | Situação |
|---|---|
| F0 — Discovery | Planejamento escrito; 4 de 12 decisões respondidas ([`decisoes.md`](docs/decisoes.md)) |
| F0.5 — Homologação fiscal | **Não iniciada.** Bloqueia o motor de cálculo |
| F1 — Fundação | Concluída |
| F2 — Banco | Próxima. Destravada pela definição do escopo CLT |
| F3 — Domínio puro | Concluída |
| F4 — Motor de cálculo | Destravada em **modo simulação** (ADR-0004) |

O que já existe é o **domínio puro**: tipos de valor, arredondamento
parametrizável, máquina de estados do recibo e invariantes. A camada web, o
banco e a geração de PDF ainda não existem.

**Escopo ampliado:** o sistema atenderá também funcionários CLT, com cálculo de
folha e emissão de holerite — **sem** férias, 13º, rescisão e eSocial. A ordem
definida é **RPA primeiro, até produção; CLT depois**, como módulo aditivo. Ver
[`docs/decisoes.md`](docs/decisoes.md) e
[ADR-0005](docs/adr/0005-rpa-e-folha-clt-o-que-e-compartilhado.md).

## Aviso sobre regras tributárias

Este projeto **não contém nenhuma regra tributária presumida**. Não há alíquota,
faixa, teto nem dedução no código-fonte, e não haverá: os valores vivem em
tabelas parametrizadas por vigência, preenchidas a partir de fonte oficial e
homologadas por profissional de contabilidade.

O documento [`docs/parametros-fiscais.md`](docs/parametros-fiscais.md) está
**vazio de propósito**.

Enquanto ele não for preenchido e homologado, o sistema opera em **modo
simulação**: parâmetros podem ser carregados como provisórios e o cálculo roda,
mas o documento sai com marca d'água e **não pode virar recibo definitivo**. A
trava é estrutural, em `app/domain/calculation/approval.py`. Ver
[ADR-0004](docs/adr/0004-modo-simulacao-sem-homologacao.md).

## Como rodar

```bash
pip install -e ".[dev]"

ruff check . && ruff format --check .   # lint e formatação
mypy                                    # tipos, modo estrito
pytest --cov=app --cov-report=term-missing
```

Os quatro precisam passar antes de qualquer coisa ser considerada pronta.

Com Docker, para subir o banco de desenvolvimento:

```bash
cp .env.example .env    # preencha POSTGRES_PASSWORD
docker compose up
```

## Estrutura

```
app/
├── core/            infraestrutura transversal (ainda vazio)
└── domain/          NÚCLEO PURO — sem framework, sem ORM, sem I/O
    ├── errors.py            exceções do domínio
    ├── rounding.py          arredondamento; nenhuma política padrão
    ├── calculation/
    │   └── approval.py      homologação e modo simulação
    ├── receipt/
    │   ├── status.py        máquina de estados do RPA
    │   └── rules.py         invariantes (RN02, RN03, RN08)
    └── value_objects/       CPF, CNPJ, Money, Competência
tests/
├── architecture/    garante o isolamento do domínio
└── unit/            unitários e baseados em propriedade
docs/
├── PLANEJAMENTO.md          requisitos, arquitetura, roadmap, backlog
├── parametros-fiscais.md    homologação fiscal (vazio)
└── adr/                     decisões de arquitetura
```

O domínio **não tem dependência de runtime** — por construção. Isso é verificado
por `tests/architecture/test_domain_purity.py`, que falha se alguém importar
framework, ORM, I/O ou ler o relógio dentro de `app/domain/`.

## Documentação

- [`docs/PLANEJAMENTO.md`](docs/PLANEJAMENTO.md) — planejamento completo
- [`docs/decisoes.md`](docs/decisoes.md) — registro das decisões de escopo
- [`docs/parametros-fiscais.md`](docs/parametros-fiscais.md) — homologação fiscal
- [`docs/adr/`](docs/adr/) — decisões de arquitetura
- [`CLAUDE.md`](CLAUDE.md) — regras de trabalho no repositório
