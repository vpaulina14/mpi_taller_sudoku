# Tarea 1: repartir tableros

Cada ID de `seeds.txt` es una tarea independiente que se asigna a un proceso MPI.
Se reutiliza el backtracking de `../sudoku.py` (a través de `../sudoku_ramas.py`, que es el mismo
algoritmo con un punto de cancelación) y los estados se reúnen en el proceso coordinador (rank 0).

## Cómo funciona

- **Reparto dinámico (maestro/trabajadores).** El rank 0 mantiene la cola de IDs y entrega el siguiente a
  cualquier proceso que quede libre. Así, un tablero lento no deja a otros procesos esperando
  (un reparto estático por bloques sí lo haría, porque los tableros duran entre ~2 y ~10 s).
- **El rank 0 también trabaja.** No hay un proceso dedicado a coordinar: mientras resuelve su tablero,
  cada ~500 colocaciones del backtracking atiende las peticiones pendientes de los demás
  (`Iprobe`). De esta forma los N procesos hacen búsqueda útil.
- **Comunicación mínima:** por tablero, 1 mensaje de petición/resultado (ID, estado, segundos) y 1 de asignación.
- **Tiempo total:** reloj real medido por el rank 0 desde que empieza el reparto hasta que han llegado los
  resultados de los 30 IDs. No se suman los tiempos de los procesos (esa suma se muestra solo como dato informativo).
- Cada resultado se valida (`es_solucion_valida`) antes de marcarlo como "Resuelto".

## Ejecutar con el contenedor

Desde la carpeta raíz del proyecto (la que contiene `seeds.txt`). Cambia `4` por el N elegido en la calibración.

**macOS (Terminal)**

```
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_por_tableros/mpi_tableros.py --all
```

**Windows (PowerShell)**

```
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_por_tableros/mpi_tableros.py --all
```

Un solo ID (solo para probar; con un tablero no hay nada que repartir): reemplaza `--all` por `--id 7`.
La salida muestra, por cada ID en cuanto termina, el estado, el tiempo parcial y qué proceso lo resolvió; al final,
`IDs procesados: 30 (resueltos: 30)` y `Tiempo total`.
