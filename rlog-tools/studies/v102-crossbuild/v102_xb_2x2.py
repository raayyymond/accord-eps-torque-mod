#!/usr/bin/env python3
r"""THE 2x2 -- breaking the gain / Lever-B confound with route 71 (V87), and the PLACEBO FLOOR.

                     Lever B ARMED          Lever B REMOVED
    4x gain          V100  route 85         V87   route 71     <- 71 vs 85 ISOLATES LEVER B
    8x gain          (never flown)          V101  route 95     <- 95 vs 71 ISOLATES THE 8x GAIN

🛑 `_scratch/cache/r71/` EXISTS -- at the REPO ROOT, not under `analysis-2020accord/`.  23,765 rows at
   99.2 Hz with the full bus channel set (`tq`, `rate_c`, `cs_ang`, `imu_*`, `cc_lat`, `e4tq`,
   `ws_*`).  No re-extraction was needed.  (`_scratch/cache/ratio/00000071.npz` at 14.6 Hz is the useless
   one; it is not touched here.)

🛑 ROUTE 71 IS A CREEP DRIVE.  Per-segment v_max is 15/14/21 km/h and segment 0 is parked.  The
   ONLY speed band shared with routes 85 and 95 is ~5-15 km/h.  Every 2x2 number below is therefore
   a CREEP number and must be labelled as one.

🛑 BUS CHANNELS ONLY.  V87's CAN 427 carries gp-0x6b98 (`sar 3`, and it SATURATES at 1023 on 3.23 %
   of frames); V100/V101's carries gp-0x6b94 (`sar 6`).  Different cell, different scale, and one
   of them clips.  `x6b94`/`mag427` are excluded from every cross-build statistic here.

🛑 PLACEBO FIRST.  r75 and r76 are two drives on V89 -- BYTE-IDENTICAL FIRMWARE.  Their ratio is
   the resolution floor.  Any V101-vs-V87 ratio inside that floor is not a result.
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
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
CH = ("tq", "rate_c", "cs_ang", "imu_lat", "imu_vert")
BN = ("6-9", "18-22", "22-26", "26-31", "32-38", "40-49")


def hdr(s):
    print("\n" + "=" * 106)
    print(s)
    print("=" * 106)


CACHE = {}


def win_of(route, vlo, vhi):
    key = (route, vlo, vhi)
    if key not in CACHE:
        if route not in CACHE:
            CACHE[route] = L.windows(route, NFFT, HOP, engaged=True)
        CACHE[key] = L.sel(CACHE[route], vlo=vlo, vhi=vhi)
    return CACHE[key]


def cells(rA, rB, vlo, vhi, vbins=None):
    out = []
    for vb in (vbins or [(vlo, vhi)]):
        for rlo, rhi in RB:
            a = L.sel(win_of(rA, vb[0], vb[1]), rlo=rlo, rhi=rhi)
            b = L.sel(win_of(rB, vb[0], vb[1]), rlo=rlo, rhi=rhi)
            if len(a) >= 5 and len(b) >= 5:
                out.append((a, b))
    return out


def ratio(pack, key, nboot=3000, seed=1):
    """B/A, min(n)-weighted mean of per-cell log ratios, 15 s blocks resampled inside cells."""
    rng = np.random.default_rng(seed)
    P = []
    for a, b in pack:
        ga, gb = {}, {}
        for r in a:
            v = r.get(key, np.nan)
            if np.isfinite(v) and v > 0:
                ga.setdefault((r["seg"], int(r["t0"] // 15.0)), []).append(v)
        for r in b:
            v = r.get(key, np.nan)
            if np.isfinite(v) and v > 0:
                gb.setdefault((r["seg"], int(r["t0"] // 15.0)), []).append(v)
        if len(ga) >= 2 and len(gb) >= 2:
            P.append(([np.array(v) for v in ga.values()], [np.array(v) for v in gb.values()]))
    if not P:
        return None

    def stat(Q):
        num = den = 0.0
        for A, B in Q:
            va, vb = np.concatenate(A), np.concatenate(B)
            w = min(len(va), len(vb))
            num += w * np.log(np.median(vb) / np.median(va))
            den += w
        return float(np.exp(num / den)) if den else np.nan
    pt = stat(P)
    out = [stat([([A[j] for j in rng.integers(0, len(A), len(A))],
                  [B[j] for j in rng.integers(0, len(B), len(B))]) for A, B in P])
           for _ in range(nboot)]
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(r=pt, lo=float(lo), hi=float(hi), cells=len(P),
                nA=sum(len(a) for a, _ in pack), nB=sum(len(b) for _, b in pack))


def table(pack, title, floor=None):
    print("\n  " + title)
    print("   %-9s %s" % ("channel", "  ".join("%17s" % b for b in BN)))
    for ch in CH:
        row = []
        for bn in BN:
            res = ratio(pack, ch + "|" + bn, seed=hash((ch, bn)) % 9999)
            if res is None:
                row.append("%17s" % "-")
                continue
            mark = ""
            if floor is not None:
                fl = floor.get(bn)
                if fl and (res["r"] > fl or res["r"] < 1.0 / fl):
                    mark = "*"
            row.append("%7.2f[%4.2f,%5.2f]%s" % (res["r"], res["lo"], res["hi"], mark))
        print("   %-9s %s" % (ch, "  ".join(row)))


# =====================================================================================================
hdr("EXPOSURE -- what each route actually offers, engaged")
for route in ("71", "85", "95", "75", "76"):
    R = L.ROUTES[route]
    w = win_of(route, 0, 200)
    v = np.array([r["v"] for r in w]) if w else np.array([np.nan])
    print("   r%-3s %-5s  gain %4d  LeverB %-5s  segs %2d  win %4d  v p5/p50/p95 = %5.1f /%5.1f /%5.1f km/h"
          % (route, R["build"], R["gain"], R["leverB"], len(R["segs"]), len(w),
             *np.percentile(v, [5, 50, 95])))
print("""
   Route 71 (V87) tops out around 21 km/h.  The shared band with 85 and 95 is 5-15 km/h ONLY.""")

# =====================================================================================================
hdr("STEP 1 -- THE PLACEBO FLOOR.  r75 vs r76 = two drives on V89, BYTE-IDENTICAL FIRMWARE.")
VB_FULL = [(5, 20), (20, 35), (35, 50), (50, 65), (65, 90)]
pl = cells("75", "76", 0, 0, vbins=VB_FULL)
print("   matched cells: %d   r75 win=%d  r76 win=%d"
      % (len(pl), sum(len(a) for a, _ in pl), sum(len(b) for _, b in pl)))
FLOOR = {}
print("\n   %-9s %s" % ("channel", "  ".join("%17s" % b for b in BN)))
for ch in CH:
    row = []
    for bn in BN:
        res = ratio(pl, ch + "|" + bn, seed=hash((ch, bn, "pl")) % 9999)
        if res is None:
            row.append("%17s" % "-")
            continue
        row.append("%7.2f[%4.2f,%5.2f]" % (res["r"], res["lo"], res["hi"]))
        FLOOR[bn] = max(FLOOR.get(bn, 1.0), max(res["r"], 1.0 / res["r"]),
                        max(res["hi"], 1.0 / max(res["lo"], 1e-9)))
    print("   %-9s %s" % (ch, "  ".join(row)))
print("\n   RESOLUTION FLOOR per band (worst |log ratio| over the 5 channels, CI edges included):")
print("      " + "   ".join("%s: %.2fx" % (b, FLOOR.get(b, float("nan"))) for b in BN))
print("   A cross-build ratio must EXCEED its band's floor to count.  '*' marks that below.")

# also the placebo restricted to creep, since the 2x2 is a creep comparison
pl_creep = cells("75", "76", 5, 15)
print("\n   PLACEBO RESTRICTED TO 5-15 km/h (the 2x2's own regime), cells=%d:" % len(pl_creep))
FLOOR_C = {}
for ch in ("tq", "rate_c"):
    row = []
    for bn in BN:
        res = ratio(pl_creep, ch + "|" + bn, seed=hash((ch, bn, "plc")) % 9999)
        if res is None:
            row.append("%17s" % "-")
            continue
        row.append("%7.2f[%4.2f,%5.2f]" % (res["r"], res["lo"], res["hi"]))
        FLOOR_C[bn] = max(FLOOR_C.get(bn, 1.0), max(res["hi"], 1.0 / max(res["lo"], 1e-9)))
    print("   %-9s %s" % (ch, "  ".join(row)))
print("      creep floor: " + "   ".join("%s: %.2fx" % (b, FLOOR_C.get(b, float("nan"))) for b in BN))

# =====================================================================================================
hdr("STEP 2 -- THE 2x2, ALL AT 5-15 km/h (the only band route 71 reaches)")
p_gain = cells("71", "95", 5, 15)      # V87 -> V101 : ONLY the 8x gain changes (both Lever B OUT)
p_lever = cells("85", "71", 5, 15)     # V100 -> V87 : ONLY Lever B changes (both 4x)
p_conf = cells("85", "95", 5, 15)      # V100 -> V101: the CONFOUNDED contrast
for pack, ttl in ((p_gain, "A) V101 / V87   -- ISOLATES THE 8x GAIN (Lever B out on both)"),
                  (p_lever, "B) V87 / V100   -- ISOLATES LEVER B REMOVAL (4x on both)"),
                  (p_conf, "C) V101 / V100  -- the CONFOUNDED contrast, for reference")):
    print("\n   cells=%d" % len(pack))
    table(pack, ttl, floor=FLOOR_C or FLOOR)

# =====================================================================================================
hdr("STEP 3 -- WHERE THE 20-28 Hz PEAK SITS ON EACH OF THE THREE BUILDS, at 5-15 km/h")
win = np.hanning(NFFT)
print("   %-6s %-6s %-16s %22s %22s" % ("route", "build", "Lever B", "tq peak 20-28", "rate_c peak 20-28"))
for route, lab in (("85", "V100 4x  ARMED"), ("71", "V87  4x  REMOVED"), ("95", "V101 8x  REMOVED")):
    recs = L.sel(L.windows(route, NFFT, HOP, engaged=True, keep_raw=True), vlo=5, vhi=15)
    if len(recs) < 8:
        print("   r%-5s %-6s %-16s   (only %d windows)" % (route, L.ROUTES[route]["build"], lab, len(recs)))
        continue
    cells_ = []
    for ch in ("tq", "rate_c"):
        P = [L.psd(r["_blk"][ch][r["_sl"]], L.FS, win)[1] for r in recs]
        f = L.psd(recs[0]["_blk"][ch][recs[0]["_sl"]], L.FS, win)[0]
        pm = np.median(np.asarray(P), axis=0)
        m = (f >= 20) & (f <= 28)
        i = int(np.argmax(pm[m]))
        fpk = f[m][i]
        loc = (f >= fpk - 2.5) & (f <= fpk + 2.5)
        cells_.append("%6.2f Hz  prom %5.2f" % (fpk, pm[m][i] / np.median(pm[loc])))
    print("   r%-5s %-6s %-16s %22s %22s   (n=%d)"
          % (route, L.ROUTES[route]["build"], lab, cells_[0], cells_[1], len(recs)))

print("\n[done]")
