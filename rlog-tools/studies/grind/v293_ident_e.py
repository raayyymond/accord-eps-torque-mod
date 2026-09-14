# -*- coding: utf-8 -*-
"""v293_ident_e.py -- PART D SUPPORT: the VEHICLE MODEL check (is the steer ratio the error?), the
regimes part C did not cover (roundabouts, lane changes), and the feedforward-delivery accounting.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

E1 is the decisive test of the "SR map too flat" hypothesis WITHOUT touching the fork's map: the
controller's own `actualLateralAccel` is the steering angle pushed through the vehicle model with
liveParameters.steerRatio; the raw gyro yaw * v is the same quantity measured.  Their RATIO,
stratified by |angle| and by speed, IS the vehicle model's error, with no model of its own.
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
u = S_OP * g["op_torque"]
err = g["la_des"] - g["la_act"]

pr("=" * 108)
pr("V293 -- PART D SUPPORT: the vehicle model, the missing regimes, and the feedforward accounting")
pr("=" * 108)

# ======================================================================================================
pr("\nE1. IS THE VEHICLE MODEL (STEER RATIO) THE ERROR?  [EVIDENCE -- two instruments, no model]")
pr("    actualLateralAccel = steering angle through VM.calc_curvature with liveParameters.steerRatio")
pr("    (FROZEN at 16.880 all route -- ForceAutoTuneOff = 1).  gyro yaw * v is the same quantity")
pr("    measured by the IMU.  ratio = la_act / la_gyro.  > 1 means the model OVER-states the lat accel")
pr("    the angle produces, i.e. the steer ratio in use is TOO SMALL there (and vice versa).")
eng = g["eng"] & np.isfinite(g["la_act"]) & np.isfinite(g["gyro_yaw"]) & (g["v"] > 3.0)
sos = signal.butter(4, 0.5, "lowpass", fs=L.FS, output="sos")
lag_lp = np.zeros(len(g["t"]))
la_g = g["gyro_yaw"] * g["v"]
# the gyro channel is LATER than the angle channel (vehicle yaw follows the wheel); align by NCC first
runs = L.stretches(L.clean_mask(g, hands_off=True, min_v=5.0), int(20 * L.FS))
lags = []
for (a, b) in runs:
    lg, cc = L.ncc_lag(L.bandpass(g["la_act"][a:b], 0.1, 1.5), L.bandpass(la_g[a:b], 0.1, 1.5),
                       lo=-0.2, hi=0.5)
    if np.isfinite(lg) and cc > 0.5:
        lags.append(lg)
LAG = float(np.median(lags)) if lags else 0.0
nk = int(round(LAG * L.FS))
pr("    angle-channel -> gyro-channel lag, measured: %+.0f ms (n %d stretches) -- the gyro is shifted"
   % (1000 * LAG, len(lags)))
pr("    back by that before every comparison below, so the ratio is not a phase artefact.")
la_g_al = np.concatenate([la_g[nk:], np.full(max(nk, 0), np.nan)]) if nk > 0 else la_g

pr("\n    (a) by |steering angle|, all engaged frames above 3 m/s, on the 0.5 Hz low-passed pair:")
pr("    %-14s %9s %11s %11s %11s %13s"
   % ("|angle| deg", "n s", "la_act p50", "la_gyro p50", "ratio", "implied SR"))
Aa = np.abs(g["ang"])
for lo, hi in [(0, 2), (2, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 400)]:
    s = eng & (Aa >= lo) & (Aa < hi) & np.isfinite(la_g_al) & (np.abs(g["la_act"]) > 0.05)
    if s.sum() < 300:
        continue
    r = g["la_act"][s] / la_g_al[s]
    A = np.vstack([la_g_al[s], np.ones(s.sum())]).T
    sl, ic = np.linalg.lstsq(A, g["la_act"][s], rcond=None)[0]
    pr("    %-14s %9.1f %11.3f %11.3f %11.4f %13.2f"
       % ("%d-%d" % (lo, hi), s.sum() * DT, np.percentile(np.abs(g["la_act"][s]), 50),
          np.percentile(np.abs(la_g_al[s]), 50), sl, 16.88 * sl))
    RES.setdefault("sr_by_angle", {})["%d-%d" % (lo, hi)] = dict(slope=float(sl), sec=s.sum() * DT)
pr("      'implied SR' = 16.88 * slope: the steer ratio that would make the model agree with the IMU")
pr("      in that stratum, on the model's own linearisation.  [BELIEF on the exact value -- it also")
pr("      absorbs the understeer coefficient and tyre slip, which are not separable here.]")

pr("\n    (b) by speed, |angle| < 20 deg (the stratum the highway spends its time in):")
pr("    %-10s %9s %11s %13s" % ("band m/s", "n s", "ratio", "implied SR"))
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    s = eng & (g["v"] >= lo) & (g["v"] < hi) & (Aa < 20) & np.isfinite(la_g_al) & (np.abs(g["la_act"]) > 0.05)
    if s.sum() < 300:
        continue
    A = np.vstack([la_g_al[s], np.ones(s.sum())]).T
    sl, ic = np.linalg.lstsq(A, g["la_act"][s], rcond=None)[0]
    pr("    %-10s %9.1f %11.4f %13.2f" % (L.BANDNAME[k], s.sum() * DT, sl, 16.88 * sl))
    RES.setdefault("sr_by_speed", {})[L.BANDNAME[k]] = float(sl)

pr("\n    (c) the same by the RATIO OF RMS (no regression, so a bias cannot hide in the intercept),")
pr("        on hands-off engaged stretches only:")
mm = L.clean_mask(g, hands_off=True, min_v=5.0)
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    s = mm & (g["v"] >= lo) & (g["v"] < hi) & np.isfinite(la_g_al)
    if s.sum() < 500:
        continue
    pr("      %-8s rms(la_act) %.4f  rms(la_gyro) %.4f  ratio %.4f  (%.0f s)"
       % (L.BANDNAME[k], np.sqrt(np.mean(g["la_act"][s] ** 2)), np.sqrt(np.mean(la_g_al[s] ** 2)),
          np.sqrt(np.mean(g["la_act"][s] ** 2)) / np.sqrt(np.mean(la_g_al[s] ** 2)), s.sum() * DT))

# ======================================================================================================
pr("\n" + "=" * 108)
pr("E2. THE REGIMES PART C DID NOT COVER")
pr("=" * 108)
ho = eng & (g["press"] < 0.5)
D = g["la_des"]
dD = np.gradient(D, DT)
sgn = np.sign(D)
pr("\n    (a) ROUNDABOUTS / low-speed high-angle work: v < 10 m/s AND |angle| > 40 deg, engaged.")
rb = g["eng"] & (g["v"] < 10) & (Aa > 40)
pr("        %.1f s engaged (%.1f s hands-off).  %d episodes >= 2 s."
   % (rb.sum() * DT, (rb & (g["press"] < 0.5)).sum() * DT, len(L.stretches(rb, int(2 * L.FS)))))
if rb.sum() > 200:
    pr("        |torque| p50 %.3f p95 %.3f ; at 1.000 for %.1f%% of it ; |tap| p50 %.0f p95 %.0f counts"
       % (np.percentile(np.abs(g["op_torque"][rb]), 50), np.percentile(np.abs(g["op_torque"][rb]), 95),
          100 * np.mean(np.abs(g["op_torque"][rb]) >= 0.999),
          np.percentile(np.abs(g["T"][rb]), 50), np.percentile(np.abs(g["T"][rb]), 95)))
    pr("        driver pressing for %.1f%% of it ; tracking: mean|la_act|/mean|la_des| = %.3f"
       % (100 * np.mean(g["press"][rb] > 0.5),
          np.mean(np.abs(g["la_act"][rb])) / max(np.mean(np.abs(g["la_des"][rb])), 1e-9)))
    pr("        driver-torque bar |bar| p50 %.0f p95 %.0f  (the taper's own axis is |bar|>>5)"
       % (np.percentile(np.abs(g["bar"][rb]), 50), np.percentile(np.abs(g["bar"][rb]), 95)))
    pr("        THE OVERRIDE TAPER BITES HERE: |tap|/|cmd| in this stratum = %.4f against %.4f"
       % (np.median(np.abs(g["T"][rb & (np.abs(g["cmd"]) > 200)]) /
                    np.abs(g["cmd"][rb & (np.abs(g["cmd"]) > 200)])), 10.3355 / 16.1876))

pr("\n    (b) LANE CHANGES: |la_des| crosses zero with |la_des| > 0.6 within 4 s either side, v > 15.")
zc = np.flatnonzero(np.diff(np.sign(D)) != 0)
lc = []
for i in zc:
    a, b = max(0, i - 400), min(len(D), i + 400)
    if g["v"][i] < 15 or not ho[a:b].all():
        continue
    if np.max(D[a:i]) > 0.6 and np.min(D[i:b]) < -0.6:
        lc.append((a, b))
    elif np.min(D[a:i]) < -0.6 and np.max(D[i:b]) > 0.6:
        lc.append((a, b))
merged = []
for (a, b) in lc:
    if merged and a <= merged[-1][1]:
        merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
    else:
        merged.append((a, b))
pr("        %d lane-change-like reversals found, %.1f s total." % (len(merged), sum(b - a for a, b in merged) * DT))
if merged:
    ovs, pk, rms = [], [], []
    for (a, b) in merged:
        ovs.append(np.max(np.abs(g["la_act"][a:b])) / max(np.max(np.abs(D[a:b])), 1e-6))
        pk.append(np.max(np.abs(g["op_torque"][a:b])))
        rms.append(np.sqrt(np.mean(err[a:b] ** 2)))
    pr("        peak|actual|/peak|desired| p50 %.3f  [p10 %.3f, p90 %.3f]"
       % (np.percentile(ovs, 50), np.percentile(ovs, 10), np.percentile(ovs, 90)))
    pr("        peak |torque| p50 %.3f   RMS error p50 %.3f m/s^2" % (np.median(pk), np.median(rms)))
    f, P = signal.welch(np.concatenate([signal.detrend(err[a:b]) for a, b in merged]),
                        fs=L.FS, nperseg=512)
    sel = (f > 0.3) & (f < 5)
    pr("        error spectrum peak in 0.3-5 Hz: %.2f Hz  (the V276 outer-loop signature lives 1-4 Hz)"
       % f[sel][int(np.argmax(P[sel]))])

pr("\n    (c) STANDSTILL AND PULL-AWAY: engaged with v < 2 m/s")
ss = g["eng"] & (g["v"] < 2.0)
pr("        %.1f s.  |torque| p50 %.3f p95 %.3f ; at 1.000 %.1f%% ; |tap| p95 %.0f"
   % (ss.sum() * DT, np.percentile(np.abs(g["op_torque"][ss]), 50) if ss.sum() else np.nan,
      np.percentile(np.abs(g["op_torque"][ss]), 95) if ss.sum() else np.nan,
      100 * np.mean(np.abs(g["op_torque"][ss]) >= 0.999) if ss.sum() else np.nan,
      np.percentile(np.abs(g["T"][ss]), 95) if ss.sum() else np.nan))

# ======================================================================================================
pr("\n" + "=" * 108)
pr("E3. THE FEEDFORWARD ACCOUNTING -- how much of the demand the FF alone delivers")
pr("=" * 108)
pr("\n    The FF commands torque = f / LAF_set with LAF_set = 6.0 and f ~= the demand, and the car")
pr("    answers with LAF_true * torque.  So the FF alone delivers LAF_true/6.0 of the demand, and")
pr("    the feedback has to find the rest.  With the measured LAF per band:")
try:
    with open(os.path.join(L.SCRATCH, "v293_ident_b3.json")) as fh:
        B3 = json.load(fh)
    LABL = "LAF: openpilot torque -> actualLateralAccel  [m/s^2 per unit]"
    tab = {nm: d["m1"]["K"] for nm, d in B3.get("fit", {}).get(LABL, {}).items()}
except Exception:
    tab = {}
try:
    with open(os.path.join(L.SCRATCH, "v293_ident_d.json")) as fh:
        Dj = json.load(fh)
    for nm, d in Dj.get("lowspeed", {}).get("LAF: openpilot torque -> actualLateralAccel", {}).items():
        tab.setdefault(nm, d["m1"]["K"])
except Exception:
    pass
pr("    %-10s %12s %14s %16s %16s" % ("band", "LAF true", "FF delivers", "shortfall", "i share (part C)"))
ISHARE = {"<8": 0.350, "1-8": 0.350, "8-15": 0.348, "15-22": 0.382, ">22": 0.384}
for nm, K in sorted(tab.items()):
    pr("    %-10s %12.3f %13.1f%% %15.1f%% %15s"
       % (nm, K, 100 * K / 6.0, 100 * (1 - K / 6.0),
          "%.3f" % ISHARE.get(nm, np.nan) if nm in ISHARE else "-"))
pr("\n    (the i share is the measured mean |i|/(|f|+|p|+|i|) from part C: the integrator is the")
pr("     mechanism that makes up a feedforward shortfall, and its size should track the shortfall.)")

with open(os.path.join(L.SCRATCH, "v293_ident_e.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_e.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_e.txt / .json")
