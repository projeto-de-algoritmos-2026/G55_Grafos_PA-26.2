"""Caminho vertical de menor energia em um DAG de pixels.

Cada pixel (y, x) e um vertice. As arestas ligam (y, x) a
(y + 1, x - 1), (y + 1, x) e (y + 1, x + 1), com peso igual a energia
do vertice de destino. Como todas as arestas avancam uma linha, a ordem
topologica e a ordem das linhas e a programacao dinamica resolve o DAG
em uma unica varredura, sem fila de prioridade.
"""

import numpy as np


def construir_tabela_custo(energia: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Retorna a tabela de custos acumulados e os predecessores escolhidos."""
    energia = np.asarray(energia, dtype=np.float64)
    if energia.ndim != 2:
        raise ValueError("a energia deve ser uma matriz 2D")
    altura, largura = energia.shape
    if altura == 0 or largura == 0:
        raise ValueError("a matriz de energia nao pode ser vazia")

    custos = np.empty((altura, largura), dtype=np.float64)
    retorno = np.full((altura, largura), -1, dtype=np.int64)
    custos[0] = energia[0]

    for linha in range(1, altura):
        vizinhos = np.full((3, largura), np.inf, dtype=np.float64)
        vizinhos[0, 1:] = custos[linha - 1, :-1]
        vizinhos[1] = custos[linha - 1]
        vizinhos[2, :-1] = custos[linha - 1, 1:]
        escolhidos = np.argmin(vizinhos, axis=0)
        custos[linha] = energia[linha] + vizinhos[escolhidos, np.arange(largura)]
        retorno[linha] = np.arange(largura) + escolhidos - 1

    return custos, retorno


def encontrar_seam_vertical(energia: np.ndarray) -> list[int]:
    """Retorna uma costura vertical de menor custo por backtracking."""
    custos, retorno = construir_tabela_custo(energia)
    seam = [0] * custos.shape[0]
    seam[-1] = int(np.argmin(custos[-1]))
    for linha in range(custos.shape[0] - 1, 0, -1):
        seam[linha - 1] = int(retorno[linha, seam[linha]])
    return seam


def custo_do_seam(energia: np.ndarray, seam: list[int]) -> float:
    """Soma a energia dos pixels percorridos pela costura."""
    energia = np.asarray(energia, dtype=np.float64)
    if energia.ndim != 2 or not validar_seam(seam, energia.shape[0], energia.shape[1]):
        raise ValueError("seam invalida para o formato da energia")
    return float(np.sum(energia[np.arange(energia.shape[0]), seam]))


def validar_seam(seam: list[int], altura: int, largura: int) -> bool:
    """Verifica comprimento, limites das colunas e conectividade da costura."""
    if len(seam) != altura or largura <= 0 or altura < 0:
        return False
    if any(coluna < 0 or coluna >= largura for coluna in seam):
        return False
    return all(abs(atual - anterior) <= 1 for anterior, atual in zip(seam, seam[1:]))