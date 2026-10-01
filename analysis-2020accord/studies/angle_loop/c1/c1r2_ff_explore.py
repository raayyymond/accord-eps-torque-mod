# -*- coding: utf-8 -*-
"""c1r2_ff_explore.py -- does a setpoint FEED-FORWARD recover the tracking that the rev-2 robust gain gives up?
ANALYSIS ONLY (linear, harness_freq's exact 1 kHz LTI blocks).

The structure studied (2-DOF, "setpoint weighting on P"): the cave hands Honda's P a different operand from Honda's I,
    E_I' = (E*G) >> 8                      -> r6 = E_I' >> 5  (the I, exactly as C1)
    E_P' = E_I' + ((4*sp) * W) >> 12       -> r16              (P = E_P' * Kp_base >> 8, Honda's own multiply)
so the extra torque is a STATIC feed-forward proportional to the angle setpoint, FF = C_ff(f) * theta_sp, with
    C_ff = K(f) * (Kp_base/256) * 160 * W/4096         (K = fade * output lag * forward gain * transport)
It is outside the loop: L, PM, GM, every GATE 2 number are unchanged; only the reference response changes:
    T_ref = (C_ref + C_ff) * P / (1 + L)
W(v) is sized as a fraction alpha of the nominal spring k(v) (T counts per deg at DC).
usage: python c1r2_ff_explore.py"""
from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1r2_members as M  # noqa: E402
import harness_freq as HF  # noqa: E402


def Kchain(f, d):
    return HF.FADE * HF.H_out(f) * HF.FWD * HF.zi(f) ** d


def W_for(kff):
    """W (Q12) giving a DC feed-forward of kff T counts per degree of setpoint."""
    k0 = abs(Kchain(np.array([1e-6]), 0)[0]) * (C.KP_BASE / 256.0) * 160.0 / 4096.0
    return kff / k0


def tref(v, mem, f, G, W, kd=C.KD, ki=C.KI_BASE, kscale=1.0):
    J, b, k, tau, ea = M.params(mem, v)
    p = HF.Plant(J=J, b=b, k=k * kscale, tau=tau)
    c = replace(C.hf_ctl(v, None, kd=kd, G=G, ki_base=ki), d=tau)
    Pf = p.frf(f)
    L = HF.C_fb(f, c) * Pf
    Cff = Kchain(f, tau) * (C.KP_BASE / 256.0) * 160.0 * W / 4096.0
    return (HF.C_ref(f, c) + Cff) * Pf / (1 + L)


def main():
    f = np.array([0.02, 0.2, 0.5])
    fb = np.linspace(1.6, 3.0, 29)
    # a representative robust schedule (Kp_eff) -- the rev-2 envelope at Kd 16 with every member, x0.96
    kpe = {8.0: 575, 10.0: 505, 11.9: 520, 12.5: 335, 15.0: 430, 17.0: 565, 19.0: 635, 22.0: 740, 26.9: 900, 30.0: 900}
    print("v      Kp_eff  k_nom  alpha | nominal 0.2/0.5 | b_hi 0.2/0.5 | b_lo | J_hi | k x0.7 | k x1.3 | b_q*J_hi | "
          "Tref pk 1.6-3 Hz nominal / b_q*J_hi / b_lo*J_hi")
    for v, kp in kpe.items():
        G = kp * 256.0 / C.KP_BASE
        kn = M.params("nominal", v)[2]
        for alpha in (0.0, 0.5, 0.7, 0.85, 1.0):
            W = W_for(alpha * kn)
            cells = []
            for mem, ks in (("nominal", 1), ("b_hi", 1), ("b_lo", 1), ("J_hi", 1), ("nominal", 0.7), ("nominal", 1.3),
                            ("b_q*J_hi", 1)):
                T = tref(v, mem, f, G, W, kscale=ks)
                cells.append(f"{T[1].real:.3f}/{T[2].real:.3f}")
            pk = [np.max(np.abs(tref(v, m, fb, G, W))) for m in ("nominal", "b_q*J_hi", "b_lo*J_hi")]
            print(f"{v:5.1f} {kp:6.0f} {kn:6.1f} {alpha:5.2f} | " + " | ".join(cells) +
                  f" | {pk[0]:.2f} / {pk[1]:.2f} / {pk[2]:.2f}   W {W:.0f}")
        print()


if __name__ == "__main__":
    main()
