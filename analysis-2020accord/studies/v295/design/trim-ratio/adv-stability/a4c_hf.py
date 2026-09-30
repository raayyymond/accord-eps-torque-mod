# -*- coding: utf-8 -*-
"""a4c_hf.py -- follow-up of a4: the hard-turn HF delivered-torque ratios x1.5-2.4 on lb_mode20_lo at 17 m/s.  Absolute
levels, and the 10-30 Hz WHEEL-RATE line (the grinding signature) on the 1 kHz om, V294 vs b964, for the flexible stress
members at their nominal 2 ms AND at the delays where a2 found the trim anti-damping (6, 9 ms).  3 seeds.
Output: a4c_out.txt"""
import os
import sys
from dataclasses import replace

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a4_core as N  # noqa: E402

out = open(os.path.join(HERE, "a4c_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


nom = N.fam["nominal"]
lb = N.fam["light_b"]
MEM = {}
for tau in (2, 6, 9):
    MEM["mode20_lo_t%d" % tau] = replace(nom.with_mode20(20.0, 0.02, 0.5), name="m20lo_t%d" % tau, tau_ms=tau)
    MEM["lb_mode20_lo_t%d" % tau] = replace(lb.with_mode20(20.0, 0.02, 0.5), name="lbm20lo_t%d" % tau, tau_ms=tau)
    MEM["mode16_lo_t%d" % tau] = replace(nom.with_mode20(16.5, 0.02, 0.5), name="m16lo_t%d" % tau, tau_ms=tau)
names = list(MEM)


def line(om, fs=1000.0, lo=10.0, hi=30.0):
    f, p = signal.welch(om - om.mean(), fs=fs, nperseg=2048)
    m = (f >= lo) & (f <= hi)
    k = np.flatnonzero(m)[int(np.argmax(p[m]))]
    sh = ((f >= 6) & (f < lo)) | ((f > hi) & (f <= 45))
    cf = np.polyfit(np.log(f[sh]), np.log(p[sh] + 1e-30), 1)
    return float(f[k]), float(10 * np.log10(p[k] / np.exp(np.polyval(cf, np.log(f[k]))))), float(np.sqrt(np.trapezoid(p[m], f[m])))


for scen, v, Aacc in (("turn", 17.0, 2.5), ("turn", 8.0, 2.0), ("hold", 17.0, 0.0), ("hold", 5.0, 0.0)):
    secs = 16.0
    t = np.arange(int(secs * 100)) / 100.0
    if scen == "turn":
        spt = np.zeros_like(t)
        for t0, sgn in ((1.0, 1), (8.0, -1)):
            spt += sgn * Aacc * np.clip((t - t0) / 1.0, 0, 1) * (1 - np.clip((t - t0 - 4.0) / 1.0, 0, 1))
    else:
        spt = 0.05 * np.sin(2 * np.pi * 0.2 * t)
    acc = {}
    for sd in range(3):
        cl = [N.V294] * len(names) + [N.B964] * len(names)
        mm = [MEM[k] for k in names] * 2
        B = len(cl)
        sp_ = np.repeat(spt[None], B, 0)
        jk = np.gradient(sp_, axis=1) * 100
        r = N.run(cl, mm, v, sp_, jk, N.road(B, int(secs * 1000), 15.0, 40 + sd), secs, seed=50 + sd)
        nn = len(names)
        for j, nm in enumerate(names):
            for c, off in enumerate((0, nn)):
                T1 = r["T1k"][j + off].astype(float)
                om = r["om1k"][j + off].astype(float)[1000:]
                hf = [N.rms(N.bp(T1[None], lo, hi, fs=1000.0)[0][500:-500]) for lo, hi in ((5, 9), (9, 13), (13, 17), (17, 23), (23, 30))]
                ln = line(om)
                acc.setdefault((nm, c), []).append((hf, ln, N.rms(N.bp(om[None], 10.0, 30.0, fs=1000.0)[0][500:-500])))
    P("=== %s v %.0f A %.1f (3 seeds): member | HF T rms 5-9/9-13/13-17/17-23/23-30 V294 -> b964 | 10-30 Hz rate line f/dB, rms(10-30) V294 -> b964" % (scen, v, Aacc))
    for nm in names:
        a = acc[(nm, 0)]
        b = acc[(nm, 1)]
        ha = np.mean([x[0] for x in a], 0)
        hb = np.mean([x[0] for x in b], 0)
        la = np.mean([x[1] for x in a], 0)
        lb_ = np.mean([x[1] for x in b], 0)
        ra = np.mean([x[2] for x in a])
        rb = np.mean([x[2] for x in b])
        P("  %-18s %s -> %s | %.1fHz %+.1fdB %.3f -> %.1fHz %+.1fdB %.3f  (rms10-30 %.3f -> %.3f x%.2f)" % (
            nm, "/".join("%.2f" % x for x in ha), "/".join("%.2f" % x for x in hb), la[0], la[1], la[2], lb_[0], lb_[1], lb_[2],
            ra, rb, rb / max(ra, 1e-9)))
out.close()
