#!/usr/bin/env python3
"""The strongest available cross-route contrast: relative excess matched on SPEED **and** MANOEUVRE
RATE simultaneously.

`v78_symptom_null.py` matches on speed alone. Grind #1 is documented as occurring "at 5 mph with the
wheel near zero", so a route that simply steered less would show less of it at the same speed. This
adds the manoeuvre-rate axis -- `rate_lp` = mean |lowpass(rate_c, 3 Hz)|, never raw |rate_c|, because
the raw channel contains the oscillation itself and would partly measure its own outcome.

Cells are 5 speed bins x 4 manoeuvre-rate bins; a cell enters only with >= 5 windows on BOTH sides.
V74/V73 is carried as the CROSS-ROUTE NULL CONTRAST throughout.

Usage:  python v78_symptom_matched.py   ->  writes _v78_matched.json
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import v78_symptom_lib as V  # noqa: E402

RNG = np.random.default_rng(4242)
G.EPKEY = "blk"
V.install_fs()
VB = [(0.5, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5)]
RB = [(0.0, 4.0), (4.0, 10.0), (10.0, 20.0), (20.0, 1e9)]
KEYS = ["e_6-9", "e_18-22", "e_40-49"]

with open(ROOT / "_cache_r5d_nearcentre.pkl", "rb") as fh:
    store = pickle.load(fh)
with open(ROOT / "_cache_r5e_sym_nearcentre.pkl", "rb") as fh:
    store.update(pickle.load(fh))


def arm(b):
    return [r for r in store[b] if r["eng"] == 1 and 0.5 <= r["v"] < 12.5
            and np.isfinite(r.get("rate_lp", np.nan)) and r.get("e_24-28", 0) > 0]


def strat(a, b, key, minn=5):
    num = den = 0.0
    nc = 0
    for v in VB:
        for rr in RB:
            xa = [r[key] / r["e_24-28"] for r in a
                  if v[0] <= r["v"] < v[1] and rr[0] <= r["rate_lp"] < rr[1] and np.isfinite(r[key])]
            xb = [r[key] / r["e_24-28"] for r in b
                  if v[0] <= r["v"] < v[1] and rr[0] <= r["rate_lp"] < rr[1] and np.isfinite(r[key])]
            if len(xa) < minn or len(xb) < minn:
                continue
            ma, mb = np.median(xa), np.median(xb)
            if ma <= 0 or mb <= 0:
                continue
            w = 1.0 / (1.0 / len(xa) + 1.0 / len(xb))
            num += w * np.log(ma / mb)
            den += w
            nc += 1
    return (np.exp(num / den) if den else np.nan), nc


def ci(A, B, key, nb=2500):
    ea, eb = {}, {}
    for r in A:
        ea.setdefault(r[G.EPKEY], []).append(r)
    for r in B:
        eb.setdefault(r[G.EPKEY], []).append(r)
    ka, kb = list(ea), list(eb)
    d = np.full(nb, np.nan)
    for i in range(nb):
        aa = [r for j in RNG.integers(0, len(ka), len(ka)) for r in ea[ka[j]]]
        bb = [r for j in RNG.integers(0, len(kb), len(kb)) for r in eb[kb[j]]]
        d[i] = strat(aa, bb, key)[0]
    p, nc = strat(A, B, key)
    return p, float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5)), nc


V.hdr("SPEED x MANOEUVRE-RATE MATCHED relative excess over the 24-28 Hz control, engaged 0.5-12.5")
print(f"  {'contrast':<16}" + "".join(f"{k:>30}" for k in KEYS))
OUT = {}
for a, b in (("V75/r5e", "V74/r5d"), ("V75/r5e", "V73/r5a"), ("V74/r5d", "V73/r5a"),
             ("V75/r5e", "V72/r59")):
    cells = []
    for key in KEYS:
        p, lo, hi, nc = ci(arm(a), arm(b), key)
        OUT[f"{a}/{b}|{key}"] = [p, lo, hi, nc]
        cells.append(f"{p:6.3f}[{lo:6.3f},{hi:7.3f}] c={nc}")
    print(f"  {a.split('/')[0]:>6}/{b.split('/')[0]:<9}" + "".join(f"{c:>30}" for c in cells))
print("\n  row 3 (V74/V73) is the CROSS-ROUTE NULL CONTRAST. 40-49 Hz (grind #2) is a further")
print("  negative control -- no build in this trio touched the rate lane.")

with open(ROOT / "_v78_matched.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _v78_matched.json")
