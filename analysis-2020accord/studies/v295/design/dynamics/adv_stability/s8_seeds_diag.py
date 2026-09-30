# -*- coding: utf-8 -*-
"""s8_seeds_diag.py -- adversary `stability`: follow-up of s7's one adverse signal -- on the light-damping-world members
the 1.6-3 Hz wheel rate during the HOLD of a hard turn (3 m/s^2 at 8-12 m/s) ROSE under A1017 (x1.06-1.24) while the
ramps fell.  Is it systematic (same sign over noise seeds), what is it (a decaying ring, stick-slip, a limit cycle), and
does it survive the harness's own hard-turn mask (|plan| >= 1.5 m/s^2 frames, transitions included)?

Re-runs s7's engine (same code) over 6 noise seeds; adds: hard16 over |plan| >= 1.5 frames; the hold split into an
early (5-8 s) and a late (8-12 s) window; stick fraction and slip-event count in the hold (noise-free run, true omega is
not recorded by s7 -> the 0x18F-quantised rate with the noise-free run is used); the hold spectrum's peak.
"""
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
    acc = {}
    for si_, seed in enumerate(seeds):
        xn = 0.0 if si_ == 0 else 1.93
        t, sc, rows, rec, lane, rt = S7.run(xn, seed=seed)
        for i, (si, mn, ln) in enumerate(rows):
            kind, v, par = sc[si][0], sc[si][1], sc[si][2]
            r = rec["rate"][i]
            ld = rec["la_des"][i]
            key = (kind, v, par, mn)
            d = acc.setdefault(key, {"V294": [], "A1017": []})
            if kind == "TURN":
                b16 = bp(r, 1.6, 3.0)
                hard = np.abs(ld) >= 1.5 - 1e-6
                early = (t > 5.0) & (t < 8.0)
                late = (t > 8.0) & (t < 12.0)
                f, P = signal.welch(r[(t > 5) & (t < 12)] - r[(t > 5) & (t < 12)].mean(), fs=100.0, nperseg=512)
                mm = (f > 0.5) & (f < 6)
                d[ln].append(dict(hard_mask=float(np.sqrt(np.mean(b16[hard] ** 2))) if hard.any() else np.nan,
                                  early=float(np.sqrt(np.mean(b16[early] ** 2))), late=float(np.sqrt(np.mean(b16[late] ** 2))),
                                  fpk=float(f[mm][np.argmax(P[mm])]),
                                  still=float(np.mean(np.abs(r[(t > 5) & (t < 12)]) < 0.125))))
            elif kind == "CENTRE":
                w = t > 5.0
                d[ln].append(dict(r035=float(np.sqrt(np.mean(bp(r, 0.3, 5.0)[w] ** 2))),
                                  r163=float(np.sqrt(np.mean(bp(r, 1.6, 3.0)[w] ** 2)))))
        pr("seed %d (x_noise %.2f) done" % (seed, xn))
    pr("\nTURN: paired A1017/V294 ratios over %d runs (seed 0 noise-free): median [min, max]" % len(seeds))
    for key in sorted(k for k in acc if k[0] == "TURN"):
        V, A = acc[key]["V294"], acc[key]["A1017"]
        out = []
        for m in ("hard_mask", "early", "late"):
            rr = np.array([a[m] / v[m] for a, v in zip(A, V) if v[m] > 1e-6])
            out.append("%s %.3f [%.3f, %.3f]" % (m, np.median(rr), rr.min(), rr.max()))
        pr("  %-4s v %4.1f a %.1f %-9s %s  | V294 hard_mask %.3f fpk %.2f still %.2f ; A1017 fpk %.2f still %.2f" % (
            key[0], key[1], key[2], key[3], "  ".join(out), np.median([v["hard_mask"] for v in V]),
            np.median([v["fpk"] for v in V]), np.median([v["still"] for v in V]), np.median([a["fpk"] for a in A]),
            np.median([a["still"] for a in A])))
    pr("\nCENTRE: paired A1017/V294 ratios: median [min, max]")
    for key in sorted(k for k in acc if k[0] == "CENTRE"):
        V, A = acc[key]["V294"], acc[key]["A1017"]
        out = []
        for m in ("r035", "r163"):
            rr = np.array([a[m] / v[m] for a, v in zip(A, V) if v[m] > 1e-6])
            if len(rr):
                out.append("%s %.3f [%.3f, %.3f]" % (m, np.median(rr), rr.min(), rr.max()))
        pr("  v %4.1f %-9s %s" % (key[1], key[3], "  ".join(out)))
    # member-level pooled summary for the harness-style hard-turn mask
    pr("\nTURN hard_mask, pooled over v, a, seeds: median ratio per member [p10, p90]")
    for mn in ("nominal", "J_lo", "J_hi2", "b_lo", "F_hi", "light_b", "lb_J2.5x", "lb_b0.5x"):
        rr = np.array([a["hard_mask"] / v["hard_mask"] for k in acc if k[0] == "TURN" and k[3] == mn
                       for a, v in zip(acc[k]["A1017"], acc[k]["V294"]) if v["hard_mask"] > 1e-6])
        pr("  %-9s median %.3f [%.3f, %.3f]  fraction > 1.05: %.2f" % (mn, np.median(rr), np.percentile(rr, 10),
                                                                       np.percentile(rr, 90), np.mean(rr > 1.05)))
    open(os.path.join(HERE, "s8_seeds_diag_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
