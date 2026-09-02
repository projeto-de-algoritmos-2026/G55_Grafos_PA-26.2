"""Testes dos utilitarios de imagem e preservacao de conteudo."""

import numpy as np
from PIL import Image

from backend.algoritmos.remocao import reduzir_largura
from backend.utils.imagem import carregar, limitar_resolucao, salvar


def test_carregar_salvar_e_limitar_resolucao(tmp_path) -> None:
    imagem = np.full((8, 12, 3), 128.0)
    entrada = tmp_path / "entrada.png"
    saida = tmp_path / "saida.png"
    Image.fromarray(imagem.astype(np.uint8)).save(entrada)
    carregada = carregar(str(entrada))
    reduzida = limitar_resolucao(carregada, maximo=6)
    salvar(reduzida, str(saida))
    assert reduzida.shape == (4, 6, 3)
    assert Image.open(saida).size == (6, 4)


def test_reducao_preserva_retangulo_vermelho() -> None:
    imagem = np.full((20, 20, 3), 128.0)
    imagem[6:14, 7:13] = [255.0, 0.0, 0.0]
    quantidade_original = int(np.all(imagem == [255.0, 0.0, 0.0], axis=2).sum())
    reduzida, _ = reduzir_largura(imagem, 6)
    quantidade_final = int(np.all(reduzida == [255.0, 0.0, 0.0], axis=2).sum())
    assert abs(quantidade_final - quantidade_original) / quantidade_original <= 0.05