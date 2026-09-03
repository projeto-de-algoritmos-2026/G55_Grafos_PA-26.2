"""Testes da remocao de costuras e da reducao de largura."""

import numpy as np
import pytest

from backend.algoritmos.remocao import (
    _costuras_distintas,
    ampliar_largura,
    reduzir_altura,
    reduzir_largura,
    remover_seam_vertical,
)


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


def _imagem_aleatoria(altura: int, largura: int, semente: int = 3) -> np.ndarray:
    """Gera uma imagem RGB aleatoria e deterministica para os testes.

    Parametros:
        altura: numero de linhas.
        largura: numero de colunas.
        semente: semente do gerador aleatorio.

    Retorno:
        Array float64 de formato (altura, largura, 3).

    Complexidade:
        O(H * W).
    """
    gerador = np.random.default_rng(semente)
    return gerador.uniform(0.0, 255.0, size=(altura, largura, 3))


def test_reduzir_altura_preserva_largura() -> None:
    """Reduzir a altura em 3 mantem a largura e os canais intactos."""
    resultado, costuras = reduzir_altura(_imagem_aleatoria(9, 7), 3)
    assert resultado.shape == (6, 7, 3)
    assert len(costuras) == 3


def test_ampliar_largura_aumenta_na_quantidade() -> None:
    """Ampliar a largura em 5 produz largura original mais 5."""
    resultado = ampliar_largura(_imagem_aleatoria(8, 10), 5)
    assert resultado.shape == (8, 15, 3)


def test_costuras_da_ampliacao_sao_distintas() -> None:
    """Nenhuma coordenada original aparece em duas costuras diferentes."""
    imagem = _imagem_aleatoria(10, 12)
    costuras = _costuras_distintas(imagem, 6, "dual")
    assert len(costuras) == 6
    for linha in range(imagem.shape[0]):
        colunas_na_linha = [costura[linha] for costura in costuras]
        assert len(colunas_na_linha) == len(set(colunas_na_linha))


def test_ampliar_e_reduzir_retorna_dimensoes_originais() -> None:
    """Ampliar em k e depois reduzir em k volta as dimensoes originais."""
    imagem = _imagem_aleatoria(9, 11)
    ampliada = ampliar_largura(imagem, 4)
    reduzida, _ = reduzir_largura(ampliada, 4)
    assert reduzida.shape == imagem.shape


def test_ampliacao_uniforme_so_gera_cores_e_medias() -> None:
    """Ampliacao nao introduz cores fora do conjunto original e das medias."""
    imagem = np.zeros((6, 8, 3), dtype=float)
    imagem[:, :4] = [200.0, 0.0, 0.0]
    imagem[:, 4:] = [0.0, 0.0, 100.0]
    resultado = ampliar_largura(imagem, 3)
    permitidas = {(200.0, 0.0, 0.0), (0.0, 0.0, 100.0), (100.0, 0.0, 50.0)}
    cores = {tuple(cor) for cor in resultado.reshape(-1, 3)}
    assert cores <= permitidas


def test_ampliar_alem_da_largura_e_invalido() -> None:
    """Quantidade maior que a largura atual levanta ValueError."""
    with pytest.raises(ValueError):
        ampliar_largura(_imagem_aleatoria(5, 6), 7)