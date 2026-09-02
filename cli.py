"""Ferramenta de linha de comando para reducao de largura."""

import argparse
import time

from backend.algoritmos.energia import calcular_energia, energia_para_imagem
from backend.algoritmos.remocao import reduzir_largura
from backend.utils.imagem import carregar, limitar_resolucao, salvar


def main() -> None:
    parser = argparse.ArgumentParser(description="Redimensiona imagens com seam carving")
    parser.add_argument("entrada")
    parser.add_argument("saida")
    parser.add_argument("--largura", type=int, required=True)
    parser.add_argument("--energia", choices=["dual", "sobel"], default="dual")
    parser.add_argument("--mapa-energia")
    args = parser.parse_args()

    inicio = time.perf_counter()
    imagem = limitar_resolucao(carregar(args.entrada))
    if args.largura <= 0 or args.largura >= imagem.shape[1]:
        parser.error("--largura deve ser positiva e menor que a largura da imagem")
    if args.mapa_energia:
        salvar(energia_para_imagem(calcular_energia(imagem, args.energia))[:, :, None].repeat(3, axis=2), args.mapa_energia)

    quantidade = imagem.shape[1] - args.largura

    def mostrar_progresso(atual: int, total: int) -> None:
        print(f"Costuras removidas: {atual}/{total}", flush=True)

    resultado, _ = reduzir_largura(imagem, quantidade, args.energia, mostrar_progresso)
    salvar(resultado, args.saida)
    print(f"Concluido em {time.perf_counter() - inicio:.2f}s")


if __name__ == "__main__":
    main()