"""Ponto de entrada da aplicacao SeamCarver.

Define a instancia FastAPI, os endpoints da API, a configuracao de CORS
e o servico de arquivos estaticos do frontend.
"""

import base64
import io
import logging
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from backend.algoritmos.energia import calcular_energia, energia_para_imagem
from backend.algoritmos.remocao import (
    ampliar_altura,
    ampliar_largura,
    reduzir_altura,
    reduzir_largura,
)
from backend.algoritmos.seam_dp import custo_do_seam, encontrar_seam_vertical
from backend.utils.imagem import limitar_resolucao
from backend.utils.sessao import sessao

DIRETORIO_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
TAMANHO_MAXIMO_UPLOAD = 10 * 1024 * 1024

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seamcarver")

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
    """Corpo da requisicao de redimensionamento.

    Alvos omitidos (None) mantem a dimensao correspondente."""

    id: str
    largura_alvo: Optional[int] = None
    altura_alvo: Optional[int] = None
    operador: str = "dual"


class RespostaRedimensionar(BaseModel):
    """Resposta do redimensionamento por seam carving."""

    imagem_base64: str
    largura: int
    altura: int
    costuras_removidas: int
    tempo_ms: float


def _registrar_log(operacao: str, identificador: str, inicio: float) -> None:
    """Registra id, operacao e duracao de uma chamada da API.

    Parametros:
        operacao: nome da operacao executada.
        identificador: id da imagem envolvida.
        inicio: instante inicial medido com time.perf_counter.

    Retorno:
        None.

    Complexidade:
        O(1).
    """
    duracao_ms = (time.perf_counter() - inicio) * 1000.0
    logger.info("operacao=%s id=%s duracao_ms=%.1f", operacao, identificador, duracao_ms)


@app.exception_handler(KeyError)
async def tratar_imagem_ausente(requisicao: Request, excecao: KeyError) -> JSONResponse:
    """Converte KeyError da sessao em HTTP 404 com corpo padronizado.

    Parametros:
        requisicao: requisicao que causou o erro.
        excecao: KeyError levantado pela sessao.

    Retorno:
        JSONResponse 404 com {"erro": "imagem nao encontrada"}.

    Complexidade:
        O(1).
    """
    return JSONResponse(status_code=404, content={"erro": "imagem nao encontrada"})


@app.exception_handler(ValueError)
async def tratar_entrada_invalida(requisicao: Request, excecao: ValueError) -> JSONResponse:
    """Converte ValueError dos algoritmos em HTTP 400 com a mensagem.

    Parametros:
        requisicao: requisicao que causou o erro.
        excecao: ValueError levantado pela validacao ou pelos algoritmos.

    Retorno:
        JSONResponse 400 com {"erro": mensagem}.

    Complexidade:
        O(1).
    """
    return JSONResponse(status_code=400, content={"erro": str(excecao)})


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
    inicio = time.perf_counter()
    dados = await arquivo.read()
    if len(dados) > TAMANHO_MAXIMO_UPLOAD:
        raise HTTPException(status_code=413, detail="arquivo acima de 10 MB")
    imagem = limitar_resolucao(_decodificar_imagem(dados))
    identificador = sessao.registrar(imagem)
    _registrar_log("upload", identificador, inicio)
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
    inicio = time.perf_counter()
    imagem = sessao.obter(identificador)
    resposta = Response(content=_codificar_png(imagem), media_type="image/png")
    _registrar_log("obter_imagem", identificador, inicio)
    return resposta


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
    inicio = time.perf_counter()
    imagem = sessao.obter(identificador)
    mapa = energia_para_imagem(calcular_energia(imagem, operador))
    resposta = Response(content=_codificar_png(mapa[:, :, None].repeat(3, axis=2)), media_type="image/png")
    _registrar_log("energia", identificador, inicio)
    return resposta


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
    inicio = time.perf_counter()
    if orientacao != "vertical":
        raise ValueError("orientacao invalida: apenas 'vertical' e suportada")
    imagem = sessao.obter(identificador)
    energia = calcular_energia(imagem, operador)
    seam = encontrar_seam_vertical(energia)
    _registrar_log("seam", identificador, inicio)
    return RespostaSeam(seam=seam, custo=custo_do_seam(energia, seam), orientacao=orientacao)


def _redimensionar_eixo(imagem: np.ndarray, alvo: int, eixo: str, operador: str) -> tuple[np.ndarray, int]:
    """Leva um eixo da imagem ate a dimensao alvo, reduzindo ou ampliando.

    Parametros:
        imagem: array float64 de formato (H, W, 3).
        alvo: dimensao final desejada para o eixo.
        eixo: "largura" ou "altura".
        operador: operador de energia ("dual" ou "sobel").

    Retorno:
        Tupla com a imagem resultante e o numero de costuras processadas.
        Levanta ValueError se o alvo for menor que 2 ou maior que o dobro
        da dimensao atual.

    Complexidade:
        O(k * H * W), onde k e o numero de costuras processadas.
    """
    atual = imagem.shape[1] if eixo == "largura" else imagem.shape[0]
    if alvo < 2:
        raise ValueError(f"{eixo}_alvo reduziria a imagem a menos de 2 pixels")
    if alvo > 2 * atual:
        raise ValueError(f"{eixo}_alvo nao pode exceder o dobro da {eixo} atual")
    quantidade = abs(alvo - atual)
    if quantidade == 0:
        return imagem, 0
    if alvo < atual:
        reduzir = reduzir_largura if eixo == "largura" else reduzir_altura
        resultado, costuras = reduzir(imagem, quantidade, operador)
        return resultado, len(costuras)
    ampliar = ampliar_largura if eixo == "largura" else ampliar_altura
    return ampliar(imagem, quantidade, operador), quantidade


@app.post(
    "/api/redimensionar",
    response_model=RespostaRedimensionar,
    responses={400: {"model": RespostaErro}, 404: {"model": RespostaErro}},
)
def redimensionar(requisicao: RequisicaoRedimensionar) -> RespostaRedimensionar:
    """Redimensiona a imagem em largura e altura por seam carving.

    Cada alvo pode ser maior (ampliacao) ou menor (reducao) que a
    dimensao atual; alvos omitidos mantem a dimensao. Quando ambos os
    eixos mudam, processa primeiro o eixo de maior variacao absoluta:
    assim as costuras mais numerosas sao escolhidas com a imagem ainda
    integra no outro eixo, preservando mais conteudo. Empate processa
    a largura primeiro.

    Parametros:
        requisicao: id da imagem, alvos de largura e altura e operador.

    Retorno:
        RespostaRedimensionar com o PNG em base64 (sem prefixo data:),
        dimensoes finais, total de costuras processadas e tempo em ms.
        Erro 400 para alvos invalidos e 404 se o id nao existir.

    Complexidade:
        O(k * H * W), onde k e o total de costuras processadas.
    """
    inicio = time.perf_counter()
    imagem = sessao.obter(requisicao.id)
    if requisicao.largura_alvo is None and requisicao.altura_alvo is None:
        raise ValueError("informe largura_alvo, altura_alvo ou ambos")
    alvo_largura = requisicao.largura_alvo if requisicao.largura_alvo is not None else imagem.shape[1]
    alvo_altura = requisicao.altura_alvo if requisicao.altura_alvo is not None else imagem.shape[0]
    eixos = [("largura", alvo_largura, abs(alvo_largura - imagem.shape[1])),
             ("altura", alvo_altura, abs(alvo_altura - imagem.shape[0]))]
    eixos.sort(key=lambda item: -item[2])
    total_costuras = 0
    for eixo, alvo, _ in eixos:
        imagem, processadas = _redimensionar_eixo(imagem, alvo, eixo, requisicao.operador)
        total_costuras += processadas
    _registrar_log("redimensionar", requisicao.id, inicio)
    return RespostaRedimensionar(
        imagem_base64=base64.b64encode(_codificar_png(imagem)).decode("ascii"),
        largura=imagem.shape[1],
        altura=imagem.shape[0],
        costuras_removidas=total_costuras,
        tempo_ms=(time.perf_counter() - inicio) * 1000.0,
    )


app.mount("/", StaticFiles(directory=DIRETORIO_FRONTEND, html=True), name="frontend")
