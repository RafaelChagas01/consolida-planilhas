from consolida.conversao import chave

SINONIMOS = {
    "data": {"data", "data da venda", "data venda", "dt venda", "dia"},
    "produto": {"produto", "descricao", "descricao do produto", "item", "mercadoria"},
    "categoria": {"categoria", "grupo", "departamento", "secao"},
    "quantidade": {"quantidade", "qtd", "qtde", "quant"},
    "preco": {"preco", "preco unitario", "valor unit", "valor unitario", "vl unit", "vl unitario", "preco unit"},
    "total": {"total", "valor total", "vl total", "total da venda"},
    "loja": {"loja", "filial", "unidade"},
}
OBRIGATORIAS = {"data", "produto", "quantidade", "preco"}
LINHAS_PROCURADAS = 20

_POR_NOME = {nome: campo for campo, nomes in SINONIMOS.items() for nome in nomes}


def mapear(cabecalho: list) -> dict[str, int]:
    """Campo -> indice da coluna. Se o nome aparece duas vezes, vale a primeira."""
    mapa: dict[str, int] = {}
    for indice, valor in enumerate(cabecalho):
        campo = _POR_NOME.get(chave(valor))
        if campo and campo not in mapa:
            mapa[campo] = indice
    return mapa


def achar_cabecalho(linhas: list) -> tuple[int, dict[str, int]] | None:
    # tem planilha com titulo e linhas em branco antes do cabecalho
    for numero, linha in enumerate(linhas[:LINHAS_PROCURADAS]):
        mapa = mapear(linha)
        if OBRIGATORIAS <= mapa.keys():
            return numero, mapa
    return None
