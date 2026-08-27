#!/usr/bin/env python3
"""DELIVERABLE 2 -- the two symptoms separated, on the metric each one actually needs.

🛑 GRIND #1 IS A LIMIT CYCLE, so DUTY is its primary metric, not median band energy
(`studies/sessions/r5d/r5d_duty.py` §1: across 8 routes, duty spans 64x while in-burst amplitude spans 1.24x). The
micro ratchet is scored the same way, on the same windows, so the two are directly comparable.
Instrument: `_nearcentre_lib` UNCHANGED -- engaged creep (< 5.556 m/s), window angle span 8-200 deg
(the grind-ACTIVE regime, so a duty question does not become an exposure question), T = 600 counts
of the band's p99 envelope.

Also here: the BAND-RELATIVE excess over the 24-28 Hz control, matched on speed bins, which is the
form that survives an amplitude-scale question -- and the manual arm, which on V74 and V75 is
BYTE-STOCK (the damper is written on the engaged column only), i.e. an on-car zero-dose control
recorded on the same route, same tyres, same driver, same day.

Usage:  python studies/sessions/v78/v78_symptom_limitcycle.py   ->  writes _scratch/out/_v78_limitcycle.json
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
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import v78_symptom_lib as V  # noqa: E402

G.EPKEY = "blk"                 # `studies/sessions/r5d/r5d_duty.py`'s own default -- the same unit, so it is comparable
RNG = np.random.default_rng(78078)
NBOOT = 3000
OUT = {"epkey": G.EPKEY}
SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
ACTIVE_SB = (2, 3, 4)
PARK = {"V74/r5d": [2, 3, 9], "V75/r5e": [0]}
V.install_fs()

SRC = ROOT / "_scratch/data/_cache_r5d_nearcentre.pkl"
MINE = ROOT / "_scratch/data/_cache_r5e_sym_nearcentre.pkl"
with open(SRC, "rb") as fh:
    store = pickle.load(fh)          # READ-ONLY -- never written back
if MINE.exists():
    with open(MINE, "rb") as fh:
        store.update(pickle.load(fh))
else:
    R = V.records()
    rs = [dict(r) for r in R["V75/r5e"] if r["seg"] not in PARK["V75/r5e"]]
    add = {"V75/r5e": N.augment_angle(rs, nfft=N.NFFT)}
    with open(MINE, "wb") as fh:
        pickle.dump(add, fh)
    store.update(add)

LADDER = [b for b in N.LADDER + ["V73/r5a", "V74/r5d", "V75/r5e"] if b in store]
for b in LADDER:
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["sb"] = G.binof(r["span"], SP)

ARMS = dict(N.ARMS)
ARMS.update({"V73/r5a": ["V73/r5a"], "V74/r5d": ["V74/r5d"], "V75/r5e": ["V75/r5e"]})
ENGC = {b: N.eng_creep(store[b]) for b in LADDER}
MANC = {b: N.man_creep(store[b]) for b in LADDER}
ARM = {k: [r for n in v for r in ENGC[n] if n in ENGC] for k, v in ARMS.items()}
ACTIVE = {k: [r for r in v if r["sb"] in ACTIVE_SB] for k, v in ARM.items()}
ORDER = ["V61 (kill)", "stock pool", "V72/r59", "V73/r5a", "V74/r5d", "V75/r5e", "V71C/r58",
         "V71B/r54", "V62+V65", "V69/r4f", "V70/r50", "V67+V68"]
ORDER = [k for k in ORDER if k in ACTIVE]


def boot_units(rs, fn, key="e_18-22", nb=NBOOT):
    ep = {}
    for r in rs:
        ep.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, key) for v in ep.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return (np.nan,) * 3
    allv = np.concatenate(per)
    d = np.full(nb, np.nan)
    for i in range(nb):
        v = np.concatenate([per[j] for j in RNG.integers(0, len(per), len(per))])
        if len(v):
            d[i] = fn(v)
    return float(fn(allv)), float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))


def ratio_units(A, B, fn, key, nb=2000):
    ea, eb = {}, {}
    for r in A:
        ea.setdefault(r[G.EPKEY], []).append(r)
    for r in B:
        eb.setdefault(r[G.EPKEY], []).append(r)
    ka, kb = list(ea), list(eb)
    if len(ka) < 2 or len(kb) < 2:
        return (np.nan,) * 3
    d = np.full(nb, np.nan)
    for i in range(nb):
        a = np.concatenate([G.col(ea[ka[j]], key) for j in RNG.integers(0, len(ka), len(ka))])
        b = np.concatenate([G.col(eb[kb[j]], key) for j in RNG.integers(0, len(kb), len(kb))])
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) and len(b) and fn(b) > 0:
            d[i] = fn(a) / fn(b)
    fa = fn(np.concatenate([G.col(ea[k], key) for k in ka]))
    fb = fn(np.concatenate([G.col(eb[k], key) for k in kb]))
    return (float(fa / fb) if fb else np.nan,
            float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5)))


def split_half(rs, fn, key, nrep=400):
    ep = {}
    for r in rs:
        ep.setdefault(r[G.EPKEY], []).append(r)
    ks = list(ep)
    if len(ks) < 4:
        return np.nan, np.nan
    out = []
    for _ in range(nrep):
        p = RNG.permutation(len(ks))
        h = len(ks) // 2
        a = np.concatenate([G.col(ep[ks[i]], key) for i in p[:h]])
        b = np.concatenate([G.col(ep[ks[i]], key) for i in p[h:]])
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) and len(b) and fn(b) > 0:
            out.append(fn(a) / fn(b))
    return (float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))) \
        if len(out) > 20 else (np.nan, np.nan)


# ================================================== 1. DUTY, BOTH BANDS ===========================
T = 600.0
res = {}
for key, kl in (("e_18-22", "GRIND #1  18-22 Hz"), ("e_6-9", "MICRO RATCHET  6-9 Hz")):
    V.hdr(f"1. ★★★ {kl} AS A LIMIT CYCLE -- duty x in-burst amplitude, T = {T:.0f} counts")
    print("  Engaged creep (< 5.556 m/s), window angle span 8-200 deg. `blk` (~10 s) resampling")
    print("  unit, exactly as `studies/sessions/r5d/r5d_duty.py`. duty = fraction of windows at or above T; in-burst =")
    print("  the median AMONG those windows. A limit cycle moves DUTY and leaves in-burst alone.\n")
    print(f"  {'arm':<12} {'n':>5} {'blk':>4} {'median':>8} | {'duty':>6} {'[95% CI]':>16} | "
          f"{'in-burst':>9} {'v_med':>6}")
    for k in ORDER:
        rs = ACTIVE.get(k, [])
        nb = len({r[G.EPKEY] for r in rs})
        if len(rs) < 10 or nb < 3:
            print(f"  {k:<12} {len(rs):>5} {nb:>4}   *** UNDERPOWERED / EMPTY")
            res[f"{key}|{k}"] = dict(n=len(rs), nb=nb, underpowered=True)
            continue
        v = G.col(rs, key)
        v = v[np.isfinite(v)]
        burst = [r for r in rs if np.isfinite(r[key]) and r[key] >= T]
        duty, dlo, dhi = boot_units(rs, lambda x: float(np.mean(x >= T)), key)
        ib = (boot_units(burst, np.median, key)[0]
              if len(burst) >= 5 and len({r[G.EPKEY] for r in burst}) >= 3 else np.nan)
        res[f"{key}|{k}"] = dict(n=len(rs), nb=nb, med=float(np.median(v)), duty=duty, dlo=dlo,
                                 dhi=dhi, inburst=ib, nburst=len(burst), k=V.K_RAMP.get(k, np.nan),
                                 vmed=float(np.median([r["v"] for r in rs])))
        print(f"  {k:<12} {len(rs):>5} {nb:>4} {np.median(v):>8.0f} | {duty:>6.3f} "
              f"[{dlo:>6.3f},{dhi:>7.3f}] | "
              + (f"{ib:>9.0f}" if np.isfinite(ib) else f"{'(' + str(len(burst)) + ' w)':>9}")
              + f" {res[f'{key}|{k}']['vmed']:>6.2f}")

    print(f"\n  ★★ V75 vs its predecessors on DUTY -- ratio (V75 / other), < 1 = V75 better.")
    nlo, nhi = split_half(ACTIVE["V75/r5e"], lambda x: float(np.mean(x >= T)), key)
    print(f"     V75's own split-half null on this statistic: [{nlo:.3f}, {nhi:.3f}]"
          + ("   (< 4 blocks -- NOT COMPUTABLE)" if not np.isfinite(nlo) else ""))
    for k in ("V74/r5d", "V73/r5a", "V72/r59", "stock pool", "V67+V68", "V62+V65"):
        if k not in ACTIVE or len(ACTIVE[k]) < 10:
            continue
        p, lo, hi = ratio_units(ACTIVE["V75/r5e"], ACTIVE[k],
                                lambda x: float(np.mean(x >= T)), key)
        cl = ("CLEARS null" if np.isfinite(nlo) and (lo > nhi or hi < nlo) else "inside null")
        print(f"       vs {k:<12} {p:7.3f} [{lo:7.3f}, {hi:7.3f}]   {cl}")
        res.setdefault(f"ratio|{key}", {})[k] = [p, lo, hi, cl]
OUT["limitcycle"] = res

# ================================================== 2. RELATIVE EXCESS ============================
V.hdr("2. ★★ BAND-RELATIVE EXCESS over the 24-28 Hz control -- speed-matched, per-window pairing")
print("  Each window contributes band/control, so an overall amplitude difference between routes")
print("  cancels inside the window. Medians are taken inside shared speed bins and combined with")
print("  weight 1/(1/nA + 1/nB), then episode-bootstrapped.")
print("  🛑 The MANUAL arm on V74 and V75 is BYTE-STOCK (engaged-column-only design), so it is a")
print("  same-route zero-dose control -- the closest thing this corpus has to a perceptual floor.\n")
VB = [(0.5, 2.0), (2.0, 4.0), (4.0, 6.2), (6.2, 9.4), (9.4, 12.5)]
R = V.records()


def rel(b, key, eng=1, vhi=12.5):
    o = []
    for r in R[b]:
        if r["seg"] in PARK.get(b, []) or r["eng"] != eng:
            continue
        if not (0.5 <= r["v"] < vhi):
            continue
        if r.get("e_24-28", 0) > 0 and np.isfinite(r[key]):
            o.append((r[key] / r["e_24-28"], r["v"], r["ep"]))
    return o


def matched(A, B, nb=3000):
    """Speed-bin-matched ratio of median relative excess, episode-resampled on BOTH arms."""
    def strat(a, b):
        num = den = 0.0
        for lo, hi in VB:
            xa = [x for x, v, _ in a if lo <= v < hi]
            xb = [x for x, v, _ in b if lo <= v < hi]
            if len(xa) < 5 or len(xb) < 5:
                continue
            ma, mb = np.median(xa), np.median(xb)
            if ma <= 0 or mb <= 0:
                continue
            w = 1.0 / (1.0 / len(xa) + 1.0 / len(xb))
            num += w * np.log(ma / mb)
            den += w
        return np.exp(num / den) if den else np.nan
    ea, eb = {}, {}
    for x in A:
        ea.setdefault(x[2], []).append(x)
    for x in B:
        eb.setdefault(x[2], []).append(x)
    ka, kb = list(ea), list(eb)
    if len(ka) < 2 or len(kb) < 2:
        return (np.nan,) * 4
    pt = strat(A, B)
    d = np.full(nb, np.nan)
    for i in range(nb):
        aa = [x for j in RNG.integers(0, len(ka), len(ka)) for x in ea[ka[j]]]
        bb = [x for j in RNG.integers(0, len(kb), len(kb)) for x in eb[kb[j]]]
        d[i] = strat(aa, bb)
    return (float(pt), float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5)),
            int(np.isfinite(d).sum()))


rel_tab = {}
print(f"  {'build':<10} {'arm':<8} {'6-9 / ctl':>26} {'18-22 / ctl':>26}")
for b in ("V75/r5e", "V74/r5d", "V73/r5a", "V72/r59", "V67/r47", "V62/r37", "V59/r2c"):
    for eng, alab in ((1, "engaged"), (0, "manual")):
        cells = []
        for key in ("e_6-9", "e_18-22"):
            xs = rel(b, key, eng)
            if len(xs) < 12:
                cells.append(f"{'(n=' + str(len(xs)) + ')':>26}")
                continue
            ep = {}
            for x in xs:
                ep.setdefault(x[2], []).append(x[0])
            ks = list(ep)
            allv = np.concatenate([ep[k] for k in ks])
            d = np.array([np.median(np.concatenate([ep[ks[j]] for j in
                                                    RNG.integers(0, len(ks), len(ks))]))
                          for _ in range(2000)])
            m, lo, hi = float(np.median(allv)), *np.nanpercentile(d, [2.5, 97.5])
            rel_tab[f"{b}|{alab}|{key}"] = [m, float(lo), float(hi), len(xs), len(ks)]
            cells.append(f"{m:8.2f} [{lo:6.2f},{hi:7.2f}]")
        print(f"  {b:<10} {alab:<8} " + " ".join(f"{c:>26}" for c in cells))
OUT["relative_excess"] = rel_tab

print("\n  ★★ SPEED-MATCHED RATIOS of the relative excess (episode-resampled, 5 shared speed bins):")
print(f"  {'contrast':<22} {'6-9 / ctl ratio':>28} {'18-22 / ctl ratio':>28}")
mt = {}
for a, b in (("V75/r5e", "V74/r5d"), ("V75/r5e", "V73/r5a"), ("V74/r5d", "V73/r5a"),
             ("V75/r5e", "V59/r2c"), ("V74/r5d", "V59/r2c")):
    cells = []
    for key in ("e_6-9", "e_18-22"):
        p, lo, hi, n = matched(rel(a, key), rel(b, key))
        mt[f"{a}/{b}|{key}"] = [p, lo, hi]
        cells.append(f"{p:8.3f} [{lo:6.3f},{hi:7.3f}]")
    print(f"  {a.split('/')[0]:>8} / {b.split('/')[0]:<10} " + " ".join(f"{c:>28}" for c in cells))
print("\n  ⊕ the SAME-ROUTE engaged/manual contrast (manual is BYTE-STOCK on V74 and V75):")
for b in ("V75/r5e", "V74/r5d"):
    cells = []
    for key in ("e_6-9", "e_18-22"):
        p, lo, hi, n = matched(rel(b, key, 1), rel(b, key, 0))
        mt[f"{b}|eng/man|{key}"] = [p, lo, hi]
        cells.append(f"{p:8.3f} [{lo:6.3f},{hi:7.3f}]")
    print(f"  {b:<22} " + " ".join(f"{c:>28}" for c in cells))
OUT["matched_ratios"] = mt

with open(ROOT / "_scratch/out/_v78_limitcycle.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_v78_limitcycle.json")
