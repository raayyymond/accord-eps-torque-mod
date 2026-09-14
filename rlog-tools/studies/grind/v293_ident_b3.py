# -*- coding: utf-8 -*-
"""v293_ident_b3.py -- PART B (FINAL): THE PLANT, per speed band, on V293's open-loop torque map.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.  Supersedes v293_ident_b.py and _b2.py.

WHAT CHANGED FROM _b2: band exposure.  Assigning a whole clean stretch to one band emptied the <8 and
>22 cells, because a real stretch crosses speeds.  Here the unit of analysis is a WINDOW (the same
window Welch would use anyway): every clean stretch is cut into overlapping windows, and each WINDOW is
assigned to the band holding >= 80 % of its samples.  Held-out validation still splits by PARENT
STRETCH (odd/even), so no window of a stretch is ever in both halves.

THE FRAME, fixed from the fork's source and confirmed on the wire:
  latcontrol_torque.update() returns `-output_torque`; controlsd assigns it to actuators.torque.
  So  u = output_torque = -actuators.torque  is the torque in the same frame as actualLateralAccel,
  and openpilot's LAF is defined by  actualLateralAccel = LAF * u.  The carcontroller then sends
  interp(-torque*STEER_MAX) = +output_torque*4096, so the 427 tap is in phase with +u.

🛑 u IS NOT EXOGENOUS.  Every gain is an INSTRUMENTAL-VARIABLE (joint input-output) estimate with
z = desiredCurvature * v^2 as the instrument:  H = S_zy / S_zu.  The direct estimate is printed
beside it so the feedback bias is a measurement, not an assumption.
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
NPER, STEP, PURITY = 1024, 256, 0.80          # 10.24 s windows, 2.56 s hop
FLO, FHI, CMIN = 0.15, 1.5, 0.35

pr("=" * 110)
pr("V293 PLANT IDENTIFICATION -- PART B: THE PLANT   (route 70, 2026-09-13, the first V293 flight)")
pr("=" * 110)

CH = dict(u_op=S_OP * g["op_torque"], u_tap=S_TAP * g["T"],
          y_ang=S_ANG * g["ang"], y_rate=S_RATE * g["rate_dps"],
          y_la=g["la_act"], y_yaw=g["gyro_yaw"] * g["v"],
          z=g["des_curv"] * g["v"] ** 2)

# ======================================================================================================
# B0.  the map on the wire, and the frame
# ======================================================================================================
e = g["eng"] & np.isfinite(g["la_act"]) & np.isfinite(g["T"]) & np.isfinite(g["op_torque"])


def slope(x, y):
    A = np.vstack([np.asarray(x, float), np.ones(len(x))]).T
    s, i = np.linalg.lstsq(A, np.asarray(y, float), rcond=None)[0]
    return float(s), float(i), L.r2(y, A @ [s, i])


pr("\nB0. THE INPUT CHANNEL -- V293's torque map, measured on the wire [EVIDENCE]")
tb = e & (np.abs(g["cmd"]) > 50) & (np.abs(g["cmd"]) < 2500) & (g["press"] < 0.5)
s_tc, i_tc, r_tc = slope(np.abs(g["cmd"][tb]), np.abs(g["T"][tb]))
pr("    |427 tap| = %.4f * |0xE4 cmd| %+.1f   R2 %.3f   n %d   (hands-off, 50<|cmd|<2500)"
   % (s_tc, i_tc, r_tc, tb.sum()))
pr("    the BUILT IMAGE's surface at full taper is 10.3355/16.1876 = %.4f -- agreement %.1f %%"
   % (10.3355 / 16.1876, 100 * s_tc / (10.3355 / 16.1876)))
pr("    STEER_MAX = 4096 (cmd = -3988.5*actuators.torque, R2 0.978), so openpilot's FULL SCALE")
pr("    torque 1.0 buys %.0f counts of delivered EPS torque on V293 -- the rail is 2461, reached at"
   % (4096 * s_tc))
pr("    |torque| = %.3f.  On V282 the same command bought about TWICE that below idx 116." % (2461 / (4096 * s_tc)))

# ======================================================================================================
# B1.  windows
# ======================================================================================================
mask = L.clean_mask(g, hands_off=True, min_v=1.0)
strets = L.stretches(mask, NPER)
WIN = {k: [] for k in range(len(L.BANDS))}
for si, (a, b) in enumerate(strets):
    for s0 in range(a, b - NPER + 1, STEP):
        v = g["v"][s0:s0 + NPER]
        bidx = np.array([L.band_of(x) for x in v])
        cnt = np.bincount(bidx, minlength=len(L.BANDS))
        k = int(np.argmax(cnt))
        if cnt[k] / float(NPER) >= PURITY:
            WIN[k].append((s0, si))
pr("\nB1. WINDOWS  (%.2f s, hop %.2f s, >= %.0f%% of samples in band; from %d clean stretches >= %.1f s)"
   % (NPER * DT, STEP * DT, 100 * PURITY, len(strets), NPER * DT))
pr("    %-8s %8s %11s %9s %10s %10s %10s"
   % ("band", "windows", "indep sec", "v med", "|ang| p50", "|ang| p95", "stretches"))
for k in range(len(L.BANDS)):
    W = WIN[k]
    if not W:
        pr("    %-8s %8d" % (L.BANDNAME[k], 0)); continue
    idx = np.unique(np.concatenate([np.arange(s, s + NPER) for s, _ in W]))
    pr("    %-8s %8d %11.1f %9.2f %10.2f %10.2f %10d"
       % (L.BANDNAME[k], len(W), len(idx) * DT, np.median(g["v"][idx]),
          np.percentile(np.abs(g["ang"][idx]), 50), np.percentile(np.abs(g["ang"][idx]), 95),
          len(set(si for _, si in W))))
RES["windows"] = {L.BANDNAME[k]: len(WIN[k]) for k in range(len(L.BANDS))}
VMED = {}
for k in range(len(L.BANDS)):
    if WIN[k]:
        idx = np.unique(np.concatenate([np.arange(s, s + NPER) for s, _ in WIN[k]]))
        VMED[L.BANDNAME[k]] = float(np.median(g["v"][idx]))


# ======================================================================================================
# estimators
# ======================================================================================================
def pooled(W, ukey, ykey):
    """pool the cross-spectra over the given windows, then divide."""
    if not W:
        return None
    win = signal.get_window("hann", NPER)
    sc = 1.0 / (L.FS * np.sum(win ** 2))
    fr = np.fft.rfftfreq(NPER, DT)
    Szu = np.zeros(len(fr), complex); Szy = np.zeros(len(fr), complex)
    Puy = np.zeros(len(fr), complex)
    Pzz = np.zeros(len(fr)); Puu = np.zeros(len(fr)); Pyy = np.zeros(len(fr))
    n = 0
    for (s0, _) in W:
        sl = slice(s0, s0 + NPER)
        z, u, y = CH["z"][sl], CH[ukey][sl], CH[ykey][sl]
        if not (np.all(np.isfinite(z)) and np.all(np.isfinite(u)) and np.all(np.isfinite(y))):
            continue
        z = signal.detrend(z) * win; u = signal.detrend(u) * win; y = signal.detrend(y) * win
        Z, U, Y = np.fft.rfft(z), np.fft.rfft(u), np.fft.rfft(y)
        Szu += np.conj(Z) * U * sc; Szy += np.conj(Z) * Y * sc
        Puy += np.conj(U) * Y * sc
        Pzz += (np.abs(Z) ** 2) * sc; Puu += (np.abs(U) ** 2) * sc; Pyy += (np.abs(Y) ** 2) * sc
        n += 1
    if n == 0:
        return None
    return dict(f=fr, n=n, H=Szy / np.where(np.abs(Szu) < 1e-300, np.nan, Szu),
                Hd=Puy / np.where(Puu < 1e-300, np.nan, Puu),
                czu=np.abs(Szu) ** 2 / np.maximum(Pzz * Puu, 1e-300),
                czy=np.abs(Szy) ** 2 / np.maximum(Pzz * Pyy, 1e-300),
                cuy=np.abs(Puy) ** 2 / np.maximum(Puu * Pyy, 1e-300))


def sel_band(R):
    coh = np.minimum(R["czu"], R["czy"])
    return (R["f"] >= FLO) & (R["f"] <= FHI) & (coh > CMIN) & np.isfinite(R["H"]), coh


def fit(R, direct=False):
    """M0 (gain+dead), M1 (first order + dead), M2 (second order + dead, numerator == 1)."""
    Hall = R["Hd"] if direct else R["H"]
    sel, coh = sel_band(R)
    sel = sel & np.isfinite(Hall)
    if sel.sum() < 4:
        return None
    f, H, w = R["f"][sel], Hall[sel], coh[sel]
    s = 2j * np.pi * f
    norm = float(np.sum(np.abs(H) ** 2 * w))

    def vaf(Hm):
        return 1.0 - float(np.sum(np.abs(Hm - H) ** 2 * w)) / norm

    def ls(fn, p0, bnd):
        return optimize.least_squares(
            lambda p: np.concatenate([((fn(p) - H) * np.sqrt(w)).real, ((fn(p) - H) * np.sqrt(w)).imag]),
            p0, bounds=bnd, max_nfev=3000)

    K0 = float(np.abs(H[0]))
    lim = 20 * abs(K0) + 1
    m0 = ls(lambda p: p[0] * np.exp(-s * p[1]), [K0, 0.15], ([-lim, 0], [lim, 0.6]))
    b1 = None
    for T0 in (0.02, 0.1, 0.3, 0.8, 2.0):
        for d0 in (0.005, 0.08, 0.2, 0.35):
            r = ls(lambda p: p[0] * np.exp(-s * p[2]) / (1 + s * p[1]), [K0, T0, d0],
                   ([-lim, 0, 0], [lim, 8.0, 0.6]))
            if b1 is None or r.cost < b1.cost:
                b1 = r
    b2 = None
    for k0 in (5.0, 60.0):
        for J0 in (1e-3, 0.1):
            for d0 in (0.02, 0.2):
                sgn = 1.0 if K0 == 0 else np.sign(np.real(H[0]) if np.real(H[0]) != 0 else 1.0)
                r = ls(lambda p: np.exp(-s * p[3]) / (p[0] * s ** 2 + p[1] * s + p[2]),
                       [J0, max(1e-3, k0 * 0.2), k0 * sgn if sgn else k0, d0],
                       ([0, 0, -1e6, 0], [200.0, 1e5, 1e6, 0.6]), )
                if b2 is None or r.cost < b2.cost:
                    b2 = r
    H0 = m0.x[0] * np.exp(-s * m0.x[1])
    H1 = b1.x[0] * np.exp(-s * b1.x[2]) / (1 + s * b1.x[1])
    H2 = np.exp(-s * b2.x[3]) / (b2.x[0] * s ** 2 + b2.x[1] * s + b2.x[2])
    return dict(fmin=float(f.min()), fmax=float(f.max()), nf=int(sel.sum()),
                m0=dict(K=float(m0.x[0]), d=float(m0.x[1]), vaf=vaf(H0)),
                m1=dict(K=float(b1.x[0]), T=float(abs(b1.x[1])), d=float(abs(b1.x[2])), vaf=vaf(H1)),
                m2=dict(J=float(b2.x[0]), c=float(b2.x[1]), k=float(b2.x[2]), d=float(b2.x[3]),
                        vaf=vaf(H2)))


def score_held(W, ukey, ykey, par):
    R = pooled(W, ukey, ykey)
    if R is None:
        return np.nan, np.nan
    sel, coh = sel_band(R)
    if sel.sum() < 4:
        return np.nan, np.nan
    f, H, w = R["f"][sel], R["H"][sel], coh[sel]
    s = 2j * np.pi * f
    Hm = par["K"] * np.exp(-s * par["d"]) / (1 + s * par["T"])
    vaf = 1.0 - float(np.sum(np.abs(Hm - H) ** 2 * w)) / float(np.sum(np.abs(H) ** 2 * w))
    # time domain on the same windows
    T, d, K = par["T"], par["d"], par["K"]
    a = float(np.exp(-DT / T)) if T > 1e-6 else 0.0
    nd = int(round(d / DT))
    num = den = 0.0
    for (s0, _) in W:
        sl = slice(s0, s0 + NPER)
        u = signal.detrend(CH[ukey][sl]); y = signal.detrend(CH[ykey][sl])
        if nd > 0:
            u = np.concatenate([np.zeros(nd), u[:-nd]])
        if T > 1e-6:
            yh = K * signal.lfilter([1 - a], [1, -a], u)
        else:
            yh = K * u
        num += float(np.sum((y - yh) ** 2)); den += float(np.sum(y ** 2))
    return vaf, (1.0 - num / den if den > 0 else np.nan)


def split(W):
    ss = sorted(set(si for _, si in W))
    odd = set(ss[0::2]); even = set(ss[1::2])
    return [w for w in W if w[1] in odd], [w for w in W if w[1] in even]


# ======================================================================================================
# B2.  spring or integrator
# ======================================================================================================
pr("\n" + "=" * 110)
pr("B2. IS THE PLANT A SPRING OR AN INTEGRATOR?   log-log slope of |H| over the coherent band")
pr("    torque->ANGLE  slope 0 = SPRING (torque sets an angle) | -1 = INTEGRATOR (torque sets a rate)")
pr("    torque->RATE   slope +1 = SPRING                       |  0 = INTEGRATOR")
pr("=" * 110)
pr("\n    %-7s %6s | %11s %11s | %10s %10s %10s | %s"
   % ("band", "n win", "slope ANG", "slope RATE", "coh 0.2", "coh 0.5", "coh 1.0", "fitted band"))
for k in range(len(L.BANDS)):
    W = WIN[k]
    Ra, Rr = pooled(W, "u_tap", "y_ang"), pooled(W, "u_tap", "y_rate")
    if Ra is None:
        continue
    outs = []
    for R in (Ra, Rr):
        sel, coh = sel_band(R)
        sel = sel & (R["f"] <= 1.2)
        if sel.sum() < 4:
            outs.append(np.nan); continue
        A = np.vstack([np.log10(R["f"][sel]), np.ones(sel.sum())]).T
        sl_, _ = np.linalg.lstsq(A, np.log10(np.abs(R["H"][sel])), rcond=None)[0]
        outs.append(float(sl_))
    sel, coh = sel_band(Ra)
    ff = Ra["f"][sel]
    pr("    %-7s %6d | %11.3f %11.3f | %10.2f %10.2f %10.2f | %.2f-%.2f Hz"
       % (L.BANDNAME[k], Ra["n"], outs[0], outs[1],
          np.interp(0.2, Ra["f"], coh), np.interp(0.5, Ra["f"], coh), np.interp(1.0, Ra["f"], coh),
          ff.min() if len(ff) else np.nan, ff.max() if len(ff) else np.nan))
    RES.setdefault("slopes", {})[L.BANDNAME[k]] = dict(ang=outs[0], rate=outs[1])

FG = [0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5]


def cont_phase(f, H, f0=0.25):
    ph = np.degrees(np.angle(H))
    k0 = int(np.argmin(np.abs(f - f0)))
    o = ph.copy()
    for i in range(k0 + 1, len(ph)):
        while o[i] - o[i - 1] > 180:
            o[i] -= 360
        while o[i] - o[i - 1] < -180:
            o[i] += 360
    for i in range(k0 - 1, -1, -1):
        while o[i] - o[i + 1] > 180:
            o[i] -= 360
        while o[i] - o[i + 1] < -180:
            o[i] += 360
    return o


pr("\n    torque(427 counts) -> steering angle(deg), IV estimate.  f (Hz):"
   + "".join("%8.2f" % x for x in FG))
for k in range(len(L.BANDS)):
    R = pooled(WIN[k], "u_tap", "y_ang")
    if R is None:
        continue
    _, coh = sel_band(R)
    ph = cont_phase(R["f"], R["H"])
    pr("    %-7s %-8s" % (L.BANDNAME[k], "|H|x1e3") + "".join("%8.2f" % x for x in np.interp(FG, R["f"], 1000 * np.abs(R["H"]))))
    pr("    %-7s %-8s" % ("", "phase") + "".join("%8.1f" % x for x in np.interp(FG, R["f"], ph)))
    pr("    %-7s %-8s" % ("", "coh") + "".join("%8.2f" % x for x in np.interp(FG, R["f"], coh)))
    pr("    %-7s %-8s" % ("", "tau_eq s") + "".join("%8.3f" % x for x in
                                                    (-np.interp(FG, R["f"], ph) / (360.0 * np.array(FG)))))
    RES.setdefault("Hang", {})[L.BANDNAME[k]] = dict(
        f=FG, mag=list(np.interp(FG, R["f"], np.abs(R["H"]))),
        phase=list(np.interp(FG, R["f"], ph)), coh=list(np.interp(FG, R["f"], coh)))

# ======================================================================================================
# B3.  the models
# ======================================================================================================
pr("\n" + "=" * 110)
pr("B3. MODELS FITTED TO THE IV TRANSFER ESTIMATE, coherence-weighted, %.2f-%.2f Hz, coh > %.2f."
   % (FLO, FHI, CMIN))
pr("    HELD OUT: fit on ODD parent stretches, score on EVEN ones (transfer VAF and time-domain R2).")
pr("    M0 = K e^{-sd}  (openpilot's own model)   M1 = K e^{-sd}/(1+sT)   M2 = e^{-sd}/(Js^2+cs+k)")
pr("=" * 110)
CHANS = [("u_op", "y_la", "LAF: openpilot torque -> actualLateralAccel  [m/s^2 per unit]"),
         ("u_op", "y_yaw", "openpilot torque -> GYRO lat accel          [m/s^2 per unit]"),
         ("u_tap", "y_ang", "delivered 427 torque -> steering angle      [deg per count]"),
         ("u_tap", "y_la", "delivered 427 torque -> actualLateralAccel  [m/s^2 per count]")]
for ukey, ykey, lab in CHANS:
    pr("\n    %s" % lab)
    pr("    %-7s %5s | %10s %6s %5s | %10s %6s %6s %5s | %5s %7s | %8s %7s"
       % ("band", "nwin", "M0 K", "M0 d", "VAF", "M1 K", "M1 T", "M1 d", "VAF", "M2", "M2 fn", "heldVAF", "heldR2"))
    for k in range(len(L.BANDS)):
        W = WIN[k]
        R = pooled(W, ukey, ykey)
        if R is None:
            continue
        F = fit(R)
        if F is None:
            continue
        odd, even = split(W)
        Fo = fit(pooled(odd, ukey, ykey)) if odd else None
        hv, hr = score_held(even, ukey, ykey, Fo["m1"]) if (Fo and even) else (np.nan, np.nan)
        fn = (np.sqrt(abs(F["m2"]["k"]) / F["m2"]["J"]) / (2 * np.pi)) if F["m2"]["J"] > 1e-9 else np.inf
        pr("    %-7s %5d | %10.4f %6.3f %5.2f | %10.4f %6.3f %6.3f %5.2f | %5.2f %7.2f | %8.2f %7.2f"
           % (L.BANDNAME[k], R["n"], F["m0"]["K"], F["m0"]["d"], F["m0"]["vaf"],
              F["m1"]["K"], F["m1"]["T"], F["m1"]["d"], F["m1"]["vaf"], F["m2"]["vaf"], fn, hv, hr))
        RES.setdefault("fit", {}).setdefault(lab, {})[L.BANDNAME[k]] = dict(
            nwin=R["n"], m0=F["m0"], m1=F["m1"], m2=F["m2"], held_vaf=hv, held_r2=hr)
    # the feedback bias, for the record
    row = []
    for k in range(len(L.BANDS)):
        R = pooled(WIN[k], ukey, ykey)
        if R is None:
            row.append("  --  "); continue
        Fd = fit(R, direct=True)
        row.append("%6.3f" % Fd["m0"]["K"] if Fd else "  --  ")
    pr("    %-7s %5s | DIRECT (feedback-biased) M0 K per band: %s"
       % ("", "", "  ".join("%s=%s" % (L.BANDNAME[i], row[i]) for i in range(len(row)))))

# ======================================================================================================
# B4.  independent static estimator -- steady turns
# ======================================================================================================
pr("\n" + "=" * 110)
pr("B4. AN INDEPENDENT STATIC ESTIMATE -- SUSTAINED TURNS (a check on the frequency-domain fits)")
pr("    runs >= 3 s with |la_des| > 0.5 m/s^2, one sign, and |d(la_act)/dt| < 1.0 m/s^3: at quasi-")
pr("    steady state the lag and the dead time do not matter, so the mean ratio IS the static gain.")
pr("=" * 110)
dla = np.gradient(g["la_act"], DT)
steady = mask & (np.abs(g["la_des"]) > 0.5) & (np.abs(dla) < 1.0)
runs = L.stretches(steady, int(3 * L.FS))
pr("\n    %-8s %7s %9s %11s %11s %11s %11s"
   % ("band", "runs", "seconds", "LAF (la/u)", "gyro LAF", "cnt/deg", "la per 1e3 cnt"))
for k in range(len(L.BANDS)):
    lo, hi = L.BANDS[k]
    U, Y, YG, TAP, ANG = [], [], [], [], []
    nr = 0
    for (a, b) in runs:
        vv = np.median(g["v"][a:b])
        if not (lo <= vv < hi):
            continue
        nr += 1
        U.append(np.mean(CH["u_op"][a:b])); Y.append(np.mean(CH["y_la"][a:b]))
        YG.append(np.mean(CH["y_yaw"][a:b])); TAP.append(np.mean(CH["u_tap"][a:b]))
        ANG.append(np.mean(CH["y_ang"][a:b]))
    if nr < 4:
        pr("    %-8s %7d  (too few runs)" % (L.BANDNAME[k], nr)); continue
    U, Y, YG, TAP, ANG = map(np.array, (U, Y, YG, TAP, ANG))
    sec = sum((b - a) for (a, b) in runs if lo <= np.median(g["v"][a:b]) < hi) * DT
    s1, _, _ = slope(U, Y); s2, _, _ = slope(U, YG)
    s3, _, _ = slope(ANG, TAP); s4, _, _ = slope(TAP, Y)
    pr("    %-8s %7d %9.1f %11.3f %11.3f %11.2f %11.4f"
       % (L.BANDNAME[k], nr, sec, s1, s2, s3, 1000 * s4))
    RES.setdefault("steady", {})[L.BANDNAME[k]] = dict(n=nr, sec=sec, laf=s1, laf_gyro=s2,
                                                       k_cnt_per_deg=s3, la_per_1000cnt=s4)

# ======================================================================================================
# B5.  the speed laws
# ======================================================================================================
pr("\n" + "=" * 110)
pr("B5. THE SPEED LAWS")
pr("=" * 110)


def power_law(xs, ys, lab):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    ok = np.isfinite(xs) & np.isfinite(ys) & (xs > 0) & (ys > 0)
    if ok.sum() < 3:
        pr("      %-52s  n=%d, no law fitted" % (lab, ok.sum())); return np.nan
    A = np.vstack([np.log(xs[ok]), np.ones(ok.sum())]).T
    p, q = np.linalg.lstsq(A, np.log(ys[ok]), rcond=None)[0]
    pr("      %-52s  ~ v^%+.2f   (R2 %.3f, n %d)" % (lab, p, L.r2(np.log(ys[ok]), A @ [p, q]), ok.sum()))
    return float(p)


FIT = RES.get("fit", {})
LAB_LAF = "LAF: openpilot torque -> actualLateralAccel  [m/s^2 per unit]"
LAB_GYR = "openpilot torque -> GYRO lat accel          [m/s^2 per unit]"
LAB_ANG = "delivered 427 torque -> steering angle      [deg per count]"
pr("\n    (a) openpilot's PREMISE is that lat accel per unit torque does not depend on speed.")
pr("    %-8s %8s %10s %10s %10s %10s %10s %10s"
   % ("band", "v med", "LAF fit", "LAF steady", "LAF gyro", "vs 6.0", "dead d s", "lag T s"))
xs, ys = [], []
for k in range(len(L.BANDS)):
    nm = L.BANDNAME[k]
    d = FIT.get(LAB_LAF, {}).get(nm)
    if not d:
        continue
    st = RES.get("steady", {}).get(nm, {})
    dg = FIT.get(LAB_GYR, {}).get(nm, {}).get("m1", {})
    pr("    %-8s %8.2f %10.3f %10.3f %10.3f %10.3f %10.3f %10.3f"
       % (nm, VMED[nm], d["m1"]["K"], st.get("laf", np.nan), dg.get("K", np.nan),
          d["m1"]["K"] / 6.0, d["m1"]["d"], d["m1"]["T"]))
    xs.append(VMED[nm]); ys.append(d["m1"]["K"])
pr("")
RES["laf_power"] = power_law(xs, ys, "LAF (m/s^2 per unit openpilot torque)")
xs2 = [VMED[n] for n in RES.get("steady", {})]
ys2 = [RES["steady"][n]["laf"] for n in RES.get("steady", {})]
RES["laf_power_steady"] = power_law(xs2, ys2, "LAF from sustained turns (independent)")

pr("\n    (b) SELF-ALIGNING STIFFNESS  k = 1/(DC gain of torque->angle), in delivered 427 counts per")
pr("        degree of steady steering angle.  Tyre prediction k ~ v^2; speed-independent is v^0.")
pr("    %-8s %8s %12s %12s %12s %12s"
   % ("band", "v med", "DC deg/cnt", "k cnt/deg", "k steady", "k/v^2"))
xs, ys = [], []
for k in range(len(L.BANDS)):
    nm = L.BANDNAME[k]
    d = FIT.get(LAB_ANG, {}).get(nm)
    if not d:
        continue
    kc = 1.0 / d["m1"]["K"] if d["m1"]["K"] else np.nan
    pr("    %-8s %8.2f %12.5f %12.2f %12.2f %12.4f"
       % (nm, VMED[nm], d["m1"]["K"], kc,
          RES.get("steady", {}).get(nm, {}).get("k_cnt_per_deg", np.nan), kc / VMED[nm] ** 2))
    xs.append(VMED[nm]); ys.append(kc)
pr("")
RES["k_power"] = power_law(xs, ys, "k (delivered counts per degree)")
xs3 = [VMED[n] for n in RES.get("steady", {})]
ys3 = [RES["steady"][n]["k_cnt_per_deg"] for n in RES.get("steady", {})]
RES["k_power_steady"] = power_law(xs3, ys3, "k from sustained turns (independent)")

pr("\n    (c) DEAD TIME vs LAG POLE -- the split the tau study could not make, now that u is KNOWN.")
pr("    %-8s %8s %10s %10s %10s %12s %12s"
   % ("band", "v med", "dead s", "lag T s", "pole Hz", "tau_eq 0.5Hz", "tau_eq 1Hz"))
for k in range(len(L.BANDS)):
    nm = L.BANDNAME[k]
    d = FIT.get(LAB_ANG, {}).get(nm)
    if not d:
        continue
    T, dd = d["m1"]["T"], d["m1"]["d"]
    pole = 1.0 / (2 * np.pi * T) if T > 1e-6 else np.inf
    te = [(np.degrees(np.arctan(2 * np.pi * ff * T)) + 360.0 * ff * dd) / (360.0 * ff) for ff in (0.5, 1.0)]
    pr("    %-8s %8.2f %10.3f %10.3f %10.2f %12.3f %12.3f" % (nm, VMED[nm], dd, T, pole, te[0], te[1]))

# ======================================================================================================
# B6.  friction and amplitude
# ======================================================================================================
pr("\n" + "=" * 110)
pr("B6. FRICTION, DEADBAND AND AMPLITUDE DEPENDENCE")
pr("=" * 110)
pr("\n    (a) the stiction model fitted directly:  u = k*theta + c*theta' + F*sign(theta') + u0,")
pr("        low-passed <= 0.5 Hz, on frames with |theta'| > 0.3 deg/s.  F is COULOMB FRICTION.")
pr("    %-8s %8s %10s %10s %10s %10s %7s %11s %12s"
   % ("band", "n s", "k cnt/deg", "c cnt/dps", "F counts", "u0 counts", "R2", "F in 0xE4", "F as torque"))
sos = signal.butter(4, 0.5, btype="lowpass", fs=L.FS, output="sos")
for k in range(len(L.BANDS)):
    W = WIN[k]
    if not W:
        continue
    U, TH, TD = [], [], []
    for (s0, _) in W[::4]:
        sl = slice(s0, s0 + NPER)
        U.append(signal.sosfiltfilt(sos, CH["u_tap"][sl]))
        th = signal.sosfiltfilt(sos, CH["y_ang"][sl])
        TH.append(th); TD.append(np.gradient(th, DT))
    U, TH, TD = np.concatenate(U), np.concatenate(TH), np.concatenate(TD)
    s = np.abs(TD) > 0.3
    if s.sum() < 400:
        continue
    A = np.vstack([TH[s], TD[s], np.sign(TD[s]), np.ones(s.sum())]).T
    co, *_ = np.linalg.lstsq(A, U[s], rcond=None)
    pr("    %-8s %8.0f %10.2f %10.2f %10.1f %10.1f %7.3f %11.0f %12.4f"
       % (L.BANDNAME[k], s.sum() * DT, co[0], co[1], co[2], co[3], L.r2(U[s], A @ co),
          co[2] / s_tc, co[2] / s_tc / 4096.0))
    RES.setdefault("friction", {})[L.BANDNAME[k]] = dict(k=co[0], c=co[1], F=co[2], u0=co[3])
pr("      'F as torque' is the Coulomb term as a fraction of openpilot's full-scale torque (1.0).")
pr("      SteerFriction's own unit is lateral accel: multiply that column by the band's LAF.")

pr("\n    (b) AMPLITUDE DEPENDENCE (friction shows as gain RISING with amplitude).  Windows split")
pr("        into terciles by the band-passed 0.2-2 Hz rms of the instrument z:")
pr("    %-8s %34s %10s %10s %10s %10s" % ("band", "channel", "LOW", "MID", "HIGH", "HIGH/LOW"))
for k in range(len(L.BANDS)):
    W = WIN[k]
    if len(W) < 9:
        continue
    rms = np.array([np.std(L.bandpass(CH["z"][s0:s0 + NPER], 0.2, 2.0)) for s0, _ in W])
    o = np.argsort(rms)
    n3 = len(W) // 3
    G = [[W[i] for i in o[:n3]], [W[i] for i in o[n3:2 * n3]], [W[i] for i in o[2 * n3:]]]
    for ukey, ykey, lab in (("u_tap", "y_ang", "427 -> deg"), ("u_op", "y_la", "op torque -> m/s^2 (LAF)")):
        vals = []
        for gg in G:
            R = pooled(gg, ukey, ykey)
            if R is None:
                vals.append(np.nan); continue
            sel, coh = sel_band(R)
            sel = sel & (R["f"] <= 0.6)
            vals.append(float(np.mean(np.abs(R["H"][sel]))) if sel.sum() else np.nan)
        pr("    %-8s %34s %10.4f %10.4f %10.4f %10.3f"
           % (L.BANDNAME[k], lab, vals[0], vals[1], vals[2],
              vals[2] / vals[0] if vals[0] else np.nan))

with open(os.path.join(L.SCRATCH, "v293_ident_b3.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_b3.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_b3.txt / .json")
