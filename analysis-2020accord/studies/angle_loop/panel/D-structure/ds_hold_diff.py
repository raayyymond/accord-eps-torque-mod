# -*- coding: utf-8 -*-
"""ds_hold_diff.py -- D1's first question, answered with arithmetic: does the 100 Hz sample-and-hold of gp-0x6a00 make a
1-tick difference useless as a D operand?  (1) the same-frequency fundamental of Delta(theta_h) vs the true rate, vs the
held rate x (gp-0x6a56 = held EMA) and the fresh EMA gp-0x6abe and the fresh accumulator difference; (2) the share of the
operand's power that is NOT the fundamental (the 100 Hz carrier and its aliases) for a 1 Hz motion; (3) the quantum: one
0.1 deg count of theta_h through each D form, in lane S counts and in delivered T counts (output lag peak).
ANALYSIS ONLY.  usage: python ds_hold_diff.py  (writes ds_hold_diff_out.txt)"""
import numpy as np
import ds_model as M
L = []
P = lambda s="": (print(s), L.append(s))
TS = 1e-3
P("(1) fundamental of each D operand per deg/s of true wheel rate (magnitude, phase deg; ideal = 1 at 0 deg)")
P("    f Hz   dTheta_h(1 tick)x1000  held x/8 (EMA, hold)   fresh EMA gp-0x6abe   fresh d-diff gp-0x6cc4")
for f in (1, 2, 5, 10, 13, 20, 30):
    w = 2 * np.pi * f
    z1 = np.exp(-1j * w * TS)
    H = np.mean([z1 ** a for a in range(1, 11)])
    ema = M.ALPHA / (1 - (1 - M.ALPHA) * z1)
    d1 = (1 - z1) * H * 1000 / (1j * w)           # Delta of the HELD angle, per tick, x1000 -> deg/s
    xh = H * ema
    fd = (1 - z1) * 1000 / (1j * w)
    row = [d1, xh, ema, fd]
    P(f"   {f:4g}   " + "   ".join(f"{abs(c):.3f} <{np.degrees(np.angle(c)):+6.1f}" for c in row))
P("   => the 1-tick difference of the HELD angle has the SAME fundamental as a 10 ms average rate (= (z^-1 - z^-11)/10 ms),")
P("      within 0.5 deg of the held EMA rate's phase at <= 20 Hz: the hold does NOT make it useless in the loop.")
P("")
P("(2) a 1 Hz, 10 deg/s-amplitude motion: power of the 1-tick held difference that is NOT at 1 Hz (carrier + aliases)")
n = 200000
t = np.arange(n) * TS
th = (10 / (2 * np.pi)) * np.sin(2 * np.pi * t)        # deg
thh = np.empty(n)
cur = 0.0
for k in range(n):
    thh[k] = cur
    if k % 10 == 4:
        cur = th[k]
d = np.diff(thh, prepend=thh[0]) * 1000
fund = 2 * np.mean(d * np.cos(2 * np.pi * t)) * np.cos(2 * np.pi * t) + 2 * np.mean(d * np.sin(2 * np.pi * t)) * np.sin(2 * np.pi * t)
P(f"   rms(operand) {np.sqrt(np.mean(d ** 2)):.1f} deg/s ; rms(fundamental) {np.sqrt(np.mean(fund ** 2)):.2f} ; "
  f"non-fundamental share of power {1 - np.mean(fund ** 2) / np.mean(d ** 2):.3f}")
# through the output lag (S -> y): the carrier is at 100 Hz
z1 = np.exp(-1j * 2 * np.pi * 100 * TS)
Hout100 = abs((M.OB / 1024) * (1 + z1) / (32 * (1 - (M.OA / 1024) * z1)))
Hout0 = (M.OB / 1024) * 2 / (32 * (1 - M.OA / 1024))
P(f"   output lag gain at 100 Hz / DC: {Hout100:.4f} / {Hout0:.4f} = {Hout100 / Hout0:.4f}  (-{-20 * np.log10(Hout100 / Hout0):.0f} dB)")
P("")
P("(3) one 0.1 deg count of theta_h, the quantum each D form delivers (D gain set to 20 S per deg/s at DC)")
# D1a: D on E, Kd_E s.t. D = 0.02 Kd_E g per deg/s = 20 -> Kd_E g = 1000 ; one count -> dE' = 16 g ; D = Kd_E/8 * 16 g = 2 Kd_E g
for nm, imp in (("D1a D on E (1 tick)", 2000.0), ("D1c held diff, 21 Hz LP (spread over ~8 ticks)", None),
                ("B0 / D2a rate operands (no angle quantum)", 0.0)):
    if imp is None:
        P(f"   {nm}: peak S {2000.0 * (1 / 8):.0f} decaying at 21 Hz (same area as D1a's impulse)")
        continue
    y_pk = imp * (M.OB / 1024) / 32
    P(f"   {nm}: S impulse {imp:.0f} for 1 tick -> y peak {y_pk:.1f} -> T peak {M.FWD * y_pk * M.FADE:.1f} T counts "
      f"(area = {imp * 1e-3 / 20 * 10:.3f} deg/s x s of D, exact)")
P("   P on the same count (Kp_eff 500): a STEP of 31 S counts = 5.0 T counts held until the next count.")
P("   D1b fine accumulator: one motor count (1/278.5 deg) -> S impulse 72 x 8 / 8 = 72 for 1 tick -> T peak "
  f"{M.FWD * 72 * (M.OB / 1024) / 32 * M.FADE:.2f}")
open("ds_hold_diff_out.txt", "w", encoding="utf-8").write("\n".join(L))
