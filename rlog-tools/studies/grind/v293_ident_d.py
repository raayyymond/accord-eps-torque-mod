# -*- coding: utf-8 -*-
"""v293_ident_d.py -- PART B SUPPLEMENT: the LOW-SPEED band, the instrument-lag controls, and the
CONTROLLER-SIDE numbers a retune needs (loop shaping on the identified plant).
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

Three jobs the main pass could not do:
  D1  INSTRUMENT CONTROLS for the dead time.  A 0.2-0.3 s dead time from delivered EPS torque to
      steering angle is large enough that it must be controlled before it is believed: measure the
      0xE4 -> 427 tap lag (the EPS's own, should be one frame or two) and the 427 tap -> 0x18F rate
      lag, plus a ZERO-LAG and a KNOWN-200 ms control through the same estimator.
  D2  THE LOW-SPEED BAND.  Below 8 m/s the 2 s recovery buffer and the 175 override episodes leave no
      10 s window.  Here the buffer is 0.5 s and the window 5.12 s, stated as a weaker mask.
  D3  LOOP SHAPING on the identified plant with the fork's own controller structure, for the retune.
"""
import json
import os
import sys

import numpy as np
from scipy import optimize, signal

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
S_OP, S_TAP, S_ANG, S_RATE = -1.0, +1.0, -1.0, +1.0
CH = dict(u_op=S_OP * g["op_torque"], u_tap=S_TAP * g["T"], y_ang=S_ANG * g["ang"],
          y_rate=S_RATE * g["rate_dps"], y_la=g["la_act"], y_yaw=g["gyro_yaw"] * g["v"],
          z=g["des_curv"] * g["v"] ** 2)

pr("=" * 108)
pr("V293 -- PART B SUPPLEMENT: instrument controls, the low-speed band, and the loop shaping")
pr("=" * 108)

# ======================================================================================================
# D1. instrument controls on the dead time
# ======================================================================================================
pr("\nD1. IS THE 0.2-0.3 s DEAD TIME REAL?  controls through the SAME estimator [EVIDENCE]")
mask = L.clean_mask(g, hands_off=True, min_v=1.0)
runs = L.stretches(mask, int(20 * L.FS))
pr("    %d hands-off stretches >= 20 s, %.0f s total.  NCC peak lag of the 0.05-0.5 Hz band-passed"
   % (len(runs), sum(b - a for a, b in runs) * DT))
pr("    pair, ROI -0.3..+0.8 s, median over stretches (IQR in brackets):")


def pair_lag(xk, yk, lo=0.05, hi=0.5, roi=(-0.3, 0.8), xs=None, ys=None):
    out = []
    for (a, b) in runs:
        x = (CH[xk][a:b] if xs is None else xs[a:b])
        y = (CH[yk][a:b] if ys is None else ys[a:b])
        if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
            continue
        lag, cc = L.ncc_lag(L.bandpass(x, lo, hi), L.bandpass(y, lo, hi), lo=roi[0], hi=roi[1])
        if np.isfinite(lag) and cc > 0.3:
            out.append(lag)
    if not out:
        return np.nan, np.nan, np.nan, 0
    return (float(np.median(out)), float(np.percentile(out, 25)),
            float(np.percentile(out, 75)), len(out))


delayed = np.concatenate([np.zeros(20), CH["u_tap"][:-20]])          # exactly 200 ms
ZERO = CH["u_tap"].copy()
tests = [("CONTROL zero lag: tap -> itself", "u_tap", "u_tap", None, ZERO),
         ("CONTROL 200 ms: tap -> tap delayed 200 ms", "u_tap", None, None, delayed),
         ("0xE4 command -> 427 tap (the EPS's own)", None, "u_tap", np.abs(g["cmd"]), None),
         ("427 tap -> 0x18F wheel RATE", "u_tap", "y_rate", None, None),
         ("427 tap -> 0x14A steering ANGLE", "u_tap", "y_ang", None, None),
         ("427 tap -> actualLateralAccel", "u_tap", "y_la", None, None),
         ("427 tap -> GYRO lat accel", "u_tap", "y_yaw", None, None),
         ("desiredCurvature*v^2 -> actualLateralAccel", "z", "y_la", None, None),
         ("0x14A angle -> actualLateralAccel (instrument)", "y_ang", "y_la", None, None)]
for lab, xk, yk, xs, ys in tests:
    m_, q1, q3, n = pair_lag(xk, yk, xs=xs, ys=ys)
    pr("      %-46s %+7.0f ms  [%+.0f, %+.0f]  n %d" % (lab, 1000 * m_, 1000 * q1, 1000 * q3, n))
    RES.setdefault("lags", {})[lab] = m_
pr("\n    ALSO: the same tap->angle lag measured on the 0.2-2 Hz band (the band the models are fitted in):")
m_, q1, q3, n = pair_lag("u_tap", "y_ang", lo=0.2, hi=2.0)
pr("      427 tap -> 0x14A angle, 0.2-2 Hz:            %+7.0f ms  [%+.0f, %+.0f]  n %d"
   % (1000 * m_, 1000 * q1, 1000 * q3, n))
pr("\n    🛑 READING: the tap->angle lag is a CLOSED-LOOP cross-correlation of a spring-like plant, so")
pr("    it is NOT by itself the dead time -- at low frequency torque and angle are IN PHASE and the")
pr("    NCC peak of an in-phase pair sits at 0.  The dead time in B3 comes from the PHASE SLOPE of")
pr("    the IV transfer, which is the right estimator; this block's job is only to prove the two")
pr("    controls pass and that the EPS's own command->tap path adds nothing material.")

# ======================================================================================================
# D2. the low-speed band
# ======================================================================================================
pr("\n" + "=" * 108)
pr("D2. THE LOW-SPEED BAND (<8 m/s) -- a WEAKER mask, stated as such")
pr("    buffer after an override cut from 2.0 s to 0.5 s, window 5.12 s instead of 10.24 s, so the")
pr("    usable frequency floor rises to ~0.25 Hz.  Everything else identical.")
pr("=" * 108)
NPER2, STEP2 = 512, 128
mask2 = L.clean_mask(g, hands_off=True, min_v=1.0, buffer_s=0.5)
strets2 = L.stretches(mask2, NPER2)
BANDS2 = [(1.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
NAMES2 = ["1-8", "8-15", "15-22", ">22"]
W2 = {k: [] for k in range(len(BANDS2))}
for si, (a, b) in enumerate(strets2):
    for s0 in range(a, b - NPER2 + 1, STEP2):
        v = g["v"][s0:s0 + NPER2]
        bi = np.array([next(i for i, (lo, hi) in enumerate(BANDS2) if lo <= x < hi)
                       if v.min() >= 1.0 or x >= 1.0 else 0 for x in v])
        cnt = np.bincount(bi, minlength=len(BANDS2))
        k = int(np.argmax(cnt))
        if cnt[k] / float(NPER2) >= 0.80:
            W2[k].append((s0, si))
pr("\n    %-8s %8s %11s %9s %10s" % ("band", "windows", "indep sec", "v med", "|ang| p95"))
VMED2 = {}
for k in range(len(BANDS2)):
    if not W2[k]:
        pr("    %-8s %8d" % (NAMES2[k], 0)); continue
    idx = np.unique(np.concatenate([np.arange(s, s + NPER2) for s, _ in W2[k]]))
    VMED2[NAMES2[k]] = float(np.median(g["v"][idx]))
    pr("    %-8s %8d %11.1f %9.2f %10.2f" % (NAMES2[k], len(W2[k]), len(idx) * DT,
                                             VMED2[NAMES2[k]], np.percentile(np.abs(g["ang"][idx]), 95)))

win = signal.get_window("hann", NPER2)
sc = 1.0 / (L.FS * np.sum(win ** 2))
fr = np.fft.rfftfreq(NPER2, DT)


def pooled2(W, ukey, ykey):
    if not W:
        return None
    Szu = np.zeros(len(fr), complex); Szy = np.zeros(len(fr), complex)
    Pzz = np.zeros(len(fr)); Puu = np.zeros(len(fr)); Pyy = np.zeros(len(fr))
    n = 0
    for (s0, _) in W:
        sl = slice(s0, s0 + NPER2)
        z, u, y = CH["z"][sl], CH[ukey][sl], CH[ykey][sl]
        if not (np.all(np.isfinite(z)) and np.all(np.isfinite(u)) and np.all(np.isfinite(y))):
            continue
        Z = np.fft.rfft(signal.detrend(z) * win); U = np.fft.rfft(signal.detrend(u) * win)
        Y = np.fft.rfft(signal.detrend(y) * win)
        Szu += np.conj(Z) * U * sc; Szy += np.conj(Z) * Y * sc
        Pzz += np.abs(Z) ** 2 * sc; Puu += np.abs(U) ** 2 * sc; Pyy += np.abs(Y) ** 2 * sc
        n += 1
    if n == 0:
        return None
    return dict(f=fr, n=n, H=Szy / np.where(np.abs(Szu) < 1e-300, np.nan, Szu),
                czu=np.abs(Szu) ** 2 / np.maximum(Pzz * Puu, 1e-300),
                czy=np.abs(Szy) ** 2 / np.maximum(Pzz * Pyy, 1e-300))


def fit2(R, flo=0.25, fhi=1.5, cmin=0.35):
    coh = np.minimum(R["czu"], R["czy"])
    sel = (R["f"] >= flo) & (R["f"] <= fhi) & (coh > cmin) & np.isfinite(R["H"])
    if sel.sum() < 3:
        return None
    f, H, w = R["f"][sel], R["H"][sel], coh[sel]
    s = 2j * np.pi * f
    norm = float(np.sum(np.abs(H) ** 2 * w))
    K0 = float(np.abs(H[0])); lim = 20 * abs(K0) + 1

    def ls(fn, p0, bnd):
        return optimize.least_squares(
            lambda p: np.concatenate([((fn(p) - H) * np.sqrt(w)).real,
                                      ((fn(p) - H) * np.sqrt(w)).imag]), p0, bounds=bnd, max_nfev=4000)
    m0 = ls(lambda p: p[0] * np.exp(-s * p[1]), [K0, 0.15], ([-lim, 0], [lim, 0.6]))
    b1 = None
    for T0 in (0.02, 0.15, 0.5, 1.5):
        for d0 in (0.01, 0.1, 0.25):
            r = ls(lambda p: p[0] * np.exp(-s * p[2]) / (1 + s * p[1]), [K0, T0, d0],
                   ([-lim, 0, 0], [lim, 8.0, 0.6]))
            if b1 is None or r.cost < b1.cost:
                b1 = r
    H0 = m0.x[0] * np.exp(-s * m0.x[1])
    H1 = b1.x[0] * np.exp(-s * b1.x[2]) / (1 + s * b1.x[1])
    return dict(nf=int(sel.sum()),
                m0=dict(K=float(m0.x[0]), d=float(m0.x[1]),
                        vaf=1 - float(np.sum(np.abs(H0 - H) ** 2 * w)) / norm),
                m1=dict(K=float(b1.x[0]), T=float(abs(b1.x[1])), d=float(abs(b1.x[2])),
                        vaf=1 - float(np.sum(np.abs(H1 - H) ** 2 * w)) / norm))


for ukey, ykey, lab in (("u_op", "y_la", "LAF: openpilot torque -> actualLateralAccel"),
                        ("u_op", "y_yaw", "openpilot torque -> GYRO lat accel"),
                        ("u_tap", "y_ang", "delivered 427 torque -> angle [deg/count]")):
    pr("\n    %s" % lab)
    pr("    %-8s %6s | %10s %7s %6s | %10s %7s %7s %6s | %8s"
       % ("band", "nwin", "M0 K", "M0 d", "VAF", "M1 K", "M1 T", "M1 d", "VAF", "coh0.3"))
    for k in range(len(BANDS2)):
        R = pooled2(W2[k], ukey, ykey)
        if R is None:
            continue
        F = fit2(R)
        if F is None:
            pr("    %-8s %6d | (no coherent bins)" % (NAMES2[k], R["n"])); continue
        coh = np.minimum(R["czu"], R["czy"])
        pr("    %-8s %6d | %10.4f %7.3f %6.2f | %10.4f %7.3f %7.3f %6.2f | %8.2f"
           % (NAMES2[k], R["n"], F["m0"]["K"], F["m0"]["d"], F["m0"]["vaf"],
              F["m1"]["K"], F["m1"]["T"], F["m1"]["d"], F["m1"]["vaf"], np.interp(0.3, R["f"], coh)))
        RES.setdefault("lowspeed", {}).setdefault(lab, {})[NAMES2[k]] = F

pr("\n    the same low-speed cells by the STATIC estimator (sustained turns >= 2 s, |la_des| > 0.5,")
pr("    |d la_act/dt| < 1.2) -- independent of any frequency-domain assumption:")
dla = np.gradient(g["la_act"], DT)
steady = mask2 & (np.abs(g["la_des"]) > 0.5) & (np.abs(dla) < 1.2)
runs2 = L.stretches(steady, int(2 * L.FS))
pr("    %-8s %7s %9s %12s %12s %12s %12s"
   % ("band", "runs", "seconds", "LAF la/u", "LAF gyro", "cnt per deg", "la/1e3 cnt"))
for k in range(len(BANDS2)):
    lo, hi = BANDS2[k]
    rows = [(np.mean(CH["u_op"][a:b]), np.mean(CH["y_la"][a:b]), np.mean(CH["y_yaw"][a:b]),
             np.mean(CH["u_tap"][a:b]), np.mean(CH["y_ang"][a:b]), b - a)
            for (a, b) in runs2 if lo <= np.median(g["v"][a:b]) < hi]
    if len(rows) < 4:
        pr("    %-8s %7d  (too few)" % (NAMES2[k], len(rows))); continue
    A = np.array(rows)

    def sl(x, y):
        M = np.vstack([x, np.ones(len(x))]).T
        return float(np.linalg.lstsq(M, y, rcond=None)[0][0])
    pr("    %-8s %7d %9.1f %12.3f %12.3f %12.2f %12.4f"
       % (NAMES2[k], len(A), A[:, 5].sum() * DT, sl(A[:, 0], A[:, 1]), sl(A[:, 0], A[:, 2]),
          sl(A[:, 4], A[:, 3]), 1000 * sl(A[:, 3], A[:, 1])))
    RES.setdefault("steady2", {})[NAMES2[k]] = dict(
        n=len(A), laf=sl(A[:, 0], A[:, 1]), laf_gyro=sl(A[:, 0], A[:, 2]),
        k=sl(A[:, 4], A[:, 3]), la_per_1000=sl(A[:, 3], A[:, 1]))

# ======================================================================================================
# D3. loop shaping on the identified plant
# ======================================================================================================
pr("\n" + "=" * 108)
pr("D3. LOOP SHAPING ON THE IDENTIFIED PLANT -- what Kp/Ki the plant supports")
pr("    The fork's controller, in LAT-ACCEL space, is:")
pr("        e   = setpoint - measurement,  with  e_used = e * (1 + lsf/Kp)")
pr("        out = Kp*e_used + Ki*Int(e_used) + ff,     torque = out / LAF")
pr("    so the FEEDBACK gain on the RAW error is  Kp_eff = Kp + lsf  and  Ki_eff = Ki*(1 + lsf/Kp).")
pr("    The plant in the same space is  P(s) = (LAF_true/LAF_set) * e^{-s d} / (1 + sT)  -- the")
pr("    factor is because the controller divides by LAF_set before the car multiplies by LAF_true.")
pr("    🛑 The planner's own lookahead does NOT enter the loop gain: it shifts the reference, not the")
pr("    return path (tau_identify.py's argument).  So the delay in L(s) is the measured plant delay.")
pr("=" * 108)


def margins(Kp, Ki, laf_true, laf_set, d, T, fmax=5.0):
    w = 2 * np.pi * np.logspace(-2, np.log10(fmax), 4000)
    s = 1j * w
    C = Kp + Ki / s
    P = (laf_true / laf_set) * np.exp(-s * d) / (1 + s * T)
    Lw = C * P
    mag = np.abs(Lw); ph = np.angle(Lw, deg=True)
    gc = np.where(np.diff(np.sign(mag - 1.0)) != 0)[0]
    if len(gc) == 0:
        pm, wc = np.nan, np.nan
    else:
        i = gc[0]
        wc = np.interp(1.0, [mag[i + 1], mag[i]], [w[i + 1], w[i]]) if mag[i] > mag[i + 1] else \
            np.interp(1.0, [mag[i], mag[i + 1]], [w[i], w[i + 1]])
        pm = 180.0 + np.interp(wc, w, np.unwrap(np.radians(ph)) * 180 / np.pi)
    S = 1.0 / (1.0 + Lw)
    Ms = float(np.max(np.abs(S)))
    Tc = Lw / (1 + Lw)
    Mt = float(np.max(np.abs(Tc)))
    return pm, wc / (2 * np.pi) if np.isfinite(wc) else np.nan, Ms, Mt


pr("\n    (a) THE LOOP AS FLOWN on route 70, per band, using the measured plant of B3/D2:")
pr("    %-8s %8s %8s %8s %8s %8s | %8s %8s %8s %8s"
   % ("band", "LAF_true", "d s", "T s", "Kp_eff", "Ki_eff", "PM deg", "wc Hz", "Ms", "Mt"))
PLANT = {}
try:
    with open(os.path.join(L.SCRATCH, "v293_ident_b3.json")) as fh:
        B3 = json.load(fh)
    LABL = "LAF: openpilot torque -> actualLateralAccel  [m/s^2 per unit]"
    for nm, d in B3.get("fit", {}).get(LABL, {}).items():
        PLANT[nm] = dict(K=d["m1"]["K"], d=d["m1"]["d"], T=d["m1"]["T"])
except Exception as ex:
    pr("    (b3 json not available yet: %s)" % ex)
for nm, d in RES.get("lowspeed", {}).get("LAF: openpilot torque -> actualLateralAccel", {}).items():
    if nm not in PLANT:
        PLANT[nm] = dict(K=d["m1"]["K"], d=d["m1"]["d"], T=d["m1"]["T"])
VM = {"1-8": 4.5, "<8": 4.5, "8-15": 11.55, "15-22": 18.87, ">22": 23.18}
ROWS = []
for nm in ("1-8", "<8", "8-15", "15-22", ">22"):
    if nm not in PLANT:
        continue
    v = VM[nm]
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2
    Kp_eff = 0.3 + lsf
    Ki_eff = 0.15 * (1 + lsf / 0.3)
    p = PLANT[nm]
    pm, wc, Ms, Mt = margins(Kp_eff, Ki_eff, p["K"], 6.0, p["d"], p["T"])
    pr("    %-8s %8.3f %8.3f %8.3f %8.3f %8.3f | %8.1f %8.3f %8.2f %8.2f"
       % (nm, p["K"], p["d"], p["T"], Kp_eff, Ki_eff, pm, wc, Ms, Mt))
    ROWS.append((nm, v, p, Kp_eff, Ki_eff, pm, wc, Ms, Mt))
RES["asflown"] = [dict(band=r[0], v=r[1], laf=r[2]["K"], d=r[2]["d"], T=r[2]["T"],
                       kp_eff=r[3], ki_eff=r[4], pm=r[5], wc=r[6], ms=r[7], mt=r[8]) for r in ROWS]

pr("\n    (b) WITH LAF SET TO THE MEASURED VALUE per band (the feedforward then delivers 1.00 of the")
pr("        demand, and the loop gain becomes Kp_eff alone):")
pr("    %-8s %8s %8s | %8s %8s %8s %8s" % ("band", "LAF_set", "Kp_eff", "PM deg", "wc Hz", "Ms", "Mt"))
for (nm, v, p, Kp_eff, Ki_eff, *_rest) in ROWS:
    pm, wc, Ms, Mt = margins(Kp_eff, Ki_eff, p["K"], p["K"], p["d"], p["T"])
    pr("    %-8s %8.3f %8.3f | %8.1f %8.3f %8.2f %8.2f" % (nm, p["K"], Kp_eff, pm, wc, Ms, Mt))

pr("\n    (c) THE LARGEST Kp THE PLANT SUPPORTS at PM >= 45 deg AND Ms <= 2.0, with LAF correct and")
pr("        Ki held at the ratio Ki/Kp the tune ships (0.15/0.3 = 0.5 per second):")
pr("    %-8s %10s %10s | %10s %10s %8s %8s %10s"
   % ("band", "d s", "T s", "Kp_eff max", "Ki_eff", "PM", "Ms", "wc Hz"))
for (nm, v, p, Kp_eff0, Ki_eff0, *_rest) in ROWS:
    best = None
    for Kp in np.logspace(-2, 1.8, 400):
        Ki = 0.5 * Kp
        pm, wc, Ms, Mt = margins(Kp, Ki, p["K"], p["K"], p["d"], p["T"])
        if np.isfinite(pm) and pm >= 45.0 and Ms <= 2.0:
            best = (Kp, Ki, pm, wc, Ms)
    if best:
        pr("    %-8s %10.3f %10.3f | %10.3f %10.3f %8.1f %8.2f %10.3f"
           % (nm, p["d"], p["T"], best[0], best[1], best[2], best[4], best[3]))
        RES.setdefault("kpmax", {})[nm] = dict(kp_eff=best[0], ki_eff=best[1], pm=best[2],
                                               ms=best[4], wc=best[3])
    else:
        pr("    %-8s %10.3f %10.3f | none found" % (nm, p["d"], p["T"]))
pr("\n    to convert Kp_eff back to the TOGGLE: SteerKP = Kp_eff - lsf(v), and the toggle is ONE")
pr("    number for all speeds, so the binding band is the one with the smallest Kp_eff headroom.")
pr("    %-8s %10s %10s %12s" % ("band", "v med", "lsf", "implied SteerKP"))
for (nm, v, p, *_r) in ROWS:
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2
    kpm = RES.get("kpmax", {}).get(nm, {}).get("kp_eff", np.nan)
    pr("    %-8s %10.2f %10.3f %12.3f" % (nm, v, lsf, kpm - lsf))

with open(os.path.join(L.SCRATCH, "v293_ident_d.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_d.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_d.txt / .json")
