#!/usr/bin/env python3
r"""studies/impedance/rez_crossover.py -- THE Re(Z) ZERO-CROSSING FREQUENCY: a better endpoint than a fixed-band sign.

`studies/impedance/rez_band_tracking.py` shows the anti-damping is NOT a notch sitting on the mode.  It is a broad
negative region running from low frequency up to a ZERO CROSSING, and what our builds do is push
that crossing UPWARD:

    STOCK 1x  negative 16-22 Hz, crossing ~21-23      V100 4x  negative 16-23, crossing ~23-25
    V102 6x   negative 16-25 Hz, crossing ~24-26

So the physically meaningful scalar is **f0, the frequency where Re(Z) crosses zero** -- the top of
the anti-damped region.  It is continuous rather than binary, monotone in gain, has a measured
STOCK target, uses every band in the fit rather than one, and -- the point `route-v102` raised --
**is immune to mode migration by construction**, because a migrating mode cannot carry the endpoint
out of its evaluation window: the endpoint IS the window's location.

f0 is estimated by a weighted linear fit of Re(Z) against frequency across the crossing region and
solving for the root, block-bootstrapped over windows.  Estimator imported read-only from
`decode_v90_probe`; `studies/impedance/rez_control.py` pins it to 0.00 % against `_scratch/logs/v92_rez.log`.
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L          # noqa: E402
import decode_v90_probe as P     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

L.ROUTES["97"] = L._mk("97", "V9b-STOCK", gain=891, clamp=512, leverB=False, idcode=0, bits="stock")
L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")
ARMS = [("97", "STOCK 1x", 891), ("85", "V100 4x", 3564), ("96", "V102 6x", 5346)]
DEG2RAD = np.pi / 180.0
RNG = np.random.default_rng(103_2026)
VLO, VHI = 8.0, 24.0
FIT = np.arange(19.0, 30.0, 1.0)      # 2 Hz bands starting here -- brackets every arm's crossing
OUT = {}


def wins(route, hop):
    R = L.ROUTES[route]
    z = np.load(R["cache"] / ("r" + route + ".npz"), allow_pickle=True)
    t = np.asarray(z["t"], float)
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    W = P._wins(lat & (~press) & (v > 0.5), t, P.NW_Z, hop,
                (np.asarray(z["rate_f"], float) * DEG2RAD, np.asarray(z["tq"], float), v))
    return ([w for w in W if VLO <= float(np.median(w[2])) < VHI],
            1.0 / float(np.median(np.diff(t))))


def f0_of(pairs, fs):
    """Zero-crossing frequency of Re(Z), from a linear fit over the crossing region."""
    f, y = [], []
    for lo in FIT:
        r = P._band_transfer(pairs, fs, P.NW_Z, [("b", lo, lo + 2.0)])["b"]
        f.append(lo + 1.0)
        y.append(r["re_over_sxx"])
    f, y = np.array(f), np.array(y)
    if not (np.any(y < 0) and np.any(y > 0)):
        return np.nan
    c = np.polyfit(f, y, 1)
    return float(-c[1] / c[0]) if c[0] != 0 else np.nan


def main():
    print("\n" + "=" * 104)
    print("Re(Z) ZERO-CROSSING FREQUENCY f0 -- engaged, hands-off, 29-86 km/h")
    print("=" * 104)
    res = {}
    for rt, lab, gain in ARMS:
        W, fs = wins(rt, P.HOP_Z)
        if len(W) < 8:
            print("\n  %-11s only %d windows -- NOT SCOREABLE" % (lab, len(W)))
            continue
        pairs = [(w[0], w[1]) for w in W]
        pt = f0_of(pairs, fs)
        bs = []
        for _ in range(300):
            v = f0_of([pairs[k] for k in RNG.integers(0, len(pairs), len(pairs))], fs)
            if np.isfinite(v):
                bs.append(v)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print("\n  %-11s n=%3d windows   f0 = %.2f Hz   95%% CI [%.2f, %.2f]   (gain cal %d)"
              % (lab, len(W), pt, lo, hi, gain))
        res[rt] = dict(build=lab, gain=gain, n=len(W), f0=pt, lo=float(lo), hi=float(hi))
        OUT[rt] = res[rt]

    if len(res) >= 2:
        print("\n  ==> f0 MARCHES WITH GAIN:")
        for rt in ("97", "85", "96"):
            if rt in res:
                r = res[rt]
                print("      %-11s gain %5d (%.1fx stock)   f0 %.2f Hz [%.2f, %.2f]"
                      % (r["build"], r["gain"], r["gain"] / 891.0, r["f0"], r["lo"], r["hi"]))
        if "97" in res and "96" in res:
            d = res["96"]["f0"] - res["97"]["f0"]
            print("      V102 - STOCK = %+.2f Hz   (CIs %s)"
                  % (d, "DISJOINT" if res["96"]["lo"] > res["97"]["hi"] else "OVERLAP"))

    # ---- power: how many NON-OVERLAPPING windows to separate V102's f0 from stock's?
    print("\n" + "=" * 104)
    print("POWER on f0 -- non-overlapping windows, so the seconds are honest")
    print("=" * 104)
    for rt, lab, _g in ARMS:
        W, fs = wins(rt, P.NW_Z)
        pairs = [(w[0], w[1]) for w in W]
        if len(pairs) < 8:
            continue
        print("\n  --- %s: %d non-overlapping windows (%.0f s) ---"
              % (lab, len(pairs), len(pairs) * P.NW_Z / fs))
        print("      %6s %9s %22s %10s" % ("n_win", "eng_s", "median 95% CI on f0", "width Hz"))
        for n in (8, 12, 16, 20, 30, 40):
            if n > len(pairs) * 3:
                break
            los, his = [], []
            for _ in range(60):
                bs = []
                for _ in range(60):
                    v = f0_of([pairs[k] for k in RNG.integers(0, len(pairs), n)], fs)
                    if np.isfinite(v):
                        bs.append(v)
                if len(bs) > 10:
                    a, b = np.percentile(bs, [2.5, 97.5])
                    los.append(a); his.append(b)
            if los:
                ml, mh = np.median(los), np.median(his)
                print("      %6d %9.0f    [%6.2f, %6.2f] %10.2f"
                      % (n, n * P.NW_Z / fs, ml, mh, mh - ml))
                OUT.setdefault("power", {}).setdefault(rt, {})[n] = dict(
                    eng_s=n * P.NW_Z / fs, lo=float(ml), hi=float(mh), width=float(mh - ml))


if __name__ == "__main__":
    main()
    Path(__file__).with_name("_scratch/out/_rez_crossover.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_rez_crossover.json")
