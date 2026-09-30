# -*- coding: utf-8 -*-
"""rj1_route_facts.py -- lens robust-joint: facts about r71b the search needs (EVIDENCE, the harness's route cache).
  * |0xE4| and idx distribution on laterally engaged frames, by speed band (how often a raised FF gain would reach the
    P-clamp rail earlier; where the Kp schedule's knots should sit)
  * the engaged command's 0.3-8 Hz spectrum (the weight for the closed-form tracking proxy), saved to npz
  * the V294 fb operand r26 distribution on the drive (the byte-exact march, plib): how close C = 1024 is to binding
ANALYSIS ONLY."""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import v295_harness as H  # noqa: E402


def main():
    d = H.route()
    eng = d["eng"] & (d["cc_lat_active_f"] > 0.5)
    w = d["e4_f"].astype(float)
    v = d["v"]
    idx = d["idx"]
    print("engaged frames %d (%.0f s)" % (eng.sum(), eng.sum() / 100))
    print("band      s    |wire| p50  p90  p99  p99.9  max | idx p50 p90 p99 max | frac |wire|>2000 >2500 >3000 >3500")
    for nm, lo, hi in H.BANDS + (("all", 0, 99),):
        m = eng & (v >= lo) & (v < hi)
        a = np.abs(w[m])
        ii = idx[m]
        print("%-6s %6.0f  %5.0f %5.0f %5.0f %6.0f %5.0f | %3d %3d %3d %3d | %.4f %.4f %.4f %.4f"
              % (nm, m.sum() / 100, *np.percentile(a, [50, 90, 99, 99.9]), a.max(), *np.percentile(ii, [50, 90, 99]).astype(int),
                 ii.max(), np.mean(a > 2000), np.mean(a > 2500), np.mean(a > 3000), np.mean(a > 3500)))
    # command spectrum over hands-off chunks
    ch = H.route_chunks()
    P, f = 0, None
    for a, b in ch:
        x = w[a:b] - np.mean(w[a:b])
        f, p = signal.welch(x, fs=100.0, nperseg=512)
        P = P + p * (b - a)
    P = P / sum(b - a for a, b in ch)
    np.savez(os.path.join(HERE, "rj1_cmd_psd.npz"), f=f, P=P)
    for lo, hi in ((0.1, 0.3), (0.3, 1), (1, 3), (3, 8), (8, 20)):
        mm = (f >= lo) & (f < hi)
        print("cmd rms %4.1f-%4.1f Hz: %.1f counts" % (lo, hi, np.sqrt(np.trapezoid(P[mm], f[mm]))))
    # r26 on the drive (V294 march, byte-exact): distribution
    L = H.Lane([H.Cells.v294()])
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    sp = d["sgn"].astype(np.int64) * L.map_tab[0, d["idx"]]
    n = len(x1k)
    r26 = np.zeros(n, np.int64)
    for i in range(n):
        k = i // 10
        _, r = L.tick(x1k[i:i + 1], sp[k:k + 1], d["idx"][k:k + 1], d["m"][k:k + 1])
        r26[i] = r[0]
    e1k = np.repeat(eng, 10)[:n]
    a = np.abs(r26[e1k])
    print("V294 |r26| on engaged ticks: p50 %d p99 %d p99.9 %d p99.99 %d max %d  (C = 1024)"
          % tuple(np.percentile(a, [50, 99, 99.9, 99.99]).astype(int).tolist() + [a.max()]))
    for k in (1.5, 2, 3, 4):
        print("   if r26 scaled x%.1f: frac engaged ticks > 1024: %.5f, > 2048: %.5f" % (k, np.mean(a * k > 1024), np.mean(a * k > 2048)))


if __name__ == "__main__":
    main()
