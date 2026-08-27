#!/usr/bin/env python3
r"""TWO CLEAN SINGLE-VARIABLE PAIRS -- and the de-confounding of the V101 2x2.

Cell lineage (orchestrator, byte-read from all 14 images):
    build   0xCBE74 m26   LeverB 0xC6446   0xC6CD0   0xC40D2   route
    V88     STOCK         FB / 5244        3564      102       73
    V89     STOCK         FB / 5244        3564      204       75, 76
    V90     STOCK         FB / 5244        3564      204       77
    V91     x1.5          FB / 5244        3564      204       78
    V87     STOCK         C5 /  512        3564      204       71
    V100    x1.5          FB / 5244        3564      204       85
    V101    x1.5          C5 /  512        7128      204       95

PAIR 1  V90 (r77) vs V91 (r78)  -> k, the effect of `0xCBE74` STOCK -> x1.5.  SINGLE VARIABLE.
PAIR 2  V88 (r73) vs V89 (r75+r76) -> the effect of `0xC40D2` 102 -> 204 (K1).  SINGLE VARIABLE.

WHY PAIR 1 MATTERS TO THE 2x2:  V87 carries `0xCBE74` at STOCK while V100/V101 carry x1.5, so
    V101/V87  = G * k       (measured 5.31)  =>  G = 5.31 / k
    V87/V100  = B / k       (measured 1.88)  =>  B = 1.88 * k
    V101/V100 = G * B       (measured 9.61)      -- k cancels ONLY in the product.
Neither arm is isolated until k is measured.

⚠ The caves differ within each pair (bus channels only here, so it does not enter), and each build's
  cave bits mean different things -- none are used.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
VB = [(5, 20), (20, 35), (35, 50), (50, 65), (65, 90)]
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
CH = ("tq", "rate_c", "cs_ang", "imu_lat", "imu_vert")
BN = ("6-9", "18-22", "22-26", "26-31", "32-38", "40-49")
CTRL = "32-38"


def hdr(s):
    print("\n" + "=" * 106)
    print(s)
    print("=" * 106)


WIN = {}


def wins(routes):
    key = tuple(routes)
    if key not in WIN:
        out = []
        for r in routes:
            if r not in WIN:
                WIN[r] = L.windows(r, NFFT, HOP, engaged=True)
                for x in WIN[r]:
                    x["arm"] = r
                    c = x.get("tq|" + CTRL, np.nan)
                    for ch in CH:
                        cc = x.get(ch + "|" + CTRL, np.nan)
                        if np.isfinite(cc) and cc > 0:
                            for bn in L.BANDS:
                                v = x.get(ch + "|" + bn, np.nan)
                                if np.isfinite(v):
                                    x["shape:" + ch + "|" + bn] = v / cc
            out += WIN[r]
        WIN[key] = out
    return WIN[key]


def cells(A, B, vbins=VB):
    out = []
    for vlo, vhi in vbins:
        for rlo, rhi in RB:
            a = L.sel(L.sel(A, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
            b = L.sel(L.sel(B, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
            if len(a) >= 5 and len(b) >= 5:
                out.append(((vlo, vhi), (rlo, rhi), a, b))
    return out


def ratio(pack, key, nboot=3000, seed=1):
    rng = np.random.default_rng(seed)
    P = []
    for _, _, a, b in pack:
        ga, gb = {}, {}
        for r in a:
            v = r.get(key, np.nan)
            if np.isfinite(v) and v > 0:
                ga.setdefault((r["arm"], r["seg"], int(r["t0"] // 15.0)), []).append(v)
        for r in b:
            v = r.get(key, np.nan)
            if np.isfinite(v) and v > 0:
                gb.setdefault((r["arm"], r["seg"], int(r["t0"] // 15.0)), []).append(v)
        if len(ga) >= 2 and len(gb) >= 2:
            P.append(([np.array(v) for v in ga.values()], [np.array(v) for v in gb.values()]))
    if not P:
        return None

    def stat(Q):
        num = den = 0.0
        for A_, B_ in Q:
            va, vb = np.concatenate(A_), np.concatenate(B_)
            w = min(len(va), len(vb))
            num += w * np.log(np.median(vb) / np.median(va))
            den += w
        return float(np.exp(num / den)) if den else np.nan
    pt = stat(P)
    out = [stat([([A_[j] for j in rng.integers(0, len(A_), len(A_))],
                  [B_[j] for j in rng.integers(0, len(B_), len(B_))]) for A_, B_ in P])
           for _ in range(nboot)]
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(r=pt, lo=float(lo), hi=float(hi), cells=len(P))


def report(pack, title, floor=None):
    print("\n  %s" % title)
    print("   per-cell census (speed / rate / nA / nB):")
    for (vlo, vhi), (rlo, rhi), a, b in pack:
        print("      %-11s %-11s %4d / %-4d" % ("%d-%d km/h" % (vlo, vhi),
                                                "%d-%d deg/s" % (rlo, rhi), len(a), len(b)))
    print("\n   %-9s %s" % ("channel", "  ".join("%17s" % x for x in BN)))
    for ch in CH:
        row = []
        for bn in BN:
            res = ratio(pack, ch + "|" + bn, seed=abs(hash((ch, bn, title))) % 9999)
            if res is None:
                row.append("%17s" % "-")
                continue
            mk = ""
            if floor and floor.get(bn) and (res["r"] > floor[bn] or res["r"] < 1.0 / floor[bn]):
                mk = "*"
            row.append("%7.2f[%4.2f,%5.2f]%s" % (res["r"], res["lo"], res["hi"], mk))
        print("   %-9s %s" % (ch, "  ".join(row)))
    print("   %-9s SHAPE (band / %s):" % ("", CTRL))
    for ch in ("tq", "rate_c", "cs_ang"):
        row = []
        for bn in BN:
            res = ratio(pack, "shape:" + ch + "|" + bn, seed=abs(hash((ch, bn, title, "s"))) % 9999)
            row.append("%17s" % "-" if res is None
                       else "%7.2f[%4.2f,%5.2f] " % (res["r"], res["lo"], res["hi"]))
        print("   %-9s %s" % (ch, "  ".join(row)))


# =====================================================================================================
hdr("EXPOSURE -- engaged windows and the speed range each arm covers")
for r in ("73", "75", "76", "77", "78", "71", "85", "95"):
    w = wins([r])
    v = np.array([x["v"] for x in w])
    print("   r%-3s %-5s  win=%4d  v p5/p50/p95 = %5.1f /%6.1f /%6.1f km/h"
          % (r, L.ROUTES[r]["build"], len(w), *np.percentile(v, [5, 50, 95])))

# =====================================================================================================
hdr("PLACEBO FLOOR (re-run in this file so it is the same estimator): r75 vs r76, BOTH V89")
pl = cells(wins(["75"]), wins(["76"]))
FLOOR = {}
print("   cells=%d" % len(pl))
print("   %-9s %s" % ("channel", "  ".join("%17s" % x for x in BN)))
for ch in CH:
    row = []
    for bn in BN:
        res = ratio(pl, ch + "|" + bn, seed=abs(hash((ch, bn, "pl"))) % 9999)
        if res is None:
            row.append("%17s" % "-")
            continue
        row.append("%7.2f[%4.2f,%5.2f]" % (res["r"], res["lo"], res["hi"]))
        FLOOR[bn] = max(FLOOR.get(bn, 1.0), max(res["hi"], 1.0 / max(res["lo"], 1e-9)))
    print("   %-9s %s" % (ch, "  ".join(row)))
print("\n   FLOOR: " + "   ".join("%s %.2fx" % (b, FLOOR[b]) for b in BN))

# =====================================================================================================
hdr("PAIR 1 -- V90 (r77) vs V91 (r78).  `0xCBE74` m26 STOCK -> x1.5.  SINGLE VARIABLE.  == k")
p1 = cells(wins(["77"]), wins(["78"]))
report(p1, "V91 / V90  (the ratio IS k)", floor=FLOOR)
k = {}
for bn in BN:
    kk = {ch: ratio(p1, ch + "|" + bn, seed=abs(hash((ch, bn, "k"))) % 9999) for ch in
          ("tq", "rate_c", "cs_ang")}
    k[bn] = kk
r22 = [k["22-26"][ch] for ch in ("tq", "rate_c", "cs_ang")]
kmid = float(np.exp(np.mean([np.log(x["r"]) for x in r22])))
klo = min(x["lo"] for x in r22)
khi = max(x["hi"] for x in r22)
print("""
   k at 22-26 Hz, geometric mean over the three steering channels = %.2f x  (channel range [%.2f, %.2f])
   FLOOR at 22-26 is %.2f x.""" % (kmid, klo, khi, FLOOR["22-26"]))

# =====================================================================================================
hdr("DE-CONFOUNDING THE V101 2x2 WITH THE MEASURED k")
print("""   V101/V87 = G * k = 5.31   ;   V87/V100 = B / k = 1.88   ;   V101/V100 = G * B = 9.61
   (all three from `studies/v102-crossbuild/v102_xb_2x2.py`, `tq` 22-26 Hz, 5-15 km/h matched cells)""")
for lab, kv in (("k = 1.00 (the uncorrected 2x2)", 1.0),
                ("k = %.2f (MEASURED, this file)" % kmid, kmid),
                ("k = %.2f (channel low)" % klo, klo),
                ("k = %.2f (channel high)" % khi, khi)):
    G = 5.31 / kv
    B = 1.88 * kv
    sh = np.log(G) / np.log(G * B) * 100.0
    print("   %-34s  true GAIN = %5.2f x   true LEVER B = %5.2f x   gain carries %4.1f %% of the log excess"
          % (lab, G, B, sh))

# =====================================================================================================
hdr("PAIR 2 -- V88 (r73) vs V89 (r75+r76).  `0xC40D2` 102 -> 204 (K1).  SINGLE VARIABLE.")
p2 = cells(wins(["73"]), wins(["75", "76"]))
report(p2, "V89 / V88  (the ratio IS the K1 doubling's effect)", floor=FLOOR)
print("""
   🛑 The pre-registered endpoints for this cell are 6-9 Hz (the micro-ratchet band the V102 power
   calculation failed on) and 22-26 Hz (never scored on this cell).  Read those two columns against
   the FLOOR line above; `imu_vert` is the channel control and should not move.""")

print("\n[done]")
