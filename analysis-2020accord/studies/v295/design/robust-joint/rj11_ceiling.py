# -*- coding: utf-8 -*-
"""rj11_ceiling.py -- lens robust-joint: PHYSICS HONESTY -- how far can cal values move the operator's metric
("alpha tracks cmd": flat gain, 0 deg) and what is structurally out of reach.

Closed form (harness alpha_per_cmd's arithmetic, linear, friction off): alpha/cmd = s^2 P_theta FF zoh100 / (1 + L_in),
the ACTUATOR branch (what the firmware makes the wheel do per command count; the fork's reaction is not in it).
Reported per member and speed: |alpha/cmd| at 0.5/1/2/3/5/8 Hz, phase, and the 1-8 Hz complex-gain R^2 weighted by the
drive's command spectrum, for V294, the pick, larger trims (inside and outside the constraints), a higher pole, and an
IDEAL acceleration servo (the same FF, infinite inner gain with no lag: alpha = FF_DC / K_alpha_ref * cmd -> flat) --
the ceiling no value set reaches.  ANALYSIS ONLY."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_lin as RL  # noqa: E402
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402


def main():
    ctx = RL.Ctx()
    F = RL.F_OUT
    fr = (0.5, 1.0, 2.0, 3.0, 5.0, 8.0)
    ix = [int(np.argmin(np.abs(F - f))) for f in fr]
    b0 = RC.base()
    cands = [("V294", b0), ("V293 (C 0)", b0.replace(fb_clamp=0, name="v293")),
             ("PICK t1.95 g1.00", RC.make(g=1.0, t=1.95, name="pick")),
             ("t3 (HF cap)", RC.make(g=1.0, t=2.95, name="t3")), ("t8 pole 2 Hz (x8 HF!)", RC.make(g=1.0, t=8.0, name="t8")),
             ("t8 pole 8 Hz (x8 HF!)", RC.make(g=1.0, t=8.0, f_fb=8.0, name="t8p8")),
             ("t32 pole 16 Hz (V282-class HF)", RC.make(g=1.0, t=32.0, f_fb=16.0, name="t32"))]
    m = (F >= 1.0) & (F <= 8.0)
    w = ctx.W[m]
    for nm_p in ("nominal", "light_b", "J_hi"):
        for v in (5.0, 12.0, 26.9):
            print("\n%s @ %.1f m/s   |alpha/cmd| deg/s^2 per 0xE4 count at %s Hz   [phase deg]   R2(1-8 Hz, complex gain)" % (nm_p, v, fr))
            for nm, c in cands:
                if c is None:
                    print("   %-32s (not constructible: b > b_max even with the opcode)" % nm)
                    continue
                lt = RL.LaneTF(c)
                Lin = RL.inner_L(ctx, lt, nm_p, v, "out", idx=30)
                A = ctx.s_out ** 2 * ctx.P_out[(nm_p, v)] * lt.ff(F, 30) * ctx.zoh100 / (1 + Lin)
                a = A[m]
                R2 = float(np.abs(np.sum(a * w)) ** 2 / (np.sum(np.abs(a) ** 2 * w) * np.sum(w)))
                print("   %-32s %s   [%s]   R2 %.3f   HF |P/x|@20Hz %.2f"
                      % (nm, " ".join("%6.3f" % abs(A[i]) for i in ix), " ".join("%+4.0f" % np.degrees(np.angle(A[i])) for i in ix),
                         R2, float(np.abs(lt.ct(np.array([20.0]), 0, kind="P"))[0])))
            # the ceiling: an ideal flat response has R2 = 1 by construction; also the pure-plant (no FF lag) shape
            P = ctx.P_out[(nm_p, v)]
            A0 = ctx.s_out ** 2 * P
            a0 = A0[m]
            R20 = float(np.abs(np.sum(a0 * w)) ** 2 / (np.sum(np.abs(a0) ** 2 * w) * np.sum(w)))
            print("   %-32s R2 %.3f  (the bare plant alpha/u shape, no lane: the spring/damper floor)" % ("plant alone s^2 P", R20))


if __name__ == "__main__":
    main()
