# Imagem da aplicação. Multi-stage: as ferramentas de build não vão para a
# imagem final, e o processo não roda como root.

# ---------------------------------------------------------------- builder
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY app ./app

# `.[dev]` por ora: a imagem ainda serve para rodar a suíte de testes. Quando a
# camada web existir (Fase 5), a imagem de produção instala só `.`.
RUN pip install --upgrade pip && pip install -e ".[dev]"

# ---------------------------------------------------------------- runtime
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Usuário sem privilégio: nada aqui precisa de root.
RUN useradd --create-home --uid 10001 rpa

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=rpa:rpa . .

USER rpa

# Enquanto não há servidor, o comando padrão é a suíte de testes — é o que a
# imagem tem para oferecer hoje. Vira `uvicorn` na Fase 5 (TASK-060+).
CMD ["pytest", "--cov=app", "--cov-report=term-missing"]
