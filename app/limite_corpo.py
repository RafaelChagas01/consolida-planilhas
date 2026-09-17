from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CorpoGrandeDemais(Exception):
    pass


class LimiteDeCorpo:
    """Recusa pelo Content-Length e, sem ele (envio em partes), conta os bytes enquanto chegam."""

    def __init__(self, app: ASGIApp, maximo: int):
        self.app = app
        self.maximo = maximo

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tamanho = dict(scope["headers"]).get(b"content-length")
        if tamanho is not None and (not tamanho.isdigit() or int(tamanho) > self.maximo):
            await JSONResponse({"erro": "envio maior que 4 MB"}, status_code=413)(scope, receive, send)
            return

        recebido = 0

        async def receber() -> Message:
            nonlocal recebido
            mensagem = await receive()
            if mensagem["type"] == "http.request":
                recebido += len(mensagem.get("body", b""))
                if recebido > self.maximo:
                    raise CorpoGrandeDemais
            return mensagem

        await self.app(scope, receber, send)
