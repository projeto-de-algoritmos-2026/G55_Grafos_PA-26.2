"""Testes do contrato da API."""

import base64
import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from backend.algoritmos.seam_dp import validar_seam
from backend.main import app

cliente = TestClient(app)


def _png_em_memoria(altura: int, largura: int) -> bytes:
    """Gera um PNG de teste com gradiente simples, em memoria.

    Parametros:
        altura: numero de linhas da imagem.
        largura: numero de colunas da imagem.

    Retorno:
        Bytes do arquivo PNG.

    Complexidade:
        O(H * W).
    """
    gerador = np.random.default_rng(0)
    pixels = gerador.integers(0, 256, size=(altura, largura, 3), dtype=np.uint8)
    saida = io.BytesIO()
    Image.fromarray(pixels).save(saida, format="PNG")
    return saida.getvalue()


def _enviar_imagem(altura: int = 30, largura: int = 20) -> dict:
    """Faz o upload de um PNG de teste e retorna o corpo da resposta.

    Parametros:
        altura: numero de linhas da imagem enviada.
        largura: numero de colunas da imagem enviada.

    Retorno:
        Dicionario com id, largura e altura.

    Complexidade:
        O(H * W).
    """
    arquivos = {"arquivo": ("teste.png", _png_em_memoria(altura, largura), "image/png")}
    resposta = cliente.post("/api/imagem", files=arquivos)
    assert resposta.status_code == 200
    return resposta.json()


def test_saude_retorna_status_ok() -> None:
    """Verifica que GET /api/saude responde 200 com o corpo esperado."""
    resposta = cliente.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "versao": "0.1.0"}


def test_upload_retorna_id_e_dimensoes() -> None:
    """Upload de PNG gerado em memoria retorna id, largura e altura corretos."""
    corpo = _enviar_imagem(altura=30, largura=20)
    assert isinstance(corpo["id"], str) and len(corpo["id"]) == 32
    assert corpo["largura"] == 20
    assert corpo["altura"] == 30


def test_upload_de_texto_retorna_400() -> None:
    """Upload de arquivo que nao e imagem retorna 400."""
    arquivos = {"arquivo": ("nota.txt", b"isto nao e uma imagem", "text/plain")}
    resposta = cliente.post("/api/imagem", files=arquivos)
    assert resposta.status_code == 400


def test_id_inexistente_retorna_404_padronizado() -> None:
    """GET de id inexistente retorna 404 com o corpo padronizado."""
    resposta = cliente.get("/api/imagem/nao-existe")
    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "imagem nao encontrada"}


def test_energia_devolve_png() -> None:
    """GET /api/energia devolve content-type image/png."""
    corpo = _enviar_imagem()
    resposta = cliente.get(f"/api/energia/{corpo['id']}")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "image/png"


def test_energia_com_operador_invalido_retorna_400() -> None:
    """Operador desconhecido em /api/energia retorna 400."""
    corpo = _enviar_imagem()
    resposta = cliente.get(f"/api/energia/{corpo['id']}", params={"operador": "laplaciano"})
    assert resposta.status_code == 400


def test_seam_tem_comprimento_e_limites_corretos() -> None:
    """A costura retornada tem um indice valido por linha da imagem."""
    corpo = _enviar_imagem(altura=25, largura=15)
    resposta = cliente.get(f"/api/seam/{corpo['id']}")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["orientacao"] == "vertical"
    assert validar_seam(dados["seam"], corpo["altura"], corpo["largura"])


def test_redimensionar_reduz_largura() -> None:
    """Reduzir 10 colunas devolve a largura correta e o PNG codificado."""
    corpo = _enviar_imagem(altura=20, largura=30)
    requisicao = {"id": corpo["id"], "largura_alvo": 20, "operador": "dual"}
    resposta = cliente.post("/api/redimensionar", json=requisicao)
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["largura"] == 20
    assert dados["altura"] == 20
    assert dados["costuras_removidas"] == 10
    assert dados["tempo_ms"] >= 0
    png = base64.b64decode(dados["imagem_base64"])
    assert Image.open(io.BytesIO(png)).size == (20, 20)


def test_redimensionar_com_largura_maior_retorna_400() -> None:
    """largura_alvo maior que a original retorna 400."""
    corpo = _enviar_imagem(altura=10, largura=12)
    requisicao = {"id": corpo["id"], "largura_alvo": 50, "operador": "dual"}
    resposta = cliente.post("/api/redimensionar", json=requisicao)
    assert resposta.status_code == 400


def test_redimensionar_para_uma_coluna_retorna_400() -> None:
    """largura_alvo igual a 1 retorna 400."""
    corpo = _enviar_imagem(altura=10, largura=12)
    requisicao = {"id": corpo["id"], "largura_alvo": 1, "operador": "dual"}
    resposta = cliente.post("/api/redimensionar", json=requisicao)
    assert resposta.status_code == 400
