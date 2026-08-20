#!/usr/bin/env python3
r"""V102 PRE-REGISTRATION -- the numbers behind the readout spec.

🛑 The operator will give ~15-30 s of engaged, symptomatic frames -- ONE episode.  A cross-build
ratio needs matched exposure on two routes and is therefore FRAGILE.  A **WITHIN-ROUTE SHAPE
RATIO** -- band RMS in the target band divided by band RMS in a control band, on the SAME frames --
needs no cross-route normalisation, no matched speed distribution, and no matched driver behaviour.
This script measures it on V101 (r95) and V100 (r85), and then does an honest POWER CALCULATION by
subsampling to the exposure V102 will actually get.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

BANDS = {"B23": (21.5, 25.5), "B8": (7.3, 9.3), "CTRL": (2.5, 4.5), "HI": (32.0, 38.0)}
ROUTES = {"95": ("V101 8x, Lever B OUT", "_cache_r95/r95.npz"),
          "85": ("V100 4x, Lever B IN", "_cache_r85/r85.npz")}
out = {}


def runs_break(mask, t, min_n):
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


def bp(x, a, b, FS, lo, hi):
    seg = np.nan_to_num(np.asarray(x[a:b], float) - np.nanmean(x[a:b]))
    X = np.fft.rfft(seg)
    f = np.fft.rfftfreq(len(seg), 1 / FS)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(seg))


TAB = {}
for r, (lab, stem) in ROUTES.items():
    z = dict(np.load(ROOT / "analysis-2020accord" / stem, allow_pickle=True))
    t = np.asarray(z["t"], float)
    FS = 1.0 / np.median(np.diff(t))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    vk = np.abs(np.asarray(z["cs_v"], float)) * 3.6
    WL = int(round(1.0 * FS))
    rows = []
    for a, b in runs_break(lat, t, WL):
        B = {(c, bn): bp(np.asarray(z[c], float), a, b, FS, *br)
             for c in ("tq", "rate_f") for bn, br in BANDS.items()}
        for i in range(0, (b - a) - WL + 1, WL):
            sl = slice(i, i + WL)
            rec = {"v": float(np.median(vk[a:b][sl]))}
            for c in ("tq", "rate_f"):
                for bn in BANDS:
                    rec[f"{c}_{bn}"] = float(np.sqrt(np.mean(B[(c, bn)][sl] ** 2)))
            rows.append(rec)
    TAB[r] = {k: np.array([x[k] for x in rows], float) for k in rows[0]}
    print(f"route {r} ({lab}): {len(rows)} engaged 1 s windows, FS {FS:.2f}")

# ======================================================================================
print("\n" + "=" * 100)
print("1. THE WITHIN-ROUTE SHAPE RATIO  --  band RMS(target) / band RMS(control), SAME frames.")
print("   No cross-route normalisation, no matched speed, no matched driver behaviour.")
print("=" * 100)
rng = np.random.default_rng(101)
BINS = [(0, 20), (20, 40), (40, 70)]
for c in ("tq", "rate_f"):
    for tgt, ctl in (("B23", "CTRL"), ("B23", "HI"), ("B8", "CTRL")):
        print(f"\n### {c}   shape = {tgt} / {ctl}")
        print(f"    {'km/h':>9s} " + "".join(f"{'r'+r:>9s}{'  n':>5s}{'   shape [95% CI]':>26s}"
                                            for r in ROUTES))
        for lo, hi in BINS:
            line = f"    {lo:3d}-{hi:<5d} "
            rec = {"lo": lo, "hi": hi}
            for r in ROUTES:
                m = (TAB[r]["v"] >= lo) & (TAB[r]["v"] < hi)
                if m.sum() < 6:
                    line += f"{'':>9s}{int(m.sum()):5d}{'   --':>26s}"
                    continue
                a = TAB[r][f"{c}_{tgt}"][m]
                b = TAB[r][f"{c}_{ctl}"][m]
                s = np.median(a / b)
                bs = [np.median((a / b)[rng.integers(0, len(a), len(a))]) for _ in range(3000)]
                l95, h95 = np.percentile(bs, [2.5, 97.5])
                line += f"{'':>9s}{int(m.sum()):5d}{s:10.2f} [{l95:6.2f},{h95:6.2f}]"
                rec[r] = dict(n=int(m.sum()), shape=float(s), lo95=float(l95), hi95=float(h95))
            print(line)
            out.setdefault(f"shape_{c}_{tgt}_over_{ctl}", []).append(rec)

# ======================================================================================
print("\n" + "=" * 100)
print("2. 🛑 POWER CALCULATION -- ONE EPISODE.  Subsample N CONSECUTIVE 1 s windows from a single")
print("   contiguous stretch of r95 (V101) and r85 (V100) and re-estimate the shape ratio.")
print("   Reported: median estimate and the 10-90 % spread of the ESTIMATE across 2000 draws,")
print("   plus the fraction of draws whose 95 % CI would EXCLUDE the other build's value.")
print("=" * 100)
for c, tgt, ctl in (("tq", "B23", "CTRL"), ("rate_f", "B23", "CTRL"), ("tq", "B8", "CTRL")):
    a95 = TAB["95"][f"{c}_{tgt}"] / TAB["95"][f"{c}_{ctl}"]
    a85 = TAB["85"][f"{c}_{tgt}"] / TAB["85"][f"{c}_{ctl}"]
    full95, full85 = float(np.median(a95)), float(np.median(a85))
    print(f"\n### {c} {tgt}/{ctl}   FULL-ROUTE: V101 {full95:.2f}  (n={len(a95)})   "
          f"V100 {full85:.2f} (n={len(a85)})   separation {full95/full85:.1f}x")
    print(f"    {'N windows':>10s} {'sec':>5s} | {'V101 est p10':>13s} {'p50':>7s} {'p90':>7s} | "
          f"{'V100 est p50':>13s} | {'P(V101 draw CI excludes V100 median)':>38s}")
    for N in (15, 20, 25, 30, 45, 60):
        est95, excl = [], 0
        for _ in range(2000):
            i0 = rng.integers(0, max(1, len(a95) - N))
            s = a95[i0:i0 + N]
            if len(s) < N:
                continue
            e = float(np.median(s))
            est95.append(e)
            bs = [np.median(s[rng.integers(0, N, N)]) for _ in range(200)]
            if np.percentile(bs, 2.5) > full85:
                excl += 1
        est85 = []
        for _ in range(2000):
            i0 = rng.integers(0, max(1, len(a85) - N))
            s = a85[i0:i0 + N]
            if len(s) == N:
                est85.append(float(np.median(s)))
        p = excl / max(len(est95), 1)
        print(f"    {N:10d} {N:5d} | {np.percentile(est95,10):13.2f} "
              f"{np.percentile(est95,50):7.2f} {np.percentile(est95,90):7.2f} | "
              f"{np.percentile(est85,50):13.2f} | {p*100:37.1f} %")
        out.setdefault(f"power_{c}_{tgt}", []).append(
            dict(N=N, v101_p10=float(np.percentile(est95, 10)),
                 v101_p50=float(np.percentile(est95, 50)),
                 v101_p90=float(np.percentile(est95, 90)),
                 v100_p50=float(np.percentile(est85, 50)), p_decisive=float(p)))

# ======================================================================================
print("\n" + "=" * 100)
print("3. THE PEAK-FREQUENCY ENDPOINT -- how many seconds to resolve 21.7 vs 23.4 Hz?")
print("   A 1.7 Hz separation needs df << 1.7 Hz.  Welch nfft=N at 100 Hz gives df = 100/N.")
print("=" * 100)
for T in (4, 8, 15, 20, 30):
    n = int(T * 100)
    print(f"    {T:3d} s single window: df = {100.0/n:6.3f} Hz   "
          f"separation 1.7 Hz = {1.7/(100.0/n):6.1f} bins   "
          f"{'RESOLVABLE' if 1.7/(100.0/n) >= 4 else 'MARGINAL'}")
print("    ⇒ even ONE 8 s engaged stretch resolves the frequency endpoint; 15-30 s is ample.")
print("    ⚠ The -3 dB WIDTH endpoint is harsher: V101's width is 0.49 Hz = 5 bins at nfft=1024")
print("      (10.2 s).  Measuring a width needs >= 10 s of CONTIGUOUS symptomatic frames in one")
print("      window, and a Q RATIO needs that on both builds.")

(ROOT / "analysis-2020accord/_cache_r95/r95_v102_prereg.json").write_text(
    json.dumps(out, indent=1, default=float))
print(f"\nwrote {ROOT / 'analysis-2020accord/_cache_r95/r95_v102_prereg.json'}")
