#!/usr/bin/env python3
"""Route-47 (V67) additions to the grind-#2 harness. Import this; do not re-implement.

Everything here is ADDITIVE on top of `_grind2_lib`. The window records, bands, envelope
estimator, episode bootstrap and split-half null all come from there unchanged, so a ratio
computed on route 47 is computed with the identical instrument as every prior route.

What this file adds:

  AUGMENT   Extra per-window covariates that the highway question needs and the creep question
            never did: openpilot's own command (`cc_req`, `e4tq`) and its slew, an approximate
            lateral acceleration, the manoeuvre size (angle excursion inside the window), and the
            0x0E4 command's own 30-49 Hz content. Computed by RE-SLICING the cache at the window's
            own `t0`, so no duplicate window loop can drift from `_grind2_lib.wrecs`.

  PURE      `gate` is the MEAN of the gate bit over the window. A window straddling an engage
            transition has 0 < gate < 1 and is NOT a valid sample of either dose. `pure_gate`
            keeps only gate <= 0.02 or gate >= 0.98.

🛑 THE CENTRAL EXPOSURE FACT OF ROUTE 47, measured, not assumed (see §0 of studies/sessions/r47/analyze_r47_grind2.py):
   g6806 == carControl.latActive in 150,302 / 150,327 frames (99.983%), and the gate is 0 for
   essentially every frame above 8 m/s ==> **there is no Kd=1 highway sample anywhere in this kit.**
   The within-route A/B is therefore a CREEP-ONLY test, and at highway speed the gate arm is
   confounded 1:1 with LKAS engagement. Any script that reports a "gated dose curve" at highway
   speed on this route is reporting an empty cell.

Usage:  import _r47_lib as R ;  store = R.records()
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
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
from _r31_common import fs_of, load  # noqa: E402

PKL = HERE.parent / "_scratch/data/_cache_r47_records.pkl"

# 🛑 Deliberately NOT added to G.ORDER or G.DOSE: every existing analyze_grind2_*.py iterates those,
# and silently changing the creep pools would rewrite results that are already on record. The highway
# question needs V58/r2b, so it lives here.
ORDER_HWY = G.ORDER + ["V58/r2b"]
# DELIVERED rate-lane multiplier at HIGHWAY speed, from the orchestrator's byte-read of all four
# images: stock r24 is a speed x motor-rate LERP that rolls OFF with speed (3072 at 0 km/h ->
# 2151 at 100 km/h); V62/V65 replace it with a flat 5244 always, V67 with a flat 5244 only while
# LKAS applies. So the highway multiplier is 5244/2151 = 2.44x, not 2.00x.
DOSE_HWY = {1.00: ["V58/r2b", "V59/r2c"], 2.00: ["V62/r37", "V65/r3b"], 2.44: ["V67/r47"]}

# 2020 Accord, opendbc honda/values.py:168. Only ever used for the APPROXIMATE lateral-accel
# covariate -- a ranking variable, never a calibrated number.
STEER_RATIO, WHEELBASE = 16.33, 2.83

# Established wheel circumference for this car (memory: accord-v57-confirms-wheel-order-tyre-line).
CIRC_LO, CIRC_HI = 2.073, 2.088


def wheel_order(v, n=1, circ=(CIRC_LO + CIRC_HI) / 2):
    """Hz of the n-th wheel-rotation order at road speed v (m/s)."""
    return n * np.asarray(v, float) / circ


def alias_family(f_obs, fs, kmax=2):
    """Every true frequency consistent with `f_obs` on a sample rate `fs`.

    A real-valued sampler folds about every multiple of fs/2, so f_obs is indistinguishable from
    k*fs +/- f_obs for all k. Reported as a list because the kit has twice quoted a folded
    frequency as if it were the physical one.
    """
    out = [float(f_obs)]
    for k in range(1, kmax + 1):
        out += [float(k * fs - f_obs), float(k * fs + f_obs)]
    return sorted(out)


def augment(recs, nfft=G.NFFT):
    """Add the highway covariates to records already produced by `_grind2_lib.wrecs`.

    Re-slices each window from its own cache by locating `t0` in `d["t"]`, so the slice is the
    SAME slice `wrecs` used -- no second window loop that could drift out of step.
    """
    by = {}
    for r in recs:
        by.setdefault((r["build"], r["seg"]), []).append(r)
    for (build, seg), rs in by.items():
        B = G.BUILDS[build]
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        if not p.exists():
            continue
        d = load(seg, B["cache"], B["pfx"])
        fs = fs_of(d)
        t = np.asarray(d["t"], float)
        taper = np.hanning(nfft) + 1e-3
        cw = slice(int(0.2 * nfft), int(0.8 * nfft))
        ang = np.asarray(d["ang"], float)
        v = np.asarray(d["cs_v"], float)
        e4 = np.asarray(d["e4tq"], float)
        req = np.asarray(d["cc_req"], float)
        press = np.asarray(d.get("cs_press", np.zeros_like(t)), float)
        for r in rs:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            sl = slice(i0, i0 + nfft)
            a, vv = ang[sl], np.abs(v[sl])
            if len(a) < nfft:
                r["latacc"] = r["dang"] = r["angsd"] = np.nan
                r["req"] = r["dreq"] = r["e4sd"] = r["e4hf"] = r["press"] = np.nan
                continue
            # steady-state bicycle model: a_lat = v^2 * delta / (SR * WB). Approximate by design.
            r["latacc"] = float(np.mean(vv ** 2 * np.abs(a) * np.pi / 180.0
                                        / (STEER_RATIO * WHEELBASE)))
            r["dang"] = float(np.max(a) - np.min(a))          # angle excursion = manoeuvre size
            r["angsd"] = float(np.std(a))
            r["vsd"] = float(np.std(vv))
            r["req"] = float(np.mean(np.abs(req[sl])))
            r["reqmax"] = float(np.max(np.abs(req[sl])))
            r["dreq"] = float(np.mean(np.abs(np.diff(req[sl]))) * fs)
            r["e4sd"] = float(np.std(e4[sl]))
            r["e4max"] = float(np.max(np.abs(e4[sl])))
            # the COMMAND's own 30-49 Hz content: if the 45 Hz line is being commanded rather than
            # excited, it must be visible on 0x0E4 as well as on the torsion bar.
            r["e4hf"] = G.win_env(e4[sl], fs, 30.0, 49.0, taper, cw)
            r["press"] = float(np.mean(press[sl] > 0.5))
            r["gate_pure"] = (1.0 if (not np.isfinite(r.get("gate", np.nan))
                                      or r["gate"] <= 0.02 or r["gate"] >= 0.98) else 0.0)
            r["w1"] = float(wheel_order(np.mean(vv), 1))
            r["w2"] = float(wheel_order(np.mean(vv), 2))
            r["w3"] = float(wheel_order(np.mean(vv), 3))
    return recs


def records(rebuild=False, order=None):
    """{build: [window records]} for every route including V67/r47, cached to a pickle."""
    order = order or G.ORDER
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            store = pickle.load(fh)
        if all(b in store for b in order):
            return store
    store = {}
    for b in order:
        store[b] = augment(G.wrecs(b))
    with open(PKL, "wb") as fh:
        pickle.dump(store, fh)
    return store


def sel(rs, **kw):
    """Filter records: sel(rs, v=(20, 99), gate=(0.98, 1.01)) -> half-open [lo, hi)."""
    out = rs
    for k, (lo, hi) in kw.items():
        out = [r for r in out if np.isfinite(r.get(k, np.nan)) and lo <= r[k] < hi]
    return out


def blockstat(rs, key, thr):
    """(blocks with >=1 exceedance, total blocks). A burst spanning 3 windows is ONE event."""
    blk = {}
    for r in rs:
        blk[r["blk"]] = blk.get(r["blk"], False) or (r[key] > thr)
    return sum(blk.values()), len(blk)


def boot_stat(rs, key, rng, fn, nboot=3000, unit="blk"):
    """(point, lo, hi) for fn(key), resampling `unit` (blk = ~10.2 s block, ep = engagement run)."""
    grp = {}
    for r in rs:
        grp.setdefault(r[unit], []).append(r)
    per = [G.col(vv, key) for vv in grp.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if not per:
        return np.nan, np.nan, np.nan
    allv = np.concatenate(per)
    dr = np.empty(nboot)
    for b in range(nboot):
        i = rng.integers(0, len(per), len(per))
        dr[b] = fn(np.concatenate([per[j] for j in i]))
    return float(fn(allv)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


def fisher2x2(a, b, c, d):
    """Two-sided Fisher exact on [[a,b],[c,d]] by exact hypergeometric enumeration."""
    from math import comb
    n, r1, c1 = a + b + c + d, a + b, a + c

    def pr(k):
        return comb(r1, k) * comb(n - r1, c1 - k) / comb(n, c1)
    p0 = pr(a)
    return float(sum(pr(k) for k in range(max(0, c1 - (n - r1)), min(r1, c1) + 1)
                     if pr(k) <= p0 * (1 + 1e-9)))
