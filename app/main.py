import base64
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException

from app.ratelimit import SlidingWindow
from consolida.arquivo import TAMANHO_MAXIMO, ArquivoInvalido
from consolida.processar import ARQUIVOS_MAXIMOS, Resultado, processar

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("consolida")

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLOS = RAIZ / "exemplos"
NOMES_EXEMPLOS = sorted(p.name for p in EXEMPLOS.glob("*.xlsx"))
CORPO_MAXIMO = 4 * 1024 * 1024
DESCARTADAS_NA_TELA = 100

CABECALHOS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}

limite = SlidingWindow(limit=12, seconds=60)
app = FastAPI(title="Consolidador de planilhas", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def protecao(request: Request, call_next):
    if request.method == "POST":
        tamanho = request.headers.get("content-length", "")
        if not tamanho.isdigit():
            return JSONResponse({"erro": "requisição sem tamanho informado"}, status_code=411)
        if int(tamanho) > CORPO_MAXIMO:
            return JSONResponse({"erro": "envio maior que 4 MB"}, status_code=413)
    response = await call_next(request)
    for nome, valor in CABECALHOS.items():
        response.headers.setdefault(nome, valor)
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


def ip(request: Request) -> str:
    # na Vercel o IP real vem nesse header, preenchido pela propria plataforma
    encaminhado = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "")
    return encaminhado.split(",")[0].strip() or (request.client.host if request.client else "desconhecido")


def conferir_limite(request: Request) -> None:
    if not limite.allow(ip(request)):
        raise HTTPException(status_code=429, detail="Muitos envios seguidos. Espera um minuto.")


def resposta(resultado: Resultado) -> dict:
    dados = resultado.dados
    total = float(dados.por_loja["faturamento"].sum())
    return {
        "periodo": {"inicio": f"{dados.vendas['data'].min():%d/%m/%Y}", "fim": f"{dados.vendas['data'].max():%d/%m/%Y}"},
        "vendas": len(dados.vendas),
        "faturamento": round(total, 2),
        "arquivos": dados.arquivos,
        "lojas": [
            {"loja": r.loja, "vendas": int(r.vendas), "faturamento": round(float(r.faturamento), 2), "pct": round(100 * r.faturamento / total, 1)}
            for r in dados.por_loja.itertuples()
        ],
        "descartadas": [
            {"arquivo": r.arquivo, "linha": int(r.linha), "motivo": r.motivo} for r in dados.descartadas.head(DESCARTADAS_NA_TELA).itertuples()
        ],
        "total_descartadas": len(dados.descartadas),
        "repetidas": dados.repetidas,
        "planilha": base64.b64encode(resultado.planilha).decode(),
    }


async def rodar(arquivos: list[tuple[str, bytes]]) -> dict:
    try:
        resultado = await run_in_threadpool(processar, arquivos)
    except ArquivoInvalido as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return resposta(resultado)


@app.exception_handler(HTTPException)
async def erro_http(request: Request, exc: HTTPException):
    return JSONResponse({"erro": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, exc: Exception):
    log.exception("erro em %s", request.url.path)
    return JSONResponse({"erro": "Não consegui processar agora. Tenta de novo em instantes."}, status_code=500)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/consolidar")
async def consolidar_envio(request: Request):
    conferir_limite(request)
    try:
        formulario = await request.form(max_files=ARQUIVOS_MAXIMOS, max_fields=2)
    except MultiPartException as erro:
        raise HTTPException(status_code=400, detail="Envio inválido. Confere se são no máximo 5 arquivos.") from erro

    try:
        # campo escondido que pessoa nao preenche; bot costuma preencher tudo
        if formulario.get("site"):
            raise HTTPException(status_code=400, detail="Envio inválido.")
        enviados = [f for f in formulario.getlist("arquivos") if isinstance(f, UploadFile)]
        if not enviados:
            raise HTTPException(status_code=422, detail="Escolhe pelo menos uma planilha .xlsx.")

        arquivos = []
        for arquivo in enviados:
            conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)
            arquivos.append((arquivo.filename or "planilha.xlsx", conteudo))
    finally:
        await formulario.close()

    return await rodar(arquivos)


@app.post("/api/exemplo")
async def consolidar_exemplo(request: Request):
    conferir_limite(request)
    return await rodar([(nome, (EXEMPLOS / nome).read_bytes()) for nome in NOMES_EXEMPLOS])


@app.get("/api/exemplos/{nome}")
def baixar_exemplo(nome: str):
    if nome not in NOMES_EXEMPLOS:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(EXEMPLOS / nome, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=nome)


# na Vercel a pasta public e servida direto pela CDN
if not os.environ.get("VERCEL") and (RAIZ / "public").is_dir():
    app.mount("/", StaticFiles(directory=RAIZ / "public", html=True), name="public")
