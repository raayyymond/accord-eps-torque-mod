# -*- coding: utf-8 -*-
"""v293r2_loop.py -- frequency-domain loop analysis of the fork's Accord torque controller (any config,
with or without the candidate 100 Hz inner loop) on the V293 plant.  2026-09-14, orchestrator's own.

Angle-domain model (everything in openpilot torque units, degrees, seconds):
    plant     u -> theta :   P(s) = e^{-s Td} / (a + b s + J s^2)          (a,b,F from the joint fit; J, Td from the delay read)
    fork P/I  torque per degree of angle error:
                Kp_a(v) = (SteerKP + lsf(v)) / LAF * A(v)        A(v) = m/s^2 of lat accel per degree (vehicle model)
                Ki_a(v) = Ki * (1 + lsf(v)/SteerKP) / LAF * A(v)
    inner loop (candidate, code):  Ka(v) * (theta_des - theta) + Kd(v) * (theta_des_rate - theta_rate) / (1 + s tau_d)
    relay: nonlinear, not in L(s) (describing function elsewhere)
    L(s) = [Kp_a + Ka + Ki_a/s + Kd s/(1+s tau_d)] * P(s)
The reference path (setpoint filter, feedforward) does not enter L(s).
"""
import math
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v293r2_simlib as S


def A_of(v, sr_level=16.88, angle_deg=10.0):
    return S.lat_accel_per_deg(v, S.steer_ratio(angle_deg, sr_level))


def gains(v, laf, kp, ki, ka=0.0, kd=0.0):
    L = S.lsf(v)
    A = A_of(v)
    kp_a = (kp + L) / laf * A
    ki_a = ki * (1.0 + L / max(kp, 1e-3)) / laf * A
    return dict(kp_a=kp_a, ki_a=ki_a, ka=ka, kd=kd, A=A, lsf=L)


def loop(v, laf, kp, ki, a, b, J=0.0, Td=0.1, ka=0.0, kd=0.0, tau_d=0.02, f=None):
    f = np.logspace(-2, 1.3, 1200) if f is None else f
    s = 1j * 2 * np.pi * f
    G = gains(v, laf, kp, ki, ka, kd)
    C = G["kp_a"] + G["ka"] + G["ki_a"] / s + G["kd"] * s / (1 + s * tau_d)
    P = np.exp(-s * Td) / (a + b * s + J * s ** 2)
    Lw = C * P
    Sw = 1 / (1 + Lw)
    Tw = Lw / (1 + Lw)
    mag = np.abs(Lw)
    # crossover: first |L| = 1 crossing from above
    idx = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(idx):
        k = idx[0]
        wc = f[k]
        pm = 180 + np.degrees(np.angle(Lw[k]))
        pm = ((pm + 180) % 360) - 180
    else:
        wc, pm = np.nan, np.nan
    Ms = float(np.max(np.abs(Sw)))
    # gain margin: |L| at the phase crossover
    ph = np.unwrap(np.angle(Lw))
    pc = np.where((ph[:-1] > -np.pi) & (ph[1:] <= -np.pi))[0]
    gm = 1 / mag[pc[0]] if len(pc) else np.inf
    # closed-loop bandwidth (|T| = -3 dB)
    tb = np.where(np.abs(Tw) < 10 ** (-3 / 20))[0]
    bw = f[tb[0]] if len(tb) else np.nan
    # peak of |T|
    Mt = float(np.max(np.abs(Tw)))
    # disturbance stiffness: torque per degree at DC excluding the integrator, and at 0.3 Hz including it
    k03 = int(np.argmin(np.abs(f - 0.3)))
    stiff_p = a + G["kp_a"] + G["ka"]
    stiff_03 = abs(a + b * s[k03] + J * s[k03] ** 2 + C[k03] * np.exp(-s[k03] * Td))
    return dict(f=f, L=Lw, S=Sw, T=Tw, wc=wc, pm=pm, gm=gm, Ms=Ms, Mt=Mt, bw=bw, stiff_p=stiff_p,
                stiff_03=float(stiff_03), G=G)


def table(rows, plant_fn, configs, title=""):
    print(title)
    print("  %-14s %5s | %6s %6s %6s %6s | %6s %6s %6s | %8s %8s %8s | %6s %5s" %
          ("cfg", "v", "Kp_a", "Ki_a", "Ka", "Kd", "a", "b", "Td", "wc Hz", "PM", "Ms", "stiffP", "bw"))
    for cfg in configs:
        for v in rows:
            p = plant_fn(v)
            r = loop(v, cfg["laf"], cfg["kp"], cfg["ki"], p["a"], p["b"], p.get("J", 0.0), p.get("Td", 0.1),
                     cfg.get("ka_fn", lambda v: 0.0)(v), cfg.get("kd_fn", lambda v: 0.0)(v), cfg.get("tau_d", 0.02))
            g = r["G"]
            print("  %-14s %5.1f | %6.4f %6.4f %6.4f %6.4f | %6.4f %6.4f %6.3f | %8.3f %8.1f %8.2f | %6.4f %5.2f" %
                  (cfg["name"], v, g["kp_a"], g["ki_a"], g["ka"], g["kd"], p["a"], p["b"], p.get("Td", 0.1),
                   r["wc"], r["pm"], r["Ms"], r["stiff_p"], r["bw"]))


if __name__ == "__main__":
    def plant_r70(v):
        return dict(a=S.plant_at(v, "a"), b=S.plant_at(v, "b"), F=S.plant_at(v, "F"), Td=0.10)
    cfgs = [dict(name="rev1", laf=6.0, kp=0.3, ki=0.15), dict(name="rev2", laf=14.0, kp=0.85, ki=0.30)]
    table([3.0, 4.5, 8.0, 12.0, 18.9, 22.8, 26.0], plant_r70, cfgs, "route-70 plant, Td 0.10 s assumed")
