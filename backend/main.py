"""Ponto de entrada da aplicacao SeamCarver.

Define a instancia FastAPI, o endpoint de saude, a configuracao de CORS
e o servico de arquivos estaticos do frontend.
"""

from pathlib import Path
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DIRETORIO_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="SeamCarver", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/saude")
def verificar_saude() -> Dict[str, str]:
    """Verifica se o servidor esta no ar.

    Parametros:
        Nenhum.

    Retorno:
        Dicionario com o status do servidor e a versao da aplicacao.

    Complexidade:
        O(1).
    """
    return {"status": "ok", "versao": "0.1.0"}


app.mount("/", StaticFiles(directory=DIRETORIO_FRONTEND, html=True), name="frontend")
