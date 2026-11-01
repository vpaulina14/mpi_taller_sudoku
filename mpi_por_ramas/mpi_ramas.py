"""Tarea 2 - MPI por ramas: los IDs en orden; las ramas de cada tablero en paralelo.

El rank 0 (coordinador) recorre los IDs uno tras otro. Para cada tablero
genera ramas a partir de las primeras casillas vacías, las reparte entre los
N procesos (rank 0 incluido) y espera. Cuando un proceso halla la solución, el
coordinador envía STOP y los demás abandonan su búsqueda. Solo entonces pasa
al siguiente ID.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mpi4py import MPI  # noqa: E402

from mpi_comun import GrupoRamas, cargar_seeds  # noqa: E402
from sudoku_ramas import es_solucion_valida  # noqa: E402


def main():
    mundo = MPI.COMM_WORLD
    rank, n = mundo.Get_rank(), mundo.Get_size()

    parser = argparse.ArgumentParser(description="Sudoku con MPI: ramas de cada tablero en paralelo.")
    parser.add_argument("--archivo", type=Path,
                        default=Path(__file__).resolve().parents[1] / "seeds.txt")
    parser.add_argument("--factor", type=int, default=8,
                        help="ramas mínimas por proceso (por defecto: 8)")
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

    grupo = GrupoRamas(mundo, factor=args.factor)
    if rank != 0:
        grupo.servir_miembro()
        return

    acumulado = 0.0
    resueltos = 0
    inicio_total = time.perf_counter()
    for identificador in ids:
        original = seeds[identificador]
        inicio = time.perf_counter()
        solucion = grupo.resolver_lider([f[:] for f in original])
        segundos = time.perf_counter() - inicio
        resuelto = solucion is not None and es_solucion_valida(original, solucion)
        resueltos += resuelto
        acumulado += segundos
        print(f"\nID: {identificador}")
        print("Resuelto" if resuelto else "Sin solución")
        etiqueta = "Tiempo" if args.id else "Tiempo parcial"
        print(f"{etiqueta}: {segundos:.6f} segundos", flush=True)
    total = time.perf_counter() - inicio_total
    grupo.cerrar()

    print(f"\nIDs procesados: {len(ids)} (resueltos: {resueltos})")
    print(f"Procesos MPI: {n}  |  Estrategia: MPI por ramas")
    print(f"Tiempo total: {total:.6f} segundos", flush=True)


if __name__ == "__main__":
    main()
