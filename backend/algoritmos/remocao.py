"""Remocao iterativa de costuras verticais."""

from typing import Callable, Optional

import numpy as np

from .energia import calcular_energia
from .seam_dp import encontrar_seam_vertical

# Valores finitos grandes em vez de infinito: somar infinito na recorrencia
# da tabela de custo acumulado pode gerar NaN (inf + (-inf)), enquanto
# valores finitos preservam a ordenacao relativa sem esse risco.
ENERGIA_REMOVER = -1e6
ENERGIA_PROTEGER = 1e6


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


def aplicar_mascara(
    energia: np.ndarray,
    mascara_remover: np.ndarray,
    mascara_proteger: np.ndarray,
) -> np.ndarray:
    """Aplica mascaras de remocao e protecao sobre o mapa de energia.

    Pixels marcados para remocao recebem ENERGIA_REMOVER (fortemente
    negativa, atraindo as costuras) e pixels protegidos recebem
    ENERGIA_PROTEGER (fortemente positiva, repelindo as costuras).
    Precedencia: se um pixel estiver nas duas mascaras, a protecao
    prevalece, pois e aplicada por ultimo. O array original nao e
    modificado.

    Parametros:
        energia: matriz float64 de formato (H, W).
        mascara_remover: matriz booleana de formato (H, W).
        mascara_proteger: matriz booleana de formato (H, W).

    Retorno:
        Nova matriz float64 com as energias substituidas. Levanta
        ValueError se os formatos nao coincidirem.

    Complexidade:
        O(H * W).
    """
    if energia.shape != mascara_remover.shape or energia.shape != mascara_proteger.shape:
        raise ValueError("as mascaras devem ter o mesmo formato da energia")
    resultado = energia.copy()
    resultado[mascara_remover] = ENERGIA_REMOVER
    resultado[mascara_proteger] = ENERGIA_PROTEGER
    return resultado


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


def _costuras_distintas(imagem: np.ndarray, quantidade: int, operador: str) -> list[list[int]]:
    """Encontra costuras verticais distintas em coordenadas originais.

    Trabalha sobre uma copia da imagem e um array de rastreamento (H, W)
    iniciado com np.arange por linha. A cada iteracao a costura de menor
    energia da copia e convertida para as colunas originais consultando o
    rastreamento, e entao removida da copia e do rastreamento. Como cada
    coluna original sai do rastreamento ao ser usada, nenhuma coordenada
    se repete entre costuras.

    Parametros:
        imagem: array float64 de formato (H, W, 3).
        quantidade: numero de costuras distintas desejadas.
        operador: nome do operador de energia ("dual" ou "sobel").

    Retorno:
        Lista de costuras em coordenadas da imagem original.

    Complexidade:
        O(k * H * W), onde k e a quantidade de costuras.
    """
    copia = imagem.copy()
    altura = imagem.shape[0]
    rastreamento = np.tile(np.arange(imagem.shape[1]), (altura, 1))
    linhas = np.arange(altura)
    costuras_originais = []
    for _ in range(quantidade):
        energia = _energia_para_tamanho_pequeno(copia, operador)
        seam = encontrar_seam_vertical(energia)
        costuras_originais.append(rastreamento[linhas, seam].tolist())
        mascara = np.ones(rastreamento.shape, dtype=bool)
        mascara[linhas, seam] = False
        copia = remover_seam_vertical(copia, seam)
        rastreamento = rastreamento[mascara].reshape(altura, -1)
    return costuras_originais


def _inserir_pixels(imagem: np.ndarray, costuras: list[list[int]]) -> np.ndarray:
    """Insere um pixel novo ao lado de cada coordenada marcada pelas costuras.

    Cada linha e processada uma unica vez com os indices ordenados
    (np.insert ja interpreta os indices em relacao a linha original, o
    que evita deslocamento acumulado incorreto). O pixel inserido e a
    media entre o pixel marcado e o vizinho da direita, ou da esquerda
    quando o marcado esta na ultima coluna.

    Parametros:
        imagem: array float64 de formato (H, W, 3).
        costuras: costuras em coordenadas originais, uma coluna por linha.

    Retorno:
        Array float64 de formato (H, W + len(costuras), 3).

    Complexidade:
        O(k * H + H * W), onde k e o numero de costuras.
    """
    altura, largura = imagem.shape[:2]
    linhas_novas = []
    for y in range(altura):
        colunas = np.sort(np.array([costura[y] for costura in costuras], dtype=np.int64))
        vizinhos = np.where(colunas < largura - 1, colunas + 1, colunas - 1)
        medias = (imagem[y, colunas] + imagem[y, vizinhos]) / 2.0
        linhas_novas.append(np.insert(imagem[y], colunas + 1, medias, axis=0))
    return np.stack(linhas_novas)


def ampliar_largura(imagem: np.ndarray, quantidade: int, operador: str = "dual") -> np.ndarray:
    """Aumenta a largura duplicando as costuras de menor energia.

    As costuras sao encontradas uma a uma sobre uma copia da imagem com
    rastreamento de indices originais, garantindo que nenhuma costura se
    repita (o que causaria uma faixa borrada). Depois, cada pixel marcado
    recebe ao lado um pixel novo com a media entre ele e o vizinho.

    Parametros:
        imagem: array de formato (H, W, 3).
        quantidade: numero de costuras a duplicar.
        operador: nome do operador de energia ("dual" ou "sobel").

    Retorno:
        Array float64 de formato (H, W + quantidade, 3). Levanta
        ValueError se quantidade for negativa ou exceder a largura atual,
        pois acima disso nao ha costuras distintas suficientes.

    Complexidade:
        O(k * H * W), onde k e a quantidade de costuras.
    """
    imagem = np.asarray(imagem, dtype=np.float64)
    if quantidade < 0 or quantidade > imagem.shape[1]:
        raise ValueError("quantidade nao pode exceder a largura atual")
    if quantidade == 0:
        return imagem.copy()
    costuras = _costuras_distintas(imagem, quantidade, operador)
    return _inserir_pixels(imagem, costuras)


def ampliar_altura(imagem: np.ndarray, quantidade: int, operador: str = "dual") -> np.ndarray:
    """Aumenta a altura duplicando costuras horizontais, por transposicao.

    Mesma justificativa de reduzir_altura: costuras horizontais da imagem
    original sao costuras verticais da transposta, e a energia e simetrica
    a transposicao dos eixos espaciais.

    Parametros:
        imagem: array de formato (H, W, 3).
        quantidade: numero de costuras horizontais a duplicar.
        operador: nome do operador de energia ("dual" ou "sobel").

    Retorno:
        Array float64 de formato (H + quantidade, W, 3). Levanta
        ValueError se quantidade for negativa ou exceder a altura atual.

    Complexidade:
        O(k * H * W), onde k e a quantidade de costuras.
    """
    transposta = np.transpose(np.asarray(imagem, dtype=np.float64), (1, 0, 2))
    return np.transpose(ampliar_largura(transposta, quantidade, operador), (1, 0, 2))
