"""O domínio não pode conhecer framework, ORM nem I/O.

Esta é a salvaguarda que impede o motor de cálculo de apodrecer. Se alguém
importar SQLAlchemy dentro de ``app/domain``, este teste falha — e é para
falhar, não para ser ajustado.
"""

import ast
import sys
from pathlib import Path

import pytest

DOMAIN = Path(__file__).resolve().parents[2] / "app" / "domain"

#: Módulos da biblioteca padrão que o domínio pode usar. Lista curta de
#: propósito: se algo novo precisar entrar aqui, é uma decisão consciente.
STDLIB_PERMITIDA = {
    "__future__",
    "abc",
    "collections",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "functools",
    "itertools",
    "re",
    "typing",
    "uuid",
}

#: Nada de I/O, rede, ORM ou framework. Se aparecer, o teste aponta o culpado.
PROIBIDOS_EXPLICITAMENTE = {
    "sqlalchemy",
    "alembic",
    "fastapi",
    "starlette",
    "pydantic",
    "httpx",
    "requests",
    "flask",
    "django",
    "jinja2",
    "weasyprint",
    "reportlab",
    "redis",
    "celery",
    "os",
    "io",
    "pathlib",
    "socket",
    "subprocess",
    "logging",
    "random",
    "time",
}

MODULOS = sorted(DOMAIN.rglob("*.py"))


def _imports(arquivo: Path) -> set[str]:
    """Módulos-raiz importados por um arquivo."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    raizes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            raizes.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            raizes.add(no.module.split(".")[0])
    return raizes


def test_existem_modulos_de_dominio_para_verificar():
    """Guarda contra o teste passar por não achar arquivo nenhum."""
    assert MODULOS, f"nenhum módulo encontrado em {DOMAIN}"


@pytest.mark.parametrize("arquivo", MODULOS, ids=lambda p: p.name)
def test_dominio_so_importa_stdlib_permitida_e_ele_mesmo(arquivo: Path):
    for raiz in sorted(_imports(arquivo)):
        if raiz == "app":
            continue
        assert raiz in STDLIB_PERMITIDA, (
            f"{arquivo.relative_to(DOMAIN.parent.parent)} importa '{raiz}', "
            "que não está na lista permitida do domínio. "
            "O domínio é puro: sem framework, sem ORM, sem I/O."
        )


@pytest.mark.parametrize("arquivo", MODULOS, ids=lambda p: p.name)
def test_dominio_nao_importa_nada_proibido(arquivo: Path):
    proibidos = _imports(arquivo) & PROIBIDOS_EXPLICITAMENTE
    assert not proibidos, (
        f"{arquivo.relative_to(DOMAIN.parent.parent)} importa {sorted(proibidos)}. "
        "Isso quebra o isolamento do domínio (RNF10/RNF11)."
    )


@pytest.mark.parametrize("arquivo", MODULOS, ids=lambda p: p.name)
def test_dominio_so_importa_de_app_domain(arquivo: Path):
    """Dentro do próprio projeto, o domínio só pode depender do domínio."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    for no in ast.walk(arvore):
        modulo = None
        if isinstance(no, ast.Import):
            for alias in no.names:
                if alias.name.startswith("app."):
                    modulo = alias.name
        elif isinstance(no, ast.ImportFrom) and no.module and no.module.startswith("app."):
            modulo = no.module
        if modulo is not None:
            assert modulo.startswith("app.domain"), (
                f"{arquivo.name} importa '{modulo}'. O domínio não pode depender "
                "de app.api, app.models, app.repositories, app.services nem app.core."
            )


def test_a_lista_permitida_so_contem_stdlib():
    """Se um pacote de terceiros entrar na lista permitida por engano, isto pega."""
    fora = {m for m in STDLIB_PERMITIDA if m not in sys.stdlib_module_names}
    assert not fora, f"não são da biblioteca padrão: {sorted(fora)}"


def test_dominio_nao_le_o_relogio():
    """Data é sempre parâmetro (RNF01: cálculo determinístico).

    ``datetime.now()``, ``date.today()`` e ``time.time()`` dentro do domínio
    tornariam o resultado dependente do dia em que o teste roda.
    """
    proibidas = {"now", "today", "utcnow"}
    for arquivo in MODULOS:
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
                assert no.func.attr not in proibidas, (
                    f"{arquivo.name}:{no.lineno} chama '{no.func.attr}()'. "
                    "O domínio não lê o relógio: receba a data como parâmetro."
                )
