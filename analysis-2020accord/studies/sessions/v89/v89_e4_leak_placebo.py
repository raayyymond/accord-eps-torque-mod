#!/usr/bin/env python3
"""studies/sessions/v89/v89_e4_leak_placebo.py -- the empirical NULL for a cross-build band contrast.

The observer-leak retrodiction rests on ONE route at alpha=286 (`6f`/V86) against routes at
alpha=573.  With n=1 the route-level offset -- surface, tyre pressure, temperature, how the
operator drove that day -- is perfectly confounded with the lever.  The band CONTRAST is supposed
to cancel that offset.  Does it?

This measures that directly.  Every route in the 30-route corpus except `6f` has alpha=573, so
EVERY pair of them is a placebo: two different builds, two different days, SAME alpha.  The
distribution of their band contrasts is the honest null against which `6f` must be judged, and it
is built from ~hundreds of pairs rather than the single C2 pair v89_e1 could afford.

Two statistics are placed in that null:
  S1  the 6-9 minus 32-38 Hz band contrast
  S2  corr(14-slice A-vs-B log-difference profile, the model's leak-ratio profile)
      -- S2 is the shape test and needs no control band at all.
All at v < 5.2 m/s engaged, matching `6f`'s parking-lot exposure.
"""
from __future__ import annotations
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
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from v89_e1_leak_retrodiction import CORPUS, NW, HOP, VMAX_MATCH, spec, brms, order_hits, fit
from v89_e3_leak_profile import SLICES, model_log_ratio

OUT = Path(__file__).resolve().parents[3].parent / "_scratch/cache/r73" / "v89_e4_placebo.json"
ORD = 6
ALPHA286 = "r6f"
MODEL = np.array([model_log_ratio(*SLICES[k]) for k in SLICES])
KEYS = list(SLICES)
I69, I32 = KEYS.index("6-9"), KEYS.index("33-36")


def harvest():
    rows = []
    for rec in np.load(CORPUS, allow_pickle=True):
        rt = rec["route"]
        fs = rec["fs"]
        tq, rate, v = rec["tq"], rec["rate"], rec["v"]
        eng, sst, seg = rec["eng"], rec["sst"], rec["seg"]
        sos = butter(4, 3.0 / (fs / 2), btype="low", output="sos")
        g = np.isfinite(tq)
        lf = np.zeros_like(tq)
        if g.sum() > 30:
            lf[g] = sosfiltfilt(sos, tq[g])
        for s in range(0, len(tq) - NW + 1, HOP):
            sl = slice(s, s + NW)
            if eng[sl].mean() <= 0.98:
                continue
            if (sst[sl] != 0).any() or not np.isfinite(tq[sl]).all():
                continue
            vm, rm = float(np.median(v[sl])), float(np.median(np.abs(rate[sl])))
            hm = float(np.median(np.abs(lf[sl])))
            if not (0.3 < vm < VMAX_MATCH) or rm < 1.0 or hm < 1.0:
                continue
            f, p = spec(tq[sl], fs)
            b = np.array([brms(f, p, *SLICES[k]) for k in KEYS])
            if b.min() <= 0:
                continue
            rows.append({"route": rt, "seg": int(np.median(seg[sl])), "i0": s,
                         "v": vm, "rate": rm, "hands": hm, "e": np.log(b)})
    return rows


def pair_stats(A, B):
    """Covariate-adjusted per-slice log-difference (B minus A), per-slice order veto."""
    both = A + B
    lab = np.array([0.0] * len(A) + [1.0] * len(B))
    vv = np.array([r["v"] for r in both])
    lv = np.log(vv)
    lr = np.log([r["rate"] for r in both])
    lh = np.log([r["hands"] for r in both])
    E = np.array([r["e"] for r in both])
    d = np.full(len(KEYS), np.nan)
    for j, k in enumerate(KEYS):
        lo, hi = SLICES[k]
        m = np.array([not order_hits(x, lo, hi, ORD) for x in vv])
        if m.sum() < 25 or len(set(lab[m])) < 2 or lab[m].sum() < 8 or (1 - lab[m]).sum() < 8:
            continue
        X = np.column_stack([np.ones(m.sum()), lab[m], lv[m] - lv[m].mean(),
                             lr[m] - lr[m].mean(), lh[m] - lh[m].mean()])
        d[j] = fit(X, E[m, j])[1]
    ok = np.isfinite(d)
    corr = (float(np.corrcoef(d[ok], MODEL[ok])[0, 1]) if ok.sum() >= 6 else np.nan)
    c69 = (d[I69] - d[I32]) if (np.isfinite(d[I69]) and np.isfinite(d[I32])) else np.nan
    return d, c69, corr, int(ok.sum())


def main():
    rows = harvest()
    byr = {}
    for r in rows:
        byr.setdefault(r["route"], []).append(r)
    usable = {k: v for k, v in byr.items() if len(v) >= 25}
    print("routes with >=25 engaged windows at v<{} m/s: {}".format(VMAX_MATCH, len(usable)))
    for k in sorted(usable):
        print("  {:5s} {:4d} windows".format(k, len(usable[k])))

    others = sorted(k for k in usable if k != ALPHA286)
    print("\nPLACEBO PAIRS (both alpha=573):")
    P69, PCR = [], []
    for i in range(len(others)):
        for j in range(i + 1, len(others)):
            _, c69, cr, nok = pair_stats(usable[others[i]], usable[others[j]])
            if np.isfinite(c69):
                P69.append(c69)
            if np.isfinite(cr) and nok >= 8:
                PCR.append(cr)
    P69, PCR = np.array(P69), np.array(PCR)
    print("  S1  6-9 minus 33-36 contrast: {} pairs   median {:+.3f}   "
          "central 95% [{:+.3f}, {:+.3f}]   |.| p95 {:.3f}".format(
              len(P69), np.median(P69), np.percentile(P69, 2.5), np.percentile(P69, 97.5),
              np.percentile(np.abs(P69), 95)))
    print("  S2  corr with model profile : {} pairs   median {:+.3f}   "
          "central 95% [{:+.3f}, {:+.3f}]".format(
              len(PCR), np.median(PCR), np.percentile(PCR, 2.5), np.percentile(PCR, 97.5)))

    print("\nOBSERVED, alpha=286 route `6f` against each alpha=573 route")
    print("  (sign convention: POSITIVE = 6f has MORE, which is what the leak model predicts)")
    print("  {:6s} {:>9s} {:>8s} {:>9s} {:>6s}".format("vs", "S1", "pct", "S2", "pct"))
    obs = {}
    for o in others:
        _, c69, cr, nok = pair_stats(usable[o], usable[ALPHA286])
        if not np.isfinite(c69):
            continue
        p1 = float((P69 < c69).mean() * 100)
        p2 = float((PCR < cr).mean() * 100) if np.isfinite(cr) else np.nan
        star = " <<<" if o in ("r6e", "r70") else ""
        print("  {:6s} {:+9.3f} {:7.1f}% {:+9.3f} {:5.1f}%{}".format(o, c69, p1, cr, p2, star))
        obs[o] = {"S1": float(c69), "S1_pct": p1, "S2": float(cr) if np.isfinite(cr) else None,
                  "S2_pct": p2}

    s1 = np.array([v["S1"] for v in obs.values()])
    s2 = np.array([v["S2"] for v in obs.values() if v["S2"] is not None])
    print("\n  ACROSS ALL {} alpha=573 comparison routes:".format(len(s1)))
    print("    S1 median {:+.3f}  (placebo median {:+.3f})   fraction of placebo pairs more "
          "extreme in the PREDICTED (+) direction: {:.1f}%".format(
              np.median(s1), np.median(P69), (P69 > np.median(s1)).mean() * 100))
    print("    S2 median {:+.3f}  (placebo median {:+.3f})   one-sided p that a placebo pair "
          "matches the model shape this poorly or worse: {:.3f}".format(
              np.median(s2), np.median(PCR), float((PCR <= np.median(s2)).mean())))
    print("\n    MODEL PREDICTS  S1 = +0.654  and  S2 = +1.00")
    print("    S1 observed median {:+.3f}; placebo pairs reaching +0.654 or more: {:.1f}%".format(
        np.median(s1), (P69 >= 0.654).mean() * 100))

    OUT.write_text(json.dumps(
        {"placebo_S1": {"n": len(P69), "median": float(np.median(P69)),
                        "ci95": [float(np.percentile(P69, 2.5)), float(np.percentile(P69, 97.5))],
                        "abs_p95": float(np.percentile(np.abs(P69), 95))},
         "placebo_S2": {"n": len(PCR), "median": float(np.median(PCR)),
                        "ci95": [float(np.percentile(PCR, 2.5)), float(np.percentile(PCR, 97.5))]},
         "observed": obs,
         "obs_S1_median": float(np.median(s1)), "obs_S2_median": float(np.median(s2))},
        indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
