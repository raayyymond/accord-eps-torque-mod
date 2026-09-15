# -*- coding: utf-8 -*-
"""v293r4_design.py -- rev-4 candidates for the fork's Accord torque controller on the V293 EPS, 2026-09-14
(orchestrator's own).  Motivated by routes 72/73: the rev-3 loop's low-frequency gain is too small to make up the
feedforward's route-to-route hold error (|H| 0.74-0.80 at 0.2 Hz, lag 0.5 s at 15-30 m/s = "loose"), and route 73's
accidental SteerFriction 0.212 relay (small-signal gain ~10x Kp) tracked 2.5x better but chattered at 4 Hz.

Plant (torque units, deg, s): J th'' + b th' + S(v,th) + F sign(th') = u(t - Td); S = NEED x the fork hold map
(NEED 1.0 = the map is right; 1.5 = today's routes).  J 1e-4, b 0.0006 (the 2 Hz mode), F 0.008, Td 0.04 + meas 0.02.
Controller = the fork chain transcribed in v293r2_simlib (hold map FF, hysteresis 0.015, tapered rate loop 0.0006,
error notch Q1 at the mode, two-pole reference filter), lat_delay 0.274 (liveDelay as flown).
Tests at 12 / 19 / 26 m/s:
  T1 straight, 0.03-torque disturbance step (a crown / crosswind bias): lat-accel error at 0.5 / 1 / 2 s, rms 0-4 s
  T2 planner step 0 -> 1 m/s^2: 90 % rise time from the planner step, overshoot, rms planner error 0-4 s
  T3 2 m/s^2 curve hold + 0.05-torque kick: tail pk-pk angle (limit cycle?)
  T4 linear margins with the notch: Ms, PM, crossover
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r2_simlib as S
import v293r3_read as R3

DT = S.DT
PLANT = dict(J=1.0e-4, b=0.0006, F=0.008, dead=0.04, meas_delay=0.02)
LAT_DELAY = 0.274


def hold_ff_scaled(scale):
    return lambda th, v: scale * float(R3.hold_torque(th, v))


def mk(name, kp=0.85, ki=0.6, ref=0.12, ffs=1.0, kv=0.0006, notch_q=1.0, hyst=0.015):
    return S.Cfg(name, 14.0, kp, ki, 0.0, rate_gain=0.5, hold_fn=hold_ff_scaled(ffs), fric_hyst=hyst, fric_band=3.0,
                 il_kd=(lambda v, k=kv: k) if kv else None, il_tau=0.03,
                 kv_taper=lambda v: min(1.0, 12.0 / max(v, 0.1)), notch_q=notch_q,
                 notch_fn=lambda v: float(R3.mode_hz(v)), ref_tau=ref, lat_delay=LAT_DELAY)


CANDS = [
    mk("R3-flown"),
    mk("Ki1.5", ki=1.5),
    mk("Ki2.5", ki=2.5),
    mk("Kp1.1Ki2.5", kp=1.1, ki=2.5),
    mk("Kp1.1Ki2.5r08", kp=1.1, ki=2.5, ref=0.08),
    mk("Kp1.3Ki3r08", kp=1.3, ki=3.0, ref=0.08),
    mk("Kp1.6Ki3r08", kp=1.6, ki=3.0, ref=0.08),
    mk("R3+FF1.3", ffs=1.3),
    mk("Kp1.1Ki2.5r08FF1.3", kp=1.1, ki=2.5, ref=0.08, ffs=1.3),
]


def run(cfg, v, curv_fn, T, need=1.0, dist_fn=None, **over):
    pl = dict(PLANT); pl.update(over)
    return S.run(cfg, v, curv_fn, T=T, a=0.01, b=pl["b"], F=pl["F"], dead=pl["dead"], J=pl["J"],
                 meas_delay=pl["meas_delay"], dist_fn=dist_fn,
                 spring_fn=lambda th, vv, n=need: n * float(R3.hold_torque(th, vv)))


def A_of(v):
    return S.lat_accel_per_deg(v, S.steer_ratio(10.0, 16.88))


def t1(cfg, v, need, **over):
    """straight; 0.03 torque disturbance at t = 2 s.  returns |error| at +0.5/+1/+2 s and rms over 0-4 s after the step."""
    out = run(cfg, v, lambda t: 0.0, T=8.0, need=need, dist_fn=lambda t: 0.03 if t >= 2.0 else 0.0, **over)
    t, meas = out[:, 0], out[:, 3]
    e = -meas   # setpoint 0
    k0 = int(2.0 / DT)
    vals = [abs(e[k0 + int(x / DT)]) for x in (0.5, 1.0, 2.0)]
    return vals + [float(np.sqrt(np.mean(e[k0:k0 + int(4 / DT)] ** 2)))]


def t2(cfg, v, need, **over):
    """planner step 0 -> 1 m/s^2 at t = 1 s (the sim applies clip_curvature's jerk limit)."""
    c1 = 1.0 / v ** 2
    out = run(cfg, v, lambda t: c1 if t >= 1.0 else 0.0, T=8.0, need=need, **over)
    t, meas = out[:, 0], out[:, 3]
    k0 = int(1.0 / DT)
    # the planner's own limited command: replay clip_curvature for the reference (the sim's internal curv)
    idx90 = np.where(meas[k0:] >= 0.9)[0]
    rise = idx90[0] * DT if len(idx90) else np.nan
    ov = float(np.max(meas[k0:]) - 1.0)
    e = 1.0 - meas[k0:k0 + int(4 / DT)]
    return [rise, ov, float(np.sqrt(np.mean(e ** 2)))]


def t3(cfg, v, need, **over):
    """2 m/s^2 curve held from t=0 (pre-wound), 0.05-torque kick for 0.1 s at t = 6 s; tail pk-pk angle 8-12 s."""
    c2 = 2.0 / v ** 2
    out = run(cfg, v, lambda t: c2, T=12.0, need=need,
              dist_fn=lambda t: 0.05 if 6.0 <= t < 6.1 else 0.0, **over)
    phi = out[:, 2]
    tail = phi[int(8 / DT):]
    return [float(tail.max() - tail.min())]


def margins(cfg, v, need, **over):
    """linear loop with the notch and the tapered rate loop; plant linearised at 0 deg."""
    pl = dict(PLANT); pl.update(over)
    a = need * float(R3.hold_slope(0.0, v))
    f = np.logspace(-2, 1.3, 2000); s = 1j * 2 * np.pi * f
    A = A_of(v); L_ = S.lsf(v)
    kp_a = (cfg.KP + L_) / cfg.LAF * A
    ki_a = cfg.KI * (1 + L_ / cfg.KP) / cfg.LAF * A
    w0 = 2 * np.pi * float(R3.mode_hz(v)); q = cfg.notch_q
    N = (s ** 2 + w0 ** 2) / (s ** 2 + w0 / q * s + w0 ** 2) if q > 0 else 1.0
    kd = 0.0006 * min(1.0, 12.0 / v) if cfg.il_kd else 0.0
    C = (kp_a + ki_a / s) * N * np.exp(-s * pl["meas_delay"]) + kd * s / (1 + s * 0.03) * np.exp(-s * pl["meas_delay"])
    P = np.exp(-s * pl["dead"]) / (a + pl["b"] * s + pl["J"] * s ** 2)
    Lw = C * P
    Sw = 1 / (1 + Lw)
    mag = np.abs(Lw)
    idx = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(idx):
        k = idx[-1]; wc = f[k]; pm = ((180 + np.degrees(np.angle(Lw[k])) + 180) % 360) - 180
    else:
        wc, pm = np.nan, np.nan
    return float(np.max(np.abs(Sw))), wc, pm


if __name__ == "__main__":
    import v293_ident_lib as L
    OUT = []; pr = L.pr_factory(OUT)
    for need in (1.0, 1.5):
        for over, lab in ((dict(), "nominal"), (dict(b=0.002, J=1.2e-4, dead=0.06, meas_delay=0.03), "robust: b 0.002, J 1.2e-4, delays x1.5")):
            pr("\n=== plant NEED x%.1f the map, %s ===" % (need, lab))
            pr("  %-20s %3s | %-30s | %-24s | %-8s | %-20s" % ("cfg", "v", "T1 dist: |e| .5s 1s 2s rms(m/s^2)", "T2 step: rise ov rms", "T3 pkpk", "T4 Ms wc PM"))
            for cfg in CANDS:
                for v in (12.0, 19.0, 26.0):
                    a1 = t1(cfg, v, need, **over); a2 = t2(cfg, v, need, **over); a3 = t3(cfg, v, need, **over)
                    Ms, wc, pm = margins(cfg, v, need, **over)
                    pr("  %-20s %3.0f | %6.3f %6.3f %6.3f %6.3f     | %5.2f %+6.2f %6.3f       | %6.2f   | %5.2f %5.2f %6.1f"
                       % (cfg.name, v, *a1, *a2, a3[0], Ms, wc, pm))
    out = os.path.join(HERE, "_scratch", "v293r4_design.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("written " + out)
