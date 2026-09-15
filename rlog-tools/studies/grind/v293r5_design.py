# -*- coding: utf-8 -*-
"""v293r5_design.py -- rev-5 candidates for the fork's Accord torque controller on the V293 EPS (orchestrator's own,
2026-09-15).  Motivated by the rev-4 drive (route 75): still loose / jerky on hard turns / "the command has to overshoot
to get over friction" / avoid Ki-heavy tuning (a variable delay).

Structural point (v293r5_loopshape.py): a P loop through a 60 ms round trip has a static stiffness of (1 + kp_a/a) --
1.7 today, ~3 at the most Kp the margins allow -- so a wrong hold level, a road crown or the friction leaves an error
of 1/stiffness x the torque error, whatever Kp does.  A 1 kHz rate servo made the plant type-1 to openpilot.  The
integrator gets type-1 back but at a corner (Ki/Kp) the loop's own phase caps at 0.2-0.5 Hz = the catch-up he feels.

Candidate: a model-based DISTURBANCE OBSERVER (DOB).  The unmodelled torque w = hold_m(angle) + b_m rate + J_m acc
- u(t - Td) is estimated from the measured wheel state and the controller's own past output, low-passed (Q, two
poles at f_Q) and added to the feedforward.  Its loop is closed only through the MODEL MISMATCH (|Q| |P/P_m - 1| < 1),
not through the plant's phase, so f_Q can sit at ~1 Hz -- 3-5x the integrator's corner -- and the reference path
keeps the P + FF response (no catch-up).  Tested here on the nonlinear plant with stiction, under both damping
hypotheses (b = 0.0006 "mode" vs the ident's b), hold NEED x1.0 / x1.5, delays x1.5.
Tests at 12 / 19 / 26 m/s:
  T1 straight, 0.03-torque disturbance step: |e| at 0.5 / 1 / 2 s, rms 0-4 s (m/s^2)
  T2 planner step 0 -> 1 m/s^2: 90 % rise, overshoot, rms 0-4 s
  T3 2 m/s^2 hold + 0.05-torque kick: tail pk-pk angle (limit cycle?)
  T5 STICTION: slow planner ramp 0 -> 0.6 m/s^2 over 6 s, F x1.5 (0.018): rms planner error, peak rate (snap), number
     of dwell-then-jump events (rate < 0.3 deg/s for >= 0.3 s followed by |rate| > 5 deg/s), max |error| (m/s^2)
  T6 HOLD LEVEL: 1.5 m/s^2 curve entered by the planner's own ramp, hold NEED x1.5: |e| at 1 / 2 / 4 s after the ramp
  T4 linear margins (from v293r5_loopshape.loop): Ms, wc, PM
ANALYSIS ONLY.
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r2_simlib as S
import v293r3_read as R3
import v293r5_loopshape as LS

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DT = S.DT
LAT_DELAY = 0.274
B_IDENT_BP = [8.0, 12.0, 19.0, 26.0]
B_IDENT_V = [0.0018, 0.0037, 0.0041, 0.0049]
def b_ident(v):
    return float(np.interp(v, B_IDENT_BP, B_IDENT_V))

WORLDS = {
    "mode (b .0006, J 1e-4)": dict(J=1.0e-4, bfn=lambda v: 0.0006, F=0.012, dead=0.04, meas_delay=0.02),
    "ident (b F1, J 1e-4)":   dict(J=1.0e-4, bfn=b_ident, F=0.012, dead=0.04, meas_delay=0.02),
    "ident, delays x1.5":     dict(J=1.0e-4, bfn=b_ident, F=0.012, dead=0.06, meas_delay=0.03),
}

OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)

def hold_ff_scaled(scale):
    return lambda th, v: scale * float(R3.hold_torque(th, v))

def ki_sched(v, lo, hi):
    if hi <= 0: return lo
    return float(np.interp(v, [8.0, 18.0], [lo, hi]))

def mk(name, kp=0.85, ki=0.6, ki_hi=2.5, ref=0.12, kv=0.0006, notch_q=1.0, hyst=0.015, dob=0.0, dob_b="ident", dob_J=True, dob_max=0.3):
    def make(v):
        return S.Cfg(name, 14.0, kp, ki_sched(v, ki, ki_hi), 0.0, rate_gain=0.5, hold_fn=hold_ff_scaled(1.0), fric_hyst=hyst, fric_band=3.0,
                     il_kd=(lambda vv, k=kv: k) if kv else None, il_tau=0.03,
                     kv_taper=lambda vv: min(1.0, 12.0 / max(vv, 0.1)), notch_q=notch_q,
                     notch_fn=lambda vv: float(R3.mode_hz(vv)), ref_tau=ref, lat_delay=LAT_DELAY,
                     dob_fc=dob, dob_td=0.06, dob_b=(b_ident if dob_b == "ident" else (lambda vv, bb=dob_b: bb)), dob_J=1.0e-4,
                     dob_use_J=dob_J, dob_max=dob_max)
    make.name = name
    return make

CANDS = [
    mk("R4-flown"),
    mk("R4+DOB.8 Ki.3flat", ki=0.3, ki_hi=0.0, dob=0.8),
    mk("R4+DOB.8 Ki0", ki=0.0, ki_hi=0.0, dob=0.8),
    mk("Kp1.5 notch DOB.8 Ki.3", kp=1.5, ki=0.3, ki_hi=0.0, dob=0.8),
    mk("Kp2 NOnotch Kv1e-3 DOB1 Ki.3", kp=2.0, ki=0.3, ki_hi=0.0, kv=0.001, notch_q=0.0, dob=1.0),
    mk("Kp2 NOnotch Kv1e-3 DOB1 Ki0", kp=2.0, ki=0.0, ki_hi=0.0, kv=0.001, notch_q=0.0, dob=1.0),
    mk("Kp2 NOnotch Kv1e-3 DOB.6 Ki.3", kp=2.0, ki=0.3, ki_hi=0.0, kv=0.001, notch_q=0.0, dob=0.6),
    mk("Kp2 NOnotch Kv1e-3 DOB1.5 Ki.3", kp=2.0, ki=0.3, ki_hi=0.0, kv=0.001, notch_q=0.0, dob=1.5),
    mk("Kp2 NOnotch Kv1e-3 Ki.6 noDOB", kp=2.0, ki=0.6, ki_hi=0.0, kv=0.001, notch_q=0.0),
    mk("Kp1.5 notch DOB.8 Ki.3 noJ", kp=1.5, ki=0.3, ki_hi=0.0, dob=0.8, dob_J=False),
]


def run(cfgf, v, curv_fn, T, world, need=1.0, dist_fn=None, Fscale=1.0):
    w = world
    return S.run(cfgf(v), v, curv_fn, T=T, a=0.01, b=w["bfn"](v), F=w["F"] * Fscale, dead=w["dead"], J=w["J"],
                 meas_delay=w["meas_delay"], dist_fn=dist_fn,
                 spring_fn=lambda th, vv, n=need: n * float(R3.hold_torque(th, vv)))


def t1(cfgf, v, world, need):
    out = run(cfgf, v, lambda t: 0.0, T=8.0, world=world, need=need, dist_fn=lambda t: 0.03 if t >= 2.0 else 0.0)
    e = -out[:, 3]; k0 = int(2.0 / DT)
    vals = [abs(e[k0 + int(x / DT)]) for x in (0.5, 1.0, 2.0)]
    return vals + [float(np.sqrt(np.mean(e[k0:k0 + int(4 / DT)] ** 2)))]


def t2(cfgf, v, world, need):
    c1 = 1.0 / v ** 2
    out = run(cfgf, v, lambda t: c1 if t >= 1.0 else 0.0, T=8.0, world=world, need=need)
    meas = out[:, 3]; k0 = int(1.0 / DT)
    idx90 = np.where(meas[k0:] >= 0.9)[0]
    rise = idx90[0] * DT if len(idx90) else np.nan
    ov = float(np.max(meas[k0:]) - 1.0)
    e = 1.0 - meas[k0:k0 + int(4 / DT)]
    return [rise, ov, float(np.sqrt(np.mean(e ** 2)))]


def t3(cfgf, v, world, need):
    c2 = 2.0 / v ** 2
    out = run(cfgf, v, lambda t: c2, T=12.0, world=world, need=need, dist_fn=lambda t: 0.05 if 6.0 <= t < 6.1 else 0.0)
    phi = out[:, 2]; tail = phi[int(8 / DT):]
    return [float(tail.max() - tail.min())]


def t5(cfgf, v, world, need):
    """stiction: slow planner ramp 0 -> 0.6 m/s^2 over 6 s (t = 1..7), F x1.5.  planner error vs the planner's own
    (jerk-limited) desire = the sim's internal curv * v^2 -- reconstructed from the command since the ramp is slow."""
    la = 0.6
    out = run(cfgf, v, lambda t: (la * min(max((t - 1.0) / 6.0, 0.0), 1.0)) / v ** 2, T=10.0, world=world, need=need, Fscale=1.5)
    t = out[:, 0]; meas = out[:, 3]; rate = out[:, 5]
    des = la * np.clip((t - 1.0 - 0.0) / 6.0, 0.0, 1.0)
    e = des - meas
    sel = (t >= 1.0) & (t <= 9.0)
    # dwell-then-jump: |rate| < 0.3 deg/s for >= 0.3 s then |rate| > 5 deg/s within 0.3 s
    still = np.abs(rate) < 0.3
    n_dwell = 0; i = 0; n = len(rate)
    while i < n:
        if still[i] and sel[i]:
            j = i
            while j < n and still[j]: j += 1
            if (j - i) * DT >= 0.3:
                k1 = min(n, j + int(0.3 / DT))
                if np.max(np.abs(rate[j:k1])) > 5.0 if k1 > j else False:
                    n_dwell += 1
            i = j
        else:
            i += 1
    return [float(np.sqrt(np.mean(e[sel] ** 2))), float(np.max(np.abs(rate[sel]))), n_dwell, float(np.max(np.abs(e[sel])))]


def t6(cfgf, v, world):
    """hold level: planner ramps to 1.5 m/s^2 over 2 s (t = 1..3); the true hold is x1.5 the map.  |e| at 1/2/4 s after the ramp end."""
    la = 1.5
    out = run(cfgf, v, lambda t: (la * min(max((t - 1.0) / 2.0, 0.0), 1.0)) / v ** 2, T=9.0, world=world, need=1.5)
    t = out[:, 0]; meas = out[:, 3]
    e = la - meas
    return [abs(e[int((3.0 + x) / DT)]) for x in (1.0, 2.0, 4.0)]


def main():
    pr("v293r5_design -- rev-5 candidates on the nonlinear V293 plant (hold map, Coulomb F 0.012, stiction, 100 Hz loop, honda limiter).")
    pr("DOB model: fork hold map x1.0, b = ident F1 table, J 1e-4, Td 0.06, two poles at f_Q, clip +-0.3; frozen when limited/pressed.")
    for wname, world in WORLDS.items():
        for need in (1.0, 1.5):
            pr("\n" + "=" * 150)
            pr("WORLD %s | hold NEED x%.1f the map" % (wname, need))
            pr("  %-30s %3s | %-30s | %-22s | %-7s | %-34s | %-18s | %-14s" % ("cfg", "v", "T1 dist |e| .5 1 2 s, rms", "T2 rise ov rms", "T3 pkpk", "T5 stiction: rms e, pk rate, dwells, max|e|", "T6 |e| 1 2 4 s", "T4 Ms wc PM"))
            for cf in CANDS:
                for v in (12.0, 19.0, 26.0):
                    a1 = t1(cf, v, world, need); a2 = t2(cf, v, world, need); a3 = t3(cf, v, world, need)
                    a5 = t5(cf, v, world, need)
                    a6 = t6(cf, v, world) if need == 1.5 else [np.nan] * 3
                    c = cf(v)
                    ms, wc, pm = [np.nan] * 3
                    if c.dob_fc == 0.0:
                        r = LS.loop(v, c.KP, c.KI, (0.0006 if c.il_kd else 0.0) if c.il_kd is None else c.il_kd(v), c.notch_q, world["bfn"](v),
                                    J=world["J"], dead=world["dead"], meas=world["meas_delay"], need=need)
                        ms, wc, pm = r["Ms"], r["wc"], r["pm"]
                    pr("  %-30s %3.0f | %6.3f %6.3f %6.3f %6.3f    | %5.2f %+6.2f %6.3f    | %6.2f  | %6.3f %7.1f %3d %6.3f            | %5.3f %5.3f %5.3f  | %5.2f %5.2f %6.1f"
                       % (cf.name, v, *a1, *a2, a3[0], *a5, *a6, ms, wc, pm))
    out = os.path.join(HERE, "V293-REV5-DESIGN-SWEEP-2026-09-15.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)


if __name__ == "__main__":
    main()
