#!/usr/bin/env python3
"""DELIVERABLE 3 (the crux) done properly, plus the two controls `studies/sessions/r4f/r4f_crossbuild.py` could not run.

THREE FIXES OVER `studies/sessions/r4f/r4f_crossbuild.py`, each of which changed a number there:

  1. 🛑 THE ENGAGED-vs-MANUAL VETO RETURNED 0 CELLS AND THAT WAS A BUG, NOT A RESULT.
     `_grind2_lib`'s cell key is (eng, vbin, effbin, ratebin) -- `eng` is its FIRST element, so the
     engaged and manual arms can never share a cell by construction and the estimator correctly
     reported nothing. Re-keyed to (vbin, effbin, ratebin) here. This is the sharpest order veto
     available: it is WITHIN one route, so tyre, rpm, road and exposure confounds cancel exactly.

  2. ★ A WITHIN-WINDOW NORMALISED METRIC. In `studies/sessions/r4f/r4f_crossbuild.py` ss4 the creep contrast moved
     18-22 Hz (1.703) AND the 24-28 Hz negative control (1.780) by the same amount -- that is a
     BROADBAND level shift, not a mode, and a raw envelope ratio cannot tell them apart. `bandnorm`
     = e_18-22 / e_24-28, formed INSIDE each window, cancels any per-window broadband gain. If the
     18-22 Hz effect survives normalisation it is a MODE; if it collapses to 1.0 it was level.
     Prominence p_18-22 (peak / local median floor) is the second, independent scale-free view.

  3. POWER. The V69 speed bins hold 11-73 windows, so the standard min_ep=3 / min_win=8 leaves 0-2
     qualifying cells and the estimator returns nan. Inside a speed bin the speed axis is already
     matched, so the cell key drops to (effort, |rate|) and the thresholds to 2/4. 🛑 Both settings
     are PRINTED per row and the qualifying-cell count is printed beside every ratio -- a ratio on
     1 cell is a matched comparison in one corner of the envelope, not a route-level result.

ss4 also runs the >= 50 km/h ORDER TRACKING TEST that the veto arithmetic demands: at v = 22.7 m/s
wheel order 2 = 21.8 Hz, i.e. INSIDE 18-22 Hz. Order 2 is only a veto if the per-window peak MOVES
with speed like 2v/CIRC; a fixed mode does not.

Writes `_scratch/out/_r4f_speedcrux.json`.  Usage: python studies/sessions/r4f/r4f_speedcrux.py [ep|blk]
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r4f_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260803)
NBOOT, NULLREP = 2000, 250
OUT = {"epkey": G.EPKEY}
store = L.records()
BUILD = "V69/r4f"


def pool(names):
    return [r for n in names for r in store.get(n, [])]


def prep(rs):
    """Add the within-window normalised metrics. Idempotent."""
    for r in rs:
        a, b = r.get("e_18-22", np.nan), r.get("e_24-28", np.nan)
        r["bandnorm"] = (a / b) if (np.isfinite(a) and np.isfinite(b) and b > 0) else np.nan
        c = r.get("e_30-40", np.nan)
        r["bandnorm2"] = (a / c) if (np.isfinite(a) and np.isfinite(c) and c > 0) else np.nan
    return rs


def recell(rs, fn):
    for r in rs:
        r["cell"] = fn(r)
    return rs


CELL_STD = lambda r: (r["eng"], G.binof(r["v"], G.V_BINS), G.binof(r["eff"], G.E_BINS),
                      G.binof(r["rate"], G.R_BINS))                                   # noqa: E731
CELL_NOENG = lambda r: (G.binof(r["v"], G.V_BINS), G.binof(r["eff"], G.E_BINS),
                        G.binof(r["rate"], G.R_BINS))                                 # noqa: E731
CELL_ER = lambda r: (G.binof(r["eff"], G.E_BINS), G.binof(r["rate"], G.R_BINS))       # noqa: E731

ARMS = {"V69": [BUILD], "Kd2": L.POOL_KD2, "Kd2g": L.POOL_GATED, "Kd1": L.POOL_KD1}
ENG = {k: prep([r for r in pool(v) if r["eng"] == 1]) for k, v in ARMS.items()}
ALL = {k: prep(pool(v)) for k, v in ARMS.items()}

METRICS = [("e_18-22", "18-22 Hz envelope p99  (raw level)"),
           ("bandnorm", "18-22 / 24-28  (level-normalised)"),
           ("p_18-22", "18-22 Hz prominence    (scale-free)"),
           ("e_24-28", "24-28 Hz envelope      (NEG CTRL)"),
           ("e_1-4", "1-4 Hz envelope        (VALIDITY)")]


def run(A, B, key, label, min_ep=3, min_win=8, nullrs=None, nrep=NULLREP):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=NBOOT,
                                                    min_ep=min_ep, min_win=min_win)
    nl = (G.split_half_null(nullrs, key, RNG, nrep=nrep, min_ep=min_ep, min_win=min_win)
          if nullrs is not None else (np.nan, np.nan, np.nan))
    verdict = ""
    if np.isfinite(r) and np.isfinite(nl[1]):
        verdict = "INSIDE NULL" if nl[1] <= r <= nl[2] else "*** OUTSIDE NULL"
    ns = f"[{nl[1]:.2f},{nl[2]:.2f}]" if np.isfinite(nl[1]) else "n/a"
    print(f"  {label:<42} {r:>7.3f} [{lo:>6.3f},{hi:>7.3f}]  cells={nc:>2} "
          f"u {na:>3}/{nb:>3}  null {ns:>14}  {verdict}")
    return dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc),
                uA=int(na), uB=int(nb), null=[float(x) for x in nl])


# ================================================================== ss1 the eng/man veto ==========
L.hdr("ss1  ★ ENGAGED vs MANUAL *within route 4f* -- the order veto that cancels every confound")
print("  A tyre order (f = n*v/CIRC) and an engine order (f = k*rpm/60) are blind to LKAS. Cells")
print("  are re-keyed to (v, effort, |rate|) WITHOUT the engagement component -- that is why the")
print("  same call returned 0 cells in studies/sessions/r4f/r4f_crossbuild.py ss5.\n")
veto = {}
for rn, (lo, hi) in [("route 4f, all speeds", (0.0, 1e9)),
                     ("route 4f, v < 2.778 (<10 km/h)", (0.0, 10 / 3.6)),
                     ("route 4f, v < 5.556 (<20 km/h)", (0.0, 20 / 3.6))]:
    A = recell([r for r in ALL["V69"] if r["eng"] == 1 and lo <= r["v"] < hi], CELL_NOENG)
    B = recell([r for r in ALL["V69"] if r["eng"] == 0 and lo <= r["v"] < hi], CELL_NOENG)
    print(f"  --- {rn}:  engaged n={len(A)} u={len({r[G.EPKEY] for r in A})} | "
          f"manual n={len(B)} u={len({r[G.EPKEY] for r in B})}")
    for key, lbl in METRICS:
        veto[f"{rn}|{key}"] = run(A, B, key, f"eng/man  {lbl}", min_ep=2, min_win=4,
                                  nullrs=A + B, nrep=150)
    print()
OUT["eng_vs_man"] = veto

# also on the OTHER builds, so "engagement-conditional" is not a route-4f peculiarity
print("  Same engaged/manual contrast on the comparison pools (18-22 Hz raw + normalised):")
for k in ("Kd2", "Kd2g", "Kd1"):
    A = recell([r for r in ALL[k] if r["eng"] == 1], CELL_NOENG)
    B = recell([r for r in ALL[k] if r["eng"] == 0], CELL_NOENG)
    if len(A) < 8 or len(B) < 8:
        print(f"    {k}: EMPTY")
        continue
    for key, lbl in (("e_18-22", "raw"), ("bandnorm", "normalised")):
        veto[f"{k}|eng-man|{key}"] = run(A, B, key, f"{k:<5} eng/man 18-22 {lbl}",
                                         min_ep=2, min_win=4, nullrs=A + B, nrep=150)

# ================================================================== ss2 headline, normalised =====
L.hdr("ss2  THE HEADLINE RE-RUN ON ALL FIVE METRICS -- engaged, all speeds")
print("  If 18-22 Hz moves but `bandnorm` and `p_18-22` do NOT, the effect is a broadband level")
print("  shift, not grind #1. If all three move together it is the MODE.\n")
head = {}
for other in ("Kd2", "Kd2g", "Kd1"):
    A = recell(ENG["V69"], CELL_STD)
    B = recell(ENG[other], CELL_STD)
    print(f"  --- V69 / {other}")
    for key, lbl in METRICS:
        head[f"{other}|{key}"] = run(A, B, key, f"V69 / {other}   {lbl}", nullrs=B)
    print()
OUT["headline"] = head

# ================================================================== ss3 THE SPEED CRUX ===========
L.hdr("ss3  ★★ THE CRUX -- 18-22 Hz by V69's OWN dose breakpoints, cells = (effort, |rate|)")
print("  Inside a speed bin the speed axis is already matched, so the cell key drops the speed")
print("  component and the thresholds drop to min_ep=2 / min_win=4. Both are stated per row.")
print("  🛑 `cells` is the number of QUALIFYING (effort, |rate|) cells behind each ratio.\n")
crux = {}
for other in ("Kd2", "Kd1", "Kd2g"):
    print(f"  ================= V69 / {other} =================")
    print(f"  {'km/h':>7} {'dose':>6} | {'nA/uA':>9} {'nB/uB':>9} | "
          f"{'18-22 raw ratio':>26} {'c':>2} | {'normalised 18-22/24-28':>26} {'c':>2}")
    for i, nm in enumerate(L.VBIN_NAMES):
        lo, hi = L.VBINS_V69[i]
        A = recell([r for r in ENG["V69"] if lo <= r["v"] < hi], CELL_ER)
        B = recell([r for r in ENG[other] if lo <= r["v"] < hi], CELL_ER)
        row = dict(bin=nm, dose=L.V69_DOSE[nm], nA=len(A), nB=len(B),
                   uA=len({r[G.EPKEY] for r in A}), uB=len({r[G.EPKEY] for r in B}))
        if len(A) < 4 or len(B) < 4:
            print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x | {len(A):>4}/{row['uA']:<4} "
                  f"{len(B):>4}/{row['uB']:<4} |  *** EMPTY CELL -- this bin cannot speak ***")
            crux[f"{other}|{nm}"] = row
            continue
        out = []
        for key in ("e_18-22", "bandnorm"):
            r, rl, rh, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=NBOOT,
                                                            min_ep=2, min_win=4)
            out.append((r, rl, rh, nc))
            row[key] = dict(ratio=float(r), lo=float(rl), hi=float(rh), ncells=int(nc))
        row["medA"] = float(np.median(G.col(A, "e_18-22")))
        row["medB"] = float(np.median(G.col(B, "e_18-22")))
        crux[f"{other}|{nm}"] = row
        print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x | {len(A):>4}/{row['uA']:<4} "
              f"{len(B):>4}/{row['uB']:<4} | "
              f"{out[0][0]:>8.3f} [{out[0][1]:>6.3f},{out[0][2]:>7.3f}] {out[0][3]:>2} | "
              f"{out[1][0]:>8.3f} [{out[1][1]:>6.3f},{out[1][2]:>7.3f}] {out[1][3]:>2}")
    print()
OUT["crux"] = crux

# unstratified medians with episode-bootstrap CIs, as the plain-language readout
L.hdr("ss3b  THE SAME BINS AS PLAIN MEDIANS with episode-bootstrap CIs (no stratification)")
print("  ⚠ Unmatched on effort and |rate| -- read beside ss3, never instead of it. Included because")
print("  a stratified ratio on one cell hides how big the underlying levels are.\n")
print(f"  {'km/h':>7} {'dose':>6} | {'V69 median 18-22 [95% CI]':>34} | "
      f"{'Kd2 median [95% CI]':>30} | {'Kd1 median [95% CI]':>30}")
plain = {}
for i, nm in enumerate(L.VBIN_NAMES):
    lo, hi = L.VBINS_V69[i]
    cells = {}
    txt = []
    for k in ("V69", "Kd2", "Kd1"):
        sel = [r for r in ENG[k] if lo <= r["v"] < hi]
        if len(sel) < 4:
            cells[k] = None
            txt.append(f"{'EMPTY (n=' + str(len(sel)) + ')':>30}")
            continue
        m, l, h = G.boot_median_ci(sel, "e_18-22", RNG, nboot=NBOOT)
        cells[k] = [float(m), float(l), float(h), len(sel)]
        txt.append(f"{m:>10.1f} [{l:>8.1f},{h:>9.1f}] n={len(sel):<4}"
                   if k == "V69" else f"{m:>9.1f} [{l:>7.1f},{h:>8.1f}]")
    plain[nm] = cells
    print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x | {txt[0]} | {txt[1]} | {txt[2]}")
OUT["plain_medians"] = plain

# ================================================================== ss4 order tracking ===========
L.hdr("ss4  THE >= 50 km/h ORDER-TRACKING TEST -- wheel order 2 IS inside 18-22 Hz up there")
print(f"  order 2 enters 18 Hz at v = 18*{L.CIRC:.4f}/2 = {18 * L.CIRC / 2:.2f} m/s and leaves "
      f"22 Hz at {22 * L.CIRC / 2:.2f} m/s.")
print(f"  order 3 occupies 18-22 Hz over v = {18 * L.CIRC / 3:.2f}-{22 * L.CIRC / 3:.2f} m/s; "
      f"order 4 over {18 * L.CIRC / 4:.2f}-{22 * L.CIRC / 4:.2f} m/s.")
print("  Engine order 1 is inside 18-22 Hz for rpm 1080-1320.\n")
trk = {}
for k in ("V69", "Kd2", "Kd1"):
    sel = [r for r in ENG[k] if r["v"] >= 13.889 and np.isfinite(r["f_18-22"])]
    hi = [r for r in sel if r["p_18-22"] > 4]
    if len(hi) < 8:
        print(f"  {k:<5} >= 50 km/h: only {len(hi)} windows with prom > 4 -- cannot test")
        continue
    v = G.col(hi, "v")
    f0 = G.col(hi, "f_18-22")
    pred2 = 2 * v / L.CIRC
    rpm = G.col(hi, "rpm")
    ok = np.isfinite(rpm)
    # correlation of the observed peak with each predictor, and the residual sd about each
    def rho(x, y):
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 5:
            return np.nan
        xr = np.argsort(np.argsort(x[m])).astype(float)
        yr = np.argsort(np.argsort(y[m])).astype(float)
        return float(np.corrcoef(xr, yr)[0, 1])
    inband2 = float(np.mean((pred2 >= 18) & (pred2 <= 22)))
    trk[k] = dict(n=len(hi), rho_v=rho(v, f0), rho_order2=rho(pred2, f0),
                  rho_rpm=rho(rpm, f0) if ok.sum() > 5 else np.nan,
                  sd_f0=float(np.std(f0)), sd_pred2=float(np.std(pred2)),
                  frac_order2_in_band=inband2,
                  rms_resid_mode=float(np.std(f0)),
                  rms_resid_order2=float(np.sqrt(np.mean((f0 - pred2) ** 2))))
    t = trk[k]
    print(f"  {k:<5} n={t['n']:>3} prom>4 windows.  observed f0 sd = {t['sd_f0']:.2f} Hz; "
          f"order-2 prediction sd = {t['sd_pred2']:.2f} Hz")
    print(f"        rank corr(f0, v) = {t['rho_v']:+.3f}   corr(f0, 2v/CIRC) = "
          f"{t['rho_order2']:+.3f}   corr(f0, rpm) = {t['rho_rpm']:+.3f}")
    print(f"        RMS residual: about a FIXED MODE {t['rms_resid_mode']:.2f} Hz  vs  "
          f"about ORDER 2 {t['rms_resid_order2']:.2f} Hz   "
          f"({'MODE wins' if t['rms_resid_mode'] < t['rms_resid_order2'] else 'ORDER 2 wins'})")
    print(f"        order 2 sits inside 18-22 Hz in {100 * inband2:.1f}% of these windows\n")
OUT["order_tracking_hwy"] = trk

(HERE / "_scratch/out/_r4f_speedcrux.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"wrote {HERE / '_scratch/out/_r4f_speedcrux.json'}")
