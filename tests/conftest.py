from io import BytesIO

import pytest
from openpyxl import Workbook

from app import main


def planilha(linhas: list[list], titulo: str = "Vendas") -> bytes:
    livro = Workbook()
    aba = livro.active
    aba.title = titulo
    for linha in linhas:
        aba.append(linha)
    saida = BytesIO()
    livro.save(saida)
    return saida.getvalue()


@pytest.fixture
def xlsx():
    return planilha


@pytest.fixture(autouse=True)
def limpar_limite():
    main.limite.hits.clear()
    yield
    main.limite.hits.clear()
