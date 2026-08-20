#!/usr/bin/env python3
r"""THE ~23 Hz V101 LINE.  Found by `v102_xb_spectra.py` #3b: the V101/V100 amplitude ratio is a
roughly FLAT 2.0-2.6x from 4 to 49 Hz -- except 22-26 Hz, where it is 7.2-7.9x in BOTH the column
torque and the wheel-rate channel.  This file decides whether that is a real new mode.

Tests, in order:
  T1  Is it band-specific?  22-26 against the 32-38 negative control, block-bootstrapped.
  T2  Is it in EVERY matched cell, or one?  per-cell ratio + within-route prominence.
  T3  Is its FREQUENCY fixed?  (a wheel order moves with speed; a mode does not)
  T4  Does it appear on channels that do NOT share a decode path?  cs_ang, imu_lat, wang.
  T5  Was it ALREADY there at 4x, just smaller?  within-V100 prominence over its own floor.
  T6  Aliasing sanity: 0x1AB is 41.7 Hz, so a 23 Hz component in the firmware lane folds to
      ~18.7 Hz.  Check `x6b94` at 18-20 Hz.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
VB = [(5, 20), (20, 35), (35, 50), (50, 65)]
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
CH2 = ("tq", "rate_c", "cs_ang", "imu_lat", "imu_vert")


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


W = {r: L.sel(L.windows(r, NFFT, HOP, engaged=True, keep_raw=True), vlo=5, vhi=65)
     for r in ("85", "95")}
CELLS = []
for vlo, vhi in VB:
    for rlo, rhi in RB:
        a = L.sel(W["85"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        b = L.sel(W["95"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        if len(a) >= 5 and len(b) >= 5:
            CELLS.append(((vlo, vhi), (rlo, rhi), a, b))
win = np.hanning(NFFT)
print("matched cells: %d" % len(CELLS))


def blkid(r):
    return (r["seg"], int(r["t0"] // 15.0))


def cell_ratio(key, nboot=3000, seed=101):
    """exp of the min(n)-weighted mean of per-cell log ratios; 15 s blocks resampled inside cells."""
    rng = np.random.default_rng(seed)
    pack = []
    for _, _, a, b in CELLS:
        ga, gb = {}, {}
        for r in a:
            v = r.get(key, np.nan)
            if np.isfinite(v):
                ga.setdefault(blkid(r), []).append(v)
        for r in b:
            v = r.get(key, np.nan)
            if np.isfinite(v):
                gb.setdefault(blkid(r), []).append(v)
        if len(ga) >= 2 and len(gb) >= 2:
            pack.append(([np.array(v) for v in ga.values()], [np.array(v) for v in gb.values()]))

    def stat(P):
        num = den = 0.0
        for A, B in P:
            va, vb = np.concatenate(A), np.concatenate(B)
            w = min(len(va), len(vb))
            num += w * np.log(np.median(vb) / np.median(va))
            den += w
        return float(np.exp(num / den)) if den else np.nan
    pt = stat(pack)
    out = []
    for _ in range(nboot):
        P = [([A[j] for j in rng.integers(0, len(A), len(A))],
              [B[j] for j in rng.integers(0, len(B), len(B))]) for A, B in pack]
        out.append(stat(P))
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(ratio=pt, lo=float(lo), hi=float(hi), cells=len(pack))


# =====================================================================================================
hdr("T1 -- IS THE 22-26 Hz RISE BAND-SPECIFIC?  vs the pre-declared 32-38 Hz negative control")
for r_ in list(W["85"]) + list(W["95"]):
    c = r_.get("tq|32-38", np.nan)
    for ch in CH2:
        cc = r_.get(ch + "|32-38", np.nan)
        for bn in L.BANDS:
            v = r_.get(ch + "|" + bn, np.nan)
            if np.isfinite(v) and np.isfinite(cc) and cc > 0:
                r_["shape:" + ch + "|" + bn] = v / cc
print("   %-14s %26s %26s" % ("channel", "V101/V100 band RMS", "V101/V100 SHAPE (band/32-38)"))
for ch in CH2:
    for bn in ("18-22", "22-26", "26-31", "32-38"):
        a = cell_ratio(ch + "|" + bn)
        b = cell_ratio("shape:" + ch + "|" + bn, seed=103)
        star = " ***" if bn == "22-26" else ""
        print("   %-8s %-6s %8.2f x [%5.2f,%5.2f] %10.2f x [%5.2f,%5.2f]%s"
              % (ch, bn, a["ratio"], a["lo"], a["hi"], b["ratio"], b["lo"], b["hi"], star))

# =====================================================================================================
hdr("T2 -- IS IT IN EVERY MATCHED CELL?  per-cell 22-26 Hz ratio, and 32-38 alongside")
print("   %-11s %-10s %14s %14s %14s" % ("speed", "rate", "tq 22-26", "tq 32-38", "rate_c 22-26"))
for (vlo, vhi), (rlo, rhi), a, b in CELLS:
    out = []
    for k in ("tq|22-26", "tq|32-38", "rate_c|22-26"):
        va = np.median([r[k] for r in a if k in r])
        vb = np.median([r[k] for r in b if k in r])
        out.append("%14.2f" % (vb / va))
    print("   %-11s %-10s %s" % ("%d-%d km/h" % (vlo, vhi), "%d-%d d/s" % (rlo, rhi), "".join(out)))

# =====================================================================================================
hdr("T3 -- IS ITS FREQUENCY FIXED?  peak location inside 20-28 Hz, per cell, per build")


def medspec(recs, ch):
    P = [L.psd(r["_blk"][ch][r["_sl"]], L.FS, win)[1] for r in recs]
    f = L.psd(recs[0]["_blk"][ch][recs[0]["_sl"]], L.FS, win)[0]
    return f, np.median(np.asarray(P), axis=0)


print("   %-11s %-10s %6s %22s %22s" % ("speed", "rate", "v m/s", "V100 peak(20-28)", "V101 peak(20-28)"))
for (vlo, vhi), (rlo, rhi), a, b in CELLS:
    v = np.median([r["v"] for r in a] + [r["v"] for r in b]) / 3.6
    cells = []
    for recs in (a, b):
        f, p = medspec(recs, "tq")
        m = (f >= 20) & (f <= 28)
        i = int(np.argmax(p[m]))
        fpk = f[m][i]
        loc = (f >= fpk - 2) & (f <= fpk + 2)
        cells.append("%8.1f Hz  prom %5.2f" % (fpk, p[m][i] / np.median(p[loc])))
    print("   %-11s %-10s %6.1f %22s %22s"
          % ("%d-%d km/h" % (vlo, vhi), "%d-%d d/s" % (rlo, rhi), v, cells[0], cells[1]))
print("""
   Wheel order 1 = 0.489*v Hz spans 1.0-7.8 Hz over these cells and order 2 spans 1.9-15.6 Hz, so
   NOTHING at 22-26 Hz can be a wheel order at these speeds.  Order 3 reaches 23.5 Hz only at the
   50-65 km/h cells; it is 3-6 Hz at the 5-20 km/h cells, where the line is also present.""")

# =====================================================================================================
hdr("T5 -- WAS IT ALREADY THERE AT 4x?  prominence of the 20-28 Hz peak WITHIN each build")
print("   (T3's prominence column read against each build's own local floor -- see above.)")

# =====================================================================================================
hdr("T6 -- ALIASING SANITY.  0x1AB samples gp-0x6b94 at 41.7 Hz => a 23 Hz component folds to 18.7 Hz")
for bn in ("15-22",):
    a = cell_ratio("x6b94|" + bn, seed=107)
    print("   x6b94 %-6s V101/V100 = %.2f x [%.2f, %.2f]   (x6b94's own Nyquist is 20.8 Hz;"
          " a true 23 Hz line in the FIRMWARE lane would appear here)"
          % (bn, a["ratio"], a["lo"], a["hi"]))
print("""
   x6b94 is the AGGREGATOR OUTPUT -- if the ~23 Hz line existed inside the firmware's own demand it
   would fold into 18-20 Hz here.  If this ratio matches the broadband ~2x and shows no excess, the
   line is NOT in the firmware's commanded torque: it is in the MECHANICAL response, i.e. the motor
   or the column, which is where a limit cycle would live.""")

print("\n[done]")
