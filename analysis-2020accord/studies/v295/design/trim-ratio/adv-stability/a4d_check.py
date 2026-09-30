# -*- coding: utf-8 -*-
"""a4d_check.py -- two loose ends from a4: (1) the +4.7 dB 3.61 Hz line that appeared on light_b / lb_mode20_lo at
26.9 m/s HOLD on ONE build per member: measure the 3-4 Hz line prominence for BOTH builds on 4 seeds; (2) FF identity of
MY lane at x = 0 (b964 vs V294 over a random command, 30000 ticks) and the staircase isolation: a hard turn with NO road
noise and NO x noise, delivered HF torque 5-30 Hz and >30 Hz, V294 vs b964.  Output: a4d_out.txt"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a4_core as N  # noqa: E402

out = open(os.path.join(HERE, "a4d_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


def prom(om, f0, fs=100.0):
    f, p = signal.welch(om - om.mean(), fs=fs, nperseg=1024)
    k = int(np.argmin(np.abs(f - f0)))
    sh = ((f >= f0 * 0.6) & (f < f0 * 0.85)) | ((f > f0 * 1.15) & (f <= f0 * 1.5))
    cf = np.polyfit(np.log(f[sh]), np.log(p[sh] + 1e-30), 1)
    return 10 * np.log10(p[k] / np.exp(np.polyval(cf, np.log(f[k]))))


names = ["light_b", "lb_mode20_lo", "nominal"]
P("(1) HOLD 26.9 m/s, 60 s, prominence dB at 3.61 Hz and at 1.27 Hz, per seed: V294 | b964")
for sd in range(4):
    cl = [N.V294] * 3 + [N.B964] * 3
    mm = [N.MEM[k] for k in names] * 2
    B = 6
    secs = 60.0
    rng = np.random.default_rng(900 + sd)
    bb, aa = signal.butter(2, [0.05 / 50, 0.5 / 50], btype="band")
    w = signal.lfilter(bb, aa, rng.normal(size=int(secs * 100)))
    w = w / w.std() * 0.05
    sp_ = np.repeat(w[None], B, 0)
    r = N.run(cl, mm, 26.9, sp_, np.gradient(sp_, axis=1) * 100, N.road(B, int(secs * 1000), 15.0, 950 + sd), secs, seed=990 + sd)
    for j, nm in enumerate(names):
        a = [prom(r["om"][j, 500:], f0) for f0 in (3.61, 1.27)]
        b = [prom(r["om"][j + 3, 500:], f0) for f0 in (3.61, 1.27)]
        P("  seed %d %-12s 3.61 Hz %+.1f | %+.1f   1.27 Hz %+.1f | %+.1f" % (sd, nm, a[0], b[0], a[1], b[1]))

P()
P("(2a) FF identity of MY lane at x = 0: b964 vs V294, 30000 ticks, random command")
L = N.A.IntLane([N.V294, N.B964])
rng = np.random.default_rng(4)
mism = 0
for i in range(30000):
    k = int(abs(np.cumsum([0])[0]) + (i // 50) % 240)
    sp = int(L.map_tab[0][k]) * (1 if (i // 3000) % 2 else -1)
    T = L.tick(0, sp, k, 254)
    mism += int(T[0] != T[1])
P("  mismatches", mism)
P("(2b) staircase isolation: hard turn 8 and 17 m/s, NO road noise, NO x noise; delivered T rms 5-30 Hz and 30-120 Hz")
for v, Aacc in ((8.0, 2.0), (17.0, 2.5)):
    secs = 16.0
    t = np.arange(int(secs * 100)) / 100.0
    spt = np.zeros_like(t)
    for t0, sgn in ((1.0, 1), (8.0, -1)):
        spt += sgn * Aacc * np.clip((t - t0) / 1.0, 0, 1) * (1 - np.clip((t - t0 - 4.0) / 1.0, 0, 1))
    nm2 = ["nominal", "light_b", "mode20_lo", "lb_mode20_lo"]
    cl = [N.V294] * 4 + [N.B964] * 4
    mm = [N.MEM[k] for k in nm2] * 2
    sp_ = np.repeat(spt[None], 8, 0)
    import a4_core as NN
    old = NN.Plant.__init__

    r = N.run(cl, mm, v, sp_, np.gradient(sp_, axis=1) * 100, np.zeros((8, int(secs * 1000))), secs, seed=1)
    for j, nm in enumerate(nm2):
        vals = []
        for off in (0, 4):
            T1 = r["T1k"][j + off].astype(float)
            vals.append((N.rms(N.bp(T1[None], 5, 30, fs=1000.0)[0][500:-500]), N.rms(N.bp(T1[None], 30, 120, fs=1000.0)[0][500:-500])))
        P("  v %4.1f %-12s 5-30 Hz %.2f -> %.2f  30-120 Hz %.2f -> %.2f" % (v, nm, vals[0][0], vals[1][0], vals[0][1], vals[1][1]))
out.close()
