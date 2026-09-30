# -*- coding: utf-8 -*-
"""rj9_flip_diag.py -- lens robust-joint: WHY does the FF gain g raise the 1-3 Hz wheel motion under dist 'lp' (the flip
that demotes F3 by the pre-registered F3 rule)?  Two hypotheses, separated by one controlled edit of the exogenous input:
  (a) PLANNER-DRIVEN: the fork passes the planner's own 1-3 Hz desired-curvature content to the command (FF path), and a
      higher EPS gain delivers more of it -> the ratio should collapse toward 1 when that content is removed;
  (b) LOOP-GENERATED: the outer loop (fork P/I/relay on the quantised angle) makes more of its own motion at higher gain
      -> the ratio should survive the removal.
Control edit: controlsState.desiredCurvature low-passed at 0.8 Hz (zero-phase, 2nd order) in the harness's route cache
(in memory only; nothing on disk changes), V294 and F3 re-simulated under lp on nominal / b_lo / light_b.
Also a finer g sweep at t 1.95 (g 1.00 / 1.03 / 1.05 / 1.08) on the UNMODIFIED route, lp and full, nominal + light_b + J_hi,
to locate the largest g whose 15-22 m/s hard-turn / 1-3 Hz rate ratio stays <= 1.00 on every member (no flip).
ANALYSIS ONLY."""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402


def row(S, dist, c, p, b, k):
    return S[(dist, c, p)][b][k]


def main():
    out = {}
    # ---------------- finer g at t 1.95, unmodified route
    cl = [RC.make(g=g, t=1.95, name="g%.2f" % g, allow_opcode=False) for g in (1.0, 1.03, 1.05, 1.08)]
    for p in ("nominal", "light_b", "J_hi", "b_lo"):
        S = H.sweep_drive(cl, plants=(p,), dists=("lp", "full"))
        for dist in ("lp", "full"):
            for c in cl:
                line = []
                for b in ("5-10", "15-22", "22+"):
                    for k in ("hard16", "r_mid"):
                        v = row(S, dist, c.name, p, b, k) / row(S, dist, "V294", p, b, k)
                        line.append("%s %s x%.3f" % (b, k, v))
                        out["fine|%s|%s|%s|%s|%s" % (dist, c.name, p, b, k)] = v
                for b in ("0-5", "5-10", "15-22", "22+"):
                    dv = row(S, dist, c.name, p, b, "track_gain") - row(S, dist, "V294", p, b, "track_gain")
                    line.append("tg %s %+.3f" % (b, dv))
                    out["fine|%s|%s|%s|%s|tg" % (dist, c.name, p, b)] = dv
                print("  %-4s %-8s %-6s %s" % (dist, p, c.name, "  ".join(line)), flush=True)
    # ---------------- planner low-pass control
    d = H.route()
    orig = d["ctl_des_curv_f"].copy()
    bb, aa = signal.butter(2, 0.8 / 50.0)
    d["ctl_des_curv_f"] = signal.filtfilt(bb, aa, orig)
    F3 = RC.make(g=1.2, t=1.95, name="F3", allow_opcode=False)
    F1 = RC.make(g=1.0, t=1.95, name="F1", allow_opcode=False)
    print("\nPLANNER LOW-PASSED (0.8 Hz) -- dist lp")
    for p in ("nominal", "b_lo", "light_b"):
        S = H.sweep_drive([F3, F1], plants=(p,), dists=("lp",))
        for c in ("F3", "F1"):
            line = []
            for b in ("5-10", "15-22", "22+"):
                for k in ("hard16", "r_mid"):
                    v = row(S, "lp", c, p, b, k) / row(S, "lp", "V294", p, b, k)
                    out["lpplan|%s|%s|%s|%s" % (c, p, b, k)] = v
                    line.append("%s %s x%.3f" % (b, k, v))
            print("  %-8s %-3s %s   (V294 r_mid 15-22 = %.3f deg/s)" % (p, c, "  ".join(line), row(S, "lp", "V294", p, "15-22", "r_mid")),
                  flush=True)
    d["ctl_des_curv_f"] = orig
    json.dump(out, open(os.path.join(HERE, "rj9_flip_diag.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
