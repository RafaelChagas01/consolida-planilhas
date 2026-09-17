from dataclasses import dataclass

import pandas as pd

from consolida.conversao import chave, texto
from consolida.leitura import ArquivoLido

COLUNAS_VENDAS = ["loja", "data", "produto", "categoria", "quantidade", "preco", "total", "arquivo", "linha"]


@dataclass
class Consolidado:
    vendas: pd.DataFrame
    descartadas: pd.DataFrame
    arquivos: list[dict]
    por_loja: pd.DataFrame
    por_mes: pd.DataFrame
    por_categoria: pd.DataFrame
    top_produtos: pd.DataFrame

    @property
    def repetidas(self) -> int:
        return int(self.vendas["repetida"].sum())


def _nome_mais_comum(df: pd.DataFrame, coluna: str) -> pd.Series:
    # cada loja escreve de um jeito ("HIDRAULICA", "Hidráulica "); fica a forma que mais aparece
    nomes = df[coluna].map(texto)
    chaves = nomes.map(chave)
    contagem = (
        pd.DataFrame({"chave": chaves, "nome": nomes})
        .value_counts()
        .reset_index(name="vezes")
        .sort_values(["chave", "vezes", "nome"], ascending=[True, False, False])
        .drop_duplicates("chave")
    )
    escolhido = dict(zip(contagem["chave"], contagem["nome"], strict=True))
    return chaves.map(lambda c: escolhido[c].capitalize() if escolhido[c].isupper() else escolhido[c])


def consolidar(lidos: list[ArquivoLido]) -> Consolidado:
    vendas = pd.DataFrame([v for lido in lidos for v in lido.vendas], columns=COLUNAS_VENDAS)
    descartadas = pd.DataFrame([d for lido in lidos for d in lido.descartadas], columns=["arquivo", "linha", "motivo", "conteudo"])

    if not vendas.empty:
        vendas["produto"] = _nome_mais_comum(vendas, "produto")
        vendas["categoria"] = _nome_mais_comum(vendas, "categoria")
    vendas["data"] = pd.to_datetime(vendas["data"])
    # linha identica a de cima costuma ser copia colada duas vezes, mas pode ser venda real: marca e mantem
    campos = ["loja", "data", "produto", "quantidade", "preco"]
    vendas = vendas.sort_values(["arquivo", "linha"], ignore_index=True)
    anterior = vendas.groupby("arquivo")[campos].shift(1)
    vendas["repetida"] = (vendas[campos] == anterior).all(axis=1)
    vendas = vendas.sort_values(["data", "loja", "arquivo", "linha"], ignore_index=True)

    por_loja = (
        vendas.groupby("loja")
        .agg(vendas=("total", "size"), itens=("quantidade", "sum"), faturamento=("total", "sum"))
        .sort_values("faturamento", ascending=False)
        .reset_index()
    )
    por_mes = vendas.assign(mes=vendas["data"].dt.to_period("M").dt.to_timestamp()).pivot_table(
        index="mes", columns="loja", values="total", aggfunc="sum", fill_value=0
    )
    por_mes = por_mes.reindex(columns=[c for c in por_loja["loja"] if c in por_mes.columns])
    por_categoria = vendas.groupby("categoria").agg(faturamento=("total", "sum")).sort_values("faturamento", ascending=False).reset_index()
    top_produtos = (
        vendas.groupby("produto")
        .agg(categoria=("categoria", "first"), quantidade=("quantidade", "sum"), faturamento=("total", "sum"))
        .sort_values("faturamento", ascending=False)
        .head(10)
        .reset_index()
    )

    arquivos = [{"arquivo": lido.arquivo, "loja": lido.loja, "vendas": len(lido.vendas), "descartadas": len(lido.descartadas)} for lido in lidos]
    return Consolidado(vendas, descartadas, arquivos, por_loja, por_mes, por_categoria, top_produtos)
