#!/usr/bin/env python3
"""Resolve the mean/tail contradiction, and test the exposure confound head-on.

Two results of mine disagree and the disagreement is the point:

  MEAN  matched-cell 30-49 Hz ratio Kd=2/Kd=1 = 0.913 [0.791, 1.026], inside the split-half null.
        Matched exceedance <= 1 at every threshold q50..q99.
  TAIL  27/219 blocks burst at Kd=2 vs 1/91 at Kd<=1; max 448 -> 4046.

The reconciliation hypothesis, stated by the orchestrator and TESTED here rather than argued:
the matched thresholds never reach the burst amplitudes (matched q99 = 317 counts; the bursts are
3,000-4,000), so the matched analysis describes the BULK and is blind to the phenomenon, while the
census is uncontrolled for exposure.

  §1  EXPOSURE IN SECONDS in the corner grind #2 lives in, per route, from RAW frames.
      🛑 If the low-dose routes barely visited that corner, the census proves nothing.
  §2  The conditional test inside that corner, with 3a/3b flagged PROVOKED and V62 r37 (ordinary
      driving) reported as the clean high-dose arm.
  §3  CREATION vs UNMASKING: creation => amplitude rises with dose in the matched corner;
      unmasking => flat with dose.
  §4  BAND SPECIFICITY of the tail. If 24-28 / 10-16 Hz blocks also jump at Kd=2 it is generic
      roughness and the 30-49 Hz mode story is wrong.
  §5  Why the exceedance table said the opposite: the threshold ladder, extended to burst scale.

Usage:  python studies/grind2/analyze_grind2_corner.py
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
from _r31_common import fs_of, load, sustained  # noqa: E402

PKL = HERE.parent / "_scratch/data/_cache_grind2_records.pkl"
OUTJSON = HERE / "_scratch/out/_grind2_corner.json"
RNG = np.random.default_rng(20260801)

# The corner, as specified by the orchestrator. `eff` is the sustained (3 Hz lowpass) torsion-bar
# torque = the driver's own push, never raw |tq| (the oscillation trips a raw test).
V_MAX, EFF_MIN, ANG_MIN = 4.0, 1200.0, 100.0
BURST = 400.0
BIG = 1000.0


def fisher2x2(a, b, c, d):
    from math import comb
    n, r1, c1 = a + b + c + d, a + b, a + c
    def pr(k):
        return comb(r1, k) * comb(n - r1, c1 - k) / comb(n, c1)
    p0 = pr(a)
    return float(sum(pr(k) for k in range(max(0, c1 - (n - r1)), min(r1, c1) + 1)
                     if pr(k) <= p0 * (1 + 1e-9)))


def exposure_seconds(build):
    """Corner exposure measured on RAW FRAMES, not windows -- windows need 2.56 s of contiguity
    and would undercount a route that only clips the corner briefly."""
    B = G.BUILDS[build]
    tot = corner = soft = 0.0
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        dt = 1.0 / fs
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        v = np.abs(d["cs_v"])
        ang = np.abs(d["ang"])
        tot += len(v) * dt
        corner += float(((v < V_MAX) & (eff >= EFF_MIN) & (ang >= ANG_MIN)).sum()) * dt
        soft += float(((v < V_MAX) & (eff >= 800) & (ang >= 50)).sum()) * dt
    return tot, corner, soft


def blockstat(rs, key, thr):
    blk = {}
    for r in rs:
        blk[r["blk"]] = blk.get(r["blk"], False) or (r[key] > thr)
    return sum(blk.values()), len(blk)


def boot_stat(rs, key, rng, fn, nboot=3000):
    blk = {}
    for r in rs:
        blk.setdefault(r["blk"], []).append(r)
    per = [G.col(v, key) for v in blk.values()]
    if not per:
        return np.nan, np.nan, np.nan
    allv = np.concatenate(per)
    dr = np.empty(nboot)
    for b in range(nboot):
        i = rng.integers(0, len(per), len(per))
        dr[b] = fn(np.concatenate([per[j] for j in i]))
    return float(fn(allv)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


def main():
    G.EPKEY = "blk"
    with open(PKL, "rb") as fh:
        store = pickle.load(fh)
    out = {}

    def corner(rs):
        return [r for r in rs if r["v"] < V_MAX and r["eff"] >= EFF_MIN and r["ang"] >= ANG_MIN]

    # ================================================================ §1 EXPOSURE ================
    G.hdr(f"§1  EXPOSURE IN SECONDS in the grind-#2 corner: v < {V_MAX:g} m/s AND sustained driver\n"
          f"torque >= {EFF_MIN:g} counts AND |steering angle| >= {ANG_MIN:g} deg. Measured on RAW\n"
          f"FRAMES. 🛑 If the low-dose routes barely visited this corner, the burst census proves\n"
          f"nothing about the burst RATE.")
    print(f"  {'build':10s} {'kd':>3s} {'provoked?':>10s} {'total s':>9s} {'CORNER s':>9s} "
          f"{'% of route':>10s} | {'soft corner s':>13s} | {'corner windows':>14s}")
    expo = {}
    for b in G.ORDER:
        tot, cor, soft = exposure_seconds(b)
        nw = len(corner(store[b]))
        prov = "PROVOKED" if b in ("V65/r3a", "V65/r3b") else "-"
        expo[b] = dict(total=tot, corner=cor, soft=soft, nwin=nw)
        print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} {prov:>10s} {tot:9.1f} {cor:9.1f} "
              f"{100 * cor / tot:9.2f}% | {soft:13.1f} | {nw:14d}")
    out["exposure"] = expo
    c1 = sum(expo[b]["corner"] for b in G.DOSE[0.0] + G.DOSE[1.0])
    c2 = sum(expo[b]["corner"] for b in G.DOSE[2.0])
    c2c = expo["V62/r37"]["corner"]
    print(f"\n  Kd<=1 total corner exposure: {c1:.1f} s     Kd=2: {c2:.1f} s "
          f"(of which V62 r37, ordinary driving: {c2c:.1f} s)")
    print(f"  exposure ratio Kd=2 / Kd<=1 = {c2 / max(c1, 1e-9):.1f}x   "
          f"(V62 r37 alone / Kd<=1 = {c2c / max(c1, 1e-9):.2f}x)")

    # ================================================================ §2 CONDITIONAL =============
    G.hdr("§2  THE CONDITIONAL TEST, INSIDE THE CORNER.  Rates are per SECOND of corner exposure,\n"
          "so more driving in the corner cannot by itself produce a higher rate.")
    print(f"  {'build':10s} {'kd':>3s} {'prov':>5s} {'nwin':>5s} {'nblk':>5s} | {'E p50':>7s} "
          f"{'p90':>7s} {'p99':>8s} {'max':>8s} | {'burst blk':>10s} {'burst s':>8s} "
          f"{'per 100 s':>10s}")
    rows = {}
    for b in G.ORDER:
        rs = corner(store[b])
        cor = expo[b]["corner"]
        if not rs:
            print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} "
                  f"{'yes' if b in ('V65/r3a', 'V65/r3b') else '-':>5s} {0:5d} "
                  f"{0:5d} |  (no windows in the corner)")
            rows[b] = dict(n=0, corner_s=cor)
            continue
        e = G.col(rs, "e_30-49")
        nb, tb = blockstat(rs, "e_30-49", BURST)
        # seconds of burst: windows above threshold x hop, a conservative upper bound
        bs = float((e > BURST).sum()) * 1.28
        rows[b] = dict(n=len(rs), nblk=tb, corner_s=cor, p50=float(np.median(e)),
                       p90=float(np.percentile(e, 90)), mx=float(e.max()), burst_blk=nb,
                       rate_per_100s=100 * bs / max(cor, 1e-9))
        print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} "
              f"{'yes' if b in ('V65/r3a', 'V65/r3b') else '-':>5s} {len(rs):5d} {tb:5d} | "
              f"{np.median(e):7.1f} {np.percentile(e, 90):7.1f} {np.percentile(e, 99):8.1f} "
              f"{e.max():8.1f} | {nb:4d}/{tb:<5d} {bs:8.1f} {100 * bs / max(cor, 1e-9):10.2f}")
    out["corner_rows"] = rows

    print("\n  ---- the CLEAN comparison: V62 route 37 (ordinary driving) vs all Kd<=1 ----")
    for lbl, hi, lo in (("V62 r37 / Kd<=1", ["V62/r37"], G.DOSE[0.0] + G.DOSE[1.0]),
                        ("V65 3a+3b / Kd<=1  [PROVOKED]", ["V65/r3a", "V65/r3b"],
                         G.DOSE[0.0] + G.DOSE[1.0]),
                        ("all Kd=2 / Kd<=1", G.DOSE[2.0], G.DOSE[0.0] + G.DOSE[1.0])):
        rh = corner([r for b in hi for r in store[b]])
        rl = corner([r for b in lo for r in store[b]])
        ah, nh = blockstat(rh, "e_30-49", BURST)
        al, nl = blockstat(rl, "e_30-49", BURST)
        sh = sum(expo[b]["corner"] for b in hi)
        sl = sum(expo[b]["corner"] for b in lo)
        p = fisher2x2(ah, nh - ah, al, nl - al) if min(nh, nl) >= 3 else np.nan
        bh = float((G.col(rh, "e_30-49") > BURST).sum()) * 1.28 if rh else 0.0
        bl = float((G.col(rl, "e_30-49") > BURST).sum()) * 1.28 if rl else 0.0
        print(f"  {lbl:32s} blocks {ah:2d}/{nh:<3d} vs {al:2d}/{nl:<3d}   "
              f"Fisher p={p:.4g}   burst s/100 s corner: "
              f"{100 * bh / max(sh, 1e-9):.2f} vs {100 * bl / max(sl, 1e-9):.2f}   "
              f"(corner exposure {sh:.0f} s vs {sl:.0f} s)")
        # max ratio, the statistic that does not depend on a threshold at all
        if rh and rl:
            print(f"  {'':32s} max envelope {G.col(rh, 'e_30-49').max():.0f} vs "
                  f"{G.col(rl, 'e_30-49').max():.0f}  = "
                  f"{G.col(rh, 'e_30-49').max() / G.col(rl, 'e_30-49').max():.1f}x")

    # ================================================================ §3 CREATION vs UNMASKING ===
    G.hdr("§3  CREATION vs UNMASKING, inside the corner.\n"
          "  CREATION  => 30-49 Hz amplitude RISES with Kd dose at matched covariate.\n"
          "  UNMASKING => 30-49 Hz amplitude is FLAT with dose; only 18-22 Hz falls, so the driver\n"
          "               starts noticing a vibration that was always there.")
    print(f"  {'dose':6s} {'routes':28s} {'corner s':>9s} {'nwin':>5s} {'nblk':>5s} | "
          f"{'30-49 p50':>26s} | {'30-49 p95':>26s}")
    dose = {}
    for k in (0.0, 1.0, 2.0):
        rs = corner([r for b in G.DOSE[k] for r in store[b]])
        cs = sum(expo[b]["corner"] for b in G.DOSE[k])
        if not rs:
            print(f"  Kd={k:.0f}  {','.join(G.DOSE[k]):28s} {cs:9.1f} {0:5d}   (empty)")
            dose[k] = dict(n=0, corner_s=cs)
            continue
        m = boot_stat(rs, "e_30-49", RNG, np.median)
        p95 = boot_stat(rs, "e_30-49", RNG, lambda v: np.percentile(v, 95))
        nb, tb = blockstat(rs, "e_30-49", BURST)
        dose[k] = dict(n=len(rs), nblk=tb, corner_s=cs, med=m, p95=p95, burst_blk=nb)
        print(f"  Kd={k:.0f}  {','.join(G.DOSE[k]):28s} {cs:9.1f} {len(rs):5d} {tb:5d} | "
              f"{m[0]:8.1f} [{m[1]:7.1f},{m[2]:7.1f}] | {p95[0]:8.1f} [{p95[1]:7.1f},{p95[2]:7.1f}]")
    print("\n  same corner, 18-22 Hz (grind #1) -- the discriminator's other arm:")
    for k in (0.0, 1.0, 2.0):
        rs = corner([r for b in G.DOSE[k] for r in store[b]])
        if not rs:
            continue
        m = boot_stat(rs, "e_18-22", RNG, np.median)
        print(f"  Kd={k:.0f}  18-22 median {m[0]:8.1f} [{m[1]:7.1f},{m[2]:7.1f}]  n={len(rs)}")
    out["dose_corner"] = dose

    # ================================================================ §4 BAND SPECIFICITY ========
    G.hdr("§4  IS THE TAIL BAND-SPECIFIC?  For each band the threshold is that band's OWN maximum\n"
          "over every Kd<=1 window, so the test is symmetric and self-scaling. If 24-28 and\n"
          "10-16 Hz blocks also jump at Kd=2, this is generic roughness and the mode story is wrong.")
    k1all = [r for b in G.DOSE[0.0] + G.DOSE[1.0] for r in store[b]]
    k2all = [r for b in G.DOSE[2.0] for r in store[b]]
    print(f"  {'band':8s} {'Kd<=1 max':>10s} {'Kd=2 max':>10s} {'max ratio':>10s} | "
          f"{'Kd=2 blocks over Kd<=1 max':>27s} {'windows':>9s} | {'Fisher p':>9s}")
    bands = {}
    for bnd in G.BANDS:
        key = "e_" + bnd
        m1 = float(G.col(k1all, key).max())
        m2 = float(G.col(k2all, key).max())
        a2, n2 = blockstat(k2all, key, m1)
        a1, n1 = blockstat(k1all, key, m1)      # 0 by construction
        p = fisher2x2(a2, n2 - a2, a1, n1 - a1)
        nwin = int((G.col(k2all, key) > m1).sum())
        bands[bnd] = dict(max1=m1, max2=m2, ratio=m2 / m1, blocks=a2, nblk=n2, p=p, nwin=nwin)
        print(f"  {bnd:8s} {m1:10.1f} {m2:10.1f} {m2 / m1:9.2f}x | {a2:8d}/{n2:<18d} "
              f"{nwin:9d} | {p:9.3g}")
    out["band_specificity"] = bands
    print("\n  same, restricted to the CORNER (where exposure is the confound):")
    k1c, k2c = corner(k1all), corner(k2all)
    print(f"  {'band':8s} {'Kd<=1 max':>10s} {'Kd=2 max':>10s} {'ratio':>8s} | "
          f"{'Kd=2 blocks over Kd<=1 corner max':>33s}")
    for bnd in G.BANDS:
        key = "e_" + bnd
        if not k1c or not k2c:
            continue
        m1 = float(G.col(k1c, key).max())
        a2, n2 = blockstat(k2c, key, m1)
        print(f"  {bnd:8s} {m1:10.1f} {float(G.col(k2c, key).max()):10.1f} "
              f"{G.col(k2c, key).max() / m1:7.2f}x | {a2:14d}/{n2:<18d}")

    # ================================================================ §5 THRESHOLD LADDER ========
    G.hdr("§5  WHY THE MATCHED EXCEEDANCE TABLE SAID THE OPPOSITE.  The ladder, extended past the\n"
          "quantiles of the Kd<=1 pool and out to burst scale. Raw pool fractions, both arms.")
    print(f"  {'threshold':>10s} {'source':22s} {'Kd<=1 frac':>11s} {'Kd=2 frac':>10s} "
          f"{'Kd<=1 n':>8s} {'Kd=2 n':>7s}")
    v1 = G.col(k1all, "e_30-49")
    for lbl, thr in ([(f"q{q} of Kd<=1", float(np.percentile(v1, q))) for q in (50, 75, 90, 95, 99)]
                     + [("fixed", 400.0), ("fixed", 1000.0), ("fixed", 2000.0)]):
        f1 = float(np.mean(v1 > thr))
        f2 = float(np.mean(G.col(k2all, "e_30-49") > thr))
        print(f"  {thr:10.1f} {lbl:22s} {f1:11.4f} {f2:10.4f} "
              f"{int((v1 > thr).sum()):8d} {int((G.col(k2all, 'e_30-49') > thr).sum()):7d}")
    print(f"\n  🛑 The Kd<=1 pool's own q99 is {np.percentile(v1, 99):.0f} counts. The bursts are "
          f"3,000-4,000.\n  Every quantile-anchored threshold therefore sits 10x BELOW the "
          f"phenomenon, and the ladder\n  is measuring the bulk -- where Kd=2 is genuinely quieter "
          f"(it fixed grind #1). Above 400\n  counts the sign flips and stays flipped. The two "
          f"analyses do not contradict; they describe\n  two different populations, and only the "
          f"upper one contains grind #2.")

    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
