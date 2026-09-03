"""Ponto de entrada da aplicacao SeamCarver.

Define a instancia FastAPI, os endpoints da API, a configuracao de CORS
e o servico de arquivos estaticos do frontend.
"""

import base64
import io
import time
from pathlib import Path
from typing import Dict

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from backend.algoritmos.energia import calcular_energia, energia_para_imagem
from backend.algoritmos.remocao import reduzir_largura
from backend.algoritmos.seam_dp import custo_do_seam, encontrar_seam_vertical
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


class RespostaSeam(BaseModel):
    """Resposta da busca da costura de menor energia."""

    seam: list[int]
    custo: float
    orientacao: str


class RequisicaoRedimensionar(BaseModel):
    """Corpo da requisicao de redimensionamento."""

    id: str
    largura_alvo: int
    operador: str = "dual"


class RespostaRedimensionar(BaseModel):
    """Resposta do redimensionamento por seam carving."""

    imagem_base64: str
    largura: int
    altura: int
    costuras_removidas: int
    tempo_ms: float


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


@app.get(
    "/api/energia/{identificador}",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}}},
        400: {"model": RespostaErro},
        404: {"model": RespostaErro},
    },
)
def obter_mapa_energia(identificador: str, operador: str = "dual") -> Response:
    """Devolve o mapa de energia da imagem como PNG em tons de cinza.

    Parametros:
        identificador: id retornado pelo upload.
        operador: operador de energia ("dual" ou "sobel").

    Retorno:
        Resposta image/png com o mapa normalizado. Erro 400 para operador
        invalido e 404 se o id nao existir.

    Complexidade:
        O(H * W).
    """
    imagem = sessao.obter(identificador)
    mapa = energia_para_imagem(calcular_energia(imagem, operador))
    return Response(content=_codificar_png(mapa[:, :, None].repeat(3, axis=2)), media_type="image/png")


@app.get(
    "/api/seam/{identificador}",
    response_model=RespostaSeam,
    responses={400: {"model": RespostaErro}, 404: {"model": RespostaErro}},
)
def obter_seam(identificador: str, orientacao: str = "vertical", operador: str = "dual") -> RespostaSeam:
    """Calcula a costura de menor energia da imagem.

    Parametros:
        identificador: id retornado pelo upload.
        orientacao: orientacao da costura; apenas "vertical" e suportada.
        operador: operador de energia ("dual" ou "sobel").

    Retorno:
        RespostaSeam com as colunas da costura, o custo total e a
        orientacao. Erro 400 para orientacao ou operador invalidos e
        404 se o id nao existir.

    Complexidade:
        O(H * W).
    """
    if orientacao != "vertical":
        raise ValueError("orientacao invalida: apenas 'vertical' e suportada")
    imagem = sessao.obter(identificador)
    energia = calcular_energia(imagem, operador)
    seam = encontrar_seam_vertical(energia)
    return RespostaSeam(seam=seam, custo=custo_do_seam(energia, seam), orientacao=orientacao)


@app.post(
    "/api/redimensionar",
    response_model=RespostaRedimensionar,
    responses={400: {"model": RespostaErro}, 404: {"model": RespostaErro}},
)
def redimensionar(requisicao: RequisicaoRedimensionar) -> RespostaRedimensionar:
    """Reduz a largura da imagem removendo costuras de menor energia.

    Parametros:
        requisicao: id da imagem, largura alvo e operador de energia.

    Retorno:
        RespostaRedimensionar com o PNG em base64 (sem prefixo data:),
        dimensoes finais, numero de costuras removidas e tempo em ms.
        Erro 400 se a largura alvo for invalida (menor que 2 ou maior
        que a original) e 404 se o id nao existir.

    Complexidade:
        O(k * H * W), onde k e o numero de costuras removidas.
    """
    inicio = time.perf_counter()
    imagem = sessao.obter(requisicao.id)
    largura_atual = imagem.shape[1]
    if requisicao.largura_alvo < 2:
        raise ValueError("largura_alvo reduziria a imagem a menos de 2 colunas")
    if requisicao.largura_alvo > largura_atual:
        raise ValueError("largura_alvo maior que a largura original")
    quantidade = largura_atual - requisicao.largura_alvo
    resultado, costuras = reduzir_largura(imagem, quantidade, requisicao.operador)
    return RespostaRedimensionar(
        imagem_base64=base64.b64encode(_codificar_png(resultado)).decode("ascii"),
        largura=resultado.shape[1],
        altura=resultado.shape[0],
        costuras_removidas=len(costuras),
        tempo_ms=(time.perf_counter() - inicio) * 1000.0,
    )


app.mount("/", StaticFiles(directory=DIRETORIO_FRONTEND, html=True), name="frontend")
