# -*- coding: utf-8 -*-
r"""rb_explore_ki.py -- C3 rev2-B EXPLORATION (not a gate): how large may the PI corner be, per speed, before GATE 2
fails at the curve OPERATING POINT (k * sech^2(theta_op / sat(v))), on every gated member, frame and hold offset?

ANALYSIS ONLY.  Uses the C3-r1 STABILITY refuter's independent model (refute_stability/c3r1/c3r1_model.py) UNCHANGED:
its Design(kp, ki, kd, rows) with the C3-P G table, its member(), plant_channels(), controller(), Kout(), pm_gm().
Only `ki` is varied (the cal 0xC63E6: I += (e5 * Ki) >> 3, e5 = E' >> 5  ->  PI corner = 3.906 * Ki / 56 rad/s).

For every (member, v, a, frame, e) it records the PID-loop PM at Ki in KIS; the bar is the refuter's: native-age singles
45 deg, aged singles + combined 30 deg.  Output: per speed, the largest Ki on the list that passes every point, and the
binding point.  -> _scratch/angle_loop/c3-rev2B/explore_ki.json / explore_ki.txt
usage: python rb_explore_ki.py [design C3-P|C3-F]"""
import json
import math
import os
import sys
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
RS = HERE.parents[1] / "refute_stability" / "c3r1"
sys.path.insert(0, str(RS))
import c3r1_model as M  # noqa: E402
import c3r1_sweep as S  # noqa: E402

OUT = M.KIT / "_scratch" / "angle_loop" / "c3-rev2B"
OUT.mkdir(parents=True, exist_ok=True)
DN = sys.argv[1] if len(sys.argv) > 1 else "C3-P"
D0 = M.designs()[DN]
KIS = (4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80)
AS = (0.0, 1.0, 1.5, 2.0, 2.5)
SP = sorted(set([round(x, 2) for x in np.arange(3.0, 35.01, 0.5)] + [3.1, 8.0, 11.9, 17.0, 26.9, 11.25, 11.75, 12.25]))
FRS = [f for f in S.FRAMES if f[0] in ("nom", "FA.83", "FA1.155", "FB.83", "FB1.155", "FAo", "FBo")]
MEMS = S.SINGLE + S.COMBINED
ES = (-1, 0, 10)
F = S.F
SR, LWB = 16.0, 2.83


def sat(v):
    return 19.3 + 546.0 * math.exp(-v / 3.01)


def theta_op(v, a):
    return min(SR * LWB * a / (v * v) * 180 / math.pi, 470.0) if a > 0 else 0.0


def bar(mem, e):
    if mem in S.SINGLE:
        return 45.0 if e <= 0 else 30.0
    return 30.0


def work(args):
    mem, v = args
    res = []
    for a in AS:
        th = theta_op(v, a)
        s2 = 1 - math.tanh(th / sat(v)) ** 2
        pl = M.member(mem, v)
        pl.k = pl.k * s2
        chans = {}
        for fn, kap, jb in FRS:
            if jb not in chans:
                chans[jb] = M.plant_channels(pl, F, jb, 0.0)
            Pt, Pw = chans[jb]
            for e in ES:
                for ki in KIS:
                    d = replace(D0, ki=float(ki))
                    Cth, Cw, Cref = M.controller(d, v, F, e, kap)
                    L = -M.Kout(F) * (Cth * Pt + Cw * Pw)
                    PM, FC, GM = M.pm_gm(L, F)
                    res.append((mem, v, a, fn, e, ki, PM, FC, GM, bar(mem, e)))
    return res


if __name__ == "__main__":
    jobs = [(m, v) for m in MEMS for v in SP]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=2) for r in rr]
    json.dump(R, open(OUT / f"explore_ki_{DN}.json", "w"))
    out = [f"{DN}: largest Ki (of {KIS}) passing every gated point at the curve operating point, per speed "
           f"(a in {AS}; frames {[f[0] for f in FRS]}; e {ES}; bars 45 native singles / 30 others; GM >= 6 dB)"]
    for v in SP:
        X = [r for r in R if r[1] == v]
        best = None
        for ki in KIS:
            Y = [r for r in X if r[5] == ki]
            ok = all(r[6] >= r[9] and r[8] >= 6.0 for r in Y)
            if ok:
                best = ki
        nxt = [k for k in KIS if best is None or k > best]
        why = ""
        if nxt:
            Y = [r for r in X if r[5] == nxt[0]]
            w = min(Y, key=lambda r: r[6] - r[9])
            why = f"  first fail at Ki {nxt[0]}: {w[0]} a{w[2]} {w[3]} e{w[4]} PM {w[6]:.1f} (bar {w[9]}) GM {w[8]:.1f}"
        out.append(f"v {v:5.2f}  G {D0.G(v):5d}  max Ki {best}" + why)
    (OUT / f"explore_ki_{DN}.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
