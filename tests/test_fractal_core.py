"""
Pruebas del núcleo de cálculo. Ejecutar desde la raíz del repositorio:

    python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import fractal_core as fc  # noqa: E402

N1 = os.path.join(ROOT, "data", "controls", "N1.txt")


def legacy_dimensions(y):
    """Copia literal del cálculo de la aplicación hasta la versión 1.0 (incluida la clave 2D con colisión)."""
    p = len(y)
    idx = np.argsort(y)
    lab3 = np.empty(p, int); t = p // 3
    lab3[idx[:t]] = 1; lab3[idx[t:2 * t]] = 2; lab3[idx[2 * t:]] = 3
    cur = np.array([0.5, 0.5]); pts = np.zeros((p, 2))
    for f in range(p):
        cur = (cur + fc.TRIANGLE_VERTS[lab3[f] - 1]) / 2; pts[f] = cur
    P = (pts - pts.min(0)) / (pts.max(0) - pts.min(0)); sizes = np.logspace(-3, 0, 10)
    c = [len(np.unique(np.floor(P / s).astype(int)[:, 0] * 1000 + np.floor(P / s).astype(int)[:, 1])) for s in sizes]
    d2 = np.polyfit(np.log(1 / sizes), np.log(c), 1)[0]
    lab4 = np.empty(p, int); t = p // 4
    lab4[idx[:t]] = 1; lab4[idx[t:2 * t]] = 2; lab4[idx[2 * t:3 * t]] = 3; lab4[idx[3 * t:]] = 4
    cur = np.array([0.5, np.sqrt(3) / 6, np.sqrt(6) / 12]); pts = np.zeros((p, 3))
    for f in range(p):
        cur = (cur + fc.TETRAHEDRON_VERTS[lab4[f] - 1]) / 2; pts[f] = cur
    P = (pts - pts.min(0)) / (pts.max(0) - pts.min(0)); eps = np.logspace(np.log10(0.005), np.log10(0.3), 10)
    c = []
    for e in eps:
        i = np.floor(P / e).astype(int); c.append(len(np.unique(i[:, 0] * 1e6 + i[:, 1] * 1e3 + i[:, 2])))
    d3 = np.polyfit(np.log(1 / eps), np.log(c), 1)[0]
    return d2, d3


class DefaultsMatchVersion10(unittest.TestCase):
    def test_classic_estimator_reproduces_original_app(self):
        y, _ = fc.preprocess(fc.read_column(N1), fc.Settings())
        d2, d3 = legacy_dimensions(y)
        # 3D idéntico; 2D difiere solo por la corrección de la colisión de claves en la caja más pequeña
        self.assertAlmostEqual(fc.series_dimension(y, "tetrahedron"), d3, places=12)
        self.assertAlmostEqual(fc.series_dimension(y, "triangle"), d2, delta=5e-4)

    def test_default_settings_do_not_change_a_clean_series(self):
        y = fc.read_column(N1)
        out, info = fc.preprocess(y, fc.Settings())
        np.testing.assert_array_equal(out, y)
        self.assertEqual(info["n_nonfinite_removed"], 0)


class Preprocessing(unittest.TestCase):
    def test_nonfinite_values_are_removed_not_ranked(self):
        y = np.array([1.0, np.nan, 2.0, np.inf, 3.0, 4.0])
        out, info = fc.preprocess(y, fc.Settings())
        np.testing.assert_array_equal(out, [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(info["n_nonfinite_removed"], 2)

    def test_outlier_correction_replaces_spikes(self):
        rng = np.random.default_rng(0)
        y = 1 + 0.01 * rng.standard_normal(500)
        y[[100, 300]] = 5.0
        out, info = fc.preprocess(y, fc.Settings(outlier_mad=5))
        self.assertEqual(info["n_outliers_corrected"], 2)
        self.assertLess(out.max(), 1.2)

    def test_coarse_grain_and_truncation(self):
        y = np.arange(10, dtype=float)
        np.testing.assert_array_equal(fc.coarse_grain(y, 2), [0.5, 2.5, 4.5, 6.5, 8.5])
        out, _ = fc.preprocess(y, fc.Settings(max_n=4))
        self.assertEqual(len(out), 4)

    def test_detrend_removes_a_ramp(self):
        y = np.linspace(0, 100, 1000)
        self.assertLess(np.abs(fc.detrend(y, 51)[50:-50]).max(), 1e-9)


class KnownSignals(unittest.TestCase):
    """Validación con señales de estructura conocida."""

    def test_white_noise_fills_the_attractor(self):
        rng = np.random.default_rng(1)
        y = fc.white_noise(20000, rng)
        self.assertAlmostEqual(fc.series_dimension(y, "triangle", "address"), np.log(3) / np.log(2), delta=0.05)
        self.assertAlmostEqual(fc.series_dimension(y, "tetrahedron", "address"), 2.0, delta=0.06)

    def test_periodic_signal_leaves_the_attractor_empty(self):
        # Un periodo de 20 solo produce unas 20 palabras distintas: D muy por debajo del máximo log3/log2
        y = fc.sine(20000, period=20)
        self.assertLess(fc.series_dimension(y, "triangle", "address"), 0.5 * np.log(3) / np.log(2))

    def test_address_estimator_does_not_drift_with_n(self):
        rng = np.random.default_rng(2)
        y = fc.white_noise(16000, rng)
        a = [fc.series_dimension(y[:n], "triangle", "address") for n in (1000, 4000, 16000)]
        c = [fc.series_dimension(y[:n], "triangle", "classic") for n in (1000, 4000, 16000)]
        self.assertLess(max(a) - min(a), 0.06)
        self.assertGreater(max(c) - min(c), 0.15)

    def test_fgn_dfa_recovers_hurst_exponent(self):
        rng = np.random.default_rng(3)
        for H in (0.5, 0.8):
            self.assertAlmostEqual(fc.dfa_alpha(fc.fgn(8192, H, rng)), H, delta=0.08)


class Inference(unittest.TestCase):
    def test_bootstrap_interval_contains_estimate(self):
        y = fc.read_column(N1)
        r = fc.bootstrap_ci(y, "triangle", "address", B=50, rng=np.random.default_rng(4))
        self.assertLessEqual(r["ci_low"], r["ci_high"])
        self.assertTrue(r["ci_low"] - 0.05 <= r["D"] <= r["ci_high"] + 0.05)

    def test_iaaft_keeps_the_value_distribution(self):
        rng = np.random.default_rng(5)
        y = fc.fgn(2048, 0.8, rng)
        s = fc.iaaft_surrogate(y, rng)
        np.testing.assert_allclose(np.sort(s), np.sort(y))

    def test_surrogate_test_flags_a_periodic_series(self):
        y = fc.sine(3000, period=25, noise=0.05, rng=np.random.default_rng(6))
        r = fc.surrogate_test(y, "triangle", "classic", M=39, method="shuffle", rng=np.random.default_rng(7))
        self.assertLess(r["z"], -5)
        self.assertLessEqual(r["p"], 0.05)

    def test_random_mode_is_reproducible_with_a_seed(self):
        a = fc.random_symbols(100, 3, np.random.default_rng(11))
        b = fc.random_symbols(100, 3, np.random.default_rng(11))
        np.testing.assert_array_equal(a, b)


class Measures(unittest.TestCase):
    def test_measures_on_a_constant_step(self):
        m = fc.measures(np.array([1.0, 2.0, 1.0, 2.0] * 50))
        self.assertAlmostEqual(m["mean"], 1.5)
        self.assertAlmostEqual(m["rmssd"], 1.0)

    def test_sample_entropy_lower_for_regular_signal(self):
        rng = np.random.default_rng(8)
        self.assertLess(fc.sample_entropy(fc.sine(1500)), fc.sample_entropy(fc.white_noise(1500, rng)))


if __name__ == "__main__":
    unittest.main()
