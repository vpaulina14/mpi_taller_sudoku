# Resultados medidos

- N = 13 (nproc del contenedor: 16)
- Contenedor: augustosalazar/slim-mpi:2
- Repeticiones: 3

| Implementación | Caso | Procesos | Mediana del tiempo total (s) | Aceleración frente a secuencial | Repeticiones (s) |
| --- | --- | ---: | ---: | ---: | --- |
| Secuencial | Todos los IDs | 1 | 105,67 | 1,00 | 110,374; 103,975; 105,666 |
| MPI por tableros | Todos los IDs | 13 | 30,55 | 3,46 | 29,453; 30,552; 31,484 |
| MPI por ramas | Todos los IDs, uno después de otro | 13 | 33,16 | 3,19 | 33,155; 35,311; 32,440 |
| MPI híbrido (4 grupos) | Todos los IDs | 13 | 26,71 | 3,96 | 26,713; 26,637; 28,366 |

Exploración del número de grupos del híbrido (1 ejecución cada uno):

| Grupos | Tiempo total (s) |
| ---: | ---: |
| 2 | 27,05 |
| 3 | 30,67 |
| 4 | 23,13 |
| 5 | 24,89 |
| 6 | 27,99 |
