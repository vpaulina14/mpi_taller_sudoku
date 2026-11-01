"""Tarea 3 - MPI híbrido: reparto de IDs entre grupos + reparto de ramas dentro de cada grupo.

Los N procesos se dividen en G = N // tam_grupo grupos (tamaños que difieren
como máximo en 1). El líder de cada grupo (su proceso de menor rank) pide IDs
al coordinador global (rank 0, que es el líder del grupo 0) en cuanto queda
libre. Con el ID recibido, el grupo entero explora las ramas de ese tablero y
el líder informa del resultado.

  tam_grupo = 1      -> equivale a "MPI por tableros"
  tam_grupo >= N     -> un solo grupo: equivale a "MPI por ramas"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mpi4py import MPI  # noqa: E402

from mpi_comun import GrupoRamas, bucle_global, cargar_seeds, resumen  # noqa: E402


def repartir_en_grupos(n, tam_grupo, grupos=None):
    """Devuelve la lista de tamaños de grupo (suma n, diferencia máxima 1).
    Si se indica `grupos` se usa ese número de grupos; si no, n // tam_grupo."""
    g = min(n, grupos) if grupos else n // max(1, tam_grupo)
    g = max(1, g)
    base, resto = divmod(n, g)
    return [base + 1 if i < resto else base for i in range(g)]


def main():
    mundo = MPI.COMM_WORLD
    rank, n = mundo.Get_rank(), mundo.Get_size()

    parser = argparse.ArgumentParser(description="Sudoku con MPI: IDs por grupos + ramas dentro del grupo.")
    parser.add_argument("--archivo", type=Path,
                        default=Path(__file__).resolve().parents[1] / "seeds.txt")
    parser.add_argument("--tam-grupo", type=int, default=2,
                        help="tamaño deseado de cada grupo (por defecto: 2)")
    parser.add_argument("--grupos", type=int, default=None,
                        help="número de grupos (tiene prioridad sobre --tam-grupo)")
    parser.add_argument("--factor", type=int, default=8,
                        help="ramas mínimas por proceso del grupo (por defecto: 8)")
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

    tamanos = repartir_en_grupos(n, args.tam_grupo, args.grupos)
    inicios = [sum(tamanos[:i]) for i in range(len(tamanos))]
    color = max(i for i, inicio in enumerate(inicios) if inicio <= rank)
    comm_grupo = mundo.Split(color, rank)
    grupo = GrupoRamas(comm_grupo, factor=args.factor)

    if rank == 0:
        print(f"Grupos: {len(tamanos)} con tamaños {tamanos} (N={n})", flush=True)

    mundo.Barrier()                       # todos listos: empieza el cronómetro
    if comm_grupo.Get_rank() != 0:
        grupo.servir_miembro()
        return

    salida = bucle_global(mundo, seeds, ids, inicios,
                          lambda tablero, extra: grupo.resolver_lider(tablero, extra),
                          lambda: f"grupo {color} ({tamanos[color]} procesos)")
    grupo.cerrar()
    if rank == 0:
        resultados, total = salida
        resumen(resultados, total, n, f"MPI híbrido ({len(tamanos)} grupos)")


if __name__ == "__main__":
    main()
