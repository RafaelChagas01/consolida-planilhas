import zipfile
from io import BytesIO

TAMANHO_MAXIMO = 1024 * 1024
DESCOMPACTADO_MAXIMO = 30 * 1024 * 1024
ENTRADAS_MAXIMAS = 300


class ArquivoInvalido(ValueError):
    pass


def validar_xlsx(nome: str, conteudo: bytes) -> None:
    """Confere o arquivo antes de entregar pro openpyxl. Mensagens podem ir direto pro usuario."""
    if not nome.lower().endswith(".xlsx"):
        raise ArquivoInvalido("só aceito arquivos .xlsx (Excel 2007 ou mais novo)")
    if not conteudo:
        raise ArquivoInvalido("arquivo vazio")
    if len(conteudo) > TAMANHO_MAXIMO:
        raise ArquivoInvalido("arquivo maior que 1 MB")
    # xlsx e um zip; .xls antigo e planilha com senha tem outro formato
    if not conteudo.startswith(b"PK\x03\x04"):
        raise ArquivoInvalido("não é um .xlsx válido (pode estar protegido por senha)")

    try:
        with zipfile.ZipFile(BytesIO(conteudo)) as pacote:
            entradas = pacote.infolist()
    except zipfile.BadZipFile as erro:
        raise ArquivoInvalido("não é um .xlsx válido") from erro

    # o zipfile nao descompacta alem do tamanho declarado, entao somar os tamanhos basta contra zip bomb
    if len(entradas) > ENTRADAS_MAXIMAS or sum(e.file_size for e in entradas) > DESCOMPACTADO_MAXIMO:
        raise ArquivoInvalido("conteúdo grande demais depois de descompactado")

    nomes = {e.filename.lower() for e in entradas}
    if "xl/workbook.xml" not in nomes:
        raise ArquivoInvalido("não é um .xlsx válido")
    if any(n.endswith("vbaproject.bin") for n in nomes):
        raise ArquivoInvalido("planilhas com macro não são aceitas")
