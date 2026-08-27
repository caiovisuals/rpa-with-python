# Regras de trabalho — sistema de RPA

Este arquivo vale para toda sessão de desenvolvimento neste repositório.
Ele deriva da seção 17 de [`docs/PLANEJAMENTO.md`](docs/PLANEJAMENTO.md).

## Contexto do projeto

Sistema de emissão de **Recibo de Pagamento Autônomo** para uma empresa que
contrata prestadores sem vínculo. Lida com **dados pessoais e valores
financeiros reais**. Estado atual: Fase 1 (fundação) e Fase 3 (domínio puro)
concluídas. O sistema opera em **modo simulação** enquanto a homologação fiscal
não existir. Escopo ampliado para incluir folha CLT, a ser construída **depois**
do RPA (ADR-0005).

Antes de começar qualquer tarefa, ler [`docs/decisoes.md`](docs/decisoes.md):
ele registra quais hipóteses do planejamento já viraram requisito e prevalece
sobre a seção 0.2 do planejamento.

## A regra que não se negocia

**Nenhum número fiscal entra no código. Nunca.**

Nem alíquota, nem faixa, nem teto, nem dedução — nem "de exemplo", nem
"temporário", nem "só para o teste passar". Os valores vivem em tabelas
parametrizadas por vigência, preenchidas a partir de fonte oficial e
homologadas por contador (ver `docs/parametros-fiscais.md`).

Fixture de teste que não veio da homologação é marcada explicitamente como
fictícia. Enquanto `docs/parametros-fiscais.md` estiver incompleto, o sistema
não emite recibo definitivo — opera em simulação (ADR-0004).

**Parâmetro provisório não é exceção a esta regra.** Provisório é dado carregado
por um administrador, com registro de quem carregou; nunca constante em Python.
A diferença é toda: o primeiro é visível, rastreável e barra a emissão; o
segundo se esconde na lógica e ninguém lembra que estava lá.

## Processo

1. **Não implementar sem entender o contexto.** Ler o código e as regras
   envolvidas antes de alterar. Em dúvida sobre requisito, perguntar — não deduzir.
2. **Uma tarefa por vez**, sempre com um `TASK-XXX` explícito do backlog
   (seção 15 do planejamento). Nada de "já aproveitei para arrumar isso aqui".
3. **Mudanças pequenas e revisáveis.** Diff grande demais se quebra em partes.
4. **Nunca alterar arquivo fora do escopo da tarefa.** Formatação em massa e
   refatoração oportunista são proibidas dentro de uma tarefa funcional.
5. **Rodar lint, tipos e testes após cada alteração** e relatar o resultado
   real. Sem "deve funcionar".
6. **Nunca ignorar, silenciar ou contornar erro.** Nada de `except: pass`,
   `# type: ignore` sem justificativa escrita, ou teste marcado como skip para
   ficar verde.
7. **Não criar abstração antes do segundo caso de uso real.** Caso de uso
   *previsto* não conta — folha CLT está no roadmap, e mesmo assim não se cria
   `Beneficiario` genérico hoje (ADR-0005).
8. **Nenhuma dependência nova sem justificativa** — problema que resolve,
   alternativa considerada, custo de manutenção — registrada em ADR.
9. **Documentação junto com a mudança**, não depois.
10. **Não marcar tarefa como concluída sem o critério de aceite atendido.**
    Se algo ficou de fora, dizer explicitamente o quê.

## Específicas deste domínio

11. **Cálculo:** toda alteração no motor exige teste antes da mudança; nenhum
    resultado muda sem apontar a fonte que justifica. Bug de cálculo vira teste
    de regressão primeiro.
12. **Dinheiro:** `Decimal` sempre, `float` nunca. O tipo `Money` recusa `float`
    por construção. Arredondamento só por `app/domain/rounding.py`, sempre com
    política explícita — não existe política padrão.
13. **Domínio puro:** `app/domain/` não importa framework, ORM, I/O nem lê o
    relógio. Garantido por `tests/architecture/`. Se esse teste falhar, o
    problema é o código novo, não o teste.
14. **Determinismo:** data e hora entram como parâmetro, nunca via
    `date.today()` dentro do domínio.
15. **Imutabilidade:** a janela de correção fecha na **entrega** ao autônomo, não
    na emissão (ADR-0003). Recibo `ENTREGUE`, `PAGO` ou `CANCELADO` não muda,
    nem "só para corrigir um errinho" — correção é cancelar + emitir
    substitutivo. Recibo `EMITIDO` e não entregue volta para rascunho por
    retificação, com justificativa, preservando o número.
16. **Migrations:** revisar o `autogenerate` à mão; nunca editar migration já
    aplicada em produção; migration com dados precisa de plano de reversão.
17. **Segurança:** toda rota nova declara autenticação e papel exigido no mesmo
    commit. Nenhuma query com string interpolada. Nenhum segredo em código, log
    ou teste.
18. **Dados reais:** nunca usar dados pessoais reais em seed, teste, fixture ou
    exemplo. CPFs e CNPJs nos testes são fictícios, válidos apenas quanto ao
    dígito verificador.

## Comandos

```bash
pip install -e ".[dev]"     # instala dependências de desenvolvimento
ruff check . && ruff format --check .
mypy
pytest --cov=app --cov-report=term-missing
```

Antes de considerar qualquer coisa pronta, os quatro passam.

## Formato de fim de sessão

Toda sessão termina com: **o que mudou**, **testes rodados e resultado**, **o
que ficou pendente**. Havendo mais de uma solução válida, comparar as
alternativas antes de escolher. Discordar quando a decisão parecer ruim —
concordância silenciosa é o pior resultado possível aqui.
