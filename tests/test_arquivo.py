import zipfile
from io import BytesIO

import pytest

from consolida.arquivo import ArquivoInvalido, validar_xlsx


def zip_com(entradas: dict[str, bytes]) -> bytes:
    saida = BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as pacote:
        for nome, conteudo in entradas.items():
            pacote.writestr(nome, conteudo)
    return saida.getvalue()


def test_planilha_valida_passa(xlsx):
    validar_xlsx("vendas.xlsx", xlsx([["Data"]]))


@pytest.mark.parametrize(
    ("nome", "conteudo", "mensagem"),
    [
        ("vendas.xls", b"PK\x03\x04", "só aceito"),
        ("vendas.csv", b"data;produto", "só aceito"),
        ("vendas.xlsx", b"", "vazio"),
        ("vendas.xlsx", b"\xd0\xcf\x11\xe0" + b"0" * 100, "protegido por senha"),
        ("vendas.xlsx", b"PK\x03\x04 corrompido", "não é um .xlsx válido"),
    ],
    ids=["xls", "csv", "vazio", "com-senha", "zip-quebrado"],
)
def test_rejeita_arquivo(nome, conteudo, mensagem):
    with pytest.raises(ArquivoInvalido, match=mensagem):
        validar_xlsx(nome, conteudo)


def test_rejeita_arquivo_grande():
    with pytest.raises(ArquivoInvalido, match="maior que 1 MB"):
        validar_xlsx("vendas.xlsx", b"PK\x03\x04" + b"0" * (1024 * 1024))


def test_rejeita_zip_que_nao_e_planilha():
    with pytest.raises(ArquivoInvalido, match="não é um .xlsx válido"):
        validar_xlsx("vendas.xlsx", zip_com({"leia-me.txt": b"oi"}))


def test_rejeita_macro():
    conteudo = zip_com({"xl/workbook.xml": b"<workbook/>", "xl/vbaProject.bin": b"\x00"})
    with pytest.raises(ArquivoInvalido, match="macro"):
        validar_xlsx("vendas.xlsx", conteudo)


def test_rejeita_zip_bomb():
    # 40 MB de zeros viram poucos KB compactados
    conteudo = zip_com({"xl/workbook.xml": b"<workbook/>", "xl/worksheets/sheet1.xml": b"0" * (40 * 1024 * 1024)})
    assert len(conteudo) < 1024 * 1024
    with pytest.raises(ArquivoInvalido, match="grande demais"):
        validar_xlsx("vendas.xlsx", conteudo)


def test_openpyxl_le_xml_com_defusedxml():
    import openpyxl

    assert openpyxl.DEFUSEDXML is True
