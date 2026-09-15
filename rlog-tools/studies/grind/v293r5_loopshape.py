# -*- coding: utf-8 -*-
"""v293r5_loopshape.py -- what limits the fork loop's STIFFNESS on the V293 torque-map EPS (orchestrator's own, 2026-09-15).

The operator's rev-4 read: still loose, jerky on hard turns, the command has to overshoot to get over friction, and
Ki-heavy tuning is a variable delay he does not want.  A 1 kHz inner rate loop made the plant a rate servo (type-1 in
angle, friction swamped); the fork's 100 Hz loop with ~60 ms round trip cannot.  This script asks, with the linear
model, how stiff the 100 Hz loop CAN be made with P (+ the rate loop) alone, and what eats the phase:

  * plant  e^{-s Td} / (a + b s + J s^2), a = hold slope at 0 deg (route-dependent x1.0..1.7), Td = 0.04 EPS + 0.02 meas
  * the fork's P (lsf-inflated) and I in lat-accel space through LAF, the speed-scheduled error notch, the 100 Hz rate loop
  * b is THE crux: the rev-3/4 design used b = 0.0006 (a lightly damped 2 Hz mode); the plant ident (F1) fitted
    b = 0.0018 / 0.0037 / 0.0041 / 0.0049 by band (an overdamped plant, no mode).  Both are tabulated.

Outputs per (v, b, notch, Kp, Kv): Ms, crossover, PM, |S| at 0.1 / 0.2 / 0.5 Hz (what fraction of a slow torque
disturbance / FF error leaks into the angle), the static stiffness ratio (1 + L(0)) with Ki = 0, and the closed-loop
stiction residual F / stiffness in deg and m/s^2.
ANALYSIS ONLY.
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r2_simlib as S
import v293r3_read as R3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)

def A_of(v):
    return S.lat_accel_per_deg(v, S.steer_ratio(10.0, 16.88))

B_IDENT = {8.0: 0.0018, 12.0: 0.0037, 19.0: 0.0041, 26.0: 0.0049}

def loop(v, kp, ki, kv, notch_q, b, J=1.0e-4, dead=0.04, meas=0.02, need=1.0, laf=14.0, rl_rc=0.03, rl_taper=12.0):
    a = need * float(R3.hold_slope(0.0, v))
    f = np.logspace(-2, 1.4, 4000); s = 1j * 2 * np.pi * f
    A = A_of(v); L_ = S.lsf(v)
    kp_a = (kp + L_) / laf * A                 # torque per deg from the P term (lsf-inflated), linearised
    ki_a = ki * (1 + L_ / max(kp, 1e-3)) / laf * A
    w0 = 2 * np.pi * float(R3.mode_hz(v)); q = notch_q
    N = (s ** 2 + w0 ** 2) / (s ** 2 + w0 / q * s + w0 ** 2) if q > 0 else 1.0
    kd = kv * min(1.0, rl_taper / v)
    Cpi = (kp_a + (ki_a / s if ki > 0 else 0.0)) * N
    Crl = kd * s / (1 + s * rl_rc)
    C = (Cpi + Crl) * np.exp(-s * meas)
    P = np.exp(-s * dead) / (a + b * s + J * s ** 2)
    Lw = C * P
    Sw = 1 / (1 + Lw)
    mag = np.abs(Lw)
    idx = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(idx):
        k = idx[-1]; wc = f[k]; pm = ((180 + np.degrees(np.angle(Lw[k])) + 180) % 360) - 180
    else:
        wc, pm = np.nan, np.nan
    def at(fq, arr):
        return float(np.interp(fq, f, np.abs(arr)))
    stiff0 = 1.0 + kp_a / a                    # static stiffness ratio with Ki = 0 (rate loop has no DC)
    return dict(Ms=float(np.max(np.abs(Sw))), wc=wc, pm=pm, S01=at(0.1, Sw), S02=at(0.2, Sw), S05=at(0.5, Sw),
                S10=at(1.0, Sw), stiff0=stiff0, a=a, kp_a=kp_a, A=A, f=f, L=Lw, Sw=Sw)


def main():
    F = 0.012   # Coulomb, torque units (ident F1 ~0.010-0.012)
    pr("v293r5_loopshape -- linear margins of the fork loop on the V293 plant.  Plant e^{-s Td}/(a + b s + J s^2), J 1e-4,")
    pr("Td 0.04 + 0.02 meas, a = hold slope at 0 deg.  Controller: fork P (lsf) + I via LAF 14, notch Q (0 = off), rate loop Kv tapered 12/v.")
    pr("Columns: Ms | wc Hz | PM deg | |S| at 0.1 / 0.2 / 0.5 / 1 Hz | static stiffness (1+L0, Ki=0) | stiction residual F/stiff: deg, m/s^2")
    for b_mode in ("ident", 0.0006, 0.002):
        pr("\n" + "=" * 130)
        pr("plant damping b = %s" % ("IDENT F1 per band (0.0018/0.0037/0.0041/0.0049)" if b_mode == "ident" else "%.4f (rev-3/4 design value)" % b_mode if b_mode == 0.0006 else "%.4f" % b_mode))
        for v in (8.0, 12.0, 19.0, 26.0):
            b = B_IDENT[v] if b_mode == "ident" else b_mode
            pr("\n  v %4.0f m/s  a %.4f torque/deg  b %.4f  mode_hz(fork) %.2f  A %.3f m/s^2 per deg  lsf %.3f"
               % (v, float(R3.hold_slope(0.0, v)), b, float(R3.mode_hz(v)), A_of(v), S.lsf(v)))
            pr("  %-34s | %5s %5s %6s | %5s %5s %5s %5s | %6s | %6s %6s" % ("cfg", "Ms", "wc", "PM", "S.1", "S.2", "S.5", "S1", "stiff", "deg", "m/s2"))
            rows = [
                ("R4 flown: Kp.85 Ki.6/2.5 notch1 Kv6e-4", 0.85, (0.6 if v < 8 else 2.5 if v >= 18 else 0.6 + (2.5 - 0.6) * (v - 8) / 10), 0.0006, 1.0),
                ("Kp.85 Ki0 notch1 Kv6e-4", 0.85, 0.0, 0.0006, 1.0),
                ("Kp.85 Ki0 NO notch Kv6e-4", 0.85, 0.0, 0.0006, 0.0),
                ("Kp1.5 Ki0 NO notch Kv6e-4", 1.5, 0.0, 0.0006, 0.0),
                ("Kp2.0 Ki0 NO notch Kv6e-4", 2.0, 0.0, 0.0006, 0.0),
                ("Kp2.5 Ki0 NO notch Kv6e-4", 2.5, 0.0, 0.0006, 0.0),
                ("Kp3.0 Ki0 NO notch Kv6e-4", 3.0, 0.0, 0.0006, 0.0),
                ("Kp2.0 Ki0 NO notch Kv1e-3", 2.0, 0.0, 0.0010, 0.0),
                ("Kp2.5 Ki0 NO notch Kv1e-3", 2.5, 0.0, 0.0010, 0.0),
                ("Kp3.0 Ki0 NO notch Kv1.2e-3", 3.0, 0.0, 0.0012, 0.0),
                ("Kp2.0 Ki0 notch1 Kv6e-4", 2.0, 0.0, 0.0006, 1.0),
                ("Kp2.0 Ki0.6 NO notch Kv1e-3", 2.0, 0.6, 0.0010, 0.0),
                ("Kp2.5 Ki0.6 NO notch Kv1e-3", 2.5, 0.6, 0.0010, 0.0),
                ("Kp2.0 Ki0 NO notch Kv0 (no rate loop)", 2.0, 0.0, 0.0, 0.0),
            ]
            for name, kp, ki, kv, nq in rows:
                r = loop(v, kp, ki, kv, nq, b)
                stiff_tpd = r["a"] + r["kp_a"]      # torque per deg, static, Ki = 0
                res_deg = F / stiff_tpd; res_la = res_deg * r["A"]
                pr("  %-34s | %5.2f %5.2f %6.1f | %5.2f %5.2f %5.2f %5.2f | %6.2f | %6.2f %6.3f"
                   % (name, r["Ms"], r["wc"], r["pm"], r["S01"], r["S02"], r["S05"], r["S10"], r["stiff0"], res_deg, res_la))
    # phase budget at 1 Hz for the flown config, ident b, 19 m/s
    pr("\n" + "=" * 130)
    pr("PHASE BUDGET at the candidate crossover (1 Hz), 19 m/s, ident b: where the 180 deg go")
    v = 19.0; b = B_IDENT[v]; a = float(R3.hold_slope(0.0, v)); J = 1e-4
    w = 2 * np.pi * 1.0; s = 1j * w
    def ph(x): return math.degrees(math.atan2(x.imag, x.real))
    pr("  plant a+bs+Js^2 : %+6.1f deg   (poles at %.2f Hz and %.1f Hz)" % (ph(1 / (a + b * s + J * s * s)), (a / b) / (2 * math.pi), (b / J) / (2 * math.pi)))
    pr("  EPS delay 0.04  : %+6.1f deg" % (-math.degrees(w * 0.04)))
    pr("  meas delay 0.02 : %+6.1f deg" % (-math.degrees(w * 0.02)))
    w0 = 2 * np.pi * float(R3.mode_hz(v)); N = (s ** 2 + w0 ** 2) / (s ** 2 + w0 / 1.0 * s + w0 ** 2)
    pr("  notch Q1 @%.2f Hz: %+6.1f deg  |N| %.2f" % (R3.mode_hz(v), ph(N), abs(N)))
    pr("  Ki 2.5 zero (Ki/Kp): %+6.1f deg" % (ph(1 + (2.5 / 0.85) / s)))
    pr("  Ki 0.6 zero (Ki/Kp): %+6.1f deg" % (ph(1 + (0.6 / 0.85) / s)))
    pr("  b = 0.0006 instead : plant %+6.1f deg (mode at %.2f Hz, zeta %.2f)" % (ph(1 / (a + 0.0006 * s + J * s * s)), math.sqrt(a / J) / (2 * math.pi), 0.0006 / (2 * math.sqrt(a * J))))
    out = os.path.join(HERE, "V293-REV5-LOOPSHAPE-2026-09-15.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)


if __name__ == "__main__":
    main()
