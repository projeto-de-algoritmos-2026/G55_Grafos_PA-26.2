"""Testes do mapa de energia (gradiente dual, Sobel e normalizacao)."""

import numpy as np
import pytest

from backend.algoritmos.energia import (
    calcular_energia,
    energia_para_imagem,
    gradiente_dual,
)

# Imagem classica 3x4.png do assignment de Princeton (4 linhas x 3 colunas),
# no formato [linha][coluna] = (R, G, B).
IMAGEM_REFERENCIA = np.array(
    [
        [(255, 101, 51), (255, 101, 153), (255, 101, 255)],
        [(255, 153, 51), (255, 153, 153), (255, 153, 255)],
        [(255, 203, 51), (255, 204, 153), (255, 205, 255)],
        [(255, 255, 51), (255, 255, 153), (255, 255, 255)],
    ],
    dtype=np.float64,
)

# Energia esperada com vizinhanca circular, verificada pixel a pixel a mao.
ENERGIA_REFERENCIA = np.array(
    [
        [20808.0, 52020.0, 20808.0],
        [20808.0, 52225.0, 21220.0],
        [20809.0, 52024.0, 20809.0],
        [20808.0, 52225.0, 21220.0],
    ],
    dtype=np.float64,
)


def test_gradiente_dual_matriz_de_referencia() -> None:
    """Compara a energia da imagem de referencia com os valores calculados a mao."""
    energia = gradiente_dual(IMAGEM_REFERENCIA)
    np.testing.assert_allclose(np.round(energia, 2), ENERGIA_REFERENCIA)


def test_imagem_uniforme_tem_energia_zero() -> None:
    """Imagem com todos os pixels iguais deve ter energia zero em todo pixel."""
    imagem = np.full((5, 6, 3), 100.0, dtype=np.float64)
    energia = gradiente_dual(imagem)
    assert np.all(energia == 0.0)


def test_borda_vertical_concentra_energia_na_transicao() -> None:
    """Metade preta e metade branca: energia alta so nas colunas da transicao.

    Com vizinhanca circular ha duas transicoes: entre as colunas 3 e 4 e,
    pelo wrap-around, entre as colunas 7 e 0. A energia nessas colunas e
    3 * 255^2 (um salto de 255 em cada canal), e zero nas demais.
    """
    imagem = np.zeros((4, 8, 3), dtype=np.float64)
    imagem[:, 4:, :] = 255.0
    energia = gradiente_dual(imagem)
    energia_transicao = 3 * 255.0**2
    colunas_transicao = [0, 3, 4, 7]
    colunas_planas = [1, 2, 5, 6]
    assert np.all(energia[:, colunas_transicao] == energia_transicao)
    assert np.all(energia[:, colunas_planas] == 0.0)


def test_valida_numero_de_dimensoes() -> None:
    """Array sem 3 dimensoes deve levantar ValueError."""
    with pytest.raises(ValueError):
        gradiente_dual(np.zeros((5, 5), dtype=np.float64))


def test_valida_numero_de_canais() -> None:
    """Ultimo eixo com tamanho diferente de 3 deve levantar ValueError."""
    with pytest.raises(ValueError):
        gradiente_dual(np.zeros((5, 5, 4), dtype=np.float64))


def test_valida_dimensoes_minimas() -> None:
    """Altura ou largura menor que 3 deve levantar ValueError."""
    with pytest.raises(ValueError):
        gradiente_dual(np.zeros((2, 5, 3), dtype=np.float64))
    with pytest.raises(ValueError):
        gradiente_dual(np.zeros((5, 2, 3), dtype=np.float64))


def test_energia_para_imagem_normaliza_para_uint8() -> None:
    """A normalizacao deve retornar uint8 com valores dentro de [0, 255]."""
    energia = gradiente_dual(IMAGEM_REFERENCIA)
    visualizacao = energia_para_imagem(energia)
    assert visualizacao.dtype == np.uint8
    assert visualizacao.min() >= 0
    assert visualizacao.max() <= 255


def test_energia_para_imagem_trata_energia_constante() -> None:
    """Energia constante deve resultar em zeros, sem divisao por zero."""
    energia = np.full((4, 4), 7.5, dtype=np.float64)
    visualizacao = energia_para_imagem(energia)
    assert visualizacao.dtype == np.uint8
    assert np.all(visualizacao == 0)


@pytest.mark.parametrize("operador", ["dual", "sobel"])
def test_simetria_rotacao_180_graus(operador: str) -> None:
    """Girar a imagem 180 graus deve produzir o mapa de energia girado 180 graus."""
    gerador = np.random.default_rng(42)
    imagem = gerador.uniform(0.0, 255.0, size=(6, 7, 3))
    girada = imagem[::-1, ::-1, :]
    energia_da_girada = calcular_energia(girada, operador)
    energia_girada = calcular_energia(imagem, operador)[::-1, ::-1]
    np.testing.assert_allclose(energia_da_girada, energia_girada)


def test_calcular_energia_rejeita_operador_desconhecido() -> None:
    """Operador fora de 'dual' e 'sobel' deve levantar ValueError."""
    with pytest.raises(ValueError):
        calcular_energia(IMAGEM_REFERENCIA, "laplaciano")
