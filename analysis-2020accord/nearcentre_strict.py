#!/usr/bin/env python3
"""THE NEAR-CENTRE TEST, ON AN UNAMBIGUOUS WINDOW DEFINITION.

🛑🛑 THE DEFECT THIS FILE FIXES, measured: binning a 2.56 s window by its MEAN angle admits
windows that SWEEP THROUGH centre. Of the 228 pooled engaged-creep windows with
|mean(cs_ang) - c| < 5 deg, **84 (37%) leave +/-10 deg of the sensor zero inside the window**, with
an angle span up to 419.9 deg, and those 84 carry median e_18-22 = 1038 against 157 for the 144
that genuinely stay near centre -- a 6.6x contamination, in the direction that would MANUFACTURE
the operator's conditional. `_grind2_lib`'s own `ang` (mean of |ang|) has the identical defect.

So every bin here is defined by the window's EXTREME re-centred angle:
    amax = max |cs_ang - c| over the window  ->  a window in bin "0-5" NEVER left +/-5 deg.
    amin = min |cs_ang - c| over the window  ->  a window in "off centre" NEVER came near zero.
Both are needed: `amax < 5` and `amin > 15` are disjoint and each is a clean physical state, where
`|mean| < 5` and `|mean| >= 15` are neither.

Usage: python nearcentre_strict.py [ep|blk] -> writes _nearcentre_strict.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402

G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT = 2000
OUT = {"epkey": G.EPKEY}

RE = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 64.0), (64.0, 1e9)]
RN = ["0-4", "4-16", "16-32", "32-64", "64+"]
AB = [(0.0, 5.0), (5.0, 15.0), (15.0, 45.0), (45.0, 100.0), (100.0, 1e9)]
AN = ["0-5", "5-15", "15-45", "45-100", "100+"]

store = N.records()
ZERO = {}
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    ZERO[b] = c
    for r in store[b]:
        lo, hi = r["a_min"] - c, r["a_max"] - c
        r["amax"] = max(abs(lo), abs(hi))                     # farthest excursion from sensor zero
        r["amin"] = 0.0 if lo <= 0.0 <= hi else min(abs(lo), abs(hi))   # closest approach
        r["ab"] = G.binof(r["amax"], AB)                      # bin by the EXTREME, not the mean
        r["rb"] = G.binof(r["rate_lp"], RE)
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
ARM["POOLED"] = [r for b in N.LADDER for r in ENGC[b]]
POOL = ARM["POOLED"]

# ------------------------------------------------------------------ ss1 the honest ladder ---------
N.hdr("ss1  ★★★ THE ANGLE LADDER ON `amax` -- a window in bin X NEVER left X deg of sensor zero")
print("  Engaged creep. Compare against `nearcentre_grind1.py` ss3, which binned on the MEAN and")
print("  reported 249 / 875 / 591 / 275 / 154 -- an inverted-U produced by sweep contamination.\n")
print(f"  {'arm':<12} " + " ".join(f"{n:>19}" for n in AN))
lad = {}
for k in ["POOLED"] + list(N.ARMS):
    row, cells = [], []
    for i in range(len(AN)):
        c = [r for r in ARM[k] if r["ab"] == i]
        nb = len({r[G.EPKEY] for r in c})
        v = G.col(c, "e_18-22")
        v = v[np.isfinite(v)]
        if len(c) >= 8 and nb >= 3:
            m, lo, hi = G.boot_median_ci(c, "e_18-22", RNG, nboot=NBOOT)
            row.append(dict(n=len(c), nb=nb, med=float(m), lo=float(lo), hi=float(hi), thin=False))
            cells.append(f"{m:>6.0f}[{lo:>5.0f},{hi:>5.0f}]n{len(c):<3}".rjust(19))
        else:
            m = float(np.median(v)) if len(v) else np.nan
            row.append(dict(n=len(c), nb=nb, med=m, thin=True))
            cells.append(f"{'EMPTY':>19}" if not len(v)
                         else f"{m:>8.0f} ~n{len(c):<3}".rjust(19))
    lad[k] = row
    print(f"  {k:<12} " + " ".join(cells))
OUT["ladder_amax"] = lad

# ------------------------------------------------------------------ ss2 the 2-way, honest ---------
N.hdr("ss2  ★★★ THE 2-WAY TABLE ON `amax` x MANOEUVRE RATE -- pooled engaged creep")
print(f"      {'amax \\ rate':<12} " + " ".join(f"{n:>15}" for n in RN) + f"{'ROW ALL':>15}")
tw = {}
for i, an in enumerate(AN):
    cells = []
    for j in range(len(RN)):
        c = [r for r in POOL if r["ab"] == i and r["rb"] == j]
        v = G.col(c, "e_18-22")
        v = v[np.isfinite(v)]
        tw[f"{an}|{RN[j]}"] = dict(n=len(c), med=float(np.median(v)) if len(v) else np.nan)
        cells.append(f"{'--':>15}" if not len(v)
                     else f"{np.median(v):>8.0f}(n{len(c)})".rjust(15))
    ra = [r for r in POOL if r["ab"] == i]
    va = G.col(ra, "e_18-22")
    va = va[np.isfinite(va)]
    cells.append(f"{np.median(va):>8.0f}(n{len(ra)})".rjust(15) if len(va) else f"{'--':>15}")
    print(f"      {an:<12} " + " ".join(cells))
cells = []
for j in range(len(RN)):
    c = [r for r in POOL if r["rb"] == j]
    v = G.col(c, "e_18-22")
    v = v[np.isfinite(v)]
    cells.append(f"{np.median(v):>8.0f}(n{len(c)})".rjust(15) if len(v) else f"{'--':>15}")
print(f"      {'COL ALL':<12} " + " ".join(cells))
OUT["two_way_amax"] = tw

# ------------------------------------------------------------------ ss3 the strict contrast -------
N.hdr("ss3  ★★★ HELD NEAR CENTRE vs HELD OFF CENTRE -- the operator's conditional, strictly")
print("  A = window never leaves +/-5 deg of the sensor zero (amax < 5)")
print("  B = window never comes within 15 deg of it     (amin >= 15)")
print("  Disjoint, and each is a clean physical state. Stratified on (v, eff, manoeuvre-rate bin).")
print("  ratio > 1 = MORE grind #1 while HELD near centre, which is what the operator reports.\n")
print(f"      {'arm':<12} {'nA':>5} {'nB':>5} {'medA':>8} {'medB':>8} {'ratio':>7} "
      f"{'[95% CI]':>17} {'24-28':>7} {'excess':>7} {'cells':>5} {'own null':<14} p")
st = {}
CELL = lambda r: (r["cell"][1], r["cell"][2], r["rb"])
for k in ["POOLED"] + list(N.ARMS):
    z = N.recell(ARM[k], CELL)
    A = [r for r in z if r["amax"] < 5.0]
    B = [r for r in z if r["amin"] >= 15.0]
    if len(A) < 6 or len(B) < 6:
        print(f"      {k:<12} {len(A):>5} {len(B):>5}  *** UNDERPOWERED")
        st[k] = dict(nA=len(A), nB=len(B), underpowered=True)
        continue
    r18 = G.boot_cellwise(A, B, "e_18-22", RNG, nboot=NBOOT, min_ep=2, min_win=4)
    r24 = G.boot_cellwise(A, B, "e_24-28", RNG, nboot=NBOOT, min_ep=2, min_win=4)
    nl = G.split_half_null(z, "e_18-22", RNG, nrep=200, min_ep=2, min_win=4)
    _, p = G.perm_p(A, B, "e_18-22", RNG, nperm=1500, min_ep=2, min_win=4)
    exc = r18[0] / r24[0] if np.isfinite(r24[0]) and r24[0] > 0 else np.nan
    ins = np.isfinite(nl[1]) and np.isfinite(r18[0]) and nl[1] <= r18[0] <= nl[2]
    st[k] = dict(nA=len(A), nB=len(B), ratio=float(r18[0]), lo=float(r18[1]), hi=float(r18[2]),
                 ncells=int(r18[3]), r2428=float(r24[0]), excess=float(exc),
                 null=[float(x) for x in nl], inside=bool(ins), p=float(p),
                 medA=float(np.median(G.col(A, "e_18-22"))),
                 medB=float(np.median(G.col(B, "e_18-22"))))
    print(f"      {k:<12} {len(A):>5} {len(B):>5} {np.median(G.col(A, 'e_18-22')):>8.0f} "
          f"{np.median(G.col(B, 'e_18-22')):>8.0f} {r18[0]:>7.3f} "
          f"[{r18[1]:>7.3f},{r18[2]:>8.3f}] {r24[0]:>7.3f} {exc:>7.3f} {r18[3]:>5} "
          f"[{nl[1]:.2f},{nl[2]:.2f}]".ljust(0) + f"  {'INSIDE' if ins else '*OUT*':<7}{p:.4f}")
OUT["strict"] = st

# ------------------------------------------------------------------ ss4 the sweep test ------------
N.hdr("ss4  ★★★ THE SWEEP TEST -- what the mean-angle bin was actually picking up")
print("  Among windows whose MEAN re-centred angle is < 5 deg, split by whether the window stayed")
print("  near centre or swept through it. This is the contamination, priced.\n")
sw = {}
print(f"  {'arm':<12} {'held n':>7} {'held med':>9} {'swept n':>8} {'swept med':>10} {'ratio':>7} "
      f"{'sweep rate p50':>15} {'held rate p50':>14}")
for k in ["POOLED"] + list(N.ARMS):
    rs = [r for r in ARM[k] if abs(r["a_mean"] - ZERO.get(r["build"], 0.0)) < 5.0]
    H = [r for r in rs if r["amax"] < 10.0]
    S = [r for r in rs if r["amax"] >= 10.0]
    if len(H) < 4 or len(S) < 4:
        print(f"  {k:<12} {len(H):>7} {'':>9} {len(S):>8}   *** UNDERPOWERED")
        continue
    mh = float(np.median(G.col(H, "e_18-22")))
    ms = float(np.median(G.col(S, "e_18-22")))
    sw[k] = dict(nH=len(H), nS=len(S), medH=mh, medS=ms, ratio=ms / mh if mh else np.nan)
    print(f"  {k:<12} {len(H):>7} {mh:>9.0f} {len(S):>8} {ms:>10.0f} {ms / mh:>7.2f} "
          f"{np.median(G.col(S, 'rate_lp')):>15.1f} {np.median(G.col(H, 'rate_lp')):>14.1f}")
OUT["sweep"] = sw

(HERE.parent / "_nearcentre_strict.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_nearcentre_strict.json'}")
