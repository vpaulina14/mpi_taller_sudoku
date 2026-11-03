# Informe de resultados

## Entorno

- Equipo: Portátil Lenovo IdeaPad 5 14ALC05, procesador AMD Ryzen 7 5700U (8 núcleos / 16 hilos, 1,80 GHz base), 16 GB de RAM (15,3 GB usables), Windows 11 Home 25H2 (compilación 26200.9711), Docker Desktop 4.73.1 (Engine 29.4.3). El contenedor ve nproc = 16.
- Versión del contenedor: `augustosalazar/slim-mpi:2`
- Cantidad de repeticiones por medición: 3
- Valor común de `N` elegido: **13** (salida de `detectar_procesos_mpi.py`: "N RECOMENDADO: 13", mediana 1,512 s)
- Número de grupos del híbrido: **4** (grupos de 4, 3, 3 y 3 procesos), elegido por exploración

### Calibración de N (conteo de primos, mediana de 3 mediciones)

| N | 1 | 2 | 4 | 7 | 8 | 11 | 13 | 14 | 16 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tiempo (s) | 6,969 | 4,050 | 2,598 | 1,961 | 1,664 | 1,617 | **1,512** | 1,613 | 1,618 |

Con N=13 la tarea (que se reparte sin dependencias) pasó de 6,969 s a 1,512 s, es decir, el equipo acelera esa tarea **4,6 veces** como máximo aunque se le den 13 procesos. Ese valor es la referencia práctica de cuánta paralelización real ofrece este equipo.

## Comparación final con el mismo `N`

Tres ejecuciones por fila; mediana del "Tiempo total" (reloj real del coordinador, no suma de procesos). `mpiexec` con `--allow-run-as-root --use-hwthread-cpus --oversubscribe` en las tres implementaciones.

| Implementación | Caso | Procesos | Mediana del tiempo total (s) | Aceleración frente a secuencial |
| --- | --- | ---: | ---: | ---: |
| Secuencial | Todos los IDs | 1 | 105,67 | 1,00 |
| MPI por tableros | Todos los IDs | 13 | 30,55 | 3,46 |
| MPI por ramas | Todos los IDs, uno después de otro | 13 | 33,16 | 3,19 |
| MPI híbrido (4 grupos) | Todos los IDs | 13 | 26,71 | 3,96 |

Tiempos individuales (s):

- Secuencial: 110,374; 103,975; 105,666
- Por tableros: 29,453; 30,552; 31,484
- Por ramas: 33,155; 35,311; 32,440
- Híbrido: 26,713; 26,637; 28,366

Exploración del número de grupos del híbrido (1 ejecución cada uno):

| Grupos | 2 | 3 | 4 | 5 | 6 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tiempo total (s) | 27,05 | 30,67 | 23,13 | 24,89 | 27,99 |

Aceleración = tiempo secuencial / tiempo MPI. En los 30 tableros, todas las ejecuciones reportaron 30 IDs resueltos.

## Conclusiones

**1. Estrategia más rápida y mejora frente al secuencial.** El híbrido con 4 grupos obtuvo el menor tiempo: 26,71 s frente a 105,67 s del secuencial, una aceleración de 3,96 (el tiempo bajó cerca de un 75 %). Le siguen MPI por tableros (30,55 s; 3,46) y MPI por ramas (33,16 s; 3,19). El orden es consistente en las tres repeticiones: el peor tiempo del híbrido (28,37 s) es menor que el mejor de tableros (29,45 s), y el peor de tableros (31,48 s) es menor que el mejor de ramas (32,44 s). La eficiencia (aceleración / N) del híbrido fue de 0,30 con N=13, que parece baja, pero hay que compararla con el límite de este equipo: en la calibración, la tarea de primos, que no tiene comunicación ni desbalance, solo aceleró 4,6 veces con 13 procesos. Frente a esto, el híbrido alcanzó cerca del 86 % (3,96 / 4,61), tableros cerca del 75 % y ramas cerca del 69 %. Es decir, la mayor parte de la brecha respecto a N=13 viene del hardware (los hilos lógicos no equivalen a núcleos completos y el rendimiento de Docker en Windows no escala linealmente) y no del algoritmo.

**2. Efecto de la comunicación y de las diferencias de duración entre tableros.** La comunicación es poca en términos de volumen: por tablero se intercambian mensajes pequeños (ID, estado, tiempo y, en las versiones con ramas, tableros de 81 bytes). Lo que pesa más es la **sincronización**. En tableros, cada uno dura entre 2 y 10 s y hay 30 para 13 procesos (poco más de dos por proceso), así que el tiempo total queda marcado por los tableros largos que se asignan al final: cuando la cola se vacía, varios procesos quedan ociosos esperando al más lento. Eso es coherente con que tableros (30,55 s) quede por encima del tiempo que daría un reparto perfecto con la capacidad real del equipo (105,67 / 4,61 ≈ 22,9 s). En ramas, la sincronización ocurre en **cada uno de los 30 tableros**: todos los procesos deben terminar o recibir el STOP antes de pasar al siguiente, y como solo una rama contiene la solución, el resto del grupo trabaja descartando ramas mientras espera a quien la tiene. Esa espera se repite 30 veces y explica por qué ramas fue la más lenta de las tres, a pesar de usar todos los procesos en cada tablero.

**3. Repartir tableros vs. resolverlos en orden repartiendo ramas, y el papel del híbrido.** Repartir tableros fue un 8 % más rápido que repartir ramas (30,55 s frente a 33,16 s): paralelizar entre tableros independientes evita sincronizarse 30 veces y da trabajo suficiente a todos mientras queda cola. Repartir ramas tiene la ventaja de acortar cada tablero individual, lo que sí elimina la cola larga del final, pero paga la sincronización y la desigualdad entre ramas en cada tablero. El híbrido combina las dos ventajas: con 4 grupos hay 4 tableros en curso a la vez (menos sincronización global que ramas) y cada tablero lo resuelven 3 o 4 procesos (cada uno termina antes, lo que reduce la cola final de tableros). Por eso fue un 12,6 % más rápido que tableros y un 19,4 % más rápido que ramas. El número de grupos importa: con 2 y 3 grupos el rendimiento fue peor (27,05 y 30,67 s), con 4 el mejor de la exploración (23,13 s) y con 5 y 6 volvió a empeorar (24,89 y 27,99 s). Hay que tomar esa exploración con cautela, porque cada valor se midió una sola vez y la medición final del híbrido con 4 grupos (mediana 26,71 s) salió más lenta que la exploración (23,13 s), lo que muestra una variación de ejecución a ejecución de varios segundos. Aun así, 4 grupos fue una elección razonable y su ventaja sobre tableros y ramas se mantuvo en las tres repeticiones finales.
