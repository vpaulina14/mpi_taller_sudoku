# Tarea 2: repartir ramas de cada tablero

Con `--all` el rank 0 recorre los 30 IDs **en orden**. Para cada tablero reparte entre los N procesos las ramas
de su árbol de búsqueda y **espera a que termine antes de pasar al siguiente**: los tableros van en secuencia y las
ramas de cada uno en paralelo.

## Cómo funciona

1. **Generar ramas.** El coordinador toma las primeras casillas vacías del tablero y las expande con todos los
   valores válidos (nivel por nivel) hasta tener al menos `--factor × N` ramas (por defecto 8 por proceso). Como el
   backtracking de `sudoku.py` siempre rellena la primera casilla vacía, cada rama es exactamente un subárbol de la
   búsqueda serial: no se pierde ni se repite trabajo.
2. **Repartir.** Las ramas se asignan cíclicamente (rama `i` → proceso `i mod N`) y el coordinador se las envía.
   Hay más ramas que procesos para suavizar que unas ramas cuestan mucho más que otras.
3. **Explorar.** Cada proceso (rank 0 incluido) aplica backtracking a sus ramas.
4. **Cancelación.** Cuando un proceso halla la solución se la comunica al coordinador, que envía `STOP` a los demás;
   ellos consultan el buzón cada ~500 colocaciones (`Iprobe`) y abandonan la búsqueda de ese tablero. Si ninguna rama
   tiene solución, el tablero se reporta como "Sin solución".
5. **Siguiente ID.** Solo cuando han respondido todos los procesos el coordinador imprime el estado y el tiempo parcial
   del ID y comienza el siguiente.

El **tiempo total** es el reloj real del rank 0 desde el primer reparto hasta el último resultado.
Se conserva `--id` para resolver un solo tablero (aquí sí tiene sentido: se reparten sus ramas).

## Ejecutar con el contenedor

Desde la carpeta raíz del proyecto. Cambia `4` por el N elegido en la calibración.

**macOS (Terminal)**

```
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_por_ramas/mpi_ramas.py --id 7
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_por_ramas/mpi_ramas.py --all
```

**Windows (PowerShell)**

```
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_por_ramas/mpi_ramas.py --id 7
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_por_ramas/mpi_ramas.py --all
```

Opción extra: `--factor K` cambia cuántas ramas por proceso se generan (por defecto 8).

Los resultados de `--all` comparados con la versión secuencial se registran en `../INFORME.md`.
