#!/usr/bin/env python3
"""Route `5d` -- DOES THE DAMPER MOVE 6-9 Hz AND 18-22 Hz THE SAME WAY, OR OPPOSITE WAYS?

The question is a SIGN question and a RATIO-OF-RATIOS question, so it must be estimated as one.
Comparing two independently-bootstrapped CIs and eyeballing the overlap is the wrong test: the two
bands are measured on the SAME windows, so a paired estimator cancels every route, exposure and
driver effect the two share, and is far better powered than either band alone.

    R = (V74/V73 effect on 6-9)  /  (V74/V73 effect on 18-22)
      R < 1  ⇒ the damper helps 6-9 MORE than 18-22   (the phase model predicts ~cos0.93/cos0.52
                                                        ≈ 1.8-2.0 in ATTENUATION, i.e. R ≈ 0.5-0.55)
      R ≈ 1  ⇒ both bands move together              (coupling, or a common cause)
      R « 1 with the 18-22 effect ABOVE 1 ⇒ the SIGN SPLIT: damping at 6-9, ANTI-damping at 21

TWO INDEPENDENT CONTRASTS, because each is confounded in a different way and they fail differently:
  1. THE LEVER CONTRAST, V74 vs V73. This is the real experiment: V73's damper was inert (0 of
     104,061 frames), V74's fires at 67.4% duty at engaged creep, and the rate lane is byte-identical
     between them. ⚠ V74 also carries LEVER D' (friction x1.5), so it is a two-lever contrast.
  2. THE WITHIN-ROUTE bit7 CONTRAST. Immune to route confounds, but 🛑 `bit7` is near-DETERMINISTIC
     in steering rate (damp fraction 0.00-0.07 at rate_lp 0-2 deg/s, 0.86-1.00 at 5-12), so it is
     reported with its own overlap census and only inside rate strata.

Both are additionally run on the CONTROL-NORMALISED bands `e_X / e_24-28`, which is the form in
which a broadband difference between two drives cancels out.

PART 3 asks the coupling question directly: partial r(6-9, 18-22 | 24-28) on this route against a
circular-shift null, and the lagged cross-correlation of the two envelopes -- does 18-22 FOLLOW 6-9?

Usage:  python studies/sessions/r5d/r5d_signsplit.py   ->  writes _scratch/out/_r5d_signsplit.json
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import _r5d_lib as L  # noqa: E402
import d6_events as D  # noqa: E402

G.EPKEY = "blk"
RNG = np.random.default_rng(19740609)
OUT = {}
NB = 3000
D.PARKED["V74/r5d"] = [2, 3, 9]
L.install_fs()

with open(ROOT / "_scratch/data/_cache_r5d_nearcentre.pkl", "rb") as fh:
    store = pickle.load(fh)


def prep(b, engaged=1):
    o = []
    for r in store[b]:
        if r["eng"] != engaged:
            continue
        if not (np.isfinite(r["e_24-28"]) and r["e_24-28"] > 0):
            continue
        if not all(np.isfinite(r[k]) for k in ("e_6-9", "e_18-22", "v")):
            continue
        q = dict(r)
        q["x_6-9"] = r["e_6-9"] / r["e_24-28"]
        q["x_18-22"] = r["e_18-22"] / r["e_24-28"]
        o.append(q)
    return o


KEYS = [("e_6-9", "6-9 Hz raw"), ("e_18-22", "18-22 Hz raw"), ("e_24-28", "24-28 control"),
        ("x_6-9", "6-9 / control"), ("x_18-22", "18-22 / control")]


def strat_pair(A, B, keys, cellfn, minn=5, nboot=NB):
    """Weighted log-ratio A/B for EVERY key on ONE bootstrap draw, so the keys are PAIRED.

    Returns {key: (point, lo, hi)} plus the draws matrix, so a ratio-of-ratios can be formed from
    the same resample rather than from two independent ones.
    """
    def est(a, b):
        ca, cb = {}, {}
        for r in a:
            ca.setdefault(cellfn(r), []).append(r)
        for r in b:
            cb.setdefault(cellfn(r), []).append(r)
        out = {}
        shared = sorted(set(ca) & set(cb), key=str)
        for k in keys:
            num = den = 0.0
            for c in shared:
                ra, rb = ca[c], cb[c]
                if len(ra) < minn or len(rb) < minn:
                    continue
                sa, sb = np.median(G.col(ra, k)), np.median(G.col(rb, k))
                if not (sa > 0 and sb > 0):
                    continue
                w = 1.0 / (1.0 / len(ra) + 1.0 / len(rb))
                num += w * np.log(sa / sb)
                den += w
            out[k] = num / den if den else np.nan
        ncell = sum(1 for c in shared if len(ca[c]) >= minn and len(cb[c]) >= minn)
        return out, ncell
    pt, nc = est(A, B)
    ea, eb = {}, {}
    for r in A:
        ea.setdefault(r["blk"], []).append(r)
    for r in B:
        eb.setdefault(r["blk"], []).append(r)
    ka, kb = list(ea), list(eb)
    draws = {k: np.full(nboot, np.nan) for k in keys}
    for i in range(nboot):
        a = [r for j in RNG.integers(0, len(ka), len(ka)) for r in ea[ka[j]]]
        b = [r for j in RNG.integers(0, len(kb), len(kb)) for r in eb[kb[j]]]
        d, _ = est(a, b)
        for k in keys:
            draws[k][i] = d[k]
    return pt, draws, nc


def show(pt, draws, nc, title, pairs):
    print(f"\n  {title}   ({nc} shared cells)")
    print(f"    {'band':<16} {'ratio':>7} {'95% CI':>18}   sign")
    for k, kl in KEYS:
        d = draws[k]
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        s = ("DOWN (attenuated)" if np.exp(hi) < 1 else
             "UP (worse)" if np.exp(lo) > 1 else "spans 1")
        print(f"    {kl:<16} {np.exp(pt[k]):>7.3f} [{np.exp(lo):>7.3f}, {np.exp(hi):>7.3f}]   {s}")
    for (ka, kb, lab) in pairs:
        d = draws[ka] - draws[kb]          # PAIRED, same resample
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        p = pt[ka] - pt[kb]
        sd = float(np.nanstd(d))
        mde = float(np.exp(2.80 * sd))
        print(f"    ⇒ {lab}: R = {np.exp(p):.3f} [{np.exp(lo):.3f}, {np.exp(hi):.3f}]   "
              f"MDE on R = {mde:.2f}x")
        print(f"       phase model predicts R ≈ 0.50-0.55 (cos0.93 vs cos0.52); "
              f"R ≈ 1 = bands move together; R < 1 with the 18-22 leg ABOVE 1 = the SIGN SPLIT")
        yield lab, float(np.exp(p)), float(np.exp(lo)), float(np.exp(hi)), mde


# ================================================== 1. THE LEVER CONTRAST =========================
N.hdr("1. ★★★ THE LEVER CONTRAST -- V74 (damper IN FORCE) vs V73 (damper INERT, 0/104,061 frames)")
print("  Engaged windows only. Cells = (speed x rate_lp x effort), so a speed or driver difference")
print("  between the two drives cannot produce the ratio. ⚠ V74 also carries LEVER D' (friction")
print("  x1.5), so this is a TWO-lever contrast, not a pure damper contrast.")
VB = [(0.0, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5), (12.5, 18.7), (18.7, 40.0)]
RB = [(0.0, 2.0), (2.0, 5.0), (5.0, 12.0), (12.0, 30.0), (30.0, 1e9)]
EB = [(0.0, 200.0), (200.0, 800.0), (800.0, 1e9)]


def cell3(r):
    return (G.binof(r["v"], VB), G.binof(r["rate_lp"], RB), G.binof(r["eff"], EB))


A, B = prep("V74/r5d"), prep("V73/r5a")
print(f"  V74 {len(A)} engaged windows / {len({r['blk'] for r in A})} blocks · "
      f"V73 {len(B)} / {len({r['blk'] for r in B})}")
pt, dr, nc = strat_pair(A, B, [k for k, _ in KEYS], cell3)
OUT["lever"] = {k: [float(np.exp(pt[k]))] + [float(np.exp(x)) for x in
                                             np.nanpercentile(dr[k], [2.5, 97.5])] for k, _ in KEYS}
OUT["lever_R"] = [t for t in show(pt, dr, nc, "V74 / V73, engaged, all speeds",
                                  [("x_6-9", "x_18-22", "R = (6-9 rel) / (18-22 rel)"),
                                   ("e_6-9", "e_18-22", "R = (6-9 raw) / (18-22 raw)")])]

# same thing against V72, whose damper was ALSO inert -- a replication with a different route
C = prep("V72/r59")
pt2, dr2, nc2 = strat_pair(A, C, [k for k, _ in KEYS], cell3)
OUT["lever_v72_R"] = [t for t in show(pt2, dr2, nc2, "V74 / V72 (V72's damper also inert)",
                                      [("x_6-9", "x_18-22", "R = (6-9 rel) / (18-22 rel)")])]

# ================================================== 2. THE bit7 CONTRAST ==========================
N.hdr("2. THE WITHIN-ROUTE bit7 CONTRAST -- damper ACTIVE vs damper IDLE, same drive")
print("  🛑 OVERLAP FIRST. bit7 is near-deterministic in steering rate, so most cells carry NO")
print("  contrast at all and the estimator silently drops them. The census says how many are left.\n")
eng = prep("V74/r5d")
q = np.percentile([r["rate_lp"] for r in eng], [20, 40, 60, 80])
print(f"  rate_lp quintile edges {np.round(q, 2)} deg/s")
for i in range(5):
    s = [r for r in eng if int(np.searchsorted(q, r["rate_lp"])) == i]
    f = np.mean([r["damp"] >= 0.5 for r in s]) if s else np.nan
    print(f"    quintile {i}: n={len(s):>4}  damp>=0.5 fraction {f:.2f}"
          + ("   <- usable overlap" if 0.15 <= f <= 0.85 else "   (no contrast)"))
hi = [r for r in eng if r["damp"] >= 0.5]
lo = [r for r in eng if r["damp"] < 0.5]


def rq(r):
    return int(np.searchsorted(q, r["rate_lp"]))


pt3, dr3, nc3 = strat_pair(hi, lo, [k for k, _ in KEYS], rq, minn=6)
OUT["bit7_R"] = [t for t in show(pt3, dr3, nc3,
                                 "damper ACTIVE / damper IDLE, rate-quintile stratified",
                                 [("x_6-9", "x_18-22", "R = (6-9 rel) / (18-22 rel)")])]
print("  ⚠ ratio > 1 here means MORE band energy when the damper is ACTIVE -- the opposite sign")
print("     convention to part 1, because this contrast is `active/idle`, not `treated/untreated`.")

# ================================================== 3. COUPLING ==================================
N.hdr("3. COUPLING -- partial r(6-9, 18-22 | 24-28), and does 18-22 FOLLOW 6-9?")


def partial_r(x, y, z):
    x, y, z = (np.log(np.asarray(a, float) + 1e-9) for a in (x, y, z))
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    x, y, z = x[m], y[m], z[m]
    if len(x) < 20:
        return np.nan
    rxy, rxz, ryz = (np.corrcoef(x, y)[0, 1], np.corrcoef(x, z)[0, 1], np.corrcoef(y, z)[0, 1])
    d = np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return float((rxy - rxz * ryz) / d) if d > 0 else np.nan


def by_run(rs):
    o = {}
    for r in rs:
        o.setdefault(r["ep"], []).append(r)
    for k in o:
        o[k].sort(key=lambda r: r["t0"])
    return o


for lab, rs in (("route 5d, ALL engaged", eng),
                ("route 5d, damper ACTIVE", hi),
                ("route 5d, damper IDLE", lo)):
    r_ = partial_r(G.col(rs, "e_6-9"), G.col(rs, "e_18-22"), G.col(rs, "e_24-28"))
    runs = by_run(rs)
    nulls = []
    for _ in range(400):
        xs, ys, zs = [], [], []
        for v in runs.values():
            if len(v) < 8:
                continue
            s = RNG.integers(2, len(v) - 1)
            xs += [w["e_6-9"] for w in v]
            ys += list(np.roll([w["e_18-22"] for w in v], s))
            zs += [w["e_24-28"] for w in v]
        nn = partial_r(xs, ys, zs)
        if np.isfinite(nn):
            nulls.append(nn)
    nlo, nhi = (np.nanpercentile(nulls, [2.5, 97.5]) if len(nulls) > 20 else (np.nan, np.nan))
    print(f"  {lab:<26} partial r = {r_:+.3f}   circular-shift null [{nlo:+.3f}, {nhi:+.3f}]   "
          f"{'CLEARS' if np.isfinite(nhi) and (r_ > nhi or r_ < nlo) else 'inside null'}")
    OUT.setdefault("partial_r", {})[lab] = dict(r=r_, null=[float(nlo), float(nhi)], n=len(rs))

print("\n  LAGGED CROSS-CORRELATION of the two ENVELOPES inside engaged runs (v < 12.5 m/s).")
print("  Positive lag = 18-22 Hz FOLLOWS 6-9 Hz. Null is a circular shift of the 18-22 envelope.\n")
lags = np.arange(-200, 201, 20)
acc = {int(k): [] for k in lags}
nullacc = {int(k): [] for k in lags}
for _, s, a, b, d, fs in D.runs("V74/r5d", 0.0, 12.5, True, 1024):
    x = np.asarray(d["tq"][a:b], float)
    e1 = np.abs(D.analytic(D.bp(x, fs, 5.0, 12.0)))
    e2 = np.abs(D.analytic(D.bp(x, fs, 18.0, 22.0)))
    e1 = (e1 - e1.mean()) / (e1.std() + 1e-9)
    e2 = (e2 - e2.mean()) / (e2.std() + 1e-9)
    sh = int(RNG.integers(len(e2) // 4, 3 * len(e2) // 4))
    e2s = np.roll(e2, sh)
    for k in lags:
        k = int(k)
        if k >= 0:
            v = float(np.mean(e1[:len(e1) - k] * e2[k:]))
            vn = float(np.mean(e1[:len(e1) - k] * e2s[k:]))
        else:
            v = float(np.mean(e1[-k:] * e2[:len(e2) + k]))
            vn = float(np.mean(e1[-k:] * e2s[:len(e2) + k]))
        acc[k].append(v)
        nullacc[k].append(vn)
print(f"    {'lag (ms)':>9} {'r':>8} {'null p95':>9}")
best = (None, -9)
for k in lags:
    k = int(k)
    if not acc[k]:
        continue
    m = float(np.median(acc[k]))
    n95 = float(np.percentile(np.abs(nullacc[k]), 95))
    if m > best[1]:
        best = (k, m)
    print(f"    {10 * k:>9d} {m:>8.3f} {n95:>9.3f}"
          + ("   <- above the shift null" if m > n95 else ""))
    OUT.setdefault("xcorr", {})[str(10 * k)] = dict(r=m, null95=n95, n=len(acc[k]))
print(f"\n    peak at lag {10 * best[0]:+d} ms, r = {best[1]:.3f}   "
      f"(0 ms = simultaneous ⇒ common excitation, not one driving the other)")

with open(ROOT / "_scratch/out/_r5d_signsplit.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5d_signsplit.json")
