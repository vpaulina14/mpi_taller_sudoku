"""Piezas MPI compartidas por las tres implementaciones del taller.

Hay dos mecanismos independientes que se combinan de distinta forma:

1) GrupoRamas  -> reparto de RAMAS de UN tablero dentro de un comunicador.
   El proceso 0 del comunicador es el *líder*: genera las ramas, las reparte
   (ciclicamente), explora su parte y recoge resultados. Cuando alguien
   encuentra la solución, el líder avisa (STOP) y los demás abandonan.

2) bucle_global -> reparto dinámico de IDs (tableros) entre *líderes*.
   El rank 0 del mundo es además el coordinador: lleva la cola de IDs y
   atiende las peticiones "dame trabajo" de los demás líderes. No hay proceso
   dedicado solo a coordinar: mientras resuelve, el rank 0 atiende peticiones
   cada pocas colocaciones del backtracking (callback `tick`).

Uso en cada tarea:
  * por tableros: cada proceso es su propio líder (grupos de tamaño 1).
  * por ramas:    un solo grupo = MPI.COMM_WORLD, los IDs se recorren en orden.
  * híbrido:      el mundo se divide en grupos; los líderes se reparten IDs y
                  cada grupo reparte las ramas del ID asignado.
"""

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mpi4py import MPI  # noqa: E402

from baseline_secuencial import leer_seeds  # noqa: E402
from sudoku_ramas import (codificar, decodificar, es_solucion_valida,  # noqa: E402
                          generar_ramas, resolver_cancelable)

# Etiquetas de mensajes.
TAG_CTRL = 21        # líder -> miembro: ("TAREA", ramas) | ("STOP", None) | ("FIN", None)
TAG_RESULTADO = 22   # miembro -> líder: solución (81 bytes) o None
TAG_PETICION = 31    # líder -> coordinador: None (libre) o resultado de un ID
TAG_TAREA = 32       # coordinador -> líder: ID siguiente o None (no hay más)


def sin_tick():
    return False


class GrupoRamas:
    """Un líder (rank 0 de `comm`) y sus miembros exploran ramas de un tablero."""

    def __init__(self, comm, factor=8, cada=500):
        self.comm = comm
        self.factor = factor      # ramas mínimas por proceso del grupo
        self.cada = cada          # cada cuántas colocaciones se consulta tick()

    # ------------------------------------------------------------------ líder
    def resolver_lider(self, tablero, extra=sin_tick):
        """Resuelve `tablero` con todo el grupo. Solo lo llama el líder.

        `extra()` se invoca periódicamente (lo usa el rank 0 para atender el
        despacho global mientras trabaja). Devuelve la solución o None."""
        comm = self.comm
        tam = comm.Get_size()
        minimo = 1 if tam == 1 else self.factor * tam
        ramas = generar_ramas(tablero, minimo)
        partes = [[codificar(r) for r in ramas[i::tam]] for i in range(tam)]

        estado = {"solucion": None, "pendientes": tam - 1, "stop": False}
        envios = []

        for destino in range(1, tam):
            comm.send(("TAREA", partes[destino]), dest=destino, tag=TAG_CTRL)

        def avisar_stop():
            if not estado["stop"]:
                estado["stop"] = True
                for destino in range(1, tam):
                    envios.append(comm.isend(("STOP", None), dest=destino, tag=TAG_CTRL))

        def recoger():
            info = MPI.Status()
            while estado["pendientes"] > 0 and comm.Iprobe(MPI.ANY_SOURCE, TAG_RESULTADO, info):
                solucion = comm.recv(source=info.Get_source(), tag=TAG_RESULTADO)
                estado["pendientes"] -= 1
                if solucion is not None and estado["solucion"] is None:
                    estado["solucion"] = solucion
                    avisar_stop()

        def tick():
            recoger()
            extra()
            return estado["solucion"] is not None

        # Parte propia del líder.
        for rama in partes[0]:
            if tick():
                break
            copia = decodificar(rama)
            resultado = resolver_cancelable(copia, tick, self.cada)
            if resultado:
                estado["solucion"] = codificar(copia)
                avisar_stop()
                break
            if resultado is None:      # cancelada: alguien ya halló la solución
                break

        # Esperar a todos los miembros (atendiendo el despacho global mientras tanto).
        while estado["pendientes"] > 0:
            recoger()
            extra()
            if estado["pendientes"] > 0:
                time.sleep(0.0005)

        if envios:
            MPI.Request.waitall(envios)
        return decodificar(estado["solucion"]) if estado["solucion"] is not None else None

    def cerrar(self):
        """El líder libera a los miembros (terminan su bucle)."""
        for destino in range(1, self.comm.Get_size()):
            self.comm.send(("FIN", None), dest=destino, tag=TAG_CTRL)

    # --------------------------------------------------------------- miembros
    def servir_miembro(self):
        """Bucle de un miembro (rank != 0 del grupo): explora lo que le manden."""
        comm = self.comm

        def tick():
            return comm.Iprobe(0, TAG_CTRL)   # lo único que llega en pleno trabajo es STOP

        while True:
            while True:                        # los STOP viejos se descartan
                tipo, datos = comm.recv(source=0, tag=TAG_CTRL)
                if tipo != "STOP":
                    break
            if tipo == "FIN":
                return
            solucion = None
            for rama in datos:
                if tick():
                    break
                copia = decodificar(rama)
                resultado = resolver_cancelable(copia, tick, self.cada)
                if resultado:
                    solucion = codificar(copia)
                    break
                if resultado is None:
                    break
            comm.send(solucion, dest=0, tag=TAG_RESULTADO)


class Coordinador:
    """Cola dinámica de IDs, atendida por el rank 0 del mundo."""

    def __init__(self, mundo, ids, otros_lideres):
        self.mundo = mundo
        self.pendientes = list(ids)
        self.activos = len(otros_lideres)
        self.resultados = {}

    def siguiente(self):
        return self.pendientes.pop(0) if self.pendientes else None

    def servir(self):
        """Atiende todas las peticiones que ya llegaron (no bloquea)."""
        info = MPI.Status()
        while self.activos > 0 and self.mundo.Iprobe(MPI.ANY_SOURCE, TAG_PETICION, info):
            origen = info.Get_source()
            mensaje = self.mundo.recv(source=origen, tag=TAG_PETICION)
            if mensaje is not None:
                self.registrar(*mensaje)
            tarea = self.siguiente()
            self.mundo.send(tarea, dest=origen, tag=TAG_TAREA)
            if tarea is None:
                self.activos -= 1

    def registrar(self, identificador, resuelto, segundos, quien):
        self.resultados[identificador] = (resuelto, segundos, quien)
        print(f"\nID: {identificador}")
        print("Resuelto" if resuelto else "Sin solución")
        print(f"Tiempo parcial: {segundos:.6f} segundos  [{quien}]", flush=True)


def bucle_global(mundo, seeds, ids, lideres, resolver, nombre_lider):
    """Reparto dinámico de `ids` entre los líderes (lista de rangos del mundo,
    el primero debe ser 0). Solo lo ejecutan los líderes.

    resolver(tablero, extra) -> solución (lista 9x9) o None; `extra` es un
    callback que debe invocarse periódicamente durante la búsqueda.

    En el rank 0 devuelve (resultados, tiempo_total_real); en los demás None."""
    if mundo.Get_rank() != 0:
        mundo.send(None, dest=0, tag=TAG_PETICION)      # "estoy libre"
        while True:
            identificador = mundo.recv(source=0, tag=TAG_TAREA)
            if identificador is None:
                return None
            original = seeds[identificador]
            inicio = time.perf_counter()
            solucion = resolver([f[:] for f in original], sin_tick)
            segundos = time.perf_counter() - inicio
            resuelto = solucion is not None and es_solucion_valida(original, solucion)
            mundo.send((identificador, resuelto, segundos, nombre_lider()),
                       dest=0, tag=TAG_PETICION)

    coord = Coordinador(mundo, ids, lideres[1:])
    inicio_total = time.perf_counter()
    while True:
        coord.servir()
        identificador = coord.siguiente()
        if identificador is not None:
            original = seeds[identificador]
            inicio = time.perf_counter()
            solucion = resolver([f[:] for f in original], coord.servir)
            segundos = time.perf_counter() - inicio
            resuelto = solucion is not None and es_solucion_valida(original, solucion)
            coord.registrar(identificador, resuelto, segundos, nombre_lider())
        elif coord.activos > 0:
            time.sleep(0.0005)
        else:
            break
    total = time.perf_counter() - inicio_total
    return coord.resultados, total


def cargar_seeds(mundo, archivo):
    """El rank 0 lee el archivo y lo distribuye (los demás no tocan el disco)."""
    seeds = leer_seeds(Path(archivo)) if mundo.Get_rank() == 0 else None
    return mundo.bcast(seeds, root=0)


def resumen(resultados, total, mundo_n, etiqueta):
    """Imprime el resumen final (rank 0)."""
    resueltos = sum(1 for r in resultados.values() if r[0])
    acumulado = sum(r[1] for r in resultados.values())
    print(f"\nIDs procesados: {len(resultados)} (resueltos: {resueltos})")
    print(f"Procesos MPI: {mundo_n}  |  Estrategia: {etiqueta}")
    print(f"Trabajo acumulado de los procesos (solo informativo): {acumulado:.6f} segundos")
    print(f"Tiempo total: {total:.6f} segundos", flush=True)
