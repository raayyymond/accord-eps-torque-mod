# -*- coding: utf-8 -*-
"""v293_ident_c.py -- PART C: HOW THE CONTROLLER DID on V293.  Subagent v293plant, 2026-09-13.
ANALYSIS ONLY.

Tracking error, the P/I/F split, saturation, integrator behaviour, the outer loop's spectrum, and a
regime breakdown (straight / turn entry / turn hold / turn exit / low-speed manoeuvre / lane change).

🛑 The pre-registered BAND SCORES are the orchestrator's scorer's job, not this script's.  The 7 Hz
and 18-22 Hz numbers here are reported only so the outer-loop reading is not made in ignorance of
them, and they are computed on the OUTER-LOOP channels (the 0xE4 command and the tracking error),
not on the driver-torque bar the record's presence predicate uses.
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []
pr = L.pr_factory(OUT)
g = L.load("r70_v293")
DT = 1.0 / L.FS
RES = {}
S_OP = -1.0

pr("=" * 108)
pr("V293 -- PART C: WHAT THE OUTER LOOP DID   (route 70, 2026-09-13)")
pr("=" * 108)

eng = g["eng"] & np.isfinite(g["la_act"]) & np.isfinite(g["la_des"])
ho = eng & (g["press"] < 0.5)
u = S_OP * g["op_torque"]
err = g["la_des"] - g["la_act"]

# ======================================================================================================
pr("\nC1. TRACKING: desiredLateralAccel vs actualLateralAccel, per speed band")
pr("    (both are the controller's OWN quantities: setpoint = expected_lat_accel + jerk*lat_delay,")
pr("     measurement = steering angle through the vehicle model.  'lag' is the NCC peak of the")
pr("     0.1-2 Hz band-passed pair -- how far the car is behind its own setpoint.)")
pr("\n    %-8s %8s %9s %9s %9s %9s %8s %9s %9s"
   % ("band", "sec", "|D| p50", "RMS err", "RMS/|D|", "bias", "lag ms", "corr", "overshoot"))
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    s = ho & (g["v"] >= lo) & (g["v"] < hi)
    if s.sum() < 500:
        continue
    E = err[s]
    runs = L.stretches(s, int(20 * L.FS))
    lags, cors = [], []
    for (a, b) in runs:
        lag, cc = L.ncc_lag(L.bandpass(g["la_des"][a:b], 0.1, 2.0),
                            L.bandpass(g["la_act"][a:b], 0.1, 2.0), lo=-0.2, hi=0.8)
        if np.isfinite(lag):
            lags.append(lag); cors.append(cc)
    # overshoot: on turn-entry runs, peak |la_act| / peak |la_des|
    ov = np.nan
    pk = []
    D = g["la_des"]
    for (a, b) in L.stretches(s & (np.abs(D) > 0.8), int(1.5 * L.FS)):
        pk.append(np.max(np.abs(g["la_act"][a:b])) / max(np.max(np.abs(D[a:b])), 1e-6))
    if pk:
        ov = float(np.median(pk))
    pr("    %-8s %8.1f %9.3f %9.3f %9.3f %+9.3f %8.0f %9.3f %9.3f"
       % (L.BANDNAME[k], s.sum() * DT, np.percentile(np.abs(g["la_des"][s]), 50),
          float(np.sqrt(np.mean(E ** 2))),
          float(np.sqrt(np.mean(E ** 2))) / max(float(np.sqrt(np.mean(g["la_des"][s] ** 2))), 1e-9),
          float(np.mean(E)), 1000 * np.median(lags) if lags else np.nan,
          np.median(cors) if cors else np.nan, ov))
    RES.setdefault("track", {})[L.BANDNAME[k]] = dict(
        sec=s.sum() * DT, rms=float(np.sqrt(np.mean(E ** 2))), bias=float(np.mean(E)),
        lag_ms=1000 * np.median(lags) if lags else np.nan, overshoot=ov)

pr("\n    gain of actual on desired (slope of la_act on la_des, low-passed <= 0.5 Hz, hands-off):")
sos = signal.butter(4, 0.5, "lowpass", fs=L.FS, output="sos")
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    runs = [r for r in L.stretches(ho & (g["v"] >= lo) & (g["v"] < hi), int(10 * L.FS))]
    if not runs:
        continue
    X, Y = [], []
    for (a, b) in runs:
        X.append(signal.sosfiltfilt(sos, g["la_des"][a:b]))
        Y.append(signal.sosfiltfilt(sos, g["la_act"][a:b]))
    X, Y = np.concatenate(X), np.concatenate(Y)
    A = np.vstack([X, np.ones(len(X))]).T
    sl, ic = np.linalg.lstsq(A, Y, rcond=None)[0]
    pr("      %-8s slope %.4f  intercept %+.4f  R2 %.4f  n %.0f s"
       % (L.BANDNAME[k], sl, ic, L.r2(Y, A @ [sl, ic]), len(X) * DT))

# ======================================================================================================
pr("\nC2. THE P / I / F SPLIT -- where the commanded torque comes from")
pr("    output_lataccel = f + p + i, and output_torque = output_lataccel / LAF.  With the rate-plant")
pr("    FF off and friction 0, f is just the (roll-corrected) demand, so f/output is the share the")
pr("    FEEDFORWARD carries and 1 - f/output is what the feedback has to make up.")
pr("\n    %-8s %8s %10s %10s %10s %10s %10s %10s"
   % ("band", "sec", "|f| p50", "|p| p50", "|i| p50", "f share", "p share", "i share"))
act = ho & np.isfinite(g["f"]) & np.isfinite(g["p"]) & np.isfinite(g["i"])
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    s = act & (g["v"] >= lo) & (g["v"] < hi)
    if s.sum() < 500:
        continue
    tot = np.abs(g["f"][s]) + np.abs(g["p"][s]) + np.abs(g["i"][s])
    ok = tot > 1e-6
    pr("    %-8s %8.1f %10.4f %10.4f %10.4f %10.3f %10.3f %10.3f"
       % (L.BANDNAME[k], s.sum() * DT, np.percentile(np.abs(g["f"][s]), 50),
          np.percentile(np.abs(g["p"][s]), 50), np.percentile(np.abs(g["i"][s]), 50),
          float(np.mean(np.abs(g["f"][s][ok]) / tot[ok])),
          float(np.mean(np.abs(g["p"][s][ok]) / tot[ok])),
          float(np.mean(np.abs(g["i"][s][ok]) / tot[ok]))))
    RES.setdefault("split", {})[L.BANDNAME[k]] = dict(
        f=float(np.mean(np.abs(g["f"][s][ok]) / tot[ok])),
        p=float(np.mean(np.abs(g["p"][s][ok]) / tot[ok])),
        i=float(np.mean(np.abs(g["i"][s][ok]) / tot[ok])))

pr("\n    the LOW-SPEED FACTOR, which is the real P gain.  The fork computes")
pr("      error_with_lsf = error * (1 + lsf/Kp),  lsf = (interp(v,[0,10,20,30],[12,10.5,8,5])/max(v,0.3))^2")
pr("    and the logged p = Kp * error_with_lsf, so the gain ON THE RAW ERROR is Kp + lsf:")
pr("    %-8s %8s %12s %12s %12s" % ("band", "v med", "lsf", "Kp+lsf", "x Kp(0.3)"))
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    s = act & (g["v"] >= lo) & (g["v"] < hi)
    if s.sum() < 500:
        continue
    v = np.median(g["v"][s])
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2
    pr("    %-8s %8.2f %12.3f %12.3f %12.1f" % (L.BANDNAME[k], v, lsf, 0.3 + lsf, (0.3 + lsf) / 0.3))

pr("\n    INTEGRATOR: Ki = 0.15 on error_with_lsf, frozen on steer_limited / pressed / low speed.")
ia = ho & np.isfinite(g["i"])
pr("      |i| p50 %.4f  p90 %.4f  p99 %.4f  max %.4f  (units m/s^2 of lat-accel command)"
   % tuple(np.percentile(np.abs(g["i"][ia]), [50, 90, 99, 100])))
big_i = ia & (np.abs(g["i"]) > 0.4)
ep = L.stretches(big_i, int(1.0 * L.FS))
pr("      |i| > 0.4 for >= 1 s: %d episodes, %.1f s total (%.2f%% of hands-off engaged time)"
   % (len(ep), big_i.sum() * DT, 100.0 * big_i.sum() / max(ho.sum(), 1)))
if ep:
    lens = [(b - a) * DT for a, b in ep]
    pr("      longest %.1f s ; median %.1f s ; speed at those episodes p50 %.1f m/s"
       % (max(lens), np.median(lens), np.median(g["v"][big_i])))
sgn_flip = np.sum(np.diff(np.sign(g["i"][ia])) != 0)
pr("      integrator sign changes: %d over %.0f s = %.2f per minute"
   % (sgn_flip, ia.sum() * DT, sgn_flip / max(ia.sum() * DT / 60.0, 1e-9)))

# ======================================================================================================
pr("\nC3. SATURATION AND LIMITS")
pr("    torqueState.saturated is openpilot's own debounced flag; |torque| >= 0.95 is the raw duty;")
pr("    the carcontroller rate limiter (STEER_DELTA_UP/DOWN) is a separate limit and is measured")
pr("    by how often the commanded 0xE4 step hits its cap.")
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    s = eng & (g["v"] >= lo) & (g["v"] < hi)
    if s.sum() < 500:
        continue
    d = np.abs(np.diff(g["cmd"]))
    dd = np.concatenate([[0], d])[s]
    pr("    %-8s |torque|>=0.95 %6.2f%%   ==1.000 %6.2f%%   sat flag %5.2f%%   |dcmd| p99 %5.0f  max %5.0f"
       % (L.BANDNAME[k], 100 * np.mean(np.abs(g["op_torque"][s]) >= 0.95),
          100 * np.mean(np.abs(g["op_torque"][s]) >= 0.999),
          100 * np.mean(g["sat"][s] > 0.5), np.percentile(dd, 99), dd.max()))

# ======================================================================================================
pr("\nC4. REGIME BREAKDOWN -- where the controller over- or under-delivers")
pr("    regimes from the DEMAND, not the response: straight |D|<0.3 m/s^2 and |dD/dt|<0.3;")
pr("    entry dD/dt*sign(D) > +0.5 ; hold |D|>0.8 and |dD/dt|<0.3 ; exit dD/dt*sign(D) < -0.5;")
pr("    low-speed manoeuvre v<8 and |D|>1.0 ; lane change |D| flips sign within 4 s with |D|>0.6.")
dD = np.gradient(g["la_des"], DT)
sgn = np.sign(g["la_des"])
REG = {
    "straight": ho & (np.abs(g["la_des"]) < 0.3) & (np.abs(dD) < 0.3),
    "turn entry": ho & (dD * sgn > 0.5) & (np.abs(g["la_des"]) > 0.3),
    "turn hold": ho & (np.abs(g["la_des"]) > 0.8) & (np.abs(dD) < 0.3),
    "turn exit": ho & (dD * sgn < -0.5) & (np.abs(g["la_des"]) > 0.3),
    "low-speed manoeuvre": ho & (g["v"] < 8) & (np.abs(g["la_des"]) > 1.0),
}
pr("\n    %-22s %8s %10s %10s %10s %10s %10s"
   % ("regime", "sec", "|D| p50", "RMS err", "bias err", "|u| p50", "deliver %"))
for nm, s in REG.items():
    if s.sum() < 200:
        pr("    %-22s %8.1f  (too little)" % (nm, s.sum() * DT)); continue
    dv = float(np.mean(np.abs(g["la_act"][s])) / max(np.mean(np.abs(g["la_des"][s])), 1e-9))
    pr("    %-22s %8.1f %10.3f %10.3f %+10.3f %10.4f %10.1f"
       % (nm, s.sum() * DT, np.percentile(np.abs(g["la_des"][s]), 50),
          float(np.sqrt(np.mean(err[s] ** 2))), float(np.mean(err[s] * sgn[s])),
          np.percentile(np.abs(u[s]), 50), 100 * dv))
    RES.setdefault("regime", {})[nm] = dict(sec=s.sum() * DT, rms=float(np.sqrt(np.mean(err[s] ** 2))),
                                            signed_bias=float(np.mean(err[s] * sgn[s])), deliver=dv)
pr("\n    'bias err' is the error PROJECTED ON THE DEMAND'S SIGN: positive means the car is")
pr("    UNDER-turning relative to what the planner asked for; negative means over-turning.")
pr("    'deliver %%' is mean|actual| / mean|desired| in that regime.")

# ======================================================================================================
pr("\nC5. THE OUTER LOOP'S SPECTRUM -- error and command, 0.2-15 Hz, per band")
pr("    reported as amplitude density; a LINE is a limit cycle, a broad rise is road input.")
pr("    🛑 the pre-registered band scores are the orchestrator's scorer's, not these.")
BANDSF = [(0.2, 1.0), (1.0, 4.0), (4.0, 6.0), (6.0, 9.0), (9.0, 13.0), (13.0, 17.0), (18.0, 22.0)]
pr("\n    %-8s %-10s" % ("band", "signal") + "".join("%11s" % ("%.0f-%.0f Hz" % b) for b in BANDSF)
   + "%12s" % "peak line")
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    s = ho & (g["v"] >= lo) & (g["v"] < hi)
    runs = L.stretches(s, 1024)
    if not runs:
        continue
    for sig_name, x in (("err m/s2", err), ("0xE4 cmd", g["cmd"]), ("angle deg", g["ang"])):
        P = None
        nn = 0
        for (a, b) in runs:
            f, p = signal.welch(signal.detrend(x[a:b]), fs=L.FS, nperseg=1024,
                                noverlap=512, detrend="linear")
            P = p * (b - a) if P is None else P + p * (b - a)
            nn += (b - a)
        P = P / nn
        amps = []
        for (f0, f1) in BANDSF:
            sel = (f >= f0) & (f < f1)
            amps.append(np.sqrt(np.sum(P[sel]) * (f[1] - f[0])))
        selp = (f >= 0.5) & (f <= 25)
        fp = f[selp][int(np.argmax(P[selp]))]
        pr("    %-8s %-10s" % (L.BANDNAME[k] if sig_name == "err m/s2" else "", sig_name)
           + "".join("%11.4f" % a for a in amps) + "%12.2f" % fp)
        RES.setdefault("spec", {}).setdefault(L.BANDNAME[k], {})[sig_name] = dict(
            bands=[list(b) for b in BANDSF], amp=[float(a) for a in amps], peak=float(fp))

with open(os.path.join(L.SCRATCH, "v293_ident_c.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_c.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_c.txt / .json")
