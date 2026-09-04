"""Caminho minimo vertical usando Dijkstra e heap binario."""

import heapq
import time

import numpy as np


def encontrar_seam_dijkstra(energia: np.ndarray) -> tuple[list[int], dict]:
    """Retorna a costura minima e metricas da busca de Dijkstra.

    O grafo possui um vertice fonte ligado a todos os pixels da primeira
    linha com o peso do pixel, e um vertice sumidouro ligado pelos pixels da
    ultima linha com peso zero. Cada pixel liga para ate tres pixels da
    linha seguinte, usando a energia do destino como peso.

    Retorna:
        Tupla com a costura vertical e um dicionario contendo
        ``vertices_visitados``, ``operacoes_heap`` e ``tempo_ms``.

    Complexidade:
        O(E log V) = O(H * W * log(H * W)).
    """
    energia = np.asarray(energia, dtype=np.float64)
    if energia.ndim != 2:
        raise ValueError("a energia deve ser uma matriz 2D")
    altura, largura = energia.shape
    if altura == 0 or largura == 0:
        raise ValueError("a matriz de energia nao pode ser vazia")

    inicio = time.perf_counter()
    fonte = altura * largura
    sumidouro = fonte + 1
    distancias = np.full(sumidouro + 1, np.inf, dtype=np.float64)
    anteriores = np.full(sumidouro + 1, -1, dtype=np.int64)
    finalizados = np.zeros(sumidouro + 1, dtype=bool)
    distancias[fonte] = 0.0
    heap: list[tuple[float, int]] = [(0.0, fonte)]
    operacoes_heap = 1
    vertices_visitados = 0

    while heap:
        distancia_atual, vertice = heapq.heappop(heap)
        operacoes_heap += 1
        if finalizados[vertice]:
            continue
        finalizados[vertice] = True
        vertices_visitados += 1
        if vertice == sumidouro:
            break

        if vertice == fonte:
            vizinhos = [
                (coluna, float(energia[0, coluna]))
                for coluna in range(largura)
            ]
        else:
            linha, coluna = divmod(vertice, largura)
            if linha == altura - 1:
                vizinhos = [(sumidouro, 0.0)]
            else:
                vizinhos = [
                    ((linha + 1) * largura + proxima_coluna,
                     float(energia[linha + 1, proxima_coluna]))
                    for proxima_coluna in range(max(0, coluna - 1), min(largura, coluna + 2))
                ]

        for vizinho, peso in vizinhos:
            nova_distancia = distancia_atual + peso
            if nova_distancia < distancias[vizinho]:
                distancias[vizinho] = nova_distancia
                anteriores[vizinho] = vertice
                heapq.heappush(heap, (nova_distancia, vizinho))
                operacoes_heap += 1

    vertice = int(anteriores[sumidouro])
    seam = [0] * altura
    while vertice != fonte:
        linha, coluna = divmod(vertice, largura)
        seam[linha] = coluna
        vertice = int(anteriores[vertice])

    metricas = {
        "vertices_visitados": vertices_visitados,
        "operacoes_heap": operacoes_heap,
        "tempo_ms": (time.perf_counter() - inicio) * 1000.0,
    }
    return seam, metricas