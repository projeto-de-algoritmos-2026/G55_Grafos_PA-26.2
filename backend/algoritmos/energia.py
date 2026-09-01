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


def _convoluir_wrap(canal: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Convolui um canal 2D com um kernel 3x3 usando bordas circulares.

    A convolucao e feita manualmente: para cada celula do kernel, o canal
    e deslocado com np.roll e acumulado ponderado pelo peso da celula.

    Parametros:
        canal: array float64 de formato (H, W).
        kernel: array de formato (3, 3) com os pesos ja refletidos.

    Retorno:
        Array float64 de formato (H, W) com o resultado da convolucao.

    Complexidade:
        O(H * W), pois o kernel tem tamanho constante.
    """
    resultado = np.zeros_like(canal)
    for desloc_y in (-1, 0, 1):
        for desloc_x in (-1, 0, 1):
            peso = kernel[desloc_y + 1, desloc_x + 1]
            if peso != 0:
                deslocado = np.roll(canal, (-desloc_y, -desloc_x), axis=(0, 1))
                resultado += peso * deslocado
    return resultado


def sobel(imagem: np.ndarray) -> np.ndarray:
    """Calcula o mapa de energia pelo operador de Sobel com bordas circulares.

    Aplica os kernels de Sobel 3x3 horizontal e vertical em cada canal RGB,
    calcula a magnitude do gradiente de cada canal e soma as magnitudes
    dos tres canais.

    Parametros:
        imagem: array float64 de formato (H, W, 3).

    Retorno:
        Array float64 de formato (H, W) com a energia de cada pixel.

    Complexidade:
        O(H * W).
    """
    _validar_imagem(imagem)
    imagem = np.asarray(imagem, dtype=np.float64)
    kernel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    kernel_y = kernel_x.T
    energia = np.zeros(imagem.shape[:2], dtype=np.float64)
    for canal in range(3):
        gx = _convoluir_wrap(imagem[:, :, canal], kernel_x)
        gy = _convoluir_wrap(imagem[:, :, canal], kernel_y)
        energia += np.sqrt(gx * gx + gy * gy)
    return energia


def energia_para_imagem(energia: np.ndarray) -> np.ndarray:
    """Normaliza o mapa de energia para visualizacao em tons de cinza.

    Os valores sao escalados linearmente para o intervalo [0, 255] em uint8.
    Se a energia for constante (maximo igual ao minimo), retorna zeros para
    evitar divisao por zero.

    Parametros:
        energia: array float64 de formato (H, W).

    Retorno:
        Array uint8 de formato (H, W) com valores em [0, 255].

    Complexidade:
        O(H * W).
    """
    minimo = float(np.min(energia))
    maximo = float(np.max(energia))
    if maximo == minimo:
        return np.zeros(energia.shape, dtype=np.uint8)
    normalizada = (energia - minimo) / (maximo - minimo) * 255.0
    return normalizada.astype(np.uint8)


_OPERADORES = {
    "dual": gradiente_dual,
    "sobel": sobel,
}


def calcular_energia(imagem: np.ndarray, operador: str = "dual") -> np.ndarray:
    """Calcula o mapa de energia despachando para o operador escolhido.

    Parametros:
        imagem: array float64 de formato (H, W, 3).
        operador: nome do operador de energia. Valores validos: "dual" e "sobel".

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
