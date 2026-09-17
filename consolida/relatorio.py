from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet

from consolida.consolidar import Consolidado

MOEDA = '"R$" #,##0.00'
DATA = "DD/MM/YYYY"
PORCENTAGEM = "0.0%"
VERDE = "1D6F42"

TITULO = Font(size=16, bold=True)
SECAO = Font(size=12, bold=True, color=VERDE)
NEGRITO = Font(bold=True)
CABECALHO = PatternFill("solid", fgColor="E8EEEA")
LINHA_TOTAL = Border(top=Side(style="thin", color="7A8A80"))
CONFERIR = PatternFill("solid", fgColor="FFF2CC")


def escrever(ws: Worksheet, linha: int, coluna: int, valor, formato: str | None = None):
    celula = ws.cell(row=linha, column=coluna, value=valor)
    # texto vindo da planilha do usuario nunca vira formula (=HYPERLINK, =cmd|...)
    if isinstance(valor, str) and celula.data_type == "f":
        celula.data_type = "s"
        celula.quotePrefix = True
    if formato:
        celula.number_format = formato
    return celula


def cabecalho(ws: Worksheet, linha: int, nomes: list[str]) -> None:
    for coluna, nome in enumerate(nomes, start=1):
        celula = ws.cell(row=linha, column=coluna, value=nome)
        celula.font = NEGRITO
        celula.fill = CABECALHO
        celula.alignment = Alignment(horizontal="left" if coluna == 1 else "right")


def aba_resumo(ws: Worksheet, dados: Consolidado) -> None:
    vendas = dados.vendas
    ws.title = "Resumo"
    ws["A1"] = "Fechamento de vendas"
    ws["A1"].font = TITULO

    inicio, fim = vendas["data"].min(), vendas["data"].max()
    ws["A2"] = (
        f"De {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}. {len(vendas)} vendas de {len(dados.arquivos)} "
        f"{'arquivo' if len(dados.arquivos) == 1 else 'arquivos'}."
    )
    avisos = []
    if len(dados.descartadas):
        avisos.append(f"{len(dados.descartadas)} linhas ficaram de fora. O motivo de cada uma está na aba Descartadas.")
    if dados.repetidas:
        avisos.append(f"{dados.repetidas} linhas são idênticas à linha de cima no arquivo original. Foram mantidas e estão marcadas na aba Vendas.")
    for i, aviso in enumerate(avisos, start=3):
        ws.cell(row=i, column=1, value=aviso)

    linha = 6
    ws.cell(row=linha, column=1, value="Faturamento por loja").font = SECAO
    cabecalho(ws, linha + 1, ["Loja", "Vendas", "Itens", "Faturamento", "% do total"])
    primeira = linha + 2
    ultima = primeira + len(dados.por_loja) - 1
    total = ultima + 1
    for i, r in enumerate(dados.por_loja.itertuples(), start=primeira):
        escrever(ws, i, 1, r.loja)
        escrever(ws, i, 2, int(r.vendas), "#,##0")
        escrever(ws, i, 3, float(r.itens), "#,##0")
        escrever(ws, i, 4, round(float(r.faturamento), 2), MOEDA)
        escrever(ws, i, 5, f"=D{i}/D${total}", PORCENTAGEM)
    escrever(ws, total, 1, "Total")
    escrever(ws, total, 2, f"=SUM(B{primeira}:B{ultima})", "#,##0")
    escrever(ws, total, 3, f"=SUM(C{primeira}:C{ultima})", "#,##0")
    escrever(ws, total, 4, f"=SUM(D{primeira}:D{ultima})", MOEDA)
    escrever(ws, total, 5, f"=D{total}/D${total}", PORCENTAGEM)
    for coluna in range(1, 6):
        ws.cell(row=total, column=coluna).font = NEGRITO
        ws.cell(row=total, column=coluna).border = LINHA_TOTAL

    linha = total + 3
    ws.cell(row=linha, column=1, value="Faturamento por mês").font = SECAO
    lojas = list(dados.por_mes.columns)
    cabecalho(ws, linha + 1, ["Mês", *lojas, "Total"])
    primeira = linha + 2
    for i, (mes, valores) in enumerate(dados.por_mes.iterrows(), start=primeira):
        escrever(ws, i, 1, mes.to_pydatetime(), "MMM/YYYY").alignment = Alignment(horizontal="left")
        for coluna, loja in enumerate(lojas, start=2):
            escrever(ws, i, coluna, round(float(valores[loja]), 2), MOEDA)
        fim_linha = get_column_letter(len(lojas) + 1)
        escrever(ws, i, len(lojas) + 2, f"=SUM(B{i}:{fim_linha}{i})", MOEDA).font = NEGRITO
    ultima = primeira + len(dados.por_mes) - 1

    if lojas and len(dados.por_mes):
        grafico = BarChart()
        grafico.type = "col"
        grafico.title = "Faturamento por mês"
        grafico.y_axis.numFmt = '"R$" #,##0'
        grafico.y_axis.majorGridlines = None
        grafico.height, grafico.width = 8, 16
        grafico.add_data(Reference(ws, min_col=2, max_col=len(lojas) + 1, min_row=primeira - 1, max_row=ultima), titles_from_data=True)
        grafico.set_categories(Reference(ws, min_col=1, min_row=primeira, max_row=ultima))
        ws.add_chart(grafico, "H7")

    linha = ultima + 3
    ws.cell(row=linha, column=1, value="Faturamento por categoria").font = SECAO
    cabecalho(ws, linha + 1, ["Categoria", "Faturamento", "% do total"])
    primeira = linha + 2
    ultima = primeira + len(dados.por_categoria) - 1
    for i, r in enumerate(dados.por_categoria.itertuples(), start=primeira):
        escrever(ws, i, 1, r.categoria)
        escrever(ws, i, 2, round(float(r.faturamento), 2), MOEDA)
        escrever(ws, i, 3, f"=B{i}/SUM(B${primeira}:B${ultima})", PORCENTAGEM)

    linha = ultima + 3
    ws.cell(row=linha, column=1, value="10 produtos com maior faturamento").font = SECAO
    cabecalho(ws, linha + 1, ["Produto", "Categoria", "Quantidade", "Faturamento"])
    for i, r in enumerate(dados.top_produtos.itertuples(), start=linha + 2):
        escrever(ws, i, 1, r.produto)
        escrever(ws, i, 2, r.categoria).alignment = Alignment(horizontal="right")
        escrever(ws, i, 3, float(r.quantidade), "#,##0")
        escrever(ws, i, 4, round(float(r.faturamento), 2), MOEDA)

    for coluna, largura in zip("ABCDE", (34, 22, 14, 16, 14), strict=True):
        ws.column_dimensions[coluna].width = largura
    for coluna in range(6, len(lojas) + 3):
        ws.column_dimensions[get_column_letter(coluna)].width = 16


def tabela(ws: Worksheet, nome: str, nomes: list[str], linhas: int, larguras: list[int]) -> None:
    cabecalho(ws, 1, nomes)
    for coluna, largura in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(coluna)].width = largura
    ws.freeze_panes = "A2"
    if linhas:
        ref = f"A1:{get_column_letter(len(nomes))}{linhas + 1}"
        excel = Table(displayName=nome, ref=ref)
        excel.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
        ws.add_table(excel)


def aba_vendas(ws: Worksheet, vendas: pd.DataFrame) -> None:
    nomes = ["Loja", "Data", "Produto", "Categoria", "Quantidade", "Preço unitário", "Total", "Arquivo", "Linha no arquivo", "Conferir"]
    tabela(ws, "Vendas", nomes, len(vendas), [16, 12, 34, 22, 12, 15, 14, 30, 16, 12])
    for i, r in enumerate(vendas.itertuples(), start=2):
        escrever(ws, i, 1, r.loja)
        escrever(ws, i, 2, r.data.to_pydatetime(), DATA)
        escrever(ws, i, 3, r.produto)
        escrever(ws, i, 4, r.categoria)
        escrever(ws, i, 5, float(r.quantidade))
        escrever(ws, i, 6, float(r.preco), MOEDA)
        escrever(ws, i, 7, float(r.total), MOEDA)
        escrever(ws, i, 8, r.arquivo)
        escrever(ws, i, 9, int(r.linha))
        if r.repetida:
            escrever(ws, i, 10, "repetida").fill = CONFERIR


def aba_descartadas(ws: Worksheet, descartadas: pd.DataFrame) -> None:
    tabela(ws, "Descartadas", ["Arquivo", "Linha", "Motivo", "Conteúdo da linha"], len(descartadas), [30, 8, 58, 80])
    for i, r in enumerate(descartadas.itertuples(), start=2):
        escrever(ws, i, 1, r.arquivo)
        escrever(ws, i, 2, int(r.linha))
        escrever(ws, i, 3, r.motivo)
        escrever(ws, i, 4, r.conteudo)


def gerar_relatorio(dados: Consolidado) -> bytes:
    livro = Workbook()
    aba_resumo(livro.active, dados)
    aba_vendas(livro.create_sheet("Vendas"), dados.vendas)
    aba_descartadas(livro.create_sheet("Descartadas"), dados.descartadas)
    saida = BytesIO()
    livro.save(saida)
    return saida.getvalue()
