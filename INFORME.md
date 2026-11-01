# Informe de resultados

> Los valores marcados con `___` los genera `medir_informe.py` (ver `resultados_medicion.md`). Las conclusiones
> deben redactarse con **tus** números; abajo hay preguntas guía para cada punto.

## Entorno

- Equipo: `___` (modelo, CPU, núcleos/hilos, RAM, sistema operativo, Docker Desktop con cuántas CPU asignadas)
- Versión del contenedor: `augustosalazar/slim-mpi:2`
- Cantidad de repeticiones por medición: 3
- Valor común de `N` elegido: `___` (salida de `detectar_procesos_mpi.py`: "N RECOMENDADO")
- Número de grupos del híbrido: `___` (elegido por exploración, ver más abajo)

Cómo se midió (para reproducir):

```
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 python /app/detectar_procesos_mpi.py
docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 python /app/medir_informe.py --n <N>
```

## Comparación final con el mismo `N`

Tres ejecuciones por fila, mediana del "Tiempo total" (reloj real, no suma de procesos). `mpiexec` con
`--allow-run-as-root --use-hwthread-cpus --oversubscribe` en las tres implementaciones.

| Implementación | Caso | Procesos | Mediana del tiempo total (s) | Aceleración frente a secuencial |
| --- | --- | ---: | ---: | ---: |
| Secuencial | Todos los IDs | 1 | ___ | 1,00 |
| MPI por tableros | Todos los IDs | N | ___ | ___ |
| MPI por ramas | Todos los IDs, uno después de otro | N | ___ | ___ |
| MPI híbrido | Todos los IDs | N | ___ | ___ |

Aceleración = tiempo secuencial / tiempo MPI. Tiempos individuales de las 3 repeticiones y exploración de grupos del
híbrido: `resultados_medicion.md`.

## Conclusiones

(Redáctalas con los números de la tabla. Preguntas guía y qué mirar en tus datos:)

- **¿Qué estrategia obtuvo el menor tiempo y cuánto mejoró?** Indica la estrategia ganadora, su mediana y la aceleración.
  Compárala con el máximo teórico N: ¿qué fracción de N alcanzó (eficiencia = aceleración / N)? Si N es mayor que los
  núcleos físicos (hilos SMT u oversubscribe), explica por qué no se acerca a N.
- **Comunicación y diferencias de duración entre tableros.** Mira en la salida de *por tableros* el "trabajo acumulado" frente
  al tiempo total (cuánto del tiempo los procesos estuvieron ocupados) y cuál fue el último tablero en terminar: un tablero
  largo al final deja procesos ociosos. Los mensajes por tablero son pocos y pequeños (ID, estado, tiempo), así que en
  *por tableros* la comunicación casi no pesa; en *ramas* hay generación y envío de ramas más un STOP en cada uno de los 30 tableros.
- **Repartir tableros vs. resolverlos en orden repartiendo ramas.** Compara los tiempos parciales por ID de *ramas* con
  los secuenciales: ¿cuáles mejoran mucho y cuáles poco? Recuerda que solo una rama contiene la solución y las demás deben
  descartarse por completo, así que el trabajo útil por proceso es desigual y el orden de búsqueda cambia respecto al serial
  (puede dar aceleraciones por encima o por debajo de lo esperado). Explica por qué el híbrido queda entre ambos o los supera,
  usando la tabla de exploración de grupos.
