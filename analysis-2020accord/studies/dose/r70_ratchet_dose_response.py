#!/usr/bin/env python3
"""studies/dose/r70_ratchet_dose_response.py -- is the ~7.5 Hz RATCHET dose-responsive across V67 / V68 / V69?

The ratchet is the only symptom in this kit with NO dose-response curve. V69 doses engaged creep at
~3.5-4x against V67's ~1.7x and is the first build since V65 to dose MANUAL creep at all, so V70's
arm choice cannot be made without knowing whether the ratchet moves with the rate-lane gain.

METHOD -- identical estimator, cell, and null machinery as `studies/sessions/r4f/r4f_v69_readout.py`, applied route by
route. The cell is the ratchet's own: ENGAGED & v <= 4 m/s & |sustained torsion bar| < 300.

  * detector      : 6-9 Hz peak / median(2-20 Hz outside the band) on the bar torque and the angle
                    rate, over fixed 2.56 s windows (256 samples). 128-sample minimum inside
                    band_prom, so a half-window is still scorable.
  * amplitude     : 6-9 Hz band-passed bar torque, peak-to-peak, per window. CONTINUOUS -- more
                    powerful than a threshold count and it is what "worse" actually means.
  * common floor  : pooled 95th percentile of every route's OUTSIDE-cell matched-window null. A
                    per-route floor would absorb exactly the effect we are testing.
  * CIs           : bootstrap over EPISODES (contiguous cell runs), never over windows. Standing
                    instruction 2026-08-02 -- window bootstraps shrink CIs by ~sqrt(n_per_episode).

🛑 EXPOSURE IS PRINTED FIRST, PER ROUTE. If a route has no engaged-creep episodes it cannot speak to
   the ratchet and is reported as UNPOWERED, not as a ratio.
🛑 ROUTE/ROAD/DAY CONFOUNDS ARE NOT CONTROLLED. These are different drives on different days over
   different surfaces. A dose-response here is SUGGESTIVE; only a within-route arm contrast (as V67's
   route 47 gave for grind #1) is decisive.
🛑 BUILD IDENTITY IS TAKEN FROM THE PROBE, never the route number -- the byte4 histogram is printed
   for every route and the caller must sanity-check it.

Usage:  python studies/dose/r70_ratchet_dose_response.py
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
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = Path(__file__).resolve().parents[2].parent
sys.path.insert(0, str(KIT / "rlog-tools"))
sys.path.insert(0, str(KIT / "analysis-2020accord"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

from decode_v67_gate import runs_of, sustained                                # noqa: E402
from r4f_v69_readout import extract                                           # noqa: E402

RLOGS = KIT / "analysis-2020accord" / "rlogs"
CACHEDIR = KIT / "analysis-2020accord"

# (label, expected build, route stem, segment indices). Identity is CHECKED from the probe below.
ROUTES = (
    ("r47", "V67 (expected)", "75604b0a432fdc89_00000047--3e0b6134c0", range(26)),
    ("r4a", "V68 (expected)", "75604b0a432fdc89_0000004a--346bf31d97", range(20, 26)),
    ("r4e", "V68 (expected)", "75604b0a432fdc89_0000004e--11f5b814b6", range(31, 35)),
    ("r4f", "V69 (expected)", "75604b0a432fdc89_0000004f--61171e660d", range(8)),
)

CREEP_MAX_MS = 4.0
HANDS_OFF_TQ = 300
W = 256          # 2.56 s analysis window
MINSEG = 128     # 1.28 s -> 0.78 Hz resolution; 6-9 Hz still spans ~4 bins
LO, HI = 6.0, 9.0
RATCHET_F0 = 7.56


def band_prom(x, fs, lo=LO, hi=HI):
    x = np.asarray(x, float)
    x = x - x.mean()
    if len(x) < MINSEG or not np.isfinite(x).all() or x.std() == 0:
        return float("nan"), float("nan")
    P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    b = (f >= lo) & (f <= hi)
    bg = (f >= 2.0) & (f <= 20.0) & ~b
    fl = np.median(P[bg])
    i = np.argmax(P[b])
    return float(f[b][i]), float(P[b][i] / fl) if fl > 0 else float("nan")


def band_pp(x, fs, lo=LO, hi=HI):
    """Peak-to-peak of the 6-9 Hz band-passed signal, in raw bar counts."""
    x = np.asarray(x, float)
    x = x - x.mean()
    if len(x) < MINSEG:
        return float("nan")
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, len(x))
    return float(y.max() - y.min())


def windows(sel, w=W, hop=W // 2):
    """Sliding windows inside each contiguous run, tagged with their episode index.

    50% overlap, because tiling wasted most of the short episodes (r47's 25.4 s cell yielded only
    5 non-overlapping windows). Overlap induces dependence BETWEEN windows, which is exactly what
    the episode-level bootstrap already handles -- it resamples episodes, never windows.
    """
    out = []
    for ei, (a, b) in enumerate(runs_of(sel)):
        for a0 in range(a, b - w + 1, hop):
            out.append((ei, a0, a0 + w))
    return out


def load_route(tag, stem, segs):
    cache = CACHEDIR / f"_cache_{tag}_ratchet.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        return {k: z[k] for k in z.files}
    paths = [str(RLOGS / f"{stem}--{i}--rlog.zst") for i in segs]
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        raise FileNotFoundError(f"{tag}: {len(missing)} segments missing, first {missing[0]}")
    d = extract(paths)
    np.savez_compressed(cache, **d)
    return d


def bootstrap_episodes(values, ep_idx, stat, n=4000, seed=70):
    """Resample EPISODES with replacement; recompute `stat` over the pooled windows each time."""
    rng = np.random.default_rng(seed)
    eps = np.unique(ep_idx)
    if len(eps) < 2:
        return float("nan"), float("nan")
    by = {e: np.flatnonzero(ep_idx == e) for e in eps}
    out = []
    for _ in range(n):
        pick = rng.choice(eps, size=len(eps), replace=True)
        idx = np.concatenate([by[e] for e in pick])
        v = stat(values[idx])
        if np.isfinite(v):
            out.append(v)
    if not out:
        return float("nan"), float("nan")
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    print(__doc__)
    per = {}
    for tag, exp, stem, segs in ROUTES:
        print("\n" + "=" * 102)
        d = load_route(tag, stem, segs)
        b4, t = d["b4"], d["t"]
        n = len(b4)
        fs = (n - 1) / (t[-1] - t[0])
        lat = d["lat"].astype(bool)
        sus = np.abs(sustained(d["tq"], fs))
        cell = lat & (d["v"] <= CREEP_MAX_MS) & (sus < HANDS_OFF_TQ)
        outside = lat & ~cell
        h = Counter(int(x) for x in b4)
        print(f"{tag}  {exp}   segments {len(np.unique(d['seg']))}   frames {n}   "
              f"span {t[-1] - t[0]:.1f} s   mean rate {fs:.3f} Hz")
        print(f"  🛑 IDENTITY FROM THE PROBE -- byte4: "
              f"{ {hex(k): v for k, v in sorted(h.items())} }")
        print(f"  EXPOSURE FIRST:  engaged {lat.sum() / fs:7.1f} s | "
              f"engaged+creep {(lat & (d['v'] <= CREEP_MAX_MS)).sum() / fs:7.1f} s | "
              f"RATCHET CELL {cell.sum() / fs:7.1f} s | episodes >= 2.56 s "
              f"{len([1 for a, b in runs_of(cell) if b - a >= W])}")
        per[tag] = dict(d=d, fs=fs, cell=cell, outside=outside, exp=exp, hist=h, n=n)

    # ---- POOLED NULL, computed BEFORE any ratio is quoted --------------------------------------
    print("\n" + "=" * 102)
    print("THE COMMON FLOOR -- pooled matched-window null from OUTSIDE the cell, all routes")
    rng = np.random.default_rng(70)
    pooled, per_route_null = [], {}
    for tag, p in per.items():
        d, fs = p["d"], p["fs"]
        orr = [ab for ab in runs_of(p["outside"]) if ab[1] - ab[0] >= W]
        vals = []
        for _ in range(600):
            if not orr:
                break
            a, b = orr[rng.integers(len(orr))]
            s0 = a + rng.integers(0, b - a - W + 1)
            for ch in (d["tq"], d["rate"]):
                _, v = band_prom(ch[s0:s0 + W], fs)
                if np.isfinite(v):
                    vals.append(v)
        per_route_null[tag] = vals
        pooled += vals
        print(f"  {tag}: n={len(vals):5d}  median {np.median(vals) if vals else np.nan:7.2f}  "
              f"95th {np.percentile(vals, 95) if vals else np.nan:8.2f}  "
              f"max {max(vals) if vals else np.nan:8.2f}")
    FLOOR = float(np.percentile(pooled, 95))
    print(f"  ⇒ POOLED 95th percentile = COMMON FLOOR = {FLOOR:.2f}   (n = {len(pooled)})")
    print("  ⚠ A per-route floor would absorb the very effect under test, so the floor is common.")

    # ---- THE MEASUREMENT ------------------------------------------------------------------------
    # 🛑 THE CONFOUND THAT MATTERS: raw 6-9 Hz p-p rises with how hard the wheel is being worked, so
    # a busier parking lot alone would produce a bigger number. `sel` = pp(6-9 Hz) / pp(1-4 Hz)
    # normalises by the DRIVER band in the same window -- the control V62's analysis used. Report
    # both; only `sel` can distinguish "the ratchet got worse" from "this drive was busier".
    print("\n" + "=" * 102)
    print("THE RATCHET, PER BUILD -- 2.56 s windows, 50% overlap, over the ratchet cell")
    print(f"  {'route':>6s} {'build':>16s} {'cell s':>7s} {'eps':>4s} {'wins':>5s} {'hits':>5s} "
          f"{'hit rate':>18s} {'pp p50':>7s} {'pp p95':>7s} {'drv p50':>8s} "
          f"{'sel p50':>8s} {'sel p50 CI':>16s} {'medHz':>6s}")
    rows = {}
    for tag, p in per.items():
        d, fs, cell = p["d"], p["fs"], p["cell"]
        wins = windows(cell)
        if not wins:
            print(f"  {tag:>6s} {p['exp']:>16s} {cell.sum() / fs:7.1f}    0     0     0"
                  f"      UNPOWERED -- no engaged-creep episodes; this route cannot speak to the "
                  f"ratchet in either direction")
            rows[tag] = None
            continue
        ei = np.array([w[0] for w in wins])
        prom = np.array([max(band_prom(d["tq"][a:b], fs)[1], band_prom(d["rate"][a:b], fs)[1])
                         for _, a, b in wins])
        pks = np.array([band_prom(d["tq"][a:b], fs)[0] for _, a, b in wins])
        pp = np.array([band_pp(d["tq"][a:b], fs) for _, a, b in wins])
        drv = np.array([band_pp(d["tq"][a:b], fs, 1.0, 4.0) for _, a, b in wins])
        sel = pp / np.where(drv > 0, drv, np.nan)
        hit = prom > FLOOR
        lo_r, hi_r = bootstrap_episodes(hit.astype(float), ei, np.mean)
        lo_s, hi_s = bootstrap_episodes(sel, ei, lambda x: np.nanmedian(x))
        print(f"  {tag:>6s} {p['exp']:>16s} {cell.sum() / fs:7.1f} {len(np.unique(ei)):4d} "
              f"{len(wins):5d} {int(hit.sum()):5d} "
              f"{'%.3f [%.3f, %.3f]' % (hit.mean(), lo_r, hi_r):>18s} "
              f"{np.percentile(pp, 50):7.0f} {np.percentile(pp, 95):7.0f} "
              f"{np.percentile(drv, 50):8.0f} {np.nanmedian(sel):8.3f} "
              f"{'[%.3f, %.3f]' % (lo_s, hi_s):>16s} "
              f"{np.median(pks[hit]) if hit.any() else float('nan'):6.2f}")
        rows[tag] = dict(prom=prom, pp=pp, sel=sel, drv=drv, hit=hit, ei=ei, pks=pks, fs=fs,
                         cell_s=cell.sum() / fs)

    # ---- SPLIT-HALF NULL ON THE STATISTIC ITSELF ------------------------------------------------
    print("\n" + "=" * 102)
    print("SPLIT-HALF NULL ON THE RATIO -- split each route's episodes in half, score half vs half.")
    print("🛑 Any cross-build ratio must clear THIS before it is called a dose-response.")
    rng2 = np.random.default_rng(700)
    nulls = {"pp": [], "sel": []}
    for tag, r in rows.items():
        if not r:
            continue
        eps = np.unique(r["ei"])
        if len(eps) < 4:
            continue
        for _ in range(400):
            sh = rng2.permutation(eps)
            a_, b_ = sh[:len(sh) // 2], sh[len(sh) // 2:]
            ia = np.concatenate([np.flatnonzero(r["ei"] == e) for e in a_])
            ib = np.concatenate([np.flatnonzero(r["ei"] == e) for e in b_])
            for k in ("pp", "sel"):
                pa, pb = np.nanmedian(r[k][ia]), np.nanmedian(r[k][ib])
                if np.isfinite(pa) and np.isfinite(pb) and pb > 0:
                    nulls[k].append(pa / pb)
    bounds = {}
    for k in ("pp", "sel"):
        if nulls[k]:
            bounds[k] = (float(np.percentile(nulls[k], 2.5)), float(np.percentile(nulls[k], 97.5)))
            print(f"  within-route split-half MEDIAN-ratio null on `{k}` (n={len(nulls[k])}): "
                  f"[{bounds[k][0]:.2f}, {bounds[k][1]:.2f}]  median {np.median(nulls[k]):.2f}")
        else:
            bounds[k] = (float("nan"), float("nan"))
            print(f"  `{k}`: too few episodes anywhere to form a split-half null")

    ref = rows.get("r47")
    print("\n  CROSS-BUILD RATIO vs r47 (V67), MEDIAN statistic, episode-bootstrapped.")
    print("  A ratio counts ONLY if its whole CI sits outside the split-half null above.")
    if ref is None:
        print("    r47 is UNPOWERED -- no reference; no ratio can be quoted.")
    else:
        for k, lab in (("pp", "raw 6-9 Hz p-p"), ("sel", "SELECTIVITY 6-9 Hz / 1-4 Hz")):
            base = float(np.nanmedian(ref[k]))
            print(f"\n    -- {lab}   (r47 base median = {base:.3f}, {ref['cell_s']:.1f} s cell)")
            for tag, r in rows.items():
                if not r or tag == "r47":
                    continue
                lo_, hi_ = bootstrap_episodes(r[k], r["ei"],
                                              lambda x: np.nanmedian(x) / base)
                val = float(np.nanmedian(r[k])) / base
                nl, nh = bounds[k]
                verdict = ("CLEARS the null" if np.isfinite(lo_) and (lo_ > nh or hi_ < nl)
                           else "DOES NOT clear the null ⇒ not established")
                print(f"       {tag:>5s} / r47 = {val:5.2f} [{lo_:.2f}, {hi_:.2f}]   {verdict}")
    print("\n  🛑 Route/road/day are NOT controlled. Read any ratio as SUGGESTIVE even if it clears.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
