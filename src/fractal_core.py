"""
Núcleo de cálculo de FractalApp, independiente de la interfaz.

Lo usan la aplicación gráfica (interfaz2d3d.py), el modo por lotes
(fractal_batch.py) y las pruebas (tests/). Con la configuración por defecto
reproduce exactamente el cálculo original de la aplicación.
"""
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np
import pandas as pd

from giroscopio_a_serie import magnitud_giroscopio
from gaitndd_a_serie import intervalos_zancada

__version__ = "1.2.0"

TRIANGLE_VERTS = np.array([
    [0, 0],
    [1, 0],
    [0.5, 1],
])
TETRAHEDRON_VERTS = np.array([
    [0, 0, 0],
    [1, 0, 0],
    [0.5, np.sqrt(3) / 2, 0],
    [0.5, np.sqrt(3) / 6, np.sqrt(6) / 3],
])
FIGURES = {
    "triangle": (TRIANGLE_VERTS, np.array([0.5, 0.5])),
    "tetrahedron": (TETRAHEDRON_VERTS, np.array([0.5, np.sqrt(3) / 6, np.sqrt(6) / 12])),
}
ESTIMATORS = {
    "classic": "Box-counting (classic)",
    "address": "Address counting (n-adjusted)",
}


# ---------------- Lectura ----------------
def read_column(filepath):
    try:
        y = pd.read_csv(filepath, sep="\t", header=None, engine="python").values.squeeze()
    except Exception:
        try:
            y = pd.read_csv(filepath, header=None).values.squeeze()
        except Exception:
            y = np.loadtxt(filepath)
    return np.asarray(y, dtype=float).reshape(-1)


def load_series(filepath):
    """Devuelve (serie, conversión aplicada o None). Los formatos con convertidor se transforman al cargar."""
    if filepath.lower().endswith(".ts"):
        return intervalos_zancada(filepath), "gaitndd stride intervals"
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        first_line = f.readline()
    if "Gyroscope" in first_line:
        return magnitud_giroscopio(filepath), "gyroscope VMω, walking only"
    return read_column(filepath), None


# ---------------- Preprocesamiento ----------------
@dataclass
class Settings:
    """Opciones de análisis. Los valores por defecto reproducen la aplicación original."""
    estimator: str = "classic"   # "classic" | "address"
    outlier_mad: float = 0.0     # corrige puntos a más de k desviaciones robustas de la mediana local; 0 = no
    detrend_window: int = 0      # resta una mediana móvil de esta longitud; 0 = no
    scale: int = 1               # promedia ventanas no solapadas de tau valores; 1 = no
    max_n: int = 0               # usa solo los primeros n valores; 0 = todos
    seed: Optional[int] = None      # semilla del modo Random; None = una nueva cada vez

    def to_dict(self):
        return asdict(self)


def moving_median(y, window):
    return pd.Series(y).rolling(int(window), center=True, min_periods=1).median().to_numpy()


def correct_outliers(y, k, window=11):
    """Reemplaza por interpolación los puntos a más de k·MAD (escalada a DE) de la mediana móvil."""
    med = moving_median(y, window)
    resid = y - med
    mad = 1.4826 * np.median(np.abs(resid - np.median(resid)))
    if mad == 0:
        return y.copy(), 0
    bad = np.abs(resid) > k * mad
    if bad.all():
        return y.copy(), 0
    out = y.copy()
    i = np.arange(len(y))
    out[bad] = np.interp(i[bad], i[~bad], y[~bad])
    return out, int(bad.sum())


def detrend(y, window):
    return y - moving_median(y, window)


def coarse_grain(y, tau):
    tau = int(tau)
    if tau <= 1:
        return y.copy()
    m = len(y) // tau
    return y[:m * tau].reshape(m, tau).mean(axis=1)


def preprocess(y, settings):
    """Aplica, en orden: quitar no finitos, corregir atípicos, quitar tendencia, escala, recorte a n."""
    y = np.asarray(y, dtype=float).reshape(-1)
    info = {"n_raw": int(len(y))}
    finite = np.isfinite(y)
    y = y[finite]
    info["n_nonfinite_removed"] = int((~finite).sum())
    info["n_outliers_corrected"] = 0
    if settings.outlier_mad > 0 and len(y) > 0:
        y, info["n_outliers_corrected"] = correct_outliers(y, settings.outlier_mad)
    if settings.detrend_window > 1:
        y = detrend(y, settings.detrend_window)
    if settings.scale > 1:
        y = coarse_grain(y, settings.scale)
    if settings.max_n > 0:
        y = y[:settings.max_n]
    info["n_used"] = int(len(y))
    return y, info


# ---------------- Chaos game ----------------
def symbolize(y, k):
    """Símbolos 0..k-1 por cuantiles de igual tamaño; el último grupo recibe el residuo (como la app original)."""
    idx = np.argsort(y)
    lab = np.empty(len(y), dtype=int)
    t = len(y) // k
    for i in range(k):
        lab[idx[i * t:(i + 1) * t if i < k - 1 else None]] = i
    return lab


def random_symbols(n, k, rng):
    return rng.integers(0, k, size=n)


def chaos_game(labels, kind):
    verts, start = FIGURES[kind]
    current = start.astype(float)
    pts = np.zeros((len(labels), verts.shape[1]))
    for f, lab in enumerate(labels):
        current = (current + verts[lab]) / 2
        pts[f] = current
    return pts


# ---------------- Dimensión ----------------
def _box_counts(pts, sizes):
    P = (pts - pts.min(0)) / (pts.max(0) - pts.min(0))
    return [len(np.unique(np.floor(P / s).astype(np.int64), axis=0)) for s in sizes]


def box_counting(pts, kind):
    """Estimador original de la aplicación: escalas fijas, independientes de n."""
    if kind == "triangle":
        sizes = np.logspace(-3, 0, 10)
    else:
        sizes = np.logspace(np.log10(0.005), np.log10(0.3), 10)
    return np.polyfit(np.log(1 / sizes), np.log(_box_counts(pts, sizes)), 1)[0]


def address_levels(n, k, min_words_per_cell=10):
    """Niveles L = 1..L_max con k^L <= n / min_words_per_cell, para que no se saturen."""
    return max(2, int(np.floor(np.log(n / min_words_per_cell) / np.log(k))))


def address_counting(labels, k):
    """
    Dimensión por conteo de direcciones. En el chaos game, el punto t cae en la
    subcelda de nivel L cuya dirección son los últimos L símbolos, así que contar
    palabras distintas de longitud L equivale a contar cajas de lado 2^-L, sin
    aproximar. Solo se usan niveles que la longitud de la serie puede llenar.
    El máximo teórico es log k / log 2 (1.585 en el triángulo, 2 en el tetraedro).
    """
    labels = np.asarray(labels)
    n = len(labels)
    L_max = address_levels(n, k)
    if n < 10 * k ** 2:
        raise ValueError(f"Address counting needs at least {10 * k ** 2} values (got {n}).")
    counts = []
    code = np.zeros(n, dtype=np.int64)
    for L in range(1, L_max + 1):
        code = code * k + labels if L == 1 else code[:-1] * k + labels[L - 1:]
        counts.append(len(np.unique(code)))
    levels = np.arange(1, L_max + 1)
    return np.polyfit(levels * np.log(2), np.log(counts), 1)[0]


def dimension(labels, kind, estimator="classic", pts=None):
    k = 3 if kind == "triangle" else 4
    if estimator == "address":
        return address_counting(labels, k)
    if pts is None:
        pts = chaos_game(labels, kind)
    return box_counting(pts, kind)


def series_dimension(y, kind, estimator="classic"):
    k = 3 if kind == "triangle" else 4
    return dimension(symbolize(y, k), kind, estimator)


# ---------------- Incertidumbre y sustitutos ----------------
def block_bootstrap(y, block, rng):
    n = len(y)
    block = max(1, min(int(block), n))
    starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
    return np.concatenate([y[s:s + block] for s in starts])[:n]


def bootstrap_ci(y, kind, estimator="classic", B=200, block=None, rng=None, alpha=0.05):
    """
    IC percentil por bootstrap de bloques móviles; el bloque por defecto es sqrt(n).
    Unir bloques rompe la estructura temporal en las uniones, lo que puede sesgar D;
    por eso se devuelven también el error estándar y el sesgo (media bootstrap - D).
    """
    rng = rng or np.random.default_rng()
    block = block or int(round(np.sqrt(len(y))))
    D = float(series_dimension(y, kind, estimator))
    ds = np.array([series_dimension(block_bootstrap(y, block, rng), kind, estimator) for _ in range(int(B))])
    lo, hi = np.percentile(ds, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"D": D, "ci_low": float(lo), "ci_high": float(hi), "se": float(ds.std(ddof=1)),
            "bias": float(ds.mean() - D), "B": int(B), "block": int(block), "level": 1 - alpha}


def shuffle_surrogate(y, rng):
    return rng.permutation(y)


def iaaft_surrogate(y, rng, iterations=200, tol=1e-8):
    """Sustituto IAAFT: conserva la distribución y, aproximadamente, el espectro de potencia."""
    y = np.asarray(y, dtype=float)
    sorted_y = np.sort(y)
    amp = np.abs(np.fft.rfft(y))
    s = rng.permutation(y)
    prev = None
    for _ in range(iterations):
        phases = np.angle(np.fft.rfft(s))
        s = np.fft.irfft(amp * np.exp(1j * phases), n=len(y))
        ranks = np.argsort(np.argsort(s))
        s = sorted_y[ranks]
        err = np.mean((np.abs(np.fft.rfft(s)) - amp) ** 2)
        if prev is not None and abs(prev - err) <= tol * max(prev, 1e-30):
            break
        prev = err
    return s


SURROGATES = {"shuffle": shuffle_surrogate, "iaaft": iaaft_surrogate}


def surrogate_test(y, kind, estimator="classic", M=99, method="shuffle", rng=None):
    """Compara D con M series sustitutas. p bilateral por rangos: (1 + extremos) / (M + 1)."""
    rng = rng or np.random.default_rng()
    D = series_dimension(y, kind, estimator)
    make = SURROGATES[method]
    ds = np.array([series_dimension(make(y, rng), kind, estimator) for _ in range(int(M))])
    mu, sd = ds.mean(), ds.std(ddof=1)
    extreme = np.sum(np.abs(ds - mu) >= abs(D - mu))
    # Si todos los sustitutos dan el mismo D (p. ej. barajados que llenan el atractor), z no está definida
    return {"D": float(D), "surrogate_mean": float(mu), "surrogate_sd": float(sd),
            "z": float((D - mu) / sd) if sd > 1e-9 else float("nan"),
            "p": float((1 + extreme) / (M + 1)), "M": int(M), "method": method}


def multiscale(y, kind, estimator="classic", scales=(1, 2, 4, 8, 16)):
    """D después de promediar ventanas de tau valores. n se reduce con tau."""
    out = []
    k = 3 if kind == "triangle" else 4
    for tau in scales:
        z = coarse_grain(y, tau)
        try:
            D = series_dimension(z, kind, estimator) if len(z) >= k else float("nan")
        except ValueError:
            D = float("nan")
        out.append({"scale": int(tau), "n": int(len(z)), "D": float(D)})
    return out


# ---------------- Medidas complementarias ----------------
def dfa_alpha(y, min_scale=4, max_scale=None):
    """Exponente de DFA de primer orden. Requiere al menos 32 valores."""
    y = np.asarray(y, dtype=float)
    if len(y) < 32:
        return float("nan")
    prof = np.cumsum(y - y.mean())
    max_scale = max_scale or len(y) // 4
    scales = np.unique(np.logspace(np.log10(min_scale), np.log10(max_scale), 12).astype(int))
    F = []
    for s in scales:
        m = len(prof) // s
        seg = prof[:m * s].reshape(m, s)
        t = np.arange(s)
        coef = np.polyfit(t, seg.T, 1)
        trend = np.outer(coef[0], t) + coef[1][:, None]
        F.append(np.sqrt(np.mean((seg - trend) ** 2)))
    return float(np.polyfit(np.log(scales), np.log(F), 1)[0])


def sample_entropy(y, m=2, r=0.2, max_n=20000):
    """SampEn(m, r·DE). Devuelve NaN si n > max_n (el costo crece con n²) o si no hay coincidencias."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n > max_n or n <= m + 1:
        return float("nan")
    tol = r * y.std()
    def matches(mm):
        X = np.lib.stride_tricks.sliding_window_view(y, mm)[:n - m]
        c = 0
        for i in range(len(X) - 1):
            c += np.sum(np.max(np.abs(X[i + 1:] - X[i]), axis=1) <= tol)
        return c
    B, A = matches(m), matches(m + 1)
    return float(-np.log(A / B)) if A > 0 and B > 0 else float("nan")


def measures(y):
    y = np.asarray(y, dtype=float)
    mean, sd = y.mean(), y.std(ddof=1)
    return {
        "mean": float(mean),
        "sd": float(sd),
        "cv": float(sd / mean) if mean != 0 else float("nan"),
        "rmssd": float(np.sqrt(np.mean(np.diff(y) ** 2))),
        "dfa_alpha": dfa_alpha(y),
        "sample_entropy": sample_entropy(y),
    }


# ---------------- Señales sintéticas para validar ----------------
def white_noise(n, rng):
    return rng.standard_normal(n)


def sine(n, period=20.0, noise=0.0, rng=None):
    t = np.arange(n)
    y = np.sin(2 * np.pi * t / period)
    return y + noise * rng.standard_normal(n) if noise and rng is not None else y


def fgn(n, hurst, rng):
    """Ruido gaussiano fraccional por el método de Davies-Harte (incremento de un fBm con exponente H)."""
    k = np.arange(n + 1)
    gamma = 0.5 * (np.abs(k - 1) ** (2 * hurst) - 2 * k ** (2 * hurst) + (k + 1) ** (2 * hurst))
    row = np.concatenate([gamma, gamma[-2:0:-1]])
    lam = np.fft.fft(row).real
    lam[lam < 0] = 0
    m = len(row)
    w = rng.standard_normal(m) + 1j * rng.standard_normal(m)
    z = np.fft.fft(np.sqrt(lam / (2 * m)) * w)
    return z.real[:n]
