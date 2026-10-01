# -*- coding: utf-8 -*-
"""c1_page_numbers.py -- the numbers the C1 design page quotes that are not printed by the gate / harness scripts:
  1. the nominal Bode table (|L|, angle L, |T_ref|) at 3 / 8 / 12.5 / 19 / 26 m/s (harness_freq LTI fundamental);
  2. tracking: |T_ref| and Re(T_ref) at 0.2 / 0.5 Hz and the inner-loop group delay, nominal / b_lo / J_hi / b_q, and
     what a single fork look-ahead tau (C10, steerActuatorDelay) would leave: Re(T_ref * e^{+j w tau});
  3. the LIVE/NOT-LIVE predictions per wire band (c_P = Kp_eff / 800 tap counts per raw count);
  4. the discriminator: the least-damped closed-loop wheel pole per member at >= 12.5 m/s (stab_lin exact);
  5. the hard-turn |T_ref| 1.6-3 Hz peak per member and speed.
ANALYSIS ONLY."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1_members as M  # noqa: E402
import harness_freq as HF  # noqa: E402
import stab_lin as S  # noqa: E402

TBL = C.c1_table()
OUT = []


def P(s=""):
    OUT.append(s)
    print(s)


def tref(v, mem, f):
    pl, tau, ea, (J, b, k) = M.member(mem, v)
    p = HF.Plant(J=J, b=b, k=k, tau=tau)
    c = HF.replace(C.hf_ctl(v, TBL, kd=C.KD), d=tau)
    Pf = p.frf(f)
    L = HF.C_fb(f, c) * Pf
    return HF.C_ref(f, c) * Pf / (1 + L), L


def main():
    FR = np.array([0.1, 0.3, 0.5, 1.0, 1.6, 2.0, 3.0, 5.0, 7.0, 10.0, 13.0, 17.0, 20.0, 25.0, 30.0])
    P("1. BODE, nominal (harness_freq LTI fundamental, C1 table, Kd 16)")
    P("| v | row | " + " | ".join(f"{f:g}" for f in FR) + " Hz |")
    P("|---|---|" + "---|" * len(FR))
    for v in (3.0, 8.0, 12.5, 19.0, 26.0):
        Tr, L = tref(v, "nominal", FR)
        P(f"| {v:g} (Kp_eff {C.kp_eff(v, TBL):.0f}) | \\|L\\| | " + " | ".join(f"{abs(x):.3g}" for x in L) + " |")
        P("| | angle L | " + " | ".join(f"{math.degrees(np.angle(x)):.0f}" for x in L) + " |")
        P("| | \\|T_ref\\| | " + " | ".join(f"{abs(x):.3f}" for x in Tr) + " |")
    P("\n2. TRACKING: |T_ref| / Re(T_ref) at 0.2 and 0.5 Hz, group delay tau_g = -phase/omega (ms); and Re after a fork "
      "look-ahead tau (Re(T e^{+j w tau}))")
    f = np.array([0.05, 0.2, 0.5])
    taus = np.arange(0.0, 0.16, 0.005)
    rows = []
    for mem in ("nominal", "b_lo", "J_hi", "b_hi", "b_q"):
        for v in (8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.0, 30.0):
            Tr, _ = tref(v, mem, f)
            ph = np.angle(Tr)
            tg = -ph / (2 * np.pi * f) * 1000
            rows.append((mem, v, Tr))
            P(f"  {mem:8s} v {v:5.1f}: hold |T(0.05)| {abs(Tr[0]):.3f} | 0.2 Hz |T| {abs(Tr[1]):.3f} Re {Tr[1].real:.3f} "
              f"tau_g {tg[1]:4.0f} ms | 0.5 Hz |T| {abs(Tr[2]):.3f} Re {Tr[2].real:.3f} tau_g {tg[2]:4.0f} ms")
    best = None
    for tau in taus:
        worst = 0.0
        for mem, v, Tr in rows:
            if mem != "nominal":
                continue
            c = (Tr[1:] * np.exp(1j * 2 * np.pi * f[1:] * tau)).real
            worst = max(worst, float(np.max(np.abs(1 - c))))
        if best is None or worst < best[1]:
            best = (tau, worst)
    P(f"  single look-ahead minimising the worst |1 - Re| over nominal 8-30 m/s at 0.2/0.5 Hz: tau = {best[0] * 1000:.0f} ms "
      f"(worst |1 - Re| {best[1]:.3f})")
    for tau in (0.0, 0.05, best[0], 0.10):
        cells = []
        for mem, v, Tr in rows:
            if mem in ("nominal", "b_lo", "b_q"):
                c = (Tr[1:] * np.exp(1j * 2 * np.pi * f[1:] * tau)).real
                cells.append(f"{mem[:4]}@{v:g}:{c[0]:.3f}/{c[1]:.3f}")
        P(f"  tau {tau * 1000:4.0f} ms: " + " ".join(cells))
    P("\n3. LIVE prediction: c_P = Kp_eff / 800 tap counts per raw count (hands-off, f = 254/256; design sec 6)")
    for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 22), (22, 35)):
        ks = [C.kp_eff(v, TBL) for v in np.arange(lo, hi + 0.01, 0.25)]
        P(f"  band {lo:2d}-{hi:2d} m/s: Kp_eff {min(ks):5.0f}-{max(ks):5.0f} -> c_P {min(ks) / 800:.2f}-{max(ks) / 800:.2f}")
    P(f"  NOT-LIVE (cave not executed, G = identity): Kp_eff = Kp_base {C.KP_BASE} -> c_P {C.KP_BASE / 800:.2f} everywhere")
    P("\n4. DISCRIMINATOR: least-damped closed-loop pole 0.3-8 Hz (stab_lin exact periodic), by member")
    for v in (12.5, 15.0, 19.0, 26.0):
        cells = []
        for mem in ("nominal", "b_lo", "J_hi", "b_hi", "b_q", "J1.0", "b_lo*J_hi", "light_b"):
            pl, tau, ea, _ = M.member(mem, v)
            c = C.stab_ctl(v, TBL, d=tau, extra_age=ea, kd=C.KD)
            rho, poles = S.exact(c, pl)
            low = [q for q in poles if 0.3 <= q[0] <= 8.0]
            q = min(low, key=lambda t: t[1]) if low else (float("nan"), float("nan"))
            cells.append(f"{mem}: {q[0]:.2f} Hz z {q[1]:.2f}" + (" UNSTABLE" if rho >= 1 else ""))
        P(f"  v {v:4.1f}: " + " | ".join(cells))
    P("\n5. HARD-TURN |T_ref| peak in 1.6-3 Hz")
    fb = np.linspace(1.6, 3.0, 57)
    for mem in ("nominal", "b_lo", "J_hi", "b_lo*J_hi", "b_lo*J_hi*tau6", "J1.0", "b_q"):
        cells = []
        for v in (3.0, 5.0, 8.0, 11.9, 12.5, 15.0, 19.0, 26.0):
            Tr, _ = tref(v, mem, fb)
            cells.append(f"{v:g}:{np.max(np.abs(Tr)):.2f}")
        P(f"  {mem:15s} " + " ".join(cells))
    (HERE / "page_numbers.txt").write_text("\n".join(OUT), encoding="utf-8")


if __name__ == "__main__":
    main()
