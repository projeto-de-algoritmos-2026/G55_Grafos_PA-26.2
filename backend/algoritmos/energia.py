"""Calculo do mapa de energia da imagem.

A energia de cada pixel define o peso das arestas do grafo usado pelo
seam carving. Pixels com energia alta pertencem a regioes de detalhe
e devem ser preservados; pixels com energia baixa sao candidatos a
remocao. As bordas sao tratadas com vizinhanca circular (wrap-around),
convencao da especificacao classica do algoritmo.
"""

import numpy as np


def _validar_imagem(imagem: np.ndarray) -> None:
    """Valida o formato esperado de uma imagem RGB.

    Parametros:
        imagem: array que deve ter formato (H, W, 3) com H >= 3 e W >= 3.

    Retorno:
        None. Levanta ValueError se o formato for invalido.

    Complexidade:
        O(1).
    """
    if imagem.ndim != 3:
        raise ValueError("a imagem deve ter 3 dimensoes no formato (H, W, 3)")
    if imagem.shape[2] != 3:
        raise ValueError("o ultimo eixo da imagem deve ter tamanho 3 (canais RGB)")
    if imagem.shape[0] < 3 or imagem.shape[1] < 3:
        raise ValueError("altura e largura da imagem devem ser no minimo 3")


def gradiente_dual(imagem: np.ndarray) -> np.ndarray:
    """Calcula o mapa de energia por gradiente dual com vizinhanca circular.

    Para cada pixel, a energia e a soma dos quadrados das diferencas
    entre os vizinhos horizontais e verticais em cada canal RGB:
    E(y, x) = dx_R^2 + dx_G^2 + dx_B^2 + dy_R^2 + dy_G^2 + dy_B^2.
    O vizinho a esquerda da coluna 0 e a ultima coluna, e o vizinho
    acima da linha 0 e a ultima linha (wrap-around via np.roll).

    Parametros:
        imagem: array float64 de formato (H, W, 3).

    Retorno:
        Array float64 de formato (H, W) com a energia de cada pixel.

    Complexidade:
        O(H * W).
    """
    _validar_imagem(imagem)
    imagem = np.asarray(imagem, dtype=np.float64)
    dx = np.roll(imagem, -1, axis=1) - np.roll(imagem, 1, axis=1)
    dy = np.roll(imagem, -1, axis=0) - np.roll(imagem, 1, axis=0)
    return np.sum(dx * dx, axis=2) + np.sum(dy * dy, axis=2)


_OPERADORES = {
    "dual": gradiente_dual,
}


def calcular_energia(imagem: np.ndarray, operador: str = "dual") -> np.ndarray:
    """Calcula o mapa de energia despachando para o operador escolhido.

    Parametros:
        imagem: array float64 de formato (H, W, 3).
        operador: nome do operador de energia. Valores validos: "dual".

    Retorno:
        Array float64 de formato (H, W) com a energia de cada pixel.
        Levanta ValueError para operador desconhecido.

    Complexidade:
        O(H * W).
    """
    if operador not in _OPERADORES:
        validos = ", ".join(sorted(_OPERADORES))
        raise ValueError(f"operador desconhecido: {operador!r}. Validos: {validos}")
    return _OPERADORES[operador](imagem)
