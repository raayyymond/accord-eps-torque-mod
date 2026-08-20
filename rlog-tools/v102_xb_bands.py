#!/usr/bin/env python3
r"""V100 (r85, 4x) vs V101 (r95, 8x): matched-speed band power, the dose test, and the spectra.

CONTROL BEFORE MEASUREMENT.  Nothing is quoted until (a) the within-route SPLIT-HALF null brackets
1.0 and (b) the LKAS-OFF matched pair is reported.  Bootstrap unit is the EPISODE, never the window.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128          # 2.56 s, 50 % overlap, df = 0.39 Hz
CACHE = L.AN / "_cache_r95" / "v102_xb_bands.json"

# speed bins both routes actually cover, engaged
VBINS = [(5, 15), (15, 25), (25, 35), (35, 45), (45, 65)]
RBINS = [("micro 1-13 deg/s", 1, 13), ("ratchet 13-50 deg/s", 13, 50), ("macro >50", 50, 1e9)]
TQBINS = [("light |tq|<400", 0, 400), ("mid 400-1200", 400, 1200), ("heavy >1200", 1200, 1e9)]
PRIMARY = ("tq", "rate_c", "imu_lat", "x6b94")


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


def line(lbl, res, extra=""):
    if not np.isfinite(res["ratio"]):
        print("   %-26s   n/a" % lbl)
        return
    print("   %-26s %6.3f x  [%5.3f, %5.3f]   epi %2d/%-2d  win %4d/%-4d %s"
          % (lbl, res["ratio"], res["lo"], res["hi"], res["nA"], res["nB"],
             res["wA"], res["wB"], extra))


print("building windows (uniform 100 Hz grid, gap-split, %d-sample Hann, hop %d)" % (NFFT, HOP))
W = {}
for route in ("85", "95"):
    W[(route, True)] = L.windows(route, NFFT, HOP, engaged=True)
    W[(route, False)] = L.windows(route, NFFT, HOP, engaged=False)
    print("   r%s  engaged win=%4d epi=%2d   manual win=%4d epi=%2d"
          % (route, len(W[(route, True)]), L.nepi(W[(route, True)]),
             len(W[(route, False)]), L.nepi(W[(route, False)])))

E85 = L.sel(W[("85", True)], vlo=5, vhi=65)
E95 = L.sel(W[("95", True)], vlo=5, vhi=65)

# =====================================================================================================
hdr("CONTROL 1 -- WITHIN-ROUTE SPLIT-HALF NULL.  Any band whose null does not bracket 1.0 is VOID.")
print("   split = alternate EPISODES (odd vs even), same route, same 5-65 km/h engaged selection")
for route, recs in (("85 V100", E85), ("95 V101", E95)):
    keys = sorted({(r["route"], r["seg"], r["epi"]) for r in recs})
    odd = {k for i, k in enumerate(keys) if i % 2}
    A = [r for r in recs if (r["route"], r["seg"], r["epi"]) in odd]
    B = [r for r in recs if (r["route"], r["seg"], r["epi"]) not in odd]
    print("  r%s   (%d vs %d episodes)" % (route, len(odd), len(keys) - len(odd)))
    for ch in PRIMARY:
        for bn in ("6-9", "18-22"):
            k = ch + "|" + bn
            if not any(k in r for r in A):
                continue
            line(ch + " " + bn, L.boot_ratio(A, B, k, nboot=2000, seed=7))

# =====================================================================================================
hdr("CONTROL 2 -- LKAS OFF, MATCHED PAIR.  Both routes only have manual exposure at 0-10 km/h.")
M85 = L.sel(W[("85", False)], vlo=0, vhi=10)
M95 = L.sel(W[("95", False)], vlo=0, vhi=10)
print("   r85 manual win=%d epi=%d   r95 manual win=%d epi=%d"
      % (len(M85), L.nepi(M85), len(M95), L.nepi(M95)))
print("   V101/V100, LKAS OFF -- the firmware LKAS lane is not running, so this must be ~1.0:")
for ch in PRIMARY:
    for bn in L.BANDS:
        k = ch + "|" + bn
        if not any(k in r for r in M85):
            continue
        line(ch + " " + bn, L.boot_ratio(M95, M85, k, nboot=2000, seed=11))

# =====================================================================================================
hdr("EXPOSURE CENSUS of the matched engaged selection (5-65 km/h) -- read this before any ratio")
print("   %-10s %8s %8s %8s %8s %8s %8s" % ("route", "win", "epi", "v p50", "rate p50", "|tq| p50", "|e4| p50"))
for lbl, recs in (("85 V100", E85), ("95 V101", E95)):
    print("   %-10s %8d %8d %8.1f %8.1f %8.0f %8.0f"
          % (lbl, len(recs), L.nepi(recs), np.median([r["v"] for r in recs]),
             np.median([r["rate"] for r in recs]), np.nan, np.median([r["e4"] for r in recs])))
print("\n   per speed bin (windows / episodes / median wheel rate deg/s):")
print("   %-12s %14s %14s" % ("bin", "V100 r85", "V101 r95"))
for lo, hi in VBINS:
    a, b = L.sel(E85, vlo=lo, vhi=hi), L.sel(E95, vlo=lo, vhi=hi)
    print("   %2d-%2d km/h   %5d/%-3d  %4.1f  %5d/%-3d  %4.1f"
          % (lo, hi, len(a), L.nepi(a), np.median([r["rate"] for r in a]) if a else np.nan,
             len(b), L.nepi(b), np.median([r["rate"] for r in b]) if b else np.nan))

# =====================================================================================================
hdr("MEASUREMENT 1 -- V101/V100 BAND RMS, ENGAGED, 5-65 km/h POOLED.  Dose expectation = 2.00x")
for ch in PRIMARY:
    print("  channel %s" % ch)
    for bn in L.BANDS:
        k = ch + "|" + bn
        if not any(k in r for r in E85):
            continue
        tag = "  <-- NEGATIVE CONTROL" if bn == L.NEGCTRL else ""
        line(bn, L.boot_ratio(E95, E85, k, nboot=4000, seed=3), tag)

# =====================================================================================================
hdr("MEASUREMENT 2 -- THE SAME, PER SPEED BIN.  'banded in speed' vs 'at all speeds'.")
for ch in PRIMARY:
    print("\n  channel %s" % ch)
    print("   %-12s %s" % ("bin", "  ".join("%14s" % b for b in ("6-9", "18-22", "26-31", "32-38*"))))
    for lo, hi in VBINS:
        a, b = L.sel(E85, vlo=lo, vhi=hi), L.sel(E95, vlo=lo, vhi=hi)
        cells = []
        for bn in ("6-9", "18-22", "26-31", "32-38"):
            k = ch + "|" + bn
            if not any(k in r for r in a) or len(a) < 6 or len(b) < 6:
                cells.append("%14s" % "-")
                continue
            r_ = L.boot_ratio(b, a, k, nboot=1500, seed=5)
            cells.append("%6.2f[%4.2f,%4.2f]" % (r_["ratio"], r_["lo"], r_["hi"]))
        print("   %2d-%2d km/h  %s" % (lo, hi, "  ".join(cells)))
print("\n   * 32-38 Hz is the PRE-DECLARED NEGATIVE CONTROL band.")

# =====================================================================================================
hdr("MEASUREMENT 3 -- MATCHED ON WHEEL RATE TOO (the ratchet's own axis), 5-65 km/h engaged")
for ch in PRIMARY:
    print("\n  channel %s" % ch)
    for rlbl, rlo, rhi in RBINS:
        cells = []
        a, b = L.sel(E85, rlo=rlo, rhi=rhi), L.sel(E95, rlo=rlo, rhi=rhi)
        for bn in ("6-9", "18-22", "26-31", "32-38"):
            k = ch + "|" + bn
            if not any(k in r for r in a) or len(a) < 6 or len(b) < 6:
                cells.append("%14s" % "-")
                continue
            r_ = L.boot_ratio(b, a, k, nboot=1500, seed=9)
            cells.append("%6.2f[%4.2f,%4.2f]" % (r_["ratio"], r_["lo"], r_["hi"]))
        print("   %-20s n=%4d/%-4d  %s" % (rlbl, len(b), len(a), "  ".join(cells)))

# =====================================================================================================
hdr("MEASUREMENT 4 -- MATCHED ON DRIVER TORQUE (the operator fought the wheel on V101)")
for ch in ("tq", "rate_c"):
    print("\n  channel %s" % ch)
    for tlbl, tlo, thi in TQBINS:
        def tq_sel(recs):
            return [r for r in recs if tlo <= r.get("tqmed", np.nan) < thi]
        cells = []
        a, b = tq_sel(E85), tq_sel(E95)
        for bn in ("6-9", "18-22", "26-31", "32-38"):
            k = ch + "|" + bn
            if len(a) < 6 or len(b) < 6:
                cells.append("%14s" % "-")
                continue
            r_ = L.boot_ratio(b, a, k, nboot=1500, seed=13)
            cells.append("%6.2f[%4.2f,%4.2f]" % (r_["ratio"], r_["lo"], r_["hi"]))
        print("   %-20s n=%4d/%-4d  %s" % (tlbl, len(b), len(a), "  ".join(cells)))

print("\n[done]")
