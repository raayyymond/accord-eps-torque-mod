#!/usr/bin/env python3
r"""The ~23 Hz V101 line, part 2: LIMIT CYCLE or EXCITATION?  And is it in the FIRMWARE's own demand?

L1  Does the line scale with the LKAS command (excitation) or sit at a fixed amplitude (limit cycle)?
L2  Does applying DRIVER TORQUE kill it, as the operator reports?
L3  Is it inside the firmware's own aggregator output?  0x1AB samples gp-0x6b94 at 41.7 Hz, so a
    23 Hz component FOLDS to 41.7-23 = 18.7 Hz.  Look for it at 17-20 Hz in `x6b94`.
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
VB = [(5, 20), (20, 35), (35, 50), (50, 65)]
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
win = np.hanning(NFFT)


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


W = {r: L.sel(L.windows(r, NFFT, HOP, engaged=True, keep_raw=True), vlo=5, vhi=65)
     for r in ("85", "95")}
for route in ("85", "95"):
    for r in W[route]:
        blk, sl = r["_blk"], r["_sl"]
        r["e4rms"] = L.bandrms(blk["e4tq"][sl], L.FS, 0.3, 10.0, win)
        r["x6b94|17-20"] = L.bandrms(blk["x6b94"][sl], L.FS, 17.0, 20.0, win)
        r["x6b94|6-9"] = r.get("x6b94|6-9", np.nan)
CELLS = []
for vlo, vhi in VB:
    for rlo, rhi in RB:
        a = L.sel(W["85"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        b = L.sel(W["95"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        if len(a) >= 5 and len(b) >= 5:
            CELLS.append((a, b))
print("matched cells: %d" % len(CELLS))


def slope(idx, ykey, xkey, nboot=2000, seed=5):
    """Within-cell slope of log(y) on log(x), 15 s blocks resampled."""
    rng = np.random.default_rng(seed)
    pts = []
    for c in CELLS:
        recs = c[idx]
        x = np.log(np.array([r.get(xkey, np.nan) for r in recs]))
        y = np.log(np.array([r.get(ykey, np.nan) for r in recs]))
        m = np.isfinite(x) & np.isfinite(y) & (x > -20)
        if m.sum() < 6:
            continue
        xx, yy = x[m] - x[m].mean(), y[m] - y[m].mean()
        blk = np.array([int(r["t0"] // 15.0) for r, ok in zip(recs, m) if ok])
        pts.append((xx, yy, blk))
    if not pts:
        return dict(s=np.nan, lo=np.nan, hi=np.nan, n=0)

    def fit(sels):
        X = np.concatenate([p[0][s] for p, s in zip(pts, sels)])
        Y = np.concatenate([p[1][s] for p, s in zip(pts, sels)])
        return float(np.sum(X * Y) / np.sum(X * X)) if np.sum(X * X) > 0 else np.nan
    s0 = fit([np.ones(len(p[0]), bool) for p in pts])
    out = []
    for _ in range(nboot):
        sels = []
        for x, y, b in pts:
            u = np.unique(b)
            idxs = np.concatenate([np.nonzero(b == u[j])[0] for j in rng.integers(0, len(u), len(u))])
            s = np.zeros(len(x), bool)
            s[np.unique(idxs)] = True
            sels.append(s)
        out.append(fit(sels))
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(s=s0, lo=float(lo), hi=float(hi), n=sum(len(p[0]) for p in pts))


# =====================================================================================================
hdr("L1 -- DOES THE LINE SCALE WITH THE LKAS COMMAND?  slope of log(band RMS) on log(command RMS)")
print("   slope ~ +1 => LINEAR EXCITATION (the band is driven by the command).")
print("   slope ~  0 => a SELF-SUSTAINED oscillation whose size does not depend on the drive.")
print("   slope > +1 => super-linear, the loop is being pushed through a nonlinearity.")
for ch in ("tq", "rate_c"):
    print("\n  channel %s   (x = 0.3-10 Hz RMS of the 0x0E4 LKAS command)" % ch)
    for bn in ("6-9", "18-22", "22-26", "26-31", "32-38"):
        cells = []
        for idx, lbl in ((0, "V100 4x"), (1, "V101 8x")):
            g = slope(idx, ch + "|" + bn, "e4rms")
            cells.append("%s %+5.2f[%+5.2f,%+5.2f]" % (lbl, g["s"], g["lo"], g["hi"]))
        print("   %-7s %s" % (bn, "   ".join(cells)))

# =====================================================================================================
hdr("L2 -- DOES DRIVER TORQUE KILL IT?  slope of log(band RMS) on log|driver torque|")
print("   The operator: \"I can get it to go away, if I apply some torque to the steering wheel.\"")
for ch in ("tq", "rate_c"):
    print("\n  channel %s" % ch)
    for bn in ("6-9", "18-22", "22-26", "26-31", "32-38"):
        cells = []
        for idx, lbl in ((0, "V100 4x"), (1, "V101 8x")):
            g = slope(idx, ch + "|" + bn, "tqmed", seed=17)
            cells.append("%s %+5.2f[%+5.2f,%+5.2f]" % (lbl, g["s"], g["lo"], g["hi"]))
        print("   %-7s %s" % (bn, "   ".join(cells)))

# =====================================================================================================
hdr("L3 -- IS THE LINE INSIDE THE FIRMWARE'S OWN DEMAND?  x6b94 at 17-20 Hz (the 23 Hz fold)")


def cell_ratio(key, nboot=3000, seed=201):
    rng = np.random.default_rng(seed)
    pack = []
    for a, b in CELLS:
        ga, gb = {}, {}
        for r in a:
            v = r.get(key, np.nan)
            if np.isfinite(v):
                ga.setdefault((r["seg"], int(r["t0"] // 15.0)), []).append(v)
        for r in b:
            v = r.get(key, np.nan)
            if np.isfinite(v):
                gb.setdefault((r["seg"], int(r["t0"] // 15.0)), []).append(v)
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
    out = [stat([([A[j] for j in rng.integers(0, len(A), len(A))],
                  [B[j] for j in rng.integers(0, len(B), len(B))]) for A, B in pack])
           for _ in range(nboot)]
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return pt, float(lo), float(hi)


for k in ("x6b94|17-20", "x6b94|10-15", "x6b94|6-9", "x6b94|3-5"):
    p, lo, hi = cell_ratio(k)
    print("   %-14s V101/V100 = %5.2f x  [%5.2f, %5.2f]" % (k, p, lo, hi))
print("""
   17-20 Hz in `x6b94` is where a genuine 23 Hz component of the firmware's OWN aggregator output
   would fold (41.7 Hz sample rate).  If that ratio matches the other x6b94 bands (~1.3-1.5x, the
   dose) and shows no excess, the ~23 Hz line is NOT in the commanded torque -- it is in the
   MECHANICAL response of the column/motor, i.e. exactly where a limit cycle lives.""")

print("\n[done]")
