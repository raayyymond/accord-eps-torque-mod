# -*- coding: utf-8 -*-
"""v293r3_read.py -- the ORCHESTRATOR'S OWN read of the rev-3 fork package (Dom e8e62f0e1 + toggle-config r3)
on the V293 torque-mode EPS, against the rev-1 (route 70) and rev-2 (route 71) drives.  2026-09-14.
ANALYSIS ONLY: reads ident npz caches (v293r2_extract.py), writes a text report.  Builds/sends/flashes nothing.

    python v293r3_read.py r72_v293r3 r73_v293r3 [r71_v293r2 r70_v293]

The goal metric is the operator's: the difference between the PLANNER'S desired lateral acceleration
(desiredCurvature * v^2, i.e. what the car should do) and the actual lateral acceleration.  Rev 3's reference
filter shapes the setpoint the PID sees, so every tracking number is given against BOTH: the planner's desire
(the goal) and the shaped setpoint (what the loop was asked to follow).

Sections (each EVIDENCE unless marked):
  S0  attribution from the wire (commit, the five rev-3 keys, Kp = p/err, LAF = -(p+i+f)/out)
  S1  exposure
  S2  tracking: rms error, gain, lag, |H| and coherence desired->actual by speed band; error energy by frequency
  S3  the 2 Hz mode and the 3-5 Hz rate-loop crossover: prominence of the rate/cmd/angle lines on curves vs straights
  S4  hard-turn jerkiness: rate bursts per minute at low speed, band-passed rate rms in hard turns
  S5  where the torque comes from (f / p / i shares), integrator share
  S6  replay of the rev-3 feedforward from the wire: hold / move / hysteresis / rate loop, and the residual
  S7  the plant model's residual: u(t-Td) - [hold(th) + b th' + J th'' + F sign th'] on hands-off stretches,
      plus a free refit of (a, b, J, F) per band against the fork's constants
  S8  straight-line looseness: low-frequency angle wander, error, and the loop's stiffness on straights
  S9  cross-route comparison table
"""
import math
import os
import re
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402
import v293r2_simlib as S   # noqa: E402  (fork tables parsed from source, vehicle-model algebra)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, DT = L.FS, 1.0 / L.FS
IB = [(1.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
IBN = ["1-8", "8-15", "15-22", ">22"]
OUT = []
pr = L.pr_factory(OUT)
G = 9.81

# ---- rev-3 fork constants, parsed from the committed source (so the replay runs what the device ran)
_SRC = S._SRC
HOLD_V_BP = S._tbl("HONDA_ACCORD_HOLD_V_BP", _SRC)
HOLD_K_V = S._tbl("HONDA_ACCORD_HOLD_K_V", _SRC)
_m = re.search(r"^HONDA_ACCORD_HOLD_SAT_DEG\s*=\s*\(([^)]*)\)", _SRC, re.M)
HOLD_SAT = [float(x) for x in _m.group(1).split(",")]
J_FORK = float(re.search(r"^HONDA_ACCORD_EPS_INERTIA\s*=\s*([0-9.eE+-]+)", _SRC, re.M).group(1))
RL_RC = S._scalar("HONDA_ACCORD_RATE_LOOP_RC", _SRC)
RL_TAPER_V = S._scalar("HONDA_ACCORD_RATE_LOOP_TAPER_V", _SRC)
HYST_BAND = S._scalar("HONDA_ACCORD_FRICTION_HYST_BAND_DEG", _SRC)


def hold_sat(v):
    a, b, c = HOLD_SAT
    return a + b * np.exp(-np.maximum(v, 0.0) / c)


def hold_torque(angle_deg, v):
    angle_deg = np.clip(angle_deg, -S.FF_ANGLE_LIMIT, S.FF_ANGLE_LIMIT)
    k = np.interp(v, HOLD_V_BP, HOLD_K_V)
    sat = hold_sat(v)
    return k * sat * np.tanh(angle_deg / sat)


def hold_slope(angle_deg, v):
    """d hold / d angle (torque per deg) at the operating point."""
    k = np.interp(v, HOLD_V_BP, HOLD_K_V)
    sat = hold_sat(v)
    return k / np.cosh(np.clip(angle_deg, -S.FF_ANGLE_LIMIT, S.FF_ANGLE_LIMIT) / sat) ** 2


def mode_hz(v):
    k = np.interp(v, HOLD_V_BP, HOLD_K_V)
    return np.sqrt(k / J_FORK) / (2 * np.pi)


def fof(x, rc, x0=None):
    """openpilot FirstOrderFilter, causal, alpha = dt/(rc+dt)."""
    a = DT / (rc + DT)
    y = np.empty_like(x)
    y0 = x[0] if x0 is None else x0
    acc = y0
    for i in range(len(x)):
        acc = (1 - a) * acc + a * x[i]
        y[i] = acc
    return y


def pfloat(P, k, d=np.nan):
    try:
        return float(P.get(k, d))
    except Exception:
        return d


def band_mask(v, lo, hi):
    return (v >= lo) & (v < hi)


def welch(x, nper=1024):
    return signal.welch(x, fs=FS, nperseg=nper, noverlap=nper // 2, detrend="linear")


def peak_in(f, P, lo, hi):
    sel = (f >= lo) & (f <= hi)
    if sel.sum() < 3:
        return np.nan, np.nan
    fs_, Ps = f[sel], P[sel]
    k = int(np.argmax(Ps))
    sh = ((f >= lo / 1.6) & (f < lo)) | ((f > hi) & (f <= hi * 1.6))
    if sh.sum() >= 4:
        c = np.polyfit(np.log(f[sh]), np.log(P[sh] + 1e-30), 1)
        base = np.exp(np.polyval(c, np.log(fs_[k])))
        prom = 10 * np.log10((Ps[k] + 1e-30) / (base + 1e-30))
    else:
        prom = np.nan
    return float(fs_[k]), float(prom)


def bp(x, lo, hi):
    return L.bandpass(np.nan_to_num(x), lo, hi)


def load_plus(tag):
    g = L.load(tag)
    D = g["raw"]
    t0 = min(D["t18"][0], D["t_cc"][0])
    ta = g["t"] + t0
    g["jerk"] = L.zoh(ta, D["t_cs"], D["cs_jerk"]) if "cs_jerk" in D else np.full(g["n"], np.nan)
    g["roll"] = L.zoh(ta, D["t_lpar"], D["lpar_roll"]) if "lpar_roll" in D else np.zeros(g["n"])
    return g


def angle_des_from_setpoint(la, v, ang_meas, roll, sr_level=None):
    """the fork's angle_des: degrees(VM.get_steer_from_curvature(-curv_des, v, roll)), VM.sR = the variable map at the
    MEASURED angle (controlsd).  +left frame.  latAccelOffset taken as 0 (KeepLearnedLatAccelOffset 0)."""
    v2 = np.maximum(v ** 2, 1.0)
    curv = la / v2
    fade = np.interp(v, [0.5, 2.5], [0.0, 1.0])
    sr = np.array([S.steer_ratio(a, sr_level) for a in np.nan_to_num(ang_meas)])
    vv = np.maximum(v, 0.1)
    cf = S.curvature_factor(vv)
    rc = G * roll * fade / ((1.0 / S.SLIP) - vv ** 2)
    return np.degrees((-curv - rc) * sr / cf)


class Route:
    pass


def analyse(tag):
    R = Route()
    g = load_plus(tag)
    P = g["meta"].get("params", {}) or {}
    R.tag, R.P, R.g = tag, P, g
    v, ang, rate, u = g["v"], g["ang"], g["rate_dps"], -g["op_torque"]
    th = -ang
    eng = g["eng"] & np.isfinite(v) & np.isfinite(u) & (g["cs_active"] > 0.5)
    w = int(0.5 * FS)
    press_buf = np.convolve((g["press"] > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0
    hoff = eng & ~press_buf
    R.eng, R.hoff = eng, hoff

    pr("=" * 118)
    pr("V293 REV-3 READ   tag %s   route %s   %d segments" % (tag, g["meta"]["route"], len(g["meta"]["segments"])))
    pr("=" * 118)

    # ------------------------------------------------------------------ S0
    pr("\nS0. ATTRIBUTION FROM THE WIRE")
    for k in ("GitCommit", "GitBranch", "AccordRatePlantFF", "AccordHoldMap", "AccordFrictionHyst", "AccordRateLoopGain",
              "AccordErrorNotchQ", "AccordRefFilter", "SteerFriction", "SteerLatAccel", "SteerKP", "AccordTorqueKi",
              "AccordFFRateGain", "AccordEpsSpringScale", "AccordEpsGainScale", "KeepLearnedLatAccelOffset", "SteerDelay",
              "SteerRatio", "AccordVariableSteerRatio"):
        pr("    %-28s %s" % (k, str(P.get(k, "ABSENT"))[:64]))
    q = eng & (np.abs(g["err"]) > 1e-3) & np.isfinite(g["p"])
    kp = g["p"][q] / g["err"][q]
    q2 = eng & (np.abs(g["out"]) > 1e-3)
    laf = -(g["p"][q2] + g["i"][q2] + g["f"][q2]) / g["out"][q2]
    R.KP, R.LAF = float(np.median(kp)), float(np.median(laf))
    pr("    Kp = median p/err = %.4f (IQR %.4f..%.4f)   LAF = median -(p+i+f)/out = %.4f (IQR %.4f..%.4f)"
       % (R.KP, *np.percentile(kp, [25, 75]), R.LAF, *np.percentile(laf, [25, 75])))
    ok = np.isfinite(rate) & np.isfinite(ang)
    c = np.corrcoef(rate[ok], np.gradient(ang, DT)[ok])[0, 1]
    rate_l = rate if c > 0 else -rate          # +left frame (same as ang)
    R.rate_l = rate_l
    pr("    0x18F rate vs d(angle)/dt corr %+.3f -> rate put in the +left angle frame" % c)
    R.KI = pfloat(P, "AccordTorqueKi", 0.3)
    R.KV = pfloat(P, "AccordRateLoopGain", 0.0) if "AccordRateLoopGain" in P else 0.0
    R.HY = pfloat(P, "AccordFrictionHyst", 0.0) if "AccordFrictionHyst" in P else 0.0
    R.REF = pfloat(P, "AccordRefFilter", 0.0) if "AccordRefFilter" in P else 0.0
    R.NQ = pfloat(P, "AccordErrorNotchQ", 0.0) if "AccordErrorNotchQ" in P else 0.0
    R.HOLDMAP = str(P.get("AccordHoldMap", "0")) in ("1", "True", "true")
    R.FR = pfloat(P, "SteerFriction", 0.0)
    R.RG = pfloat(P, "AccordFFRateGain", 0.5)

    # ------------------------------------------------------------------ S1
    pr("\nS1. EXPOSURE")
    R.t_eng = eng.sum() * DT
    pr("    wall %.0f s   laterally engaged %.0f s   hands-off (0.5 s buffer) %.0f s   pressed-while-engaged %.1f s"
       % (g["n"] * DT, R.t_eng, hoff.sum() * DT, (eng & (g["press"] > 0.5)).sum() * DT))
    vv = v[eng]
    pr("    engaged speed p05/p50/p95/max %.1f / %.1f / %.1f / %.1f m/s;  by band: %s"
       % (*np.percentile(vv, [5, 50, 95]), vv.max(),
          "  ".join("%s %.0f s" % (nm, (eng & band_mask(v, lo, hi)).sum() * DT) for (lo, hi), nm in zip(IB, IBN))))
    la_plan = g["des_curv"] * v ** 2
    R.la_plan = la_plan
    hard = eng & (np.abs(la_plan) > 1.5)
    pr("    |planner lat accel| > 1.5 m/s^2 engaged: %.0f s;  > 2.5: %.0f s;  |angle| > 30 deg: %.0f s"
       % (hard.sum() * DT, (eng & (np.abs(la_plan) > 2.5)).sum() * DT, (eng & (np.abs(ang) > 30)).sum() * DT))

    # ------------------------------------------------------------------ S2
    pr("\nS2. TRACKING  (goal metric: planner desire desiredCurvature*v^2 vs actual; also vs the shaped setpoint the PID saw)")
    pr("    %-6s %5s | %8s %8s %8s | %8s %8s | %6s %6s | %s" %
       ("band", "s", "rms(plan)", "rms(set)", "rms|la|", "gain pl", "gain set", "lag pl", "lag set", "|H| / coh plan->act @ 0.2 0.5 1.0 2.0 Hz"))
    R.trk = {}
    for (lo, hi), nm in zip(IB, IBN):
        m = hoff & band_mask(v, lo, hi) & np.isfinite(la_plan) & np.isfinite(g["la_act"]) & np.isfinite(g["la_des"])
        if m.sum() < 500:
            continue
        st = L.stretches(m, int(8 * FS))
        if not st:
            continue
        e_pl = (la_plan - g["la_act"])[m]; e_st = (g["la_des"] - g["la_act"])[m]
        gp = np.polyfit(la_plan[m], g["la_act"][m], 1)[0]
        gs = np.polyfit(g["la_des"][m], g["la_act"][m], 1)[0]
        # lag and transfer on concatenated detrended stretches
        Xp = np.concatenate([signal.detrend(la_plan[a:b]) for a, b in st])
        Xs = np.concatenate([signal.detrend(g["la_des"][a:b]) for a, b in st])
        Y = np.concatenate([signal.detrend(g["la_act"][a:b]) for a, b in st])
        lag_p, _ = L.ncc_lag(Xp, Y, lo=0.0, hi=1.5)
        lag_s, _ = L.ncc_lag(Xs, Y, lo=0.0, hi=1.5)
        f, Pxx, Pyy, Pxy, coh = L.welch_cross(Xp, Y, nper=1024)
        H = Pxy / np.maximum(Pxx, 1e-30)
        hs = []
        for fq in (0.2, 0.5, 1.0, 2.0):
            k = int(np.argmin(np.abs(f - fq)))
            hs.append("%.2f/%.2f" % (np.abs(H[k]), coh[k]))
        pr("    %-6s %5.0f | %8.3f %8.3f %8.3f | %8.3f %8.3f | %6.2f %6.2f | %s"
           % (nm, m.sum() * DT, np.sqrt(np.mean(e_pl ** 2)), np.sqrt(np.mean(e_st ** 2)), np.sqrt(np.mean(g["la_act"][m] ** 2)),
              gp, gs, lag_p, lag_s, "  ".join(hs)))
        # error energy by frequency band (planner error)
        E = np.concatenate([signal.detrend((la_plan - g["la_act"])[a:b]) for a, b in st])
        fe, Pe = welch(E, 2048)
        tot = np.trapezoid(Pe, fe)
        parts = []
        for flo, fhi in ((0.0, 0.3), (0.3, 1.0), (1.0, 3.0), (3.0, 50.0)):
            s_ = (fe >= flo) & (fe < fhi)
            parts.append(100 * np.trapezoid(Pe[s_], fe[s_]) / max(tot, 1e-30))
        pr("           planner-error energy share <0.3 / 0.3-1 / 1-3 / >3 Hz: %4.0f / %4.0f / %4.0f / %4.0f %%   (dc offset %+.3f m/s^2)"
           % (*parts, np.mean(e_pl)))
        R.trk[nm] = dict(rms_pl=float(np.sqrt(np.mean(e_pl ** 2))), rms_st=float(np.sqrt(np.mean(e_st ** 2))),
                         gain_pl=float(gp), gain_set=float(gs), lag_pl=float(lag_p), lag_set=float(lag_s),
                         shares=parts, t=float(m.sum() * DT))
    # turn-hold ratio in sustained curves: median actual/desired where |plan| > 0.8 and slowly varying
    pr("    turn-hold actual/planner (|plan| 0.8-1.5 / >1.5 m/s^2, |d plan/dt| < 0.5 m/s^3):")
    dpl = np.gradient(np.nan_to_num(la_plan), DT)
    R.hold_ratio = {}
    for (lo, hi), nm in zip(IB, IBN):
        row = []
        for plo, phi in ((0.8, 1.5), (1.5, 9.0)):
            m = hoff & band_mask(v, lo, hi) & (np.abs(la_plan) >= plo) & (np.abs(la_plan) < phi) & (np.abs(dpl) < 0.5)
            if m.sum() > 200:
                r_ = np.median(g["la_act"][m] / la_plan[m])
                row.append("%.3f (n %d)" % (r_, m.sum())); R.hold_ratio[(nm, plo)] = float(r_)
            else:
                row.append("   -   ")
        pr("      %-6s %s" % (nm, "   ".join(row)))

    # ------------------------------------------------------------------ S3
    pr("\nS3. THE 2 Hz MODE AND THE 3-5 Hz RATE-LOOP CROSSOVER  (Welch 1024, prominence dB above the log-log shoulders)")
    pr("    stratum: curve = |planner| > 1.0 m/s^2, straight = |planner| < 0.4; hands-off stretches >= 6 s")
    pr("    %-6s %-8s %5s | %-22s %-22s %-22s | %-22s" % ("band", "stratum", "s", "rate 1.6-3 Hz", "cmd 1.6-3 Hz", "ang 1.6-3 Hz", "rate 3-5.5 Hz"))
    R.spec = {}
    for (lo, hi), nm in zip(IB, IBN):
        for sname, smask in (("curve", np.abs(la_plan) > 1.0), ("straight", np.abs(la_plan) < 0.4)):
            m = hoff & band_mask(v, lo, hi) & smask & np.isfinite(rate_l) & np.isfinite(g["cmd"])
            st = L.stretches(m, int(6 * FS))
            if not st or sum(b - a for a, b in st) < 20 * FS:
                continue
            cells = []
            for arr, (flo, fhi) in ((rate_l, (1.6, 3.0)), (g["cmd"], (1.6, 3.0)), (ang, (1.6, 3.0)), (rate_l, (3.0, 5.5))):
                X = np.concatenate([signal.detrend(np.nan_to_num(arr[a:b])) for a, b in st])
                f, Pw = welch(X, 1024)
                fk, prom = peak_in(f, Pw, flo, fhi)
                rms_band = np.sqrt(np.trapezoid(Pw[(f >= flo) & (f <= fhi)], f[(f >= flo) & (f <= fhi)]))
                cells.append("%.2f Hz %+5.1f dB rms %5.2f" % (fk, prom, rms_band))
            pr("    %-6s %-8s %5.0f | %s" % (nm, sname, sum(b - a for a, b in st) * DT, " | ".join(cells)))
            R.spec[(nm, sname)] = cells
    # the 0.5-3 Hz band-passed rms on curves at speed (the route-71 headline: rate 27 deg/s, angle 2.3 deg, cmd 108 counts)
    for (lo, hi), nm in zip(IB, IBN):
        m = hoff & band_mask(v, lo, hi) & (np.abs(la_plan) > 1.0)
        st = L.stretches(m, int(6 * FS))
        if not st:
            continue
        rr = np.concatenate([bp(rate_l[a:b], 0.5, 3.0) for a, b in st])
        aa = np.concatenate([bp(ang[a:b], 0.5, 3.0) for a, b in st])
        cc = np.concatenate([bp(g["cmd"][a:b], 0.5, 3.0) for a, b in st])
        R.spec[("bp", nm)] = (float(np.sqrt(np.mean(rr ** 2))), float(np.sqrt(np.mean(aa ** 2))), float(np.sqrt(np.mean(cc ** 2))))
        pr("    curves at %-5s 0.5-3 Hz band-passed rms: rate %5.1f deg/s   angle %4.2f deg   cmd %5.0f counts   (%.0f s)"
           % (nm, *R.spec[("bp", nm)], sum(b - a for a, b in st) * DT))

    # ------------------------------------------------------------------ S4
    pr("\nS4. HARD-TURN JERKINESS")
    R.bursts = {}
    for vlo, vhi, nm in ((0.0, 10.0, "v<10"), (10.0, 20.0, "10-20"), (20.0, 99.0, ">20")):
        m = eng & band_mask(v, vlo, vhi) & (np.abs(la_plan) > 1.0)
        if m.sum() < 300:
            continue
        r_abs = np.abs(np.nan_to_num(rate_l))
        thr = 80.0 if vhi <= 10 else 40.0
        onsets = np.diff(np.r_[0, ((r_abs > thr) & m).astype(int)]) == 1
        n_b = int(onsets.sum()); dur = m.sum() * DT
        # rate reversals per minute while turning hard (|rate| > 5 crossing sign)
        rr = np.nan_to_num(rate_l) * m
        rev = np.sum((np.sign(rr[1:]) * np.sign(rr[:-1]) < 0) & (np.abs(rr[1:]) > 5) & m[1:])
        jr = bp(rate_l, 0.5, 5.0)[m]
        acc = np.gradient(np.nan_to_num(rate_l), DT)[m]
        pr("    %-6s hard turns %5.0f s: |rate| > %.0f deg/s bursts %5.1f /min;  rate sign reversals %5.1f /min;  0.5-5 Hz rate rms %5.1f deg/s;  |d rate/dt| p90 %6.0f deg/s^2;  cmd step p99 %4.0f counts;  honda cap (|step| >= 120) %.1f %%"
           % (nm, dur, thr, n_b / (dur / 60), rev / (dur / 60), np.sqrt(np.mean(jr ** 2)), np.percentile(np.abs(acc), 90),
              np.percentile(np.abs(np.diff(g["cmd"]))[m[1:]], 99), 100 * np.mean(np.abs(np.diff(g["cmd"]))[m[1:]] >= 120)))
        R.bursts[nm] = dict(bpm=n_b / (dur / 60), rev=rev / (dur / 60), rms=float(np.sqrt(np.mean(jr ** 2))), dur=dur)
    # the stall-ramp-snap signature: wheel still (|rate|<3) for >= 0.3 s while |d cmd| grows > 400 counts, then |rate| > 100
    still = (np.abs(np.nan_to_num(rate_l)) < 3.0) & eng & (v < 10) & (np.abs(la_plan) > 0.8)
    st = L.stretches(still, int(0.3 * FS))
    n_snap = 0
    for a, b in st:
        if b + 50 < len(rate_l) and np.abs(g["cmd"][b - 1] - g["cmd"][a]) > 400 and np.nanmax(np.abs(rate_l[b:b + 50])) > 100:
            n_snap += 1
    lowhard = (eng & (v < 10) & (np.abs(la_plan) > 0.8)).sum() * DT
    R.snaps = n_snap / max(lowhard / 60, 1e-6)
    pr("    stall -> ramp (> 400 counts) -> snap (> 100 deg/s) events at v < 10, |plan| > 0.8: %d in %.0f s = %.1f /min" % (n_snap, lowhard, R.snaps))

    # ------------------------------------------------------------------ S5
    pr("\nS5. WHERE THE TORQUE COMES FROM (torque units = output/LAF)")
    f_t, p_t, i_t = g["f"] / R.LAF, g["p"] / R.LAF, g["i"] / R.LAF
    R.shares = {}
    pr("    %-6s | %6s %6s %6s | %7s %7s %7s | %8s" % ("band", "f shr", "p shr", "i shr", "med|f|", "med|p|", "med|i|", "|i|>0.2 %"))
    for (lo, hi), nm in zip(IB, IBN):
        m = eng & band_mask(v, lo, hi) & np.isfinite(f_t)
        if m.sum() < 200:
            continue
        af, ap, ai = np.abs(f_t[m]), np.abs(p_t[m]), np.abs(i_t[m])
        tot = af + ap + ai + 1e-9
        R.shares[nm] = (float(np.mean(af / tot)), float(np.mean(ap / tot)), float(np.mean(ai / tot)))
        pr("    %-6s | %6.3f %6.3f %6.3f | %7.3f %7.3f %7.3f | %8.1f"
           % (nm, *R.shares[nm], np.median(af), np.median(ap), np.median(ai), 100 * np.mean(ai > 0.2)))

    # ------------------------------------------------------------------ S6
    pr("\nS6. REPLAY OF THE FEEDFORWARD FROM THE WIRE  (angle_des from the shaped setpoint through the fork's SR map + roll comp)")
    sr_level = pfloat(P, "SteerRatio", 16.88) if str(P.get("AccordVariableSteerRatio", "1")) == "1" else None
    a_des = angle_des_from_setpoint(np.nan_to_num(g["la_des"]), np.nan_to_num(v), ang, np.nan_to_num(g["roll"]), None)
    R.a_des = a_des
    d_ades = np.r_[0.0, np.diff(a_des)]
    d_ades[~eng] = 0.0
    ades_rate = fof(d_ades / DT, S.FF_RATE_RC)
    Gv = np.interp(v, S.G_BP, S.G_V)
    lim = np.interp(v, S.MOVE_BP, S.MOVE_V)
    move = np.clip(R.RG * ades_rate / Gv, -lim, lim)
    if R.HOLDMAP:
        hold = hold_torque(a_des, v)
    else:
        hold = np.interp(v, S.K_BP, S.K_V) * np.clip(a_des, -S.FF_ANGLE_LIMIT, S.FF_ANGLE_LIMIT) / Gv
    # hysteresis
    z = np.zeros_like(a_des)
    if R.HY > 0:
        acc = 0.0
        for i in range(len(z)):
            if not eng[i]:
                acc = 0.0
            else:
                acc = float(np.clip(acc + d_ades[i] * R.HY / HYST_BAND, -R.HY, R.HY))
            z[i] = acc
    # rate loop
    rate_meas = fof(np.nan_to_num(rate_l), RL_RC)
    kv = R.KV * np.minimum(1.0, RL_TAPER_V / np.maximum(v, 0.1))
    rl = kv * (ades_rate - rate_meas)
    ff_rep = -(hold + move) - z - rl          # controller frame
    resid = f_t - ff_rep
    R.ff_parts = dict(hold=-hold, move=-move, hyst=-z, rl=-rl)
    pr("    %-6s | %8s %8s %8s %8s | %8s %8s %8s" % ("band", "rms hold", "rms move", "rms hyst", "rms rl", "rms f", "rms resid", "R2"))
    R.rep = {}
    for (lo, hi), nm in zip(IB, IBN):
        m = eng & band_mask(v, lo, hi) & np.isfinite(f_t)
        if m.sum() < 200:
            continue
        r2 = L.r2(f_t[m], ff_rep[m])
        R.rep[nm] = dict(hold=float(np.sqrt(np.mean(hold[m] ** 2))), move=float(np.sqrt(np.mean(move[m] ** 2))),
                         hyst=float(np.sqrt(np.mean(z[m] ** 2))), rl=float(np.sqrt(np.mean(rl[m] ** 2))),
                         f=float(np.sqrt(np.mean(f_t[m] ** 2))), resid=float(np.sqrt(np.mean(resid[m] ** 2))), r2=float(r2))
        d = R.rep[nm]
        pr("    %-6s | %8.4f %8.4f %8.4f %8.4f | %8.4f %8.4f %8.3f" % (nm, d["hold"], d["move"], d["hyst"], d["rl"], d["f"], d["resid"], d["r2"]))
    # what does the rate loop DO: its sign vs the wheel rate (damping if opposite), and its spectrum share
    m = eng & np.isfinite(rate_l) & (np.abs(rate_l) > 5)
    if R.KV > 0 and m.sum() > 100:
        damp = np.mean(np.sign(rl[m]) == np.sign(rate_meas[m]))   # rl = kv*(des - meas): opposes meas when des small
        pr("    rate loop: |rl| p50/p90 %.4f/%.4f torque; fraction of frames where rl opposes the measured rate (damping): %.2f;"
           " ades_rate rms %.1f vs rate_meas rms %.1f deg/s (engaged)" %
           (*np.percentile(np.abs(rl[eng]), [50, 90]), 1 - damp, np.sqrt(np.mean(ades_rate[eng] ** 2)), np.sqrt(np.mean(rate_meas[eng] ** 2))))
    # how well does angle_des track the measured angle (the plant FF's own error)
    m = hoff & np.isfinite(ang)
    e_a = (a_des - ang)[m]
    pr("    angle_des - angle (hands-off): rms %.2f deg, median %+.2f, p90 |.| %.2f;  by band: %s"
       % (np.sqrt(np.mean(e_a ** 2)), np.median(e_a), np.percentile(np.abs(e_a), 90),
          "  ".join("%s %.2f" % (nm, np.sqrt(np.mean(((a_des - ang)[hoff & band_mask(v, lo, hi)]) ** 2))) for (lo, hi), nm in zip(IB, IBN) if (hoff & band_mask(v, lo, hi)).sum() > 100)))

    # ------------------------------------------------------------------ S7
    pr("\nS7. THE PLANT MODEL'S RESIDUAL  (u(t - Td) = hold(th) + b th' + J th'' + F sign(th') + u0; hands-off stretches >= 4 s, 5 Hz LPF)")
    mask = L.clean_mask(g, hands_off=True, min_v=1.0, buffer_s=0.5)
    strets = L.stretches(mask, int(4 * FS))
    pr("    %d stretches, %.0f s;  fork constants: J %.1e, b (mode) 0.0006, F (hyst) %.3f" % (len(strets), sum(b - a for a, b in strets) * DT, J_FORK, R.HY))
    sos = signal.butter(4, 5.0, "lowpass", fs=FS, output="sos")
    Td = 0.04
    nd = int(round(Td / DT))
    pr("    %-6s %5s %5s | %-40s | %-44s | %s" % ("band", "v", "n", "fork map: rms resid / rms u, R2 (b,J,F fixed)", "free fit a(t/deg) b(t/dps) J(t/dps2) F", "R2 free"))
    R.plant = {}
    for (lo, hi), nm in zip(IB, IBN):
        TH, TD, TDD, U, VV, HOLDF = [], [], [], [], [], []
        for (a0, b0) in strets:
            idx = np.arange(a0, b0)
            sel = band_mask(v[idx], lo, hi)
            if sel.sum() < 200:
                continue
            uu = signal.sosfiltfilt(sos, u[a0:b0]); tt = signal.sosfiltfilt(sos, th[a0:b0])
            td = np.gradient(tt, DT); tdd = np.gradient(td, DT)
            # delay: the plant sees u nd frames ago
            uu_d = np.r_[np.full(nd, uu[0]), uu[:-nd]] if nd > 0 else uu
            q = sel.copy(); q[:nd + 10] = False
            TH.append(tt[q]); TD.append(td[q]); TDD.append(tdd[q]); U.append(uu_d[q]); VV.append(np.median(v[idx][sel]))
            HOLDF.append(hold_torque(tt[q], v[idx][q]))
        if len(TH) < 2:
            pr("    %-6s only %d stretches" % (nm, len(TH))); continue
        TH_, TD_, TDD_, U_, HF_ = map(np.concatenate, (TH, TD, TDD, U, HOLDF))
        # fork model residual with b, J, F fixed
        pred = HF_ + 0.0006 * TD_ + J_FORK * TDD_ + R.HY * np.sign(TD_)
        res = U_ - pred
        res -= np.median(res)
        r2_f = L.r2(U_, pred + np.median(U_ - pred))
        # free fit
        A = np.vstack([TH_, TD_, TDD_, np.sign(TD_), np.ones(len(TH_))]).T
        cf, *_ = np.linalg.lstsq(A, U_, rcond=None)
        r2_free = L.r2(U_, A @ cf)
        vmed = float(np.median(VV))
        R.plant[nm] = dict(v=vmed, resid=float(np.sqrt(np.mean(res ** 2))), rms_u=float(np.sqrt(np.mean((U_ - U_.mean()) ** 2))),
                           r2_fork=float(r2_f), a=float(cf[0]), b=float(cf[1]), J=float(cf[2]), F=float(cf[3]), r2_free=float(r2_free),
                           fork_slope=float(np.median(hold_slope(TH_, vmed))))
        d = R.plant[nm]
        pr("    %-6s %5.1f %5d | %8.4f / %8.4f  R2 %6.3f              | %8.5f %8.5f %9.2e %7.4f | %6.3f   fork hold slope at op %.5f"
           % (nm, vmed, len(TH), d["resid"], d["rms_u"], d["r2_fork"], d["a"], d["b"], d["J"], d["F"], d["r2_free"], d["fork_slope"]))
        # residual spectrum: where does the model miss
        fe, Pe = welch(res, 1024)
        tot = np.trapezoid(Pe, fe)
        parts = []
        for flo, fhi in ((0.0, 0.3), (0.3, 1.0), (1.0, 3.0), (3.0, 50.0)):
            s_ = (fe >= flo) & (fe < fhi)
            parts.append(100 * np.trapezoid(Pe[s_], fe[s_]) / max(tot, 1e-30))
        pr("           residual energy <0.3 / 0.3-1 / 1-3 / >3 Hz: %4.0f / %4.0f / %4.0f / %4.0f %%" % tuple(parts))
    # hold-map check: wheel still, torque vs map
    pr("    hold-map check (hands-off, |rate| < 15 deg/s, 1 Hz LPF): median u / map(th) by |angle| cell and band")
    sos1 = signal.butter(2, 1.0, "lowpass", fs=FS, output="sos")
    u1 = signal.sosfiltfilt(sos1, np.nan_to_num(u)); th1 = signal.sosfiltfilt(sos1, np.nan_to_num(th))
    still = hoff & (np.abs(np.nan_to_num(rate_l)) < 15)
    R.holdchk = {}
    for (lo, hi), nm in zip(IB, IBN):
        row = []
        for alo, ahi in ((3, 12), (12, 25), (25, 45), (45, 90), (90, 400)):
            m = still & band_mask(v, lo, hi) & (np.abs(th1) >= alo) & (np.abs(th1) < ahi)
            if m.sum() > 150:
                ratio = np.median(u1[m] * np.sign(th1[m])) / max(np.median(hold_torque(np.abs(th1[m]), v[m])), 1e-4)
                row.append("%2d-%3d: %5.2f (%4.0fs)" % (alo, ahi, ratio, m.sum() * DT)); R.holdchk[(nm, alo)] = float(ratio)
        if row:
            pr("      %-6s %s" % (nm, "  ".join(row)))

    # ------------------------------------------------------------------ S8
    pr("\nS8. STRAIGHT-LINE LOOSENESS  (hands-off, |planner| < 0.4 m/s^2, v >= 8, stretches >= 10 s)")
    R.straight = {}
    for (lo, hi), nm in zip(IB[1:], IBN[1:]):
        m = hoff & band_mask(v, lo, hi) & (np.abs(la_plan) < 0.4)
        st = L.stretches(m, int(10 * FS))
        if not st:
            continue
        A_lo = np.concatenate([bp(ang[a:b], 0.05, 0.5) for a, b in st])
        E_lo = np.concatenate([bp((la_plan - g["la_act"])[a:b], 0.05, 0.5) for a, b in st])
        E_mid = np.concatenate([bp((la_plan - g["la_act"])[a:b], 0.5, 3.0) for a, b in st])
        # loop stiffness: torque change per degree of angle error (angle_des - angle), low-passed 1 Hz
        X = np.concatenate([signal.sosfiltfilt(sos1, (a_des - ang)[a:b]) for a, b in st])
        Y = np.concatenate([signal.sosfiltfilt(sos1, (-u)[a:b]) for a, b in st])   # -u is in the +left frame
        k_st = np.polyfit(X, Y, 1)[0]
        R.straight[nm] = dict(t=sum(b - a for a, b in st) * DT, ang_lo=float(np.sqrt(np.mean(A_lo ** 2))),
                              e_lo=float(np.sqrt(np.mean(E_lo ** 2))), e_mid=float(np.sqrt(np.mean(E_mid ** 2))), k=float(k_st))
        d = R.straight[nm]
        pr("    %-6s %5.0f s: angle wander 0.05-0.5 Hz rms %.2f deg;  planner error rms 0.05-0.5 Hz %.3f, 0.5-3 Hz %.3f m/s^2;  loop stiffness %.4f torque/deg (fork hold slope %.4f)"
           % (nm, d["t"], d["ang_lo"], d["e_lo"], d["e_mid"], d["k"], float(np.median(hold_slope(0.0, v[m])))))
    return R


def compare(RS):
    pr("\n" + "=" * 118)
    pr("S9. CROSS-ROUTE COMPARISON")
    pr("=" * 118)
    tags = [R.tag for R in RS]
    pr("    %-44s " % "" + "".join("%14s" % t[:13] for t in tags))
    pr("    %-44s " % "commit" + "".join("%14s" % str(R.P.get("GitCommit", "?"))[:9] for R in RS))
    pr("    %-44s " % "Kp / LAF / Ki" + "".join("%14s" % ("%.2f/%.0f/%.2f" % (R.KP, R.LAF, R.KI)) for R in RS))
    pr("    %-44s " % "engaged s" + "".join("%14.0f" % R.t_eng for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("rms planner error %s" % nm) + "".join("%14s" % ("%.3f" % R.trk[nm]["rms_pl"] if nm in R.trk else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("rms shaped-setpoint error %s" % nm) + "".join("%14s" % ("%.3f" % R.trk[nm]["rms_st"] if nm in R.trk else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("tracking gain planner %s" % nm) + "".join("%14s" % ("%.3f" % R.trk[nm]["gain_pl"] if nm in R.trk else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("lag planner->actual s %s" % nm) + "".join("%14s" % ("%.2f" % R.trk[nm]["lag_pl"] if nm in R.trk else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("planner-error share 1-3 Hz %% %s" % nm) + "".join("%14s" % ("%.0f" % R.trk[nm]["shares"][2] if nm in R.trk else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("turn-hold act/plan 0.8-1.5 %s" % nm) + "".join("%14s" % ("%.3f" % R.hold_ratio[(nm, 0.8)] if (nm, 0.8) in R.hold_ratio else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("curve 0.5-3 Hz rate rms deg/s %s" % nm) + "".join("%14s" % ("%.1f" % R.spec[("bp", nm)][0] if ("bp", nm) in R.spec else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("curve 0.5-3 Hz angle rms deg %s" % nm) + "".join("%14s" % ("%.2f" % R.spec[("bp", nm)][1] if ("bp", nm) in R.spec else "-") for R in RS))
    for nm in ("v<10", "10-20", ">20"):
        pr("    %-44s " % ("hard-turn rate bursts /min %s" % nm) + "".join("%14s" % ("%.1f" % R.bursts[nm]["bpm"] if nm in R.bursts else "-") for R in RS))
    for nm in ("v<10", "10-20", ">20"):
        pr("    %-44s " % ("hard-turn 0.5-5 Hz rate rms %s" % nm) + "".join("%14s" % ("%.1f" % R.bursts[nm]["rms"] if nm in R.bursts else "-") for R in RS))
    pr("    %-44s " % "stall-ramp-snap /min (v<10)" + "".join("%14.1f" % R.snaps for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("integrator share %s" % nm) + "".join("%14s" % ("%.2f" % R.shares[nm][2] if nm in R.shares else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("plant resid/rms u (fork map) %s" % nm) + "".join("%14s" % ("%.2f" % (R.plant[nm]["resid"] / max(R.plant[nm]["rms_u"], 1e-9)) if nm in R.plant else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("free-fit a torque/deg %s" % nm) + "".join("%14s" % ("%.5f" % R.plant[nm]["a"] if nm in R.plant else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("fork hold slope at op %s" % nm) + "".join("%14s" % ("%.5f" % R.plant[nm]["fork_slope"] if nm in R.plant else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("free-fit b torque/(deg/s) %s" % nm) + "".join("%14s" % ("%.5f" % R.plant[nm]["b"] if nm in R.plant else "-") for R in RS))
    for nm in IBN:
        pr("    %-44s " % ("free-fit J torque/(deg/s2) %s" % nm) + "".join("%14s" % ("%.1e" % R.plant[nm]["J"] if nm in R.plant else "-") for R in RS))
    for nm in IBN[1:]:
        pr("    %-44s " % ("straight angle wander rms deg %s" % nm) + "".join("%14s" % ("%.2f" % R.straight[nm]["ang_lo"] if nm in R.straight else "-") for R in RS))
    for nm in IBN[1:]:
        pr("    %-44s " % ("straight loop stiffness t/deg %s" % nm) + "".join("%14s" % ("%.4f" % R.straight[nm]["k"] if nm in R.straight else "-") for R in RS))


if __name__ == "__main__":
    tags = sys.argv[1:] or ["r72_v293r3", "r73_v293r3", "r71_v293r2", "r70_v293"]
    RS = [analyse(t) for t in tags]
    if len(RS) > 1:
        compare(RS)
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    out = os.path.join(HERE, "_scratch", "v293r3_read_%s.txt" % "_".join(t.split("_")[0] for t in tags))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))
    pr("\nwritten %s" % out)
