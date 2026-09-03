"""Utilitarios de entrada, saida e controle de resolucao de imagens."""

from PIL import Image
import numpy as np


def carregar(caminho: str) -> np.ndarray:
    """Abre uma imagem do disco e a converte para array RGB.

    Parametros:
        caminho: caminho do arquivo de imagem.

    Retorno:
        Array float64 de formato (H, W, 3) com os pixels em RGB.

    Complexidade:
        O(H * W).
    """
    with Image.open(caminho) as imagem:
        return np.asarray(imagem.convert("RGB"), dtype=np.float64)


def salvar(imagem: np.ndarray, caminho: str) -> None:
    """Salva a imagem no disco apos limitar os pixels a [0, 255].

    Parametros:
        imagem: array de formato (H, W, 3).
        caminho: caminho do arquivo de saida.

    Retorno:
        None.

    Complexidade:
        O(H * W).
    """
    pixels = np.clip(np.asarray(imagem), 0, 255).astype(np.uint8)
    Image.fromarray(pixels, mode="RGB").save(caminho)


def limitar_resolucao(imagem: np.ndarray, maximo: int = 1024) -> np.ndarray:
    """Reduz proporcionalmente a imagem se a maior dimensao exceder o maximo.

    A reducao usa reamostragem simples por indexacao (vizinho mais
    proximo), suficiente para manter a responsividade da aplicacao.

    Parametros:
        imagem: array de formato (H, W, 3).
        maximo: maior dimensao permitida apos a reducao.

    Retorno:
        A propria imagem se ja couber no limite; caso contrario, uma nova
        imagem reduzida proporcionalmente.

    Complexidade:
        O(H * W).
    """
    altura, largura = imagem.shape[:2]
    maior = max(altura, largura)
    if maior <= maximo:
        return imagem
    escala = maximo / maior
    nova_altura = max(1, round(altura * escala))
    nova_largura = max(1, round(largura * escala))
    linhas = np.minimum((np.arange(nova_altura) / escala).astype(int), altura - 1)
    colunas = np.minimum((np.arange(nova_largura) / escala).astype(int), largura - 1)
    return imagem[np.ix_(linhas, colunas)]
