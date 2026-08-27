# ADR-0001 — Arquitetura em camadas com domínio isolado

- **Status:** aceito
- **Data:** 2026-08-27
- **Contexto do backlog:** TASK-018

## Contexto

O sistema calcula valores financeiros a partir de regras tributárias que mudam
todo ano e que ainda não estão validadas. O cálculo é o ativo crítico: se ele
estiver errado, nada mais no sistema importa.

Além disso, a decisão D2 do planejamento (onde o sistema roda — servidor web ou
aplicação local) ainda está em aberto. Escolher a arquitetura em torno do
transporte agora significaria refazer o trabalho se a resposta vier diferente.

## Decisão

Monólito modular em camadas, com `app/domain/` **puro**: sem framework web, sem
ORM, sem I/O, sem leitura de relógio.

```
HTTP / CLI          borda: valida entrada, autentica, serializa
Services            casos de uso: transação, fluxo
Domain (puro)       cálculo, máquina de estados, invariantes
Repositories        acesso a dados
Persistência
```

A regra de dependência é verificada por teste automatizado
(`tests/architecture/test_domain_purity.py`), que falha se alguém importar
SQLAlchemy, FastAPI, `os`, `logging` ou qualquer coisa fora da lista permitida
dentro do domínio.

## Consequências

**A favor**

- O motor de cálculo é testável com `pytest` puro: sem subir servidor, sem
  banco, sem container. Os testes mais importantes do projeto são os mais rápidos.
- O domínio sobrevive intacto se a decisão D2 mudar. Troca-se a casca, não o miolo.
- O determinismo exigido pelo RNF01 fica estrutural: sem relógio e sem I/O
  dentro do domínio, o mesmo cálculo dá o mesmo resultado sempre.

**Contra**

- Mais arquivos e mais indireção do que colocar a lógica direto no handler.
- Exige disciplina: a tentação de importar a sessão do banco dentro do domínio
  vai aparecer. É por isso que existe o teste de arquitetura.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Django** com admin, auth e ORM prontos | Aceleraria muito o começo, mas o admin vira porta de fuga das regras de negócio — dá para editar um recibo emitido direto no banco pela interface, violando a RN09. O acoplamento do ORM ao modelo também levaria regras fiscais para dentro de classes de persistência. |
| **Tudo no handler HTTP** (script direto) | Torna o cálculo dependente de `Request`/`Session`. Os testes de cálculo passariam a exigir servidor e banco: lentos, frágeis, e a suíte crítica seria a pior de rodar. |
| **Microsserviços** | Um time, volume baixo, e a emissão precisa ser atômica (numerar + emitir + gravar na mesma transação). Distribuir isso adiciona latência e falha parcial sem resolver nenhum problema real. Overengineering. |
| **Arquitetura hexagonal completa**, com portas e adaptadores para tudo | Abstração antes do segundo caso de uso. Hoje há um banco e um formato de documento. Criar interface para trocar de banco é resolver problema que não existe. |
