# -*- coding: utf-8 -*-
"""c1r2_page_numbers.py -- the numbers the C1 rev-2 design page quotes that the gate / harness scripts do not print:
  1. the schedule: G, Kp_eff, Ki_eff, T per degree, the P-rail angle, at the page's speeds (from the integer walk);
  2. the nominal Bode table (|L|, angle L, |T_ref|) at 3 / 8 / 12.5 / 17 / 26 m/s (harness_freq LTI fundamental);
  3. TRACKING on the goal's own metric (c1r2_trackmetric: the inner-loop factor of the slope of actual on desired
     lateral accel, 0.5 Hz filtfilt, r71b's measured spectrum), by band and member; plus the 0.2 / 0.5 Hz in-phase
     proxies and turn-hold (|T(0.02 Hz)|), and what a single fork look-ahead does to the metric;
  4. the LIVE / NOT-LIVE predictions per wire band (c_P = Kp_eff / 800 tap counts per raw count);
  5. the discriminator: least-damped closed-loop pole 0.3-8 Hz per member at >= 10 m/s (stab_lin exact), which sets
     the R3 stop band;
  6. the hard-turn |T_ref| 1.6-3 Hz peak per member and speed;
  7. the fork's Delta-max cap on demanded P: 0.1 * Kp_eff * Delta-max.
ANALYSIS ONLY.  usage: python c1r2_page_numbers.py   -> c1/page_numbers_r2.txt"""
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
import c1r2_trackmetric as TM  # noqa: E402
import harness_freq as HF  # noqa: E402
import stab_lin as S  # noqa: E402

TBL = C.c1_table()
OUT = []


def P(s=""):
    OUT.append(s)
    print(s)


def tref_fn(v, mem):
    J, b, k, tau, ea = M.params(mem, v)
    p = HF.Plant(J=J, b=b, k=k, tau=tau)
    c = replace(C.hf_ctl(v, TBL, kd=C.KD), d=tau)

    def T(f):
        f = np.asarray(f, float)
        Pf = p.frf(f)
        return HF.C_ref(f, c) * Pf / (1 + HF.C_fb(f, c) * Pf)

    def L(f):
        f = np.asarray(f, float)
        return HF.C_fb(f, c) * p.frf(f)
    return T, L


def main():
    P(f"C1 rev 2: table {TBL}; Kp_base {C.KP_BASE}, Ki_base {C.KI_BASE} (fI {7.8125 * C.KI_BASE / (2 * math.pi * C.KP_BASE):.3f} Hz), "
      f"Kd {C.KD}")
    P("\n1. SCHEDULE (integer walk)")
    P("| v (m/s) | G | Kp_eff | Ki_eff | T per deg (~Kp_eff/10) | P rails at |e| (deg) = 24576/Kp_eff |")
    P("|---|---|---|---|---|---|")
    for v in (1.0, 3.1, 5.0, 8.0, 10.0, 11.9, 12.25, 12.5, 13.0, 15.0, 15.25, 17.0, 19.25, 22.0, 26.0, 27.0, 30.0):
        G = C.G_at(v, TBL)
        kp = C.KP_BASE * G / 256
        P(f"| {v:g} | {G} | {kp:.0f} | {C.KI_BASE * G / 256:.0f} | {kp / 10:.0f} | {24576 / kp:.1f} |")

    FR = np.array([0.1, 0.3, 0.5, 1.0, 1.6, 2.0, 3.0, 5.0, 7.0, 10.0, 13.0, 17.0, 20.0, 25.0, 30.0])
    P("\n2. BODE, nominal (harness_freq LTI fundamental)")
    P("| v | row | " + " | ".join(f"{f:g}" for f in FR) + " Hz |")
    P("|---|---|" + "---|" * len(FR))
    for v in (3.0, 8.0, 12.5, 17.0, 26.0):
        T, L = tref_fn(v, "nominal")
        Lv, Tv = L(FR), T(FR)
        P(f"| {v:g} (Kp_eff {C.kp_eff(v, TBL):.0f}) | \\|L\\| | " + " | ".join(f"{abs(x):.3g}" for x in Lv) + " |")
        P("| | angle L | " + " | ".join(f"{math.degrees(np.angle(x)):.0f}" for x in Lv) + " |")
        P("| | \\|T_ref\\| | " + " | ".join(f"{abs(x):.3f}" for x in Tv) + " |")

    P("\n3. TRACKING on the GOAL'S OWN METRIC (inner-loop factor; r71b desired-lat-accel spectrum) and the proxies")
    mems = ("nominal", "b_hi", "b_lo", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_lo*J_hi")
    P("| v | band | Kp_eff | " + " | ".join(mems) + " | nominal tg0.2 / tg0.5 / turn-hold |T(0.02)| |")
    P("|---|---|---|" + "---|" * len(mems) + "---|")
    worst = {}
    for v in (8.0, 10.0, 11.9, 12.5, 13.0, 15.0, 17.0, 19.0, 22.0, 26.0, 30.0):
        cells = []
        for m in mems:
            T, _ = tref_fn(v, m)
            s = TM.slope(T, v)
            cells.append(f"{s:.3f}")
            b = TM.band_of(v)
            worst[b] = min(worst.get(b, (9, "", 0)), (s, m, v))
        T, _ = tref_fn(v, "nominal")
        t = T(np.array([0.02, 0.2, 0.5]))
        tg = -np.angle(t[1:]) / (2 * np.pi * np.array([0.2, 0.5])) * 1000
        P(f"| {v:g} | {TM.band_of(v)} | {C.kp_eff(v, TBL):.0f} | " + " | ".join(cells) +
          f" | {t[1].real:.3f} / {t[2].real:.3f} / {abs(t[0]):.3f} ; |T(0.2)| {abs(t[1]):.3f} tau_g(0.2) {tg[0]:.0f} ms,"
          f" |T(0.5)| {abs(t[2]):.3f} tau_g(0.5) {tg[1]:.0f} ms |")
    P("  worst member per band (the goal's 0.95-1.05 bar): " + "; ".join(
        f"{b}: {w[0]:.3f} ({w[1]} @ {w[2]:g})" for b, w in worst.items()))
    P("  a single fork look-ahead tau on the metric (nominal), Re(T e^{+j w tau}):")
    for tau in (0.0, 0.05, 0.10, 0.15):
        cells = []
        for v in (8.0, 12.5, 15.0, 17.0, 19.0, 26.0):
            T, _ = tref_fn(v, "nominal")
            cells.append(f"{v:g}: {TM.slope(lambda f: T(f) * np.exp(1j * 2 * np.pi * f * tau), v):.3f}")
        P(f"    tau {tau * 1000:3.0f} ms: " + "  ".join(cells))

    P("\n4. LIVE prediction: c_P = Kp_eff / 800 tap counts per raw count (hands-off, f = 254/256)")
    for lo, hi in ((0, 5), (5, 10), (10, 12.4), (12.5, 15), (15, 22), (22, 35)):
        ks = [C.kp_eff(v, TBL) for v in np.arange(lo, hi + 0.01, 0.25)]
        P(f"  band {lo:4g}-{hi:4g} m/s: Kp_eff {min(ks):5.0f}-{max(ks):5.0f} -> c_P {min(ks) / 800:.3f}-{max(ks) / 800:.3f}")
    P(f"  NOT-LIVE (cave not executed, G = identity): Kp_eff = Kp_base {C.KP_BASE} -> c_P {C.KP_BASE / 800:.3f} everywhere")
    P(f"  c_I / c_P = 2 pi fI = {2 * math.pi * 7.8125 * C.KI_BASE / (2 * math.pi * C.KP_BASE):.2f} s^-1 ; "
      f"c_D = Kd * 0.16 / 8 tap per deg/s = {C.KD * 0.1604 / 8:.3f} (tap = T/8)")

    P("\n5. DISCRIMINATOR: least-damped closed-loop pole 0.3-8 Hz (stab_lin exact periodic), by member")
    dmems = ("nominal", "b_lo", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_lo*J_hi", "b_q*J1.0+h10", "light_b")
    for v in (10.0, 12.5, 15.0, 17.0, 19.0, 22.0, 26.0, 30.0):
        cells = []
        for mem in dmems:
            pl, tau, ea, _ = M.member(mem, v)
            c = C.stab_ctl(v, TBL, d=tau, extra_age=ea, kd=C.KD)
            rho, poles = S.exact(c, pl)
            low = [q for q in poles if 0.3 <= q[0] <= 8.0]
            q = min(low, key=lambda t: t[1]) if low else (float("nan"), float("nan"))
            cells.append(f"{mem}: {q[0]:.2f} Hz z {q[1]:.2f}" + (" UNSTABLE" if rho >= 1 else ""))
        P(f"  v {v:4.1f}: " + " | ".join(cells))

    P("\n6. HARD-TURN |T_ref| peak in 1.6-3 Hz")
    fb = np.linspace(1.6, 3.0, 57)
    for mem in ("nominal", "b_lo", "J_hi", "b_lo*J_hi", "b_lo*J_hi*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0"):
        cells = []
        for v in (3.0, 5.0, 8.0, 11.9, 12.5, 15.0, 17.0, 19.0, 26.0):
            T, _ = tref_fn(v, mem)
            cells.append(f"{v:g}:{np.max(np.abs(T(fb))):.2f}")
        P(f"  {mem:15s} " + " ".join(cells))

    P("\n7. THE FORK'S DELTA-MAX CAP ON DEMANDED P (0.1 * Kp_eff * Delta-max; Delta-max from the spec's 7.1 table, BELIEF)")
    for v, dm in ((5.0, 15.0), (8.0, 10.0), (10.0, 8.0), (15.0, 5.0), (20.0, 4.0), (30.0, 3.0)):
        P(f"  v {v:4g}: Kp_eff {C.kp_eff(v, TBL):5.0f}, Delta-max {dm:4.1f} deg -> P cap {0.1 * C.kp_eff(v, TBL) * dm:5.0f} T")
    (HERE / "page_numbers_r2.txt").write_text("\n".join(OUT), encoding="utf-8")


if __name__ == "__main__":
    main()
