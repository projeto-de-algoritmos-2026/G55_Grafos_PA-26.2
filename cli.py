"""Ferramenta de linha de comando para reducao de largura.

Exemplos de uso:
    python cli.py entrada.jpg saida.jpg --largura 400
    python cli.py entrada.jpg saida.jpg --largura 400 --energia sobel
    python cli.py entrada.jpg saida.jpg --mapa-energia energia.png
"""

import argparse
import time

import numpy as np

from backend.algoritmos.energia import calcular_energia, energia_para_imagem
from backend.algoritmos.remocao import reduzir_largura
from backend.utils.imagem import carregar, limitar_resolucao, salvar


def _criar_parser() -> argparse.ArgumentParser:
    """Monta o parser de argumentos da linha de comando.

    Parametros:
        Nenhum.

    Retorno:
        Parser configurado com entrada, saida, largura alvo, operador de
        energia e caminho opcional do mapa de energia.

    Complexidade:
        O(1).
    """
    parser = argparse.ArgumentParser(description="Redimensiona imagens com seam carving")
    parser.add_argument("entrada", help="caminho da imagem de entrada")
    parser.add_argument("saida", help="caminho da imagem de saida")
    parser.add_argument("--largura", type=int, help="largura alvo em pixels")
    parser.add_argument("--energia", choices=["dual", "sobel"], default="dual", help="operador de energia")
    parser.add_argument("--mapa-energia", help="caminho para salvar o mapa de energia em tons de cinza")
    return parser


def _salvar_mapa_energia(imagem: np.ndarray, operador: str, caminho: str) -> None:
    """Salva o mapa de energia normalizado como imagem em tons de cinza.

    Parametros:
        imagem: array float64 de formato (H, W, 3).
        operador: nome do operador de energia ("dual" ou "sobel").
        caminho: caminho do arquivo de saida.

    Retorno:
        None.

    Complexidade:
        O(H * W).
    """
    mapa = energia_para_imagem(calcular_energia(imagem, operador))
    salvar(mapa[:, :, None].repeat(3, axis=2), caminho)


def main() -> None:
    """Executa o redimensionamento por seam carving via linha de comando.

    Le a imagem de entrada, opcionalmente exporta o mapa de energia,
    remove costuras ate a largura alvo exibindo o progresso e informa o
    tempo total ao final. Sem --largura, apenas copia a imagem e exporta
    o mapa de energia, se pedido.

    Parametros:
        Nenhum (argumentos vem da linha de comando).

    Retorno:
        None.

    Complexidade:
        O(k * H * W), onde k e o numero de costuras removidas.
    """
    parser = _criar_parser()
    args = parser.parse_args()
    if args.largura is None and not args.mapa_energia:
        parser.error("informe --largura, --mapa-energia ou ambos")

    inicio = time.perf_counter()
    imagem = limitar_resolucao(carregar(args.entrada))
    if args.mapa_energia:
        _salvar_mapa_energia(imagem, args.energia, args.mapa_energia)

    resultado = imagem
    if args.largura is not None:
        if args.largura <= 0 or args.largura >= imagem.shape[1]:
            parser.error("--largura deve ser positiva e menor que a largura da imagem")

        def mostrar_progresso(atual: int, total: int) -> None:
            print(f"Costuras removidas: {atual}/{total}", flush=True)

        quantidade = imagem.shape[1] - args.largura
        resultado, _ = reduzir_largura(imagem, quantidade, args.energia, mostrar_progresso)

    salvar(resultado, args.saida)
    print(f"Concluido em {time.perf_counter() - inicio:.2f}s")


if __name__ == "__main__":
    main()
