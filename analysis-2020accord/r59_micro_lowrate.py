#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §8 IS THE MICRO-RATCHET A LOW-RATE FRICTION/NOTCHINESS, NOT A LINE?

D4-fixes-audit's second lead: V72's MANUAL creep median |bar torque| at |rate| 0-20 deg/s runs
1.48x V71C / 1.66x V71B -- a low-rate effort rise. V72's Lever B opened base-assist damping below
35 km/h for the first time (stock has EXACTLY ZERO base damping below 35 km/h), which is a mechanism
for exactly that. A notchy, inaudible, not-heavy roughness felt when turning the wheel slowly by
hand is a plausible "micro-ratcheting" that is NOT a spectral line and would be invisible to §1-§7.

🛑 THE BUILD-SPECIFIC BREAKPOINT TEST IS NOT RUNNABLE. Lever B is gated at 35 km/h = 9.72 m/s, so
V72 and only V72 should show a break there. But the MANUAL arm has 0.0-6.4 s of moving-wheel
exposure above 9.72 m/s on EVERY route in the corpus -- nobody drives hands-on with LKAS off at
speed. The clean falsifier is unavailable; that is a fact about the corpus, not a result.

WHAT IS RUNNABLE, in the manual moving-wheel creep cell where every build has 37-102 s:
  §1 THE EFFORT LEVEL, decomposed. Regressing |tq| on |rate| separates the two mechanisms:
     a SLOPE is viscous damping (torque proportional to rate); an INTERCEPT is friction/stiction.
     Only the intercept feels like ratcheting. D4's ratio alone cannot tell them apart.
  §2 THE ROUGHNESS, at matched rate. RMS of the 3-6 and 10-16 Hz components -- bands that exclude
     both known lines -- inside low-rate samples only.
  §3 THE NOTCH DENSITY. Reversals of the 3-30 Hz effort component per DEGREE of wheel travel. A
     ratchet is discrete catches per unit travel; this counts them without assuming a frequency.

Episode-clustered CIs throughout. Writes `_r59_lowrate.json`.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
import _r37_ratchet_lib as R37  # noqa: E402

RNG = np.random.default_rng(20260805)
CREEP = 4.0
RATE_LO, RATE_HI = 3.0, 20.0        # "moving slowly by hand" -- D4's own 0-20 deg/s window
OUT = {}
ROUTES = {"V59 r2c": ("_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
          "V62 r37": ("_cache_r37", "r37s", list(range(15)), []),
          "V67 r47": ("_cache_r47", "r47s", list(range(26)), []),
          "V69 r4f": ("_cache_r4f", "r4fs", list(range(8)), []),
          "V70 r50": ("_cache_r50", "r50s", [0, 1, 2], [0]),
          "V71B r54": ("_cache_r54", "r54s", list(range(21)), [10, 11]),
          "V71C r58": ("_cache_r58", "r58s", list(range(16)), [12, 13, 14, 15]),
          "V72 r59": ("_cache_r59", "r59s", list(range(15)), [12, 13, 14])}


def hdr(s):
    print("\n" + "=" * 120 + f"\n{s}\n" + "=" * 120)


def blocks(tag):
    """Contiguous manual moving-wheel creep RUNS -- the episode unit. One dict per run."""
    cache, pfx, segs, skip = ROUTES[tag]
    out = []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        rt = np.abs(np.asarray(d["rate_c"], float))
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        ang = np.asarray(d["ang"], float)
        b36 = R37.bandpass(tq, fs, 3, 6)
        b1016 = R37.bandpass(tq, fs, 10, 16)
        b330 = R37.bandpass(tq, fs, 3, 30)
        m = (~lat) & (v > 0.3) & (v < CREEP) & (rt >= RATE_LO) & (rt <= RATE_HI)
        for a, b in C.runs_of(m, np.asarray(d["t"], float), 25):
            w = slice(a, b)
            trav = float(np.abs(np.diff(ang[w])).sum())
            sg = np.signbit(b330[w])
            nrev = int((sg[:-1] != sg[1:]).sum())
            out.append(dict(tag=tag, seg=int(s), n=b - a, secs=(b - a) / fs,
                            tq=np.abs(tq[w]), rate=rt[w],
                            mtq=float(np.median(np.abs(tq[w]))),
                            mrate=float(np.median(rt[w])),
                            r36=float(np.sqrt(np.mean(b36[w] ** 2))),
                            r1016=float(np.sqrt(np.mean(b1016[w] ** 2))),
                            r330=float(np.sqrt(np.mean(b330[w] ** 2))),
                            trav=trav, nrev=nrev,
                            notch=(nrev / trav if trav > 1 else np.nan)))
    return out


ALL = {t: blocks(t) for t in ROUTES}


def epci(bl, key, nb=4000, w="secs"):
    """Exposure-weighted median of a per-block statistic, bootstrapped over BLOCKS."""
    if not bl:
        return np.nan, np.nan, np.nan
    v = np.array([b[key] for b in bl], float)
    wt = np.array([b[w] for b in bl], float)
    ok = np.isfinite(v)
    v, wt = v[ok], wt[ok]
    if not len(v):
        return np.nan, np.nan, np.nan

    def wmed(x, ww):
        i = np.argsort(x)
        x, ww = x[i], ww[i]
        c = np.cumsum(ww) / ww.sum()
        return float(x[np.searchsorted(c, 0.5)])
    pt = wmed(v, wt)
    dr = np.empty(nb)
    for i in range(nb):
        k = RNG.integers(0, len(v), len(v))
        dr[i] = wmed(v[k], wt[k])
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


hdr("§0  EXPOSURE -- manual, moving wheel (|rate| 3-20 deg/s), creep 0.3-4 m/s")
print(f"   {'route':10s} {'blocks':>7s} {'secs':>7s} {'median |rate|':>14s} {'travel deg':>11s}")
for t in ROUTES:
    bl = ALL[t]
    print(f"   {t:10s} {len(bl):>7d} {sum(b['secs'] for b in bl):>7.1f} "
          f"{np.median([b['mrate'] for b in bl]) if bl else np.nan:>14.1f} "
          f"{sum(b['trav'] for b in bl):>11.0f}")

# ================================================================= §1 effort decomposition ========
hdr("§1  ★★ THE EFFORT RISE, DECOMPOSED -- viscous SLOPE vs friction INTERCEPT")
print("   |tq| regressed on |rate| over pooled low-rate samples. A damper raises the SLOPE;")
print("   friction/stiction raises the INTERCEPT. Only an intercept rise feels like ratcheting.\n")
print(f"   {'route':10s} {'median |tq|':>12s} {'95% CI':>20s} | {'intercept':>10s} {'slope':>9s} "
      f"{'(counts per deg/s)':>19s}")
dec = {}
for t in ROUTES:
    bl = ALL[t]
    if not bl:
        continue
    m, lo, hi = epci(bl, "mtq")
    x = np.concatenate([b["rate"] for b in bl])
    y = np.concatenate([b["tq"] for b in bl])
    A = np.vstack([np.ones_like(x), x]).T
    c = np.linalg.lstsq(A, y, rcond=None)[0]
    dec[t] = dict(mtq=m, lo=lo, hi=hi, icept=float(c[0]), slope=float(c[1]), n=int(len(x)))
    print(f"   {t:10s} {m:>12.0f} {f'[{lo:.0f}, {hi:.0f}]':>20s} | {c[0]:>10.0f} {c[1]:>9.1f} "
          f"{'':>19s}")
OUT["effort"] = dec
v72 = dec["V72 r59"]
print(f"\n   V72 vs the two builds before it:")
for t in ("V71B r54", "V71C r58"):
    print(f"     vs {t:10s} median |tq| {v72['mtq'] / dec[t]['mtq']:.2f}x   "
          f"intercept {v72['icept'] / dec[t]['icept']:.2f}x   "
          f"slope {v72['slope'] / dec[t]['slope']:.2f}x")

# ================================================================= §2 roughness ===================
hdr("§2  ROUGHNESS AT MATCHED LOW RATE -- RMS in bands that EXCLUDE both known lines")
print(f"   {'route':10s} | " + " ".join(f"{n:>26s}" for n in
                                        ("3-6 Hz RMS", "10-16 Hz RMS", "3-30 Hz RMS")))
rough = {}
for t in ROUTES:
    bl = ALL[t]
    if not bl:
        continue
    row, cells = {}, []
    for k, lbl in (("r36", "3-6"), ("r1016", "10-16"), ("r330", "3-30")):
        m, lo, hi = epci(bl, k)
        row[lbl] = dict(m=m, lo=lo, hi=hi)
        cells.append(f"{f'{m:.0f} [{lo:.0f}, {hi:.0f}]':>26s}")
    rough[t] = row
    print(f"   {t:10s} | " + " ".join(cells))
OUT["roughness"] = rough

# ================================================================= §3 notch density ===============
hdr("§3  ★★ NOTCH DENSITY -- reversals of the 3-30 Hz effort component PER DEGREE of wheel travel")
print("   A felt ratchet is discrete catches per unit of travel. This counts them without")
print("   assuming any frequency, and it normalises out how fast the wheel was turned.\n")
print(f"   {'route':10s} {'reversals/deg':>14s} {'95% CI':>20s} {'total revs':>11s} {'travel deg':>11s}")
notch = {}
for t in ROUTES:
    bl = ALL[t]
    if not bl:
        continue
    m, lo, hi = epci(bl, "notch")
    notch[t] = dict(m=m, lo=lo, hi=hi, revs=int(sum(b["nrev"] for b in bl)),
                    trav=float(sum(b["trav"] for b in bl)))
    print(f"   {t:10s} {m:>14.3f} {f'[{lo:.3f}, {hi:.3f}]':>20s} "
          f"{sum(b['nrev'] for b in bl):>11d} {sum(b['trav'] for b in bl):>11.0f}")
OUT["notch"] = notch

hdr("§4  THE VERDICT LINE -- is V72 an OUTLIER on any of these, or inside the corpus spread?")
print(f"   {'statistic':22s} {'V72':>10s} {'corpus min':>11s} {'corpus max':>11s} "
      f"{'V72 rank':>9s}   verdict")
verd = {}
STATS = [("median |tq|", lambda t: dec[t]["mtq"]), ("friction intercept", lambda t: dec[t]["icept"]),
         ("viscous slope", lambda t: dec[t]["slope"]),
         ("3-6 Hz RMS", lambda t: rough[t]["3-6"]["m"]),
         ("10-16 Hz RMS", lambda t: rough[t]["10-16"]["m"]),
         ("notch/deg", lambda t: notch[t]["m"])]
others = [t for t in ROUTES if t != "V72 r59" and t in dec]
for lbl, fn in STATS:
    vals = [fn(t) for t in others]
    v = fn("V72 r59")
    rank = 1 + sum(1 for x in vals if x > v)
    out = "OUTLIER (highest)" if rank == 1 else ("OUTLIER (lowest)" if rank == len(vals) + 1
                                                 else "inside the corpus spread")
    verd[lbl] = dict(v72=v, lo=min(vals), hi=max(vals), rank=rank, n=len(vals) + 1)
    print(f"   {lbl:22s} {v:>10.3f} {min(vals):>11.3f} {max(vals):>11.3f} "
          f"{f'{rank}/{len(vals) + 1}':>9s}   {out}")
OUT["verdict"] = verd

json.dump(OUT, open(ROOT / "_r59_lowrate.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_r59_lowrate.json'}")
