# -*- coding: utf-8 -*-
"""s12_heavyJ_turns.py -- adversary `stability`: second method for the F-e finding (heavy-J members, medium speed).
My own nonlinear engine (s7: my lane, my plant, the fork port) on synthetic hard turns, heavy-J members only:
J_hi (J 0.5 refitted), J_hi2 (0.8 refitted), nom_J0.5nr (nominal b/k/F, J 0.5 not refitted), nominal as the control.
6 runs (seed 0 noise-free); the harness-style hard-turn mask (|plan| >= 1.5 m/s^2 frames) 1.6-3 Hz rate, A1017/V294."""
import os
import sys
from dataclasses import replace

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s7_closedloop as S7  # noqa: E402

H = S7.H


def members():
    fam = H.family()
    nom = fam["nominal"]
    return {"nominal": nom, "J_hi": fam["J_hi"], "J_hi2": fam["J_hi2"],
            "nom_J0.5nr": replace(nom, name="nom_J0.5nr", J=np.full(len(nom.J), 0.5))}


def bp(x, lo, hi, fs=100.0):
    sos = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band", output="sos")
    return signal.sosfiltfilt(sos, x)


def main():
    S7.members = members
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    acc = {}
    for j, seed in enumerate((0, 11, 22, 33, 44, 55)):
        t, sc, rows, rec, lane, rt = S7.run(0.0 if j == 0 else 1.93, seed=seed)
        for i, (si, mn, ln) in enumerate(rows):
            kind, v, par = sc[si][0], sc[si][1], sc[si][2]
            if kind != "TURN":
                continue
            b16 = bp(rec["rate"][i], 1.6, 3.0)
            hard = np.abs(rec["la_des"][i]) >= 1.5 - 1e-6
            acc.setdefault((v, par, mn), {"V294": [], "A1017": []})[ln].append(float(np.sqrt(np.mean(b16[hard] ** 2))))
    for mn in ("nominal", "J_hi", "J_hi2", "nom_J0.5nr"):
        allr = []
        for key in sorted(k for k in acc if k[2] == mn):
            rr = np.array(acc[key]["A1017"]) / np.array(acc[key]["V294"])
            allr += rr.tolist()
            pr("  %-10s v %4.1f a %.1f  hard-mask 1.6-3 Hz A1017/V294 median %.3f [%.3f, %.3f]  (V294 %.3f deg/s)" % (
                mn, key[0], key[1], np.median(rr), rr.min(), rr.max(), np.median(acc[key]["V294"])))
        pr("  %-10s POOLED median %.3f  p90 %.3f  fraction > 1.05: %.2f" % (mn, np.median(allr), np.percentile(allr, 90),
                                                                           np.mean(np.array(allr) > 1.05)))
    open(os.path.join(HERE, "s12_heavyJ_turns_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
