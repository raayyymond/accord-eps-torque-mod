#!/usr/bin/env python3
r"""Two closing figures.

(A) ANATOMY OF ONE BURST -- a 3 s window at full resolution over the four channels, so the shape
    of the event is visible rather than inferred: the driver loads the wheel, the load breaks, and
    a near-constant-amplitude oscillation runs until he unloads.

(B) PAIRED SUMMARY -- 6-9 Hz driver-torque RMS for every elicitation episode in both routes,
    engaged against LKAS-off, on a log axis, with the 15-22 Hz and 1-3 Hz control bands beside it
    so a broadband shift cannot be read as a band-specific one.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
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
ROOT = HERE.parent
from v96_elicitation_finder import load, band_env, mmss, FS  # noqa: E402
from v96_probe_vs_ratchet import signed_lane  # noqa: E402

OUT = ROOT / "analysis-2020accord" / "figures/r7e_r7f"
CACHE = {r: ROOT / "analysis-2020accord" / f"r{r}" / f"r{r}.npz" for r in ("7e", "7f")}
C_TQ, C_CMD, C_ANG, C_LANE = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"
C_INK, C_MUTED, SURF, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e2"


def style(a):
    a.set_facecolor(SURF)
    a.grid(True, color=GRID, lw=0.8)
    a.set_axisbelow(True)
    for sp in ("top", "right"):
        a.spines[sp].set_visible(False)
    a.tick_params(colors=C_MUTED, labelsize=8)


def anatomy(r, t_c, half=1.5, name="anatomy"):
    D = load(r)
    env = band_env(D["tq"])
    z = np.load(CACHE[r], allow_pickle=True)
    lt, ly, _ = signed_lane(z)
    m = (D["t"] >= t_c - half) & (D["t"] <= t_c + half)
    ml = (lt >= t_c - half) & (lt <= t_c + half)
    tt = D["t"][m] - t_c
    fig, ax = plt.subplots(4, 1, figsize=(13.5, 8.6), sharex=True,
                           gridspec_kw=dict(hspace=0.11))
    fig.patch.set_facecolor(SURF)
    for a in ax:
        style(a)
    ax[0].plot(tt, D["tq"][m], lw=1.5, color=C_TQ)
    ax[0].plot(tt, env[m], lw=1.2, color=C_MUTED, ls="--")
    ax[0].plot(tt, -env[m], lw=1.2, color=C_MUTED, ls="--")
    ax[0].axhline(0, color=C_MUTED, lw=0.7)
    ax[0].set_ylabel("driver torque\n0x18F counts", fontsize=9, color=C_MUTED)
    ax[0].legend(["driver torque", "6-9 Hz envelope"], frameon=False, fontsize=8,
                 loc="upper right", labelcolor=C_MUTED)
    ax[1].plot(tt, D["cmd"][m], lw=1.5, color=C_CMD)
    ax[1].set_ylim(-4400, 4400)
    ax[1].axhline(4096, color=C_MUTED, lw=0.7, ls=":")
    ax[1].axhline(0, color=C_MUTED, lw=0.7)
    ax[1].set_ylabel("LKAS command\n0x0E4 counts", fontsize=9, color=C_MUTED)
    ax[2].plot(lt[ml] - t_c, ly[ml], lw=1.5, color=C_LANE)
    ax[2].axhline(0, color=C_MUTED, lw=0.7)
    ax[2].set_ylabel("gp-0x6b70\nV96 probe, counts", fontsize=9, color=C_MUTED)
    ax[3].plot(tt, D["ang"][m], lw=1.5, color=C_ANG)
    ax[3].set_ylabel("steering angle\ndeg", fontsize=9, color=C_MUTED)
    ax[3].set_xlabel("seconds", color=C_MUTED)
    ax[3].set_xlim(-half, half)
    sl = m
    ax[0].set_title(f"route {r} @ {mmss(t_c)} — anatomy of one elicitation burst, LKAS engaged, "
                    f"{D['v'][m].mean():.0f} km/h.  Rim moves "
                    f"{np.ptp(D['ang'][sl]):.1f}° over the window; the torque swings "
                    f"{np.ptp(D['tq'][sl]):.0f} counts.",
                    fontsize=11.5, color=C_INK, loc="left", pad=10)
    p = OUT / f"{name}_r{r}_{int(t_c)}.png"
    fig.savefig(p, dpi=130, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    print(f"  {p.name}")


def paired_summary():
    ch = json.loads((ROOT / "analysis-2020accord" / "_scratch/out/_r7e_r7f_character.json").read_text())
    rows = ch["episodes"]
    bands = ["6-9 Hz (ratchet)", "15-22 Hz (control)", "1-3 Hz (control)"]
    fig, ax = plt.subplots(1, 3, figsize=(12.5, 5.2), sharey=True,
                           gridspec_kw=dict(wspace=0.08))
    fig.patch.set_facecolor(SURF)
    for j, b in enumerate(bands):
        a = ax[j]
        style(a)
        for x, st in ((0, True), (1, False)):
            vals = [e[f"tq[{b}]"] for e in rows if e["eng"] == st and np.isfinite(e[f"tq[{b}]"])]
            jit = (np.random.default_rng(j).random(len(vals)) - 0.5) * 0.22
            a.scatter(np.full(len(vals), x) + jit, vals, s=64,
                      color=(C_TQ if st else C_MUTED), alpha=0.85,
                      edgecolor=SURF, linewidth=1.6, zorder=3)
            a.plot([x - 0.28, x + 0.28], [np.median(vals)] * 2, color=C_INK, lw=2.4, zorder=4)
            a.text(x - 0.33, np.median(vals), f"{np.median(vals):.0f} ct", ha="right",
                   va="center", fontsize=9.5, color=C_INK, zorder=5,
                   fontweight="bold" if j == 0 else "normal")
        a.set_yscale("log")
        a.set_xticks([0, 1])
        a.set_xticklabels(["LKAS\nENGAGED", "LKAS\noff"], fontsize=9, color=C_MUTED)
        a.set_xlim(-0.85, 1.6)
        a.set_title(b, fontsize=11, color=(C_INK if j == 0 else C_MUTED),
                    fontweight=("bold" if j == 0 else "normal"))
    ax[0].set_ylabel("driver-torque band RMS (0x18F counts, log)", fontsize=9.5, color=C_MUTED)
    fig.suptitle("routes 7e + 7f — every low-speed elicitation episode, 8 engaged vs 9 LKAS-off.  "
                 "Bar = median.  Only the 6-9 Hz band separates by an order of magnitude.",
                 fontsize=11.5, color=C_INK, y=1.0)
    p = OUT / "paired_summary.png"
    fig.savefig(p, dpi=140, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    print(f"  {p.name}")


if __name__ == "__main__":
    anatomy("7f", 13 * 60 + 1.8)
    anatomy("7e", 12 * 60 + 47.2)
    paired_summary()
