# -*- coding: utf-8 -*-
"""v293r5_design_pred.py -- can the 100 Hz rate loop damp the 2-2.7 Hz mode if it closes on a MODEL-PREDICTED wheel rate?
(orchestrator's own, 2026-09-15, after the real rev-4 drive r75 showed the hard-turn jerk IS the lightly damped closed-loop
mode: rate bursts every 0.53 s, torque command +6.9 dB at 1.95 Hz at v < 10; des->act |H| 2.3 at 2 Hz at 10-20 m/s.)

Through the 60 ms round trip plus the 30 ms measurement filter a rate damper has phase -(w*Td + atan(w*RC)): it damps
below ~2.8 Hz and PUMPS 3-5 Hz (the +2.6..+4 dB 3-5.5 Hz rate hump in S3).  The predictor propagates the measured
(angle, rate) forward through the observer's model, driven by the outputs still in flight, so the damper acts at the phase
the wheel will have when the torque lands.  Model mismatch is the risk: the worlds below deliberately mismatch b (x3-8),
J (x1.5), the delay (x1.5) and the hold map (x1.5).
Tests: T3 kick (ringing pk-pk), T5 slow ramp stiction, T7 small step, T8 HARD TURN (0 -> 2.5 m/s^2 in 1.5 s, hold, back).
ANALYSIS ONLY.
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r2_simlib as S
import v293r3_read as R3
import v293r5_design as D
import v293r5_design_lowspeed as DL
import v293_ident_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DT = S.DT
OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)

WORLDS = dict(D.WORLDS)
WORLDS["mode, delays x1.5"] = dict(J=1.0e-4, bfn=lambda v: 0.0006, F=0.012, dead=0.06, meas_delay=0.03)
WORLDS["mode, J x1.5"] = dict(J=1.5e-4, bfn=lambda v: 0.0006, F=0.012, dead=0.04, meas_delay=0.02)


def mk(name, kp=1.2, ki=0.3, ki_hi=0.0, ref=0.12, kv=0.0006, rc=0.03, notch_q=1.0, hyst=0.015, dob=0.8, dob_b="ident",
       pred=0.0, pred_F=0.0, dob_max=0.3):
    def make(v):
        return S.Cfg(name, 14.0, kp, D.ki_sched(v, ki, ki_hi), 0.0, rate_gain=0.5, hold_fn=D.hold_ff_scaled(1.0), fric_hyst=hyst,
                     fric_band=3.0, il_kd=(lambda vv, k=kv: k) if kv else None, il_tau=rc,
                     kv_taper=lambda vv: min(1.0, 12.0 / max(vv, 0.1)), notch_q=notch_q,
                     notch_fn=lambda vv: float(R3.mode_hz(vv)), ref_tau=ref, lat_delay=D.LAT_DELAY,
                     dob_fc=dob, dob_td=0.06, dob_b=(D.b_ident if dob_b == "ident" else (lambda vv, bb=dob_b: bb)), dob_J=1.0e-4,
                     dob_use_J=True, dob_max=dob_max, il_pred_td=pred, il_pred_F=pred_F)
    make.name = name
    return make


CANDS = [
    D.mk("R4-flown"),
    mk("R5 base (rc.03 Kv6e-4)"),
    mk("R5 rc.01", rc=0.01),
    mk("R5 rc.01 Kv1e-3", rc=0.01, kv=0.001),
    mk("R5 pred.06 Kv6e-4", rc=0.01, pred=0.06),
    mk("R5 pred.06 Kv1e-3", rc=0.01, kv=0.001, pred=0.06),
    mk("R5 pred.06 Kv1.5e-3", rc=0.01, kv=0.0015, pred=0.06),
    mk("R5 pred.06 Kv1e-3 F.012", rc=0.01, kv=0.001, pred=0.06, pred_F=0.012),
    mk("R5 pred.09 Kv1e-3", rc=0.01, kv=0.001, pred=0.09),
    mk("R5 pred.06 Kv1e-3 bmode", rc=0.01, kv=0.001, pred=0.06, dob_b=0.0006),
    mk("R5 pred.06 Kv1e-3 noDOB", rc=0.01, kv=0.001, pred=0.06, dob=0.0, ki=0.6, ki_hi=2.5),
]


def run(cfgf, v, curv_fn, T, world, need=1.0, dist_fn=None, Fscale=1.0):
    w = world
    return S.run(cfgf(v), v, curv_fn, T=T, a=0.01, b=w["bfn"](v), F=w["F"] * Fscale, dead=w["dead"], J=w["J"],
                 meas_delay=w["meas_delay"], dist_fn=dist_fn,
                 spring_fn=lambda th, vv, n=need: n * float(R3.hold_torque(th, vv)))


def t8(cfgf, v, world, need, la=2.5, Fscale=1.5):
    def prof(t):
        if t < 1.0: x = 0.0
        elif t < 2.5: x = la * (t - 1.0) / 1.5
        elif t < 5.0: x = la
        elif t < 6.5: x = la * (6.5 - t) / 1.5
        else: x = 0.0
        return x / v ** 2
    out = run(cfgf, v, prof, T=9.0, world=world, need=need, Fscale=Fscale)
    t, u, phi, meas, rate = out[:, 0], out[:, 1], out[:, 2], out[:, 3], out[:, 5]
    des = np.array([prof(tt) * v ** 2 for tt in t])
    e = des - meas
    band = L.bandpass(rate - rate.mean(), 1.6, 3.0)
    rms_mode = float(np.sqrt(np.mean(band[int(1.0 / DT):int(7.5 / DT)] ** 2)))
    ab = np.abs(rate) > 40.0
    bursts = int(np.sum(np.diff(ab.astype(int)) == 1))
    hold = slice(int(3.0 / DT), int(5.0 / DT))
    max_e_hold = float(np.max(np.abs(e[hold])))
    ov = float((np.max(meas[int(2.0 / DT):int(5.0 / DT)]) - la) / la)
    rms_e = float(np.sqrt(np.mean(e[int(1.0 / DT):int(8.0 / DT)] ** 2)))
    # damping power: fraction of frames where the inner-loop torque (col 8, controller frame) opposes the wheel rate
    il = out[:, 8]
    mv = np.abs(rate) > 2.0
    damp = float(np.mean(np.sign(-il[mv]) == np.sign(rate[mv]))) if mv.sum() > 10 else np.nan
    return [rms_mode, bursts, max_e_hold, ov, rms_e, damp]


def main():
    pr("v293r5_design_pred -- rate loop on a MODEL-PREDICTED rate: shortlist x worlds x speeds.  Kp 1.2 notch Q1 DOB .8 Ki .3 flat unless named.")
    for wname, world in WORLDS.items():
        for need in (1.0, 1.5):
            pr("\n" + "=" * 150)
            pr("WORLD %s | hold NEED x%.1f" % (wname, need))
            pr("  %-28s %3s | %-7s | %-36s | %-40s | %-40s" % ("cfg", "v", "T3 pkpk", "T5 stiction rms e, pk rate, dwells, max|e|",
                                                              "T7 step t50 t90 ov pk-rate windup past tail", "T8 HARD TURN mode-rms bursts max|e|hold ov rms-e damp"))
            for cf in CANDS:
                for v in (6.0, 8.0, 12.0, 19.0, 26.0):
                    a3 = D.t3(cf, v, world, need); a5 = D.t5(cf, v, world, need); a7 = DL.t7(cf, v, world, need); a8 = t8(cf, v, world, need)
                    pr("  %-28s %3.0f | %6.2f  | %6.3f %7.1f %3d %6.3f                 | %5.2f %5.2f %+5.2f %6.1f %+7.4f %+6.2f %6.3f | %6.2f %3d %6.3f %+6.3f %6.3f %5.2f"
                       % (cf.name, v, a3[0], *a5, *a7, *a8))
    out = os.path.join(HERE, "V293-REV5-DESIGN-PRED-2026-09-15.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)


if __name__ == "__main__":
    main()
