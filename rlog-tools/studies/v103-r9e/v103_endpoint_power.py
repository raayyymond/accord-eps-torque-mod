#!/usr/bin/env python3
r"""studies/v103-r9e/v103_endpoint_power.py -- THE V103 ENDPOINT SPEC, with its power calculation MEASURED.

Answers, from data rather than assertion:
  P1  Is Re(Z) robust to the band edges?  (i.e. does it need `route-v102`'s 20-28 widening?)
  P2  How many engaged hands-off seconds in 29-86 km/h to resolve a SIGN FLIP at 22-26 Hz?
  P3  What is the smallest change at 6-9 Hz we could detect at a given exposure?
  P4  Is 26-31 Hz the right negative control, and what must the shuffled-pair value look like?

🛑 INDEPENDENCE.  The frozen Re(Z) estimator runs NW_Z = 512 with HOP_Z = 256, i.e. **50 % overlap**,
   so its windows are NOT independent and a naive bootstrap over them understates the CI.  Every
   power number below is computed on NON-OVERLAPPING windows (HOP = NW_Z) and is therefore
   CONSERVATIVE.  The point estimates still use the frozen 50 % hop so they stay comparable with
   `_scratch/logs/v92_rez.log` and with everything reported this session.

🛑 Estimator is imported read-only from `decode_v90_probe`; `studies/impedance/rez_control.py` pins it to 0.00 %
   against `_scratch/logs/v92_rez.log`'s published route-77 table.  Run that FIRST if anything here looks wrong.
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
ARMS = [("97", "STOCK 1x"), ("96", "V102 6x"), ("85", "V100 4x")]
DEG2RAD = np.pi / 180.0
RNG = np.random.default_rng(103_2026)
VLO, VHI = 8.0, 24.0                      # m/s == 29-86 km/h, the band where the flip lives
OUT = {}


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


def wins(route, hop):
    R = L.ROUTES[route]
    z = np.load(R["cache"] / ("r" + route + ".npz"), allow_pickle=True)
    t = np.asarray(z["t"], float)
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    W = P._wins(lat & (~press) & (v > 0.5), t, P.NW_Z, hop,
                (np.asarray(z["rate_f"], float) * DEG2RAD, np.asarray(z["tq"], float), v))
    fs = 1.0 / float(np.median(np.diff(t)))
    return [w for w in W if VLO <= float(np.median(w[2])) < VHI], fs


def rez(pairs, fs, lo, hi):
    return P._band_transfer(pairs, fs, P.NW_Z, [("b", lo, hi)])["b"]


def boot(pairs, fs, lo, hi, n=None, nboot=400):
    """Bootstrap Re(Z); if n is given, subsample n windows per draw (the power curve)."""
    k = n if n else len(pairs)
    out = [rez([pairs[j] for j in RNG.integers(0, len(pairs), k)], fs, lo, hi)["re_over_sxx"]
           for _ in range(nboot)]
    return np.array([o for o in out if np.isfinite(o)])


# =========================================================================================
def p1():
    hdr("P1 -- IS Re(Z) ROBUST TO THE BAND EDGES?\n"
        "     `route-v102` recommends widening the band-RMS endpoint to 20-28 Hz because the mode\n"
        "     MIGRATES (+0.157 Hz/(m/s), ~+1 Hz per gain doubling).  Re(Z) is a RATIO of a cross-\n"
        "     spectrum to an auto-spectrum, both summed over the SAME bins, so a common scale\n"
        "     factor cancels -- but that is an argument, not a measurement.  Here is the measurement.")
    OUT["p1"] = {}
    BANDS = [("21.5-25.5", 21.5, 25.5), ("22-26", 22.0, 26.0), ("20-28", 20.0, 28.0),
             ("18-30", 18.0, 30.0), ("6-9", 6.0, 9.0), ("26-31", 26.0, 31.0)]
    for rt, lab in ARMS:
        W, fs = wins(rt, P.HOP_Z)
        if len(W) < 8:
            print("\n  %-10s only %d windows in 29-86 km/h -- skipped" % (lab, len(W)))
            continue
        pairs = [(w[0], w[1]) for w in W]
        print("\n  --- %s, %d windows (29-86 km/h, engaged hands-off) ---" % (lab, len(W)))
        print("      %-11s %11s %20s %8s" % ("band", "Re(Z)", "95% CI", "coh2"))
        for bn, lo, hi in BANDS:
            r = rez(pairs, fs, lo, hi)
            b = boot(pairs, fs, lo, hi)
            blo, bhi = np.percentile(b, [2.5, 97.5])
            print("      %-11s %11.0f  [%8.0f, %8.0f] %8.3f"
                  % (bn, r["re_over_sxx"], blo, bhi, r["coh2"]))
            OUT["p1"].setdefault(rt, {})[bn] = dict(re_z=float(r["re_over_sxx"]),
                                                    lo=float(blo), hi=float(bhi),
                                                    coh2=float(r["coh2"]))
    a = OUT["p1"].get("97", {})
    b = OUT["p1"].get("96", {})
    if a and b:
        print("\n  SIGN AGREEMENT ACROSS BAND CHOICES (the thing that matters for a sign endpoint):")
        for bn in ("21.5-25.5", "22-26", "20-28", "18-30"):
            if bn in a and bn in b:
                print("      %-11s STOCK %+8.0f   V102 %+8.0f   %s"
                      % (bn, a[bn]["re_z"], b[bn]["re_z"],
                         "SIGNS DIFFER (endpoint holds)" if a[bn]["re_z"] * b[bn]["re_z"] < 0
                         else "same sign -- endpoint would NOT fire in this band"))


# =========================================================================================
def p2():
    hdr("P2 -- POWER: HOW MANY ENGAGED HANDS-OFF SECONDS TO RESOLVE THE SIGN FLIP AT 22-26 Hz?\n"
        "     Windows are NON-OVERLAPPING here (HOP = NW_Z = 5.12 s) so the count is honest.\n"
        "     Two curves:  (A) if V103 lands at STOCK's value, how often does the CI exclude 0\n"
        "     from ABOVE?   (B) if V103 stays at V102's value, how often from BELOW?")
    OUT["p2"] = {}
    for rt, lab, side in (("97", "STOCK (+, the TARGET)", +1), ("96", "V102 (-, NO CHANGE)", -1)):
        W, fs = wins(rt, P.NW_Z)
        pairs = [(w[0], w[1]) for w in W]
        print("\n  --- %s: %d NON-OVERLAPPING windows available (%.0f s) ---"
              % (lab, len(W), len(W) * P.NW_Z / fs))
        if len(W) < 8:
            print("      too few -- skipped")
            continue
        full = rez(pairs, fs, 22.0, 26.0)["re_over_sxx"]
        print("      full-sample Re(Z) 22-26 = %+.0f" % full)
        print("      %6s %9s %12s %22s %10s" % ("n_win", "eng_s", "P(CI excl 0)", "median CI", "width"))
        for n in (8, 12, 16, 20, 25, 30, 40, 50):
            if n > len(pairs) * 3:
                break
            los, his, hit = [], [], 0
            for _ in range(300):
                b = boot(pairs, fs, 22.0, 26.0, n=n, nboot=60)
                lo, hi = np.percentile(b, [2.5, 97.5])
                los.append(lo); his.append(hi)
                hit += 1 if (lo > 0 if side > 0 else hi < 0) else 0
            ml, mh = np.median(los), np.median(his)
            print("      %6d %9.0f %11.2f   [%+8.0f, %+8.0f] %10.0f"
                  % (n, n * P.NW_Z / fs, hit / 300.0, ml, mh, mh - ml))
            OUT["p2"].setdefault(rt, {})[n] = dict(eng_s=n * P.NW_Z / fs, power=hit / 300.0,
                                                   ci_lo=float(ml), ci_hi=float(mh))


# =========================================================================================
def p3():
    hdr("P3 -- SMALLEST DETECTABLE CHANGE AT 6-9 Hz (the ratchet secondary).\n"
        "     Stock -1297 / -1709 / -1507 across the three speed bands; our builds x2.4-3.0 at\n"
        "     29-86 km/h.  The question a build needs answered: what RATIO change is resolvable?")
    OUT["p3"] = {}
    for rt, lab in (("97", "STOCK 1x"), ("96", "V102 6x")):
        W, fs = wins(rt, P.NW_Z)
        pairs = [(w[0], w[1]) for w in W]
        if len(pairs) < 8:
            continue
        full = rez(pairs, fs, 6.0, 9.0)["re_over_sxx"]
        print("\n  --- %s: %d non-overlapping windows, Re(Z) 6-9 = %+.0f ---"
              % (lab, len(pairs), full))
        print("      %6s %9s %20s %12s   %s"
              % ("n_win", "eng_s", "95% CI", "half-width", "min detectable ratio"))
        for n in (8, 12, 16, 20, 30, 40, 50):
            if n > len(pairs) * 3:
                break
            b = boot(pairs, fs, 6.0, 9.0, n=n, nboot=400)
            lo, hi = np.percentile(b, [2.5, 97.5])
            hw = (hi - lo) / 2.0
            # two independent arms of the same size => sqrt(2) x the half-width
            mdr = (abs(full) + np.sqrt(2) * hw) / abs(full)
            print("      %6d %9.0f  [%+8.0f, %+8.0f] %12.0f   %.2fx  (or 1/%.2f)"
                  % (n, n * P.NW_Z / fs, lo, hi, hw, mdr, mdr))
            OUT["p3"].setdefault(rt, {})[n] = dict(eng_s=n * P.NW_Z / fs, half_width=float(hw),
                                                  min_detectable_ratio=float(mdr))


# =========================================================================================
def p4():
    hdr("P4 -- CONTROLS.  Is 26-31 Hz the right negative control, and what must the shuffled-pair\n"
        "     value be for a run to be VALID?")
    OUT["p4"] = {}
    for rt, lab in ARMS:
        W, fs = wins(rt, P.HOP_Z)
        if len(W) < 8:
            continue
        pairs = [(w[0], w[1]) for w in W]
        print("\n  --- %s ---" % lab)
        print("      %-8s %11s %9s %9s %9s   %s"
              % ("band", "Re(Z)", "coh2", "shuffled", "ratio", "verdict"))
        for bn, lo, hi in (("6-9", 6.0, 9.0), ("18-22", 18.0, 22.0), ("22-26", 22.0, 26.0),
                           ("26-31", 26.0, 31.0), ("31-35", 31.0, 35.0)):
            r = rez(pairs, fs, lo, hi)
            idx = RNG.permutation(len(pairs))
            s = rez([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                     for i in range(len(pairs))], fs, lo, hi)
            ratio = r["coh2"] / max(s["coh2"], 1e-9)
            ok = r["coh2"] >= 0.10 and ratio >= 5.0
            print("      %-8s %11.0f %9.3f %9.4f %9.1f   %s"
                  % (bn, r["re_over_sxx"], r["coh2"], s["coh2"], ratio,
                     "PASS" if ok else "FAIL the trust gate"))
            OUT["p4"].setdefault(rt, {})[bn] = dict(re_z=float(r["re_over_sxx"]),
                                                    coh2=float(r["coh2"]),
                                                    shuf=float(s["coh2"]), ratio=float(ratio),
                                                    trust=bool(ok))


PARTS = dict(p1=p1, p2=p2, p3=p3, p4=p4)

if __name__ == "__main__":
    for k in (sys.argv[1:] or list(PARTS)):
        PARTS[k]()
    Path(__file__).with_name("_scratch/out/_v103_endpoint_power.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_v103_endpoint_power.json")
