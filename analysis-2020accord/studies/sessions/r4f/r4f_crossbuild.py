#!/usr/bin/env python3
"""DELIVERABLES 2 + 3 -- the cross-build contrast, and WHERE IN SPEED grind #1 came back.

METRIC. `e_18-22` = p99 of the analytic 18-22 Hz envelope of one 2.56 s window on the torsion-bar
channel. That is the kit's grind-#1 statistic and the one V62's 8x/42x headline was computed on.
Prominence `p_18-22` is reported beside it as a scale-free second view.

ESTIMATOR. `_grind2_lib.boot_cellwise` unchanged: a STRATIFIED log-ratio over (engagement, speed
bin, effort bin, |rate| bin) cells occupied by BOTH arms, weighted 1/(1/nepA + 1/nepB) so a cell one
arm barely visited cannot dominate, with the CI resampling EPISODES. A cell needs >= 3 episodes AND
>= 8 windows on BOTH sides or it is dropped -- and the dropped cells are PRINTED, because a prior
session found ZERO shared (speed, effort, |rate|) cells between two arms and the raw contrast was
uninterpretable.

🛑 EVERY RATIO IS QUOTED BESIDE A SPLIT-HALF NULL computed FIRST, from the same data, with the
identical estimator. A ratio inside its own null is not a result.

🛑 NEGATIVE CONTROLS. 24-28 Hz (pre-declared, between the modes) and 30-40 Hz. VALIDITY CHECK:
1-4 Hz, the driver's own input -- it must NOT differ once the cells are matched.

★ ss3 IS THE CRUX. V69's delivered rate-lane multiplier is a FUNCTION OF SPEED: 4.000x to 10 km/h,
3.658 @15, 3.307 @20, 2.578 @30, 1.808 @40, and EXACTLY 1.000x -- stock, byte-identical, because
rec2/rec3 are untouched -- at and above 50 km/h. V62/V65 were 2.00x at every speed; V67/V68 were
2.00x whenever LKAS applied, at every speed. So V69 is the FIRST build since V62 that is back to
STOCK gain above 50 km/h. If grind #1's return is confined to >= 50 km/h the cause is loss of the
fix at speed; if it is ALSO (or only) at creep where V69 gives 4x, the cause is something else --
too much gain, or saturation.

Writes `_scratch/out/_r4f_crossbuild.json`.  Usage: python studies/sessions/r4f/r4f_crossbuild.py [ep|blk]
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
NBOOT, NULLREP = 2000, 300
OUT = {"epkey": G.EPKEY}

store = L.records()
BUILD = "V69/r4f"


def pool(names):
    return [r for n in names for r in store.get(n, [])]


ARMS = {
    "V69/r4f (4x<10, 1x>=50)": [BUILD],
    "Kd=2.00 pool V62+V65": L.POOL_KD2,
    "Kd=2 gated V67+V68": L.POOL_GATED,
    "Kd=1.00 stock pool": L.POOL_KD1,
}
ENG = {k: [r for r in pool(v) if r["eng"] == 1] for k, v in ARMS.items()}

L.hdr(f"ss0  ARM INVENTORY  (unit = '{G.EPKEY}'; engaged windows only)")
print(f"  {'arm':<26} {'builds':<28} {'wins':>6} {'units':>6} "
      f"{'v p10':>6} {'v p50':>6} {'v p90':>6} {'eff p50':>8} {'rate p50':>8}")
for k, rs in ENG.items():
    v = G.col(rs, "v")
    print(f"  {k:<26} {','.join(ARMS[k]):<28} {len(rs):>6} {len({r[G.EPKEY] for r in rs}):>6} "
          f"{np.percentile(v, 10):>6.2f} {np.percentile(v, 50):>6.2f} {np.percentile(v, 90):>6.2f} "
          f"{np.median(G.col(rs, 'eff')):>8.0f} {np.median(G.col(rs, 'rate')):>8.1f}")
OUT["inventory"] = {k: dict(builds=ARMS[k], n=len(rs),
                            units=len({r[G.EPKEY] for r in rs}),
                            v=[float(np.percentile(G.col(rs, "v"), p)) for p in (10, 50, 90)])
                    for k, rs in ENG.items()}

# ---------------------------------------------------------------- ss1 split-half nulls -----------
L.hdr("ss1  THE NOISE FLOOR FIRST -- split-half null inside each arm, identical estimator")
print("  Each arm's own units are halved at random and run through the SAME stratified matched-cell")
print("  estimator. Nothing inside this interval is distinguishable from route/exposure noise.\n")
print(f"  {'band':<8} {'arm':<26} {'median':>8} {'2.5%':>8} {'97.5%':>8}")
nulls = {}
for band in ("1-4", "18-22", "24-28", "30-40"):
    for k, rs in ENG.items():
        m, lo, hi = G.split_half_null(rs, "e_" + band, RNG, nrep=NULLREP)
        nulls[(band, k)] = (m, lo, hi)
        print(f"  {band:<8} {k:<26} {m:>8.3f} {lo:>8.3f} {hi:>8.3f}")
    print()
OUT["nulls"] = {f"{b}|{k}": list(v) for (b, k), v in nulls.items()}


def contrast(A, B, key, label, nullkey=None, min_ep=3, min_win=8, verbose=False):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=NBOOT,
                                                    min_ep=min_ep, min_win=min_win)
    s = (f"  {label:<40} {r:>7.3f}  [{lo:>6.3f}, {hi:>6.3f}]  cells={nc:>2}  "
         f"units {na:>3}/{nb:>3}")
    if nullkey and nullkey in nulls and np.isfinite(nulls[nullkey][1]):
        nl, nh = nulls[nullkey][1], nulls[nullkey][2]
        inside = np.isfinite(r) and nl <= r <= nh
        s += f"   null [{nl:.3f}, {nh:.3f}]  {'INSIDE NULL' if inside else '*** OUTSIDE'}"
    print(s)
    if verbose and tab:
        for c, na_, nb_, nea, neb, sa, sb, ratio, w in tab:
            print(f"        cell eng={c[0]} v={G.V_BINS[c[1]]} eff={G.E_BINS[c[2]]} "
                  f"rate={G.R_BINS[c[3]]}  nA={na_:>3}/{nea:>2}u  nB={nb_:>3}/{neb:>2}u  "
                  f"A={sa:>9.1f} B={sb:>9.1f} ratio={ratio:>6.3f}")
    return dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc),
                unitsA=int(na), unitsB=int(nb),
                cells=[[list(c), na_, nb_, nea, neb, sa, sb, ratio, w]
                       for c, na_, nb_, nea, neb, sa, sb, ratio, w in tab])


def cellshare(A, B, min_ep=3, min_win=8):
    """Which (eng, v, eff, rate) cells each arm occupies, and which are SHARED. Printed, never
    assumed -- a prior session found ZERO shared cells and the raw contrast was uninterpretable."""
    def occ(rs):
        c = {}
        for r in rs:
            c.setdefault(r["cell"], []).append(r)
        return c
    ca, cb = occ(A), occ(B)
    shared, qual = set(ca) & set(cb), []
    for c in sorted(shared):
        nea = len({r[G.EPKEY] for r in ca[c]})
        neb = len({r[G.EPKEY] for r in cb[c]})
        if nea >= min_ep and neb >= min_ep and len(ca[c]) >= min_win and len(cb[c]) >= min_win:
            qual.append(c)
    return len(ca), len(cb), len(shared), qual


# ---------------------------------------------------------------- ss2 headline ------------------
L.hdr("ss2  ★ THE HEADLINE -- V69/route 4f against every existing pool, ENGAGED, all speeds")
print("  ratio > 1  =  MORE 18-22 Hz on V69 than on the comparison arm  =  grind #1 is back.\n")
head = {}
for other in ("Kd=2.00 pool V62+V65", "Kd=2 gated V67+V68", "Kd=1.00 stock pool"):
    na, nb, ns, qual = cellshare(ENG["V69/r4f (4x<10, 1x>=50)"], ENG[other])
    print(f"  --- vs {other}  |  V69 occupies {na} cells, {other} {nb}, shared {ns}, "
          f"QUALIFYING {len(qual)}")
    if not qual:
        print("      🛑 ZERO QUALIFYING SHARED CELLS -- the stratified contrast is UNINTERPRETABLE "
              "for this pair.")
    for band, lbl in (("18-22", "GRIND #1  18-22 Hz"), ("24-28", "neg control 24-28 Hz"),
                      ("30-40", "neg control 30-40 Hz"), ("1-4", "validity  1-4 Hz")):
        head[f"{other}|{band}"] = contrast(
            ENG["V69/r4f (4x<10, 1x>=50)"], ENG[other], "e_" + band,
            f"{lbl} vs {other.split()[0]}", nullkey=(band, other))
    head[f"{other}|prom"] = contrast(
        ENG["V69/r4f (4x<10, 1x>=50)"], ENG[other], "p_18-22",
        f"prominence 18-22 Hz vs {other.split()[0]}")
    print()
OUT["headline"] = head

# ---------------------------------------------------------------- ss3 THE SPEED QUESTION --------
L.hdr("ss3  ★★ THE CRUX -- 18-22 Hz binned on V69's OWN dose breakpoints")
print("  V69 dose: 4.000x to 10 km/h -> 3.658 @15 -> 3.307 @20 -> 2.578 @30 -> 1.808 @40 -> "
      "1.000x (STOCK) at >= 50.")
print("  V62/V65 = 2.00x at EVERY speed. V67/V68 = 2.00x whenever LKAS applies, at EVERY speed.")
print("  ⇒ >= 50 km/h is the ONLY region where V69 is back to stock gain.\n")

speed = {}
print(f"  {'km/h':>7} {'dose':>6} | {'V69 n/units':>12} {'V69 e18-22 p50':>15} | "
      f"{'Kd2 n/units':>12} {'Kd2 p50':>9} | {'ratio V69/Kd2 [95% CI]':>28} | "
      f"{'cells':>5} {'null':>16}")
for i, nm in enumerate(L.VBIN_NAMES):
    lo, hi = L.VBINS_V69[i]
    A = [r for r in ENG["V69/r4f (4x<10, 1x>=50)"] if lo <= r["v"] < hi]
    Bm = [r for r in ENG["Kd=2.00 pool V62+V65"] if lo <= r["v"] < hi]
    row = dict(bin=nm, dose=L.V69_DOSE[nm], nA=len(A), nB=len(Bm),
               uA=len({r[G.EPKEY] for r in A}), uB=len({r[G.EPKEY] for r in Bm}))
    if len(A) < 4 or len(Bm) < 4:
        print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x | {len(A):>5}/{row['uA']:<6} "
              f"{'--':>15} | {len(Bm):>5}/{row['uB']:<6} {'--':>9} |  *** EMPTY / TOO FEW ***")
        speed[nm] = row
        continue
    mA = float(np.median(G.col(A, "e_18-22")))
    mB = float(np.median(G.col(Bm, "e_18-22")))
    r, rl, rh, nc, na, nb, tab, _ = G.boot_cellwise(A, Bm, "e_18-22", RNG, nboot=NBOOT)
    nl = G.split_half_null(A + Bm, "e_18-22", RNG, nrep=150)
    row.update(medA=mA, medB=mB, ratio=float(r), lo=float(rl), hi=float(rh), ncells=int(nc),
               null=[float(x) for x in nl])
    speed[nm] = row
    nstr = (f"[{nl[1]:.2f},{nl[2]:.2f}]" if np.isfinite(nl[1]) else "n/a")
    print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x | {len(A):>5}/{row['uA']:<6} {mA:>15.1f} | "
          f"{len(Bm):>5}/{row['uB']:<6} {mB:>9.1f} | "
          f"{r:>8.3f} [{rl:>6.3f},{rh:>7.3f}] | {nc:>5} {nstr:>16}")
OUT["speed_vs_kd2"] = speed

print("\n  Same binning, V69 against the Kd=1.00 STOCK pool (V59+V64+V58):")
speed1 = {}
print(f"  {'km/h':>7} {'dose':>6} | {'V69 n/units':>12} {'V69 p50':>9} | {'Kd1 n/units':>12} "
      f"{'Kd1 p50':>9} | {'ratio V69/Kd1 [95% CI]':>28} | {'cells':>5}")
for i, nm in enumerate(L.VBIN_NAMES):
    lo, hi = L.VBINS_V69[i]
    A = [r for r in ENG["V69/r4f (4x<10, 1x>=50)"] if lo <= r["v"] < hi]
    Bm = [r for r in ENG["Kd=1.00 stock pool"] if lo <= r["v"] < hi]
    row = dict(bin=nm, nA=len(A), nB=len(Bm), uA=len({r[G.EPKEY] for r in A}),
               uB=len({r[G.EPKEY] for r in Bm}))
    if len(A) < 4 or len(Bm) < 4:
        print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x | {len(A):>5}/{row['uA']:<6} {'--':>9} | "
              f"{len(Bm):>5}/{row['uB']:<6} {'--':>9} |  *** EMPTY / TOO FEW ***")
        speed1[nm] = row
        continue
    mA, mB = float(np.median(G.col(A, "e_18-22"))), float(np.median(G.col(Bm, "e_18-22")))
    r, rl, rh, nc, na, nb, tab, _ = G.boot_cellwise(A, Bm, "e_18-22", RNG, nboot=NBOOT)
    row.update(medA=mA, medB=mB, ratio=float(r), lo=float(rl), hi=float(rh), ncells=int(nc))
    speed1[nm] = row
    print(f"  {nm:>7} {L.V69_DOSE[nm]:>5.2f}x | {len(A):>5}/{row['uA']:<6} {mA:>9.1f} | "
          f"{len(Bm):>5}/{row['uB']:<6} {mB:>9.1f} | {r:>8.3f} [{rl:>6.3f},{rh:>7.3f}] | {nc:>5}")
OUT["speed_vs_kd1"] = speed1

# ---------------------------------------------------------------- ss4 the two regions -----------
L.hdr("ss4  THE TWO REGIONS, POOLED -- creep (V69 = 4x-3.3x) vs highway (V69 = STOCK 1.000x)")
REGIONS = {"CREEP  v < 5.556 m/s (<20 km/h, dose 3.3-4.0x)": (0.0, 20 / 3.6),
           "MID    5.556-13.889 m/s (20-50 km/h, 1.4-2.9x)": (20 / 3.6, 50 / 3.6),
           "HIGHWAY v >= 13.889 m/s (>=50 km/h, dose 1.000x = STOCK)": (50 / 3.6, 1e9)}
reg = {}
for rn, (lo, hi) in REGIONS.items():
    print(f"\n  --- {rn}")
    A = [r for r in ENG["V69/r4f (4x<10, 1x>=50)"] if lo <= r["v"] < hi]
    for other in ("Kd=2.00 pool V62+V65", "Kd=2 gated V67+V68", "Kd=1.00 stock pool"):
        Bm = [r for r in ENG[other] if lo <= r["v"] < hi]
        na, nb, ns, qual = cellshare(A, Bm)
        if len(A) < 4 or len(Bm) < 4:
            print(f"      vs {other:<24} *** EMPTY CELL: V69 n={len(A)}, other n={len(Bm)}")
            reg[f"{rn}|{other}"] = dict(nA=len(A), nB=len(Bm), empty=True)
            continue
        for band in ("18-22", "24-28"):
            lbl = f"{'GRIND #1' if band == '18-22' else 'neg ctrl'} {band} vs {other.split()[0]}"
            reg[f"{rn}|{other}|{band}"] = contrast(A, Bm, "e_" + band, lbl,
                                                   nullkey=(band, other))
        print(f"      (shared cells {ns}, qualifying {len(qual)}; V69 n={len(A)} "
              f"u={len({r[G.EPKEY] for r in A})}, other n={len(Bm)} "
              f"u={len({r[G.EPKEY] for r in Bm})})")
OUT["regions"] = reg

# ---------------------------------------------------------------- ss5 within-route order veto ---
L.hdr("ss5  ★ THE SHARPEST ORDER VETO -- ENGAGED vs MANUAL *within route 4f*, speed-matched")
print("  A tyre or engine order does not care whether LKAS is engaged. This contrast is WITHIN one")
print("  route, so route/exposure/tyre/rpm confounds cancel; only the speed distributions must be")
print("  matched, and boot_cellwise does that by construction.\n")
r4 = store[BUILD]
vet = {}
for rn, (lo, hi) in [("all speeds", (0.0, 1e9)), ("creep < 2.778 m/s (<10 km/h)", (0.0, 10 / 3.6)),
                     ("2.778-5.556 m/s (10-20 km/h)", (10 / 3.6, 20 / 3.6))]:
    A = [r for r in r4 if r["eng"] == 1 and lo <= r["v"] < hi]
    Bm = [r for r in r4 if r["eng"] == 0 and lo <= r["v"] < hi]
    if len(A) < 4 or len(Bm) < 4:
        print(f"  {rn:<32} *** EMPTY: engaged n={len(A)}, manual n={len(Bm)}")
        continue
    print(f"  --- {rn}   engaged n={len(A)} u={len({r[G.EPKEY] for r in A})} | "
          f"manual n={len(Bm)} u={len({r[G.EPKEY] for r in Bm})}")
    for band in ("18-22", "24-28", "1-4"):
        vet[f"{rn}|{band}"] = contrast(A, Bm, "e_" + band, f"eng/man {band} Hz", min_ep=2,
                                       min_win=4)
OUT["eng_vs_man"] = vet

(HERE / "_scratch/out/_r4f_crossbuild.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r4f_crossbuild.json'}")
