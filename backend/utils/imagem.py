"""Utilitarios de entrada, saida e controle de resolucao de imagens."""

from PIL import Image
import numpy as np


def carregar(caminho: str) -> np.ndarray:
    """Abre uma imagem RGB e retorna pixels float64 em (H, W, 3)."""
    with Image.open(caminho) as imagem:
        return np.asarray(imagem.convert("RGB"), dtype=np.float64)


def salvar(imagem: np.ndarray, caminho: str) -> None:
    """Salva a imagem depois de limitar seus pixels a [0, 255]."""
    pixels = np.clip(np.asarray(imagem), 0, 255).astype(np.uint8)
    Image.fromarray(pixels, mode="RGB").save(caminho)


def limitar_resolucao(imagem: np.ndarray, maximo: int = 1024) -> np.ndarray:
    """Reduz proporcionalmente a maior dimensao usando amostragem simples."""
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