"""Componentes conexos por BFS para validacao de mascaras de pincel.

Cada pixel marcado da mascara e um vertice, e as arestas ligam vizinhos
nas 4 direcoes (cima, baixo, esquerda, direita). A BFS e implementada
manualmente com collections.deque, sem rotulacao de biblioteca.
"""

from collections import deque

import numpy as np

_DIRECOES = ((-1, 0), (1, 0), (0, -1), (0, 1))

LIMITE_COMPONENTES = 5
FRACAO_LARGURA_MAXIMA = 0.8


def _explorar_componente(
    mascara: np.ndarray,
    visitados: np.ndarray,
    origem: tuple[int, int],
) -> list[tuple[int, int]]:
    """Percorre por BFS o componente conexo que contem a origem.

    Parametros:
        mascara: matriz booleana de formato (H, W).
        visitados: matriz booleana de mesmo formato, atualizada no lugar.
        origem: coordenada (linha, coluna) inicial, ja marcada na mascara.

    Retorno:
        Lista de coordenadas (linha, coluna) do componente.

    Complexidade:
        O(V + E) sobre os pixels do componente.
    """
    altura, largura = mascara.shape
    fila = deque([origem])
    visitados[origem] = True
    componente = []
    while fila:
        linha, coluna = fila.popleft()
        componente.append((linha, coluna))
        for delta_linha, delta_coluna in _DIRECOES:
            vizinho = (linha + delta_linha, coluna + delta_coluna)
            if 0 <= vizinho[0] < altura and 0 <= vizinho[1] < largura:
                if mascara[vizinho] and not visitados[vizinho]:
                    visitados[vizinho] = True
                    fila.append(vizinho)
    return componente


def componentes_conexos(mascara: np.ndarray) -> list[list[tuple[int, int]]]:
    """Encontra os componentes conexos de uma mascara booleana.

    Cada pixel marcado e um vertice conectado aos vizinhos de 4 direcoes.

    Parametros:
        mascara: matriz booleana de formato (H, W).

    Retorno:
        Lista de componentes, cada um como lista de coordenadas
        (linha, coluna).

    Complexidade:
        O(V + E), onde V e o numero de pixels marcados e E o numero de
        adjacencias entre eles.
    """
    mascara = np.asarray(mascara, dtype=bool)
    visitados = np.zeros(mascara.shape, dtype=bool)
    componentes = []
    for linha, coluna in zip(*np.nonzero(mascara)):
        origem = (int(linha), int(coluna))
        if not visitados[origem]:
            componentes.append(_explorar_componente(mascara, visitados, origem))
    return componentes


def validar_mascara(mascara: np.ndarray, largura: int) -> tuple[bool, str]:
    """Valida uma mascara de remocao antes do processamento.

    A mascara e invalida se for vazia, se algum componente ocupar largura
    maior que 80% da largura da imagem, ou se houver mais de 5
    componentes desconexos.

    Parametros:
        mascara: matriz booleana de formato (H, W).
        largura: largura da imagem em pixels.

    Retorno:
        Tupla (valido, motivo); motivo e vazio quando a mascara e valida.

    Complexidade:
        O(V + E) sobre os pixels marcados.
    """
    mascara = np.asarray(mascara, dtype=bool)
    if not mascara.any():
        return False, "a mascara esta vazia"
    componentes = componentes_conexos(mascara)
    if len(componentes) > LIMITE_COMPONENTES:
        return False, f"a mascara tem mais de {LIMITE_COMPONENTES} regioes desconexas"
    for componente in componentes:
        colunas = [coluna for _, coluna in componente]
        if max(colunas) - min(colunas) + 1 > FRACAO_LARGURA_MAXIMA * largura:
            return False, "uma regiao da mascara ocupa mais de 80% da largura da imagem"
    return True, ""
