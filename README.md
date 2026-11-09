# Multiscale Fractal Complexity of Cardiac Variability: A Biomarker for Seizures

[![Tests](https://github.com/Richard7987/Multiscale-Fractal-Complexity-of-Cardiac-Variability-A-Biomarker-for-Seizures/actions/workflows/tests.yml/badge.svg)](https://github.com/Richard7987/Multiscale-Fractal-Complexity-of-Cardiac-Variability-A-Biomarker-for-Seizures/actions/workflows/tests.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](#installation)
[![Version 1.1](https://img.shields.io/badge/version-1.1-blue)](#changes-in-version-11)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**FractalApp** — Chaos Game Representation and fractal dimension analysis of physiological time series

**Authors:** Alma Rocío Patiño-Chávez, Gael Aguirre-Cruz, Erik Leonardo Mateos-Salgado, Salvador Quiroz-González, Federico Menéndez-Conde Lara and Erika Elizabeth Rodríguez-Torres

This is an independent fork of [analisisenales/Multiscale-Fractal-Complexity-of-Cardiac-Variability-A-Biomarker-for-Seizures](https://github.com/analisisenales/Multiscale-Fractal-Complexity-of-Cardiac-Variability-A-Biomarker-for-Seizures), maintained separately while the original authors prepare their paper. Version 1.0 and the method are their work.

**Version:** 1.1

---

## Overview

FractalApp is a graphical application written in Python (Tkinter) that maps a one-dimensional time series, such as a sequence of cardiac RR intervals (heart rate variability, HRV), onto a Sierpinski triangle (2D) or a Sierpinski tetrahedron (3D) through the Chaos Game algorithm. It estimates the fractal dimension of the resulting point set by box-counting.

Its purpose is to compare how completely the fractal attractor is filled by series from control subjects and from patients, including recordings from different seizure states (preictal, ictal, postictal).

<p align="center">
  <img src="preview/fractal.gif" width="700" alt="Chaos Game construction of the Sierpinski triangle (2D) and tetrahedron (3D) from a control RR series">
</p>

<p align="center"><em>Sierpinski triangle and tetrahedron built point by point from <code>data/controls/N1.txt</code> (4000 RR intervals, Control mode).</em></p>

---

## Method

Given a series `y_1, ..., y_n`, the application proceeds as follows.

1. **Symbolization.** The values are ranked and split into equally sized groups: terciles for the triangle (3 symbols) and quartiles for the tetrahedron (4 symbols). Each sample receives the symbol of the group its value belongs to, while keeping its original position in time.
2. **Chaos Game.** Starting from the centre of the figure, for every sample in temporal order the current point moves halfway towards the vertex associated with that sample's symbol. The sequence of visited points forms the representation.
3. **Fractal dimension.** Two estimators are available (see [Analysis settings](#analysis-settings)):
   - **Box-counting (classic, default).** The point cloud is normalised to the unit square (or cube) and the number of occupied boxes `N(ε)` is counted for a range of box sizes `ε`. `D` is the slope of `log N(ε)` against `log(1/ε)`. 2D: 10 box sizes, log-spaced between 10⁻³ and 1. 3D: 10 box sizes, log-spaced between 0.005 and 0.3. This is the estimator of version 1.0.
   - **Address counting (n-adjusted, optional).** In the Chaos Game, the point at time `t` lies in the sub-triangle (or sub-tetrahedron) of side 2⁻ᴸ whose address is the last `L` symbols. Counting the distinct symbol words of length `L` therefore counts the occupied cells exactly. `D` is the slope of `log N(L)` against `L log 2`, using only the levels with `kᴸ ≤ n / 10`, so that a series of `n` values can fill them. The estimate does not drift with `n`.

If the symbols are independent and equiprobable, the points fill the whole Sierpinski attractor (theoretical dimension log 3 / log 2 ≈ 1.585 for the triangle and 2 for the tetrahedron). Temporal correlations make some symbol sequences rare or absent, leaving empty regions in the figure and lowering the estimated `D`. With 4000 values, address counting gives values close to these maxima for uncorrelated series, whereas the classic estimator gives values near 1.07 (2D) because its finest boxes cannot be filled.

### Generation modes

| Mode | Symbol assignment | Use |
|---|---|---|
| Control | Tercile / quartile of each value | Series from control subjects |
| Patient | Tercile / quartile of each value | Series from patients |
| Random | Uniformly random symbols from a seeded generator | Reference for an unstructured sequence |

The Control and Patient modes perform the same computation. They differ only in plot colour and labelling, so that the two groups can be told apart in exported figures.

### Methodological notes

- The classic box-counting estimate depends on the number of points. Compare series of the same length (the example files contain 4000 values each; the setting *Use first n values* truncates longer series), or use address counting.
- Missing or non-numeric values (empty cells, NaN, infinity) are removed automatically before ranking, and the number removed is shown. In version 1.0 they were silently placed in the highest group.
- Slow trends keep the series in the same tercile for long stretches and lower `D` without any change in the beat-to-beat dynamics. Compare `D` with and without detrending, or across scales, before attributing a low value to a loss of complexity.
- Symbolization uses ranks, so `D` does not see the amplitude of the variability. Two series with the same ordering but different spread give the same `D`; the complementary measures in [Statistics](#statistics) report amplitude.
- The method is intended for series sampled once per event, such as one value per heartbeat. Signals sampled at a fixed high rate are strongly autocorrelated from one sample to the next, which by itself produces a poorly filled attractor.

---

## Features

- Loads single-column time series from `.txt`, `.csv` or `.dat` files.
- Converts gait recordings on load: ParkinSenseDB gyroscope files (`data.csv`) and PhysioNet gaitndd stride files (`.ts`). See [Supported input formats](#supported-input-formats).
- Generates the Sierpinski triangle (2D) and the Sierpinski tetrahedron (3D).
- Three generation modes: Control, Patient and Random.
- Estimates the fractal dimension in 2D and 3D by classic box-counting or by n-adjusted address counting.
- Optional preprocessing: outlier correction, detrending, coarse-graining to a scale τ and truncation to `n` values.
- Statistics window: bootstrap confidence interval for `D`, test against shuffled or IAAFT surrogates, `D` across scales with a plot, and complementary measures (mean, SD, CV, RMSSD, DFA α, sample entropy), exportable to JSON and CSV.
- Batch mode for whole folders, writing one CSV row per file plus a JSON with the parameters.
- Reproducibility: seeded Random mode, and a JSON file with every parameter saved next to each image or GIF.
- Exports high-resolution PNG images and rotating GIF animations of the tetrahedron. The individual GIF frames are also saved as PNG files.
- Light or dark plot background.
- On Linux (X11), includes a file browser with search, which replaces the native Tk dialog.

---

## Repository structure

```
data/
  controls/        N1–N5: RR interval series from control subjects (4000 values each)
  epileptics/      E1–E5: RR interval series from patients with epilepsy (4000 values each)
  states/          Preictal, ictal and postictal series (3000 values each), with
                   example triangle, tetrahedron and GIF outputs; RANDOM holds the
                   random-mode reference figures
preview/           Interface screenshots and fractal.gif (2D and 3D construction)
src/
  interfaz2d3d.py        Main application (interface)
  fractal_core.py        Computation: loading, preprocessing, Chaos Game, estimators, statistics
  fractal_batch.py       Batch mode for folders of series
  giroscopio_a_serie.py  ParkinSenseDB gyroscope converter (used by the app and as a batch command)
  gaitndd_a_serie.py     PhysioNet gaitndd stride converter (used by the app and as a batch command)
  Software English.rar   Packaged executable, English interface
  Software Español.rar   Packaged executable, Spanish interface
tests/
  test_fractal_core.py   Regression and validation tests
requirements.txt
LICENSE
```

---

## Installation

Requires Python 3.9 or later with Tkinter. The tests run on Python 3.9, 3.12 and 3.13 on every push and pull request.

```bash
git clone https://github.com/Richard7987/Multiscale-Fractal-Complexity-of-Cardiac-Variability-A-Biomarker-for-Seizures.git
cd Multiscale-Fractal-Complexity-of-Cardiac-Variability-A-Biomarker-for-Seizures

python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

Dependencies: `numpy`, `pandas`, `matplotlib`, `imageio`, `imageio-ffmpeg`, and `openpyxl` (only needed by the ParkinSenseDB batch command, which reads the demographics spreadsheet).

The application imports `fractal_core.py` and the two converters from `src/`, so keep the `.py` files of `src/` in the same folder.

---

## Usage

```bash
python src/interfaz2d3d.py
```

1. Click **Browse** and select a data file (see the formats below). The side panel shows the number of values and, for converted files, which conversion was applied.
2. Optionally, open **Settings…** to choose the estimator and the preprocessing. The panel summarises the active settings.
3. Under the triangle or tetrahedron section, choose **Control**, **Patient** or **Random**.
4. The fractal dimension is shown in the side panel and above the figure.
5. Optionally, open **Statistics…** for a confidence interval, a surrogate test, `D` across scales and complementary measures.
6. Export the result with **Save Image (PNG)** or, for the tetrahedron, **Save GIF (3D)**. A `.json` file with the same name records the parameters.

With the default settings the results are those of version 1.0 (see [Changes in version 1.1](#changes-in-version-11)).

### Analysis settings

All options are off by default. They are applied in this order to the loaded series, and the same prepared series is used by the figures, the statistics and the saved files.

| Setting | Default | Effect |
|---|---|---|
| Dimension estimator | Box-counting (classic) | Classic box-counting, or address counting (n-adjusted); see [Method](#method) |
| Outlier correction | 0 (off) | Points farther than `k` robust standard deviations (1.4826 × MAD) from an 11-point moving median are replaced by linear interpolation |
| Detrend window | 0 (off) | Subtracts a moving median of this length |
| Coarse-grain scale τ | 1 (off) | Replaces the series by the means of non-overlapping windows of τ values |
| Use first n values | 0 (all) | Truncates the series, so that series of different length can be compared |
| Random-mode seed | blank | Fixes the random symbols of the Random mode; when blank, a new seed is drawn and reported |

Non-finite values are always removed first.

### Statistics

The **Statistics…** window works on the prepared series with the active estimator, for the triangle (`D2`), the tetrahedron (`D3`) or both.

- **Bootstrap confidence interval.** Moving-block bootstrap with `B` replicates (default 200) and blocks of √n values unless another length is given. The window reports the 95 % percentile interval, the bootstrap standard error and the bias (bootstrap mean minus `D`). Joining blocks breaks the temporal structure at the joins, which can bias `D`; when `D` falls outside the interval the window says so, and a longer block is advisable.
- **Surrogate test.** `D` is compared with `M` surrogate series (default 99). *Shuffle* keeps the values and destroys their order. *IAAFT* keeps the values and, approximately, the power spectrum, so it tests for structure beyond linear correlation. The window reports the surrogate mean and SD, `z = (D − mean) / SD` and a two-sided rank p-value `(1 + extreme surrogates) / (M + 1)`. If every surrogate gives the same `D` (for example shuffled series that fill the attractor under address counting), `z` is undefined and only `p` is reported.
- **Scales.** `D` after coarse-graining to each τ in the list, with a plot. `n` falls as τ grows; with the classic estimator this alone lowers `D`, so address counting is better suited to compare scales.
- **Complementary measures.** Mean, SD, CV, RMSSD (root mean square of successive differences), DFA α (first-order detrended fluctuation analysis, scales 4 to n/4) and sample entropy (m = 2, r = 0.2 SD; not computed above 20 000 values).

**Export…** writes a JSON file with the results, the settings, the preprocessing summary and the seed, and a CSV file with one row per quantity.

### Reproducibility

Each saved image or GIF gets a `.json` file with the program version, the input file, the conversion applied, the settings, the preprocessing summary (values read, removed and corrected), the figure, the mode, the random seed, the estimator and `D`. The statistics export and the batch mode record the same information.

### Supported input formats

The format is detected when the file is opened; no separate conversion step is needed.

| File | Detected by | What the app loads |
|---|---|---|
| Single-column series (`.txt`, `.csv`, `.dat`) | anything not listed below | the values as they are |
| ParkinSenseDB inertial recording (`data.csv`) | a header containing `Gyroscope` | `VM_ω = sqrt(ω_x² + ω_y² + ω_z²)` of the gyroscope, without sensor dropouts and without the standing intervals |
| PhysioNet gaitndd record (`.ts`) | the `.ts` extension | left stride intervals, without the first 20 s and without values more than 3 SD from the median |

A single-column file has one numeric value per line and no header, for example RR intervals:

```
0.977
1.016
0.945
```

Tab- or comma-separated files are accepted as long as they contain a single column.

A converted file keeps all its valid samples, so its length depends on the recording (for example, about 1800–2000 gyroscope samples for one ParkinSenseDB walk, or about 200–300 strides for one gaitndd record). Because the classic estimate depends on the number of points, set *Use first n values*, use address counting, or use the batch commands below when comparing groups.

---

## Batch mode

`fractal_batch.py` analyses many files at once with the same options as the application and writes one CSV row per file, plus a JSON file with the parameters, the program version and the seed. Folders are searched recursively for `.txt`, `.csv`, `.dat` and `.ts` files; the conversions of the application apply. A file that cannot be read gets an `error` column instead of stopping the run.

```bash
# Default settings: the same D2 and D3 as the application
python src/fractal_batch.py data/controls data/epileptics -o results.csv

# Address counting, 95 % bootstrap CI, surrogate test, D across scales and complementary measures
python src/fractal_batch.py data -o results.csv --estimator address --bootstrap 200 \
       --surrogates 99 --surrogate-method iaaft --scales 1,2,4,8,16 --measures --seed 1
```

| Option | Meaning |
|---|---|
| `--figures triangle,tetrahedron` | which dimensions to compute |
| `--estimator classic\|address` | dimension estimator |
| `--outlier-mad K`, `--detrend W`, `--scale TAU`, `--max-n N` | preprocessing, as in the settings window |
| `--bootstrap B`, `--block L` | bootstrap confidence interval (adds `_ci_low`, `_ci_high`, `_se`, `_bias`) |
| `--surrogates M`, `--surrogate-method shuffle\|iaaft` | surrogate test (adds `_surrogate_mean`, `_z`, `_p`) |
| `--scales 1,2,4` | `D` at each scale (adds `_scale1`, `_scale2`, …) |
| `--measures` | mean, SD, CV, RMSSD, DFA α, sample entropy |
| `--seed S` | seed for bootstrap and surrogates |

Every row also reports `n_raw`, `n_nonfinite_removed`, `n_outliers_corrected` and `n_used`.

---

## Converting whole datasets

The same converters can be run from the command line on a complete dataset. They write one single-column `.txt` file per subject, all with the same length `n`, sorted into one folder per group. Subjects with fewer than `n` valid samples are skipped. These files can then be opened in the app like any other series. The gait conversions are not part of the published HRV analysis.

**ParkinSenseDB (inertial sensors, 100 Hz).** Computes `VM_ω` for every repetition of one test (A: simple walk, B: narrowing walk, C: change of direction, D: Timed Up and Go), concatenates the repetitions in order, and writes the first `n` samples of each subject into `controls/` and `parkinson/`. The demographics spreadsheet supplies each subject's group.

```bash
python src/giroscopio_a_serie.py <Full_Dataset> <Demographic_Information.xlsx> <output_dir> [test A|B|C|D] [n=4000]
```

**PhysioNet gaitndd (Gait Dynamics in Neuro-Degenerative Disease).** Writes the first `n` cleaned left stride intervals of each subject into `controls/`, `parkinson/`, `huntington/` and `ela/`. The stride interval plays the role of the RR interval in gait: one value per cycle.

```bash
python src/gaitndd_a_serie.py <gaitndd/1.0.0> <output_dir> [n=190]
```

Notes on the data:

- `VM_ω` is sampled at 100 Hz, not once per event, so consecutive samples are strongly correlated (see [Methodological notes](#methodological-notes)).
- In both datasets the control groups are younger than the Parkinson's groups; compare them only with an adjustment for age.

---

## Building a standalone executable (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/interfaz2d3d.py
```

The executable is written to `dist/`. PyInstaller includes `fractal_core.py` and the two converters automatically because the application imports them. The prebuilt packages for both interface languages in `src/` correspond to version 1.0: they read single-column files only and do not include the settings, statistics or batch mode.

---

## Testing

```bash
python -m unittest discover -s tests -v
```

The same tests run automatically in GitHub Actions (`.github/workflows/tests.yml`) on Python 3.9, 3.12 and 3.13; the *Tests* badge at the top shows the latest result. They check that:

- with the default settings the classic estimator reproduces version 1.0 (3D identical; 2D within 5 × 10⁻⁴, see below);
- non-finite values are removed rather than ranked, and the preprocessing steps behave as described;
- white noise fills the attractor (address counting close to log 3 / log 2 and 2), a periodic signal leaves it largely empty, and address counting does not drift with `n` while the classic estimator does;
- DFA recovers the Hurst exponent of fractional Gaussian noise (H = 0.5 and 0.8);
- IAAFT surrogates keep the value distribution, the surrogate test flags a periodic series, the bootstrap interval is well formed, and the Random mode is reproducible with a seed.

---

## Changes in version 1.1

- Computation moved to `fractal_core.py`, shared by the application, the batch mode and the tests.
- New: address-counting estimator, preprocessing options, statistics window, batch mode, seeded Random mode, parameter files next to saved images, automatic conversion of gait recordings, tests.
- Fixed: non-finite values were ranked into the highest group; they are now removed and reported.
- Fixed: in the 2D box count, the cell key `x · 1000 + y` made the cell `(x, 1000)` collide with `(x + 1, 0)` at the smallest box size. Cells are now compared as pairs. On the example files this changes `D2` by at most 0.0002; `D3` is unchanged.

---

## Citation

If you use this software in academic work, please cite:

> Patiño-Chávez, A. R., Aguirre-Cruz, G., Mateos-Salgado, E. L., Quiroz-González, S., Menéndez-Conde Lara, F., & Rodríguez-Torres, E. E. *Fractal-HRV-Analyzer: A Multiscale Software Framework to Analyze Seizures via Chaos Game Mapping.*

Once the article is published, cite the final journal version together with this repository.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE).

---

## Contact

Alma Rocío Patiño-Chávez — pa401981@uaeh.com

Corresponding author: Erika Elizabeth Rodríguez-Torres — erikart@uaeh.edu.mx
