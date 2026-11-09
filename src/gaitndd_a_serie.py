"""
Convierte las series de intervalos de zancada de PhysioNet gaitndd
(Gait Dynamics in Neuro-Degenerative Disease) en archivos de una columna
que FractalApp (interfaz2d3d.py) puede cargar, igual que los archivos de HRV.

El intervalo de zancada es el análogo en la marcha del intervalo RR del ECG:
un valor por ciclo. Se usa la zancada izquierda (columna 2 de los .ts).

Preprocesamiento (Hausdorff et al.):
  - se descartan los primeros 20 s (arranque)
  - se descartan intervalos a más de 3 DE de la mediana (vueltas en el pasillo)

Uso:
    python gaitndd_a_serie.py <carpeta gaitndd/1.0.0> <salida> [n]

    n: número de zancadas por sujeto (por defecto 190). El box-counting depende
       del número de puntos, así que todos los sujetos deben tener el mismo n.
"""
import glob
import os
import re
import sys

import numpy as np

GRUPOS = {"control": "controls", "park": "parkinson", "hunt": "huntington", "als": "ela"}


def intervalos_zancada(ts):
    d = np.loadtxt(ts)
    x = d[d[:, 0] > 20, 1]
    return x[np.abs(x - np.median(x)) < 3 * x.std()]


def convertir(origen, salida, n=190, log=print):
    """Escribe un .txt de n zancadas por sujeto en una carpeta por grupo; devuelve cuántos por grupo."""
    archivos = sorted(glob.glob(os.path.join(origen, "*.ts")))
    if not archivos:
        raise ValueError(f"No .ts files in {origen}. Choose the gaitndd folder that holds the .ts records "
                         "(for example gaitndd/1.0.0).")
    for g in GRUPOS.values():
        os.makedirs(os.path.join(salida, g), exist_ok=True)

    conteo = {g: 0 for g in GRUPOS.values()}
    conteo["skipped"] = 0
    for ts in archivos:
        sid = os.path.basename(ts)[:-3]
        grupo = GRUPOS.get(re.sub(r"\d+", "", sid))
        if grupo is None:
            log(f"{sid}: unknown group, skipped")
            conteo["skipped"] += 1
            continue
        x = intervalos_zancada(ts)
        if len(x) < n:
            log(f"{sid}: only {len(x)} strides (< {n}), skipped")
            conteo["skipped"] += 1
            continue
        np.savetxt(os.path.join(salida, grupo, f"{sid}.txt"), x[:n], fmt="%.4f")
        conteo[grupo] += 1
        log(f"{sid}: {n} strides -> {grupo}")
    return conteo


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    origen, salida = sys.argv[1:3]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 190
    try:
        convertir(origen, salida, n)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
