#!/usr/bin/env python3
"""v78_surface_plots.py -- plots for the damper calibration surface, stock / V74 / V75.

Run with an interpreter that has numpy + matplotlib, e.g.
    C:/Users/dudei/anaconda3/envs/analyze-log/python.exe v78_surface_plots.py

Every value plotted is read from the images at build time; nothing is hard-coded.
Colors: dataviz reference categorical slots 1/2/3 (blue/orange/aqua), which validate all-pairs.
Sequential single hue (blue, light->dark) for the magnitude heatmaps. No dual axes anywhere.
"""
import os
import struct
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                           r"C:\Users\dudei\Desktop\Projects\accord-firmwares")) / "analysis-2020accord"
OUT = Path(__file__).resolve().parent / "plots"
OUT.mkdir(exist_ok=True)

IMGS = {
    "stock": ROOT / "stock_fw_dump" / "code.bin",
    "V74":   ROOT / "_v74_engagedcols_x0_12_addonly_plain_image.bin",
    "V75":   ROOT / "_v75_CY0.566-EX1.200_magprobe_plain_image.bin",
}
COL = {"stock": "#2a78d6", "V74": "#eb6834", "V75": "#1baf7a"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"

FACTOR_C_PTRS, FACTOR_E_PTRS = 0xC9E9C, 0xC9F84
LIVE_MODE = 26
KMH, DEGS = 64.0, 4.7121
FLOOR = 512


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, base):
    n = u16(b, base)
    return (list(struct.unpack_from(f"<{n}h", b, base + 2)),
            list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n)))


def lerp_int(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for j in range(len(xs) - 1):
        if xs[j] <= x <= xs[j + 1]:
            s = xs[j + 1] - xs[j]
            return ((ys[j + 1] - ys[j]) * (x - xs[j])) // s + ys[j] if s else ys[j]
    return ys[-1]


B = {k: v.read_bytes() for k, v in IMGS.items()}
CB = u32(B["stock"], FACTOR_C_PTRS + 4 * LIVE_MODE)
EB = u32(B["stock"], FACTOR_E_PTRS + 4 * LIVE_MODE)
C = {k: rec(B[k], CB) for k in B}
E = {k: rec(B[k], EB) for k in B}


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor(SURF)
    ax.set_title(title, color=INK, fontsize=11, loc="left", pad=10)
    ax.set_xlabel(xlabel, color=INK2, fontsize=9)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8, length=0)


# ------------------------------------------------------------------ FIG 1: FactorC shape
fig, ax = plt.subplots(figsize=(9, 5), facecolor=SURF)
speeds = list(range(0, 10241, 16))
for k in ("stock", "V74", "V75"):
    xs, ys = C[k]
    ax.plot([v / KMH for v in speeds], [lerp_int(v, xs, ys) for v in speeds],
            color=COL[k], lw=2, zorder=3, label=k)
    ax.plot([x / KMH for x in xs], ys, "o", color=COL[k], ms=6,
            mec=SURF, mew=1.5, zorder=4)
for name, cy, ls in (("proposal: half-fill  [566,429,429,908]", [566, 429, 429, 908], "--"),
                     ("proposal: monotone   [566,566,566,908]", [566, 566, 566, 908], ":")):
    xs = C["V75"][0]
    ax.plot([v / KMH for v in speeds], [lerp_int(v, xs, cy) for v in speeds],
            color=COL["V75"], lw=1.6, ls=ls, alpha=0.75, zorder=2, label=name)
ax.annotate("THE DIP\nY[1] = 234 at 60 km/h\n(-332 counts on V75;\nstock is monotone)",
            xy=(60, 234), xytext=(74, 120), color=INK, fontsize=8.5,
            arrowprops=dict(arrowstyle="->", color=INK2, lw=1))
ax.text(2, 575, "V75  566", color=COL["V75"], fontsize=8.5, va="bottom")
ax.text(2, 438, "V74  429", color=COL["V74"], fontsize=8.5, va="bottom")
ax.text(2, 10, "stock  0", color=COL["stock"], fontsize=8.5, va="bottom")
ax.text(96, 700, "above 60 km/h all three builds are byte-identical\n(the green line covers blue "
        "and orange)", color=INK2, fontsize=8)
style(ax, "FactorC (mode 26, engaged) @0x%05X — speed axis. The dip is OURS, not stock's." % CB,
      "vehicle speed (km/h)   [X in counts / 64]", "FactorC (Q10; 1024 = unity)")
ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper left", bbox_to_anchor=(0.0, 0.99))
fig.tight_layout()
fig.savefig(OUT / "v78_factorC_shape.png", dpi=150, facecolor=SURF)
plt.close(fig)

# ------------------------------------------------------------------ FIG 2: FactorE shape
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), facecolor=SURF)
rates_full = list(range(0, 4201, 4))
rates_zoom = list(range(0, 501, 1))
for ax, rates, ttl in ((axes[0], rates_full, "full rate axis"),
                       (axes[1], rates_zoom, "the ramp, zoomed (0-106 deg/s)")):
    for k in ("stock", "V74", "V75"):
        xs, ys = E[k]
        ax.plot([r / DEGS for r in rates], [lerp_int(r, xs, ys) for r in rates],
                color=COL[k], lw=2, zorder=3, label=k)
        pts = [(x, y) for x, y in zip(xs, ys) if x <= rates[-1]]
        ax.plot([p[0] / DEGS for p in pts], [p[1] for p in pts], "o", color=COL[k], ms=6,
                mec=SURF, mew=1.5, zorder=4)
    xs, ys = E["V75"]
    ax.plot([r / DEGS for r in rates], [lerp_int(r, [0] + xs[1:], ys) for r in rates],
            color=COL["V75"], lw=1.6, ls="--", alpha=0.8, zorder=2,
            label="V75 with X[0] := 0 (operator's request)")
    style(ax, "FactorE (mode 26) @0x%05X — %s" % (EB, ttl),
          "column rate (deg/s)   [X in counts / 4.7121]", "FactorE (Q10)")
axes[1].annotate("X[0]=12 ct = 2.55 deg/s\nY[0]=0 ⇒ E is 0 below it",
                 xy=(2.55, 0), xytext=(14, 90), color=INK, fontsize=8.5,
                 arrowprops=dict(arrowstyle="->", color=INK2, lw=1))
axes[1].annotate("X[0]:=0 RAISES E on (0,200 ct)\nand LOWERS the slope 2.867 -> 2.695",
                 xy=(12, 128), xytext=(30, 200), color=INK, fontsize=8.5,
                 arrowprops=dict(arrowstyle="->", color=INK2, lw=1))
axes[0].legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="lower right")
fig.tight_layout()
fig.savefig(OUT / "v78_factorE_shape.png", dpi=150, facecolor=SURF)
plt.close(fig)

# ------------------------------------------------------------------ FIG 3: dose heatmaps
seq = LinearSegmentedColormap.from_list("blue_seq", ["#f2f6fc", "#c3d9f4", "#7fb0e6",
                                                     "#2a78d6", "#1c4f8c", "#12304f"])
kmh_grid = [i * 0.5 for i in range(121)]
fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.4), facecolor=SURF, sharey="row")
for row, (top, step) in enumerate(((500, 2), (60, 0.25))):
    deg_grid = [i * step for i in range(int(top / step) + 1)]
    for ax, k in zip(axes[row], ("stock", "V74", "V75")):
        cx, cy = C[k]
        ex, ey = E[k]
        Z = [[min(FLOOR, (lerp_int(int(round(s * KMH)), cx, cy)
                          * lerp_int(int(round(d * DEGS)), ex, ey)) >> 10)
              for s in kmh_grid] for d in deg_grid]
        im = ax.imshow(Z, origin="lower", aspect="auto", cmap=seq, vmin=0, vmax=FLOOR,
                       extent=[0, 60, 0, top], interpolation="nearest", zorder=1)
        style(ax, f"{k}" + ("" if row == 0 else "  — low-rate detail"), "vehicle speed (km/h)",
              "column rate (deg/s)" if k == "stock" else "")
        ax.grid(False)
        ax.axhline(21.0, color="#ffffff", lw=1.2, ls="--", alpha=0.85, zorder=3)
        ax.text(1.2, 21.0 + top * 0.015, "21 deg/s = measured in-burst rate",
                color="#ffffff", fontsize=7.5, va="bottom")
cb = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.015)
cb.set_label("damper output |gp-0x6bd0| (counts), after the +/-512 clamp", color=INK2, fontsize=8.5)
cb.ax.tick_params(colors=INK2, labelsize=8)
fig.suptitle("Damper dose surface, mode 26 (engaged): dose = (FactorC(speed) x FactorE(rate)) >> 10"
             "   [FactorB and FactorD are flat 1024]", color=INK, fontsize=11, x=0.012, ha="left")
fig.savefig(OUT / "v78_dose_surface.png", dpi=150, facecolor=SURF, bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------------ FIG 4: design space
fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURF)
ex1s = list(range(200, 401, 2))
EY1 = E["V75"][1][1]
ax.axhspan(0.5799, 1.5798, color="#eda100", alpha=0.12, zorder=0)
ax.axhline(0.5799, color=COL["V74"], lw=2, zorder=3)
ax.axhline(1.5798, color=COL["V75"], lw=2, zorder=3)
ax.text(402, 0.5799, "V74  k=0.5799  flew 1,011 s CLEAN", color=COL["V74"], fontsize=8.5, va="center")
ax.text(402, 1.5798, "V75  k=1.5798  FAULTED", color=COL["V75"], fontsize=8.5, va="center")
ax.text(203, 1.08, "k* is somewhere in this band", color="#8a6a00", fontsize=9)
for i, cy0 in enumerate((429, 470, 500, 530, 566)):
    M = (cy0 * EY1) >> 10
    for ex0, ls, a in ((12, "-", 1.0), (0, "--", 0.6)):
        ax.plot(ex1s, [M / (x - ex0) for x in ex1s], color="#4a3aa7", ls=ls, lw=1.8,
                alpha=a * (0.35 + 0.16 * i), zorder=2)
    ax.text(198, M / (200 - 12), f"C_Y0={cy0}", color="#4a3aa7", fontsize=8,
            ha="right", va="center", alpha=0.5 + 0.1 * i)
ax.plot([], [], color="#4a3aa7", ls="-", lw=1.8, label="E_X0 = 12 (V74/V75, guard G3 floor)")
ax.plot([], [], color="#4a3aa7", ls="--", lw=1.8, label="E_X0 = 0 (operator's request; violates G3)")
ax.set_xlim(150, 400)
ax.set_ylim(0.4, 1.7)
style(ax, "The reachable ramp-regime loop gain  k = ((C_Y0 x 539) >> 10) / (E_X1 - E_X0)",
      "FactorE X[1] (rate counts)   [/ 4.7121 = deg/s]", "k  (damper counts per rate count)")
ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper right")
fig.tight_layout()
fig.savefig(OUT / "v78_design_space.png", dpi=150, facecolor=SURF)
plt.close(fig)

print("wrote:")
for p in ("v78_factorC_shape.png", "v78_factorE_shape.png", "v78_dose_surface.png",
          "v78_design_space.png"):
    print("  ", OUT / p)
