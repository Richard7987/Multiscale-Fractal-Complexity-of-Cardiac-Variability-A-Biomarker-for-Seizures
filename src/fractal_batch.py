"""
Modo por lotes de FractalApp: calcula la dimensión fractal de muchos archivos
y escribe una tabla CSV, más un JSON con los parámetros y la versión usada.

Ejemplos:
    python src/fractal_batch.py data/controls data/epileptics -o resultados.csv
    python src/fractal_batch.py data -o r.csv --estimator address --bootstrap 200 --surrogates 99 --measures
    python src/fractal_batch.py data -o r.csv --scales 1,2,4,8 --max-n 4000

Acepta los mismos formatos que la aplicación (una columna, CSV de giroscopio
de ParkinSenseDB y .ts de gaitndd). Sin opciones, el cálculo es el de la app.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

import fractal_core as fc

EXTENSIONS = (".txt", ".csv", ".dat", ".ts")


def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                files += [os.path.join(root, n) for n in names if n.lower().endswith(EXTENSIONS)]
        elif os.path.isfile(p):
            files.append(p)
        else:
            print(f"No existe: {p}", file=sys.stderr)
    return sorted(files)


def analyse(path, args, settings, rng):
    raw, source = fc.load_series(path)
    y, info = fc.preprocess(raw, settings)
    row = {"file": path, "conversion": source or "", **info}
    for kind in args.figures:
        tag = "D2" if kind == "triangle" else "D3"
        row[tag] = fc.series_dimension(y, kind, settings.estimator)
        if args.bootstrap:
            b = fc.bootstrap_ci(y, kind, settings.estimator, B=args.bootstrap, block=args.block, rng=rng)
            row[f"{tag}_ci_low"], row[f"{tag}_ci_high"] = b["ci_low"], b["ci_high"]
            row[f"{tag}_se"], row[f"{tag}_bias"] = b["se"], b["bias"]
        if args.surrogates:
            s = fc.surrogate_test(y, kind, settings.estimator, M=args.surrogates, method=args.surrogate_method, rng=rng)
            row[f"{tag}_surrogate_mean"], row[f"{tag}_z"], row[f"{tag}_p"] = s["surrogate_mean"], s["z"], s["p"]
        for r in fc.multiscale(y, kind, settings.estimator, args.scales) if args.scales else []:
            row[f"{tag}_scale{r['scale']}"] = r["D"]
    if args.measures:
        row.update(fc.measures(y))
    return row


def main():
    ap = argparse.ArgumentParser(description="FractalApp batch mode: fractal dimension for many files.")
    ap.add_argument("inputs", nargs="+", help="files or folders (searched recursively)")
    ap.add_argument("-o", "--output", required=True, help="output CSV")
    ap.add_argument("--figures", default="triangle,tetrahedron", help="triangle, tetrahedron or both (comma-separated)")
    ap.add_argument("--estimator", choices=list(fc.ESTIMATORS), default="classic")
    ap.add_argument("--outlier-mad", type=float, default=0.0, help="correct points beyond k robust SD of the local median (0 = off)")
    ap.add_argument("--detrend", type=int, default=0, help="subtract a moving median of this length (0 = off)")
    ap.add_argument("--scale", type=int, default=1, help="average non-overlapping windows of tau values (1 = off)")
    ap.add_argument("--max-n", type=int, default=0, help="use only the first n values (0 = all)")
    ap.add_argument("--bootstrap", type=int, default=0, help="moving-block bootstrap replicates for a 95%% CI (0 = off)")
    ap.add_argument("--block", type=int, default=None, help="bootstrap block length (default sqrt(n))")
    ap.add_argument("--surrogates", type=int, default=0, help="number of surrogate series (0 = off)")
    ap.add_argument("--surrogate-method", choices=list(fc.SURROGATES), default="shuffle")
    ap.add_argument("--scales", default="", help="multiscale D at these tau values, e.g. 1,2,4,8")
    ap.add_argument("--measures", action="store_true", help="add mean, SD, CV, RMSSD, DFA alpha and sample entropy")
    ap.add_argument("--seed", type=int, default=None, help="seed for bootstrap and surrogates")
    args = ap.parse_args()
    args.figures = [f.strip() for f in args.figures.split(",") if f.strip()]
    args.scales = [int(s) for s in args.scales.split(",") if s.strip()]

    settings = fc.Settings(estimator=args.estimator, outlier_mad=args.outlier_mad,
                           detrend_window=args.detrend, scale=args.scale, max_n=args.max_n)
    seed = args.seed if args.seed is not None else int(np.random.SeedSequence().generate_state(1)[0])
    rng = np.random.default_rng(seed)

    rows = []
    for path in collect(args.inputs):
        try:
            rows.append(analyse(path, args, settings, rng))
            print(f"ok  {path}")
        except Exception as e:
            rows.append({"file": path, "error": str(e)})
            print(f"err {path}: {e}", file=sys.stderr)

    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    meta = {"fractalapp_version": fc.__version__, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "settings": settings.to_dict(), "figures": args.figures, "bootstrap": args.bootstrap, "block": args.block,
            "surrogates": args.surrogates, "surrogate_method": args.surrogate_method, "scales": args.scales,
            "measures": args.measures, "seed": seed, "files": len(rows)}
    with open(os.path.splitext(args.output)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"{len(rows)} files -> {args.output}")


if __name__ == "__main__":
    main()
