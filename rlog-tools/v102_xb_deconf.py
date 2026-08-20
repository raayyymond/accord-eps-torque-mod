#!/usr/bin/env python3
r"""DE-CONFOUNDING THE 2x2, DONE IN SHAPE UNITS -- and the placebo floor for the shape statistic.

Why shape and not raw band RMS: the V90-vs-V91 pair came out at 0.70/0.57/0.73 at 22-26 Hz, but its
32-38 Hz CONTROL band came out at 0.74/0.70/0.89 -- i.e. V91's whole spectrum sits ~0.7-0.9x below
V90's.  That is drive-to-drive level, exactly what the r75-vs-r76 placebo says is normal (its raw
ratios run 0.62-1.06 with nothing changed at all).  The SHAPE ratio (band / 32-38) divides it out.
Every number in this file is a shape ratio, including the floor, so they are commensurable.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
VB_FULL = [(5, 20), (20, 35), (35, 50), (50, 65), (65, 90)]
VB_CREEP = [(5, 15)]
CH3 = ("tq", "rate_c", "cs_ang")
BN = ("6-9", "18-22", "22-26", "26-31", "40-49")
CTRL = "32-38"

W = {}


def wins(route):
    if route not in W:
        w = L.windows(route, NFFT, HOP, engaged=True)
        for x in w:
            x["arm"] = route
            for ch in ("tq", "rate_c", "cs_ang", "imu_lat", "imu_vert"):
                c = x.get(ch + "|" + CTRL, np.nan)
                if np.isfinite(c) and c > 0:
                    for bn in L.BANDS:
                        v = x.get(ch + "|" + bn, np.nan)
                        if np.isfinite(v):
                            x["s:" + ch + "|" + bn] = v / c
        W[route] = w
    return W[route]


def cells(A, B, vbins):
    out = []
    for vlo, vhi in vbins:
        for rlo, rhi in RB:
            a = L.sel(L.sel(A, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
            b = L.sel(L.sel(B, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
            if len(a) >= 5 and len(b) >= 5:
                out.append((a, b))
    return out


def ratio(pack, key, nboot=4000, seed=1):
    rng = np.random.default_rng(seed)
    P = []
    for a, b in pack:
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


def block(name, pack, floor=None):
    print("\n  %s   (cells=%d, nA=%d, nB=%d)"
          % (name, len(pack), sum(len(a) for a, _ in pack), sum(len(b) for _, b in pack)))
    print("   %-9s %s" % ("channel", "  ".join("%17s" % b for b in BN)))
    got = {}
    for ch in CH3:
        row = []
        for bn in BN:
            res = ratio(pack, "s:" + ch + "|" + bn, seed=abs(hash((ch, bn, name))) % 9999)
            if res is None:
                row.append("%17s" % "-")
                continue
            got[(ch, bn)] = res
            mk = ""
            if floor and floor.get(bn) and (res["r"] > floor[bn] or res["r"] < 1 / floor[bn]):
                mk = "*"
            row.append("%7.2f[%4.2f,%5.2f]%s" % (res["r"], res["lo"], res["hi"], mk))
        print("   %-9s %s" % (ch, "  ".join(row)))
    return got


print("=" * 106)
print("PLACEBO SHAPE FLOOR -- r75 vs r76, BOTH V89, byte-identical firmware")
print("=" * 106)
pl = cells(wins("75"), wins("76"), VB_FULL)
g = block("V89 / V89", pl)
FLOOR = {}
for bn in BN:
    vals = [g[(ch, bn)] for ch in CH3 if (ch, bn) in g]
    FLOOR[bn] = max(max(v["hi"], 1 / max(v["lo"], 1e-9)) for v in vals)
print("\n   SHAPE FLOOR: " + "   ".join("%s %.2fx" % (b, FLOOR[b]) for b in BN))
print("   (compare with the RAW-band floor 6-9 1.82 / 18-22 1.79 / 22-26 2.18 / 26-31 2.42 --")
print("    the shape statistic is roughly TWICE as sensitive because it divides out drive level.)")

print("\n" + "=" * 106)
print("k -- `0xCBE74` STOCK -> x1.5, single variable, V90 (r77) vs V91 (r78)")
print("=" * 106)
gk = block("V91 / V90  == k", cells(wins("77"), wins("78"), VB_FULL), floor=FLOOR)

print("\n" + "=" * 106)
print("THE 2x2 IN SHAPE UNITS, 5-15 km/h (route 71 is a creep drive)")
print("=" * 106)
gA = block("A) V101 / V87   = G * k    (isolates the 8x gain)",
           cells(wins("71"), wins("95"), VB_CREEP), floor=FLOOR)
gB = block("B) V87 / V100   = B / k    (isolates Lever B)",
           cells(wins("85"), wins("71"), VB_CREEP), floor=FLOOR)
gC = block("C) V101 / V100  = G * B    (the confounded contrast)",
           cells(wins("85"), wins("95"), VB_CREEP), floor=FLOOR)

print("\n" + "=" * 106)
print("DECOMPOSITION at 22-26 Hz, in shape units")
print("=" * 106)
print("   %-9s %9s %9s %9s %9s | %9s %9s %7s" %
      ("channel", "A=G*k", "B=B/k", "C=G*B", "k", "G true", "B true", "gain %"))
for ch in CH3:
    A = gA.get((ch, "22-26"))
    Bv = gB.get((ch, "22-26"))
    C = gC.get((ch, "22-26"))
    K = gk.get((ch, "22-26"))
    if not all((A, Bv, C, K)):
        continue
    G = A["r"] / K["r"]
    Bt = Bv["r"] * K["r"]
    pct = 100.0 * np.log(G) / np.log(max(G * Bt, 1.0001))
    print("   %-9s %9.2f %9.2f %9.2f %9.2f | %9.2f %9.2f %6.1f %%"
          % (ch, A["r"], Bv["r"], C["r"], K["r"], G, Bt, pct))
print("""
   Consistency check: A x B should reproduce C, since k cancels in the product.
   Sensitivity of the split to k, on `tq`:""")
A = gA.get(("tq", "22-26"))
Bv = gB.get(("tq", "22-26"))
K = gk.get(("tq", "22-26"))
if A and Bv and K:
    for lab, kv in (("k = 1.00 (uncorrected)", 1.0), ("k = %.2f (point)" % K["r"], K["r"]),
                    ("k = %.2f (CI low)" % K["lo"], K["lo"]), ("k = %.2f (CI high)" % K["hi"], K["hi"])):
        G = A["r"] / kv
        Bt = Bv["r"] * kv
        print("      %-26s  G = %5.2f x   LeverB = %5.2f x   gain carries %5.1f %%"
              % (lab, G, Bt, 100.0 * np.log(G) / np.log(max(G * Bt, 1.0001))))

print("\n[done]")
