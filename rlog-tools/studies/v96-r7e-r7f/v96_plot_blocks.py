#!/usr/bin/env python3
r"""Block-level figures for the elicitation blocks found by `studies/v96-r7e-r7f/v96_elicitation_finder.py`.

One PNG per block: speed+engagement, steering angle, driver torque, LKAS command, and the
6-9 Hz component of driver torque.  These exist so the 1 s zooms can be chosen from something
visible rather than from a ranking alone.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
from v96_elicitation_finder import load, band_env, mmss  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "analysis-2020accord" / "figures/r7e_r7f"
OUT.mkdir(parents=True, exist_ok=True)

C_TQ, C_CMD, C_ANG = "#2a78d6", "#eb6834", "#1baf7a"
C_SPD, C_INK, C_MUTED, C_ENG = "#4a3aa7", "#0b0b0b", "#52514e", "#eda100"
SURF, GRID = "#fcfcfb", "#e6e5e2"


def style(a):
    a.set_facecolor(SURF)
    a.grid(True, color=GRID, lw=0.8)
    a.set_axisbelow(True)
    for sp in ("top", "right"):
        a.spines[sp].set_visible(False)
    a.tick_params(colors=C_MUTED, labelsize=8)


def shade_engaged(a, t, lat):
    d = np.diff(lat.astype(int))
    s = list(np.where(d == 1)[0] + 1)
    e = list(np.where(d == -1)[0] + 1)
    if lat[0]:
        s = [0] + s
    if lat[-1]:
        e = e + [len(lat) - 1]
    for i, j in zip(s, e):
        a.axvspan(t[i], t[j], color=C_ENG, alpha=0.15, lw=0)


def block_fig(r, D, env, rec, tag):
    t0, t1 = rec["t0"], rec["t1"]
    pad = 2.0
    m = (D["t"] >= t0 - pad) & (D["t"] <= t1 + pad)
    t = D["t"][m]
    fig, ax = plt.subplots(5, 1, figsize=(15, 10), sharex=True,
                           gridspec_kw=dict(height_ratios=[0.8, 1, 1, 1, 0.9], hspace=0.13))
    fig.patch.set_facecolor(SURF)
    for a in ax:
        style(a)
        shade_engaged(a, t, D["lat"][m])

    ax[0].plot(t, D["v"][m], lw=1.4, color=C_SPD)
    ax[0].set_ylabel("speed\nkm/h", fontsize=9, color=C_MUTED)
    ax[1].plot(t, D["ang"][m], lw=1.2, color=C_ANG)
    ax[1].axhline(0, color=C_MUTED, lw=0.8)
    ax[1].set_ylabel("steering angle\ndeg", fontsize=9, color=C_MUTED)
    ax[2].plot(t, D["tq"][m], lw=0.8, color=C_TQ)
    ax[2].axhline(0, color=C_MUTED, lw=0.8)
    for s in (1200, -1200):
        ax[2].axhline(s, color=C_MUTED, lw=0.7, ls=":")
    ax[2].set_ylabel("driver torque\n0x18F counts", fontsize=9, color=C_MUTED)
    ax[3].plot(t, D["cmd"][m], lw=0.8, color=C_CMD)
    ax[3].axhline(0, color=C_MUTED, lw=0.8)
    for s in (4096, -4096):
        ax[3].axhline(s, color=C_MUTED, lw=0.7, ls=":")
    ax[3].set_ylabel("LKAS command\n0x0E4 counts", fontsize=9, color=C_MUTED)
    ax[4].plot(t, env[m], lw=1.0, color=C_TQ)
    ax[4].set_ylabel("driver torque\n6-9 Hz envelope", fontsize=9, color=C_MUTED)
    ax[4].set_xlabel("route time (m:ss)  —  amber = LKAS engaged", color=C_MUTED)

    for ev in rec["events"]:
        for a in ax:
            a.axvline(ev["t_peak"], color=C_MUTED, lw=0.6, alpha=0.5)
    ticks = np.arange(np.floor((t0 - pad) / 5) * 5, t1 + pad + 5, 5)
    ax[4].set_xticks(ticks)
    ax[4].set_xticklabels([mmss(x)[:-2] for x in ticks])
    ax[4].set_xlim(t0 - pad, t1 + pad)
    ax[0].set_title(f"route {r}  block {rec['i']}  —  {mmss(t0)} to {mmss(t1)}  "
                    f"({rec['dur']:.1f} s, {100*rec['eng']:.0f}% LKAS engaged, "
                    f"{rec['n_events']} override pushes)   [{tag}]",
                    color=C_INK, fontsize=12, loc="left", pad=10)
    p = OUT / f"block_r{r}_{rec['i']}.png"
    fig.savefig(p, dpi=120, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    print(f"  {p.name}")


if __name__ == "__main__":
    rep = json.loads((ROOT / "analysis-2020accord" / "_scratch/out/_r7e_r7f_elicitations.json").read_text())
    for r in ("7e", "7f"):
        D = load(r)
        env = band_env(D["tq"])
        print(f"route {r}:")
        for rec in rep[r]:
            tag = ("ENGAGED" if rec["eng"] > 0.8 else
                   "MANUAL" if rec["eng"] < 0.05 else "MIXED")
            block_fig(r, D, env, rec, tag)
