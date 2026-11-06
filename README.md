# Multiscale Fractal Complexity of Cardiac Variability: A Biomarker for Seizures

**FractalApp** — Chaos Game Representation and fractal dimension analysis of physiological time series

**Authors:** Alma Rocío Patiño-Chávez, Gael Aguirre-Cruz, Erik Leonardo Mateos-Salgado, Salvador Quiroz-González, Federico Menéndez-Conde Lara and Erika Elizabeth Rodríguez-Torres

**Version:** 1.0

---

## Overview

FractalApp is a graphical application written in Python (Tkinter) that maps a one-dimensional time series, such as a sequence of cardiac RR intervals (heart rate variability, HRV), onto a Sierpinski triangle (2D) or a Sierpinski tetrahedron (3D) through the Chaos Game algorithm. It estimates the fractal dimension of the resulting point set by box-counting.

The application was developed within the research project *Exploring the fractal complexity of cardiac variability in epilepsy*. Its purpose is to compare how completely the fractal attractor is filled by series from control subjects and from patients, including recordings from different seizure states (preictal, ictal, postictal).

<p align="center">
  <img src="preview/interfaz.png" width="700" alt="FractalApp main window">
</p>

---

## Method

Given a series `y_1, ..., y_n`, the application proceeds as follows.

1. **Symbolization.** The values are ranked and split into equally sized groups: terciles for the triangle (3 symbols) and quartiles for the tetrahedron (4 symbols). Each sample receives the symbol of the group its value belongs to, while keeping its original position in time.
2. **Chaos Game.** Starting from the centre of the figure, for every sample in temporal order the current point moves halfway towards the vertex associated with that sample's symbol. The sequence of visited points forms the representation.
3. **Fractal dimension.** The point cloud is normalised to the unit square (or cube) and the number of occupied boxes `N(ε)` is counted for a range of box sizes `ε`. The dimension `D` is the slope of `log N(ε)` against `log(1/ε)`:
   - 2D: 10 box sizes, log-spaced between 10⁻³ and 1.
   - 3D: 10 box sizes, log-spaced between 0.005 and 0.3.

If the symbols are independent and equiprobable, the points fill the whole Sierpinski attractor (theoretical dimension log 3 / log 2 ≈ 1.585 for the triangle and 2 for the tetrahedron). Temporal correlations make some symbol sequences rare or absent, leaving empty regions in the figure and lowering the estimated `D`.

### Generation modes

| Mode | Symbol assignment | Use |
|---|---|---|
| Control | Tercile / quartile of each value | Series from control subjects |
| Patient | Tercile / quartile of each value | Series from patients |
| Random | Uniformly random symbols (the triangle also shuffles the sample order) | Reference for an unstructured sequence |

The Control and Patient modes perform the same computation. They differ only in plot colour and labelling, so that the two groups can be told apart in exported figures.

### Methodological notes

- The box-counting estimate depends on the number of points. Compare series of the same length (the example files contain 4000 values each).
- Missing or non-numeric values must be removed beforehand. During ranking they would be placed in the highest group.
- The method is intended for series sampled once per event, such as one value per heartbeat. Signals sampled at a fixed high rate are strongly autocorrelated from one sample to the next, which by itself produces a poorly filled attractor.

---

## Features

- Loads single-column time series from `.txt`, `.csv` or `.dat` files.
- Generates the Sierpinski triangle (2D) and the Sierpinski tetrahedron (3D).
- Three generation modes: Control, Patient and Random.
- Estimates the fractal dimension by box-counting in 2D and 3D.
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
preview/           Screenshots of the interface
src/
  interfaz2d3d.py        Main application
  giroscopio_a_serie.py  Converter for gyroscope data (ParkinSenseDB), see below
  gaitndd_a_serie.py     Converter for stride interval data (PhysioNet gaitndd), see below
  Software English.rar   Packaged executable, English interface
  Software Español.rar   Packaged executable, Spanish interface
requirements.txt
LICENSE
```

---

## Installation

Requires Python 3 with Tkinter.

```bash
git clone https://github.com/analisisenales/Multiscale-Fractal-Complexity-of-Cardiac-Variability-A-Biomarker-for-Seizures.git
cd Multiscale-Fractal-Complexity-of-Cardiac-Variability-A-Biomarker-for-Seizures

python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

Dependencies: `numpy`, `pandas`, `matplotlib`, `imageio`, `imageio-ffmpeg`.

---

## Usage

```bash
python src/interfaz2d3d.py
```

1. Click **Browse** and select a single-column data file.
2. Under the triangle or tetrahedron section, choose **Control**, **Patient** or **Random**.
3. The fractal dimension is shown in the side panel and above the figure.
4. Export the result with **Save Image (PNG)** or, for the tetrahedron, **Save GIF (3D)**.

### Input format

A plain text file with one numeric value per line and no header, for example RR intervals:

```
0.977
1.016
0.945
```

Tab- or comma-separated files are accepted as long as they contain a single column.

---

## Converting other datasets

Two auxiliary scripts convert gait recordings into the single-column format above, so that FractalApp can be applied outside cardiac data. They are not part of the published HRV analysis.

**ParkinSenseDB (inertial sensors, 100 Hz).** For each subject, computes the magnitude of the angular velocity

```
VM_ω = sqrt(ω_x² + ω_y² + ω_z²)
```

from the gyroscope, discards sensor dropouts and the standing intervals before and after each walk, concatenates the repetitions of one test, and writes `n` samples per subject, separated into control and Parkinson's disease folders.

```bash
python src/giroscopio_a_serie.py <Full_Dataset> <Demographic_Information.xlsx> <output_dir> [test A|B|C|D] [n=4000]
```

**PhysioNet gaitndd (Gait Dynamics in Neuro-Degenerative Disease).** Extracts the left stride interval series, which plays the role of the RR interval in gait (one value per cycle). It removes the first 20 s and the intervals more than 3 SD from the median, and writes `n` strides per subject, grouped into control, Parkinson's disease, Huntington's disease and ALS.

```bash
python src/gaitndd_a_serie.py <gaitndd/1.0.0> <output_dir> [n=190]
```

Subjects with fewer than `n` valid samples are skipped, so that every output series has the same length.

---

## Building a standalone executable (optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed src/interfaz2d3d.py
```

The executable is written to `dist/`. Prebuilt packages for both interface languages are provided in `src/`.

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

---

## Acknowledgements

This software was developed as part of the research project *Exploring the fractal complexity of cardiac variability in epilepsy*.
