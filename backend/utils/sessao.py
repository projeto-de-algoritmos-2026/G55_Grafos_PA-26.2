"""Armazenamento em memoria das imagens carregadas na aplicacao."""

import uuid

import numpy as np


class Sessao:
    """Guarda imagens por identificador, com limite de itens e descarte do
    mais antigo quando o limite e excedido. Nao persiste em disco."""

    def __init__(self, limite: int = 20) -> None:
        """Cria uma sessao vazia.

        Parametros:
            limite: numero maximo de imagens simultaneas.

        Retorno:
            None.

        Complexidade:
            O(1).
        """
        self._limite = limite
        self._imagens: dict[str, np.ndarray] = {}

    def registrar(self, imagem: np.ndarray) -> str:
        """Registra uma imagem e retorna seu identificador.

        Se o limite de itens for atingido, a imagem mais antiga e
        descartada antes do registro (dicts preservam ordem de insercao).

        Parametros:
            imagem: array de formato (H, W, 3).

        Retorno:
            Identificador uuid4 em hexadecimal.

        Complexidade:
            O(1).
        """
        if len(self._imagens) >= self._limite:
            mais_antigo = next(iter(self._imagens))
            del self._imagens[mais_antigo]
        identificador = uuid.uuid4().hex
        self._imagens[identificador] = imagem
        return identificador

    def obter(self, identificador: str) -> np.ndarray:
        """Retorna a imagem associada ao identificador.

        Parametros:
            identificador: id retornado por registrar.

        Retorno:
            Array de formato (H, W, 3). Levanta KeyError se ausente.

        Complexidade:
            O(1).
        """
        return self._imagens[identificador]

    def remover(self, identificador: str) -> None:
        """Remove a imagem associada ao identificador.

        Parametros:
            identificador: id retornado por registrar.

        Retorno:
            None. Levanta KeyError se ausente.

        Complexidade:
            O(1).
        """
        del self._imagens[identificador]


sessao = Sessao()
