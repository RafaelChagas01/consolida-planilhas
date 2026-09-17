from datetime import date, datetime

import pytest

from consolida.conversao import chave, data, numero, texto


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (12, 12.0),
        (19.9, 19.9),
        ("R$ 1.234,56", 1234.56),
        ("1234,5", 1234.5),
        ("1.234", 1234.0),
        ("12.5", 12.5),
        ("R$\xa036,90", 36.9),
        ("", None),
        ("abc", None),
        (None, None),
        (float("nan"), None),
        ("inf", None),
        (True, None),
    ],
)
def test_numero(entrada, esperado):
    assert numero(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (datetime(2026, 3, 5, 14, 30), date(2026, 3, 5)),
        (date(2026, 3, 5), date(2026, 3, 5)),
        ("05/03/2026", date(2026, 3, 5)),
        ("05/03/26", date(2026, 3, 5)),
        ("2026-03-05", date(2026, 3, 5)),
        (46086, date(2026, 3, 5)),
        ("31/02/2026", None),
        ("ontem", None),
        (3, None),
        ("", None),
    ],
)
def test_data(entrada, esperado):
    assert data(entrada) == esperado


def test_chave_ignora_acento_caixa_e_espacos():
    assert chave("  Hidráulica ") == chave("HIDRAULICA") == "hidraulica"
    assert chave("Valor Unit.") == "valor unit"


def test_texto_junta_espacos():
    assert texto("  Cimento   CP II ") == "Cimento CP II"
    assert texto(None) == ""
