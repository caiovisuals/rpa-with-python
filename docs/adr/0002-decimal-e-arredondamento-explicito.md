# ADR-0002 — `Decimal` obrigatório e arredondamento sempre explícito

- **Status:** aceito
- **Data:** 2026-08-27
- **Contexto do backlog:** TASK-040, TASK-041

## Contexto

O sistema calcula descontos sobre valores em reais. Um centavo perdido por
arredondamento silencioso vira divergência contábil, e divergência contábil em
documento fiscal é problema real, não detalhe.

Agrava o quadro o fato de que a **política de arredondamento aplicável ainda não
foi validada** (regra RV05). Não sabemos ainda quantas casas, em que momento,
nem por qual critério cada tributo arredonda.

## Decisão

1. **`float` é proibido em valores monetários.** O tipo `Money` recusa `float`
   no construtor e como fator de multiplicação, levantando erro. Não converte:
   recusa.
2. **Nenhuma operação arredonda em silêncio.** Soma e subtração são exatas.
   Multiplicação por alíquota devolve o valor exato, com quantas casas
   precisar — transformá-lo em valor de moeda exige chamar `quantized()`
   passando a política.
3. **Não existe política de arredondamento padrão.** `app/domain/rounding.py`
   oferece as seis políticas possíveis e obriga o chamador a escolher. Um padrão
   seria uma regra tributária inventada, disfarçada de conveniência.
4. **Entrada digitada com mais de duas casas é recusada**, não arredondada:
   quem digitou precisa saber que o valor não cabe na moeda.
5. **Um único ponto de arredondamento.** Nenhum outro módulo chama
   `Decimal.quantize` diretamente.

## Consequências

**A favor**

- Impossível perder centavo por acidente: o tipo não deixa.
- Quando a RV05 for homologada, a política entra em um lugar só.
- O código deixa visível onde há decisão de arredondamento — cada chamada a
  `quantized()` é um ponto que o contador pode auditar.

**Contra**

- Mais verboso: `(base * aliquota).quantized(policy)` em vez de `base * aliquota`.
  É verbosidade proposital — o ponto é que a decisão apareça.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Inteiros em centavos** | Tecnicamente sólido e às vezes superior — imune a erro de escala. Mas alíquota progressiva com parcela a deduzir fica difícil de ler em centavos, e a legibilidade da regra fiscal importa: o contador precisa conseguir conferir. **Decisão a revisar na Fase 4**, se o motor de cálculo mostrar atrito. |
| **`Money` arredondando sozinho para 2 casas** | Esconde exatamente a decisão que precisa ficar visível, e escolheria uma política antes de a RV05 existir. |
| **`float` com arredondamento no fim** | `0.1 + 0.2 != 0.3` em binário. Inaceitável para dinheiro. |
| **Biblioteca de terceiros (`py-moneyed`, etc.)** | Traz câmbio, catálogo de moedas e formatação que não usamos. O tipo que precisamos tem ~90 linhas e regras específicas deste domínio (recusar `float`, recusar arredondamento implícito) que nenhuma biblioteca genérica impõe. Dependência sem justificativa. |
