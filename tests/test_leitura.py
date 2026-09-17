from datetime import date
from io import BytesIO

import pytest
from openpyxl import Workbook

from consolida.arquivo import ArquivoInvalido
from consolida.colunas import achar_cabecalho
from consolida.leitura import ler_planilha, nome_da_loja, nome_seguro


def test_acha_cabecalho_depois_do_titulo():
    linhas = [["Relatório de vendas"], [], ["data da venda", "descrição", "QTDE", "VL UNIT"]]
    assert achar_cabecalho(linhas) == (2, {"data": 0, "produto": 1, "quantidade": 2, "preco": 3})


def test_sem_colunas_obrigatorias_nao_acha_cabecalho():
    assert achar_cabecalho([["Data", "Produto", "Quantidade"]]) is None


@pytest.mark.parametrize(
    ("arquivo", "loja"),
    [
        ("loja_centro.xlsx", "Centro"),
        ("vendas_rudge_ramos.xlsx", "Rudge Ramos"),
        ("Loja Diadema - jan a mar.xlsx", "Diadema"),
        ("VENDAS SAO BERNARDO DO CAMPO 2026.xlsx", "Sao Bernardo do Campo"),
        ("vendas-03-2026.xlsx", "Arquivo 2"),
    ],
)
def test_nome_da_loja(arquivo, loja):
    assert nome_da_loja(arquivo, 2) == loja


def test_nome_seguro_remove_caminho_e_caracteres_estranhos():
    assert nome_seguro("..\\..\\<script>vendas.xlsx") == "scriptvendas.xlsx"
    assert nome_seguro("/etc/passwd") == "passwd"


def test_le_e_descarta_com_motivo(xlsx):
    conteudo = xlsx(
        [
            ["Data", "Produto", "Categoria", "Qtd", "Valor Unit.", "Total"],
            [date(2026, 1, 5), "Cimento CP II 50kg", "Cimento", 2, 36.9, 73.8],
            [],
            ["31/02/2026", "Trena 5m", "Ferramentas", 1, 24.9, 24.9],
            [date(2026, 1, 6), "", "Ferramentas", 1, 24.9, 24.9],
            [date(2026, 1, 6), "Trena 5m", "Ferramentas", None, 24.9, None],
            [date(2026, 1, 6), "Trena 5m", "Ferramentas", -1, 24.9, -24.9],
            [date(2026, 1, 6), "Trena 5m", "Ferramentas", 1, "grátis", None],
            [date(2026, 1, 7), "Tomada 10A", None, 3, "R$ 9,90", "R$ 99,00"],
            [date(1990, 1, 7), "Tomada 10A", "Elétrica", 1, 9.9, 9.9],
            [None, "TOTAL", None, None, None, 73.8],
        ]
    )
    lido = ler_planilha("loja_centro.xlsx", conteudo)

    assert lido.loja == "Centro"
    assert [(v["linha"], v["produto"], v["total"]) for v in lido.vendas] == [(2, "Cimento CP II 50kg", 73.8)]
    assert [(d["linha"], d["motivo"]) for d in lido.descartadas] == [
        (4, "data vazia ou inválida"),
        (5, "produto vazio"),
        (6, "quantidade vazia ou inválida"),
        (7, "quantidade zero ou negativa (devolução não entra no fechamento)"),
        (8, "preço vazio ou inválido"),
        (9, "total informado (99,00) diferente de quantidade x preço (29,70)"),
        (10, "data fora do intervalo esperado"),
        (11, "linha de total da planilha"),
    ]
    assert lido.descartadas[0]["conteudo"] == "31/02/2026 | Trena 5m | Ferramentas | 1 | 24.9 | 24.9"


def test_coluna_de_loja_tem_prioridade_sobre_o_nome_do_arquivo(xlsx):
    conteudo = xlsx([["Filial", "Data", "Item", "Quantidade", "Preço"], ["Santo André", "02/01/2026", "Lixa", "10", "1,50"]])
    lido = ler_planilha("consolidado.xlsx", conteudo)
    assert lido.vendas[0]["loja"] == "Santo André"
    assert lido.vendas[0]["total"] == 15.0


def test_categoria_vazia_vira_sem_categoria(xlsx):
    lido = ler_planilha("a.xlsx", xlsx([["Data", "Produto", "Qtd", "Preço"], ["02/01/2026", "Lixa", 1, 1.5]]))
    assert lido.vendas[0]["categoria"] == "Sem categoria"


def test_procura_o_cabecalho_nas_outras_abas():
    livro = Workbook()
    livro.active.append(["Anotações da semana"])
    vendas = livro.create_sheet("Vendas")
    vendas.append(["Data", "Produto", "Qtd", "Preço"])
    vendas.append(["02/01/2026", "Lixa", 1, 1.5])
    saida = BytesIO()
    livro.save(saida)
    assert len(ler_planilha("a.xlsx", saida.getvalue()).vendas) == 1


def test_planilha_sem_cabecalho(xlsx):
    with pytest.raises(ArquivoInvalido, match="cabeçalho"):
        ler_planilha("a.xlsx", xlsx([["nome", "telefone"], ["Ana", "1199999"]]))
