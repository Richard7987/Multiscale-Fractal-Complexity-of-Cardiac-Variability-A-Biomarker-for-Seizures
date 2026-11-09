"""
Convierte los datos de giroscopio de ParkinSenseDB en series de una columna
que FractalApp (interfaz2d3d.py) puede cargar, igual que los archivos de HRV.

Para cada muestra se calcula la magnitud vectorial de la velocidad angular:

    VM_w = sqrt(wx^2 + wy^2 + wz^2)     [dps, 100 Hz]

Uso:
    python giroscopio_a_serie.py <Full_Dataset> <Demographic_Information.xlsx> <salida> [prueba] [n]

    prueba: A, B, C o D (por defecto A, caminata simple)
    n:      número de muestras por sujeto (por defecto 4000, como los archivos de HRV)
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

UMBRAL_MARCHA = 15  # dps, media móvil de 1 s


def leer_demografia(path):
    # La hoja trae todo en una sola columna separada por comas: "ID,Sex,Status,Age"
    raw = pd.read_excel(path, dtype=str).iloc[:, 0].str.split(",")
    status = raw.str[2].str.strip().replace({"Controllo": "Control"})
    return dict(zip(raw.str[0].str.strip(), status))


def magnitud_giroscopio(csv):
    # En algunos sujetos el encabezado viene entrecomillado como un solo campo,
    # así que se ignora y se toman las columnas por posición (GyroX, GyroY, GyroZ)
    g = pd.read_csv(csv, header=None, skiprows=1, usecols=[4, 5, 6]).to_numpy(float)
    vm = np.sqrt((g ** 2).sum(axis=1))
    # Se descartan los huecos del sensor (NaN); el programa los ordenaría como valores altos
    vm = vm[np.isfinite(vm)]
    # Solo tramos de marcha: al inicio y al final de cada repetición el sujeto está de pie
    # (VM ~ 4 dps) y esos segmentos deforman el fractal sin relación con la marcha
    marcha = pd.Series(vm).rolling(100, center=True, min_periods=1).mean().to_numpy() > UMBRAL_MARCHA
    return vm[marcha]


def serie_sujeto(carpeta, prueba):
    # Concatena las repeticiones (gait1, gait2, ...) en orden numérico
    archivos = glob.glob(os.path.join(carpeta, f"TEST {prueba}", "gait*", "data.csv"))
    archivos.sort(key=lambda p: int(re.search(r"gait(\d+)", p).group(1)))
    if not archivos:
        return np.array([])
    return np.concatenate([magnitud_giroscopio(a) for a in archivos])


def convertir(dataset, demografia, salida, prueba="A", n=4000, log=print):
    """Escribe un .txt de n valores por sujeto en salida/controls y salida/parkinson; devuelve cuántos por grupo."""
    if not os.path.isdir(dataset):
        raise ValueError(f"Dataset folder not found: {dataset}")
    status = leer_demografia(demografia)
    grupos = {"Control": "controls", "PD": "parkinson"}
    sujetos = [s for s in sorted(os.listdir(dataset)) if os.path.isdir(os.path.join(dataset, s, f"TEST {prueba}"))]
    if not sujetos:
        raise ValueError(f'No subject folders with a "TEST {prueba}" folder inside {dataset}. '
                         "Choose the Full_Dataset folder, which holds one folder per subject.")
    for g in grupos.values():
        os.makedirs(os.path.join(salida, g), exist_ok=True)

    conteo = {"controls": 0, "parkinson": 0, "skipped": 0}
    for sid in sujetos:
        grupo = grupos.get(status.get(sid))
        if grupo is None:
            log(f"{sid}: not in the demographics file, skipped")
            conteo["skipped"] += 1
            continue
        y = serie_sujeto(os.path.join(dataset, sid), prueba)
        if len(y) < n:
            log(f"{sid}: only {len(y)} samples (< {n}), skipped")
            conteo["skipped"] += 1
            continue
        np.savetxt(os.path.join(salida, grupo, f"{sid}_test{prueba}.txt"), y[:n], fmt="%.3f")
        conteo[grupo] += 1
        log(f"{sid} ({status[sid]}): {n} samples -> {grupo}")
    return conteo


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    dataset, demografia, salida = sys.argv[1:4]
    prueba = sys.argv[4] if len(sys.argv) > 4 else "A"
    n = int(sys.argv[5]) if len(sys.argv) > 5 else 4000
    try:
        convertir(dataset, demografia, salida, prueba, n)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
