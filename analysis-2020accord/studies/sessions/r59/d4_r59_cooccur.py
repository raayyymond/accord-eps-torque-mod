#!/usr/bin/env python3
"""D4 follow-up 2, REDONE. The first attempt was UNDERPOWERED BY CONSTRUCTION and I am discarding it.

🛑 WHAT WENT WRONG THE FIRST TIME. I required contiguous runs of the engaged-HANDS-OFF-CREEP mask
long enough for >=3 disjoint 2.56 s windows (7.68 s). That mask is intrinsically fragmentary -- the
driver brushes the wheel, speed drifts out of the creep band -- and it yielded **12 windows / 3
episodes across the ENTIRE corpus**. The "no relationship" that came out of it was a statement about
the mask, not about the physics, and it is withdrawn.

THE FIX. Run the same test on masks that actually produce long contiguous runs, and add a guard the
first version did not have:

  MASK 1  engaged + hands-off, ALL SPEEDS      (long runs; the relay's own conditional set minus creep)
  MASK 2  engaged, creep, ANY GRIP             (keeps creep, drops the fragile hands-off cut)

  GUARD   🛑 Pooling across speed can manufacture a positive correlation, because BOTH bands fall
          with speed (follow-up 2b: 6-9 x0.103 and 18-22 x0.083 at 10-16 m/s). So every correlation
          is reported TWICE: raw episode-centred, and again after the within-episode SPEED
          dependence is regressed out of both bands. If the relationship is a shared speed driver it
          dies in the second column.

  NULL    the 18-22 deviations permuted WITHIN each episode, 4000x -- marginals and episode
          structure preserved, pairing destroyed. Disjoint windows only (hop = NFFT).

Writes `_scratch/out/_d4_r59_cooccur.json`.
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
from _r31_common import band_envelope, runs_of, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
G1 = (18.0, 22.0)
NEG = (24.0, 28.0)              # the kit's pre-declared negative control band
HANDS_OFF = 300.0
CREEP_R = 4.0
OUT = {}
RNG = np.random.default_rng(20260805)

ROUTES = {
    "V59 r2c":  ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
    "V62 r37":  ("_scratch/cache/r37", "r37s", list(range(15)), []),
    "V67 r47":  ("_scratch/cache/r47", "r47s", list(range(26)), []),
    "V69 r4f":  ("_scratch/cache/r4f", "r4fs", list(range(8)), []),
    "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11]),
    "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15]),
    "V72 r59":  ("_scratch/cache/r59", "r59s", list(range(15)), [12, 13, 14]),
}
NEW = "V72 r59"


def hdr(s):
    print("\n" + "=" * 126 + f"\n{s}\n" + "=" * 126)


MASKS = {
    "engaged + hands-off, ALL speeds":
        lambda v, lat, eff: lat & (eff <= HANDS_OFF),
    "engaged, creep, any grip":
        lambda v, lat, eff: lat & (v < CREEP_R),
}


def episodes_of(cache, pfx, segs, skip, maskfn, minwin=3):
    eps = []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        er = band_envelope(tq, fs, *RATCH)
        eg = band_envelope(tq, fs, *G1)
        en = band_envelope(tq, fs, *NEG)
        eff = np.abs(sustained(tq, fs))
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        m = maskfn(v, lat, eff)
        for a, b in runs_of(m, d["t"], NFFT):
            cur = []
            for i in range(a, b - NFFT + 1, NFFT):
                w = slice(i, i + NFFT)
                cur.append((float(np.percentile(er[w], 99)), float(np.percentile(eg[w], 99)),
                            float(np.percentile(en[w], 99)), float(v[w].mean())))
            if len(cur) >= minwin:
                eps.append(np.array(cur))
    return eps


def _resid(dev, sdev):
    """Remove the within-episode linear dependence on speed."""
    if np.std(sdev) < 1e-9:
        return dev
    b = float(np.dot(dev, sdev) / np.dot(sdev, sdev))
    return dev - b * sdev


def corr_test(eps, ycol=1, despeed=False, nperm=4000):
    """(r, null lo, null hi, perm p, nwin, neps) on episode-centred log deviations."""
    xs, ys = [], []
    for e in eps:
        lx = np.log(np.maximum(e[:, 0], 1e-6))
        ly = np.log(np.maximum(e[:, ycol], 1e-6))
        ls = e[:, 3]
        dx, dy = lx - lx.mean(), ly - ly.mean()
        if despeed:
            ds = ls - ls.mean()
            dx, dy = _resid(dx, ds), _resid(dy, ds)
        xs.append(dx)
        ys.append(dy)
    if not xs:
        return (np.nan,) * 4 + (0, 0)
    X, Y = np.concatenate(xs), np.concatenate(ys)
    if len(X) < 12 or np.std(X) < 1e-12 or np.std(Y) < 1e-12:
        return (np.nan,) * 4 + (len(X), len(eps))
    obs = float(np.corrcoef(X, Y)[0, 1])
    draws = np.empty(nperm)
    for j in range(nperm):
        draws[j] = np.corrcoef(X, np.concatenate([RNG.permutation(y) for y in ys]))[0, 1]
    p = float((np.sum(np.abs(draws) >= abs(obs)) + 1) / (nperm + 1))
    return (obs, float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)), p,
            len(X), len(eps))


for mname, mfn in MASKS.items():
    hdr(f"CO-OCCURRENCE under mask: {mname}\n"
        f"    6-9 Hz vs 18-22 Hz, episode-centred log deviations. Right block regresses out the\n"
        f"    within-episode SPEED dependence from BOTH bands. 24-28 Hz is the negative control.")
    print(f"   {'route':10s} {'nwin':>5s} {'neps':>5s} | {'r (raw)':>8s} {'null':>17s} {'p':>7s} "
          f"| {'r (de-speeded)':>14s} {'null':>17s} {'p':>7s} | {'r vs 24-28':>10s} {'p':>7s}")
    tab = {}
    pool = []
    for tag, (cache, pfx, segs, skip) in ROUTES.items():
        eps = episodes_of(cache, pfx, segs, skip, mfn)
        pool += eps
        a = corr_test(eps)
        b = corr_test(eps, despeed=True)
        c = corr_test(eps, ycol=2, despeed=True)
        tab[tag] = dict(raw=a[:4], despeed=b[:4], neg=c[:4], n=a[4], neps=a[5])
        if not np.isfinite(a[0]):
            print(f"   {tag:10s} {a[4]:>5d} {a[5]:>5d} |   *** too few windows")
            continue
        print(f"   {tag:10s} {a[4]:>5d} {a[5]:>5d} | {a[0]:>8.3f} [{a[1]:>6.3f},{a[2]:>7.3f}] "
              f"{a[3]:>7.4f} | {b[0]:>14.3f} [{b[1]:>6.3f},{b[2]:>7.3f}] {b[3]:>7.4f} | "
              f"{c[0]:>10.3f} {c[3]:>7.4f}")
    a = corr_test(pool)
    b = corr_test(pool, despeed=True)
    c = corr_test(pool, ycol=2, despeed=True)
    print(f"   {'POOLED':10s} {a[4]:>5d} {a[5]:>5d} | {a[0]:>8.3f} [{a[1]:>6.3f},{a[2]:>7.3f}] "
          f"{a[3]:>7.4f} | {b[0]:>14.3f} [{b[1]:>6.3f},{b[2]:>7.3f}] {b[3]:>7.4f} | "
          f"{c[0]:>10.3f} {c[3]:>7.4f}")
    v = ("POSITIVE co-occurrence, survives de-speeding" if (b[0] > b[2]) else
         "ANTI-correlated" if (b[0] < b[1]) else "no relationship once speed is removed")
    print(f"   ⇒ {v}")
    tab["POOLED"] = dict(raw=a[:4], despeed=b[:4], neg=c[:4], n=a[4], neps=a[5], verdict=v)
    OUT[mname] = tab

# ---------------------------------------------------------------- conditional-shape agreement ----
hdr("CONDITIONAL-SHAPE AGREEMENT -- do the two bands respond to the SAME conditionals by the SAME\n"
    "    factors? Route 59 only, so both bands are read off the SAME windows.")
d = ROUTES[NEW]
cache, pfx, segs, skip = d
rows = []
for s in segs:
    if s in skip:
        continue
    p = ROOT / cache / f"{pfx}{s}.npz"
    if not p.exists():
        continue
    dd = C.load(s, ROOT / cache, pfx)
    fs = R4F.fs_lattice(dd)
    tq = np.asarray(dd["tq"], float)
    er, eg, en = (band_envelope(tq, fs, *b) for b in (RATCH, G1, NEG))
    eff = np.abs(sustained(tq, fs))
    v = np.abs(np.asarray(dd["cs_v"], float))
    lat = np.asarray(dd["cc_lat"], float) > 0.5
    for i in range(0, len(tq) - NFFT + 1, NFFT):
        w = slice(i, i + NFFT)
        rows.append(dict(er=float(np.percentile(er[w], 99)), eg=float(np.percentile(eg[w], 99)),
                         en=float(np.percentile(en[w], 99)), v=float(v[w].mean()),
                         eff=float(np.median(eff[w])), lat=float(lat[w].mean())))
CELLS = {
    "engaged hands-off creep (base)": lambda r: r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] > 0.9,
    "engaged hands-ON creep": lambda r: r["v"] < CREEP_R and r["eff"] > HANDS_OFF and r["lat"] > 0.9,
    "MANUAL hands-off creep": lambda r: r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] < 0.1,
    "MANUAL hands-ON creep": lambda r: r["v"] < CREEP_R and r["eff"] > HANDS_OFF and r["lat"] < 0.1,
    "engaged hands-off 4-10 m/s": lambda r: 4 <= r["v"] < 10 and r["eff"] <= HANDS_OFF and r["lat"] > 0.9,
    "engaged hands-off 10-16 m/s": lambda r: 10 <= r["v"] < 16 and r["eff"] <= HANDS_OFF and r["lat"] > 0.9,
    "engaged hands-off >=16 m/s": lambda r: r["v"] >= 16 and r["eff"] <= HANDS_OFF and r["lat"] > 0.9,
}
base = [r for r in rows if list(CELLS.values())[0](r)]
b6, b18, bn = (np.median([r[k] for r in base]) for k in ("er", "eg", "en"))
print(f"   {'cell':34s} {'n':>4s} | {'6-9 x':>8s} {'18-22 x':>8s} {'24-28 x':>8s}")
lr, lg = [], []
sh = {}
for cn, sel in CELLS.items():
    s = [r for r in rows if sel(r)]
    if len(s) < 4:
        continue
    r6 = np.median([r["er"] for r in s]) / b6
    r18 = np.median([r["eg"] for r in s]) / b18
    rn = np.median([r["en"] for r in s]) / bn
    sh[cn] = dict(n=len(s), r69=float(r6), r1822=float(r18), r2428=float(rn))
    lr.append(np.log(r6))
    lg.append(np.log(r18))
    print(f"   {cn:34s} {len(s):>4d} | {r6:>8.3f} {r18:>8.3f} {rn:>8.3f}")
rho = float(np.corrcoef(lr, lg)[0, 1])
sl = float(np.polyfit(lr, lg, 1)[0])
print(f"\n   ★ Across the {len(lr)} cells: corr(log 6-9 factor, log 18-22 factor) = {rho:.3f}; "
      f"log-log slope {sl:.3f}")
print("   A slope near 1 means the two bands are switched on and off by the SAME conditionals in")
print("   the SAME proportion. ⚠ n = 7 cells and they are not independent; this is descriptive.")
OUT["conditional_shape"] = dict(cells=sh, corr=rho, slope=sl)

(ROOT / "_scratch/out/_d4_r59_cooccur.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_r59_cooccur.json'}")
