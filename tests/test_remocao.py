"""Testes da remocao de costuras e da reducao de largura."""

import numpy as np
import pytest

from backend.algoritmos.remocao import reduzir_largura, remover_seam_vertical


def test_remocao_preserva_ordem_dos_pixels() -> None:
    imagem = np.arange(4 * 5 * 3, dtype=float).reshape(4, 5, 3)
    seam = [1, 2, 2, 3]
    resultado = remover_seam_vertical(imagem, seam)
    esperado = np.stack([np.delete(imagem[linha], coluna, axis=0) for linha, coluna in enumerate(seam)])
    np.testing.assert_array_equal(resultado, esperado)


def test_reduzir_largura_remove_quantidade() -> None:
    imagem = np.zeros((6, 8, 3), dtype=float)
    resultado, costuras = reduzir_largura(imagem, 3)
    assert resultado.shape == (6, 5, 3)
    assert len(costuras) == 3


def test_quantidade_igual_a_largura_e_invalida() -> None:
    with pytest.raises(ValueError):
        reduzir_largura(np.zeros((4, 5, 3)), 5)


def test_remocao_uniforme_nao_inventa_cores() -> None:
    imagem = np.zeros((5, 7, 3), dtype=float)
    imagem[:, :3] = [255, 0, 0]
    imagem[:, 3:] = [0, 0, 255]
    resultado, _ = reduzir_largura(imagem, 2)
    cores = {tuple(cor) for cor in resultado.reshape(-1, 3)}
    assert cores <= {(255.0, 0.0, 0.0), (0.0, 0.0, 255.0)}