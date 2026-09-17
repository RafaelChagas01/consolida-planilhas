"""Uso: python -m consolida exemplos/ -o fechamento.xlsx"""

import argparse
import sys
from pathlib import Path

from consolida.arquivo import ArquivoInvalido
from consolida.processar import processar


def main() -> int:
    parser = argparse.ArgumentParser(description="Junta planilhas de vendas de várias lojas num relatório só.")
    parser.add_argument("entradas", nargs="+", type=Path, help="arquivos .xlsx ou pastas com eles")
    parser.add_argument("-o", "--saida", type=Path, default=Path("fechamento.xlsx"))
    args = parser.parse_args()

    arquivos = []
    for entrada in args.entradas:
        arquivos.extend(sorted(entrada.glob("*.xlsx")) if entrada.is_dir() else [entrada])
    arquivos = [a for a in arquivos if not a.name.startswith("~$") and a.resolve() != args.saida.resolve()]
    if not arquivos:
        print("nenhum .xlsx encontrado", file=sys.stderr)
        return 1

    try:
        resultado = processar([(a.name, a.read_bytes()) for a in arquivos])
    except ArquivoInvalido as erro:
        print(erro, file=sys.stderr)
        return 1

    args.saida.write_bytes(resultado.planilha)
    for item in resultado.dados.arquivos:
        print(f"{item['arquivo']}: {item['vendas']} vendas, {item['descartadas']} descartadas (loja {item['loja']})")
    print(f"relatório salvo em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
