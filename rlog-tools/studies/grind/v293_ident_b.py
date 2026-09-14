# -*- coding: utf-8 -*-
"""v293_ident_b.py -- PART B: THE PLANT, identified per speed band on the V293 open-loop torque map.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

WHY THIS DRIVE CAN IDENTIFY THE PLANT AT ALL.  With 0xC62E6 = 0 the EPS LKAS lane carries no rate
feedback, no D and no I: the delivered lane torque is a static function of the 0xE4 command alone
(T = 10.3355 * demand_index, rail 2461, verified against the golden model's byte-exact march in
v293_ident_surface.py, and against the wire in part A).  So for the first time `u` = the torque the
EPS applied is KNOWN, and everything downstream of it is the car.

🛑 u IS STILL NOT EXOGENOUS -- it is openpilot's own output and depends on the measured angle.  Every
gain below is therefore an INSTRUMENTAL-VARIABLE estimate with z = the planner's desired curvature
(camera + road) as the instrument:  H = S_zy / S_zu.  The direct (biased) estimate is printed beside
it so the size of the feedback bias is visible rather than assumed.

Sign conventions are MEASURED here, not assumed (section B0).
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

pr("=" * 104)
pr("V293 PLANT IDENTIFICATION -- PART B: THE PLANT, PER SPEED BAND")
pr("=" * 104)

# ======================================================================================================
# B0.  Signs, units, and the input channel
# ======================================================================================================
pr("\nB0. SIGNS AND UNITS, MEASURED [EVIDENCE]")
e = g["eng"] & np.isfinite(g["la_act"]) & np.isfinite(g["T"])
big = e & (np.abs(g["cmd"]) > 100)


def slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    A = np.vstack([x, np.ones(len(x))]).T
    s, i = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(s), float(i), L.r2(y, A @ [s, i]), float(np.corrcoef(x, y)[0, 1])


pr("    (a) instantaneous pairs -- only meaningful for channels with NO relative phase")
for nm, x, y in (("0x14A angle -> carState.steeringAngleDeg", g["ang"][e], g["sa"][e]),
                 ("d(0x14A angle)/dt -> 0x18F rate (deg/s)",
                  np.gradient(g["ang"], DT)[e], g["rate_dps"][e]),
                 ("0x14A angle -> actualLateralAccel", g["ang"][e], g["la_act"][e]),
                 ("actualLateralAccel -> currentCurvature*v^2",
                  g["la_act"][e], g["curv_now"][e] * g["v"][e] ** 2),
                 ("gyro yaw*v -> actualLateralAccel", g["gyro_yaw"][e] * g["v"][e], g["la_act"][e]),
                 ("desiredCurvature*v^2 -> desiredLateralAccel",
                  g["des_curv"][e] * g["v"][e] ** 2, g["la_des"][e]),
                 ("desiredLateralAccel -> actualLateralAccel", g["la_des"][e], g["la_act"][e]),
                 ("427 tap -> 0xE4 cmd", g["T"][big], g["cmd"][big]),
                 ("0xE4 cmd -> actuators.torque", g["cmd"][e], g["op_torque"][e])):
    s, i, rr, cc = slope(x, y)
    pr("    %-46s slope %+10.4f  corr %+.4f  R2 %.4f" % (nm, s, cc, rr))

pr("\n    (b) 🛑 torque and angle are ~90 deg apart, so an INSTANTANEOUS slope reads near zero and its")
pr("        sign is noise.  The sign is taken from the LOW-FREQUENCY (0.03-0.3 Hz) correlation, where")
pr("        the self-aligning spring dominates and torque and angle are in phase, and cross-checked")
pr("        against the lagged NCC peak of the 0.2-2 Hz band-passed pair.")
mlow = L.clean_mask(g, hands_off=True, min_v=3.0)
stl = L.stretches(mlow, int(20 * L.FS))
accum = []
for (a, b) in stl:
    tl = L.bandpass(g["T"][a:b], 0.03, 0.3)
    al = L.bandpass(g["ang"][a:b], 0.03, 0.3)
    ll = L.bandpass(g["la_act"][a:b], 0.03, 0.3)
    ol = L.bandpass(g["op_torque"][a:b], 0.03, 0.3)
    accum.append((np.corrcoef(tl, al)[0, 1], np.corrcoef(tl, ll)[0, 1],
                  np.corrcoef(ol, ll)[0, 1], np.corrcoef(ol, al)[0, 1]))
accum = np.array(accum)
pr("        over %d stretches >= 20 s, median low-frequency correlation:" % len(stl))
pr("          427 tap        vs 0x14A angle          %+.4f" % np.median(accum[:, 0]))
pr("          427 tap        vs actualLateralAccel   %+.4f" % np.median(accum[:, 1]))
pr("          actuators.torque vs actualLateralAccel %+.4f" % np.median(accum[:, 2]))
pr("          actuators.torque vs 0x14A angle        %+.4f" % np.median(accum[:, 3]))

SGN = 1.0 if np.median(accum[:, 2]) * np.median(accum[:, 1]) > 0 else -1.0
SGN = -1.0 if np.median(accum[:, 1]) > 0 and np.median(accum[:, 2]) < 0 else SGN
# put EVERYTHING in openpilot's own torque frame: the frame in which `actuators.torque` is the input
# and `actualLateralAccel` is the output, because that is the frame LAF is defined in.
S_TAP = 1.0 if np.median(accum[:, 1]) > 0 else -1.0     # tap -> +actualLateralAccel
S_ANG = 1.0 if np.median(accum[:, 0]) * np.median(accum[:, 1]) > 0 else -1.0
s_ang_la, _, _, _ = slope(g["ang"][e], g["la_act"][e])
S_ANG = 1.0 if s_ang_la > 0 else -1.0                   # angle -> +actualLateralAccel
s_ar, _, _, _ = slope(np.gradient(g["ang"], DT)[e], g["rate_dps"][e])
S_RATE = S_ANG * (1.0 if s_ar > 0 else -1.0)            # rate in the same frame as S_ANG*angle
pr("\n    => FRAME: openpilot's torque frame (the one LAF is defined in).  Applied factors:")
pr("       u_op   = actuators.torque                          [-1,1]")
pr("       u_tap  = %+.0f * 427 tap                             counts of delivered lane torque" % S_TAP)
pr("       y_ang  = %+.0f * 0x14A angle                          deg" % S_ANG)
pr("       y_rate = %+.0f * (0x18F rate / 8)                     deg/s" % S_RATE)
pr("       y_la   = torqueState.actualLateralAccel            m/s^2")
pr("       y_yaw  = raw gyro yaw * v                          m/s^2  (independent instrument)")
pr("       z      = controlsState.desiredCurvature * v^2      m/s^2  THE INSTRUMENT (camera + road)")

# ======================================================================================================
# B1.  the clean stretches, split for held-out validation
# ======================================================================================================
MINSEC = 8.0
m = L.clean_mask(g, hands_off=True, min_v=1.0)
st = L.stretches(m, int(MINSEC * L.FS))
byband = {k: [] for k in range(len(L.BANDS))}
for (a, b) in st:
    # split a long stretch at band boundaries so a cell is homogeneous in speed
    vv = g["v"][a:b]
    bidx = np.array([L.band_of(x) for x in vv])
    cut = np.flatnonzero(np.diff(bidx) != 0) + 1
    for s0, s1 in zip(np.concatenate([[0], cut]), np.concatenate([cut, [len(vv)]])):
        if s1 - s0 >= int(MINSEC * L.FS):
            byband[bidx[s0]].append((a + s0, a + s1))
pr("\nB1. CLEAN STRETCHES per band (engaged, hands-off, unsaturated, >= %.0f s, homogeneous in band)"
   % MINSEC)
pr("    %-8s %7s %8s   %s" % ("band", "n", "seconds", "fit/test split (alternating stretches)"))
for k in range(len(L.BANDS)):
    S = byband[k]
    sec = sum((b - a) for a, b in S) * DT
    pr("    %-8s %7d %8.1f   fit %d / test %d" % (L.BANDNAME[k], len(S), sec,
                                                  len(S[0::2]), len(S[1::2])))
RES["stretch_seconds"] = {L.BANDNAME[k]: sum((b - a) for a, b in byband[k]) * DT
                          for k in range(len(L.BANDS))}


def cat(S, key, f=None):
    xs = []
    for (a, b) in S:
        x = g[key][a:b] if f is None else f(a, b)
        xs.append(x)
    return xs


def chan(a, b):
    v = g["v"][a:b]
    return dict(
        u_tap=S_TAP * g["T"][a:b], u_op=g["op_torque"][a:b],
        y_ang=S_ANG * g["ang"][a:b], y_rate=S_RATE * g["rate_dps"][a:b],
        y_la=g["la_act"][a:b], y_yaw=g["gyro_yaw"][a:b] * v,
        z=g["des_curv"][a:b] * v ** 2, v=v,
        z_curv=g["des_curv"][a:b], la_des=g["la_des"][a:b])


# ======================================================================================================
# B2.  THE STATIC GAIN -- M0, openpilot's own model
# ======================================================================================================
pr("\n" + "=" * 104)
pr("B2. M0 -- openpilot's implicit model:  lat_accel = LAF * torque_fraction  (+ friction, + dead time)")
pr("    LAF is what the fork calls SteerLatAccel and it SHIPS AT 6.0 on this drive.")
pr("    Estimated three ways per band, on the SAME low-passed (<= 0.5 Hz) quasi-static data:")
pr("      DIR  direct least squares of y_la on u_op         (BIASED by the feedback -- shown for size)")
pr("      IV   instrumental variables, instrument z         (consistent under closed loop)")
pr("      IVd  IV with the delay first removed (u advanced by the measured NCC lag)")
pr("=" * 104)


def lowpass(x, fc=0.5):
    sos = signal.butter(4, fc, btype="lowpass", fs=L.FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def iv_gain(z, u, y):
    """two-stage least squares through the origin: gain = <z,y>/<z,u>."""
    z = z - z.mean(); u = u - u.mean(); y = y - y.mean()
    den = float(z @ u)
    return float(z @ y) / den if abs(den) > 1e-12 else np.nan


def dir_gain(u, y):
    u = u - u.mean(); y = y - y.mean()
    return float(u @ y) / float(u @ u) if float(u @ u) > 1e-12 else np.nan


pr("\n    %-7s %6s | %7s %7s %7s | %7s %7s | %8s %8s"
   % ("band", "n_s", "LAF_DIR", "LAF_IV", "LAF_IVd", "lag_ms", "corr", "R2_fit", "R2_test"))
laf_tab = {}
for k in range(len(L.BANDS)):
    S = byband[k]
    if not S:
        continue
    fit, test = S[0::2], S[1::2]

    def pool(SS, fc=0.5):
        Z, U, Y, UT = [], [], [], []
        for (a, b) in SS:
            c = chan(a, b)
            Z.append(lowpass(c["z"], fc)); U.append(lowpass(c["u_op"], fc))
            Y.append(lowpass(c["y_la"], fc)); UT.append(lowpass(c["u_tap"], fc))
        return [np.concatenate(x) for x in (Z, U, Y, UT)]

    Zf, Uf, Yf, UTf = pool(fit)
    Zt, Ut, Yt, UTt = pool(test)
    # measured dead time u_op -> y_la on the fit half (0.2-2 Hz band-passed, NCC)
    lags = []
    for (a, b) in fit:
        c = chan(a, b)
        if (b - a) < int(12 * L.FS):
            continue
        lag, cc = L.ncc_lag(L.bandpass(c["u_op"], 0.2, 2.0), L.bandpass(c["y_la"], 0.2, 2.0))
        if np.isfinite(lag):
            lags.append((lag, cc))
    lag_ms = 1000 * np.median([x[0] for x in lags]) if lags else np.nan
    corr = np.median([x[1] for x in lags]) if lags else np.nan
    kk = int(round((lag_ms / 1000.0) * L.FS)) if np.isfinite(lag_ms) else 0

    gd = dir_gain(Uf, Yf)
    gi = iv_gain(Zf, Uf, Yf)
    if kk > 0:
        gid = iv_gain(Zf[:-kk], Uf[:-kk], Yf[kk:])
    else:
        gid = gi
    # held-out: predict y from u with the IVd gain and the lag
    if kk > 0:
        yhat = gid * (Ut[:-kk] - Ut[:-kk].mean()) + Yt[kk:].mean()
        r2t = L.r2(Yt[kk:], yhat)
        yhatf = gid * (Uf[:-kk] - Uf[:-kk].mean()) + Yf[kk:].mean()
        r2f = L.r2(Yf[kk:], yhatf)
    else:
        r2t = L.r2(Yt, gid * (Ut - Ut.mean()) + Yt.mean())
        r2f = L.r2(Yf, gid * (Uf - Uf.mean()) + Yf.mean())
    pr("    %-7s %6.0f | %7.3f %7.3f %7.3f | %7.0f %7.3f | %8.3f %8.3f"
       % (L.BANDNAME[k], len(Zf) * DT + len(Zt) * DT, gd, gi, gid, lag_ms, corr, r2f, r2t))
    laf_tab[L.BANDNAME[k]] = dict(dir=gd, iv=gi, ivd=gid, lag_ms=lag_ms, r2_fit=r2f, r2_test=r2t,
                                  tap_gain=iv_gain(Zf, UTf, Yf))
RES["M0"] = laf_tab
pr("\n    the fork's installed value is LAF = 6.000.  ratio true/installed, per band:")
for k in range(len(L.BANDS)):
    if L.BANDNAME[k] in laf_tab:
        pr("      %-7s  LAF_IVd %6.3f   true/6.0 = %.3f   =>  openpilot's feedforward is %s by %.2fx"
           % (L.BANDNAME[k], laf_tab[L.BANDNAME[k]]["ivd"], laf_tab[L.BANDNAME[k]]["ivd"] / 6.0,
              "SHORT" if laf_tab[L.BANDNAME[k]]["ivd"] < 6.0 else "LONG",
              6.0 / laf_tab[L.BANDNAME[k]]["ivd"] if laf_tab[L.BANDNAME[k]]["ivd"] > 0 else np.nan))
pr("\n    lat accel per 1000 counts of DELIVERED 427 torque (the physical gain, band by band):")
for k in range(len(L.BANDS)):
    if L.BANDNAME[k] in laf_tab:
        pr("      %-7s  %.4f m/s^2 per 1000 counts" % (L.BANDNAME[k],
                                                       1000 * laf_tab[L.BANDNAME[k]]["tap_gain"]))

# ======================================================================================================
# B3.  FREQUENCY DOMAIN -- integrator vs first-order lag vs pure delay
# ======================================================================================================
pr("\n" + "=" * 104)
pr("B3. THE TRANSFER FUNCTIONS, IV form H = S_zy/S_zu, coherence-weighted, per band")
pr("    torque -> RATE and torque -> ANGLE.  An integrator plant (torque commands a RATE) gives")
pr("    |H_rate| flat and |H_ang| ~ 1/f with phase -90 deg.  A spring plant (torque commands an")
pr("    ANGLE) gives |H_ang| flat at low f and |H_rate| ~ f with phase +90 deg.")
pr("=" * 104)
FGRID = [0.15, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]


def pooled_tf(S, ukey, ykey, nper=None):
    """average the cross-spectra over stretches, then divide (a proper pooled estimator).

    nper is chosen as the longest power-of-two window that at least half the stretches can carry,
    so a band made of short stretches is not silently emptied."""
    if nper is None:
        lens = sorted((b - a) for a, b in S)
        nper = 1024
        while nper > 256 and (len([x for x in lens if x >= nper]) < max(1, len(lens) // 2)):
            nper //= 2
    Szu = Szy = Pzz = Puu = Pyy = None
    f = None
    nseg = 0
    for (a, b) in S:
        c = chan(a, b)
        if (b - a) < nper:
            continue
        z, u, y = c["z"], c[ukey], c[ykey]
        if not (np.all(np.isfinite(z)) and np.all(np.isfinite(u)) and np.all(np.isfinite(y))):
            continue
        kw = dict(fs=L.FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        f, a1 = signal.csd(z, u, **kw)
        _, a2 = signal.csd(z, y, **kw)
        _, a3 = signal.welch(z, **kw)
        _, a4 = signal.welch(u, **kw)
        _, a5 = signal.welch(y, **kw)
        w = (b - a)
        Szu = a1 * w if Szu is None else Szu + a1 * w
        Szy = a2 * w if Szy is None else Szy + a2 * w
        Pzz = a3 * w if Pzz is None else Pzz + a3 * w
        Puu = a4 * w if Puu is None else Puu + a4 * w
        Pyy = a5 * w if Pyy is None else Pyy + a5 * w
        nseg += 1
    if Szu is None:
        return None
    H = Szy / Szu
    czu = np.abs(Szu) ** 2 / np.maximum(Pzz * Puu, 1e-30)
    czy = np.abs(Szy) ** 2 / np.maximum(Pzz * Pyy, 1e-30)
    return dict(f=f, H=H, czu=czu, czy=czy, Puu=Puu, Pyy=Pyy, nper=nper, nseg=nseg)


for ykey, unit, lab in (("y_rate", "deg/s per tap-count", "TORQUE -> WHEEL RATE"),
                        ("y_ang", "deg per tap-count", "TORQUE -> STEERING ANGLE")):
    pr("\n    %s   (|H| in %s, x1000)" % (lab, unit))
    pr("    %-7s %-6s" % ("band", "") + "".join("%9.2f" % ff for ff in FGRID))
    for k in range(len(L.BANDS)):
        S = byband[k]
        if not S:
            continue
        R = pooled_tf(S, "u_tap", ykey)
        if R is None:
            continue
        mag = np.interp(FGRID, R["f"], 1000 * np.abs(R["H"]))
        ph = np.interp(FGRID, R["f"], np.degrees(np.unwrap(np.angle(R["H"]))))
        co = np.interp(FGRID, R["f"], np.minimum(R["czu"], R["czy"]))
        pr("    %-7s %-6s" % (L.BANDNAME[k], "|H|") + "".join("%9.4f" % x for x in mag))
        pr("    %-7s %-6s" % ("", "phase") + "".join("%9.1f" % x for x in ph))
        pr("    %-7s %-6s" % ("", "coh") + "".join("%9.2f" % x for x in co))
        RES.setdefault("TF", {}).setdefault(ykey, {})[L.BANDNAME[k]] = dict(
            f=FGRID, mag=list(mag), phase=list(ph), coh=list(co))

pr("\n    MAGNITUDE SLOPE of |H| over 0.2-1.5 Hz (log-log), per band -- the discriminator:")
pr("      0 = pure gain    -1 = integrator    +1 = differentiator")
pr("    %-7s %14s %14s" % ("band", "d log|H_rate|", "d log|H_ang|"))
for k in range(len(L.BANDS)):
    S = byband[k]
    if not S:
        continue
    row = []
    for ykey in ("y_rate", "y_ang"):
        R = pooled_tf(S, "u_tap", ykey)
        sel = (R["f"] >= 0.2) & (R["f"] <= 1.5) & (np.minimum(R["czu"], R["czy"]) > 0.3)
        if sel.sum() < 4:
            row.append(np.nan); continue
        A = np.vstack([np.log10(R["f"][sel]), np.ones(sel.sum())]).T
        sl_, _ = np.linalg.lstsq(A, np.log10(np.abs(R["H"][sel])), rcond=None)[0]
        row.append(sl_)
    pr("    %-7s %14.3f %14.3f" % (L.BANDNAME[k], row[0], row[1]))
    RES.setdefault("slope", {})[L.BANDNAME[k]] = row

# ======================================================================================================
# B4.  M1 and M2 fitted to the measured transfer function
# ======================================================================================================
pr("\n" + "=" * 104)
pr("B4. M1 (first order + dead time) and M2 (J th'' + c th' + k th = G u) FITTED TO H_ang(f)")
pr("    Fit is complex least squares on the IV transfer estimate, coherence-weighted, 0.15-2.0 Hz.")
pr("    M1:  H = K e^{-s d} / (1 + s T)            M2:  H = G / (J s^2 + c s + k)  (per unit tap count)")
pr("    M2 is reported NORMALISED to J = 1, so c and k are per unit inertia and the reported")
pr("    time constant is c/k (the torque->ANGLE lag) and the natural frequency is sqrt(k)/2pi.")
pr("=" * 104)


def fit_models(S, nper=None):
    R = pooled_tf(S, "u_tap", "y_ang", nper)
    if R is None:
        return None
    f, H = R["f"], R["H"]
    w = np.minimum(R["czu"], R["czy"])
    sel = (f >= 0.15) & (f <= 2.0) & np.isfinite(H) & (w > 0.2)
    if sel.sum() < 5:
        return None
    f, H, w = f[sel], H[sel], w[sel]
    s = 2j * np.pi * f

    def m1_resid(p):
        K, T, d = p[0], abs(p[1]), abs(p[2])
        Hm = K * np.exp(-s * d) / (1 + s * T)
        r = (Hm - H) * np.sqrt(w)
        return np.concatenate([r.real, r.imag])

    def m2_resid(p):
        G, c, k, d = p[0], abs(p[1]), abs(p[2]), abs(p[3])
        Hm = G * np.exp(-s * d) / (s ** 2 + c * s + k)
        r = (Hm - H) * np.sqrt(w)
        return np.concatenate([r.real, r.imag])

    K0 = float(np.abs(H[0]))
    best1 = None
    for T0 in (0.05, 0.2, 0.5, 1.0, 2.0):
        for d0 in (0.02, 0.08, 0.15):
            try:
                r = optimize.least_squares(m1_resid, [K0 * (1 + (2 * np.pi * f[0] * T0) ** 2) ** .5,
                                                      T0, d0], max_nfev=4000)
                if best1 is None or r.cost < best1.cost:
                    best1 = r
            except Exception:
                pass
    best2 = None
    for k0 in (1.0, 10.0, 50.0, 200.0):
        for c0 in (1.0, 5.0, 20.0):
            for d0 in (0.01, 0.06, 0.12):
                try:
                    r = optimize.least_squares(m2_resid, [K0 * k0, c0, k0, d0], max_nfev=6000)
                    if best2 is None or r.cost < best2.cost:
                        best2 = r
                except Exception:
                    pass

    def vaf(p, fn):
        r = fn(p)
        rr = r[:len(f)] + 1j * r[len(f):]
        return 1.0 - float(np.sum(np.abs(rr) ** 2)) / float(np.sum(np.abs(H * np.sqrt(w)) ** 2))

    return dict(f=f, H=H, w=w,
                m1=dict(K=best1.x[0], T=abs(best1.x[1]), d=abs(best1.x[2]), vaf=vaf(best1.x, m1_resid)),
                m2=dict(G=best2.x[0], c=abs(best2.x[1]), k=abs(best2.x[2]), d=abs(best2.x[3]),
                        vaf=vaf(best2.x, m2_resid)))


pr("\n    %-7s | %9s %8s %8s %6s | %10s %8s %9s %7s %8s %8s %6s"
   % ("band", "M1 K", "M1 T s", "M1 d s", "VAF", "M2 G", "M2 c", "M2 k", "M2 d s", "c/k s",
      "fn Hz", "VAF"))
m2tab = {}
for k in range(len(L.BANDS)):
    S = byband[k]
    if not S:
        continue
    F = fit_models(S)
    if F is None:
        continue
    a1, a2 = F["m1"], F["m2"]
    pr("    %-7s | %9.2e %8.3f %8.3f %6.3f | %10.2e %8.3f %9.3f %7.3f %8.3f %8.3f %6.3f"
       % (L.BANDNAME[k], a1["K"], a1["T"], a1["d"], a1["vaf"],
          a2["G"], a2["c"], a2["k"], a2["d"], a2["c"] / max(a2["k"], 1e-9),
          np.sqrt(max(a2["k"], 0)) / (2 * np.pi), a2["vaf"]))
    m2tab[L.BANDNAME[k]] = dict(m1=a1, m2=a2, vmed=float(np.median(
        np.concatenate([g["v"][a:b] for a, b in S]))))
RES["M1M2"] = m2tab

pr("\n    IS k PROPORTIONAL TO v^2 ?  (tyre self-aligning stiffness)  [the decision the tau study left open]")
pr("    %-7s %8s %10s %12s %12s" % ("band", "v med", "k", "k/v^2", "c/k = T_lag s"))
ks, vs = [], []
for nm, d in m2tab.items():
    vmed = d["vmed"]
    pr("    %-7s %8.2f %10.3f %12.5f %12.4f"
       % (nm, vmed, d["m2"]["k"], d["m2"]["k"] / max(vmed ** 2, 1e-9), d["m2"]["c"] / max(d["m2"]["k"], 1e-9)))
    ks.append(d["m2"]["k"]); vs.append(vmed)
if len(ks) >= 3:
    lv, lk = np.log(np.array(vs)), np.log(np.array(ks))
    A = np.vstack([lv, np.ones(len(lv))]).T
    p_, q_ = np.linalg.lstsq(A, lk, rcond=None)[0]
    pr("    => power law  k ~ v^%.2f   (v^2 is the tyre self-aligning prediction; v^0 = speed-independent)"
       % p_)
    RES["k_power"] = float(p_)

# ======================================================================================================
# B5.  deadband / friction / hysteresis
# ======================================================================================================
pr("\n" + "=" * 104)
pr("B5. DEADBAND, FRICTION AND HYSTERESIS -- is there a torque below which nothing moves?")
pr("=" * 104)
mm = L.clean_mask(g, hands_off=True, min_v=1.0)
u = S_TAP * g["T"]
r = S_RATE * g["rate_dps"]
pr("\n    |427 tap| bin -> what the wheel does (engaged, hands-off; the tap's own quantiser is 8 counts)")
pr("    %-14s %8s %10s %10s %10s %10s" % ("|u| counts", "n", "|rate| p50", "|rate| p90",
                                          "P(|rate|<0.5)", "|cmd| p50"))
edges = [0, 8, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 1024, 4096]
for i in range(len(edges) - 1):
    s = mm & (np.abs(u) >= edges[i]) & (np.abs(u) < edges[i + 1])
    if s.sum() < 100:
        continue
    pr("    %-14s %8d %10.3f %10.3f %10.3f %10.0f"
       % ("%d-%d" % (edges[i], edges[i + 1]), s.sum(), np.percentile(np.abs(r[s]), 50),
          np.percentile(np.abs(r[s]), 90), np.mean(np.abs(r[s]) < 0.5),
          np.percentile(np.abs(g["cmd"][s]), 50)))
pr("\n    NOTE: this is not a clean breakaway test -- the wheel is usually already moving.  The")
pr("    controlled version is the STANDSTILL-of-the-wheel test below: frames where |rate| was < 0.5")
pr("    deg/s for the previous 0.3 s, asking what |u| it took to start moving within 0.2 s.")
still = np.convolve((np.abs(r) < 0.5).astype(float), np.ones(30) / 30.0, mode="same") > 0.99
moved = np.convolve((np.abs(r) >= 1.0).astype(float), np.ones(20), mode="full")[19:19 + len(r)] > 0
cand = mm & still
pr("    %-14s %8s %14s" % ("|u| counts", "n frames", "P(moves in 0.2 s)"))
for i in range(len(edges) - 1):
    s = cand & (np.abs(u) >= edges[i]) & (np.abs(u) < edges[i + 1])
    if s.sum() < 60:
        continue
    pr("    %-14s %8d %14.3f" % ("%d-%d" % (edges[i], edges[i + 1]), s.sum(), np.mean(moved[s])))
pr("\n    in 0xE4 command counts, the same thresholds are |cmd| = |u| / %.4f  (the V293 map's slope)"
   % (10.3355 / 16.1876))

# hysteresis: the angle-torque loop area at quasi-steady state
pr("\n    HYSTERESIS -- slow (<0.3 Hz) angle vs torque, split by the sign of the wheel rate.")
pr("    A pure spring gives the same angle/torque ratio either way; Coulomb friction offsets them.")
lowf = mm & (np.abs(r) > 0.5)
for k in range(len(L.BANDS)):
    s = lowf & (g["v"] >= L.BANDS[k][0]) & (g["v"] < L.BANDS[k][1])
    if s.sum() < 2000:
        continue
    up = s & (r > 0.5); dn = s & (r < -0.5)
    if up.sum() < 500 or dn.sum() < 500:
        continue
    su, iu, _, _ = slope(S_ANG * g["ang"][up], u[up])
    sd, id_, _, _ = slope(S_ANG * g["ang"][dn], u[dn])
    pr("    %-7s  torque-vs-angle slope  rate>0 %+8.2f (offset %+8.1f)   rate<0 %+8.2f (offset %+8.1f)"
       "   half-width %.0f counts" % (L.BANDNAME[k], su, iu, sd, id_, abs(iu - id_) / 2.0))

with open(os.path.join(L.SCRATCH, "v293_ident_b.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_b.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_b.txt / .json")
