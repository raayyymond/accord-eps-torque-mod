#!/usr/bin/env python3
"""Exposure-matched cross-build comparison, and where V62's extreme jumps actually are.

Two things the raw census in analyze_r37_crossbuild_hf.py cannot settle:

  1. Are V62's 28 samples with |d(tq)|>2500 spread across the route, or all inside one burst?
     One burst means n_independent = 1, and the cross-build claim is "one event vs zero", not a
     rate comparison. This is the difference between a strong result and a suggestive one.
  2. Is V62's route simply more exposed to the provoking regime (hard manual turn, low speed,
     LKAS engaged)? If route 37 is the only route that spent time there, a null on the others is
     uninformative.

Both are answered by counting, not by spectra.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r31_common as C  # noqa: E402

ROUTES = [
    ("2b", C.ROOT / "_cache_r2b", "r2bs", [0, 1, 2, 11, 12, 13]),
    ("2c", C.ROOT / "_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    ("31 (V61)", C.ROOT / "_cache_r31", "r31s", [0, 1, 2, 3]),
    ("35 (V64=V59)", C.ROOT / "_cache_r35", "r35s", [0, 1, 2]),
    ("37 (V62)", C.ROOT / "_cache_r37", "r37s", list(range(1, 15))),
]


def main():
    # ---- 1. where are V62's extreme jumps? --------------------------------------------------
    print("V62 route 37: every sample with |d(tq)| > 1500, grouped into events (gap > 1 s).")
    ev = []
    for s in range(1, 15):
        d = C.load(s, C.ROOT / "_cache_r37", "r37s")
        j = np.flatnonzero(np.abs(np.diff(d["tq"])) > 1500)
        for k in j:
            ev.append((s, float(d["t"][k]), float(abs(np.diff(d["tq"])[k])),
                       float(d["cs_v"][k]), float(abs(d["ang"][k])),
                       float(d["cc_lat"][k]), float(abs(d["e4tq"][k]))))
    groups, cur = [], None
    for e in ev:
        if cur and e[0] == cur[-1][0] and e[1] - cur[-1][1] < 1.0:
            cur.append(e)
        else:
            if cur:
                groups.append(cur)
            cur = [e]
    if cur:
        groups.append(cur)
    print(f"  {len(ev)} samples in {len(groups)} events")
    print("   seg   t_start..t_end    n   max|djump|  n>2500   v      |ang|  lat   |e4|")
    for g in groups:
        print(f"   {g[0][0]:3d}  {g[0][1]:6.2f}..{g[-1][1]:6.2f}  {len(g):4d} "
              f"{max(x[2] for x in g):10.0f} {sum(1 for x in g if x[2]>2500):7d} "
              f"{np.mean([x[3] for x in g]):6.2f} {np.mean([x[4] for x in g]):6.1f} "
              f"{np.mean([x[5] for x in g]):5.2f} {np.mean([x[6] for x in g]):6.0f}")

    # ---- 2. exposure to the provoking regime -------------------------------------------------
    print("\nEXPOSURE: seconds spent in each regime, per route (LKAS engaged throughout).")
    print(f"{'route':14s} {'total s':>8s} {'eng s':>7s} | "
          f"{'v<4 & |ang|>90':>15s} {'v<4 & eff>2000':>15s} {'v 3.5-10 & eff>800':>19s} "
          f"{'|e4| sat':>9s}")
    for name, cache, pfx, segs in ROUTES:
        tot = eng = a = b = c = sat = 0.0
        for s in segs:
            f = cache / f"{pfx}{s}.npz"
            if not f.exists():
                continue
            d = C.load(s, cache, pfx)
            fs = C.fs_of(d)
            dt = 1.0 / fs
            le = d["cc_lat"] > 0.5
            eff = C.sustained(d["tq"], fs)
            v, ang = d["cs_v"], np.abs(d["ang"])
            tot += len(v) * dt
            eng += le.sum() * dt
            a += (le & (v < 4) & (ang > 90)).sum() * dt
            b += (le & (v < 4) & (eff > 2000)).sum() * dt
            c += (le & (v >= 3.5) & (v < 10) & (eff > 800)).sum() * dt
            sat += (le & (np.abs(d["e4tq"]) >= 4090)).sum() * dt
        print(f"{name:14s} {tot:8.1f} {eng:7.1f} | {a:15.1f} {b:15.1f} {c:19.1f} {sat:9.1f}")

    # ---- 3. the same census, restricted to the matched regime --------------------------------
    print("\nMATCHED-REGIME census: 26-45 Hz envelope, windows entirely inside "
          "(engaged & v<4 & |ang|>90).")
    print(f"{'route':14s} {'nwin':>5s} {'p50':>7s} {'p90':>7s} {'max':>8s} {'>900':>5s} "
          f"{'maxjump':>8s}")
    for name, cache, pfx, segs in ROUTES:
        vals, jm, n = [], 0.0, 0
        for s in segs:
            f = cache / f"{pfx}{s}.npz"
            if not f.exists():
                continue
            d = C.load(s, cache, pfx)
            fs = C.fs_of(d)
            m = (d["cc_lat"] > 0.5) & (d["cs_v"] < 4) & (np.abs(d["ang"]) > 90)
            for aa, bb in C.runs_of(m, d["t"], 256):
                x = d["tq"][aa:bb]
                e = C.band_envelope(x, fs, 26.0, 45.0)
                for i in range(0, len(x) - 256 + 1, 64):
                    vals.append(float(np.percentile(e[i:i + 256], 99)))
                    jm = max(jm, float(np.max(np.abs(np.diff(x[i:i + 256])))))
                    n += 1
        if not vals:
            print(f"{name:14s} {0:5d}   (no window fits the regime)")
            continue
        v = np.array(vals)
        print(f"{name:14s} {n:5d} {np.median(v):7.1f} {np.percentile(v,90):7.1f} {v.max():8.1f} "
              f"{int((v>900).sum()):5d} {jm:8.0f}")


if __name__ == "__main__":
    main()
