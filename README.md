# RPA COM PYTHON

Sistema de geração e gerenciamento de **Recibo de Pagamento Autônomo (RPA)**
para uma empresa que contrata prestadores de serviço sem vínculo empregatício.

## Estado atual

| Fase | Situação |
|---|---|
| F0 — Discovery | Planejamento escrito; 4 de 12 decisões respondidas ([`decisoes.md`](docs/decisoes.md)) |
| F0.5 — Homologação fiscal | **Não iniciada.** Bloqueia o motor de cálculo |
| F1 — Fundação | Concluída |
| F2 — Banco | **Retida** pela ampliação de escopo para funcionários CLT (D1) |
| F3 — Domínio puro | Concluída |
| F4 — Motor de cálculo | **Bloqueada pela homologação fiscal** |

O que já existe é o **domínio puro**: tipos de valor, arredondamento
parametrizável, máquina de estados do recibo e invariantes. A camada web, o
banco e a geração de PDF ainda não existem.

**Ampliação de escopo em aberto:** ficou definido que o sistema deve atender
também funcionários CLT, além de autônomos. Folha de pagamento é outro domínio
— holerite, férias, 13º, rescisão, eSocial — e o alcance exato ainda está sendo
definido. Por isso o modelo de dados está retido: ver
[`docs/decisoes.md`](docs/decisoes.md).

## Aviso sobre regras tributárias

Este projeto **não contém nenhuma regra tributária presumida**. Não há alíquota,
faixa, teto nem dedução no código-fonte, e não haverá: os valores vivem em
tabelas parametrizadas por vigência, preenchidas a partir de fonte oficial e
homologadas por profissional de contabilidade.

O documento [`docs/parametros-fiscais.md`](docs/parametros-fiscais.md) está
**vazio de propósito**. Enquanto ele não for preenchido e homologado, o motor de
cálculo não pode ser implementado e o sistema não emite recibo definitivo.

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
