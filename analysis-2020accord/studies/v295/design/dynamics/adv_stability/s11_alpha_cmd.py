# -*- coding: utf-8 -*-
"""s11_alpha_cmd.py -- adversary `stability`, attack surface (e), the literal goal metric: closed-form wheel angular
acceleration per 0xE4 count with the inner trim loop closed (my exact-ZOH model, advlin.alpha_per_cmd), A1017 / V294,
over the family and my J corners, at 0.5 / 1 / 2 / 3 / 5 Hz; plus the restart pulse by my own integer lane.
F-e clause: |alpha/cmd| at 1 Hz below x0.85 on an identified member or x0.75 on light_b."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness"))
import advlin as AL  # noqa: E402
import v295_harness as H  # noqa: E402
from s0_lane_spotcheck import MyLane  # noqa: E402

LV = AL.LaneLin(1011, 567)
LA = AL.LaneLin(1017, 567)


def main():
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    fam = H.family()
    f = np.array([0.5, 1.0, 2.0, 3.0, 5.0])
    worst = {}
    for mn in ("nominal", "J_lo", "J_hi", "J_hi2", "J_0.3", "b_lo", "b_hi", "ms_free", "light_b"):
        for js in (0.5, 1.0, 2.5):
            for v in (3.1, 8.0, 12.0, 17.0, 26.9):
                p = fam[mn].at(v)
                pl = AL.Plant(p.J * js, p.b, p.k)
                a0 = AL.alpha_per_cmd(LV, pl, f, tau=p.tau_ms)
                a1 = AL.alpha_per_cmd(LA, pl, f, tau=p.tau_ms)
                rr = np.abs(a1 / a0)
                dph = np.degrees(np.angle(a1 / a0))
                key = (mn, js)
                w = worst.setdefault(key, [np.inf] * len(f))
                worst[key] = [min(w[i], rr[i]) for i in range(len(f))]
                if js == 1.0 and v in (8.0, 12.0, 26.9):
                    pr("  %-8s J x%.1f v %4.1f  ratio %s  dphase %s  | V294 |a/cmd| %s ph %s" % (
                        mn, js, v, np.round(rr, 3).tolist(), np.round(dph, 1).tolist(), np.round(np.abs(a0), 3).tolist(),
                        np.round(np.degrees(np.angle(a0)), 0).tolist()))
    pr("\nworst (minimum) ratio over speeds 3.1-26.9, per member x J scale, at f = %s Hz" % f.tolist())
    for k, w in worst.items():
        pr("  %-8s J x%.1f  %s" % (k[0], k[1], np.round(w, 3).tolist()))
    pr("\nrestart pulse after a filter bail (my integer lane, x held, sp 0, m 254): peak |T| / ms above 50 T")
    for wd in (10.0, 30.0, 100.0, 300.0):
        out = []
        for a in (1011, 1017):
            L = MyLane(1, a, 567)
            x = int(round(-8 * wd))
            L.s = np.array([(567 * x) // (1024 - a)], np.int64)
            L.rst = np.array([True])
            T = np.array([abs(int(L.tick(np.array([x]), np.array([0]))[0][0])) for _ in range(1500)])
            out.append((T.max(), int(np.sum(T > 50))))
        pr("  %5.0f deg/s: V294 %d T / %d ms ; A1017 %d T / %d ms" % (wd, out[0][0], out[0][1], out[1][0], out[1][1]))
    open(os.path.join(HERE, "s11_alpha_cmd_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
