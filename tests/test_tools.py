"""
Pruebas del modo por lotes y de los convertidores de datasets, con datos sintéticos.

    python -m unittest discover -s tests -v
"""
import csv
import os
import sys
import tempfile
import threading
import unittest

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import fractal_batch as fb  # noqa: E402
import fractal_core as fc  # noqa: E402
import gaitndd_a_serie  # noqa: E402
import giroscopio_a_serie  # noqa: E402


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        rng = np.random.default_rng(0)
        for group in ("controls", "patients"):
            os.makedirs(os.path.join(self.tmp.name, group))
            for i in range(3):
                np.savetxt(os.path.join(self.tmp.name, group, f"s{i}.txt"), rng.normal(size=500))
        with open(os.path.join(self.tmp.name, "patients", "broken.txt"), "w") as f:
            f.write("not a number\n")
        self.out = os.path.join(self.tmp.name, "results.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_rows_groups_and_summary(self):
        rows, meta = fb.run([self.tmp.name], self.out, fc.Settings(), seed=1)
        self.assertEqual(meta["files"], 7)
        self.assertFalse(meta["cancelled"])
        with open(self.out, newline="", encoding="utf-8") as f:
            table = list(csv.DictReader(f))
        self.assertEqual(len(table), 7)
        self.assertTrue(os.path.exists(os.path.splitext(self.out)[0] + ".json"))
        summary = {s["group"]: s for s in fb.summarize(rows)}
        self.assertEqual(summary["controls"]["D2"][2], 3)
        self.assertEqual(summary["patients"]["errors"], 1)
        self.assertEqual(summary["patients"]["D3"][2], 3)

    def test_same_result_as_single_file(self):
        rows, _ = fb.run([os.path.join(self.tmp.name, "controls", "s0.txt")], self.out, fc.Settings())
        y = np.loadtxt(os.path.join(self.tmp.name, "controls", "s0.txt"))
        self.assertAlmostEqual(rows[0]["D2"], fc.series_dimension(y, "triangle"))

    def test_cancel_keeps_partial_table(self):
        cancel = threading.Event()
        rows, meta = fb.run([self.tmp.name], self.out, fc.Settings(),
                            progress=lambda i, *a: cancel.set() if i == 2 else None, cancel=cancel)
        self.assertEqual(len(rows), 2)
        self.assertTrue(meta["cancelled"])

    def test_empty_folder(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(empty)
        with self.assertRaises(ValueError):
            fb.run([empty], self.out, fc.Settings())


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = os.path.join(self.tmp.name, "out")
        self.rng = np.random.default_rng(0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_gaitndd(self):
        src = os.path.join(self.tmp.name, "gaitndd")
        os.makedirs(src)
        for sid, strides in (("control1", 300), ("park1", 300), ("hunt1", 50)):
            t = np.arange(strides) * 1.1
            np.savetxt(os.path.join(src, f"{sid}.ts"), np.column_stack([t, 1.1 + 0.02 * self.rng.normal(size=strides)]))
        counts = gaitndd_a_serie.convertir(src, self.out, n=190, log=lambda line: None)
        self.assertEqual(counts["controls"], 1)
        self.assertEqual(counts["parkinson"], 1)
        self.assertEqual(counts["skipped"], 1)
        self.assertEqual(len(np.loadtxt(os.path.join(self.out, "controls", "control1.txt"))), 190)

    def test_gaitndd_wrong_folder(self):
        with self.assertRaises(ValueError):
            gaitndd_a_serie.convertir(self.tmp.name, self.out, log=lambda line: None)

    def test_parkinsense(self):
        dataset = os.path.join(self.tmp.name, "Full_Dataset")
        for sid in ("001", "002"):
            folder = os.path.join(dataset, sid, "TEST A", "gait1")
            os.makedirs(folder)
            gyro = 40 + 5 * self.rng.normal(size=(1500, 3))
            data = np.column_stack([np.arange(1500), np.zeros((1500, 3)), gyro])
            pd.DataFrame(data, columns=["t", "AccX", "AccY", "AccZ", "GyroscopeX", "GyroscopeY", "GyroscopeZ"]).to_csv(
                os.path.join(folder, "data.csv"), index=False)
        demographics = os.path.join(self.tmp.name, "Demographic_Information.xlsx")
        pd.DataFrame({"ID,Sex,Status,Age": ["001,M,Control,60", "002,F,PD,70"]}).to_excel(demographics, index=False)
        counts = giroscopio_a_serie.convertir(dataset, demographics, self.out, "A", 1000, log=lambda line: None)
        self.assertEqual((counts["controls"], counts["parkinson"], counts["skipped"]), (1, 1, 0))
        self.assertEqual(len(np.loadtxt(os.path.join(self.out, "parkinson", "002_testA.txt"))), 1000)

    def test_parkinsense_wrong_folder(self):
        demographics = os.path.join(self.tmp.name, "d.xlsx")
        pd.DataFrame({"ID,Sex,Status,Age": ["001,M,Control,60"]}).to_excel(demographics, index=False)
        with self.assertRaises(ValueError):
            giroscopio_a_serie.convertir(self.tmp.name, demographics, self.out, log=lambda line: None)


if __name__ == "__main__":
    unittest.main()
