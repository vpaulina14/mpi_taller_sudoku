"""Extensiones del resolvedor serial para repartir el trabajo con MPI.

No usa MPI: solo agrega dos cosas a sudoku.py.

* generar_ramas(): divide un tablero en sub-tableros independientes fijando
  las primeras casillas vacías con todos los valores válidos. Como el
  backtracking de sudoku.py siempre rellena la primera casilla vacía, cada
  rama corresponde exactamente a un subárbol de esa búsqueda: la unión de
  todas las ramas recorre el mismo espacio de búsqueda que la versión serial.
* resolver_cancelable(): el mismo backtracking de sudoku.resolver(), pero
  cada cierto número de colocaciones llama a tick(); si tick() devuelve True
  la búsqueda se abandona (otro proceso ya encontró la solución).
"""

from sudoku import puede_colocar


class _Cancelado(Exception):
    """Se lanza para desenrollar la recursión cuando tick() pide parar."""


def primera_vacia(tablero):
    for fila in range(9):
        for columna in range(9):
            if tablero[fila][columna] == 0:
                return fila, columna
    return None


def generar_ramas(tablero, minimo, profundidad_maxima=8):
    """Devuelve una lista de tableros (ramas) con al menos `minimo` elementos,
    si el tablero lo permite. Expande nivel por nivel la primera casilla vacía
    de cada rama. Lista vacía = el tablero no tiene solución."""
    ramas = [[fila[:] for fila in tablero]]
    for _ in range(profundidad_maxima):
        if len(ramas) >= minimo:
            break
        nuevas = []
        expandio = False
        for rama in ramas:
            posicion = primera_vacia(rama)
            if posicion is None:          # rama ya completa
                nuevas.append(rama)
                continue
            expandio = True
            fila, columna = posicion
            for valor in range(1, 10):
                if puede_colocar(rama, fila, columna, valor):
                    hija = [f[:] for f in rama]
                    hija[fila][columna] = valor
                    nuevas.append(hija)
        ramas = nuevas
        if not expandio or not ramas:
            break
    return ramas


def resolver_cancelable(tablero, tick, cada=500):
    """Backtracking idéntico a sudoku.resolver() con punto de cancelación.

    Resuelve in situ. Devuelve True (resuelto), False (sin solución en esta
    rama) o None (cancelado por tick())."""
    colocaciones = 0

    def buscar():
        nonlocal colocaciones
        for fila in range(9):
            for columna in range(9):
                if tablero[fila][columna] != 0:
                    continue
                for valor in range(1, 10):
                    if puede_colocar(tablero, fila, columna, valor):
                        tablero[fila][columna] = valor
                        colocaciones += 1
                        if colocaciones % cada == 0 and tick():
                            raise _Cancelado
                        if buscar():
                            return True
                        tablero[fila][columna] = 0
                return False
        return True

    try:
        return buscar()
    except _Cancelado:
        return None


def codificar(tablero):
    """Tablero 9x9 -> 81 bytes (mensajes MPI pequeños y rápidos de serializar)."""
    return bytes(valor for fila in tablero for valor in fila)


def decodificar(datos):
    return [list(datos[i:i + 9]) for i in range(0, 81, 9)]


def es_solucion_valida(original, solucion):
    """Comprueba que `solucion` respeta las pistas de `original` y las reglas."""
    todos = set(range(1, 10))
    for f in range(9):
        for c in range(9):
            if original[f][c] != 0 and solucion[f][c] != original[f][c]:
                return False
    for i in range(9):
        fila = {solucion[i][c] for c in range(9)}
        columna = {solucion[f][i] for f in range(9)}
        bloque = {solucion[(i // 3) * 3 + a][(i % 3) * 3 + b]
                  for a in range(3) for b in range(3)}
        if fila != todos or columna != todos or bloque != todos:
            return False
    return True
