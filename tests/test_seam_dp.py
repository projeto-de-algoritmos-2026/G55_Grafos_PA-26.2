"""Testes do caminho minimo vertical em DAG."""

import numpy as np

from backend.algoritmos.seam_dp import construir_tabela_custo, custo_do_seam, encontrar_seam_vertical, validar_seam


def test_matriz_de_referencia() -> None:
    energia = np.array([[9, 9, 0, 9, 9], [9, 1, 9, 8, 9], [9, 9, 9, 9, 0], [9, 9, 9, 0, 9]], dtype=float)
    esperada = np.array([[9, 9, 0, 9, 9], [18, 1, 9, 8, 18], [10, 10, 10, 17, 8], [19, 19, 19, 8, 17]], dtype=float)
    custos, _ = construir_tabela_custo(energia)
    np.testing.assert_allclose(custos, esperada)
    seam = encontrar_seam_vertical(energia)
    assert seam == [2, 3, 4, 3]
    assert custo_do_seam(energia, seam) == 8.0


def test_energia_uniforme_apenas_valida_costura() -> None:
    seam = encontrar_seam_vertical(np.ones((6, 5)))
    assert validar_seam(seam, 6, 5)


def test_corredor_em_zigue_zague() -> None:
    corredor = [1, 2, 1, 2, 1]
    energia = np.full((5, 4), 100.0)
    energia[np.arange(5), corredor] = 0.0
    assert encontrar_seam_vertical(energia) == corredor


def test_imagem_de_uma_coluna() -> None:
    assert encontrar_seam_vertical(np.arange(12, dtype=float).reshape(12, 1)) == [0] * 12


def test_costuras_aleatorias_sao_validas() -> None:
    gerador = np.random.default_rng(42)
    for _ in range(20):
        altura = int(gerador.integers(1, 10))
        largura = int(gerador.integers(1, 10))
        seam = encontrar_seam_vertical(gerador.random((altura, largura)))
        assert validar_seam(seam, altura, largura)


def _todos_seams(energia: np.ndarray, linha: int, coluna: int, caminho: list[int]):
    caminho = caminho + [coluna]
    if linha == energia.shape[0] - 1:
        yield caminho
        return
    for proxima in range(max(0, coluna - 1), min(energia.shape[1], coluna + 2)):
        yield from _todos_seams(energia, linha + 1, proxima, caminho)


def test_otimalidade_contra_forca_bruta() -> None:
    gerador = np.random.default_rng(7)
    for _ in range(10):
        energia = gerador.integers(0, 100, size=(5, 5)).astype(float)
        minimo = min(custo_do_seam(energia, seam) for coluna in range(5) for seam in _todos_seams(energia, 0, coluna, []))
        assert custo_do_seam(energia, encontrar_seam_vertical(energia)) == minimo