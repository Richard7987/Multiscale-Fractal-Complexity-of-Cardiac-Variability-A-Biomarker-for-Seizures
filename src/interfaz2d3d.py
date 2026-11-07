# -*- coding: utf-8 -*-
"""
FractalApp - Sierpinski Triangle (2D) & Tetrahedron (3D)
Author: Alma 💙
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import imageio, os, time

from giroscopio_a_serie import magnitud_giroscopio
from gaitndd_a_serie import intervalos_zancada

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

TRIANGLE_VERTS = np.array([
    [0,0],
    [1,0],
    [0.5,1]
])
TETRAHEDRON_VERTS = np.array([
    [0,0,0],
    [1,0,0],
    [0.5,np.sqrt(3)/2,0],
    [0.5,np.sqrt(3)/6,np.sqrt(6)/3]
])

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


class FractalApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Fractal Generator - Sierpinski Triangle & Tetrahedron")
        self.root.geometry("1150x720")
        self.root.minsize(900, 720)
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

        # ---- Botones de fractales ----
        self._section(side, "Sierpinski Triangle (2D)", 4)
        self._section(side, "Sierpinski Tetrahedron (3D)", 6)
        for col, mode in enumerate(MODES):
            pad = (0 if col == 0 else 3, 0 if col == 2 else 3)
            ttk.Button(side, text=MODE_LABELS[mode], style=f"{mode}.TButton",
                       command=lambda m=mode: self.generate_triangle(m)).grid(row=5, column=col, sticky="ew", padx=pad)
            ttk.Button(side, text=MODE_LABELS[mode], style=f"{mode}.TButton",
                       command=lambda m=mode: self.generate_tetrahedron(m)).grid(row=7, column=col, sticky="ew", padx=pad)

        # Dimensión fractal
        self._section(side, "Fractal Dimension", 8)
        card = ttk.Frame(side, style="Card.TFrame", padding=(14,8))
        card.grid(row=9, column=0, columnspan=3, sticky="ew")
        self.dim_label = ttk.Label(card, text="-", style="Metric.TLabel")
        self.dim_label.pack(anchor="w")
        self.dim_caption = ttk.Label(card, text="Box-counting estimate", style="CardMuted.TLabel")
        self.dim_caption.pack(anchor="w")

        # Guardar
        self._section(side, "Save", 10)
        self.btn_image = ttk.Button(side, text="Save Image (PNG)", command=self.save_image, state=tk.DISABLED)
        self.btn_image.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(0,4))
        self.btn_gif = ttk.Button(side, text="Save GIF (3D)", command=self.save_gif, state=tk.DISABLED)
        self.btn_gif.grid(row=12, column=0, columnspan=3, sticky="ew")
        self.light_plot = tk.BooleanVar(master=self.root, value=False)
        ttk.Checkbutton(side, text="White plot background", variable=self.light_plot,
                        command=self._render).grid(row=13, column=0, columnspan=3, sticky="w", pady=(8,0))

        # Instrucciones
        self._section(side, "Notes", 14)
        ttk.Label(side, style="Muted.TLabel", justify="left",
                  text="Load a single-column data file.\nGyroscope CSV (ParkinSenseDB) and .ts\n(gaitndd) files are converted on load.\nTriangle uses 3 labels.\nTetrahedron uses 4 labels.\nRandom assigns random labels."
                  ).grid(row=15, column=0, columnspan=3, sticky="w")

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
        self.points = None
        self.fractal = None
        self.kind = None
        self.mode = None
        self.dimension = None
        self.last_dir = None

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

    def _ask_save(self, extension, label):
        initial = f"sierpinski_{self.kind}_{self.mode}{extension}"
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
                self.points, source = self._load_series(fp)
                note = f"\nConverted: {source}" if source else ""
                self.file_label.config(text=f"{os.path.basename(fp)}\n{len(self.points):,} values{note}")
                self.status.set(f"{len(self.points):,} values loaded from {fp}" + (f" ({source})" if source else ""))
            except Exception as e:
                messagebox.showerror("Error", f"Could not load file:\n{e}")

    def _load_series(self, filepath):
        # Los formatos con convertidor se transforman al cargar; el resto se lee como una columna
        if filepath.lower().endswith(".ts"):
            return intervalos_zancada(filepath), "gaitndd stride intervals"
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
        if "Gyroscope" in first_line:
            return magnitud_giroscopio(filepath), "gyroscope VMω, walking only"
        return self._read_column(filepath), None

    def _read_column(self, filepath):
        try:
            y = pd.read_csv(filepath, sep="\t", header=None, engine="python").values.squeeze()
        except Exception:
            try:
                y = pd.read_csv(filepath, header=None).values.squeeze()
            except Exception:
                y = np.loadtxt(filepath)
        return np.asarray(y).reshape(-1)

    # ---------------- TRIÁNGULO ----------------
    def generate_triangle(self, mode):
        if self.points is None:
            messagebox.showerror("Error", "Please load a data file first.")
            return

        Y = self.points
        p = len(Y)
        if p < 3:
            messagebox.showerror("Error", "Need at least 3 values.")
            return

        arr = np.column_stack((Y, np.zeros(p)))

        if mode == "random":
            np.random.shuffle(arr)
            arr[:,1] = np.random.randint(1, 4, size=p)
        else:
            idx = np.argsort(arr[:,0])
            Y2 = arr[idx]
            t = p // 3
            Y2[:t,1]=1; Y2[t:2*t,1]=2; Y2[2*t:,1]=3
            arr = Y2[np.argsort(idx)]

        # Vértices del triángulo
        p1, p2, p3 = TRIANGLE_VERTS
        current = np.array([0.5,0.5])
        pts = np.zeros((p,2))

        for f in range(p):
            lab = int(arr[f,1])
            if lab==1: current=(current+p1)/2
            elif lab==2: current=(current+p2)/2
            else: current=(current+p3)/2
            pts[f,:]=current

        self._show("triangle", mode, pts, self._box_counting_2d(pts))

    # ---------------- TETRAEDRO ----------------
    def generate_tetrahedron(self, mode):
        if self.points is None:
            messagebox.showerror("Error", "Please load a data file first.")
            return

        Y = self.points
        p = len(Y)
        if p < 4:
            messagebox.showerror("Error", "Need at least 4 values.")
            return

        arr = np.column_stack((Y, np.zeros(p)))

        if mode == "random":
            arr[:,1] = np.random.randint(1, 5, size=p)
        else:
            idx = np.argsort(arr[:,0])
            Y2 = arr[idx]
            t = p // 4
            Y2[:t,1]=1; Y2[t:2*t,1]=2; Y2[2*t:3*t,1]=3; Y2[3*t:,1]=4
            arr = Y2[np.argsort(idx)]

        verts = TETRAHEDRON_VERTS
        current = np.array([0.5,np.sqrt(3)/6,np.sqrt(6)/12])
        pts = np.zeros((p,3))
        for f in range(p):
            v = verts[int(arr[f,1])-1]
            current = (current+v)/2
            pts[f,:]=current

        self._show("tetrahedron", mode, pts, self._box_counting_3d(pts))

    # ---------------- GRÁFICAS ----------------
    def _show(self, kind, mode, pts, D):
        self.kind, self.mode, self.fractal, self.dimension = kind, mode, pts, D
        name = "Triangle" if kind == "triangle" else "Tetrahedron"
        self.dim_label.config(text=f"{D:.4f}")
        self.dim_caption.config(text=f"Box-counting · {name} · {MODE_LABELS[mode]}")
        self.btn_image.config(state=tk.NORMAL)
        self.btn_gif.config(state=tk.NORMAL if kind == "tetrahedron" else tk.DISABLED)
        self.status.set(f"{name} generated from {len(pts):,} points")
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

    def _box_counting_2d(self, pts):
        P = (pts - pts.min(0)) / (pts.max(0)-pts.min(0))
        sizes = np.logspace(-3, 0, 10)
        counts = []
        for s in sizes:
            idx = np.floor(P/s).astype(int)
            counts.append(len(np.unique(idx[:,0]*1000+idx[:,1])))
        D = np.polyfit(np.log(1/sizes), np.log(counts), 1)[0]
        return D

    def _box_counting_3d(self, pts):
        P = (pts - pts.min(0)) / (pts.max(0)-pts.min(0))
        eps = np.logspace(np.log10(0.005), np.log10(0.3), 10)
        N = []
        for e in eps:
            idx = np.floor(P/e).astype(int)
            N.append(len(np.unique(idx[:,0]*1e6+idx[:,1]*1e3+idx[:,2])))
        D = np.polyfit(np.log(1/eps), np.log(N), 1)[0]
        return D

    # ---------------- GUARDADO ----------------
    def save_image(self):
        if self.fractal is None:
            messagebox.showerror("Error", "No fractal generated.")
            return
        fp = self._ask_save(".png", "PNG")
        if fp:
            self.fig.savefig(fp, dpi=300)
            self.status.set(f"Image saved: {fp}")

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
        self.ax.view_init(elev, azim)
        self.canvas.draw()
        self.status.set(f"GIF saved: {fp} — frames in {out_dir}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = FractalApp()
    app.run()
