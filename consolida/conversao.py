import math
import re
import unicodedata
from datetime import date, datetime, timedelta

EXCEL_EPOCH = date(1899, 12, 30)
MILHAR = re.compile(r"^\d{1,3}(\.\d{3})+$")


def vazio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return isinstance(valor, str) and not valor.strip()


def texto(valor) -> str:
    if vazio(valor):
        return ""
    return " ".join(str(valor).split())


def chave(valor) -> str:
    # "  Hidráulica " e "HIDRAULICA" viram a mesma chave
    sem_acento = unicodedata.normalize("NFKD", texto(valor)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).split())


def numero(valor) -> float | None:
    if vazio(valor) or isinstance(valor, bool):
        return None
    if isinstance(valor, int | float):
        return None if math.isnan(valor) or math.isinf(valor) else float(valor)

    limpo = str(valor).replace("R$", "").replace("\xa0", "").replace(" ", "").strip()
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif MILHAR.match(limpo):
        limpo = limpo.replace(".", "")
    try:
        convertido = float(limpo)
    except ValueError:
        return None
    return None if math.isnan(convertido) or math.isinf(convertido) else convertido


def data(valor) -> date | None:
    if vazio(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, int | float) and not isinstance(valor, bool):
        # data sem formatacao aparece como numero de serie do Excel
        return EXCEL_EPOCH + timedelta(days=int(valor)) if 20000 < valor < 80000 else None

    bruto = texto(valor)
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(bruto, formato).date()
        except ValueError:
            continue
    return None
