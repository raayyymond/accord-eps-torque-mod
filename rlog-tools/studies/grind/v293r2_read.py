# -*- coding: utf-8 -*-
"""v293r2_read.py -- the ORCHESTRATOR'S OWN read of a rev-2 (plant-FF) drive on the V293 torque-mode EPS.
2026-09-14.  ANALYSIS ONLY: reads an ident npz cache (v293r2_extract.py), writes a text report.

    python v293r2_read.py <tag> [--ref r70_v293]

What it answers, in order (each section says EVIDENCE or BELIEF):
  S0  attribution from the wire   Kp = p/err, LAF = -(p+i+f)/out, the config keys from initData
  S1  exposure by speed band, hands-off, pressed episodes
  S2  where the torque comes from  f/LAF = plant FF + friction relay (reconstructed), p/LAF, i/LAF
  S3  the plant re-identified      u = a*th + b*th' + F*sign(th') + u0 per band (joint fit, as v293_ident_j)
  S4  delay / phase                IV transfer op-torque -> angle and -> rate, tau_eq(f) to 3 Hz;
                                   direct cross-correlation lags cmd->rate and cmd->tap
  S5  spectra by band and stratum  angle / rate / cmd / err, peaks 0.3-6 Hz (straight vs curve)
  S6  low-speed hard-curve jerks   rate bursts: what the command did around each one
  S7  high-speed hard-curve oscillation  error zero-crossing rate, ring frequency, amplitude
  S8  the friction relay's own behaviour  sign flips per minute, step size on the wire
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

FS, DT = L.FS, 1.0 / L.FS
IB = [(1.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
IBN = ["1-8", "8-15", "15-22", ">22"]
SB = [(0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 99.0)]
SBN = ["0-5", "5-10", "10-20", ">20"]
OUT = []
pr = L.pr_factory(OUT)


def load_plus(tag):
    g = L.load(tag)
    D = g["raw"]
    t0 = min(D["t18"][0], D["t_cc"][0])
    ta = g["t"] + t0
    g["jerk"] = L.zoh(ta, D["t_cs"], D["cs_jerk"]) if "cs_jerk" in D else np.full(g["n"], np.nan)
    g["roll"] = L.zoh(ta, D["t_lpar"], D["lpar_roll"]) if "lpar_roll" in D else np.full(g["n"], np.nan)
    g["aego"] = L.zoh(ta, D["t_cst"], D["aego"]) if "aego" in D else np.full(g["n"], np.nan)
    return g


def pfloat(params, k, default=np.nan):
    try:
        return float(params.get(k, default))
    except Exception:
        return default


def band_mask(v, lo, hi):
    return (v >= lo) & (v < hi)


def welch(x, nper=1024):
    f, P = signal.welch(x, fs=FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
    return f, P


def peak_in(f, P, lo, hi):
    sel = (f >= lo) & (f <= hi)
    if sel.sum() < 3:
        return np.nan, np.nan, np.nan
    fs_, Ps = f[sel], P[sel]
    k = int(np.argmax(Ps))
    # prominence above a log-log line through the shoulders (lo/1.5..lo and hi..hi*1.5)
    sh = ((f >= lo / 1.6) & (f < lo)) | ((f > hi) & (f <= hi * 1.6))
    if sh.sum() >= 4:
        c = np.polyfit(np.log(f[sh]), np.log(P[sh] + 1e-30), 1)
        base = np.exp(np.polyval(c, np.log(fs_[k])))
        prom_db = 10 * np.log10((Ps[k] + 1e-30) / (base + 1e-30))
    else:
        prom_db = np.nan
    return float(fs_[k]), float(10 * np.log10(Ps[k] + 1e-30)), float(prom_db)


def main(tag, ref):
    g = load_plus(tag)
    P = g["meta"].get("params", {}) or {}
    v, ang, rate = g["v"], g["ang"], g["rate_dps"]
    u = -g["op_torque"]            # output_torque frame (the plant FF's frame): cmd ~ +4096*u
    th = -ang                      # same frame
    eng = g["eng"] & np.isfinite(v) & np.isfinite(u)
    hoff = eng & (g["press"] < 0.5)
    w = int(0.5 * FS)
    press_buf = np.convolve((g["press"] > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0
    hoff_b = eng & ~press_buf
    n_eng = int(eng.sum())

    pr("=" * 110)
    pr("V293 REV-2 DRIVE READ  tag %s   route %s   segments %s" % (tag, g["meta"]["route"], g["meta"]["segments"]))
    pr("=" * 110)

    # ------------------------------------------------------------------ S0
    pr("\nS0. ATTRIBUTION FROM THE WIRE [EVIDENCE]")
    for k in ("GitCommit", "GitBranch", "AccordRatePlantFF", "AccordEpsSpringScale", "AccordEpsGainScale",
              "AccordFFRateGain", "SteerFriction", "SteerLatAccel", "SteerKP", "AccordTorqueKi",
              "KeepLearnedLatAccelOffset", "SteerDelay", "UseAutoSteerDelay", "ForceAutoTuneOff",
              "ForceAutoTune", "AdvancedLateralTune", "AccordTurnFFTaper", "SteerRatio",
              "AccordVariableSteerRatio", "AccordCurvatureLead"):
        pr("    %-28s %s" % (k, str(P.get(k, "ABSENT"))[:60]))
    act = eng & (g["cs_active"] > 0.5) & np.isfinite(g["p"]) & np.isfinite(g["err"])
    q = act & (np.abs(g["err"]) > 1e-3)
    kp = g["p"][q] / g["err"][q]
    q2 = act & (np.abs(g["out"]) > 1e-3)
    laf = -(g["p"][q2] + g["i"][q2] + g["f"][q2]) / g["out"][q2]
    KP = float(np.median(kp)); LAF = float(np.median(laf))
    pr("    Kp  = median p/err        = %.4f  (IQR %.4f..%.4f, n %d)" % (KP, *np.percentile(kp, [25, 75]), len(kp)))
    pr("    LAF = median -(p+i+f)/out = %.4f  (IQR %.4f..%.4f, n %d)" % (LAF, *np.percentile(laf, [25, 75]), len(laf)))
    FR = pfloat(P, "SteerFriction", 0.011)
    KI = pfloat(P, "AccordTorqueKi", 0.30)
    RG = pfloat(P, "AccordFFRateGain", 0.5)
    pr("    friction toggle %.4f   Ki toggle %.3f   rate gain %.2f   (used below to reconstruct the relay)" % (FR, KI, RG))
    # wire-rate sign check against d(angle)/dt
    ok = np.isfinite(rate) & np.isfinite(ang)
    dang = np.gradient(ang, DT)
    c = np.corrcoef(rate[ok], dang[ok])[0, 1]
    pr("    0x18F rate vs d(0x14A angle)/dt: corr %+.3f  (rate_dps sign convention: %s the kit angle's)"
       % (c, "SAME as" if c > 0 else "OPPOSITE to"))
    rate_s = rate if c > 0 else -rate     # in the kit's +left angle frame
    rate_u = -rate_s                      # in th's frame

    # ------------------------------------------------------------------ S1
    pr("\nS1. EXPOSURE [EVIDENCE]")
    pr("    wall %.0f s   laterally engaged %.0f s (%.1f %%)   hands-off %.0f s   hands-off (0.5 s buffer) %.0f s"
       % (g["n"] * DT, n_eng * DT, 100.0 * n_eng / g["n"], hoff.sum() * DT, hoff_b.sum() * DT))
    pe = np.diff(np.r_[0, (eng & (g["press"] > 0.5)).astype(int)]) == 1
    pr("    steeringPressed while engaged: %.1f s in %d episodes" % ((eng & (g["press"] > 0.5)).sum() * DT, pe.sum()))
    vv = v[eng]
    pr("    engaged speed p05/p50/p95/max: %.1f / %.1f / %.1f / %.1f m/s" % (*np.percentile(vv, [5, 50, 95]), vv.max()))
    for bands, names in ((IB, IBN), (SB, SBN)):
        pr("    " + "  ".join("%s: %.0f s" % (nm, (eng & band_mask(v, lo, hi)).sum() * DT) for (lo, hi), nm in zip(bands, names)))
    big = eng & (np.abs(ang) >= 30)
    pr("    |angle| >= 30 deg engaged: %.1f s   (hands-off %.1f s)" % (big.sum() * DT, (big & hoff).sum() * DT))
    sat = eng & (np.abs(g["op_torque"]) >= 0.95)
    for (lo, hi), nm in zip(SB, SBN):
        m = eng & band_mask(v, lo, hi)
        if m.sum() > 100:
            pr("    |torque| >= 0.95 duty at %s: %.2f %%   |cmd step| p99 %.0f counts" %
               (nm, 100.0 * (sat & m).sum() / m.sum(), np.percentile(np.abs(np.diff(g["cmd"]))[m[1:]], 99)))

    # ------------------------------------------------------------------ S2
    pr("\nS2. WHERE THE TORQUE COMES FROM (output frame, torque units) [EVIDENCE; the relay reconstruction is BELIEF-grade]")
    f_t, p_t, i_t = g["f"] / LAF, g["p"] / LAF, g["i"] / LAF
    # friction relay reconstruction: friction * clip((err + 0.22*fj)/0.30, +-1); fj = jerk past the centre-chatter deadzone
    jerk = g["jerk"]
    dz = np.interp(np.maximum(v, 0), [0, 5, 12, 25], [0.08, 0.12, 0.18, 0.18]) * np.interp(np.abs(g["la_des"]), [0, 0.18, 0.35], [1, 1, 0])
    fj = np.sign(jerk) * np.maximum(np.abs(jerk) - dz, 0.0)
    relay = FR * np.clip((g["err"] + 0.22 * np.nan_to_num(fj)) / 0.30, -1, 1)
    plant_ff = f_t - relay                # what is left of f is the spring+move feedforward (sign: pid frame)
    pr("    %-6s %6s | %7s %7s %7s | %7s %7s %7s %7s | %8s %8s" %
       ("band", "s", "f shr", "p shr", "i shr", "med|f|", "med|p|", "med|i|", "med|rl|", "|i|>.2 %", "|i|>.4 %"))
    for (lo, hi), nm in zip(IB, IBN):
        m = eng & band_mask(v, lo, hi) & np.isfinite(f_t)
        if m.sum() < 200:
            continue
        af, ap, ai = np.abs(f_t[m]), np.abs(p_t[m]), np.abs(i_t[m])
        tot = af + ap + ai + 1e-9
        pr("    %-6s %6.0f | %7.3f %7.3f %7.3f | %7.3f %7.3f %7.3f %7.3f | %8.1f %8.1f" %
           (nm, m.sum() * DT, np.mean(af / tot), np.mean(ap / tot), np.mean(ai / tot),
            np.median(af), np.median(ap), np.median(ai), np.median(np.abs(relay[m])),
            100 * np.mean(ai > 0.2), 100 * np.mean(ai > 0.4)))
    # the integrator as a slow bias: its sign persistence
    m = eng & np.isfinite(i_t)
    sgn_flips = np.sum(np.diff(np.sign(i_t[m])) != 0)
    pr("    integrator sign changes: %.2f per minute; |i| p50/p90 %.3f/%.3f" %
       (sgn_flips / (m.sum() * DT / 60), *np.percentile(np.abs(i_t[m]), [50, 90])))
    # relay duty: how often the relay is saturated (|arg| >= 1) and its flip rate
    arg = (g["err"] + 0.22 * np.nan_to_num(fj)) / 0.30
    for (lo, hi), nm in zip(SB, SBN):
        m = eng & band_mask(v, lo, hi) & np.isfinite(arg)
        if m.sum() < 200:
            continue
        a = arg[m]
        flips = np.sum(np.diff(np.sign(a)) != 0) / (m.sum() * DT / 60)
        pr("    relay at %-5s: |arg|>=1 (saturated) %5.1f %%, |arg|<0.25 %5.1f %%, sign flips %.1f /min, relay step p90 %.4f torque = %.0f cmd counts"
           % (nm, 100 * np.mean(np.abs(a) >= 1), 100 * np.mean(np.abs(a) < 0.25), flips,
              np.percentile(np.abs(np.diff(relay[m])), 90), 4096 * np.percentile(np.abs(np.diff(relay[m])), 90)))

    # ------------------------------------------------------------------ S3
    pr("\nS3. THE PLANT, RE-IDENTIFIED (joint fit u = a*th + b*th' + F*sign(th') + u0; hands-off, 0.5 s buffer, 0.5 Hz LPF) [EVIDENCE]")
    mask = L.clean_mask(g, hands_off=True, min_v=1.0, buffer_s=0.5)
    strets = L.stretches(mask, int(4 * FS))
    pr("    %d clean stretches >= 4 s, %.0f s" % (len(strets), sum(b - a for a, b in strets) * DT))
    CELL = {}
    for lpf_hz in (0.5, 1.5):
        sos = signal.butter(4, lpf_hz, "lowpass", fs=FS, output="sos")
        pr("    --- LPF %.1f Hz ---" % lpf_hz)
        pr("    %-6s %5s %5s | %9s %9s %9s %9s | %7s %8s %8s" % ("band", "v", "n", "a t/deg", "b t/dps", "F", "u0", "R2", "G=1/b", "k=a/b"))
        for (lo, hi), nm in zip(IB, IBN):
            TH, TD, U, VV = [], [], [], []
            for (a0, b0) in strets:
                idx = np.arange(a0, b0)
                sel = band_mask(v[idx], lo, hi)
                if sel.sum() < 200:
                    continue
                uu = signal.sosfiltfilt(sos, u[a0:b0]); tt = signal.sosfiltfilt(sos, th[a0:b0])
                td = np.gradient(tt, DT)
                q = sel & (np.abs(td) > 0.3)
                if q.sum() < 100:
                    continue
                TH.append(tt[q]); TD.append(td[q]); U.append(uu[q]); VV.append(np.median(v[idx][sel]))
            if len(TH) < 3:
                pr("    %-6s only %d stretches" % (nm, len(TH))); continue
            TH_ = np.concatenate(TH); TD_ = np.concatenate(TD); U_ = np.concatenate(U)
            A = np.vstack([TH_, TD_, np.sign(TD_), np.ones(len(TH_))]).T
            cf, *_ = np.linalg.lstsq(A, U_, rcond=None)
            r2 = L.r2(U_, A @ cf)
            pr("    %-6s %5.1f %5d | %9.5f %9.5f %9.5f %9.4f | %7.3f %8.1f %8.2f" %
               (nm, np.median(VV), len(TH), cf[0], cf[1], cf[2], cf[3], r2, 1 / cf[1] if cf[1] else np.nan, cf[0] / cf[1] if cf[1] else np.nan))
            if lpf_hz == 0.5:
                CELL[nm] = dict(v=float(np.median(VV)), a=float(cf[0]), b=float(cf[1]), F=float(cf[2]), r2=float(r2))
    # fork tables as flown (66cf4454a) -- hold k/G and move 1/G at the band medians
    G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [550.0, 271.0, 246.0, 167.0]
    K_BP, K_V = [4.0, 8.0, 12.5, 18.5, 28.5], [0.30, 1.00, 2.30, 2.77, 3.91]
    pr("    fork tables (66cf4454a) at the band medians vs the fit:  hold = K/G, move = 1/G")
    for nm, c in CELL.items():
        Gf = np.interp(c["v"], G_BP, G_V); Kf = np.interp(c["v"], K_BP, K_V)
        pr("    %-6s v %5.1f  fork hold %.5f vs a %.5f (ratio %.2f)   fork 1/G %.5f vs b %.5f (ratio %.2f)   F %.4f vs toggle %.4f"
           % (nm, c["v"], Kf / Gf, c["a"], (Kf / Gf) / c["a"] if c["a"] else np.nan, 1 / Gf, c["b"], (1 / Gf) / c["b"] if c["b"] else np.nan, c["F"], FR))
    # hold bound at low speed from the largest hands-off angles
    m = hoff_b & (v < 5) & (np.abs(ang) > 100)
    if m.sum() > 50:
        pr("    low-speed hold bound: hands-off v<5, |angle|>100: n %d, |u| p50 %.3f p95 %.3f, OLS |u| on |angle| slope %.5f"
           % (m.sum(), *np.percentile(np.abs(u[m]), [50, 95]), np.polyfit(np.abs(ang[m]), np.abs(u[m]), 1)[0]))

    # ------------------------------------------------------------------ S4
    pr("\nS4. DELAY / PHASE  (IV transfer, instrument z = desiredCurvature*v^2; clean hands-off stretches >= 10 s) [EVIDENCE for tau_eq; the split is BELIEF]")
    mask10 = L.clean_mask(g, hands_off=True, min_v=1.0, buffer_s=0.5)
    st10 = L.stretches(mask10, int(10 * FS))
    z_all = g["des_curv"] * v ** 2
    FQ = [0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]
    for (lo, hi), nm in zip(IB, IBN):
        segs = [(a0, b0) for (a0, b0) in st10 if band_mask(np.median(v[a0:b0]), lo, hi)]
        if len(segs) < 2:
            pr("    %-6s only %d stretches >= 10 s" % (nm, len(segs))); continue
        # concatenate stretches (each detrended) -- Welch segments of 512 (5.12 s) inside
        Z = np.concatenate([signal.detrend(z_all[a:b]) for a, b in segs])
        U = np.concatenate([signal.detrend(u[a:b]) for a, b in segs])
        Y = np.concatenate([signal.detrend(th[a:b]) for a, b in segs])
        R = np.concatenate([signal.detrend(rate_u[a:b]) for a, b in segs])
        f, H, czu, czy = L.iv_tf(Z, U, Y, nper=512)
        f, Hr, _, czr = L.iv_tf(Z, U, R, nper=512)
        pr("    %-6s %d stretches, %.0f s" % (nm, len(segs), len(U) * DT))
        pr("      f Hz   |H| t->ang  phase  tau_eq   coh(z,ang) |  |H| t->rate phase  coh  | |H_rate|/(2pi f |H_ang|) [ident. check]")
        for fq in FQ:
            k = int(np.argmin(np.abs(f - fq)))
            ph = np.degrees(np.angle(H[k])); phr = np.degrees(np.angle(Hr[k]))
            tau = -np.deg2rad(ph) / (2 * np.pi * f[k]) if np.isfinite(ph) else np.nan
            pr("      %4.1f   %8.1f %7.1f %7.3f   %5.2f     | %8.1f %7.1f %5.2f | %6.2f" %
               (f[k], np.abs(H[k]), ph, tau, czy[k], np.abs(Hr[k]), phr, czr[k], np.abs(Hr[k]) / (2 * np.pi * f[k] * np.abs(H[k]) + 1e-12)))
        # log-log slope of |H| t->ang over 0.2-1.5 Hz where coh > 0.3
        sel = (f >= 0.2) & (f <= 1.5) & (czy > 0.3)
        if sel.sum() >= 4:
            sl = np.polyfit(np.log(f[sel]), np.log(np.abs(H[sel])), 1)[0]
            pr("      log-log slope |H| torque->angle 0.2-1.5 Hz (coh>0.3): %+.2f   (spring 0, integrator -1)" % sl)
        # direct cross-correlation lags (NOT IV -- biased by feedback, printed for the record)
        lag_r, c_r = L.ncc_lag(L.bandpass(U, 0.3, 4.0), L.bandpass(R, 0.3, 4.0), lo=-0.2, hi=0.6)
        lag_a, c_a = L.ncc_lag(L.bandpass(U, 0.2, 2.0), L.bandpass(Y, 0.2, 2.0), lo=-0.2, hi=0.8)
        pr("      direct xcorr lag u->rate (0.3-4 Hz) %+.3f s (c %.2f);  u->angle (0.2-2 Hz) %+.3f s (c %.2f)" % (lag_r, c_r, lag_a, c_a))
    # cmd -> tap lag at 50 Hz (EPS-internal), all engaged
    tt = g["tap_t"]; tap = g["tap"]
    cmd_on_tap = np.interp(tt, g["t"], g["cmd"])
    e_on_tap = np.interp(tt, g["t"], eng.astype(float)) > 0.5
    if e_on_tap.sum() > 1000:
        x = signal.detrend(cmd_on_tap[e_on_tap]); y = signal.detrend(tap[e_on_tap])
        lag, cc = L.ncc_lag(x, y, fs=50.0, lo=-0.1, hi=0.3)
        pr("    cmd -> 427 tap (50 Hz, all engaged): lag %+.3f s, corr %.3f  [the EPS-internal delay + tap timing]" % (lag, cc))

    # ------------------------------------------------------------------ S5
    pr("\nS5. SPECTRA BY BAND AND STRATUM (Welch 10.24 s, engaged; peaks 0.3-6 Hz with log-log shoulder prominence) [EVIDENCE]")
    strata = [("all", eng), ("straight |Ddes|<0.3", eng & (np.abs(g["la_des"]) < 0.3)),
              ("curve |Ddes|>1.0", eng & (np.abs(g["la_des"]) > 1.0)), ("hands-off curve", hoff & (np.abs(g["la_des"]) > 1.0))]
    for (lo, hi), nm in zip(SB, SBN):
        for sname, sm in strata:
            m = sm & band_mask(v, lo, hi)
            runs = L.stretches(m, int(10.24 * FS))
            if not runs:
                continue
            tot = sum(b - a for a, b in runs)
            if tot < 30 * FS:
                continue
            line = "    %-5s %-22s %5.0f s |" % (nm, sname, tot * DT)
            for cname, x in (("angle", ang), ("rate", rate_s), ("cmd", g["cmd"]), ("err", g["err"])):
                X = np.concatenate([signal.detrend(x[a:b]) for a, b in runs])
                f, Pw = welch(X, 1024)
                for (plo, phi) in ((0.3, 1.0), (1.0, 3.0), (3.0, 6.0)):
                    fpk, db, prom = peak_in(f, Pw, plo, phi)
                    line += " %s %.1f-%.0f: %.2fHz %+.1fdB |" % (cname[:3], plo, phi, fpk, prom)
            pr(line)
    # rate rms in 0.5-3 Hz by band and stratum -- the "oscillation" size
    pr("    band-passed RMS (0.5-3 Hz) of the wheel rate [deg/s], angle [deg] and command [counts]:")
    for (lo, hi), nm in zip(SB, SBN):
        for sname, sm in strata[1:3]:
            m = sm & band_mask(v, lo, hi)
            runs = L.stretches(m, int(5 * FS))
            if not runs or sum(b - a for a, b in runs) < 20 * FS:
                continue
            r_ = np.sqrt(np.mean(np.concatenate([L.bandpass(rate_s[a:b], 0.5, 3.0) ** 2 for a, b in runs])))
            a_ = np.sqrt(np.mean(np.concatenate([L.bandpass(ang[a:b], 0.5, 3.0) ** 2 for a, b in runs])))
            c_ = np.sqrt(np.mean(np.concatenate([L.bandpass(g["cmd"][a:b], 0.5, 3.0) ** 2 for a, b in runs])))
            e_ = np.sqrt(np.mean(np.concatenate([L.bandpass(g["err"][a:b], 0.5, 3.0) ** 2 for a, b in runs])))
            pr("      %-5s %-22s rate %6.2f  angle %5.2f  cmd %6.1f  err %5.3f m/s2" % (nm, sname, r_, a_, c_, e_))

    # ------------------------------------------------------------------ S6
    pr("\nS6. LOW-SPEED HARD-CURVE JERKS: v<10, |angle|>30 or |Ddes|>1, engaged; rate bursts = |rate| above 3x the 1 s local median [EVIDENCE]")
    m = eng & (v < 10) & ((np.abs(ang) > 30) | (np.abs(g["la_des"]) > 1.0))
    if m.sum() > 200:
        ar = np.abs(rate_s)
        loc = signal.medfilt(ar, 101)
        burst = m & (ar > np.maximum(3 * loc, 15.0))
        runs = L.stretches(burst, 3)
        pr("    exposure %.0f s, bursts %d (%.1f /min), burst |rate| p50/p90 %.1f/%.1f deg/s" %
           (m.sum() * DT, len(runs), len(runs) / (m.sum() * DT / 60), *(np.percentile([ar[a:b].max() for a, b in runs], [50, 90]) if runs else (np.nan, np.nan))))
        # for the 8 largest bursts print the 1.2 s trace around onset every 100 ms
        big = sorted(runs, key=lambda r: -ar[r[0]:r[1]].max())[:8]
        for a0, b0 in sorted(big):
            k0 = a0
            pr("    burst at t=%.1f s v %.1f m/s |angle| %.0f: peak rate %.0f deg/s, hands %s" %
               (k0 * DT, v[k0], abs(ang[k0]), ar[a0:b0].max(), "ON" if g["press"][k0] > 0.5 else "off"))
            pr("      t-t0  ang   rate    cmd   dcmd   err    f/L    p/L    i/L   relay  Ddes   Dact")
            for dk in range(-40, 61, 10):
                k = k0 + dk
                if 0 <= k < g["n"]:
                    pr("      %+4.1f %6.1f %6.1f %6.0f %6.0f %6.2f %6.3f %6.3f %6.3f %6.3f %6.2f %6.2f" %
                       (dk * DT, ang[k], rate_s[k], g["cmd"][k], g["cmd"][k] - g["cmd"][max(k - 10, 0)], g["err"][k],
                        f_t[k], p_t[k], i_t[k], relay[k], g["la_des"][k], g["la_act"][k]))
    else:
        pr("    no exposure")

    # ------------------------------------------------------------------ S7
    pr("\nS7. HIGH-SPEED HARD CURVES: v>15, |Ddes|>1.0, engaged runs >= 5 s [EVIDENCE]")
    m = eng & (v > 15) & (np.abs(g["la_des"]) > 1.0)
    runs = L.stretches(m, int(5 * FS))
    if runs:
        tot = sum(b - a for a, b in runs)
        E = np.concatenate([g["err"][a:b] for a, b in runs])
        zc = np.sum(np.diff(np.sign(E)) != 0) / (tot * DT)
        pr("    %d runs, %.0f s; error rms %.3f m/s2, zero-crossings %.2f /s (=> ~%.2f Hz if a cycle)" % (len(runs), tot * DT, np.sqrt(np.mean(E ** 2)), zc, zc / 2))
        for cname, x in (("rate", rate_s), ("cmd", g["cmd"]), ("err", g["err"]), ("angle", ang)):
            X = np.concatenate([signal.detrend(x[a:b]) for a, b in runs])
            f, Pw = welch(X, 512)
            fpk, db, prom = peak_in(f, Pw, 0.3, 3.0)
            pr("      %-6s peak 0.3-3 Hz at %.2f Hz, prominence %+.1f dB; rms 0.5-3 Hz %.3f" % (cname, fpk, prom, np.sqrt(np.mean(L.bandpass(X, 0.5, 3.0) ** 2))))
        # print the worst run's trace at 100 ms
        worst = max(runs, key=lambda r: np.sqrt(np.mean(L.bandpass(rate_s[r[0]:r[1]], 0.5, 3.0) ** 2)))
        a0, b0 = worst
        pr("    worst run t=%.1f..%.1f s (v %.1f): 100 ms trace" % (a0 * DT, b0 * DT, np.median(v[a0:b0])))
        pr("      t     ang   rate    cmd   err    f/L    p/L    i/L   relay  Ddes   Dact")
        for k in range(a0, min(b0, a0 + int(6 * FS)), 10):
            pr("      %5.1f %6.1f %6.1f %6.0f %6.2f %6.3f %6.3f %6.3f %6.3f %6.2f %6.2f" %
               (k * DT, ang[k], rate_s[k], g["cmd"][k], g["err"][k], f_t[k], p_t[k], i_t[k], relay[k], g["la_des"][k], g["la_act"][k]))
    else:
        pr("    no runs")

    # ------------------------------------------------------------------ S8
    pr("\nS8. STRAIGHTS: what holds the wheel  (v>15, |Ddes|<0.3, hands-off) [EVIDENCE]")
    m = hoff & (v > 15) & (np.abs(g["la_des"]) < 0.3)
    if m.sum() > 500:
        pr("    %.0f s; |f/L| p50 %.3f, |p/L| p50 %.3f, |i/L| p50 %.3f, |relay| p50 %.3f; err rms %.3f m/s2; angle rms (0.1-1 Hz) %.2f deg"
           % (m.sum() * DT, np.median(np.abs(f_t[m])), np.median(np.abs(p_t[m])), np.median(np.abs(i_t[m])),
              np.median(np.abs(relay[m])), np.sqrt(np.nanmean(g["err"][m] ** 2)),
              np.sqrt(np.mean(np.concatenate([L.bandpass(ang[a:b], 0.1, 1.0) ** 2 for a, b in L.stretches(m, int(10 * FS))]))) if L.stretches(m, int(10 * FS)) else np.nan))
        # loop stiffness on straights: regress -u (torque) on angle error proxy (err / (v^2 * cf/sR)) -> use err directly: torque per m/s2
        A = np.vstack([g["err"][m], np.ones(m.sum())]).T
        cfit, *_ = np.linalg.lstsq(A, u[m], rcond=None)
        pr("    torque per m/s2 of error on straights (P+I+relay, OLS): %.4f;  Kp_eff/LAF = (%.2f + lsf)/%.1f" % (cfit[0], KP, LAF))


    # ------------------------------------------------------------------ S9  (discrepancy census, operator's request 2026-09-14)
    pr("\nS9. MODEL RESIDUAL REPLAY: the torque the identified plant needed for the MEASURED angle vs what the fork's FF put up [EVIDENCE]")
    pr("    need = a*th + b*th' + F*sign(th') per band (this route's own S3 fit, 0.5 Hz LPF);  ff = f/LAF - relay;  u = the whole command")
    sos = signal.butter(4, 0.5, "lowpass", fs=FS, output="sos")
    for (lo, hi), nm in zip(IB, IBN):
        if nm not in CELL:
            continue
        c = CELL[nm]
        need_all = np.full(g["n"], np.nan)
        for (a0, b0) in L.stretches(hoff_b & band_mask(v, lo, hi) & np.isfinite(u) & np.isfinite(f_t), int(4 * FS)):
            tt = signal.sosfiltfilt(sos, th[a0:b0]); td = np.gradient(tt, DT)
            need_all[a0:b0] = c["a"] * tt + c["b"] * td + c["F"] * np.sign(td)
        m = np.isfinite(need_all)
        if m.sum() < 200:
            continue
        ffl = signal.sosfiltfilt(sos, np.nan_to_num(plant_ff)); ul = signal.sosfiltfilt(sos, np.nan_to_num(u))
        rl = signal.sosfiltfilt(sos, np.nan_to_num(relay))
        need = need_all[m]
        A = np.vstack([need, np.ones(m.sum())]).T
        cf_ff, *_ = np.linalg.lstsq(A, ffl[m], rcond=None)
        cf_u, *_ = np.linalg.lstsq(A, ul[m], rcond=None)
        pr("    %-6s %5.0f s | ff vs need: gain %.3f off %+.4f rms(ff-need) %.4f | (ff+relay) rms %.4f | u vs need: gain %.3f rms(u-need) %.4f | need rms %.4f"
           % (nm, m.sum() * DT, cf_ff[0], cf_ff[1], np.sqrt(np.mean((ffl[m] - need) ** 2)), np.sqrt(np.mean((ffl[m] + rl[m] - need) ** 2)),
              cf_u[0], np.sqrt(np.mean((ul[m] - need) ** 2)), np.sqrt(np.mean(need ** 2))))

    # ------------------------------------------------------------------ S10
    pr("\nS10. TRACKING AND THE REFERENCE PATH [EVIDENCE]")
    sos05 = signal.butter(4, 0.5, "lowpass", fs=FS, output="sos")
    for (lo, hi), nm in zip(IB, IBN):
        runs = L.stretches(hoff & band_mask(v, lo, hi) & np.isfinite(g["la_des"]) & np.isfinite(g["la_act"]), int(10 * FS))
        if not runs:
            continue
        D_ = np.concatenate([signal.sosfiltfilt(sos05, g["la_des"][a:b]) for a, b in runs])
        A_ = np.concatenate([signal.sosfiltfilt(sos05, g["la_act"][a:b]) for a, b in runs])
        C_ = np.concatenate([signal.sosfiltfilt(sos05, (g["des_curv"] * v ** 2)[a:b]) for a, b in runs])
        gain = np.polyfit(D_, A_, 1)[0]
        lag_da, c_da = L.ncc_lag(D_, A_, lo=-0.5, hi=1.0)
        lag_cd, c_cd = L.ncc_lag(C_, D_, lo=-0.5, hi=1.0)
        pr("    %-6s %5.0f s | gain act/des %.3f | lag des->act %+.3f s | lag cmd->setpoint %+.3f s (the fork's own reference filter) | rms err %.3f  bias %+.3f m/s2"
           % (nm, len(D_) * DT, gain, lag_da, lag_cd, np.sqrt(np.mean((D_ - A_) ** 2)), np.mean(D_ - A_)))
    # reference-path phase at 1-3 Hz: setpoint vs the raw command
    runs = L.stretches(eng & np.isfinite(g["la_des"]), int(10.24 * FS))
    if runs:
        D_ = np.concatenate([signal.detrend(g["la_des"][a:b]) for a, b in runs])
        C_ = np.concatenate([signal.detrend((g["des_curv"] * v ** 2)[a:b]) for a, b in runs])
        f, Pcc, Pdd, Pcd, coh = L.welch_cross(C_, D_, nper=1024)
        pr("    setpoint (torqueState.desiredLateralAccel) relative to the raw command desiredCurvature*v^2:")
        pr("      " + "  ".join("%.1fHz: |H| %.2f ph %+.0f coh %.2f" % (f[k], abs(Pcd[k]) / Pcc[k], np.degrees(np.angle(Pcd[k])), coh[k])
                             for k in [int(np.argmin(np.abs(f - fq))) for fq in (0.2, 0.5, 1.0, 1.5, 2.0, 3.0)]))

    # ------------------------------------------------------------------ S11
    pr("\nS11. MEASUREMENT CHECKS [EVIDENCE]")
    m = eng & np.isfinite(g["gyro_yaw"]) & np.isfinite(g["la_act"]) & (v > 3)
    if m.sum() > 500:
        ga = signal.sosfiltfilt(sos05, np.nan_to_num(g["gyro_yaw"] * v)); la = signal.sosfiltfilt(sos05, np.nan_to_num(g["la_act"]))
        for (lo, hi), nm in zip(IB, IBN):
            q = m & band_mask(v, lo, hi)
            if q.sum() > 500:
                sl = np.polyfit(la[q], ga[q], 1)
                pr("    %-6s gyro_yaw*v vs actualLateralAccel: slope %.3f offset %+.3f  (vehicle-model check; 1.00 = the angle->lat-accel map is right)" % (nm, sl[0], sl[1]))
    if np.isfinite(g["roll"]).any():
        r = g["roll"][eng & np.isfinite(g["roll"])]
        pr("    liveParameters.roll median %+.4f rad = %+.2f deg  (9.81*roll = %+.3f m/s2 of feedforward)" % (np.median(r), np.degrees(np.median(r)), 9.81 * np.median(r)))
    ao = g["angle_off"][eng & np.isfinite(g["angle_off"])]
    pr("    liveParameters.angleOffsetDeg median %+.3f; steerRatio %.3f" % (np.median(ao), np.median(g["sr_ratio"][eng & np.isfinite(g["sr_ratio"])])))

    # ------------------------------------------------------------------ S12
    pr("\nS12. DRIVER INTERVENTIONS (steeringPressed onsets while engaged): what the car was doing 0.5 s before [EVIDENCE]")
    pon = np.where(np.diff(np.r_[0, (eng & (g["press"] > 0.5)).astype(int)]) == 1)[0]
    if len(pon):
        rows = []
        for k in pon:
            k0 = max(k - 50, 0)
            rows.append((v[k], abs(ang[k]), g["err"][k0], abs(rate_s[k0:k]).max() if k > k0 else np.nan, g["la_des"][k0], g["la_act"][k0], u[k0]))
        R = np.array(rows, float)
        for (lo, hi), nm in zip(SB, SBN):
            q = band_mask(R[:, 0], lo, hi)
            if q.sum():
                pr("    %-5s %3d onsets | |angle| p50 %5.1f | err(t-0.5) p50 %+.2f | max|rate| p50 %5.1f | |Ddes| p50 %.2f | |u| p50 %.2f"
                   % (nm, q.sum(), np.median(R[q, 1]), np.median(R[q, 2]), np.nanmedian(R[q, 3]), np.median(np.abs(R[q, 4])), np.median(np.abs(R[q, 6]))))

    # ------------------------------------------------------------------ S13
    pr("\nS13. COMMAND DITHER AND THE HONDA LIMITER [EVIDENCE]")
    for (lo, hi), nm in zip(SB, SBN):
        m = eng & band_mask(v, lo, hi)
        runs = L.stretches(m, int(5 * FS))
        if not runs or sum(b - a for a, b in runs) < 20 * FS:
            continue
        C_ = np.concatenate([signal.detrend(g["cmd"][a:b]) for a, b in runs])
        dc = np.abs(np.diff(g["cmd"]))[m[1:]]
        pr("    %-5s cmd rms 3-10 Hz %6.1f counts, 1-3 Hz %6.1f | |dcmd| p50 %.0f p99 %.0f, at the 123 cap %.2f %% | |cmd| p50 %.0f p99 %.0f (rail 4096)"
           % (nm, np.sqrt(np.mean(L.bandpass(C_, 3.0, 10.0) ** 2)), np.sqrt(np.mean(L.bandpass(C_, 1.0, 3.0) ** 2)),
              *np.percentile(dc, [50, 99]), 100 * np.mean(dc >= 122), *np.percentile(np.abs(g["cmd"][m]), [50, 99])))

    out = os.path.join(L.SCRATCH, "v293r2_read_%s.txt" % tag)
    os.makedirs(L.SCRATCH, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))
    pr("\nwritten %s" % out)


if __name__ == "__main__":
    args = sys.argv[1:]
    ref = "r70_v293"
    if "--ref" in args:
        i = args.index("--ref"); ref = args[i + 1]; del args[i:i + 2]
    main(args[0] if args else "r70_v293", ref)
