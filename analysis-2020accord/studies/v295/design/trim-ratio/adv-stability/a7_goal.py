# -*- coding: utf-8 -*-
"""a7_goal.py -- (e) the literal goal metric, cmd -> wheel angular acceleration, closed form with MY inner loop, on EVERY
member x speed, V294 vs b964: |alpha/cmd| at 0.3/0.5/1/2/3/5 Hz, flatness max/min over 0.5-3 Hz, phase spread over
0.5-3 Hz, and the best-flat-gain relative error (how far from alpha = G * cmd).  Does the direction hold across the
family or only on nominal?  (100 Hz ZOH of the command included; small-signal, friction off; open outer loop, i.e. the
firmware's own cmd -> alpha, which is what the goal names.)  Output: a7_goal_out.txt"""
import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adv_lib as A  # noqa: E402
import v294_plant as VP  # noqa: E402

out = open(os.path.join(HERE, "a7_goal_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


WIRE_PER_IDX = 2 ** 22 / (4 * 65025)


def ff_path(c, f, idx=60, m=254):
    z = np.exp(2j * np.pi * f * A.DT)
    zi = 1 / z
    sp_per_idx = (A.lerp(c["map_x"], c["map_y"], idx + 8) - A.lerp(c["map_x"], c["map_y"], idx - 8)) / 16.0
    E = (2 ** c["e_shift"]) * sp_per_idx / WIRE_PER_IDX
    S = (m / 256.0) * E * A.lerp(c["kp_x"], c["kp_y"], idx) / 256.0
    OL = (c["lag_b"] / 1024.0) * (1 + zi) / (32.0 * (1 - (c["lag_a"] / 1024.0) * zi))
    return S * OL * c["gain"] / 32768.0


def alpha_per_cmd(p, c, f):
    s = 2j * np.pi * f
    z = np.exp(s * A.DT)
    Lin = A.inner_L(p, c, f)
    G = A.plant_frf_th(p, f)
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    return s ** 2 * G * z ** (-p.tau_ms) / (1 + Lin) * ff_path(c, f) * zoh100      # deg/s^2 per wire count (magnitude chain)


V294 = A.read_cells("V294")
B964 = A.with_b(V294, 964)
fam = VP.family()
mem = dict(fam)
mem["tau9"] = replace(fam["nominal"], name="tau9", tau_ms=9)
fq = np.array([0.3, 0.5, 1.0, 2.0, 3.0, 5.0])
fb = np.linspace(0.5, 3.0, 60)
P("member v | |a/cmd| 0.3/0.5/1/2/3/5 Hz V294 -> ratio b964 | flatness(0.5-3) V294 -> b964 | phase spread deg | best-flat-G rel err")
agg = []
for nm, mb in mem.items():
    for v in (3.1, 8.0, 12.0, 17.0, 26.9):
        p = mb.at(v)
        a0, a1 = alpha_per_cmd(p, V294, fq), alpha_per_cmd(p, B964, fq)
        h0, h1 = alpha_per_cmd(p, V294, fb), alpha_per_cmd(p, B964, fb)
        fl0, fl1 = np.abs(h0).max() / np.abs(h0).min(), np.abs(h1).max() / np.abs(h1).min()
        ps0 = np.degrees(np.ptp(np.unwrap(np.angle(h0))))
        ps1 = np.degrees(np.ptp(np.unwrap(np.angle(h1))))

        def flat_err(h):
            G = np.vdot(np.ones_like(h), h) / len(h)     # least-squares complex flat gain
            return float(np.sqrt(np.mean(np.abs(h - G) ** 2)) / np.sqrt(np.mean(np.abs(h) ** 2)))
        e0, e1 = flat_err(h0), flat_err(h1)
        agg.append((nm, v, fl0, fl1, ps0, ps1, e0, e1, np.abs(a1) / np.abs(a0)))
        P("%-9s %5.1f | %s -> %s | %.2f -> %.2f | %.0f -> %.0f | %.3f -> %.3f" % (
            nm, v, "/".join("%.3f" % x for x in np.abs(a0)), "/".join("%.2f" % x for x in np.abs(a1) / np.abs(a0)),
            fl0, fl1, ps0, ps1, e0, e1))
P()
fl_better = sum(1 for r in agg if r[3] < r[2])
e_better = sum(1 for r in agg if r[7] < r[6])
ps_better = sum(1 for r in agg if r[5] < r[4])
P("flatness improves (b964 < V294) on %d / %d member-speeds; flat-gain error improves on %d / %d; phase spread on %d / %d" % (
    fl_better, len(agg), e_better, len(agg), ps_better, len(agg)))
P("flat-gain error V294 range %.3f..%.3f  b964 %.3f..%.3f ; median change %+.3f" % (
    min(r[6] for r in agg), max(r[6] for r in agg), min(r[7] for r in agg), max(r[7] for r in agg),
    float(np.median([r[7] - r[6] for r in agg]))))
out.close()
