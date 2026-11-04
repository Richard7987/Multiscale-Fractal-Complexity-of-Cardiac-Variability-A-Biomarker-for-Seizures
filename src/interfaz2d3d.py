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
import imageio, os


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
                  text="Load a single-column data file.\nTriangle uses 3 labels.\nTetrahedron uses 4 labels.\nRandom assigns random labels."
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

    def _section(self, parent, text, row):
        ttk.Label(parent, text=text, style="Section.TLabel").grid(row=row, column=0, columnspan=3, sticky="w", pady=(14,5))

    # ---------------- Archivo ----------------
    def browse_file(self):
        fp = filedialog.askopenfilename(filetypes=[("Text or CSV", ("*.txt", "*.csv", "*.dat")), ("All", "*.*")])
        if fp:
            try:
                self.points = self._read_column(fp)
                self.file_label.config(text=f"{os.path.basename(fp)}\n{len(self.points):,} values")
                self.status.set(f"{len(self.points):,} values loaded from {fp}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not load file:\n{e}")

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
        fp = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG","*.png")])
        if fp:
            self.fig.savefig(fp, dpi=300)
            self.status.set(f"Image saved: {fp}")

    def save_gif(self):
        if self.fractal is None or self.kind != "tetrahedron":
            messagebox.showerror("Error", "Generate a tetrahedron first.")
            return
        fp = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF","*.gif")])
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
