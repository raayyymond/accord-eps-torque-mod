# -*- coding: utf-8 -*-
"""aw2_reads_replay.py -- ADV "wiring+observability", part (c): the PRE-REGISTERED fork reads (V295-FORK-CONFIG-r2.md s7)
applied to r71b's own logged inputs replayed through the REAL fork LatControlTorque @20d24ab79 with the r2alt value
substituted (AccordTorqueKiHigh 0.8 -> runtime accord_torque_ki_high 0.8, exactly what starpilot_variables yields: clamp
[0, 6]).  Criteria: ../ADV-wiring-r2-CRITERIA.md W7/W8.

Replay = the harness's h3 path (design/harness/fork_real.py + h3_fork_replay.run, post-hoc carState alignment, which
reproduces every logged torqueState field to float32 on r71b).  It is OPEN LOOP: the measurement is r71b's; only the
controller's own state (i, and therefore output) differs between r1 and r2alt.  So every read below is a check of the
READ'S ARITHMETIC against the real code, not a prediction of the closed-loop drive (integrator share is an upper bound).

Method 1 = the attribution script's own estimator (median of di/(0.01*error) on its "unfrozen" mask), binned by vEgo.
Method 2 = the fork's own get_honda_accord_torque_ki(vEgo, 0.3, 0.8) evaluated per frame (closed form), and a
           through-origin OLS slope of di on 0.01*error per bin.
All torqueState fields are cast to float32 before any read (they are capnp Float32 on the wire).
ANALYSIS ONLY.
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
HARN = os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness")
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"))
sys.path.insert(0, HARN)
import r71b_cache as RC  # noqa: E402
import fork_real as FK  # noqa: E402
import h3_fork_replay as H3  # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
LOG = []


def pr(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


D = RC.load(with_raw=False)
T1 = dict(D["meta"]["starpilot_toggles"]["first"]["toggles"])
assert T1["accord_torque_ki_high"] == 0.0 and T1["accord_torque_ki"] == 0.3 and T1["steerKp"] == [[0], [0.9]]
T2 = dict(T1)
T2["accord_torque_ki_high"] = 0.8
t_ = time.time()
icm, found = H3.matched_cs_index(D)
o1, I = H3.run(D, toggles=T1, ic_override=icm)
o2, _ = H3.run(D, toggles=T2, ic_override=icm)
pr("replay r1 and r2alt through the real LatControlTorque @%s (post-hoc aligned), %.0f s" % (FK.FORK_COMMIT, time.time() - t_))

f32 = lambda a: np.asarray(a, np.float32).astype(np.float64)  # noqa: E731
act = (D["ctl_active"] > 0.5) & o1["active"] & o2["active"]
# control: r1 replay == logged
for k in ("p", "i", "f", "output", "error"):
    lg = D["ctl_" + k]
    rp = f32(o1[k]) if k != "output" else f32(o1["torque"])      # the fork returns -output_torque == pid_log.output
    pr("   control r1 replay vs logged %-6s max|d| %.3g (active frames)" % (k, np.max(np.abs(rp[act] - lg[act]))))

from openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes import get_honda_accord_torque_ki, HONDA_ACCORD_KI_SCHEDULE_V_BP  # noqa
pr("   fork HONDA_ACCORD_KI_SCHEDULE_V_BP =", HONDA_ACCORD_KI_SCHEDULE_V_BP)

# ------------------------------------------------------------------------------------------------ the pre-registered reads
tcs = D["ctl_t"]
press = np.interp(tcs, D["cs_t"], D["cs_pressed"]) > 0.5
vv = np.interp(tcs, D["cs_t"], D["cs_vego"])
v_used = I["v"]                                     # the carState vEgo the controller actually used (matched sample)
unw = np.interp(tcs, D["spl_t"], D["spl_unwind"]) > 0.5
sat = D["ctl_saturated"] > 0.5
cct = np.interp(tcs, D["cc_t"], D["cc_torque"])
lim = np.r_[False, np.abs(np.diff(cct)) > 0.03]


def reads(o, label, log=False):
    if log:
        p, i_, d_, f_, e, out = (D["ctl_" + k] for k in ("p", "i", "d", "f", "error", "output"))
    else:
        p, i_, f_, e = f32(o["p"]), f32(o["i"]), f32(o["f"]), f32(o["error"])
        d_ = np.zeros_like(p)
        out = f32(np.asarray(o["torque"]))                          # == torqueState.output (dither 0)
    a = act
    m = a & (np.abs(e) > 0.01)
    kp = np.median(p[m] / e[m])
    di = np.r_[np.nan, np.diff(i_)]
    ok = a & np.r_[False, a[:-1]] & ~press & np.r_[False, ~press[:-1]] & (vv > 1.0) & ~unw & ~sat & ~lim & (np.abs(e) > 0.02)
    ki = di / (0.01 * e)
    m2 = a & (np.abs(out) > 0.02) & ~sat
    laf = np.median((p[m2] + i_[m2] + d_[m2] + f_[m2]) / (-out[m2]))
    fade = np.interp(vv, [0.5, 2.5], [0.0, 1.0])
    roll = np.interp(tcs, D["lpar_t"], D["lpar_roll"])
    ltp_off = np.interp(tcs, D["ltp_t"], D["ltp_off"])
    fric = f_ - (D["ctl_des_curv"] * vv ** 2 - roll * 9.81 * fade) + ltp_off * fade
    m3 = a & (vv > 3)
    fr95 = np.percentile(np.abs(fric[m3]), 95)
    hi = a & (vv >= 15)
    share_mean = np.mean(np.abs(i_[hi])) / np.mean(np.abs(f_[hi]) + np.abs(p[hi]) + np.abs(i_[hi]))
    share_med = np.median(np.abs(i_[hi]) / np.maximum(np.abs(f_[hi]) + np.abs(p[hi]) + np.abs(i_[hi]), 1e-9))
    pr("\n[%s] Kp = median p/error %.5f ; LAF = median (p+i+d+f)/-output %.4f ; friction plateau p95 %.4f m/s^2 = %.4f torque"
       " = %.0f CAN counts ; integrator share >= 15 m/s: mean-ratio %.3f, median %.3f ; Ki-read frames %d"
       % (label, kp, laf, fr95, fr95 / 14.0, fr95 / 14.0 * 4096, share_mean, share_med, ok.sum()))
    rows = []
    for lo, hi_, name in ((1, 8, "1-8"), (8, 9, "8-9"), (9.5, 10.5, "~10"), (11.5, 12.5, "~12"), (14.5, 15.5, "~15"),
                          (18, 40, ">=18"), (8, 18, "8-18 all")):
        b = ok & (vv >= lo) & (vv < hi_)
        if b.sum() == 0:
            rows.append((name, 0))
            continue
        med = np.median(ki[b])
        q1, q3 = np.percentile(ki[b], [25, 75])
        x = 0.01 * e[b]
        ols = float(np.sum(x * di[b]) / np.sum(x * x))
        expect = np.array([get_honda_accord_torque_ki(float(v), 0.3, 0.8 if label.startswith("r2alt") else 0.0)
                           for v in v_used[b]])
        dev = np.abs(ki[b] - expect)
        rows.append((name, int(b.sum()), med, q1, q3, ols, float(np.median(expect)), float(np.percentile(dev, 99)),
                     float(np.mean(dev < 0.005))))
        pr("   Ki bin %-9s n %6d (%.0f s) : M1 median %.4f IQR [%.4f, %.4f] | M2 OLS slope %.4f ; fork closed form median "
           "%.4f ; |read - closed form| p99 %.4f, share within 0.005: %.4f"
           % (name, b.sum(), b.sum() / 100, med, q1, q3, ols, np.median(expect), np.percentile(dev, 99), np.mean(dev < 0.005)))
    return dict(kp=kp, laf=laf, fr95=fr95, share_mean=share_mean, share_med=share_med, ki_rows=rows)


R = dict(logged=reads(None, "r71b LOGGED (drive 1 reference)", log=True), r1=reads(o1, "r1 replay"),
         r2alt=reads(o2, "r2alt replay (open loop)"))

# how different are the two commands (open-loop, an UPPER bound on the r2alt change)?
dT = np.asarray(o2["torque"]) - np.asarray(o1["torque"])
for lo, hi_ in ((0, 8), (8, 15), (15, 22), (22, 40)):
    b = act & (vv >= lo) & (vv < hi_)
    pr("   open-loop |torque r2alt - r1| by band %2d-%2d m/s: rms %.4f (%.0f CAN counts), p99 %.4f, max %.4f ; r1 torque rms %.4f"
       % (lo, hi_, np.sqrt(np.mean(dT[b] ** 2)), 4096 * np.sqrt(np.mean(dT[b] ** 2)), np.percentile(np.abs(dT[b]), 99),
          np.max(np.abs(dT[b])), np.sqrt(np.mean(np.asarray(o1["torque"])[b] ** 2))))
# "below 8 m/s it is r1 exactly": the GAIN is; is the integrator STATE?  (open loop = upper bound)
di_state = np.asarray(o2["i"]) - np.asarray(o1["i"])
low = act & (vv < 8)
last_hi = np.full(len(vv), -1e9)
th = -1e9
for k in range(len(vv)):
    if not act[k]:
        th = -1e9
    elif vv[k] >= 8:
        th = tcs[k]
    last_hi[k] = th
since = tcs - last_hi
for lo_s, hi_s, name in ((0, 2, "<2 s after leaving 8 m/s"), (2, 10, "2-10 s after"), (10, 1e8, ">10 s after"),
                         (1e8, 1e12, "never above 8 in this engagement")):
    b = low & (since >= lo_s) & (since < hi_s)
    if b.sum():
        pr("   0-8 m/s, %-34s: %6d frames, |i_r2alt - i_r1| p50 %.4f p95 %.4f m/s^2 (/LAF 14 = %.4f torque p95)"
           % (name, b.sum(), np.median(np.abs(di_state[b])), np.percentile(np.abs(di_state[b]), 95),
              np.percentile(np.abs(di_state[b]), 95) / 14))
np.savez_compressed(os.path.join(HERE, "_aw2_replay.npz"), t=tcs, torque_r1=np.asarray(o1["torque"]),
                    torque_r2alt=np.asarray(o2["torque"]), act=act, v=vv, i_r1=np.asarray(o1["i"]), i_r2alt=np.asarray(o2["i"]))

# one-drive sufficiency of the discriminator: frames per 120 s of 8-22 m/s exposure on r71b
b = act & (vv >= 8) & (vv < 22)
okm = act & np.r_[False, act[:-1]] & ~press & np.r_[False, ~press[:-1]] & (vv > 1.0) & ~unw & ~sat & ~lim & \
    (np.abs(D["ctl_error"]) > 0.02)
pr("\nKi-read yield at 8-22 m/s on r71b: %.0f s engaged, %d usable frames (%.2f of engaged) -> ~%d usable frames per 120 s"
   % (b.sum() / 100, (okm & b).sum(), (okm & b).sum() / b.sum(), int(120 * 100 * (okm & b).sum() / b.sum())))
json.dump(R, open(os.path.join(OUT, "aw2_reads_replay_out.json"), "w"), indent=1, default=float)
open(os.path.join(OUT, "aw2_reads_replay_out.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
