"""Ponto de entrada da aplicacao SeamCarver.

Define a instancia FastAPI, os endpoints da API, a configuracao de CORS
e o servico de arquivos estaticos do frontend.
"""

import io
from pathlib import Path
from typing import Dict

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from backend.utils.imagem import limitar_resolucao
from backend.utils.sessao import sessao

DIRETORIO_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
TAMANHO_MAXIMO_UPLOAD = 10 * 1024 * 1024

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


class RespostaErro(BaseModel):
    """Corpo padronizado das respostas de erro da API."""

    erro: str


class RespostaUpload(BaseModel):
    """Resposta do upload de imagem."""

    id: str
    largura: int
    altura: int


def _decodificar_imagem(dados: bytes) -> np.ndarray:
    """Decodifica os bytes de um arquivo de imagem para array RGB.

    Parametros:
        dados: conteudo bruto do arquivo enviado.

    Retorno:
        Array float64 de formato (H, W, 3). Levanta ValueError se o
        formato nao for suportado ou o arquivo estiver corrompido.

    Complexidade:
        O(H * W).
    """
    try:
        with Image.open(io.BytesIO(dados)) as imagem:
            return np.asarray(imagem.convert("RGB"), dtype=np.float64)
    except (UnidentifiedImageError, OSError) as excecao:
        raise ValueError("formato de imagem nao suportado ou arquivo corrompido") from excecao


def _codificar_png(imagem: np.ndarray) -> bytes:
    """Codifica um array RGB como PNG em memoria.

    Parametros:
        imagem: array de formato (H, W, 3).

    Retorno:
        Bytes do arquivo PNG.

    Complexidade:
        O(H * W).
    """
    pixels = np.clip(imagem, 0, 255).astype(np.uint8)
    saida = io.BytesIO()
    Image.fromarray(pixels, mode="RGB").save(saida, format="PNG")
    return saida.getvalue()


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


@app.post(
    "/api/imagem",
    response_model=RespostaUpload,
    responses={400: {"model": RespostaErro}, 413: {"model": RespostaErro}},
)
async def enviar_imagem(arquivo: UploadFile = File(...)) -> RespostaUpload:
    """Recebe uma imagem, registra na sessao e retorna id e dimensoes.

    A imagem e convertida para RGB e reduzida com limitar_resolucao para
    manter a responsividade; largura e altura retornadas sao as da imagem
    armazenada.

    Parametros:
        arquivo: campo multipart com o arquivo de imagem.

    Retorno:
        RespostaUpload com id, largura e altura. Erro 413 se o arquivo
        exceder 10 MB e 400 se o formato for invalido.

    Complexidade:
        O(H * W).
    """
    dados = await arquivo.read()
    if len(dados) > TAMANHO_MAXIMO_UPLOAD:
        raise HTTPException(status_code=413, detail="arquivo acima de 10 MB")
    imagem = limitar_resolucao(_decodificar_imagem(dados))
    identificador = sessao.registrar(imagem)
    return RespostaUpload(id=identificador, largura=imagem.shape[1], altura=imagem.shape[0])


@app.get(
    "/api/imagem/{identificador}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}, 404: {"model": RespostaErro}},
)
def obter_imagem(identificador: str) -> Response:
    """Devolve a imagem armazenada como PNG.

    Parametros:
        identificador: id retornado pelo upload.

    Retorno:
        Resposta image/png. Erro 404 se o id nao existir.

    Complexidade:
        O(H * W).
    """
    imagem = sessao.obter(identificador)
    return Response(content=_codificar_png(imagem), media_type="image/png")


app.mount("/", StaticFiles(directory=DIRETORIO_FRONTEND, html=True), name="frontend")
