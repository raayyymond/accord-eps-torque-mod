# -*- coding: utf-8 -*-
"""s9_post_turn.py -- adversary `stability`: the post-turn (turn exit -> straight) behaviour over 6 seeds.  s7 showed
light-damping-world cells where one build settles and the other keeps a sustained 0.5-5 Hz motion for 15 s after the
turn (both directions).  Count, per build, the cells with a SUSTAINED post-turn oscillation (0.5-5 Hz rms over the last
5 s of the run > 0.15 deg/s and > 50 % of the 15-29 s rms), and its frequency.  Same engine as s7 (my lane, my plant,
the fork port)."""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s7_closedloop as S7  # noqa: E402


def bp(x, lo, hi, fs=100.0):
    sos = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band", output="sos")
    return signal.sosfiltfilt(sos, x)


def main():
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    seeds = (0, 11, 22, 33, 44, 55)
    res = {}
    for j, seed in enumerate(seeds):
        t, sc, rows, rec, lane, rt = S7.run(0.0 if j == 0 else 1.93, seed=seed)
        for i, (si, mn, ln) in enumerate(rows):
            kind, v, par = sc[si][0], sc[si][1], sc[si][2]
            if kind != "TURN":
                continue
            r = rec["rate"][i]
            b = bp(r, 0.5, 5.0)
            post = (t > 15) & (t < 29)
            last = (t > 24) & (t < 29)
            rp, rl = float(np.sqrt(np.mean(b[post] ** 2))), float(np.sqrt(np.mean(b[last] ** 2)))
            f, P = signal.welch(r[post] - r[post].mean(), fs=100.0, nperseg=512)
            mm = (f > 0.3) & (f < 6)
            res.setdefault((v, par, mn), {"V294": [], "A1017": []})[ln].append(
                (rp, rl, float(f[mm][np.argmax(P[mm])]), rl > 0.15 and rl > 0.5 * rp))
    pr("post-turn (15-29 s) 0.5-5 Hz rms / last-5 s rms / peak f / sustained?  -- per cell, 6 seeds (seed 0 noise-free)")
    tot = {"V294": 0, "A1017": 0}
    n = 0
    both = only_V = only_A = 0
    for key in sorted(res):
        V, A = res[key]["V294"], res[key]["A1017"]
        sv, sa = sum(x[3] for x in V), sum(x[3] for x in A)
        tot["V294"] += sv
        tot["A1017"] += sa
        n += len(V)
        for a_, v_ in zip(A, V):
            both += a_[3] and v_[3]
            only_V += v_[3] and not a_[3]
            only_A += a_[3] and not v_[3]
        if sv or sa:
            pr("  v %4.1f a %.1f %-9s V294 sustained %d/6 (last-5s rms med %.3f, f %.2f) | A1017 %d/6 (med %.3f, f %.2f)" % (
                key[0], key[1], key[2], sv, np.median([x[1] for x in V]), np.median([x[2] for x in V]), sa,
                np.median([x[1] for x in A]), np.median([x[2] for x in A])))
    pr("TOTAL sustained post-turn oscillation cells: V294 %d, A1017 %d of %d ; both %d, V294 only %d, A1017 only %d" % (
        tot["V294"], tot["A1017"], n, both, only_V, only_A))
    open(os.path.join(HERE, "s9_post_turn_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
