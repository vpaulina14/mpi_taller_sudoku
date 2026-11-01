# Tarea 3: combinar tableros y ramas

Los N procesos se dividen en **grupos**. Los IDs se reparten entre los grupos (como en la tarea 1) y, dentro de cada
grupo, los procesos exploran ramas distintas del tablero asignado (como en la tarea 2).

## Cómo funciona

- **Grupos.** `MPI_Comm_split` crea G subcomunicadores contiguos. El tamaño de los grupos difiere como máximo en 1
  (p. ej. N=7, G=2 → grupos de 4 y 3). El proceso 0 de cada grupo es su **líder**.
- **Reparto de IDs (nivel global).** El rank 0 del mundo es el líder del grupo 0 y además el coordinador de la cola de IDs.
  Cada líder pide un ID cuando su grupo queda libre (reparto dinámico, como en la tarea 1).
- **Reparto de ramas (nivel de grupo).** Con el ID recibido, el líder genera las ramas (`--factor × tamaño_del_grupo`),
  las reparte cíclicamente entre los miembros de su grupo, explora la suya y espera a los demás. Si alguien encuentra la
  solución, el líder envía `STOP` solo a su grupo; los otros grupos siguen con sus tableros.
- **Coordinador sin quedarse bloqueado.** Mientras el rank 0 explora o espera a su grupo, atiende las peticiones de los demás
  líderes (mismo mecanismo de `tick` que en las otras tareas), así que ningún grupo espera por él.
- **Tiempo total:** reloj real del rank 0 desde el inicio del reparto hasta tener los 30 resultados.

### Cómo elegir el tamaño de los grupos

El tamaño es un compromiso entre dos efectos, y los dos extremos son las tareas anteriores:

| Opción | Equivale a | Ventaja | Costo |
| --- | --- | --- | --- |
| Grupos de 1 (G = N) | MPI por tableros | Sin comunicación dentro del tablero; balanceo dinámico | El tiempo de un tablero no baja; el último tablero largo deja procesos ociosos al final |
| Un solo grupo (G = 1) | MPI por ramas | Acorta cada tablero y el tramo final | Generar/enviar ramas y cancelar en **cada** tablero; ramas desiguales dejan procesos esperando |
| Grupos intermedios | Híbrido | Equilibra ambos: suficientes tableros en paralelo para amortiguar la desigualdad, y grupos pequeños que acortan la cola | Hay que ajustar G |

Criterio aplicado: se **mide** el tiempo total variando G entre 2 y N/2 (una ejecución por valor) y se elige el más rápido;
`../medir_informe.py` lo hace automáticamente y deja la tabla en `resultados_medicion.md`.
Con N pequeño (≤ 3) solo hay un grupo útil. Los valores medidos y la elección final están en `../INFORME.md`.

Parámetros: `--grupos G` (número de grupos) o `--tam-grupo S` (G = N // S, por defecto S = 2), y `--factor K`.

## Ejecutar con el contenedor

Desde la carpeta raíz del proyecto. Cambia `4` por el N elegido y `2` por el número de grupos elegido.

**macOS (Terminal)**

```
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_hibrido/mpi_hibrido.py --all --grupos 2
```

**Windows (PowerShell)**

```
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_hibrido/mpi_hibrido.py --all --grupos 2
```
