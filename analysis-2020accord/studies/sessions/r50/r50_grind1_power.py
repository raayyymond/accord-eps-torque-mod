#!/usr/bin/env python3
"""ROUTE 50 / V70 -- GRIND #1 part 2: POWER, coarse-matched contrasts, and the spectral line.

WHY THIS FILE EXISTS. `studies/sessions/r50/r50_grind1.py` ss3 returned ZERO qualifying cells at creep: V70 has 19
engaged-creep windows in 5 blocks spread over 13 (eng, v, eff, |rate|) cells, so no cell reaches
3 units / 8 windows on both sides and the stratified estimator is undefined. That is an EXPOSURE
fact, not a null. Three things follow, all done here:

  1. POWER, BY SUBSAMPLING THE REFERENCE POOLS. For each candidate arm, draw V70's own block
     structure (5 blocks) from that arm's creep windows and read the median. This gives the exact
     sampling distribution of "what V70's headline would have looked like had V70 been build X",
     and therefore the DISCRIMINATION probability between arms at V70's real exposure. No CI is
     quoted here without it.
  2. COARSE-MATCHED CONTRASTS. The 4-dim cell is unaffordable, so the strata are relaxed in a
     PRE-DECLARED ladder -- (eng,v,eff,rate) -> (eng,v,rate) -> (eng,v) -- and every rung is
     reported with its own split-half null recomputed on the SAME strata. 🛑 A ratio from a coarser
     rung is not comparable to the record's 4-dim ratios; it is labelled every time.
  3. THE LINE ITSELF. Averaged periodogram (average FIRST, peak-find AFTER) over engaged creep,
     located FREE in 12-30 Hz, with a per-window speed census beside it, for V70 and every
     comparison arm. A band statistic can move without a line existing.

Writes `_scratch/out/_r50_grind1_power.json`.  Usage: python studies/sessions/r50/r50_grind1_power.py
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r50_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = "blk"
RNG = np.random.default_rng(20260804)
OUT = {}
store = L.records()
BUILD = "V70/r50"
CREEP = 20 / 3.6

ARMS = {"V70/r50": [BUILD], "stock V58+V59+V64": L.POOL_KD1, "V69/r4f": ["V69/r4f"],
        "V62+V65": L.POOL_KD2, "V67+V68": L.POOL_GATED, "V61/r31": ["V61/r31"]}
CREEP_ENG = {k: [r for n in v for r in store.get(n, [])
                 if r["eng"] == 1 and r["v"] < CREEP] for k, v in ARMS.items()}

# ---------------------------------------------------------------- ss1 POWER ---------------------
L.hdr("ss1  ★★ POWER FIRST -- what could route 50 have distinguished at all?")
print("  V70's engaged-creep exposure is 28.9 s = 19 windows in 5 blocks. For each candidate arm we")
print("  RESAMPLE THAT EXACT STRUCTURE from the arm's own creep windows (5 blocks with replacement)")
print("  and read the median e_18-22. That is the distribution V70's headline would have had if V70")
print("  had been that build.  P(>= obs) is then the probability that arm produces a reading at")
print("  least as high as V70's, at V70's real exposure.\n")

NB_V70 = len({r[G.EPKEY] for r in CREEP_ENG["V70/r50"]})
obs = float(np.median(G.col(CREEP_ENG["V70/r50"], "e_18-22")))
print(f"  V70 observed median e_18-22 (engaged, creep) = {obs:.1f}   over {NB_V70} blocks / "
      f"{len(CREEP_ENG['V70/r50'])} windows\n")


def subsample_median(rs, nblk, ndraw=20000, key="e_18-22"):
    blk = {}
    for r in rs:
        blk.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, key) for v in blk.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return None
    out = np.empty(ndraw)
    for i in range(ndraw):
        j = RNG.integers(0, len(per), nblk)
        out[i] = np.median(np.concatenate([per[k] for k in j]))
    return out


print(f"  {'arm':<20} {'blocks':>7} {'wins':>6} | {'sim p2.5':>9} {'sim p50':>9} {'sim p97.5':>10} "
      f"| {'P(>= V70 obs)':>14}  verdict")
pw = {}
for k, rs in CREEP_ENG.items():
    d = subsample_median(rs, NB_V70)
    nb = len({r[G.EPKEY] for r in rs})
    if d is None:
        print(f"  {k:<20} {nb:>7} {len(rs):>6} |  *** too few blocks")
        continue
    p = float((d >= obs).mean())
    pw[k] = dict(nblk=nb, nwin=len(rs), p025=float(np.percentile(d, 2.5)),
                 p50=float(np.percentile(d, 50)), p975=float(np.percentile(d, 97.5)), p_ge=p)
    vd = ("CONSISTENT" if 0.025 <= p <= 0.975 else
          ("EXCLUDED (V70 too high)" if p < 0.025 else "EXCLUDED (V70 too low)"))
    print(f"  {k:<20} {nb:>7} {len(rs):>6} | {pw[k]['p025']:>9.1f} {pw[k]['p50']:>9.1f} "
          f"{pw[k]['p975']:>10.1f} | {p:>14.4f}  {vd}")
OUT["power_subsample"] = pw

print("\n  PAIRWISE DISCRIMINATION at V70's exposure -- overlap of the two simulated distributions")
print("  (the probability a draw from arm A exceeds a draw from arm B; 0.5 = indistinguishable):")
sims = {k: subsample_median(rs, NB_V70, 8000) for k, rs in CREEP_ENG.items()}
disc = {}
names = [k for k in ARMS if sims.get(k) is not None]
for i, a in enumerate(names):
    for b in names[i + 1:]:
        A, B = sims[a], sims[b]
        pr = float((A[:, None][:800] > B[None, :][:, :800]).mean())
        disc[f"{a} > {b}"] = pr
        print(f"    P({a:<18} > {b:<18}) = {pr:.3f}")
OUT["pairwise_discrimination"] = disc

# ---------------------------------------------------------------- ss2 coarse ladder -------------
L.hdr("ss2  COARSE-MATCHED CONTRAST LADDER -- pre-declared, each rung with its OWN null")
LADDER = {"4d (eng,v,eff,rate) = the record's cell": lambda r: r["cell"],
          "3d (eng,v,rate)": lambda r: (r["cell"][0], r["cell"][1], r["cell"][3]),
          "2d (eng,v)": lambda r: (r["cell"][0], r["cell"][1])}


def with_cells(rs, fn):
    out = []
    for r in rs:
        q = dict(r)
        q["cell"] = fn(r)
        out.append(q)
    return out


lad = {}
for lname, fn in LADDER.items():
    print(f"\n  --- strata: {lname}")
    A = with_cells(CREEP_ENG["V70/r50"], fn)
    for other in ("stock V58+V59+V64", "V69/r4f", "V62+V65", "V67+V68"):
        B = with_cells(CREEP_ENG[other], fn)
        nl = G.split_half_null(B, "e_18-22", RNG, nrep=200, min_ep=2, min_win=4)
        for band in ("18-22", "24-28", "1-4"):
            r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, "e_" + band, RNG, nboot=2000,
                                                            min_ep=2, min_win=4)
            tag = ""
            if band == "18-22" and np.isfinite(nl[1]):
                tag = (f"  null[{nl[1]:.2f},{nl[2]:.2f}] "
                       f"{'INSIDE' if (np.isfinite(r) and nl[1] <= r <= nl[2]) else '*OUT*'}")
            print(f"      {band:>6} Hz  V70/{other:<18} {r:>7.3f} [{lo:>6.3f},{hi:>8.3f}] "
                  f"cells={nc:>2}{tag}")
            lad[f"{lname}|{other}|{band}"] = dict(ratio=float(r), lo=float(lo), hi=float(hi),
                                                  ncells=int(nc))
OUT["ladder"] = lad

# ---------------------------------------------------------------- ss3 the line ------------------
L.hdr("ss3  IS THERE A LINE? averaged periodogram, engaged creep, located FREE in 12-30 Hz")
print("  ★ AVERAGE FIRST, PEAK-FIND AFTER. Speed census printed beside every spectrum -- a moving")
print("  wheel order concentrates in a narrow-speed route and smears in a wide one.\n")
print(f"  {'arm':<20} {'K':>5} {'v mean':>7} {'v sd':>6} | {'f0 (12-30)':>11} {'prom':>7} "
      f"{'P@f0':>10} | {'wheel-1 Hz':>11} {'18-22 sum':>11} {'24-28 sum':>11}")
lines = {}
for k, names in ARMS.items():
    accs, Ks, vs, fref = [], 0, [], None
    for n in names:
        f, P, K, stack, meta = L.avg_periodogram(n, mask_fn=L.eng_mask, vlo=0.0, vhi=CREEP)
        if P is None:
            continue
        fref = f
        accs.append(P * K)
        Ks += K
        vs += [m["v"] for m in meta]
    if not accs or Ks == 0:
        print(f"  {k:<20} {'--':>5}  (no windows)")
        continue
    P = np.sum(accs, axis=0) / Ks
    f = fref
    f0, pr = G.locate(f, P, 12.0, 30.0)
    j = int(np.argmin(np.abs(f - f0)))
    b1 = float(P[(f >= 18) & (f <= 22)].sum())
    b2 = float(P[(f >= 24) & (f <= 28)].sum())
    vm, vsd = float(np.mean(vs)), float(np.std(vs))
    lines[k] = dict(K=Ks, v=vm, vsd=vsd, f0=float(f0), prom=float(pr), Pf0=float(P[j]),
                    w1=float(L.wheel_order(vm)), b1822=b1, b2428=b2)
    print(f"  {k:<20} {Ks:>5} {vm:>7.2f} {vsd:>6.2f} | {f0:>11.2f} {pr:>7.2f} {P[j]:>10.3g} | "
          f"{L.wheel_order(vm):>11.2f} {b1:>11.4g} {b2:>11.4g}")
OUT["lines"] = lines

# ---------------------------------------------------------------- ss4 speed-matched line --------
L.hdr("ss4  SPEED-MATCHED spectra -- every arm restricted to V70's own creep speed span")
vlo = float(np.percentile(G.col(CREEP_ENG["V70/r50"], "v"), 5))
vhi = float(np.percentile(G.col(CREEP_ENG["V70/r50"], "v"), 95))
print(f"  V70 engaged-creep speed p5-p95 = [{vlo:.2f}, {vhi:.2f}] m/s.  Every arm cut to that span.\n")
print(f"  {'arm':<20} {'K':>5} {'v mean':>7} | {'f0':>7} {'prom':>7} | {'18-22 sum':>11} "
      f"{'24-28 sum':>11} {'ratio 18-22/24-28':>18}")
sm = {}
for k, names in ARMS.items():
    accs, Ks, vs, fref = [], 0, [], None
    for n in names:
        f, P, K, stack, meta = L.avg_periodogram(n, mask_fn=L.eng_mask, vlo=vlo, vhi=vhi)
        if P is None:
            continue
        fref, Ks = f, Ks + K
        accs.append(P * K)
        vs += [m["v"] for m in meta]
    if not accs or Ks == 0:
        print(f"  {k:<20} {'--':>5}  (no windows in span)")
        continue
    P, f = np.sum(accs, axis=0) / Ks, fref
    f0, pr = G.locate(f, P, 12.0, 30.0)
    b1 = float(P[(f >= 18) & (f <= 22)].sum())
    b2 = float(P[(f >= 24) & (f <= 28)].sum())
    sm[k] = dict(K=Ks, v=float(np.mean(vs)), f0=float(f0), prom=float(pr), b1822=b1, b2428=b2)
    print(f"  {k:<20} {Ks:>5} {np.mean(vs):>7.2f} | {f0:>7.2f} {pr:>7.2f} | {b1:>11.4g} "
          f"{b2:>11.4g} {b1 / b2 if b2 else np.nan:>18.3f}")
OUT["speed_matched_lines"] = sm

(HERE / "_scratch/out/_r50_grind1_power.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r50_grind1_power.json'}")
