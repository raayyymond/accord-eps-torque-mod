#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §4 WHICH CHANNEL CHANGED? bar torque vs rim ANGLE vs angle RATE.

🛑 THE REASON THIS FILE EXISTS. §2/§3 found route 59's 6-9 Hz BAR-TORQUE amplitude unattenuated
(median 3,647 counts p-p, 63% hit rate) while the operator reports the ratchet FIXED. Those two
statements are only compatible if the thing that changed is not the bar.

The torsion bar measures the TWIST between the rim and the motor side. If V72's Lever B (base-assist
damping below 35 km/h, which stock leaves at exactly zero) damps the COLUMN, rim motion can fall
while bar twist stays flat or even rises -- the damper's reaction torque is carried BY the bar.
`ang` (steering angle, 100 Hz, raw CAN) is rim POSITION; `rate_c` is rim RATE. Those are what the
hands feel as motion. This file prices the 6-9 Hz and 18-22 Hz bands in all three channels, per
route, in the same engaged hands-off creep cell, with episode-clustered CIs.

Writes `_scratch/out/_r59_channels.json`.
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
from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

NFFT = 256
RATCH, GRIND = (6.0, 9.0), (18.0, 22.0)
HANDS_OFF, CREEP = 300.0, 4.0
RNG = np.random.default_rng(20260805)
CHANS = [("tq", "bar torque, counts"), ("ang", "rim angle, deg"),
         ("rate_c", "rim rate, deg/s"), ("e4tq", "openpilot cmd")]
OUT = {}
ROUTES = {
    "V59 r2c":  ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
    "V62 r37":  ("_scratch/cache/r37", "r37s", list(range(15)), []),
    "V67 r47":  ("_scratch/cache/r47", "r47s", list(range(26)), []),
    "V69 r4f":  ("_scratch/cache/r4f", "r4fs", list(range(8)), []),
    "V70 r50":  ("_scratch/cache/r50", "r50s", [0, 1, 2], [0]),
    "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11]),
    "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15]),
    "V72 r59":  ("_scratch/cache/r59", "r59s", list(range(15)), [12, 13, 14]),
}


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


def scan(tag):
    cache, pfx, segs, skip = ROUTES[tag]
    recs = []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        t, tq = np.asarray(d["t"], float), np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        env = {}
        for ch, _ in CHANS:
            if ch not in d:
                continue
            x = np.asarray(d[ch], float)
            if not np.all(np.isfinite(x)):
                x = np.nan_to_num(x, nan=float(np.nanmedian(x)))
            env[(ch, "r")] = band_envelope(x, fs, *RATCH)
            env[(ch, "g")] = band_envelope(x, fs, *GRIND)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            r = dict(tag=tag, seg=int(s), i0=i, t0=float(t[i]), fs=fs,
                     v=float(v[w].mean()), lat=float(lat[w].mean()), eff=float(np.median(eff[w])),
                     fr=peak_prom(f, P, *RATCH)[0], fg=peak_prom(f, P, *GRIND)[0])
            for (ch, bnd), e in env.items():
                r[f"{ch}_{bnd}"] = float(2 * np.percentile(e[w], 99))
            recs.append(r)
    return recs


ALL = {t: scan(t) for t in ROUTES}


def cell(rs, eng=True, hands="off", vhi=CREEP):
    out = [r for r in rs if r["v"] < vhi]
    if eng is True:
        out = [r for r in out if r["lat"] > 0.9]
    elif eng is False:
        out = [r for r in out if r["lat"] < 0.1]
    if hands == "off":
        out = [r for r in out if r["eff"] <= HANDS_OFF]
    elif hands == "on":
        out = [r for r in out if r["eff"] > HANDS_OFF]
    return out


def episodes(rs):
    eps, cur = [], []
    for r in sorted(rs, key=lambda r: (r["seg"], r["i0"])):
        if cur and r["seg"] == cur[-1]["seg"] and r["i0"] == cur[-1]["i0"] + NFFT:
            cur.append(r)
        else:
            if cur:
                eps.append(cur)
            cur = [r]
    if cur:
        eps.append(cur)
    return eps


def epci(rs, key, nb=4000):
    eps = episodes(rs)
    v = np.array([r.get(key, np.nan) for r in rs], float)
    v = v[np.isfinite(v)]
    if not len(v) or not eps:
        return np.nan, np.nan, np.nan
    dr = np.empty(nb)
    for b in range(nb):
        k = RNG.integers(0, len(eps), len(eps))
        x = np.concatenate([[r.get(key, np.nan) for r in eps[j]] for j in k])
        x = x[np.isfinite(x)]
        dr[b] = np.median(x) if len(x) else np.nan
    return float(np.median(v)), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


def ratio_boot(a, b, key, nb=4000):
    ea, eb = episodes(a), episodes(b)
    va = np.array([r.get(key, np.nan) for r in a], float)
    vb = np.array([r.get(key, np.nan) for r in b], float)
    va, vb = va[np.isfinite(va)], vb[np.isfinite(vb)]
    if not len(va) or not len(vb) or not ea or not eb:
        return np.nan, np.nan, np.nan
    pt = float(np.median(va) / np.median(vb))
    dr = np.empty(nb)
    for i in range(nb):
        ka, kb = RNG.integers(0, len(ea), len(ea)), RNG.integers(0, len(eb), len(eb))
        xa = np.concatenate([[r.get(key, np.nan) for r in ea[j]] for j in ka])
        xb = np.concatenate([[r.get(key, np.nan) for r in eb[j]] for j in kb])
        xa, xb = xa[np.isfinite(xa)], xb[np.isfinite(xb)]
        dr[i] = np.median(xa) / np.median(xb) if len(xa) and len(xb) and np.median(xb) > 0 else np.nan
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


# ================================================================= §1 all channels, all routes ====
for bnd, bl, rng in (("r", "6-9 Hz  (the RATCHET band)", RATCH), ("g", "18-22 Hz  (GRIND #1)", GRIND)):
    hdr(f"§1{bnd}  {bl} -- p-p amplitude by CHANNEL, engaged hands-off creep, per route")
    print(f"   {'route':10s} {'n':>4s} | " + " ".join(f"{n:>26s}" for _, n in CHANS))
    tab = {}
    for tag in ROUTES:
        rs = cell(ALL[tag])
        if not rs:
            continue
        cells_s, row = [], {}
        for ch, _ in CHANS:
            k = f"{ch}_{bnd}"
            m, lo, hi = epci(rs, k)
            row[ch] = dict(med=m, lo=lo, hi=hi)
            cells_s.append(f"{f'{m:.3g} [{lo:.3g},{hi:.3g}]':>26s}")
        tab[tag] = row
        print(f"   {tag:10s} {len(rs):>4d} | " + " ".join(cells_s))
    OUT[f"chan_{bnd}"] = tab

# ================================================================= §2 the r59 vs prior ratio ======
hdr("§2  ★★ ROUTE 59 vs EACH PRIOR ROUTE, PER CHANNEL -- ratio of medians, episode-bootstrapped")
print("   ratio < 1 = V72 is QUIETER on that channel. THE QUESTION: does the bar say 'unchanged'")
print("   while the RIM says 'quieter'? That is the only way the operator's report and §2's")
print("   bar-torque null are both true.\n")
r59 = cell(ALL["V72 r59"])
rat = {}
for bnd, bl in (("r", "6-9 Hz"), ("g", "18-22 Hz")):
    print(f"   --- {bl}")
    print(f"   {'vs route':10s} | " + " ".join(f"{n:>24s}" for _, n in CHANS))
    for tag in ROUTES:
        if tag == "V72 r59":
            continue
        rs = cell(ALL[tag])
        if not rs:
            continue
        cells_s = []
        for ch, _ in CHANS:
            p, lo, hi = ratio_boot(r59, rs, f"{ch}_{bnd}")
            rat[f"{bnd}|{tag}|{ch}"] = dict(r=p, lo=lo, hi=hi)
            star = "*" if (np.isfinite(hi) and hi < 1) else (" " if not np.isfinite(hi) else " ")
            cells_s.append(f"{f'{p:.2f} [{lo:.2f},{hi:.2f}]{star}':>24s}")
        print(f"   {tag:10s} | " + " ".join(cells_s))
    print()
OUT["ratios"] = rat

# ================================================================= §3 pooled prior ================
hdr("§3  ★★★ POOLED: route 59 vs ALL PRIOR ROUTES POOLED, per channel and band")
print("   Pooling widens the prior arm's episode base from 2-20 to 74. 🛑 The pooled arm mixes")
print("   builds with known different doses -- read it as 'V72 vs the corpus', not vs one build.\n")
prior = [r for t in ROUTES if t != "V72 r59" for r in cell(ALL[t])]
print(f"   pooled prior: {len(episodes(prior))} episodes, {len(prior)} windows "
      f"({len(prior) * 2.56:.0f} s); route 59: {len(episodes(r59))} episodes, {len(r59)} windows "
      f"({len(r59) * 2.56:.0f} s)\n")
print(f"   {'band':10s} {'channel':22s} | {'prior median':>14s} {'r59 median':>12s} | "
      f"{'r59/prior':>10s} {'95% CI':>18s}   verdict")
pool = {}
for bnd, bl in (("r", "6-9 Hz"), ("g", "18-22 Hz")):
    for ch, nm in CHANS:
        k = f"{ch}_{bnd}"
        mp, _, _ = epci(prior, k)
        mr, _, _ = epci(r59, k)
        p, lo, hi = ratio_boot(r59, prior, k)
        pool[f"{bnd}|{ch}"] = dict(prior=mp, r59=mr, r=p, lo=lo, hi=hi)
        vd = ("V72 QUIETER" if np.isfinite(hi) and hi < 1 else
              ("V72 LOUDER" if np.isfinite(lo) and lo > 1 else "CI spans 1 -- no change shown"))
        print(f"   {bl:10s} {nm:22s} | {mp:>14.4g} {mr:>12.4g} | {p:>10.3f} "
              f"{f'[{lo:.3f}, {hi:.3f}]':>18s}   {vd}")
OUT["pooled"] = pool

json.dump(OUT, open(ROOT / "_scratch/out/_r59_channels.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_scratch/out/_r59_channels.json'}")
