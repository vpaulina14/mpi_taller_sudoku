"""Tarea 1 - MPI por tableros: cada ID es una tarea que se asigna a un proceso.

Reparto dinámico: el rank 0 lleva la cola de IDs y entrega el siguiente a
cualquier proceso que quede libre (así los tableros lentos no dejan a otros
procesos esperando). El rank 0 también resuelve tableros; entre colocaciones
del backtracking atiende las peticiones de los demás.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mpi4py import MPI  # noqa: E402

from mpi_comun import bucle_global, cargar_seeds, resumen  # noqa: E402
from sudoku_ramas import resolver_cancelable  # noqa: E402


def resolver_un_proceso(tablero, extra):
    """Resuelve el tablero completo en este proceso (sin repartir ramas)."""
    resuelto = resolver_cancelable(tablero, extra, cada=500)
    return tablero if resuelto else None


def main():
    mundo = MPI.COMM_WORLD
    rank, n = mundo.Get_rank(), mundo.Get_size()

    parser = argparse.ArgumentParser(description="Sudoku con MPI: un tablero por proceso.")
    parser.add_argument("--archivo", type=Path,
                        default=Path(__file__).resolve().parents[1] / "seeds.txt")
    seleccion = parser.add_mutually_exclusive_group()
    seleccion.add_argument("--id", "--seed", dest="id")
    seleccion.add_argument("--all", action="store_true")
    args = parser.parse_args()

    seeds = cargar_seeds(mundo, args.archivo)
    if args.id:
        if args.id not in seeds:
            parser.error(f"ID '{args.id}' no existe. Disponibles: {', '.join(seeds)}")
        ids = [args.id]
    else:
        ids = list(seeds)

    mundo.Barrier()                      # todos listos: empieza el cronómetro
    lideres = list(range(n))             # cada proceso es su propio "grupo"
    salida = bucle_global(mundo, seeds, ids, lideres, resolver_un_proceso,
                          lambda: f"proceso {rank}")
    if rank == 0:
        resultados, total = salida
        resumen(resultados, total, n, "MPI por tableros")


if __name__ == "__main__":
    main()
