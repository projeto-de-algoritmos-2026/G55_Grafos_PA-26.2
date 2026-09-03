"""Remocao iterativa de costuras verticais."""

from typing import Callable, Optional

import numpy as np

from .energia import calcular_energia
from .seam_dp import encontrar_seam_vertical


def remover_seam_vertical(imagem: np.ndarray, seam: list[int]) -> np.ndarray:
    """Remove uma costura vertical da imagem com mascara booleana.

    Cada linha perde exatamente o pixel indicado pela costura, e os pixels
    remanescentes preservam a ordem original. A remocao usa mascara
    booleana e reshape, sem laco sobre linhas.

    Parametros:
        imagem: array de formato (H, W, 3).
        seam: lista de H colunas, uma por linha.

    Retorno:
        Array de formato (H, W - 1, 3). Levanta ValueError se a costura
        nao couber na imagem.

    Complexidade:
        O(H * W).
    """
    imagem = np.asarray(imagem)
    altura, largura = imagem.shape[:2]
    if len(seam) != altura or any(coluna < 0 or coluna >= largura for coluna in seam):
        raise ValueError("seam invalida para a imagem")
    mascara = np.ones((altura, largura), dtype=bool)
    mascara[np.arange(altura), seam] = False
    return imagem[mascara].reshape(altura, largura - 1, *imagem.shape[2:])


def _energia_para_tamanho_pequeno(imagem: np.ndarray, operador: str) -> np.ndarray:
    """Calcula a energia mesmo quando a imagem fica menor que 3x3.

    O calculo de energia exige dimensoes minimas de 3. Quando a reducao
    leva a imagem abaixo disso, as bordas sao replicadas ate o minimo,
    a energia e calculada e o resultado e recortado ao tamanho real.

    Parametros:
        imagem: array float64 de formato (H, W, 3).
        operador: nome do operador de energia ("dual" ou "sobel").

    Retorno:
        Matriz float64 de formato (H, W) com a energia de cada pixel.

    Complexidade:
        O(H * W).
    """
    altura, largura = imagem.shape[:2]
    if altura >= 3 and largura >= 3:
        return calcular_energia(imagem, operador)
    preenchimento = ((0, max(0, 3 - altura)), (0, max(0, 3 - largura)), (0, 0))
    imagem_ampliada = np.pad(imagem, preenchimento, mode="edge")
    return calcular_energia(imagem_ampliada, operador)[:altura, :largura]


def reduzir_largura(
    imagem: np.ndarray,
    quantidade: int,
    operador: str = "dual",
    progresso: Optional[Callable[[int, int], None]] = None,
) -> tuple[np.ndarray, list[list[int]]]:
    """Remove costuras verticais em sequencia, recalculando a energia.

    A cada iteracao a energia da imagem inteira e recalculada, a costura
    de menor custo e encontrada e removida. Versao de referencia; a
    otimizacao por faixa afetada fica para etapa futura.

    Parametros:
        imagem: array de formato (H, W, 3).
        quantidade: numero de costuras a remover.
        operador: nome do operador de energia ("dual" ou "sobel").
        progresso: funcao opcional chamada apos cada remocao com os
            argumentos (removidas, total).

    Retorno:
        Tupla com a imagem final de formato (H, W - quantidade, 3) e a
        lista das costuras removidas, na ordem. Levanta ValueError se
        quantidade for negativa ou maior ou igual a largura atual.

    Complexidade:
        O(k * H * W), onde k e a quantidade de costuras.
    """
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


def reduzir_altura(
    imagem: np.ndarray,
    quantidade: int,
    operador: str = "dual",
    progresso: Optional[Callable[[int, int], None]] = None,
) -> tuple[np.ndarray, list[list[int]]]:
    """Remove costuras horizontais reutilizando a reducao de largura.

    Implementacao por transposicao: os dois primeiros eixos sao trocados,
    reduzir_largura e aplicada e o resultado e transposto de volta. A
    escolha e correta porque uma costura horizontal da imagem original
    (um pixel por coluna, com passos de no maximo 1 entre colunas
    vizinhas) corresponde exatamente a uma costura vertical da imagem
    transposta, e os operadores de energia sao simetricos a transposicao
    dos eixos espaciais: transpor a imagem transpoe o mapa de energia.

    Parametros:
        imagem: array de formato (H, W, 3).
        quantidade: numero de costuras horizontais a remover.
        operador: nome do operador de energia ("dual" ou "sobel").
        progresso: funcao opcional chamada apos cada remocao com os
            argumentos (removidas, total).

    Retorno:
        Tupla com a imagem final de formato (H - quantidade, W, 3) e a
        lista das costuras removidas em coordenadas da transposta: o
        elemento x de cada costura e a linha ocupada na coluna x.
        Levanta ValueError se quantidade for negativa ou maior ou igual
        a altura atual.

    Complexidade:
        O(k * H * W), onde k e a quantidade de costuras.
    """
    transposta = np.transpose(np.asarray(imagem, dtype=np.float64), (1, 0, 2))
    reduzida, costuras = reduzir_largura(transposta, quantidade, operador, progresso)
    return np.transpose(reduzida, (1, 0, 2)), costuras
