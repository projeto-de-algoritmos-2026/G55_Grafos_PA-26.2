"""Testes da remocao de costuras e da reducao de largura."""

import numpy as np
import pytest

from backend.algoritmos.conectividade import componentes_conexos, validar_mascara
from backend.algoritmos.remocao import (
    ENERGIA_PROTEGER,
    _costuras_distintas,
    ampliar_largura,
    aplicar_mascara,
    reduzir_altura,
    reduzir_largura,
    reduzir_largura_otimizado,
    remover_objeto,
    remover_seam_vertical,
)
from backend.algoritmos.seam_dp import encontrar_seam_vertical


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


def test_reduzir_largura_otimizado_e_identico_a_referencia() -> None:
    gerador = np.random.default_rng(26)
    for _ in range(10):
        altura = int(gerador.integers(5, 16))
        largura = int(gerador.integers(7, 20))
        imagem = gerador.uniform(0.0, 255.0, size=(altura, largura, 3))
        esperado, _ = reduzir_largura(imagem, 3, "dual")
        resultado, _ = reduzir_largura_otimizado(imagem, 3, "dual")
        np.testing.assert_array_equal(resultado, esperado)


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


def test_aplicar_mascara_nao_modifica_entrada() -> None:
    """A energia original permanece intacta apos aplicar as mascaras."""
    energia = np.full((4, 6), 10.0)
    copia = energia.copy()
    remover = np.zeros((4, 6), dtype=bool)
    remover[1, 2] = True
    aplicar_mascara(energia, remover, np.zeros((4, 6), dtype=bool))
    np.testing.assert_array_equal(energia, copia)


def test_protecao_prevalece_sobre_remocao() -> None:
    """Pixel marcado nas duas mascaras recebe o valor de protecao."""
    energia = np.full((3, 3), 5.0)
    marcada = np.zeros((3, 3), dtype=bool)
    marcada[1, 1] = True
    resultado = aplicar_mascara(energia, marcada, marcada)
    assert resultado[1, 1] == ENERGIA_PROTEGER


def test_costura_atravessa_regiao_de_remocao() -> None:
    """Com mascara de remocao, a costura passa pela regiao marcada."""
    energia = np.full((5, 9), 100.0)
    remover = np.zeros((5, 9), dtype=bool)
    remover[2, 6] = True
    com_mascara = aplicar_mascara(energia, remover, np.zeros((5, 9), dtype=bool))
    seam = encontrar_seam_vertical(com_mascara)
    assert seam[2] == 6


def test_costura_evita_regiao_protegida() -> None:
    """Com mascara de protecao, a costura nao atravessa a regiao marcada."""
    energia = np.full((6, 10), 1.0)
    proteger = np.zeros((6, 10), dtype=bool)
    proteger[:, 3:6] = True
    com_mascara = aplicar_mascara(energia, np.zeros((6, 10), dtype=bool), proteger)
    seam = encontrar_seam_vertical(com_mascara)
    assert all(coluna not in (3, 4, 5) for coluna in seam)


def test_componentes_conexos_identifica_blocos() -> None:
    """Tres blocos separados sao reconhecidos como tres componentes."""
    mascara = np.zeros((10, 10), dtype=bool)
    mascara[0:2, 0:2] = True
    mascara[4:6, 5:8] = True
    mascara[8, 9] = True
    componentes = componentes_conexos(mascara)
    assert len(componentes) == 3
    tamanhos = sorted(len(componente) for componente in componentes)
    assert tamanhos == [1, 4, 6]


def test_validar_mascara_rejeita_vazia_e_larga_demais() -> None:
    """Mascara vazia e mascara acima de 80% da largura sao rejeitadas."""
    vazia = np.zeros((5, 10), dtype=bool)
    valido, motivo = validar_mascara(vazia, 10)
    assert not valido and "vazia" in motivo
    larga = np.zeros((5, 10), dtype=bool)
    larga[2, 0:9] = True
    valido, motivo = validar_mascara(larga, 10)
    assert not valido and "largura" in motivo
    aceitavel = np.zeros((5, 10), dtype=bool)
    aceitavel[2, 3:6] = True
    assert validar_mascara(aceitavel, 10) == (True, "")


def test_remover_objeto_elimina_retangulo_vermelho() -> None:
    """O retangulo vermelho some e a largura original e restaurada."""
    imagem = np.full((20, 30, 3), 128.0)
    imagem[6:14, 10:16] = [255.0, 0.0, 0.0]
    vermelhos_originais = int(np.all(imagem == [255.0, 0.0, 0.0], axis=2).sum())
    remover = np.zeros((20, 30), dtype=bool)
    remover[6:14, 10:16] = True
    resultado = remover_objeto(imagem, remover, np.zeros((20, 30), dtype=bool))
    vermelhos_finais = int(np.all(resultado == [255.0, 0.0, 0.0], axis=2).sum())
    assert resultado.shape == imagem.shape
    assert vermelhos_finais < 0.05 * vermelhos_originais