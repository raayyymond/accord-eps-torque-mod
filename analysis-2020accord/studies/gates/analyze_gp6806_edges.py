#!/usr/bin/env python3
"""Two controls on the gp-0x6806 gate result.

(1) Are the ~25 probe-vs-proxy disagreements SKEW (sitting on an engagement edge) or real?
(2) Is the "15.04 Hz, prominence 2.80x" peak a real line, or Hann leakage from the step edges?
    Control: replace the measured bit with a SYNTHETIC square wave having the SAME edge times.
    If the synthetic reproduces the same peak/prominence, the peak is leakage.
"""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
FS = 100.0
SEGS = [("r28", s) for s in (10, 11, 12, 13, 14)] + [("r29", s) for s in (0, 1)]


def welch(x, nfft=512):
    x = np.asarray(x, float) - np.mean(x)
    w = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / FS)
    acc, k = np.zeros(len(f)), 0
    for i in range(0, len(x) - nfft + 1, nfft // 2):
        acc += np.abs(np.fft.rfft(x[i:i + nfft] * w)) ** 2
        k += 1
    return f, acc / k, k


print("=" * 96)
print("(1) DISAGREEMENT FRAMES vs distance to the nearest latActive / SCA edge")
tot = {"lat": [], "sca": []}
for rt, s in SEGS:
    z = np.load(ROOT / f"_cache_{rt}" / f"{rt}s{s}.npz")
    nz = (z["probe"].astype(int) & 0x40) == 0          # gp-0x6806 != 0
    for nm, ref in (("lat", z["cc_lat"] > 0.5), ("sca", z["sca"].astype(int) == 1)):
        bad = np.flatnonzero(nz != ref)
        edges = np.flatnonzero(np.diff(ref.astype(int)) != 0)
        if len(bad) == 0:
            continue
        dist = np.array([np.min(np.abs(edges - b)) if len(edges) else 9999 for b in bad])
        tot[nm].extend(dist.tolist())
        print(f"  {rt}s{s:<3} vs {nm}: {len(bad):3d} disagreements, "
              f"edges={len(edges)}, distance-to-edge (frames): {sorted(dist.tolist())}")
for nm, dl in tot.items():
    d = np.array(dl)
    print(f"  POOLED {nm}: n={len(d)}  within 1 frame of an edge: {int((d <= 1).sum())}  "
          f"within 3: {int((d <= 3).sum())}  max distance: {d.max() if len(d) else 0}")

print()
print("=" * 96)
print("(2) LEAKAGE CONTROL -- measured bit vs a synthetic square with IDENTICAL edge times")
print(f"  {'seg':8s} {'trans':>6s} | {'meas 15-50 pk':>14s} {'@Hz':>7s} {'prom':>7s} | "
      f"{'synth 15-50 pk':>15s} {'@Hz':>7s} {'prom':>7s}")
for rt, s in SEGS:
    z = np.load(ROOT / f"_cache_{rt}" / f"{rt}s{s}.npz")
    x = ((z["probe"].astype(int) & 0x40) == 0).astype(float)
    tr = int((np.diff(x) != 0).sum())
    if x.std() == 0:
        print(f"  {rt}s{s:<5} {tr:6d} | bit constant -- no spectrum")
        continue
    out = []
    for y in (x, x.copy()):        # identical by construction: the synthetic IS the edge train
        f, P, K = welch(y)
        hb = (f >= 15) & (f <= 50)
        j = int(np.argmax(np.where(hb, P, -np.inf)))
        med = np.median(P[(f >= 5) & (f <= 50)])
        out.append((P[j], f[j], P[j] / med if med > 0 else np.nan))
    # true synthetic: an ideal step train with the same transition sample indices
    idx = np.flatnonzero(np.diff(x) != 0) + 1
    y = np.zeros_like(x)
    lvl = x[0]
    prev = 0
    for i in idx:
        y[prev:i] = lvl
        lvl = 1 - lvl
        prev = i
    y[prev:] = lvl
    f, P, K = welch(y)
    hb = (f >= 15) & (f <= 50)
    j = int(np.argmax(np.where(hb, P, -np.inf)))
    med = np.median(P[(f >= 5) & (f <= 50)])
    print(f"  {rt}s{s:<5} {tr:6d} | {out[0][0]:14.5g} {out[0][1]:7.2f} {out[0][2]:7.2f} | "
          f"{P[j]:15.5g} {f[j]:7.2f} {P[j]/med if med>0 else np.nan:7.2f}   "
          f"(identical => the peak IS the edge train, i.e. leakage)")

print()
print("  TOTAL transitions and duration, pooled:")
T, D = 0, 0.0
for rt, s in SEGS:
    z = np.load(ROOT / f"_cache_{rt}" / f"{rt}s{s}.npz")
    x = ((z["probe"].astype(int) & 0x40) == 0).astype(int)
    T += int((np.diff(x) != 0).sum())
    D += z["t"][-1] - z["t"][0]
print(f"    {T} transitions over {D:.1f} s  =>  {T/D:.4f} transitions/s  "
      f"=>  equivalent square-wave fundamental {T/(2*D):.4f} Hz")
