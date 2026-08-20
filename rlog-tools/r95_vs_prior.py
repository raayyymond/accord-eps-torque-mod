#!/usr/bin/env python3
r"""V101 (route 95) vs V100 (route 85) vs V99 (route 82) -- **DID THE 8x GAIN CAUSE IT?**

🛑 TRAPS OBEYED
  * MATCHED SPEED.  Every ratio is computed inside the SAME km/h bin on both routes, and the
    per-bin speed census is printed.  An unmatched average manufactures a moving wheel order.
  * The SAME estimator on every route: 1 s non-overlapping windows inside contiguous ENGAGED runs,
    band RMS of a brick-wall band-pass computed per run.
  * The CTRL band (2.5-4.5 Hz) is carried through as the negative control on every comparison.
  * Route 85 (V100) has a ~60 s HOLE between segments 16 and 18 -- the whole-route `t` axis is
    discontiguous there.  Windows are cut inside contiguous ENGAGED runs, and a run is broken
    wherever dt > 50 ms, so the hole cannot be spanned.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ROUTES = {"95": ("V101  8x LKAS gain, Lever B removed", "_cache_r95/r95.npz"),
          "85": ("V100  4x gain, Lever B armed", "_cache_r85/r85.npz"),
          "82": ("V99   4x gain, Lever B armed", "_cache_r82/r82.npz")}
BANDS = {"B8": (7.3, 9.3), "B23": (21.5, 25.5), "CTRL": (2.5, 4.5)}
CHANS = ("tq", "rate_f")


def load(stem):
    return dict(np.load(ROOT / "analysis-2020accord" / stem, allow_pickle=True))


def runs_break(mask, t, min_n):
    """Contiguous runs of `mask` with NO sample gap > 50 ms (so a segment hole cannot be spanned)."""
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    o, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > 0.05:
            if prev - s + 1 >= min_n:
                o.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        o.append((s, prev + 1))
    return o


def bandpass_run(x, a, b, FS, lo, hi):
    seg = np.asarray(x[a:b], float)
    seg = np.nan_to_num(seg - np.nanmean(seg))
    X = np.fft.rfft(seg)
    f = np.fft.rfftfreq(len(seg), 1 / FS)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(seg))


TAB = {}
print("=" * 108)
print("SAME-ESTIMATOR WINDOW TABLES")
print("=" * 108)
for r, (lab, stem) in ROUTES.items():
    z = load(stem)
    t = np.asarray(z["t"], float)
    FS = 1.0 / np.median(np.diff(t))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    vk = np.abs(np.asarray(z["cs_v"], float)) * 3.6
    tqs_all = np.abs(np.asarray(z["tq"], float))
    WL = int(round(1.0 * FS))
    rows = []
    for a, b in runs_break(lat, t, WL):
        bp = {(c, bn): bandpass_run(np.asarray(z[c], float), a, b, FS, *br)
              for c in CHANS for bn, br in BANDS.items()}
        for i in range(0, (b - a) - WL + 1, WL):
            sl = slice(i, i + WL)
            rec = dict(v=float(np.median(vk[a:b][sl])),
                       tq_abs=float(np.median(tqs_all[a:b][sl])))
            for c in CHANS:
                for bn in BANDS:
                    rec[f"{c}_{bn}"] = float(np.sqrt(np.mean(bp[(c, bn)][sl] ** 2)))
            rows.append(rec)
    TAB[r] = {k: np.array([x[k] for x in rows], float) for k in rows[0]}
    v = TAB[r]["v"]
    print(f"  route {r}  {lab:44s}  FS {FS:6.2f}  {len(rows):4d} engaged 1 s windows  "
          f"v p10/p50/p90 {np.percentile(v,10):5.1f}/{np.percentile(v,50):5.1f}/"
          f"{np.percentile(v,90):5.1f} km/h  max {v.max():5.1f}")

BINS = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70)]
rng = np.random.default_rng(41)
out = {}

print("\n" + "=" * 108)
print("MATCHED-SPEED BAND RMS.  median over 1 s engaged windows; [ ] = 95 % window bootstrap.")
print("=" * 108)
for c in CHANS:
    for bn in BANDS:
        k = f"{c}_{bn}"
        print(f"\n### {k}")
        print(f"    {'km/h':>10s} " + "".join(f"{'r'+r+' n':>7s}{'  median [95% CI]':>26s}"
                                              for r in ROUTES) +
              f"{'  V101/V100':>13s}{'  V101/V99':>12s}")
        for lo, hi in BINS:
            cells, meds, ns = "", {}, {}
            for r in ROUTES:
                m = (TAB[r]["v"] >= lo) & (TAB[r]["v"] < hi)
                if m.sum() < 5:
                    cells += f"{int(m.sum()):7d}{'      --':>26s}"
                    meds[r] = np.nan
                    ns[r] = int(m.sum())
                    continue
                v = TAB[r][k][m]
                bs = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(2000)]
                l95, h95 = np.percentile(bs, [2.5, 97.5])
                cells += f"{int(m.sum()):7d}{np.median(v):10.1f} [{l95:7.1f},{h95:7.1f}]"
                meds[r] = float(np.median(v))
                ns[r] = int(m.sum())
            r1 = meds["95"] / meds["85"] if np.isfinite(meds.get("85", np.nan)) and \
                np.isfinite(meds["95"]) else np.nan
            r2 = meds["95"] / meds["82"] if np.isfinite(meds.get("82", np.nan)) and \
                np.isfinite(meds["95"]) else np.nan
            print(f"    {lo:4d}-{hi:<5d} " + cells + f"{r1:13.2f}{r2:12.2f}")
            out.setdefault(k, []).append(dict(lo=lo, hi=hi, med=meds, n=ns,
                                              v101_over_v100=float(r1),
                                              v101_over_v99=float(r2)))

# ---- pooled, speed-stratified (weight each bin by the smaller n) ratio with a CI
print("\n" + "=" * 108)
print("POOLED SPEED-STRATIFIED RATIO  V101 / V100  and  V101 / V99")
print("  Bins are pooled as a weighted geometric mean of the per-bin ratios, weight = min(n).")
print("  CI by resampling WINDOWS inside every bin of both routes simultaneously (2000 draws).")
print("=" * 108)
for c in CHANS:
    for bn in BANDS:
        k = f"{c}_{bn}"
        line = f"    {k:9s}"
        rec = {}
        for other in ("85", "82"):
            num, den, boots = [], [], []
            usable = []
            for lo, hi in BINS:
                ma = (TAB["95"]["v"] >= lo) & (TAB["95"]["v"] < hi)
                mb = (TAB[other]["v"] >= lo) & (TAB[other]["v"] < hi)
                if ma.sum() < 5 or mb.sum() < 5:
                    continue
                usable.append((TAB["95"][k][ma], TAB[other][k][mb], min(ma.sum(), mb.sum())))
            if not usable:
                line += f"   vs r{other}: no matched bin"
                continue
            w = np.array([u[2] for u in usable], float)
            pt = np.exp(np.sum(w * np.log([np.median(u[0]) / np.median(u[1]) for u in usable]))
                        / w.sum())
            for _ in range(2000):
                lr = []
                for A, B, _n in usable:
                    lr.append(np.log(np.median(A[rng.integers(0, len(A), len(A))]) /
                                     np.median(B[rng.integers(0, len(B), len(B))])))
                boots.append(np.exp(np.sum(w * np.array(lr)) / w.sum()))
            l95, h95 = np.percentile(boots, [2.5, 97.5])
            line += (f"   V101/{'V100' if other=='85' else 'V99 '} = {pt:5.2f} "
                     f"[{l95:.2f}, {h95:.2f}]{'*' if (l95>1 or h95<1) else ' '}"
                     f" ({len(usable)} bins)")
            rec[other] = dict(ratio=float(pt), lo=float(l95), hi=float(h95),
                              bins=len(usable))
        print(line)
        out.setdefault("pooled", {})[k] = rec

(ROOT / "analysis-2020accord/_cache_r95/r95_vs_prior.json").write_text(
    json.dumps(out, indent=1, default=float))
print(f"\nwrote {ROOT / 'analysis-2020accord/_cache_r95/r95_vs_prior.json'}")
