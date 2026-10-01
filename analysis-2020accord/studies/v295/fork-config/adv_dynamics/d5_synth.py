# -*- coding: utf-8 -*-
"""d5_synth -- ADV-dynamics (b)(c)(e) in the time domain with the REAL fork controller (d2_engine):
  S1 HUNT      straight road, zero demand, constant crown torque c0 = crown x Fs(member, v) on the plant, 60 s.
  S2 CURVE     5 s straight, 2 s ramp to a*, 20 s hold, 2 s ramp down, straight: hold ratio, curve-exit overshoot /
               settling (integrator wind-up), 2.0-2.7 Hz line and 0.2-1.5 Hz hunt during the hold.
  S3 RESIST    straight road; a light driver torque (NOT flagged steeringPressed) of 150 T on the plant for 4 s, then
               released -> post-release excursion (what the integrator wound up during the push).
  S3P          the same push flagged steeringPressed (integrator frozen; x0.8 on release, latcontrol_torque.py 291-292).
  S5 LANECHG   one full-sine lateral-accel cycle (+-1.5 m/s^2, 4 s), then straight: post-manoeuvre overshoot.
Every config is its own batch with the identical row layout and seed (paired sensor noise).
"""
import os, sys, json, time
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d2_engine as E
import v295_harness as H

OUT = os.path.join(HERE, "out")
SECS = 60.0
fam = H.family()


def ramp_profile(a, t_on=5.0, tr=2.0, hold=20.0):
    t1, t2, t3 = t_on + tr, t_on + tr + hold, t_on + 2 * tr + hold
    def f(t):
        if t < t_on:
            return 0.0
        if t < t1:
            return a * (t - t_on) / tr
        if t < t2:
            return a
        if t < t3:
            return a * (1 - (t - t2) / tr)
        return 0.0
    return f


def lanechange(a=1.5, t_on=10.0, per=4.0):
    return lambda t: a * np.sin(2 * np.pi * (t - t_on) / per) if t_on <= t < t_on + per else 0.0


def build_rows():
    rows = []
    for m in ("nominal", "F_hi", "b_lo", "J_hi", "light_b"):
        for v in (3.1, 5.0, 8.0, 12.0, 17.0, 19.0, 22.0, 26.9):
            Fs = float(fam[m].at(v).Fs)
            for cr in (0.0, 0.6, 1.0, 1.5, 2.5):
                rows.append(dict(kind="S1", member=m, v=v, crown=cr, c0=cr * Fs))
    for m in ("nominal", "F_hi", "b_lo", "J_hi", "light_b"):
        for v in (12.0, 15.0, 17.0, 19.0, 22.0, 26.9):
            for a in (1.0, 2.0):
                rows.append(dict(kind="S2", member=m, v=v, a=a, des=ramp_profile(a)))
    for m in ("nominal", "F_hi", "light_b"):
        for v in (12.0, 19.0, 22.0, 26.9):
            rows.append(dict(kind="S3", member=m, v=v, drv=(lambda t: 150.0 if 10.0 <= t < 14.0 else 0.0)))
            rows.append(dict(kind="S3P", member=m, v=v, drv=(lambda t: 150.0 if 10.0 <= t < 14.0 else 0.0),
                             pressed=(lambda t: 10.0 <= t < 14.0)))
    for m in ("nominal", "F_hi", "b_lo", "J_hi", "light_b"):
        for v in (19.0, 22.0, 26.9):
            rows.append(dict(kind="S5", member=m, v=v, des=lanechange()))
    return rows


def welch_peak(x, lo, hi):
    f, p = signal.welch(x - np.mean(x), fs=100.0, nperseg=min(1024, len(x)))
    m = (f >= lo) & (f <= hi)
    return float(f[m][np.argmax(p[m])])


def score(R, rows):
    out = []
    for j, r in enumerate(rows):
        ang, rate, la = R["ang"][j], R["rate"][j], R["la_act"][j]
        cmd, stuck, ii = R["cmd"][j], R["stuck"][j], R["i"][j]
        s = dict(kind=r["kind"], member=r["member"], v=r["v"])
        if r["kind"] == "S1":
            s["crown"] = r["crown"]
            a = ang[3000:]; rr = rate[3000:]
            s["pp"] = float(a.max() - a.min())
            s["pp_w"] = float(np.ptp(H._bp(a, 0.1, 1.5)))                  # slow-weave content, p-p
            s["pp_c"] = float(np.ptp(H._bp(a, 3.0, 6.0)))                  # chatter content (route 73: 4 Hz), p-p
            s["r_c"] = float(np.std(H._bp(rr, 3.0, 6.0)))
            s["r_w"] = float(np.std(H._bp(rr, 0.2, 1.5)))
            s["fpk"] = welch_peak(rr, 0.1, 8.0)
            s["cmd_pp"] = float(np.ptp(cmd[3000:]))
            s["stuck"] = float(np.mean(stuck[3000:]))
            s["mean"] = float(a.mean())
        elif r["kind"] == "S2":
            a_ = r["a"]; s["a"] = a_
            hold = la[2200:2700]
            s["hold"] = float(np.mean(hold) / a_)
            s["hold_min"] = float(np.min(la[900:2700]) / a_)                # droop (dwell) inside the curve
            s["peak_in"] = float(np.max(la[500:2900]) / a_)                 # overshoot inside the curve
            post = la[2900:]
            s["exit_os"] = float(-min(0.0, np.min(post) * np.sign(a_)))     # m/s^2 to the far side after exit
            s["exit_res"] = float(np.mean(np.abs(post[:500])))             # residual |la| first 5 s after exit
            bad = np.flatnonzero(np.abs(post) > 0.05 * abs(a_))
            s["settle"] = float((bad[-1] + 1) / 100.0) if len(bad) else 0.0
            s["i_exit"] = float(ii[2900])
            h = rate[1200:2700]
            s["c24"] = float(np.std(H._bp(h, 2.0, 2.7)))
            s["hunt_pp"] = float(np.ptp(H._bp(ang[1200:2700], 0.1, 1.5)))
            s["fpk"] = welch_peak(h, 0.5, 8.0)
            s["stuck"] = float(np.mean(stuck[1200:2700]))
        elif r["kind"] in ("S3", "S3P"):
            base = la[800:1000].mean()
            s["push"] = float(np.max(np.abs(la[1000:1400] - base)))
            post = la[1400:2400] - base
            s["post_pk"] = float(np.max(np.abs(post)))
            s["post_os"] = float(np.max(-post * np.sign(np.mean(la[1300:1400] - base) + 1e-12)))
            s["i_at_rel"] = float(ii[1399] - ii[990])
            s["ang_post_pk"] = float(np.max(np.abs(ang[1400:2400] - ang[800:1000].mean())))
        elif r["kind"] == "S5":
            post = la[1400:]
            s["post_pk"] = float(np.max(np.abs(post)))
            s["post_rms"] = float(np.sqrt(np.mean(post[:500] ** 2)))
            s["peak_in"] = float(np.max(np.abs(la[1000:1400])))
        out.append(s)
    return out


def main():
    t0 = time.time()
    rows = build_rows()
    pipe = int(sys.argv[1]) if len(sys.argv) > 1 else 22
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    res = {}
    for cfg in ("V294+r1", "V295+r1", "V295+r2alt"):
        R = E.run(cfg, rows, SECS, pipe_ms=pipe, seed=seed)
        res[cfg] = score(R, rows)
        np.savez_compressed(os.path.join(OUT, "d5_traces_%s_p%d_s%d.npz" % (cfg.replace("+", "_"), pipe, seed)),
                            ang=R["ang"].astype(np.float32), rate=R["rate"].astype(np.float32),
                            la_act=R["la_act"].astype(np.float32), la_des=R["la_des"].astype(np.float32),
                            i=R["i"].astype(np.float32), cmd=R["cmd"].astype(np.float32))
        print("  %s done %.0f s" % (cfg, time.time() - t0), flush=True)
    json.dump(res, open(os.path.join(OUT, "d5_synth_p%d_s%d.json" % (pipe, seed)), "w"), indent=0)
    print("runtime %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
