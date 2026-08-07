#!/usr/bin/env python3
"""THE NOISE FLOOR for the one decision-bearing claim -- run BEFORE the ratio is believed.

`memory/feedback-episodes-not-windows.md`: get the noise floor from a split-half null with the
IDENTICAL estimator before quoting any ratio. The claim under test is

    V75 / V74, speed-matched relative excess over the 24-28 Hz control, 18-22 Hz = 0.349

Three floors are computed, all with the same speed-bin-matched, episode-resampled estimator:
  1. each build's OWN split-half null (halve its episodes, run the estimator against itself);
  2. the CROSS-ROUTE null-contrast V74/V73 -- two routes whose damper cells are provably different
     but whose measured symptom step the V74 session already reported as absent. If the estimator
     returns ~1 there, a route-to-route difference alone does not manufacture 0.349;
  3. the NEGATIVE-CONTROL BANDS on the same windows: 24-28 Hz (pre-declared control) and 1-4 Hz
     (driver input). If those move as much as 18-22 Hz did, the 18-22 result is exposure.

Usage:  python v78_symptom_null.py   ->  writes _v78_null.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import v78_symptom_lib as V  # noqa: E402

RNG = np.random.default_rng(78999)
OUT = {}
PARK = {"V74/r5d": [2, 3, 9], "V75/r5e": [0]}
VB = [(0.5, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5)]
V.install_fs()
R = V.records()
KEYS = ["e_6-9", "e_18-22", "e_24-28", "e_1-4", "e_40-49"]


def pairs(b, key):
    o = []
    for r in R[b]:
        if r["seg"] in PARK.get(b, []) or r["eng"] != 1 or not (0.5 <= r["v"] < 12.5):
            continue
        if r.get("e_24-28", 0) > 0 and np.isfinite(r[key]):
            val = r[key] if key == "e_24-28" else r[key] / r["e_24-28"]
            o.append((val, r["v"], r["ep"]))
    return o


def strat(a, b):
    num = den = 0.0
    for lo, hi in VB:
        xa = [x for x, v, _ in a if lo <= v < hi]
        xb = [x for x, v, _ in b if lo <= v < hi]
        if len(xa) < 5 or len(xb) < 5:
            continue
        ma, mb = np.median(xa), np.median(xb)
        if ma <= 0 or mb <= 0:
            continue
        w = 1.0 / (1.0 / len(xa) + 1.0 / len(xb))
        num += w * np.log(ma / mb)
        den += w
    return np.exp(num / den) if den else np.nan


def ci(A, B, nb=3000):
    ea, eb = {}, {}
    for x in A:
        ea.setdefault(x[2], []).append(x)
    for x in B:
        eb.setdefault(x[2], []).append(x)
    ka, kb = list(ea), list(eb)
    if len(ka) < 2 or len(kb) < 2:
        return (np.nan,) * 3
    d = np.full(nb, np.nan)
    for i in range(nb):
        aa = [x for j in RNG.integers(0, len(ka), len(ka)) for x in ea[ka[j]]]
        bb = [x for j in RNG.integers(0, len(kb), len(kb)) for x in eb[kb[j]]]
        d[i] = strat(aa, bb)
    return (float(strat(A, B)), float(np.nanpercentile(d, 2.5)),
            float(np.nanpercentile(d, 97.5)))


def selfnull(A, nrep=600):
    ea = {}
    for x in A:
        ea.setdefault(x[2], []).append(x)
    ks = list(ea)
    if len(ks) < 4:
        return np.nan, np.nan
    out = []
    for _ in range(nrep):
        p = RNG.permutation(len(ks))
        h = len(ks) // 2
        v = strat([x for i in p[:h] for x in ea[ks[i]]], [x for i in p[h:] for x in ea[ks[i]]])
        if np.isfinite(v):
            out.append(v)
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))) \
        if len(out) > 20 else (np.nan, np.nan)


V.hdr("1. EACH BUILD'S OWN SPLIT-HALF NULL, per band -- the floor, computed FIRST")
print(f"  {'build':<10} " + "".join(f"{k:>22}" for k in KEYS))
for b in ("V75/r5e", "V74/r5d", "V73/r5a"):
    cells = []
    for k in KEYS:
        lo, hi = selfnull(pairs(b, k))
        OUT.setdefault("selfnull", {})[f"{b}|{k}"] = [lo, hi]
        cells.append(f"[{lo:7.3f},{hi:7.3f}]")
    print(f"  {b:<10} " + "".join(f"{c:>22}" for c in cells))
print("  (V75 has 6 engagement episodes; a 3-vs-3 split-half is the weakest form of this null and")
print("   its interval is correspondingly wide. That WIDTH is the honest floor, not a defect.)")

V.hdr("2. THE CONTRASTS, every band, against those floors")
print(f"  {'contrast':<20} " + "".join(f"{k:>26}" for k in KEYS))
for a, b in (("V75/r5e", "V74/r5d"), ("V75/r5e", "V73/r5a"), ("V74/r5d", "V73/r5a")):
    cells = []
    for k in KEYS:
        p, lo, hi = ci(pairs(a, k), pairs(b, k))
        OUT.setdefault("contrast", {})[f"{a}/{b}|{k}"] = [p, lo, hi]
        cells.append(f"{p:6.3f}[{lo:6.3f},{hi:7.3f}]")
    print(f"  {a.split('/')[0]:>7}/{b.split('/')[0]:<11} " + "".join(f"{c:>26}" for c in cells))
print("\n  ★ Read row 3 (V74/V73) as the CROSS-ROUTE NULL CONTRAST: two different routes, and the")
print("  V74 session's own conclusion was that V74's step over V73 is not visible. If this")
print("  estimator returns ~1 there and 0.35 on V75/V74, a route change alone does not produce it.")

V.hdr("3. THE ABSOLUTE 24-28 Hz CONTROL LEVEL -- is the denominator itself stable?")
print("  The relative excess divides by 24-28. If that band moved between routes, every ratio")
print("  above inherits it. Row `e_24-28` in section 2 is the ABSOLUTE control (not divided by")
print("  itself), so it answers this directly.")

with open(ROOT / "_v78_null.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _v78_null.json")
