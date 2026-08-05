#!/usr/bin/env python3
"""D4 shared: cache `r47_orchestrator_checks._windows` rows for every pool ONCE.

Nothing numeric is added -- the rows are exactly what `r58_grind2.py` / `r58_r54_highrate_4049.py`
build, so every count stays comparable to the corpus. Only two derived keys are attached, both
already established: `idx` (rate index at PEAK |rate_c|) and `eff` (sustained driver effort).
"""
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import r47_orchestrator_checks as R47  # noqa: E402
from _r31_common import sustained  # noqa: E402

PKL = ROOT / "_d4_rows.pkl"
CPD = 4.7121
CREEP = (0.3, 4.0)
HWY = 14.0

POOLS = {
    "Kd=0     (V61 r31)":                     ["_cache_r31"],
    "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)": ["_cache_r2b", "_cache_r2c", "_cache_r35"],
    "Kd=2.00  (V62 r37 + V65 r3a/r3b)":       ["_cache_r37", "_cache_r3a", "_cache_r3b"],
    "Kd=gated (V67 r47 + V68 r4e)":           ["_cache_r47", "_cache_v68"],
    "Kd=4x<50 (V69 r4f)":                     ["_cache_r4f"],
    "Kd=2x<50 (V70 r50)":                     ["_cache_r50"],
    "V71B r54  r26 x2 UNGATED":               ["_cache_r54"],
    "V71C r58  both arms GATED":              ["_cache_r58"],
    "V72 r59  BOTH lanes UNGATED  ***":       ["_cache_r59"],
}
SKIP = {"_cache_r54": ("r54s10", "r54s11"),
        "_cache_r58": ("r58s12", "r58s13", "r58s14", "r58s15"),
        "_cache_r50": ("r50s0",),
        "_cache_r59": ("r59s12", "r59s13", "r59s14")}
REF = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
NEW = "V72 r59  BOTH lanes UNGATED  ***"
RB = [(0.0, 400.0), (400.0, 1400.0), (1400.0, 1e9)]
RNAMES = ["plateau", "knee", "HIGH-RATE"]


def rows(rebuild=False):
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            return pickle.load(fh)
    out = {}
    for name, caches in POOLS.items():
        r = []
        for c in caches:
            rr = R47._windows(c, name, lambda v: True)
            r += [x for x in rr if not any(s in str(x["ep"][0]) for s in SKIP.get(c, ()))]
        for x in r:
            x["idx"] = CPD * x["ratemax"]
            x["eff"] = float(np.median(np.abs(sustained(np.asarray(x["raw"], float), x["fs"]))))
            x["rb"] = next(i for i, (lo, hi) in enumerate(RB) if lo <= x["idx"] < hi)
            x.pop("raw", None)          # 2.56 s of raw torque per window is 100 MB of pickle
        out[name] = r
    with open(PKL, "wb") as fh:
        pickle.dump(out, fh)
    return out


def secs(rs):
    return len(rs) * R47.WIN_S / 2.0


def bursts(rs, key="40-49"):
    return int(sum(1 for r in rs if r[key] > R47.BURST))


def hdr(s):
    print("\n" + "=" * 120 + f"\n{s}\n" + "=" * 120)
