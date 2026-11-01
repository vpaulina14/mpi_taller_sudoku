"""Automatiza las mediciones del INFORME.md (se ejecuta DENTRO del contenedor).

    docker run --rm -v "$(pwd):/app" augustosalazar/slim-mpi:2 \
        python /app/medir_informe.py --n 4

Para cada implementación ejecuta --all `--repeticiones` veces con el mismo N,
toma la mediana del "Tiempo total" que imprime cada programa (tiempo real del
cronómetro, no suma de procesos) y calcula la aceleración frente al secuencial.
Si no se indica --grupos, antes de la medición final explora cuántos grupos
usar en el híbrido (1 ejecución por candidato) y elige el más rápido.
Escribe resultados_medicion.md y resultados_medicion.json junto a este archivo.
"""

import argparse
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PATRON = re.compile(r"Tiempo total:\s*([0-9.]+)")
MPIEXEC = ["mpiexec", "--allow-run-as-root", "--use-hwthread-cpus", "--oversubscribe"]


def ejecutar(comando, esperados):
    salida = subprocess.run(comando, capture_output=True, text=True)
    if salida.returncode != 0:
        sys.exit(f"Falló: {' '.join(comando)}\n{salida.stdout}\n{salida.stderr}")
    texto = salida.stdout
    coincidencia = PATRON.search(texto)
    if not coincidencia:
        sys.exit(f"No encontré 'Tiempo total' en la salida de {' '.join(comando)}")
    resueltos = texto.count("\nResuelto")
    if resueltos != esperados:
        sys.exit(f"Se esperaban {esperados} tableros resueltos y hubo {resueltos}: {' '.join(comando)}")
    return float(coincidencia.group(1))


def medir(nombre, comando, repeticiones, esperados):
    tiempos = []
    for i in range(1, repeticiones + 1):
        t = ejecutar(comando, esperados)
        tiempos.append(t)
        print(f"  {nombre}, repetición {i}/{repeticiones}: {t:.3f} s", flush=True)
    mediana = statistics.median(tiempos)
    print(f"  -> mediana {nombre}: {mediana:.3f} s\n", flush=True)
    return tiempos, mediana


def coma(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, required=True, help="N elegido con detectar_procesos_mpi.py")
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--grupos", type=int, default=None,
                        help="grupos del híbrido; si se omite se explora automáticamente")
    parser.add_argument("--archivo", type=Path, default=RAIZ / "seeds.txt")
    parser.add_argument("--contenedor", default="augustosalazar/slim-mpi:2",
                        help="solo para dejarlo escrito en el informe")
    args = parser.parse_args()

    n = args.n
    py = sys.executable
    total_ids = sum(1 for l in args.archivo.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.strip().startswith("#"))
    archivo = ["--archivo", str(args.archivo), "--all"]
    cmd_seq = [py, str(RAIZ / "baseline_secuencial.py")] + archivo
    cmd_tab = MPIEXEC + ["-n", str(n), py, str(RAIZ / "mpi_por_tableros/mpi_tableros.py")] + archivo
    cmd_ram = MPIEXEC + ["-n", str(n), py, str(RAIZ / "mpi_por_ramas/mpi_ramas.py")] + archivo

    def cmd_hib(g):
        return MPIEXEC + ["-n", str(n), py, str(RAIZ / "mpi_hibrido/mpi_hibrido.py"),
                          "--grupos", str(g)] + archivo

    print(f"N={n}, {args.repeticiones} repeticiones, {total_ids} tableros\n")

    exploracion = {}
    grupos = args.grupos
    if grupos is None:
        candidatos = list(range(2, n // 2 + 1))
        if not candidatos:
            grupos = 1
            print("N es demasiado pequeño para formar varios grupos de 2: se usa 1 grupo.\n")
        else:
            print("Explorando número de grupos del híbrido (1 ejecución por candidato):", flush=True)
            for g in candidatos:
                t = ejecutar(cmd_hib(g), total_ids)
                exploracion[g] = t
                print(f"  grupos={g}: {t:.3f} s", flush=True)
            grupos = min(exploracion, key=exploracion.get)
            print(f"  -> se elige grupos={grupos}\n", flush=True)

    print("Secuencial:", flush=True)
    t_seq, m_seq = medir("secuencial", cmd_seq, args.repeticiones, total_ids)
    print("MPI por tableros:", flush=True)
    t_tab, m_tab = medir("por tableros", cmd_tab, args.repeticiones, total_ids)
    print("MPI por ramas:", flush=True)
    t_ram, m_ram = medir("por ramas", cmd_ram, args.repeticiones, total_ids)
    print(f"MPI híbrido ({grupos} grupos):", flush=True)
    t_hib, m_hib = medir("híbrido", cmd_hib(grupos), args.repeticiones, total_ids)

    filas = [
        ("Secuencial", "Todos los IDs", 1, t_seq, m_seq),
        ("MPI por tableros", "Todos los IDs", n, t_tab, m_tab),
        ("MPI por ramas", "Todos los IDs, uno después de otro", n, t_ram, m_ram),
        (f"MPI híbrido ({grupos} grupos)", "Todos los IDs", n, t_hib, m_hib),
    ]
    lineas = [
        "| Implementación | Caso | Procesos | Mediana del tiempo total (s) | Aceleración frente a secuencial | Repeticiones (s) |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for nombre, caso, procs, ts, med in filas:
        lineas.append(f"| {nombre} | {caso} | {procs} | {coma(med)} | {coma(m_seq / med)} | "
                      + "; ".join(coma(t, 3) for t in ts) + " |")
    tabla = "\n".join(lineas)

    extra = ""
    if exploracion:
        extra = ("\n\nExploración del número de grupos del híbrido (1 ejecución cada uno):\n\n"
                 "| Grupos | Tiempo total (s) |\n| ---: | ---: |\n"
                 + "\n".join(f"| {g} | {coma(t)} |" for g, t in exploracion.items()))

    nproc = subprocess.run(["nproc"], capture_output=True, text=True).stdout.strip()
    texto = (f"# Resultados medidos\n\n- N = {n} (nproc del contenedor: {nproc})\n"
             f"- Contenedor: {args.contenedor}\n- Repeticiones: {args.repeticiones}\n\n{tabla}{extra}\n")
    (RAIZ / "resultados_medicion.md").write_text(texto, encoding="utf-8")
    (RAIZ / "resultados_medicion.json").write_text(json.dumps({
        "n": n, "grupos_hibrido": grupos, "secuencial": t_seq, "tableros": t_tab,
        "ramas": t_ram, "hibrido": t_hib, "exploracion_grupos": exploracion}, indent=2),
        encoding="utf-8")
    print("\n" + texto)
    print("Guardado en resultados_medicion.md y resultados_medicion.json")


if __name__ == "__main__":
    main()
