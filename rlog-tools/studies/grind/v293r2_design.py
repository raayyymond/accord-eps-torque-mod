# -*- coding: utf-8 -*-
"""v293r2_design.py -- candidate fork controllers for the V293 torque-mode EPS, simulated on the plant
identified from routes 70 + 71 (2026-09-14, orchestrator's own).

Plant (all torque units, deg, s):  J*th'' + b*th' + S(v,th) + F*sign(th') = u(t - Td_eps),  measured angle/rate
delayed by Td_meas.  S(v,th) = the measured hold map (spring part, r70r71_hold_joint_fit), J 8e-5, b 0.0006
(the 2 Hz mode: zeta ~0.25-0.35), F 0.015 (between the kinetic 0.012 and the static ~0.02), Td_eps 0.04, Td_meas 0.02.

Candidates (each = the fork's exact chain + the change):
  rev2      as flown on route 71 (linear tables, SteerFriction relay 0.011, LAF 14, Kp 0.85, Ki 0.30, rg 0.5)
  A  hold-map FF, relay off              (model fix only)
  B  A + hysteresis static-friction FF   (F_s 0.020, band 3 deg, driven by the desired angle)
  C  B + 100 Hz rate loop Kv 0.0004      (torque per deg/s on angle_des_rate - measured rate, 5 Hz LPF)
  D  B + rate loop Kv 0.0006
  E  D + error LPF 0.12 s + SteerKP 1.5
  F  D + error LPF 0.12 s + SteerKP 2.0
Tests per speed: T1 hard-curve hold with a 0.05-torque kick (limit cycle?); T2 1 m/s^2 planner-limited step
(overshoot); T3 0.05-torque disturbance step on a straight ("loose": deflection at 1 s / 5 s); T4 kick ring-down
on a straight (mode damping: log decrement).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293r2_simlib as S  # noqa: E402

P = json.load(open(os.path.join(HERE, "_scratch", "hold_fit_params.json")))
VK = np.array(P["VK"]); KV = np.array(P["k"]); CA, CB, CC = P["ths"]
# smoothed (monotone) k(v) for the feedforward table -- the fitted knots wobble at 12.5/15 from sparse cells
KV_SMOOTH = np.array([0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0134])


def ths_of(v):
    return CA + CB * math.exp(-v / CC)


def spring_true(theta, v, scale=1.0):
    """the plant's spring torque (fitted knots, unsmoothed) -- signed"""
    k = float(np.interp(v, VK, KV)) * scale
    t = ths_of(v)
    return k * t * math.tanh(theta / t)


def hold_ff(theta, v):
    """the fork feedforward's hold: the smoothed table"""
    k = float(np.interp(v, VK, KV_SMOOTH))
    t = ths_of(v)
    return k * t * math.tanh(theta / t)


PLANT = dict(J=8e-5, b=0.0006, F=0.015, dead=0.04, meas_delay=0.02)


def mk(name, laf=14.0, kp=0.85, ki=0.30, fric=0.0, rg=0.5, hold=True, hyst=0.0, kv=None, tau_v=0.03, err_tau=0.0, ref_tau=0.0):
    return S.Cfg(name, laf, kp, ki, fric, rate_gain=rg, hold_fn=hold_ff if hold else None,
                 fric_hyst=hyst, fric_band=3.0, il_kd=(lambda v, k=kv: k) if kv else None, il_tau=tau_v,
                 err_tau=err_tau, ref_tau=ref_tau)


CANDS = [
    mk("rev2", fric=0.011, hold=False),
    mk("D", hold=True, hyst=0.020, kv=0.0006),
    mk("Dki6", hold=True, hyst=0.020, kv=0.0006, ki=0.6),
    mk("Dki9", hold=True, hyst=0.020, kv=0.0006, ki=0.9),
    mk("Dr10", hold=True, hyst=0.020, kv=0.0006, ref_tau=0.10),
    mk("Dr15", hold=True, hyst=0.020, kv=0.0006, ref_tau=0.15),
    mk("Dr15k6", hold=True, hyst=0.020, kv=0.0006, ref_tau=0.15, ki=0.6),
    mk("Dr15k6v8", hold=True, hyst=0.020, kv=0.0008, tau_v=0.02, ref_tau=0.15, ki=0.6),
    mk("Dr15k6rg0", hold=True, hyst=0.020, kv=0.0006, ref_tau=0.15, ki=0.6, rg=0.0),
]


def run(cfg, v, curv_fn, T, dist_fn=None, spring_scale=1.0, **over):
    pl = dict(PLANT); pl.update(over)
    return S.run(cfg, v, curv_fn, T=T, a=0.01, b=pl["b"], F=pl["F"], dead=pl["dead"], J=pl["J"],
                 meas_delay=pl["meas_delay"], spring_fn=lambda th, vv: spring_true(th, vv, spring_scale), dist_fn=dist_fn)


def t1_cycle(cfg, v, la, **over):
    kick = lambda t: 0.05 if 8.0 <= t < 8.3 else 0.0
    o = run(cfg, v, lambda t: la / v ** 2, 22.0, dist_fn=kick, **over)
    tail = o[-800:]
    x = tail[:, 2] - tail[:, 2].mean(); pk = x.max() - x.min()
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))); fx = np.fft.rfftfreq(len(x), 0.01)
    fpk = fx[1:][np.argmax(sp[1:])]
    umax = np.abs(o[-800:, 1]).max()
    return pk, fpk, umax, tail[:, 2].mean()


def t2_step(cfg, v, la=1.0, **over):
    o = run(cfg, v, lambda t: (la / v ** 2) if t > 2 else 0.0, 8.0, **over)
    fin = o[-1, 2]; pk = o[:, 2].max(); k = int(np.argmax(o[:, 2]))
    # settling: last time |phi - fin| > 5 % of fin
    dev = np.abs(o[:, 2] - fin) > 0.05 * abs(fin)
    ts = (np.where(dev)[0][-1] * 0.01 - 2.0) if dev.any() else 0.0
    return fin, (pk - fin) / max(abs(fin), 1e-6), o[k, 0] - 2, ts


def t3_dist(cfg, v, **over):
    o = run(cfg, v, lambda t: 0.0, 8.0, dist_fn=lambda t: 0.05 if t > 2 else 0.0, **over)
    return o[300, 2], o[700, 2], o[300:, 2].max()


def t4_ring(cfg, v, **over):
    o = run(cfg, v, lambda t: 0.0, 8.0, dist_fn=lambda t: 0.08 if 2.0 <= t < 2.1 else 0.0, **over)
    x = o[210:, 2]
    # log decrement from successive peaks of |x|
    pk = []
    for i in range(1, len(x) - 1):
        if abs(x[i]) > abs(x[i - 1]) and abs(x[i]) >= abs(x[i + 1]) and abs(x[i]) > 0.05:
            pk.append(abs(x[i]))
    if len(pk) >= 3:
        d = np.log(pk[0] / pk[2]) / 2.0
        zeta = d / math.sqrt(4 * math.pi ** 2 + d ** 2)
    else:
        zeta = float("nan")
    return x.max(), zeta, len(pk)


def main():
    speeds = [4.5, 8.0, 12.0, 18.9, 22.8, 28.0]
    la_hard = {4.5: 1.5, 8.0: 1.8, 12.0: 2.2, 18.9: 2.7, 22.8: 2.7, 28.0: 2.5}
    print("PLANT", PLANT)
    print("\nT1  hard-curve hold + 0.05 torque kick: tail angle pk-pk [deg] @ f [Hz], |u|max   (LIMIT CYCLE if pk-pk > 1 deg)")
    print("%-9s" % "cfg" + "".join("%18s" % ("v %.1f" % v) for v in speeds))
    for c in CANDS:
        row = "%-9s" % c.name
        for v in speeds:
            pk, f, um, mean = t1_cycle(c, v, la_hard[v])
            row += " %6.2fdeg %4.2fHz %3.2f" % (pk, f, um)
        print(row)
    print("\nT2  1 m/s^2 planner-limited step: overshoot %, time-to-peak s, 5%-settling s")
    print("%-9s" % "cfg" + "".join("%18s" % ("v %.1f" % v) for v in speeds))
    for c in CANDS:
        row = "%-9s" % c.name
        for v in speeds:
            fin, ov, tp, ts = t2_step(c, v)
            row += " %+5.0f%% %4.2fs %5.2fs" % (100 * ov, tp, ts)
        print(row)
    print("\nT3  0.05 torque disturbance step on a straight: angle deflection at 1 s / 5 s [deg]  (LOOSE)")
    print("%-9s" % "cfg" + "".join("%18s" % ("v %.1f" % v) for v in speeds))
    for c in CANDS:
        row = "%-9s" % c.name
        for v in speeds:
            d1, d5, dmax = t3_dist(c, v)
            row += " %6.2f / %5.2f (%4.2f)" % (d1, d5, dmax)
        print(row)
    print("\nT4  0.08 torque, 0.1 s kick on a straight: peak [deg], damping ratio of the ring-down, number of peaks")
    print("%-9s" % "cfg" + "".join("%18s" % ("v %.1f" % v) for v in speeds))
    for c in CANDS:
        row = "%-9s" % c.name
        for v in speeds:
            pk, z, n = t4_ring(c, v)
            row += " %6.2f z%5.2f n%2d " % (pk, z, n)
        print(row)
    print("\nROBUSTNESS of T1 (cycle pk-pk deg) at 18.9 and 22.8 m/s: b 0.0004 | J 1e-4 | delays x1.5 | plant spring x0.8 | x1.25")
    for c in CANDS:
        row = "%-9s" % c.name
        for v in (18.9, 22.8):
            vals = []
            for over in (dict(b=0.0004), dict(J=1.0e-4), dict(dead=0.06, meas_delay=0.03), dict(), dict()):
                pass
            r1 = t1_cycle(c, v, la_hard[v], b=0.0004)[0]
            r2 = t1_cycle(c, v, la_hard[v], J=1.0e-4)[0]
            r3 = t1_cycle(c, v, la_hard[v], dead=0.06, meas_delay=0.03)[0]
            r4 = t1_cycle(c, v, la_hard[v], spring_scale=0.8)[0]
            r5 = t1_cycle(c, v, la_hard[v], spring_scale=1.25)[0]
            row += "  v%4.1f: %5.2f %5.2f %5.2f %5.2f %5.2f |" % (v, r1, r2, r3, r4, r5)
        print(row)


if __name__ == "__main__":
    main()
