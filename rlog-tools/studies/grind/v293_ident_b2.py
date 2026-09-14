# -*- coding: utf-8 -*-
"""v293_ident_b2.py -- PART B (final): THE PLANT of the 2020 Accord with V293's open-loop torque map,
identified per speed band.  Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

Supersedes v293_ident_b.py, which had three defects found by its own output and fixed here:
  (1) the M2 parametrisation (J normalised to 1) left G and k trading off, so the reported k -- and
      the k ~ v^p power law drawn from it -- were not identified.  M2 is now fitted with the NUMERATOR
      FIXED AT 1, so k is literally "delivered torque counts per degree of steady steering angle" and
      the DC gain is 1/k.  M1 is then exactly M2's low-frequency limit, and the two are comparable.
  (2) stretches were split at band boundaries, which destroyed every stretch below 8 m/s.  A stretch
      is now assigned to the band holding >= 70 % of its samples, and kept whole.
  (3) the sign frame.  RESOLVED FROM THE FORK'S OWN CODE AND CONFIRMED ON THE WIRE:
      latcontrol_torque.update() ends `return -output_torque, 0.0, pid_log`, and controlsd assigns
      `actuators.torque = steer`.  So  actuators.torque = -output_torque, and openpilot's LAF is
      defined by  actualLateralAccel = LAF * output_torque = LAF * (-actuators.torque).
      The carcontroller then sends `interp(-torque*STEER_MAX)` = +output_torque*4096, which is why the
      427 tap is in phase with +output_torque and with +actualLateralAccel.  Measured: the wire gives
      cmd = -3988.5 * actuators.torque (R2 0.978), and at 0.03-0.3 Hz tap vs actualLateralAccel = +0.89.

🛑 u IS NOT EXOGENOUS.  Every gain is an INSTRUMENTAL-VARIABLE / joint input-output estimate with
z = controlsState.desiredCurvature * v^2 (camera + road) as the instrument:  H = S_zy / S_zu.  The
direct estimate is printed beside it so the feedback bias is visible rather than assumed.
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
SR_L = None

pr("=" * 108)
pr("V293 PLANT IDENTIFICATION -- PART B: THE PLANT, PER SPEED BAND   (route 70, 2026-09-13)")
pr("=" * 108)

# ======================================================================================================
# B0.  the frame, fixed from the code and confirmed on the wire
# ======================================================================================================
e = g["eng"] & np.isfinite(g["la_act"]) & np.isfinite(g["T"]) & np.isfinite(g["op_torque"])


def slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    A = np.vstack([x, np.ones(len(x))]).T
    s, i = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(s), float(i), L.r2(y, A @ [s, i]), float(np.corrcoef(x, y)[0, 1])


pr("\nB0. THE FRAME  [EVIDENCE -- fork source + wire]")
pr("    latcontrol_torque.update() returns  -output_torque  and controlsd assigns it to")
pr("    actuators.torque, so    u = output_torque = -actuators.torque    is the torque in the same")
pr("    frame as torqueState.actualLateralAccel, and LAF is defined by  la = LAF * u.")
s_, i_, r_, c_ = slope(g["op_torque"][e], g["cmd"][e])
pr("    wire check: 0xE4 cmd = %+.1f * actuators.torque %+.1f  (R2 %.4f)  => +output_torque -> +cmd"
   % (s_, i_, r_))
s_, i_, r_, c_ = slope(g["ang"][e], g["la_act"][e])
pr("    0x14A angle -> actualLateralAccel  slope %+.5f  => y_ang = -1 * 0x14A angle" % s_)
s_, i_, r_, c_ = slope(np.gradient(g["ang"], DT)[e], g["rate_dps"][e])
pr("    d(0x14A angle)/dt -> 0x18F rate/8  slope %+.4f corr %+.4f  => y_rate = +1 * (0x18F rate / 8)"
   % (s_, c_))
S_OP, S_TAP, S_ANG, S_RATE = -1.0, +1.0, -1.0, +1.0

pr("\n    CHANNELS (all in the actualLateralAccel frame):")
pr("      u_op  = -actuators.torque          [-1,1]     the unit LAF is defined in")
pr("      u_tap = +427 tap                   counts     the DELIVERED EPS lane torque, 50 Hz")
pr("      y_ang = -0x14A angle               deg        y_rate = +0x18F rate/8   deg/s")
pr("      y_la  = actualLateralAccel         m/s^2      y_yaw  = raw gyro yaw * v   m/s^2")
pr("      z     = desiredCurvature * v^2     m/s^2      THE INSTRUMENT")

# the tap's own scale against the command, measured -- the V293 map, on the wire
tb = e & (np.abs(g["cmd"]) > 50) & (np.abs(g["cmd"]) < 2500) & (g["press"] < 0.5)
s_tapcmd, _, r_tapcmd, _ = slope(np.abs(g["cmd"][tb]), np.abs(g["T"][tb]))
pr("\n    the V293 map ON THE WIRE (hands-off, 50 < |cmd| < 2500):  |tap| = %.4f * |cmd|   R2 %.3f"
   % (s_tapcmd, r_tapcmd))
pr("    the BUILT IMAGE says 10.3355/16.1876 = %.4f at full taper.  1.0 of openpilot torque = 4096"
   % (10.3355 / 16.1876))
pr("    counts of 0xE4 = %.0f counts of delivered torque (image) / %.0f (wire).  V282 delivered ~2x"
   % (4096 * 10.3355 / 16.1876, 4096 * s_tapcmd))

# ======================================================================================================
# B1.  stretches
# ======================================================================================================
MINSEC, PURITY = 8.0, 0.70
m = L.clean_mask(g, hands_off=True, min_v=1.0)
st = L.stretches(m, int(MINSEC * L.FS))
byband = {k: [] for k in range(len(L.BANDS))}
for (a, b) in st:
    bidx = np.array([L.band_of(x) for x in g["v"][a:b]])
    cnt = np.bincount(bidx, minlength=len(L.BANDS))
    k = int(np.argmax(cnt))
    if cnt[k] / float(len(bidx)) >= PURITY:
        byband[k].append((a, b))
pr("\nB1. CLEAN STRETCHES (laterally engaged, hands-off, unsaturated, 2 s recovery buffer, >= %.0f s,"
   % MINSEC)
pr("    assigned to the band holding >= %.0f%% of their samples)" % (100 * PURITY))
pr("    %-8s %6s %9s %9s %9s %12s" % ("band", "n", "seconds", "v med", "|ang| p50", "|ang| p95"))
for k in range(len(L.BANDS)):
    S = byband[k]
    if not S:
        pr("    %-8s %6d %9.1f" % (L.BANDNAME[k], 0, 0.0)); continue
    idx = np.concatenate([np.arange(a, b) for a, b in S])
    pr("    %-8s %6d %9.1f %9.2f %9.2f %12.2f"
       % (L.BANDNAME[k], len(S), len(idx) * DT, np.median(g["v"][idx]),
          np.percentile(np.abs(g["ang"][idx]), 50), np.percentile(np.abs(g["ang"][idx]), 95)))
RES["stretches"] = {L.BANDNAME[k]: dict(n=len(byband[k]),
                                        sec=sum(b - a for a, b in byband[k]) * DT)
                    for k in range(len(L.BANDS))}


def chan(a, b):
    v = g["v"][a:b]
    return dict(u_op=S_OP * g["op_torque"][a:b], u_tap=S_TAP * g["T"][a:b],
                y_ang=S_ANG * g["ang"][a:b], y_rate=S_RATE * g["rate_dps"][a:b],
                y_la=g["la_act"][a:b], y_yaw=g["gyro_yaw"][a:b] * v,
                z=g["des_curv"][a:b] * v ** 2, v=v, la_des=g["la_des"][a:b])


def pooled_tf(S, ukey, ykey, nper=None, minf=None):
    if not S:
        return None
    if nper is None:
        lens = sorted((b - a) for a, b in S)
        nper = 1024
        while nper > 256 and len([x for x in lens if x >= nper]) < max(1, len(lens) // 2):
            nper //= 2
    Szu = Szy = Pzz = Puu = Pyy = None
    f, nseg, wtot = None, 0, 0.0
    for (a, b) in S:
        if (b - a) < nper:
            continue
        c = chan(a, b)
        z, u, y = c["z"], c[ukey], c[ykey]
        if not (np.all(np.isfinite(z)) and np.all(np.isfinite(u)) and np.all(np.isfinite(y))):
            continue
        kw = dict(fs=L.FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        f, a1 = signal.csd(z, u, **kw)
        _, a2 = signal.csd(z, y, **kw)
        _, a3 = signal.welch(z, **kw)
        _, a4 = signal.welch(u, **kw)
        _, a5 = signal.welch(y, **kw)
        w = float(b - a)
        Szu = a1 * w if Szu is None else Szu + a1 * w
        Szy = a2 * w if Szy is None else Szy + a2 * w
        Pzz = a3 * w if Pzz is None else Pzz + a3 * w
        Puu = a4 * w if Puu is None else Puu + a4 * w
        Pyy = a5 * w if Pyy is None else Pyy + a5 * w
        nseg += 1; wtot += w
    if Szu is None or nseg == 0:
        return None
    return dict(f=f, H=Szy / Szu, Hd=_direct(S, ukey, ykey, nper),
                czu=np.abs(Szu) ** 2 / np.maximum(Pzz * Puu, 1e-30),
                czy=np.abs(Szy) ** 2 / np.maximum(Pzz * Pyy, 1e-30),
                nper=nper, nseg=nseg, sec=wtot * DT)


def _direct(S, ukey, ykey, nper):
    Puy = Puu = None
    for (a, b) in S:
        if (b - a) < nper:
            continue
        c = chan(a, b)
        kw = dict(fs=L.FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, p1 = signal.csd(c[ukey], c[ykey], **kw)
        _, p2 = signal.welch(c[ukey], **kw)
        w = float(b - a)
        Puy = p1 * w if Puy is None else Puy + p1 * w
        Puu = p2 * w if Puu is None else Puu + p2 * w
    return Puy / Puu if Puy is not None else None


def cont_phase(f, H, coh, f0=0.2):
    """principal-value phase, made continuous starting from the most coherent low bin."""
    ph = np.degrees(np.angle(H))
    k0 = int(np.argmin(np.abs(f - f0)))
    out = ph.copy()
    for k in range(k0 + 1, len(ph)):
        while out[k] - out[k - 1] > 180:
            out[k] -= 360
        while out[k] - out[k - 1] < -180:
            out[k] += 360
    for k in range(k0 - 1, -1, -1):
        while out[k] - out[k + 1] > 180:
            out[k] -= 360
        while out[k] - out[k + 1] < -180:
            out[k] += 360
    return out


# ======================================================================================================
# B2.  THE HEADLINE -- is the plant a spring or an integrator, and what is the true LAF?
# ======================================================================================================
pr("\n" + "=" * 108)
pr("B2. SPRING OR INTEGRATOR?  the log-log slope of |H| over the coherent band, IV estimate")
pr("    torque -> ANGLE slope  0 = SPRING (torque sets an angle)   -1 = INTEGRATOR (torque sets a rate)")
pr("    torque -> RATE  slope +1 = SPRING                           0 = INTEGRATOR")
pr("=" * 108)
pr("\n    %-7s %6s %6s | %11s %11s | %11s %11s | %s"
   % ("band", "nper", "nseg", "slope ANG", "slope RATE", "coh 0.2 Hz", "coh 0.5 Hz", "band fitted"))
for k in range(len(L.BANDS)):
    S = byband[k]
    Ra = pooled_tf(S, "u_tap", "y_ang")
    Rr = pooled_tf(S, "u_tap", "y_rate")
    if Ra is None:
        continue
    out = []
    for R in (Ra, Rr):
        coh = np.minimum(R["czu"], R["czy"])
        sel = (R["f"] >= 0.15) & (R["f"] <= 1.2) & (coh > 0.35)
        if sel.sum() < 4:
            out.append(np.nan); continue
        A = np.vstack([np.log10(R["f"][sel]), np.ones(sel.sum())]).T
        sl_, _ = np.linalg.lstsq(A, np.log10(np.abs(R["H"][sel])), rcond=None)[0]
        out.append(sl_)
    coh = np.minimum(Ra["czu"], Ra["czy"])
    fsel = Ra["f"][(Ra["f"] >= 0.15) & (Ra["f"] <= 1.2) & (coh > 0.35)]
    pr("    %-7s %6d %6d | %11.3f %11.3f | %11.2f %11.2f | %.2f-%.2f Hz"
       % (L.BANDNAME[k], Ra["nper"], Ra["nseg"], out[0], out[1],
          np.interp(0.2, Ra["f"], coh), np.interp(0.5, Ra["f"], coh),
          fsel.min() if len(fsel) else np.nan, fsel.max() if len(fsel) else np.nan))
    RES.setdefault("slopes", {})[L.BANDNAME[k]] = dict(ang=out[0], rate=out[1])

pr("\n    the measured |H| and phase, torque(427 counts) -> angle(deg), IV form:")
FG = [0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0]
for k in range(len(L.BANDS)):
    R = pooled_tf(byband[k], "u_tap", "y_ang")
    if R is None:
        continue
    coh = np.minimum(R["czu"], R["czy"])
    ph = cont_phase(R["f"], R["H"], coh)
    pr("    %-7s %-7s" % (L.BANDNAME[k], "|H|x1e3") + "".join("%8.2f" % x for x in
                                                              np.interp(FG, R["f"], 1000 * np.abs(R["H"]))))
    pr("    %-7s %-7s" % ("", "phase") + "".join("%8.1f" % x for x in np.interp(FG, R["f"], ph)))
    pr("    %-7s %-7s" % ("", "coh") + "".join("%8.2f" % x for x in np.interp(FG, R["f"], coh)))
    pr("    %-7s %-7s" % ("", "tau_eq") + "".join("%8.3f" % x for x in
                                                  (-np.interp(FG, R["f"], ph) / (360.0 * np.array(FG)))))
pr("      (tau_eq(f) = -phase/(360 f), the pure delay that reproduces the MEASURED phase at f --")
pr("       the deliverable TAU-ACTUATOR-DELAY sec.4.3 asks for, now on the TORQUE->ANGLE channel)")
pr("      header f (Hz):" + "".join("%8.2f" % x for x in FG))

# ======================================================================================================
# B3.  M0 / M1 / M2 fitted, with held-out validation
# ======================================================================================================
pr("\n" + "=" * 108)
pr("B3. THE MODELS.  Fitted by complex least squares to the IV transfer estimate, coherence-weighted,")
pr("    over the coherent part of 0.15-1.5 Hz.  Held out: fit on the ODD stretches, score VAF on the")
pr("    EVEN ones' transfer estimate, and R2 on the even stretches' TIME SERIES.")
pr("      M0  y = K * u(t-d)                      static gain + dead time (openpilot's own model)")
pr("      M1  y = K e^{-sd} / (1 + sT) * u        first order + dead time")
pr("      M2  y = e^{-sd} / (J s^2 + c s + k) * u NUMERATOR FIXED AT 1, so k is counts per degree")
pr("=" * 108)


def fit_band(S, ukey, ykey, flo=0.15, fhi=1.5, cmin=0.35):
    R = pooled_tf(S, ukey, ykey)
    if R is None:
        return None
    coh = np.minimum(R["czu"], R["czy"])
    sel = (R["f"] >= flo) & (R["f"] <= fhi) & (coh > cmin) & np.isfinite(R["H"])
    if sel.sum() < 4:
        return None
    f, H, w = R["f"][sel], R["H"][sel], coh[sel]
    s = 2j * np.pi * f
    norm = float(np.sum(np.abs(H) ** 2 * w))

    def vaf(Hm):
        return 1.0 - float(np.sum(np.abs(Hm - H) ** 2 * w)) / norm

    def ls(fn, p0, bounds):
        def res(p):
            r = (fn(p) - H) * np.sqrt(w)
            return np.concatenate([r.real, r.imag])
        return optimize.least_squares(res, p0, bounds=bounds, max_nfev=8000)

    K0 = float(np.abs(H[0]))
    m0 = ls(lambda p: p[0] * np.exp(-s * p[1]), [K0, 0.1], ([-10 * abs(K0) - 1, 0], [10 * abs(K0) + 1, 0.6]))
    best1 = None
    for T0 in (0.02, 0.1, 0.3, 0.8):
        for d0 in (0.01, 0.08, 0.18):
            r = ls(lambda p: p[0] * np.exp(-s * p[2]) / (1 + s * p[1]),
                   [K0, T0, d0], ([-10 * abs(K0) - 1, 0, 0], [10 * abs(K0) + 1, 5.0, 0.6]))
            if best1 is None or r.cost < best1.cost:
                best1 = r
    best2 = None
    for k0 in (10.0, 40.0, 150.0):
        for J0 in (1e-4, 1e-2, 0.3):
            for d0 in (0.01, 0.1, 0.2):
                r = ls(lambda p: np.exp(-s * p[3]) / (p[0] * s ** 2 + p[1] * s + p[2]),
                       [J0, max(1e-3, k0 * 0.1), k0, d0],
                       ([0, 0, 1e-6, 0], [100.0, 1e5, 1e6, 0.6]))
                if best2 is None or r.cost < best2.cost:
                    best2 = r
    H0 = m0.x[0] * np.exp(-s * m0.x[1])
    H1 = best1.x[0] * np.exp(-s * best1.x[2]) / (1 + s * best1.x[1])
    H2 = np.exp(-s * best2.x[3]) / (best2.x[0] * s ** 2 + best2.x[1] * s + best2.x[2])
    return dict(f=f, H=H, w=w, sec=R["sec"],
                m0=dict(K=m0.x[0], d=m0.x[1], vaf=vaf(H0)),
                m1=dict(K=best1.x[0], T=abs(best1.x[1]), d=abs(best1.x[2]), vaf=vaf(H1)),
                m2=dict(J=best2.x[0], c=best2.x[1], k=best2.x[2], d=best2.x[3], vaf=vaf(H2)))


def score_on(S, ukey, ykey, par, flo=0.15, fhi=1.5, cmin=0.35):
    """VAF of a fitted model on a HELD-OUT set's transfer estimate."""
    R = pooled_tf(S, ukey, ykey)
    if R is None:
        return np.nan
    coh = np.minimum(R["czu"], R["czy"])
    sel = (R["f"] >= flo) & (R["f"] <= fhi) & (coh > cmin) & np.isfinite(R["H"])
    if sel.sum() < 4:
        return np.nan
    f, H, w = R["f"][sel], R["H"][sel], coh[sel]
    s = 2j * np.pi * f
    Hm = par["K"] * np.exp(-s * par["d"]) / (1 + s * par.get("T", 0.0))
    return 1.0 - float(np.sum(np.abs(Hm - H) ** 2 * w)) / float(np.sum(np.abs(H) ** 2 * w))


def sim_r2(S, ukey, ykey, par):
    """time-domain held-out R2: run the M1 model on each stretch and score."""
    num = den = 0.0
    T, d, K = par.get("T", 0.0), par["d"], par["K"]
    a = np.exp(-DT / T) if T > 1e-6 else 0.0
    nd = int(round(d / DT))
    for (aa, bb) in S:
        c = chan(aa, bb)
        u = c[ukey] - np.mean(c[ukey])
        y = c[ykey] - np.mean(c[ykey])
        if nd > 0:
            u = np.concatenate([np.zeros(nd), u[:-nd]])
        yh = np.zeros_like(u)
        acc = 0.0
        for i in range(len(u)):
            acc = a * acc + (1 - a) * u[i] if T > 1e-6 else u[i]
            yh[i] = K * acc
        num += float(np.sum((y - yh) ** 2)); den += float(np.sum(y ** 2))
    return 1.0 - num / den if den > 0 else np.nan


CHANNELS = [("u_tap", "y_ang", "427 counts -> deg"),
            ("u_op", "y_la", "openpilot torque -> m/s^2  == LAF"),
            ("u_tap", "y_la", "427 counts -> m/s^2"),
            ("u_op", "y_yaw", "openpilot torque -> m/s^2 (GYRO, path channel)")]
for ukey, ykey, lab in CHANNELS:
    pr("\n    CHANNEL  %s" % lab)
    pr("    %-7s %6s | %9s %6s %5s | %9s %7s %6s %5s | %7s %7s | %8s %8s"
       % ("band", "sec", "M0 K", "M0 d", "VAF", "M1 K", "M1 T", "M1 d", "VAF", "M2 VAF", "M2 fn",
          "held VAF", "held R2"))
    for k in range(len(L.BANDS)):
        S = byband[k]
        if len(S) < 2:
            if S:
                F = fit_band(S, ukey, ykey)
                if F:
                    pr("    %-7s %6.0f | %9.4f %6.3f %5.2f | %9.4f %7.3f %6.3f %5.2f | %7.2f %7s | %8s %8s"
                       % (L.BANDNAME[k], F["sec"], F["m0"]["K"], F["m0"]["d"], F["m0"]["vaf"],
                          F["m1"]["K"], F["m1"]["T"], F["m1"]["d"], F["m1"]["vaf"], F["m2"]["vaf"],
                          "-", "n<2", "n<2"))
                    RES.setdefault("fit", {}).setdefault(lab, {})[L.BANDNAME[k]] = dict(
                        K=F["m1"]["K"], T=F["m1"]["T"], d=F["m1"]["d"], vaf=F["m1"]["vaf"],
                        m0=F["m0"], m2=F["m2"], sec=F["sec"], held_vaf=np.nan, held_r2=np.nan)
            continue
        odd, even = S[0::2], S[1::2]
        F = fit_band(S, ukey, ykey)
        Ff = fit_band(odd, ukey, ykey)
        if F is None:
            continue
        hv = score_on(even, ukey, ykey, Ff["m1"]) if Ff else np.nan
        hr = sim_r2(even, ukey, ykey, Ff["m1"]) if Ff else np.nan
        fn = np.sqrt(F["m2"]["k"] / max(F["m2"]["J"], 1e-12)) / (2 * np.pi) if F["m2"]["J"] > 1e-9 else np.inf
        pr("    %-7s %6.0f | %9.4f %6.3f %5.2f | %9.4f %7.3f %6.3f %5.2f | %7.2f %7.2f | %8.2f %8.2f"
           % (L.BANDNAME[k], F["sec"], F["m0"]["K"], F["m0"]["d"], F["m0"]["vaf"],
              F["m1"]["K"], F["m1"]["T"], F["m1"]["d"], F["m1"]["vaf"], F["m2"]["vaf"], fn, hv, hr))
        RES.setdefault("fit", {}).setdefault(lab, {})[L.BANDNAME[k]] = dict(
            K=F["m1"]["K"], T=F["m1"]["T"], d=F["m1"]["d"], vaf=F["m1"]["vaf"],
            m0=F["m0"], m2=F["m2"], sec=F["sec"], held_vaf=hv, held_r2=hr)

# ======================================================================================================
# B4.  the speed laws
# ======================================================================================================
pr("\n" + "=" * 108)
pr("B4. THE SPEED LAWS -- the decision the tau study left open, and openpilot's own premise")
pr("=" * 108)
vmed = {}
for k in range(len(L.BANDS)):
    if byband[k]:
        idx = np.concatenate([np.arange(a, b) for a, b in byband[k]])
        vmed[L.BANDNAME[k]] = float(np.median(g["v"][idx]))


def power_law(xs, ys, lab):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    ok = np.isfinite(xs) & np.isfinite(ys) & (xs > 0) & (ys > 0)
    if ok.sum() < 3:
        pr("      %s: too few points" % lab); return np.nan
    A = np.vstack([np.log(xs[ok]), np.ones(ok.sum())]).T
    p, q = np.linalg.lstsq(A, np.log(ys[ok]), rcond=None)[0]
    pr("      %-46s  ~ v^%+.2f   (R2 %.3f, n %d)"
       % (lab, p, L.r2(np.log(ys[ok]), A @ [p, q]), ok.sum()))
    return float(p)


FIT = RES.get("fit", {})
lab_ang = "427 counts -> deg"
lab_laf = "openpilot torque -> m/s^2  == LAF"
lab_tla = "427 counts -> m/s^2"
pr("\n    (a) SELF-ALIGNING STIFFNESS  k = 1 / (DC gain of torque->angle), in 427 counts per degree.")
pr("        the tyre prediction is k ~ v^2 ; speed-independent is v^0.")
pr("    %-8s %8s %12s %12s %12s %12s" % ("band", "v med", "1/K deg^-1", "k cnt/deg", "k/v^2", "T lag s"))
kk, vv = [], []
for k in range(len(L.BANDS)):
    nm = L.BANDNAME[k]
    if nm not in FIT.get(lab_ang, {}):
        continue
    d = FIT[lab_ang][nm]
    kcd = 1.0 / d["K"] if d["K"] != 0 else np.nan
    pr("    %-8s %8.2f %12.5f %12.2f %12.4f %12.3f"
       % (nm, vmed[nm], d["K"], kcd, kcd / vmed[nm] ** 2, d["T"]))
    kk.append(kcd); vv.append(vmed[nm])
RES["k_counts_per_deg"] = dict(zip([L.BANDNAME[i] for i in range(len(L.BANDS))
                                    if L.BANDNAME[i] in FIT.get(lab_ang, {})], kk))
pr("")
RES["k_power"] = power_law(vv, kk, "k (counts per degree)")

pr("\n    (b) openpilot's PREMISE: lat accel per unit torque is speed-INDEPENDENT (that is what")
pr("        'torque correlates to lateral acceleration, not to speed' means, and it is why LAF is")
pr("        a single number).  Measured LAF per band:")
pr("    %-8s %8s %10s %10s %10s %10s %10s"
   % ("band", "v med", "LAF true", "vs 6.0", "lag T s", "dead d s", "held R2"))
lafs, lv = [], []
for k in range(len(L.BANDS)):
    nm = L.BANDNAME[k]
    if nm not in FIT.get(lab_laf, {}):
        continue
    d = FIT[lab_laf][nm]
    pr("    %-8s %8.2f %10.3f %10.3f %10.3f %10.3f %10.2f"
       % (nm, vmed[nm], d["K"], d["K"] / 6.0, d["T"], d["d"], d["held_r2"]))
    lafs.append(d["K"]); lv.append(vmed[nm])
pr("")
RES["laf_power"] = power_law(lv, lafs, "LAF (m/s^2 per unit openpilot torque)")
RES["LAF"] = dict(zip([L.BANDNAME[i] for i in range(len(L.BANDS))
                       if L.BANDNAME[i] in FIT.get(lab_laf, {})], lafs))

pr("\n    (c) IS THE SPEED-DEPENDENT DELAY A LAG POLE OR A DEAD TIME?  [the tau study's open question]")
pr("        M1 splits them on the torque->angle channel, where the input is now KNOWN:")
pr("    %-8s %8s %10s %10s %12s %12s %12s"
   % ("band", "v med", "dead d s", "lag T s", "pole Hz", "tau_eq@0.5Hz", "tau_eq@1Hz"))
for k in range(len(L.BANDS)):
    nm = L.BANDNAME[k]
    if nm not in FIT.get(lab_ang, {}):
        continue
    d = FIT[lab_ang][nm]
    pole = 1.0 / (2 * np.pi * d["T"]) if d["T"] > 1e-6 else np.inf
    te = []
    for ff in (0.5, 1.0):
        phz = -np.degrees(np.arctan(2 * np.pi * ff * d["T"])) - 360.0 * ff * d["d"]
        te.append(-phz / (360.0 * ff))
    pr("    %-8s %8.2f %10.3f %10.3f %12.2f %12.3f %12.3f"
       % (nm, vmed[nm], d["d"], d["T"], pole, te[0], te[1]))

# ======================================================================================================
# B5.  friction, deadband, amplitude dependence
# ======================================================================================================
pr("\n" + "=" * 108)
pr("B5. FRICTION, DEADBAND AND AMPLITUDE DEPENDENCE")
pr("=" * 108)
pr("\n    (a) the STICTION model fitted directly:   u = k*theta + c*theta' + F*sign(theta') + u0")
pr("        on low-passed (<= 0.5 Hz) clean data.  F is the Coulomb friction in DELIVERED 427 counts.")
pr("    %-8s %8s %10s %10s %10s %10s %8s %12s"
   % ("band", "n s", "k cnt/deg", "c cnt/dps", "F counts", "u0 counts", "R2", "F in 0xE4"))
for k in range(len(L.BANDS)):
    S = byband[k]
    if not S:
        continue
    U, TH, TD = [], [], []
    for (a, b) in S:
        c = chan(a, b)
        sos = signal.butter(4, 0.5, btype="lowpass", fs=L.FS, output="sos")
        U.append(signal.sosfiltfilt(sos, c["u_tap"]))
        th = signal.sosfiltfilt(sos, c["y_ang"])
        TH.append(th); TD.append(np.gradient(th, DT))
    U, TH, TD = np.concatenate(U), np.concatenate(TH), np.concatenate(TD)
    sel = np.abs(TD) > 0.3
    if sel.sum() < 500:
        continue
    A = np.vstack([TH[sel], TD[sel], np.sign(TD[sel]), np.ones(sel.sum())]).T
    coef, *_ = np.linalg.lstsq(A, U[sel], rcond=None)
    pr("    %-8s %8.0f %10.2f %10.2f %10.1f %10.1f %8.3f %12.1f"
       % (L.BANDNAME[k], sel.sum() * DT, coef[0], coef[1], coef[2], coef[3],
          L.r2(U[sel], A @ coef), coef[2] / max(s_tapcmd, 1e-9)))
    RES.setdefault("stiction", {})[L.BANDNAME[k]] = dict(k=coef[0], c=coef[1], F=coef[2], u0=coef[3])
pr("      (F in 0xE4 counts uses the measured wire map |tap| = %.4f*|cmd|; divide by 4096 for the" % s_tapcmd)
pr("       fraction of openpilot's full-scale torque, and multiply by LAF for SteerFriction's unit)")

pr("\n    (b) AMPLITUDE DEPENDENCE -- friction shows as GAIN RISING with amplitude (tau study sec.4.7).")
pr("        stretches split into terciles by band-passed (0.2-2 Hz) demand rms:")
pr("    %-8s %28s %9s %9s %9s %10s" % ("band", "channel", "LOW |H|", "MID", "HIGH", "HIGH/LOW"))
for k in range(len(L.BANDS)):
    S = byband[k]
    if len(S) < 3:
        continue
    rms = [np.std(L.bandpass(chan(a, b)["z"], 0.2, 2.0)) for a, b in S]
    order = np.argsort(rms)
    n3 = max(1, len(S) // 3)
    groups = [[S[i] for i in order[:n3]], [S[i] for i in order[n3:-n3]] if len(S) > 2 * n3 else [],
              [S[i] for i in order[-n3:]]]
    for ukey, ykey, lab in (("u_tap", "y_ang", "427 -> deg"), ("u_op", "y_la", "op torque -> m/s^2")):
        vals = []
        for G in groups:
            if not G:
                vals.append(np.nan); continue
            R = pooled_tf(G, ukey, ykey)
            if R is None:
                vals.append(np.nan); continue
            coh = np.minimum(R["czu"], R["czy"])
            sel = (R["f"] >= 0.2) & (R["f"] <= 0.6) & (coh > 0.3)
            vals.append(float(np.mean(np.abs(R["H"][sel]))) if sel.sum() else np.nan)
        pr("    %-8s %28s %9.4f %9.4f %9.4f %10.3f"
           % (L.BANDNAME[k], lab, vals[0], vals[1], vals[2],
              vals[2] / vals[0] if vals[0] else np.nan))

pr("\n    (c) BREAKAWAY -- frames where the wheel was within +-0.25 deg/s for 0.4 s, asking what")
pr("        |delivered torque| coincided with it starting to move (>= 1 deg/s) in the next 0.3 s.")
r = S_RATE * g["rate_dps"]
u = S_TAP * g["T"]
mm = L.clean_mask(g, hands_off=True, min_v=1.0)
w_still, w_move = 40, 30
still = np.convolve((np.abs(r) <= 0.25).astype(float), np.ones(w_still), "same") >= w_still - 0.5
mv = (np.abs(r) >= 1.0).astype(float)
fut = np.zeros(len(r))
cs = np.concatenate([[0.0], np.cumsum(mv)])
fut[:len(r) - w_move] = cs[w_move:len(r)] - cs[:len(r) - w_move]
moved = fut > 0
cand = mm & still
pr("    %-14s %9s %16s %12s" % ("|u| counts", "n frames", "P(moves in 0.3 s)", "|cmd| p50"))
edges = [0, 8, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 4096]
for i in range(len(edges) - 1):
    s = cand & (np.abs(u) >= edges[i]) & (np.abs(u) < edges[i + 1])
    if s.sum() < 40:
        continue
    pr("    %-14s %9d %16.3f %12.0f" % ("%d-%d" % (edges[i], edges[i + 1]), s.sum(),
                                        float(np.mean(moved[s])), np.percentile(np.abs(g["cmd"][s]), 50)))
pr("    total candidate frames (wheel effectively still, engaged, hands-off): %d = %.1f s"
   % (cand.sum(), cand.sum() * DT))

with open(os.path.join(L.SCRATCH, "v293_ident_b2.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_b2.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_b2.txt / .json")
