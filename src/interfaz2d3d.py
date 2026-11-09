# -*- coding: utf-8 -*-
"""
FractalApp - Sierpinski Triangle (2D) & Tetrahedron (3D)
Author: Alma 💙
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import imageio, os, time, json, csv, threading
from datetime import datetime, timezone

import fractal_core as fc

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

TRIANGLE_VERTS = fc.TRIANGLE_VERTS
TETRAHEDRON_VERTS = fc.TETRAHEDRON_VERTS
ESTIMATOR_SHORT = {"classic": "Box-counting", "address": "Address counting"}

MODES = ("controls", "patients", "random")
MODE_LABELS = {"controls": "Control", "patients": "Patient", "random": "Random"}

UI = {
    "bg": "#15181d",
    "card": "#20242b",
    "border": "#323842",
    "text": "#eceef1",
    "muted": "#a0a8b4",
    "disabled": "#646c78",
    "accent": "#4a94e6",
}
MODE_BUTTONS = {
    "controls": ("#245fbf", "#2f6fde"),
    "patients": ("#b83f27", "#d1492e"),
    "random": ("#0c8576", "#0f9d8a"),
}
PLOT_THEMES = {
    "dark": {
        "bg": "#15181d",
        "text": "#eceef1",
        "muted": "#a0a8b4",
        "frame": "#4a515c",
        "colors": {"controls": "#4a94e6", "patients": "#e4604b", "random": "#14a38f"},
        "halo": 0.05,
    },
    "light": {
        "bg": "#ffffff",
        "text": "#1c2026",
        "muted": "#5c6470",
        "frame": "#c3c8cf",
        "colors": {"controls": "#2f6fde", "patients": "#d1492e", "random": "#0f9d8a"},
        "halo": 0,
    },
}


class FileBrowser(tk.Toplevel):
    """Explorador de archivos para X11, donde Tk no usa el diálogo del sistema."""

    def __init__(self, parent, title, extensions, start_dir, save=False, initial=""):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=UI["bg"])
        self.geometry("780x500")
        self.minsize(620, 360)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.extensions = extensions
        self.save = save
        self.result = ""
        self.entries = []
        self.rows = []
        self.cwd = start_dir

        self.path_var = tk.StringVar(master=self)
        self.search = tk.StringVar(master=self)
        self.name_var = tk.StringVar(master=self, value=initial)
        self.show_hidden = tk.BooleanVar(master=self, value=False)
        self.show_all = tk.BooleanVar(master=self, value=False)

        body = ttk.Frame(self, padding=14)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(2, weight=1)

        # Lugares
        places = ttk.Frame(body)
        places.grid(row=0, column=0, rowspan=5, sticky="ns", padx=(0,14))
        ttk.Label(places, text="Places", style="Section.TLabel").pack(anchor="w", pady=(0,6))
        for label, path in self._places():
            ttk.Button(places, text=label, style="Place.TButton",
                       command=lambda p=path: self._go(p)).pack(fill=tk.X, pady=1)

        # Ruta
        top = ttk.Frame(body)
        top.grid(row=0, column=1, sticky="ew")
        top.columnconfigure(1, weight=1)
        ttk.Button(top, text="Up", command=lambda: self._go(os.path.dirname(self.cwd))).grid(row=0, column=0, padx=(0,6))
        path_entry = ttk.Entry(top, textvariable=self.path_var)
        path_entry.grid(row=0, column=1, sticky="ew")
        path_entry.bind("<Return>", lambda e: self._go_typed())

        # Búsqueda
        bar = ttk.Frame(body)
        bar.grid(row=1, column=1, sticky="ew", pady=8)
        bar.columnconfigure(1, weight=1)
        ttk.Label(bar, text="Search").grid(row=0, column=0, padx=(0,8))
        self.search_entry = ttk.Entry(bar, textvariable=self.search)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0,10))
        self.search_entry.bind("<Return>", lambda e: self._activate_first())
        self.search_entry.bind("<Down>", lambda e: self._focus_list())
        ttk.Checkbutton(bar, text="All file types", variable=self.show_all, command=self._fill).grid(row=0, column=2, padx=(0,8))
        ttk.Checkbutton(bar, text="Hidden files", variable=self.show_hidden, command=self._fill).grid(row=0, column=3)
        self.search.trace_add("write", lambda *a: self._fill())

        # Lista
        frame = ttk.Frame(body)
        frame.grid(row=2, column=1, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=("size","modified"), selectmode="browse")
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("size", text="Size", anchor="e")
        self.tree.heading("modified", text="Modified", anchor="w")
        self.tree.column("#0", stretch=True, width=300)
        self.tree.column("size", stretch=False, width=80, anchor="e")
        self.tree.column("modified", stretch=False, width=130)
        self.tree.tag_configure("dir", foreground="#8fbdf0")
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_select())
        self.tree.bind("<Double-1>", lambda e: self._activate())
        self.tree.bind("<Return>", lambda e: self._activate())

        self.message = ttk.Label(body, style="Muted.TLabel")
        self.message.grid(row=3, column=1, sticky="w", pady=(6,8))

        # Nombre y acciones
        bottom = ttk.Frame(body)
        bottom.grid(row=4, column=1, sticky="ew")
        bottom.columnconfigure(1, weight=1)
        ttk.Label(bottom, text="File name").grid(row=0, column=0, padx=(0,8))
        self.name_entry = ttk.Entry(bottom, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(0,10))
        self.name_entry.bind("<Return>", lambda e: self._accept())
        ttk.Button(bottom, text="Cancel", command=self.destroy).grid(row=0, column=2, padx=(0,6))
        ttk.Button(bottom, text="Save" if save else "Open", style="Accent.TButton",
                   command=self._accept).grid(row=0, column=3)

        self.bind("<Escape>", lambda e: self.destroy())
        self.path_var.set(self.cwd)
        self._scan(self.cwd)
        self._fill()

    def show(self):
        self.wait_visibility()
        self.grab_set()
        if self.save:
            self.name_entry.focus_set()
            self.name_entry.selection_range(0, tk.END)
        else:
            self.search_entry.focus_set()
        self.wait_window()
        return self.result

    def _places(self):
        home = os.path.expanduser("~")
        places = [("Home", home)]
        if os.path.isdir(DATA_DIR):
            places.append(("App data", DATA_DIR))
        for name in ("Desktop", "Escritorio", "Documents", "Documentos", "Downloads", "Descargas"):
            path = os.path.join(home, name)
            if os.path.isdir(path):
                places.append((name, path))
        places.append(("Computer", os.path.abspath(os.sep)))
        return places

    def _scan(self, path):
        entries = []
        try:
            with os.scandir(path) as it:
                for item in it:
                    try:
                        info = item.stat()
                        entries.append((item.name, item.is_dir(), info.st_size, info.st_mtime))
                    except OSError:
                        entries.append((item.name, False, None, None))
        except OSError as e:
            self.message.config(text=f"Cannot open folder: {e.strerror}")
            return False
        self.cwd = path
        self.path_var.set(path)
        self.entries = sorted(entries, key=lambda x: (not x[1], x[0].casefold()))
        return True

    def _go(self, path):
        if self._scan(path):
            self.search.set("")
            self._fill()
            self.tree.yview_moveto(0)

    def _go_typed(self):
        path = os.path.abspath(os.path.expanduser(self.path_var.get().strip()))
        if os.path.isdir(path):
            self._go(path)
        elif os.path.isfile(path) and not self.save:
            self.result = path
            self.destroy()
        else:
            self.message.config(text=f"Not found: {path}")

    def _matches(self, name, is_dir):
        if name.startswith(".") and not self.show_hidden.get():
            return False
        if self.search.get().strip().casefold() not in name.casefold():
            return False
        return is_dir or self.show_all.get() or name.lower().endswith(self.extensions)

    def _fill(self):
        self.tree.delete(*self.tree.get_children())
        self.rows = [e for e in self.entries if self._matches(e[0], e[1])]
        for i, (name, is_dir, size, mtime) in enumerate(self.rows):
            text = name + "/" if is_dir else name
            shown_size = "" if is_dir or size is None else self._format_size(size)
            shown_time = "" if mtime is None else time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
            self.tree.insert("", tk.END, iid=str(i), text=text, values=(shown_size, shown_time),
                             tags=("dir",) if is_dir else ())
        query = self.search.get().strip()
        if self.rows:
            self.message.config(text=f"{len(self.rows)} item{'' if len(self.rows) == 1 else 's'}")
        elif query:
            self.message.config(text=f'No matches for "{query}" in this folder')
        else:
            self.message.config(text="No matching files in this folder")

    def _format_size(self, size):
        for unit in ("B", "KB", "MB"):
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    def _selected(self):
        sel = self.tree.selection()
        return self.rows[int(sel[0])] if sel else None

    def _on_select(self):
        row = self._selected()
        if row and (not row[1] or not self.save):
            self.name_var.set(row[0])

    def _focus_list(self):
        if self.rows:
            self.tree.focus_set()
            self.tree.selection_set("0")
            self.tree.focus("0")
        return "break"

    def _activate_first(self):
        if self.rows:
            self.tree.selection_set("0")
            self._activate()

    def _activate(self):
        row = self._selected()
        if row and row[1]:
            self._go(os.path.join(self.cwd, row[0]))
        elif row:
            self.name_var.set(row[0])
            self._accept()
        return "break"

    def _accept(self):
        name = self.name_var.get().strip()
        if not name:
            self.message.config(text="Choose a file first.")
            return
        path = os.path.abspath(os.path.join(self.cwd, os.path.expanduser(name)))
        if os.path.isdir(path):
            self.name_var.set("")
            self._go(path)
            return
        if self.save:
            if not path.lower().endswith(self.extensions):
                path += self.extensions[0]
            if os.path.exists(path) and not messagebox.askyesno(
                    "Replace file", f"{os.path.basename(path)} already exists. Replace it?", parent=self):
                return
        elif not os.path.isfile(path):
            self.message.config(text=f"File not found: {name}")
            return
        self.result = path
        self.destroy()


class SettingsDialog(tk.Toplevel):
    """Opciones de análisis. Los valores por defecto reproducen el cálculo de la versión 1.0."""

    FIELDS = (
        ("outlier", "Outlier correction (robust SD, 0 = off)",
         "Points farther than k robust standard deviations from an 11-point moving median are replaced by interpolation."),
        ("detrend", "Detrend window (values, 0 = off)",
         "Subtracts a moving median of this length, removing slow trends before symbolization."),
        ("scale", "Coarse-grain scale τ (1 = off)",
         "Averages non-overlapping windows of τ values (multiscale analysis)."),
        ("max_n", "Use first n values (0 = all)",
         "D depends on the number of points: compare series of equal length."),
        ("seed", "Random-mode seed (blank = new each time)",
         "The seed used is shown in the status bar and saved with images and statistics."),
    )

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Analysis settings")
        self.configure(bg=UI["bg"])
        self.transient(app.root)
        self.resizable(False, False)

        body = ttk.Frame(self, padding=18)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text="Analysis settings", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

        self.vars = {}
        self.estimator = tk.StringVar(master=self)
        ttk.Label(body, text="Dimension estimator").grid(row=1, column=0, sticky="w", pady=(12,0), padx=(0,12))
        ttk.Combobox(body, textvariable=self.estimator, values=list(fc.ESTIMATORS.values()),
                     state="readonly", width=30).grid(row=1, column=1, sticky="ew", pady=(12,0))
        ttk.Label(body, style="Muted.TLabel", wraplength=470, justify="left",
                  text="Classic: fixed box sizes, as in version 1.0. Address counting: counts the occupied cells "
                       "exactly, using only the scales that n values can fill; its maximum is log k / log 2 "
                       "(1.585 for the triangle, 2 for the tetrahedron).").grid(row=2, column=0, columnspan=2, sticky="w")
        r = 3
        for key, label, hint in self.FIELDS:
            self.vars[key] = tk.StringVar(master=self)
            ttk.Label(body, text=label).grid(row=r, column=0, sticky="w", pady=(10,0), padx=(0,12))
            ttk.Entry(body, textvariable=self.vars[key], width=12).grid(row=r, column=1, sticky="w", pady=(10,0))
            ttk.Label(body, text=hint, style="Muted.TLabel", wraplength=470, justify="left").grid(row=r+1, column=0, columnspan=2, sticky="w")
            r += 2
        self._load(app.settings)

        bar = ttk.Frame(body)
        bar.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(16,0))
        ttk.Button(bar, text="Reset to defaults", command=lambda: self._load(fc.Settings())).pack(side=tk.LEFT)
        ttk.Button(bar, text="Apply", style="Accent.TButton", command=self._apply).pack(side=tk.RIGHT)
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=(0,6))
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()

    def _load(self, s):
        self.estimator.set(fc.ESTIMATORS[s.estimator])
        self.vars["outlier"].set(f"{s.outlier_mad:g}")
        self.vars["detrend"].set(str(s.detrend_window))
        self.vars["scale"].set(str(s.scale))
        self.vars["max_n"].set(str(s.max_n))
        self.vars["seed"].set("" if s.seed is None else str(s.seed))

    def _apply(self):
        v = {k: var.get().strip() for k, var in self.vars.items()}
        try:
            settings = fc.Settings(
                estimator=next(k for k, name in fc.ESTIMATORS.items() if name == self.estimator.get()),
                outlier_mad=float(v["outlier"] or 0),
                detrend_window=int(v["detrend"] or 0),
                scale=int(v["scale"] or 1),
                max_n=int(v["max_n"] or 0),
                seed=int(v["seed"]) if v["seed"] else None,
            )
            if settings.outlier_mad < 0 or settings.detrend_window < 0 or settings.scale < 1 or settings.max_n < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid value", "Use non-negative numbers (τ ≥ 1); the seed must be an integer.", parent=self)
            return
        self.destroy()
        self.app.apply_settings(settings)


class StatisticsWindow(tk.Toplevel):
    """Intervalo de confianza, prueba contra sustitutos, D por escala y medidas complementarias."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.results = None
        self.title("Statistics")
        self.configure(bg=UI["bg"])
        self.geometry("880x760")
        self.minsize(760, 640)

        top = ttk.Frame(self, padding=(18,16,18,8))
        top.pack(fill=tk.X)
        for c in (1, 3, 5):
            top.columnconfigure(c, weight=1)
        ttk.Label(top, text="Statistics", style="Title.TLabel").grid(row=0, column=0, columnspan=6, sticky="w")
        ttk.Label(top, style="Muted.TLabel", wraplength=820, justify="left",
                  text=f"Series as prepared by the current settings: {len(app.points):,} values · "
                       f"{fc.ESTIMATORS[app.settings.estimator]}.").grid(row=1, column=0, columnspan=6, sticky="w", pady=(2,8))

        self.tri = tk.BooleanVar(master=self, value=True)
        self.tet = tk.BooleanVar(master=self, value=True)
        self.B = tk.StringVar(master=self, value="200")
        self.block = tk.StringVar(master=self, value="")
        self.M = tk.StringVar(master=self, value="99")
        self.method = tk.StringVar(master=self, value="shuffle")
        self.scales = tk.StringVar(master=self, value="1, 2, 4, 8, 16")
        self.do_measures = tk.BooleanVar(master=self, value=True)

        ttk.Checkbutton(top, text="Triangle (D2)", variable=self.tri).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(top, text="Tetrahedron (D3)", variable=self.tet).grid(row=2, column=1, sticky="w")
        ttk.Checkbutton(top, text="Complementary measures", variable=self.do_measures).grid(row=2, column=2, columnspan=2, sticky="w")
        fields = (
            ("Bootstrap replicates (0 = off)", self.B, 3, 0), ("Block length (blank = √n)", self.block, 3, 2),
            ("Surrogates (0 = off)", self.M, 4, 0), ("Scales τ (blank = off)", self.scales, 4, 4),
        )
        for label, var, row, col in fields:
            ttk.Label(top, text=label).grid(row=row, column=col, sticky="w", pady=(8,0), padx=(0,8))
            ttk.Entry(top, textvariable=var, width=12).grid(row=row, column=col+1, sticky="ew", pady=(8,0), padx=(0,14))
        ttk.Label(top, text="Surrogate type").grid(row=4, column=2, sticky="w", pady=(8,0), padx=(0,8))
        ttk.Combobox(top, textvariable=self.method, values=list(fc.SURROGATES), state="readonly",
                     width=10).grid(row=4, column=3, sticky="ew", pady=(8,0), padx=(0,14))

        bar = ttk.Frame(top)
        bar.grid(row=5, column=0, columnspan=6, sticky="ew", pady=(12,0))
        self.btn_run = ttk.Button(bar, text="Run", style="Accent.TButton", command=self._run)
        self.btn_run.pack(side=tk.LEFT)
        self.btn_export = ttk.Button(bar, text="Export…", command=self._export, state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=(6,0))
        self.progress = ttk.Label(bar, style="Muted.TLabel")
        self.progress.pack(side=tk.LEFT, padx=(12,0))

        box = ttk.Frame(self)
        box.pack(fill=tk.X, padx=18)
        self.text = tk.Text(box, height=16, bg=UI["card"], fg=UI["text"], insertbackground=UI["text"],
                            relief="flat", font=("DejaVu Sans Mono", 10), padx=12, pady=10, wrap="word")
        scroll = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.text.insert("1.0", "Choose the analyses and press Run.\n\n"
                                "Bootstrap: moving-block resampling of the series; 95 % percentile interval for D.\n"
                                "Surrogates: shuffle keeps the values and destroys their order; IAAFT also keeps the "
                                "power spectrum. z and p compare D with the surrogate distribution.\n"
                                "Scales: D after averaging windows of τ values; n falls as τ grows.")
        self.text.config(state=tk.DISABLED)

        self.fig = plt.Figure(figsize=(8, 3.2), dpi=100, facecolor=UI["bg"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().configure(highlightthickness=0, bg=UI["bg"])
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=18, pady=(10,16))

    def _params(self):
        figures = [k for k, v in (("triangle", self.tri), ("tetrahedron", self.tet)) if v.get()]
        if not figures:
            raise ValueError("Select at least one figure.")
        scales = [int(s) for s in self.scales.get().replace(";", ",").split(",") if s.strip()]
        if any(s < 1 for s in scales):
            raise ValueError("Scales must be integers ≥ 1.")
        B, M = int(self.B.get() or 0), int(self.M.get() or 0)
        block = int(self.block.get()) if self.block.get().strip() else None
        if B < 0 or M < 0 or (block is not None and block < 1):
            raise ValueError("Use non-negative integers.")
        return {"figures": figures, "B": B, "block": block, "M": M, "method": self.method.get(),
                "scales": scales, "measures": self.do_measures.get()}

    def _run(self):
        try:
            params = self._params()
        except ValueError as e:
            messagebox.showerror("Invalid value", str(e) or "Check the numeric fields.", parent=self)
            return
        settings = self.app.settings
        seed = settings.seed if settings.seed is not None else int(np.random.SeedSequence().generate_state(1)[0])
        y = self.app.points.copy()
        self.btn_run.config(state=tk.DISABLED)
        self.btn_export.config(state=tk.DISABLED)
        self.progress.config(text="Computing…")

        def work():
            try:
                rng = np.random.default_rng(seed)
                res = {"seed": seed, "n": int(len(y)), "estimator": settings.estimator, "params": params, "figures": {}}
                for kind in params["figures"]:
                    r = {"D": float(fc.series_dimension(y, kind, settings.estimator))}
                    if params["B"]:
                        r["bootstrap"] = fc.bootstrap_ci(y, kind, settings.estimator, B=params["B"], block=params["block"], rng=rng)
                    if params["M"]:
                        r["surrogates"] = fc.surrogate_test(y, kind, settings.estimator, M=params["M"], method=params["method"], rng=rng)
                    if params["scales"]:
                        r["multiscale"] = fc.multiscale(y, kind, settings.estimator, params["scales"])
                    res["figures"][kind] = r
                if params["measures"]:
                    res["measures"] = fc.measures(y)
                self.after(0, lambda: self._done(res))
            except Exception as e:
                self.after(0, lambda: self._failed(e))

        threading.Thread(target=work, daemon=True).start()

    def _failed(self, error):
        self.btn_run.config(state=tk.NORMAL)
        self.progress.config(text="")
        messagebox.showerror("Error", str(error), parent=self)

    def _done(self, res):
        self.results = res
        self.btn_run.config(state=tk.NORMAL)
        self.btn_export.config(state=tk.NORMAL)
        self.progress.config(text=f"Done · seed {res['seed']}")
        names = {"triangle": "Triangle (D2)", "tetrahedron": "Tetrahedron (D3)"}
        lines = [f"{os.path.basename(self.app.source_path)} · n = {res['n']:,} · {fc.ESTIMATORS[res['estimator']]} · seed {res['seed']}", ""]
        for kind, r in res["figures"].items():
            lines.append(names[kind])
            lines.append(f"  D = {r['D']:.4f}")
            if "bootstrap" in r:
                b = r["bootstrap"]
                lines.append(f"  95 % CI [{b['ci_low']:.4f}, {b['ci_high']:.4f}] · SE {b['se']:.4f} · bias {b['bias']:+.4f}"
                             f"  (B = {b['B']}, block = {b['block']})")
                if not b["ci_low"] <= r["D"] <= b["ci_high"]:
                    lines.append("  ! D lies outside the interval: resampling bias at block joins; try a longer block.")
            if "surrogates" in r:
                s = r["surrogates"]
                z = "undefined (all surrogates equal)" if np.isnan(s["z"]) else f"{s['z']:.2f}"
                lines.append(f"  Surrogates ({s['method']}, M = {s['M']}): mean {s['surrogate_mean']:.4f} ± {s['surrogate_sd']:.4f}, "
                             f"z = {z}, p = {s['p']:.3f}")
            if "multiscale" in r:
                lines.append("  Scales: " + "  ".join(f"τ={m['scale']}: {m['D']:.3f} (n={m['n']})" for m in r["multiscale"]))
            lines.append("")
        if "measures" in res:
            m = res["measures"]
            lines.append("Complementary measures")
            lines.append(f"  mean {m['mean']:.4g} · SD {m['sd']:.4g} · CV {m['cv']:.4g} · RMSSD {m['rmssd']:.4g}")
            lines.append(f"  DFA α {m['dfa_alpha']:.3f} · sample entropy (m = 2, r = 0.2 SD) {m['sample_entropy']:.3f}")
        if res["estimator"] == "classic" and any("multiscale" in r for r in res["figures"].values()):
            lines.append("\nNote: the classic estimator depends on n, which falls with τ; address counting is better suited to compare scales.")
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", "\n".join(lines))
        self.text.config(state=tk.DISABLED)
        self._plot(res)

    def _plot(self, res):
        self.fig.clf()
        series = [(k, r["multiscale"]) for k, r in res["figures"].items() if "multiscale" in r]
        if not series:
            self.canvas.draw()
            return
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(UI["bg"])
        colors = {"triangle": "#4a94e6", "tetrahedron": "#e4604b"}
        for kind, ms in series:
            ax.plot([m["scale"] for m in ms], [m["D"] for m in ms], marker="o", color=colors[kind],
                    label="D2 (triangle)" if kind == "triangle" else "D3 (tetrahedron)")
        ax.set_xscale("log", base=2)
        ax.set_xticks([m["scale"] for m in series[0][1]], [str(m["scale"]) for m in series[0][1]])
        ax.set_xlabel("Scale τ (values averaged)", color=UI["muted"])
        ax.set_ylabel("D", color=UI["muted"])
        ax.tick_params(colors=UI["muted"])
        for spine in ax.spines.values():
            spine.set_color(UI["border"])
        ax.grid(color=UI["border"], linewidth=0.5)
        ax.legend(facecolor=UI["card"], edgecolor=UI["border"], labelcolor=UI["text"])
        self.fig.tight_layout()
        self.canvas.draw()

    def _export(self):
        fp = self.app._ask_save(".json", "JSON", initial="fractal_statistics.json")
        if not fp:
            return
        meta = {"fractalapp_version": fc.__version__, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "input_file": self.app.source_path, "conversion": self.app.source,
                "settings": self.app.settings.to_dict(), "preprocessing": self.app.prep_info, "results": self.results}
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        # Versión plana en CSV: una fila por magnitud
        rows = [("n", self.results["n"]), ("seed", self.results["seed"]), ("estimator", self.results["estimator"])]
        for kind, r in self.results["figures"].items():
            tag = "D2" if kind == "triangle" else "D3"
            rows.append((tag, r["D"]))
            for k, v in r.get("bootstrap", {}).items():
                rows.append((f"{tag}_bootstrap_{k}", v))
            for k, v in r.get("surrogates", {}).items():
                rows.append((f"{tag}_surrogate_{k}", v))
            for m in r.get("multiscale", []):
                rows.append((f"{tag}_scale{m['scale']}", m["D"]))
        rows += [(k, v) for k, v in self.results.get("measures", {}).items()]
        with open(os.path.splitext(fp)[0] + ".csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["quantity", "value"])
            w.writerows(rows)
        self.progress.config(text=f"Exported {os.path.basename(fp)} and .csv")


class FractalApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Fractal Generator - Sierpinski Triangle & Tetrahedron")
        self.root.geometry("1150x800")
        self.root.minsize(900, 780)
        self.root.configure(bg=UI["bg"])
        self._setup_style()

        # ====== Layout principal ======
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # ====== Panel lateral ======
        side = ttk.Frame(main, style="Side.TFrame", padding=18)
        side.pack(side=tk.LEFT, fill=tk.Y)
        side.columnconfigure((0,1,2), weight=1, uniform="modes")

        ttk.Label(side, text="Fractal Options", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")

        # Archivo
        self._section(side, "Data File", 1)
        ttk.Button(side, text="Browse", command=self.browse_file, style="Accent.TButton").grid(row=2, column=0, columnspan=3, sticky="ew")
        self.file_label = ttk.Label(side, text="No file loaded", style="Muted.TLabel", wraplength=270)
        self.file_label.grid(row=3, column=0, columnspan=3, sticky="w", pady=(6,0))

        # Análisis: opciones y estadística
        self._section(side, "Analysis", 4)
        ttk.Button(side, text="Settings…", command=self.open_settings).grid(row=5, column=0, columnspan=2, sticky="ew", padx=(0,3))
        self.btn_stats = ttk.Button(side, text="Statistics…", command=self.open_statistics, state=tk.DISABLED)
        self.btn_stats.grid(row=5, column=2, sticky="ew", padx=(3,0))
        self.settings_label = ttk.Label(side, style="Muted.TLabel", wraplength=270, justify="left")
        self.settings_label.grid(row=6, column=0, columnspan=3, sticky="w", pady=(6,0))

        # ---- Botones de fractales ----
        self._section(side, "Sierpinski Triangle (2D)", 7)
        self._section(side, "Sierpinski Tetrahedron (3D)", 9)
        for col, mode in enumerate(MODES):
            pad = (0 if col == 0 else 3, 0 if col == 2 else 3)
            ttk.Button(side, text=MODE_LABELS[mode], style=f"{mode}.TButton",
                       command=lambda m=mode: self.generate_triangle(m)).grid(row=8, column=col, sticky="ew", padx=pad)
            ttk.Button(side, text=MODE_LABELS[mode], style=f"{mode}.TButton",
                       command=lambda m=mode: self.generate_tetrahedron(m)).grid(row=10, column=col, sticky="ew", padx=pad)

        # Dimensión fractal
        self._section(side, "Fractal Dimension", 11)
        card = ttk.Frame(side, style="Card.TFrame", padding=(14,8))
        card.grid(row=12, column=0, columnspan=3, sticky="ew")
        self.dim_label = ttk.Label(card, text="-", style="Metric.TLabel")
        self.dim_label.pack(anchor="w")
        self.dim_caption = ttk.Label(card, text="Box-counting estimate", style="CardMuted.TLabel")
        self.dim_caption.pack(anchor="w")

        # Guardar
        self._section(side, "Save", 13)
        self.btn_image = ttk.Button(side, text="Save Image (PNG)", command=self.save_image, state=tk.DISABLED)
        self.btn_image.grid(row=14, column=0, columnspan=3, sticky="ew", pady=(0,4))
        self.btn_gif = ttk.Button(side, text="Save GIF (3D)", command=self.save_gif, state=tk.DISABLED)
        self.btn_gif.grid(row=15, column=0, columnspan=3, sticky="ew")
        self.light_plot = tk.BooleanVar(master=self.root, value=False)
        ttk.Checkbutton(side, text="White plot background", variable=self.light_plot,
                        command=self._render).grid(row=16, column=0, columnspan=3, sticky="w", pady=(8,0))

        # Instrucciones
        self._section(side, "Notes", 17)
        ttk.Label(side, style="Muted.TLabel", justify="left",
                  text="Single-column files; gyroscope CSV and .ts\nfiles are converted on load. Triangle uses 3\nlabels, tetrahedron 4, Random random labels.\nSaved images get a .json with all parameters."
                  ).grid(row=18, column=0, columnspan=3, sticky="w")

        # ====== Panel de gráfica ======
        self.frame_plot = ttk.Frame(main)
        self.frame_plot.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status = tk.StringVar(master=self.root, value="Ready")
        ttk.Label(self.frame_plot, textvariable=self.status, style="Status.TLabel", padding=(14,6)).pack(side=tk.BOTTOM, fill=tk.X)

        self.fig = plt.Figure(figsize=(8,7), dpi=100)
        self.ax = None
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_plot)
        self.canvas.get_tk_widget().configure(highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Variables
        self.settings = fc.Settings()
        self.raw = None
        self.points = None
        self.prep_info = {}
        self.source = None
        self.source_path = None
        self.seed_used = None
        self.fractal = None
        self.kind = None
        self.mode = None
        self.dimension = None
        self.last_dir = None

        self._update_settings_label()
        self._render()

    # ---------------- Estilo ----------------
    def _setup_style(self):
        families = set(tkfont.families(self.root))
        family = next((f for f in ("Segoe UI", "Inter", "Cantarell", "Noto Sans", "DejaVu Sans") if f in families), tkfont.nametofont("TkDefaultFont", root=self.root).actual("family"))

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=UI["bg"], foreground=UI["text"], font=(family, 10),
                        bordercolor=UI["border"], lightcolor=UI["border"], darkcolor=UI["border"], focuscolor=UI["accent"])
        style.configure("Side.TFrame", background=UI["bg"])
        style.configure("Card.TFrame", background=UI["card"])
        style.configure("Title.TLabel", font=(family, 15, "bold"))
        style.configure("Section.TLabel", font=(family, 10, "bold"), foreground=UI["muted"])
        style.configure("Muted.TLabel", font=(family, 9), foreground=UI["muted"])
        style.configure("Metric.TLabel", font=(family, 22, "bold"), background=UI["card"])
        style.configure("CardMuted.TLabel", font=(family, 9), foreground=UI["muted"], background=UI["card"])
        style.configure("Status.TLabel", font=(family, 9), foreground=UI["muted"], background=UI["card"])

        style.configure("TButton", background=UI["card"], padding=(8,6), relief="flat", width=-7)
        style.map("TButton", background=[("disabled", UI["bg"]), ("active", UI["border"])],
                  foreground=[("disabled", UI["disabled"])])
        filled = {"Accent": ("#2f6fde", "#4a94e6")}
        filled.update({mode: MODE_BUTTONS[mode] for mode in MODES})
        for name, (base, hover) in filled.items():
            style.configure(f"{name}.TButton", background=base, foreground="#ffffff",
                            bordercolor=base, lightcolor=base, darkcolor=base)
            style.map(f"{name}.TButton", background=[("active", hover)],
                      lightcolor=[("active", hover)], darkcolor=[("active", hover)])

        style.configure("TCheckbutton", font=(family, 9), foreground=UI["muted"], indicatorbackground=UI["card"])
        style.map("TCheckbutton", background=[("active", UI["bg"])],
                  indicatorbackground=[("selected", UI["accent"])])

        style.configure("Place.TButton", background=UI["bg"], foreground=UI["text"], anchor="w",
                        bordercolor=UI["bg"], lightcolor=UI["bg"], darkcolor=UI["bg"], width=11)
        style.map("Place.TButton", background=[("active", UI["card"])],
                  lightcolor=[("active", UI["card"])], darkcolor=[("active", UI["card"])])
        style.configure("TEntry", fieldbackground=UI["card"], foreground=UI["text"], insertcolor=UI["text"], padding=5)
        style.map("TEntry", bordercolor=[("focus", UI["accent"])], lightcolor=[("focus", UI["accent"])])
        style.configure("TCombobox", fieldbackground=UI["card"], background=UI["card"], foreground=UI["text"],
                        arrowcolor=UI["muted"], padding=4)
        style.map("TCombobox", fieldbackground=[("readonly", UI["card"])], foreground=[("readonly", UI["text"])],
                  selectbackground=[("readonly", UI["card"])], selectforeground=[("readonly", UI["text"])])
        self.root.option_add("*TCombobox*Listbox.background", UI["card"])
        self.root.option_add("*TCombobox*Listbox.foreground", UI["text"])
        style.configure("Treeview", background=UI["card"], fieldbackground=UI["card"], foreground=UI["text"],
                        rowheight=26, borderwidth=0)
        style.map("Treeview", background=[("selected", "#245fbf")], foreground=[("selected", "#ffffff")])
        style.configure("Treeview.Heading", background=UI["bg"], foreground=UI["muted"], relief="flat", padding=(6,5))
        style.map("Treeview.Heading", background=[("active", UI["border"])])
        style.configure("Vertical.TScrollbar", background=UI["border"], troughcolor=UI["bg"],
                        arrowcolor=UI["muted"], bordercolor=UI["bg"])
        style.map("Vertical.TScrollbar", background=[("active", UI["disabled"])])

    def _section(self, parent, text, row):
        ttk.Label(parent, text=text, style="Section.TLabel").grid(row=row, column=0, columnspan=3, sticky="w", pady=(14,5))

    # ---------------- Archivo ----------------
    def _start_dir(self):
        if self.last_dir:
            return self.last_dir
        return DATA_DIR if os.path.isdir(DATA_DIR) else os.path.expanduser("~")

    def _uses_tk_dialogs(self):
        return self.root.tk.call("tk", "windowingsystem") == "x11"

    def _ask_open(self):
        if self._uses_tk_dialogs():
            fp = FileBrowser(self.root, "Open data file", (".txt", ".csv", ".dat", ".ts"), self._start_dir()).show()
        else:
            fp = filedialog.askopenfilename(initialdir=self._start_dir(),
                                            filetypes=[("Text or CSV", ("*.txt", "*.csv", "*.dat", "*.ts")), ("All", "*.*")])
        if fp:
            self.last_dir = os.path.dirname(fp)
        return fp

    def _ask_save(self, extension, label, initial=None):
        initial = initial or f"sierpinski_{self.kind}_{self.mode}{extension}"
        if self._uses_tk_dialogs():
            fp = FileBrowser(self.root, f"Save {label}", (extension,), self._start_dir(), save=True, initial=initial).show()
        else:
            fp = filedialog.asksaveasfilename(initialdir=self._start_dir(), initialfile=initial,
                                              defaultextension=extension, filetypes=[(label, f"*{extension}")])
        if fp:
            self.last_dir = os.path.dirname(fp)
        return fp

    def browse_file(self):
        fp = self._ask_open()
        if fp:
            try:
                self.raw, self.source = fc.load_series(fp)
                self.source_path = fp
                self._prepare()
                self.btn_stats.config(state=tk.NORMAL)
                self.status.set(f"{len(self.raw):,} values loaded from {fp}" + (f" ({self.source})" if self.source else ""))
            except Exception as e:
                messagebox.showerror("Error", f"Could not load file:\n{e}")

    def _prepare(self):
        # Aplica el preprocesamiento elegido a la serie cargada
        self.points, self.prep_info = fc.preprocess(self.raw, self.settings)
        lines = [os.path.basename(self.source_path), f"{self.prep_info['n_raw']:,} values"]
        if self.prep_info["n_used"] != self.prep_info["n_raw"]:
            lines[1] += f" · {self.prep_info['n_used']:,} used"
        if self.prep_info["n_nonfinite_removed"]:
            lines.append(f"{self.prep_info['n_nonfinite_removed']:,} missing values removed")
        if self.prep_info["n_outliers_corrected"]:
            lines.append(f"{self.prep_info['n_outliers_corrected']:,} outliers corrected")
        if self.source:
            lines.append(f"Converted: {self.source}")
        self.file_label.config(text="\n".join(lines))

    def _update_settings_label(self):
        s = self.settings
        steps = []
        if s.outlier_mad > 0: steps.append(f"outliers > {s.outlier_mad:g} SD")
        if s.detrend_window > 1: steps.append(f"detrend {s.detrend_window}")
        if s.scale > 1: steps.append(f"scale τ = {s.scale}")
        if s.max_n > 0: steps.append(f"first {s.max_n:,} values")
        seed = f" · seed {s.seed}" if s.seed is not None else ""
        self.settings_label.config(text=f"{ESTIMATOR_SHORT[s.estimator]}{seed}\n" + (", ".join(steps) if steps else "No preprocessing"))

    # ---------------- FRACTALES ----------------
    def generate_triangle(self, mode):
        self._generate("triangle", mode)

    def generate_tetrahedron(self, mode):
        self._generate("tetrahedron", mode)

    def _generate(self, kind, mode):
        if self.points is None:
            messagebox.showerror("Error", "Please load a data file first.")
            return
        k = 3 if kind == "triangle" else 4
        if len(self.points) < k:
            messagebox.showerror("Error", f"Need at least {k} values.")
            return
        if mode == "random":
            self.seed_used = self.settings.seed if self.settings.seed is not None else int(np.random.SeedSequence().generate_state(1)[0])
            labels = fc.random_symbols(len(self.points), k, np.random.default_rng(self.seed_used))
        else:
            self.seed_used = None
            labels = fc.symbolize(self.points, k)
        pts = fc.chaos_game(labels, kind)
        try:
            D = fc.dimension(labels, kind, self.settings.estimator, pts)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self._show(kind, mode, pts, D)

    # ---------------- GRÁFICAS ----------------
    def _show(self, kind, mode, pts, D):
        self.kind, self.mode, self.fractal, self.dimension = kind, mode, pts, D
        name = "Triangle" if kind == "triangle" else "Tetrahedron"
        self.dim_label.config(text=f"{D:.4f}")
        self.dim_caption.config(text=f"{ESTIMATOR_SHORT[self.settings.estimator]} · {name} · {MODE_LABELS[mode]}")
        self.btn_image.config(state=tk.NORMAL)
        self.btn_gif.config(state=tk.NORMAL if kind == "tetrahedron" else tk.DISABLED)
        seed = f" · seed {self.seed_used}" if self.seed_used is not None else ""
        self.status.set(f"{name} generated from {len(pts):,} points{seed}")
        self._render()

    def _render(self):
        theme = PLOT_THEMES["light" if self.light_plot.get() else "dark"]
        self.fig.clf()
        self.fig.set_facecolor(theme["bg"])
        self.canvas.get_tk_widget().configure(bg=theme["bg"])

        if self.fractal is None:
            self.ax = None
            self.fig.text(0.5, 0.52, "No fractal yet", ha="center", color=theme["text"], fontsize=15, weight="bold")
            self.fig.text(0.5, 0.47, "Load a data file, then choose a group in the side panel",
                          ha="center", color=theme["muted"], fontsize=10)
        elif self.kind == "triangle":
            self._draw_triangle(theme)
        else:
            self._draw_tetrahedron(theme)
        self.canvas.draw()

    def _header(self, theme, title):
        self.fig.text(0.04, 0.945, f"{title} — {self.mode.capitalize()}",
                      color=theme["text"], fontsize=14, weight="bold")
        self.fig.text(0.04, 0.91, f"n = {len(self.fractal):,}   ·   D = {self.dimension:.4f}",
                      color=theme["muted"], fontsize=10)

    def _vertex_names(self, count):
        if self.mode == "random":
            return [f"Label {i+1}" for i in range(count)]
        if count == 3:
            return ["Low tercile", "Mid tercile", "High tercile"]
        return [f"Quartile {i+1}" for i in range(count)]

    def _draw_triangle(self, theme):
        pts = self.fractal
        color = self._color_by_mode(self.mode, theme)
        self._header(theme, "Sierpinski Triangle (2D)")

        ax = self.fig.add_axes([0.06, 0.05, 0.88, 0.82])
        outline = TRIANGLE_VERTS[[0,1,2,0]]
        ax.plot(outline[:,0], outline[:,1], color=theme["frame"], linewidth=0.8, zorder=1)
        if theme["halo"]:
            ax.scatter(pts[:,0], pts[:,1], s=14, color=color, alpha=theme["halo"], linewidths=0, zorder=2)
        ax.scatter(pts[:,0], pts[:,1], s=2.5, color=color, linewidths=0, zorder=3)

        offsets = [(0,-13), (0,-13), (0,7)]
        for vert, name, off in zip(TRIANGLE_VERTS, self._vertex_names(3), offsets):
            ax.annotate(name, vert, xytext=off, textcoords="offset points", ha="center",
                        color=theme["muted"], fontsize=9, annotation_clip=False)
        ax.axis("off")
        ax.set_aspect("equal")
        self.ax = ax

    def _draw_tetrahedron(self, theme):
        pts = self.fractal
        color = self._color_by_mode(self.mode, theme)
        self._header(theme, "Sierpinski Tetrahedron (3D)")

        ax = self.fig.add_axes([0, 0, 1, 0.9], projection="3d")
        ax.set_facecolor(theme["bg"])
        V = TETRAHEDRON_VERTS
        for a in range(4):
            for b in range(a+1, 4):
                ax.plot(V[[a,b],0], V[[a,b],1], V[[a,b],2], color=theme["frame"], linewidth=0.8)
        if theme["halo"]:
            ax.scatter(pts[:,0], pts[:,1], pts[:,2], s=12, color=color, alpha=theme["halo"], linewidths=0)
        ax.scatter(pts[:,0], pts[:,1], pts[:,2], s=2.5, color=color, linewidths=0)

        for vert, name in zip(V, self._vertex_names(4)):
            ax.text(vert[0], vert[1], vert[2], f" {name}", color=theme["muted"], fontsize=9)
        ax.axis("off")
        ax.set_box_aspect([1,1,1], zoom=1.05)
        self.ax = ax

    # ---------------- CÁLCULOS ----------------
    def _color_by_mode(self, mode, theme):
        return theme["colors"][mode]

    # ---------------- GUARDADO ----------------
    def _metadata(self, output):
        return {
            "fractalapp_version": fc.__version__,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "output": os.path.basename(output),
            "input_file": self.source_path,
            "conversion": self.source,
            "settings": self.settings.to_dict(),
            "preprocessing": self.prep_info,
            "figure": self.kind,
            "mode": MODE_LABELS[self.mode],
            "random_seed": self.seed_used,
            "estimator": fc.ESTIMATORS[self.settings.estimator],
            "dimension": float(self.dimension),
            "points": int(len(self.fractal)),
        }

    def _write_metadata(self, output):
        # Guarda junto a la imagen los parámetros que la generaron, para poder reproducirla
        with open(os.path.splitext(output)[0] + ".json", "w", encoding="utf-8") as f:
            json.dump(self._metadata(output), f, indent=2, ensure_ascii=False)

    def save_image(self):
        if self.fractal is None:
            messagebox.showerror("Error", "No fractal generated.")
            return
        fp = self._ask_save(".png", "PNG")
        if fp:
            self.fig.savefig(fp, dpi=300)
            self._write_metadata(fp)
            self.status.set(f"Image saved: {fp} (parameters in .json)")

    def save_gif(self):
        if self.fractal is None or self.kind != "tetrahedron":
            messagebox.showerror("Error", "Generate a tetrahedron first.")
            return
        fp = self._ask_save(".gif", "GIF")
        if not fp: return

        out_dir = os.path.splitext(fp)[0] + "_frames"
        os.makedirs(out_dir, exist_ok=True)
        frames = []
        angles = range(0,360,5)
        elev, azim = self.ax.elev, self.ax.azim

        for i, ang in enumerate(angles):
            self.status.set(f"Rendering GIF frame {i+1}/{len(angles)}…")
            self.root.update_idletasks()
            self.ax.view_init(30, ang)
            self.fig.canvas.draw()
            buf, size = self.fig.canvas.print_to_buffer()
            img = np.frombuffer(buf, dtype=np.uint8).reshape(size[1], size[0], 4)
            img = img[:,:,:3]
            frames.append(img)
            plt.imsave(os.path.join(out_dir, f"frame_{i:03d}.png"), img)

        imageio.mimsave(fp, frames, fps=15)
        self._write_metadata(fp)
        self.ax.view_init(elev, azim)
        self.canvas.draw()
        self.status.set(f"GIF saved: {fp} — frames in {out_dir}")

    # ---------------- ANÁLISIS ----------------
    def open_settings(self):
        SettingsDialog(self)

    def apply_settings(self, settings):
        self.settings = settings
        self._update_settings_label()
        if self.raw is None:
            return
        self._prepare()
        if self.fractal is not None:
            self._generate(self.kind, self.mode)

    def open_statistics(self):
        if self.points is None:
            messagebox.showerror("Error", "Please load a data file first.")
            return
        StatisticsWindow(self)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = FractalApp()
    app.run()
