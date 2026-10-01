# -*- coding: utf-8 -*-
"""c1r2_compare.py -- compare (Kd, Ki_base) choices for C1 rev 2 at their OWN robust envelope (x margin), on the
goal's own tracking metric (c1r2_trackmetric: the inner-loop factor of the slope of actual on desired lateral
accel, 0.5 Hz filtfilt, r71b's measured desired spectrum), the 0.2 / 0.5 Hz in-phase proxies, turn-hold (|T| at
0.02 Hz) and Re(T/omega) at 13 and 20 Hz vs V295.  ANALYSIS ONLY.
usage: python c1r2_compare.py kd,ki [kd,ki ...] [--margin 0.96]"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1r2_explore as X  # noqa: E402
import c1r2_members as M  # noqa: E402
import c1r2_trackmetric as TM  # noqa: E402
import harness_freq as HF  # noqa: E402

V295_RE20 = -0.633
SPEEDS = (3.0, 5.0, 8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.9, 30.0)
MEMS = ("nominal", "b_hi", "b_lo", "J_hi", "J1.0", "b_q*J_hi")


def env_of(kd, ki):
    js = json.loads((C.OUT / ("design_G_r2_" + (f"kp{C.KP_BASE}_" if C.KP_BASE != 225 else "") + f"kd{kd}_ki{ki}.json")).read_text())
    out = {}
    for vs, r in js.items():
        out[float(vs)] = min(r[n] for n in M.TIER_A + M.TIER_B)
    return out


def tref_fn(v, mem, G, kd, ki):
    J, b, k, tau, ea = M.params(mem, v)
    p = HF.Plant(J=J, b=b, k=k, tau=tau)
    c = replace(C.hf_ctl(v, None, kd=kd, G=G, ki_base=ki), d=tau)

    def T(f):
        f = np.asarray(f, float)
        Pf = p.frf(f)
        return HF.C_ref(f, c) * Pf / (1 + HF.C_fb(f, c) * Pf)
    return T


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    margin = 0.96
    if "--margin" in sys.argv:
        margin = float(sys.argv[sys.argv.index("--margin") + 1])
    for a in args:
        kd, ki = (int(x) for x in a.split(","))
        env = env_of(kd, ki)
        print(f"=== Kd {kd}  Ki_base {ki} (fI {7.8125 * ki / (2 * math.pi * C.KP_BASE):.3f} Hz)  G = {margin} x envelope ===")
        print("   v   G   Kp_eff | metric slope " + " ".join(f"{m[:8]:>8s}" for m in MEMS) +
              " | nominal tg0.2 tg0.5 hold | Re13   Re20/V295")
        for v in SPEEDS:
            vv = min(env, key=lambda x: abs(x - v))
            G = int(env[vv] * margin)
            sl = []
            for m in MEMS:
                sl.append(TM.slope(tref_fn(v, m, G, kd, ki), v))
            Tn = tref_fn(v, "nominal", G, kd, ki)(np.array([0.02, 0.2, 0.5]))
            print(f"{v:5.1f} {G:5d} {C.KP_BASE * G / 256:6.0f} |              " + " ".join(f"{s:8.3f}" for s in sl) +
                  f" |  {Tn[1].real:.3f} {Tn[2].real:.3f} {abs(Tn[0]):.3f} | {X.tpr(G, C.KP_BASE, ki, kd, 13):+.3f}"
                  f" {X.tpr(G, C.KP_BASE, ki, kd, 20) / V295_RE20:6.3f}")


if __name__ == "__main__":
    main()
