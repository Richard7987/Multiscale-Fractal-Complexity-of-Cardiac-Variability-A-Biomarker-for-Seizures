# FractalApp guide

Detailed reference for [FractalApp](../README.md): method, settings, statistics, input formats, batch mode and tests.

- [Method](#method)
- [Analysis settings](#analysis-settings)
- [Statistics](#statistics)
- [Reproducibility](#reproducibility)
- [Supported input formats](#supported-input-formats)
- [Batch mode](#batch-mode)
- [Converting whole datasets](#converting-whole-datasets)
- [Testing](#testing)
- [Changes in version 1.2](#changes-in-version-12)
- [Changes in version 1.1](#changes-in-version-11)
- [Releases](#releases)

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

## Analysis settings

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

## Statistics

The **Statistics…** window works on the prepared series with the active estimator, for the triangle (`D2`), the tetrahedron (`D3`) or both.

- **Bootstrap confidence interval.** Moving-block bootstrap with `B` replicates (default 200) and blocks of √n values unless another length is given. The window reports the 95 % percentile interval, the bootstrap standard error and the bias (bootstrap mean minus `D`). Joining blocks breaks the temporal structure at the joins, which can bias `D`; when `D` falls outside the interval the window says so, and a longer block is advisable.
- **Surrogate test.** `D` is compared with `M` surrogate series (default 99). *Shuffle* keeps the values and destroys their order. *IAAFT* keeps the values and, approximately, the power spectrum, so it tests for structure beyond linear correlation. The window reports the surrogate mean and SD, `z = (D − mean) / SD` and a two-sided rank p-value `(1 + extreme surrogates) / (M + 1)`. If every surrogate gives the same `D` (for example shuffled series that fill the attractor under address counting), `z` is undefined and only `p` is reported.
- **Scales.** `D` after coarse-graining to each τ in the list, with a plot. `n` falls as τ grows; with the classic estimator this alone lowers `D`, so address counting is better suited to compare scales.
- **Complementary measures.** Mean, SD, CV, RMSSD (root mean square of successive differences), DFA α (first-order detrended fluctuation analysis, scales 4 to n/4) and sample entropy (m = 2, r = 0.2 SD; not computed above 20 000 values).

**Export…** writes a JSON file with the results, the settings, the preprocessing summary and the seed, and a CSV file with one row per quantity.

## Reproducibility

Each saved image or GIF gets a `.json` file with the program version, the input file, the conversion applied, the settings, the preprocessing summary (values read, removed and corrected), the figure, the mode, the random seed, the estimator and `D`. The statistics export and the batch mode record the same information.

## Supported input formats

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

**In the app:** *Tools → Batch analysis…*. Add one or more folders, choose what to compute and where to save the table, and press *Run*. The analysis uses the current *Settings*. When it finishes, the window shows the mean and SD of `D2` and `D3` for each group, and *Open table* opens the CSV in the spreadsheet program. *Use example data* adds the example controls and patients.

**From the command line:** `fractal_batch.py` takes the same options.

Both write one CSV row per file, plus a JSON file with the parameters, the program version and the seed. Folders are searched recursively for `.txt`, `.csv`, `.dat` and `.ts` files; the conversions of the application apply. Each row's `group` is the name of the folder that holds the file. A file that cannot be read gets an `error` column instead of stopping the run.

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

**In the app:** *Tools → Convert dataset…*. Choose the dataset, its folder (and, for ParkinSenseDB, the demographics spreadsheet and the test), the number of values per subject and an output folder, then press *Convert*. *Analyse these files…* opens the batch analysis with the converted folder.

**From the command line:** the commands below do the same. The converters write one single-column `.txt` file per subject, all with the same length `n`, sorted into one folder per group. Subjects with fewer than `n` valid samples are skipped. These files can then be opened in the app like any other series. The gait conversions are not part of the published HRV analysis.

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

## Testing

```bash
python -m unittest discover -s tests -v
```

The same tests run automatically in GitHub Actions (`.github/workflows/tests.yml`) on Python 3.9, 3.12 and 3.13. They check that:

- with the default settings the classic estimator reproduces version 1.0 (3D identical; 2D within 5 × 10⁻⁴, see below);
- non-finite values are removed rather than ranked, and the preprocessing steps behave as described;
- white noise fills the attractor (address counting close to log 3 / log 2 and 2), a periodic signal leaves it largely empty, and address counting does not drift with `n` while the classic estimator does;
- DFA recovers the Hurst exponent of fractional Gaussian noise (H = 0.5 and 0.8);
- IAAFT surrogates keep the value distribution, the surrogate test flags a periodic series, the bootstrap interval is well formed, and the Random mode is reproducible with a seed.

---

## Changes in version 1.2

- Batch analysis and dataset conversion are available in the app (*Tools*), so the executables can do everything the scripts do.
- Help window (*Help* or F1) with a quick start.
- The executables include the example data.
- The batch table has a `group` column.
- Fixed: the Statistics window could stay at *Computing…* without showing results, because the calculation thread called Tk directly.

---

## Changes in version 1.1

- Computation moved to `fractal_core.py`, shared by the application, the batch mode and the tests.
- New: address-counting estimator, preprocessing options, statistics window, batch mode, seeded Random mode, parameter files next to saved images, automatic conversion of gait recordings, tests.
- Fixed: non-finite values were ranked into the highest group; they are now removed and reported.
- Fixed: in the 2D box count, the cell key `x · 1000 + y` made the cell `(x, 1000)` collide with `(x + 1, 0)` at the smallest box size. Cells are now compared as pairs. On the example files this changes `D2` by at most 0.0002; `D3` is unchanged.

---

## Releases

Pushing a tag `vX.Y.Z` that matches `__version__` in `src/fractal_core.py` runs the tests, builds the executables with PyInstaller on Windows and Linux, and publishes them in a GitHub release (`.github/workflows/release.yml`).

```bash
git tag -m "FractalApp v1.2.0" v1.2.0
git push origin v1.2.0
```
