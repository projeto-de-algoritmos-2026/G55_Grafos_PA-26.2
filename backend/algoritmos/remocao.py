"""Remocao iterativa de costuras verticais."""

import numpy as np

from .energia import calcular_energia
from .seam_dp import encontrar_seam_vertical


def remover_seam_vertical(imagem: np.ndarray, seam: list[int]) -> np.ndarray:
    """Remove uma coluna por linha com mascara booleana."""
    imagem = np.asarray(imagem)
    altura, largura = imagem.shape[:2]
    if len(seam) != altura or any(coluna < 0 or coluna >= largura for coluna in seam):
        raise ValueError("seam invalida para a imagem")
    mascara = np.ones((altura, largura), dtype=bool)
    mascara[np.arange(altura), seam] = False
    return imagem[mascara].reshape(altura, largura - 1, *imagem.shape[2:])


def _energia_para_tamanho_pequeno(imagem: np.ndarray, operador: str) -> np.ndarray:
    """Mantem o calculo disponivel quando a reducao chega a uma borda minima."""
    altura, largura = imagem.shape[:2]
    if altura >= 3 and largura >= 3:
        return calcular_energia(imagem, operador)
    imagem_ampliada = np.pad(imagem, ((0, max(0, 3 - altura)), (0, max(0, 3 - largura)), (0, 0)), mode="edge")
    return calcular_energia(imagem_ampliada, operador)[:altura, :largura]


def reduzir_largura(imagem: np.ndarray, quantidade: int, operador: str = "dual", progresso=None) -> tuple[np.ndarray, list[list[int]]]:
    """Remove costuras, recalculando a energia completa a cada iteracao."""
    imagem_atual = np.asarray(imagem, dtype=np.float64)
    if quantidade < 0 or quantidade >= imagem_atual.shape[1]:
        raise ValueError("quantidade deve ser menor que a largura atual")
    costuras = []
    for indice in range(quantidade):
        energia = _energia_para_tamanho_pequeno(imagem_atual, operador)
        seam = encontrar_seam_vertical(energia)
        costuras.append(seam)
        imagem_atual = remover_seam_vertical(imagem_atual, seam)
        if progresso is not None:
            progresso(indice + 1, quantidade)
    return imagem_atual, costuras