from dataclasses import dataclass

from consolida.arquivo import ArquivoInvalido
from consolida.consolidar import Consolidado, consolidar
from consolida.leitura import ler_planilha, nome_seguro
from consolida.relatorio import gerar_relatorio

ARQUIVOS_MAXIMOS = 5


@dataclass
class Resultado:
    dados: Consolidado
    planilha: bytes


def processar(arquivos: list[tuple[str, bytes]]) -> Resultado:
    if not arquivos:
        raise ArquivoInvalido("nenhum arquivo enviado")
    if len(arquivos) > ARQUIVOS_MAXIMOS:
        raise ArquivoInvalido(f"envie no máximo {ARQUIVOS_MAXIMOS} arquivos por vez")

    lidos = []
    for posicao, (nome, conteudo) in enumerate(arquivos, start=1):
        try:
            lidos.append(ler_planilha(nome, conteudo, posicao))
        except ArquivoInvalido as erro:
            raise ArquivoInvalido(f"{nome_seguro(nome)}: {erro}") from erro

    if not any(lido.vendas for lido in lidos):
        raise ArquivoInvalido("nenhuma linha de venda válida nos arquivos enviados")

    dados = consolidar(lidos)
    return Resultado(dados, gerar_relatorio(dados))
