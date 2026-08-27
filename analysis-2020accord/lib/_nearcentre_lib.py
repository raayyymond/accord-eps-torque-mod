#!/usr/bin/env python3
"""NEAR-CENTRE conditional for grind #1 -- the signed-angle augmentation the corpus never carried.

🛑 WHY THIS FILE EXISTS. `_grind2_lib.wrecs` records `r["ang"] = mean(|ang|)` -- an ABSOLUTE value,
taken on the RAW CAN channel. That is unusable for the operator's conditional for two reasons:

  1. The operator's steering sensor carries a **+/- 4 deg offset**, so "centred" is a region around
     the SENSOR's own zero, not around 0.0. An absolute value cannot be re-centred after the fact:
     mean(|x|) is not recoverable to mean(x - c).
  2. mean(|ang|) over a 2.56 s window through centre reads ~0 for a fast sweep AND for a genuine
     hold at centre. The two must be separable, or "near centre" is confounded with "low rate" by
     construction -- which is the single question this task exists to settle.

So this adds SIGNED per-window angle statistics, re-sliced from each cache at the window's own `t0`
exactly the way `_r47_lib.augment` does, so the slice is the same slice `wrecs` used.

Everything numeric downstream is `_grind2_lib` unchanged: same `e_18-22` envelope, same episode
bootstrap, same split-half null, same `fs_lattice` sample rate.
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r59_lib as L  # noqa: E402  -- registers V72/r59 and re-exports r54/r58/r50/r4f

PKL = ROOT / "_scratch/data/_cache_nearcentre_records_v72.pkl"

CREEP = 20 / 3.6            # 5.556 m/s -- the kit's standing creep cut for grind #1
NFFT = G.NFFT

# The ladder in the record's own order (studies/sessions/r58/r58_grind1.py ss1), plus their r24/r26 creep prices.
LADDER = ["V61/r31", "V59/r2c", "V64/r35", "V58/r2b", "V69/r4f", "V70/r50", "V62/r37", "V65/r3a",
          "V65/r3b", "V67/r47", "V68/r4e", "V71B/r54", "V71C/r58", "V72/r59"]
PRICE = {"V61/r31": (0.000, 1.000), "V59/r2c": (1.000, 1.000), "V64/r35": (1.000, 1.000),
         "V58/r2b": (1.000, 1.000), "V69/r4f": (1.000, 1.000), "V70/r50": (1.000, 1.000),
         "V62/r37": (2.000, 2.000), "V65/r3a": (2.000, 2.000), "V65/r3b": (2.000, 2.000),
         "V67/r47": (2.452, 0.167), "V68/r4e": (2.452, 0.167),
         "V71B/r54": (1.000, 2.000), "V71C/r58": (0.931, 1.000),
         # ⚠ V72 is UNGATED: the same pair applies in the MANUAL arm too (`_r59_lib`).
         "V72/r59": (1.862, 0.169)}
# Arms as `studies/sessions/r58/r58_grind1.py` groups them -- so a number here is comparable to one already on record.
ARMS = {"stock pool": ["V59/r2c", "V64/r35", "V58/r2b"],
        "V61 (kill)": ["V61/r31"],
        "V62+V65": ["V62/r37", "V65/r3a", "V65/r3b"],
        "V67+V68": ["V67/r47", "V68/r4e"],
        "V69/r4f": ["V69/r4f"], "V70/r50": ["V70/r50"],
        "V71B/r54": ["V71B/r54"], "V71C/r58": ["V71C/r58"],
        "V72/r59": ["V72/r59"]}


# ------------------------------------------------------------------ the augmentation -------------
def augment_angle(recs, nfft=NFFT):
    """Signed per-window angle + rate statistics, re-sliced at each window's own `t0`.

    Adds, on `cs_ang` (carState.steeringAngleDeg, signed) unless noted:
        a_mean  a_med   signed mean / median over the window
        a_absm            mean |cs_ang|  (the re-centrable counterpart of `wrecs`'s `ang`)
        a_min a_max a_sd
        a_cross           1 if the window CONTAINS a zero crossing of cs_ang, else 0
        a_raw             signed mean of the RAW CAN `ang` channel -- an independent second method
        rate_sm           signed mean of rate_c (deg/s)
        rate_absm         mean |rate_c|      (== `wrecs`'s `rate`, recomputed as a cross-check)
        rate_p95          p95 |rate_c|
        rate_dadt         |cs_ang[-1] - cs_ang[0]| / window duration -- an FFT-free rate, so the
                          angle/rate discrimination does not rest on one channel's own scaling
        rate_lp           mean |lowpass(rate_c, 3 Hz)| -- the MANOEUVRE rate
        e18_ang           p99 of the 18-22 Hz envelope of the ANGLE channel
        e18_cmd           p99 of the 18-22 Hz envelope of openpilot's 0x0E4 command

    🛑🛑 `rate_lp` EXISTS BECAUSE THE RAW RATE IS CIRCULAR. `rate_c` is sampled at ~100 Hz and a
    21 Hz oscillation of angle amplitude A contributes 2*pi*21*A deg/s to mean |rate_c| -- roughly
    132 deg/s per degree of oscillation. So "high mean |rate_c|" can BE grind #1 rather than a
    condition for it, and a rate axis built on the raw channel is partly measuring its own outcome.
    This is the identical trap `_r31_common.sustained` exists for on the torque channel ("EFFORT is
    sustained |lowpass(tq, 3 Hz)|, never raw |tq| -- the oscillation trips the raw test"), applied
    to the rate channel, where the corpus had never applied it.
    """
    by = {}
    for r in recs:
        by.setdefault((r["build"], r["seg"]), []).append(r)
    for (build, seg), rs in by.items():
        B = G.BUILDS[build]
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        if not p.exists():
            continue
        d = C.load(seg, B["cache"], B["pfx"])
        t = np.asarray(d["t"], float)
        fs = G.fs_of(d)
        taper = np.hanning(nfft) + 1e-3
        cw = slice(int(0.2 * nfft), int(0.8 * nfft))
        ca = np.asarray(d["cs_ang"], float)
        ra = np.asarray(d["ang"], float)
        rc = np.asarray(d["rate_c"], float)
        e4 = np.asarray(d["e4tq"], float)
        for r in rs:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            sl = slice(i0, i0 + nfft)
            a, rw, q = ca[sl], ra[sl], rc[sl]
            if len(a) < nfft:
                for k in ("a_mean", "a_med", "a_absm", "a_min", "a_max", "a_sd", "a_cross",
                          "a_raw", "rate_sm", "rate_absm", "rate_p95", "rate_dadt", "rate_lp",
                          "e18_ang", "e18_cmd"):
                    r[k] = np.nan
                continue
            r["rate_lp"] = float(np.mean(np.abs(C.sustained(q, fs, 3.0))))
            r["e18_ang"] = G.win_env(rw, fs, 18.0, 22.0, taper, cw)
            r["e18_cmd"] = G.win_env(e4[sl], fs, 18.0, 22.0, taper, cw)
            r["a_mean"] = float(np.mean(a))
            r["a_med"] = float(np.median(a))
            r["a_absm"] = float(np.mean(np.abs(a)))
            r["a_min"], r["a_max"] = float(np.min(a)), float(np.max(a))
            r["a_sd"] = float(np.std(a))
            r["a_cross"] = float(np.min(a) < 0.0 < np.max(a))
            r["a_raw"] = float(np.mean(rw))
            r["rate_sm"] = float(np.mean(q))
            r["rate_absm"] = float(np.mean(np.abs(q)))
            r["rate_p95"] = float(np.percentile(np.abs(q), 95))
            dt = float(t[min(i0 + nfft - 1, len(t) - 1)] - t[i0])
            r["rate_dadt"] = float(abs(a[-1] - a[0]) / dt) if dt > 0 else np.nan
    return recs


def route_zero(build, store, vhi_hwy=11.0, vhi_fall=5.0):
    """The route's OWN sensor zero: median signed cs_ang at straight-ahead cruise.

    🛑 The operator's sensor carries a +/- 4 deg offset, so `|cs_ang| < 5` around a HARD zero is not
    the same cell as `|cs_ang - c| < 5`. `c` is estimated from the route's own straight cruise --
    the only self-contained definition of "the sensor reads centre".

    Returns (c, n_windows_used, tier). Tier "hwy" = >= 40 km/h windows; "mid" = >= 18 km/h;
    "all" = every driving window (weakest -- a route with asymmetric turning biases it).
    """
    rs = [r for r in store.get(build, []) if np.isfinite(r.get("a_mean", np.nan))]
    for tier, vlo in (("hwy", vhi_hwy), ("mid", vhi_fall)):
        sub = [r for r in rs if r["v"] >= vlo and r["rate_absm"] < 8.0]
        if len(sub) >= 20:
            return float(np.median([r["a_mean"] for r in sub])), len(sub), tier
    sub = [r for r in rs if r["rate_absm"] < 8.0]
    if len(sub) >= 20:
        return float(np.median([r["a_mean"] for r in sub])), len(sub), "all"
    return 0.0, len(sub), "EMPTY (c forced to 0)"


def records(rebuild=False):
    """`_r58_lib.records()` plus the signed-angle augmentation, cached."""
    L.install_fs()
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            store = pickle.load(fh)
        if all(b in store for b in LADDER) and "rate_lp" in (store[LADDER[0]][0] or {}):
            return store
    base = L.records()
    store = {}
    for b in LADDER:
        store[b] = augment_angle([dict(r) for r in L.driving(base.get(b, []), b)], nfft=NFFT)
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)
    return store


# ------------------------------------------------------------------ selection helpers ------------
def eng_creep(rs, creep=CREEP):
    return [r for r in rs if r["eng"] == 1 and r["v"] < creep]


def man_creep(rs, creep=CREEP):
    return [r for r in rs if r["eng"] == 0 and r["v"] < creep]


def recell(rs, fn):
    """Restratify: `_grind2_lib`'s `cell` is (eng, v, eff, rate) and its FIRST component is
    engagement, so an engaged and a manual window can never share a cell."""
    out = []
    for r in rs:
        q = dict(r)
        q["cell"] = fn(r)
        out.append(q)
    return out


A_BINS = [(0.0, 5.0), (5.0, 15.0), (15.0, 45.0), (45.0, 100.0), (100.0, 1e9)]
A_NAMES = ["0-5", "5-15", "15-45", "45-100", "100+"]
RATE_BINS = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 1e9)]     # == G.R_BINS
RATE_NAMES = ["0-4", "4-16", "16-32", "32+"]


def abin(x, bins=A_BINS):
    for i, (lo, hi) in enumerate(bins):
        if lo <= x < hi:
            return i
    return len(bins) - 1


def hdr(s):
    print(f"\n{'=' * 112}\n{s}\n{'=' * 112}")
