# -*- coding: utf-8 -*-
"""v293r5_read.py -- the orchestrator's own read of the rev-4 drive (Dom 08a5a7064 + toggle-config r4) on the V293
torque-map EPS, against rev 3 (routes 72/73).  2026-09-15.  ANALYSIS ONLY: reads ident npz caches (v293r2_extract.py).

    python v293r5_read.py r75_v293r4 [r72_v293r3 r73_v293r3]

Operator's words for this drive: still a little loose; still jerky on hard turns; not as smooth / confident as the
1 kHz inner loop; "feels like the command has to overshoot to get over friction, isn't able to linearize friction";
avoid things that add a variable delay (relying heavily on Ki).  The sections are the instruments behind those words:

  N0  attribution (commit, SteerFriction 0.0, AccordTorqueKiHigh, live delay), Kp / LAF from the wire
  N1  DAMPING: is the plant a lightly damped 2 Hz mode (b 0.0006, the rev-3/4 design premise) or overdamped (the ident's
      b 0.004)?  Joint-IO (planner-instrumented) torque->angle transfer at 15-30 m/s, 0.2-4 Hz, against both model shapes.
  N2  STICTION / BREAKAWAY: dwell-then-jump events per minute, the torque the command had to add during the dwell before
      the wheel moved (the "overshoot to get over friction"), the jump size vs what the planner asked, P/I/F shares at
      breakaway; by speed band, hands-off.
  N3  THE INTEGRATOR: |i| share of the torque, and the 0.2-1 Hz error / rate content on >15 m/s curves (an integrator hunt
      would show here) vs rev 3.
  N4  COMMAND-PROPORTIONAL FRICTION (the EPS's own 1 kHz friction-compensation lane is |command|-proportional): the plant
      residual regressed on sign(rate), sign(rate)*|u|, rate*|u| on hands-off stretches.
  N5  ROAD CROWN: the low-frequency residual vs liveParameters.roll.
  N6  TRACKING vs the PLANNER by band (gain, lag, rms error, |H|(0.2 Hz)), error energy by frequency band -- the goal metric.
"""
import math
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L        # noqa: E402
import v293r2_simlib as S         # noqa: E402
import v293r3_read as R3          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, DT = L.FS, 1.0 / L.FS
G = 9.81
IB = [(4.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
IBN = ["4-8", "8-15", "15-22", ">22"]
B_IDENT_BP = [8.0, 12.0, 19.0, 26.0]
B_IDENT_V = [0.0018, 0.0037, 0.0041, 0.0049]
J_ID = 1.0e-4
TD = 0.06
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def bp(x, lo, hi, order=3):
    sos = signal.butter(order, [lo, hi], btype="bandpass", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def lp(x, fc, order=3):
    sos = signal.butter(order, fc, btype="lowpass", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def stretches(mask, min_len):
    return L.stretches(mask, min_len)


class Route:
    pass


def load(tag):
    R = Route()
    g = R3.load_plus(tag)
    P = g["meta"].get("params", {}) or {}
    R.tag, R.P, R.g = tag, P, g
    v = g["v"]; ang = g["ang"]; u = -g["op_torque"]; th = -ang
    rate_raw = g["rate_dps"]
    ok = np.isfinite(rate_raw) & np.isfinite(ang)
    c = np.corrcoef(rate_raw[ok], np.gradient(ang, DT)[ok])[0, 1]
    rate_l = rate_raw if c > 0 else -rate_raw           # +left = ang frame
    R.v, R.ang, R.u, R.th, R.thd = v, ang, u, th, -rate_l   # thd: rate in the th (= u) frame
    eng = g["eng"] & np.isfinite(v) & np.isfinite(u) & (g["cs_active"] > 0.5)
    w = int(0.5 * FS)
    press_buf = np.convolve((g["press"] > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0
    R.eng = eng; R.hoff = eng & ~press_buf
    R.des = g["des_curv"] * np.maximum(v, 0.1) ** 2      # planner desire, m/s^2 (controlsState.desiredCurvature)
    R.act = g["la_act"]
    R.sp = g["la_des"]                                     # what the PID saw (rev-3/4: after the reference filter)
    R.err = g["err"]; R.p = g["p"]; R.i = g["i"]; R.f = g["f"]; R.out = g["out"]
    R.roll = g["roll"]
    return R


def n0(R):
    P = R.P; g = R.g
    pr("\n" + "=" * 120)
    pr("N0. ATTRIBUTION  tag %s  route %s  %d segments" % (R.tag, g["meta"]["route"], len(g["meta"]["segments"])))
    for k in ("GitCommit", "GitBranch", "SteerFriction", "SteerFrictionStock", "AccordTorqueKi", "AccordTorqueKiHigh", "SteerKP",
              "SteerLatAccel", "AccordFrictionHyst", "AccordRateLoopGain", "AccordErrorNotchQ", "AccordRefFilter", "AccordHoldMap",
              "UseAutoSteerDelay", "SteerDelay", "KeepLearnedLatAccelOffset"):
        pr("    %-26s %s" % (k, str(P.get(k, "ABSENT"))[:60]))
    eng = R.eng
    q = eng & (np.abs(R.err) > 1e-3) & np.isfinite(R.p)
    kp = R.p[q] / R.err[q]
    q2 = eng & (np.abs(R.out) > 1e-3)
    laf = -(R.p[q2] + R.i[q2] + R.f[q2]) / R.out[q2]
    pr("    Kp = median p/err %.3f   LAF = median -(p+i+f)/out %.2f" % (np.median(kp), np.median(laf)))
    ld = R.g["ld_delay"]; ok = np.isfinite(ld)
    pr("    liveDelay median %.3f s (min %.3f max %.3f)" % (np.median(ld[ok]), ld[ok].min(), ld[ok].max()) if ok.any() else "    liveDelay: none")
    v = R.v
    pr("    engaged %.0f s, hands-off %.0f s;  by band: %s" % (eng.sum() * DT, R.hoff.sum() * DT,
       "  ".join("%s %.0f s" % (n, (R.hoff & (v >= lo) & (v < hi)).sum() * DT) for n, (lo, hi) in zip(IBN, IB))))


def n1(R):
    """damping: IV torque->angle transfer at 15-30 m/s vs the two model shapes."""
    pr("\nN1. DAMPING -- is there a 2 Hz mode?  joint-IO transfer torque -> angle (instrument z = planner desire), hands-off, v 15-30")
    v = R.v; m = R.hoff & (v >= 15) & (v < 30)
    segs = stretches(m, int(20 * FS))
    if not segs:
        pr("    no 20 s stretches"); return
    z = np.concatenate([signal.detrend(R.des[a:b]) for a, b in segs])
    u = np.concatenate([signal.detrend(R.u[a:b]) for a, b in segs])
    y = np.concatenate([signal.detrend(R.th[a:b]) for a, b in segs])
    f, H, czu, czy = L.iv_tf(z, u, y, nper=1024)
    fd, Hd, _, _ = L.iv_tf(u, u, y, nper=1024)     # direct (biased) for reference
    vmed = float(np.median(v[m]))
    a = float(R3.hold_slope(0.0, vmed))
    def model(bb):
        s = 1j * 2 * np.pi * f
        return 1.0 / (a + bb * s + J_ID * s ** 2)
    Hm1 = model(0.0006); Hm2 = model(float(np.interp(vmed, B_IDENT_BP, B_IDENT_V)))
    sel = (f >= 0.2) & (f <= 4.0)
    # normalise at 0.2-0.4 Hz
    ref = (f >= 0.2) & (f <= 0.4)
    k1 = np.median(np.abs(H[ref])); km1 = np.median(np.abs(Hm1[ref])); km2 = np.median(np.abs(Hm2[ref]))
    pr("    %d stretches, %.0f s, v med %.1f, a %.4f torque/deg; |H| normalised at 0.2-0.4 Hz (meas DC ~ %.1f deg/torque vs 1/a %.1f)"
       % (len(segs), len(z) / FS, vmed, a, k1, 1 / a))
    pr("    %6s | %8s %6s %6s | %8s %8s | %6s" % ("f Hz", "|H|meas", "coh zu", "coh zy", "b=.0006", "b=ident", "direct"))
    for fq in (0.25, 0.4, 0.6, 0.8, 1.0, 1.3, 1.6, 1.9, 2.2, 2.6, 3.0, 3.5):
        k = int(np.argmin(np.abs(f - fq)))
        pr("    %6.2f | %8.3f %6.2f %6.2f | %8.3f %8.3f | %6.3f" % (f[k], abs(H[k]) / k1, czu[k], czy[k], abs(Hm1[k]) / km1, abs(Hm2[k]) / km2, abs(Hd[k]) / k1))
    band = (f >= 1.5) & (f <= 2.6)
    pr("    peak |H| in 1.5-2.6 Hz / |H| at 0.3 Hz:  measured %.2f   model b=.0006 %.2f   model b=ident %.2f   (coh zy in band med %.2f)"
       % (np.max(np.abs(H[band])) / k1, np.max(np.abs(Hm1[band])) / km1, np.max(np.abs(Hm2[band])) / km2, np.median(czy[band])))
    # closed-loop planner -> actual |H| 1-3 Hz bump
    f2, H2, c2u, c2y = L.iv_tf(z, z, np.concatenate([signal.detrend(R.act[a:b]) for a, b in segs]), nper=1024)
    pr("    closed loop planner->actual |H|: " + "  ".join("%.1f Hz %.2f" % (fq, abs(H2[int(np.argmin(np.abs(f2 - fq)))])) for fq in (0.2, 0.5, 1.0, 1.5, 2.0, 2.5)))


def n2(R, ref=None):
    """stiction / breakaway events, hands-off."""
    pr("\nN2. STICTION / BREAKAWAY  (hands-off; dwell = |rate| < 0.5 deg/s for >= 0.3 s while |planner error| > 0.05 m/s^2; jump = |rate| > 4 deg/s within 0.3 s)")
    v = R.v; th = R.th; thd = R.thd; u = R.u
    e = R.des - R.act
    still = np.abs(thd) < 0.5
    pr("    %-6s | %6s %7s | %8s %8s %8s | %8s %8s | %8s %8s %8s" % ("band", "min", "ev/min", "dwell s", "du wind", "du/F.015", "jump deg", "jump/ask", "P@brk", "I@brk", "F@brk"))
    for n, (lo, hi) in zip(IBN, IB):
        m = R.hoff & (v >= lo) & (v < hi)
        mins = m.sum() * DT / 60.0
        if mins < 0.5:
            continue
        evs = []
        i = 0; N = len(th)
        while i < N:
            if m[i] and still[i] and abs(e[i]) > 0.05:
                j = i
                while j < N and still[j] and m[j]:
                    j += 1
                dur = (j - i) * DT
                if dur >= 0.3 and j < N:
                    k1 = min(N, j + int(0.3 / DT))
                    if k1 > j and np.max(np.abs(thd[j:k1])) > 4.0:
                        # wind-up: torque change over the dwell; jump: angle change over 0.5 s after breakaway
                        du = u[j - 1] - u[i]
                        k2 = min(N, j + int(0.5 / DT))
                        jump = th[k2 - 1] - th[j - 1]
                        # what the planner asked over the same dwell, in degrees (A per deg)
                        A = S.lat_accel_per_deg(max(v[i], 1.0), S.steer_ratio(10.0, 16.88))
                        ask = (R.des[j - 1] - R.act[i]) / A
                        evs.append((dur, du, jump, ask, R.p[j - 1], R.i[j - 1], R.f[j - 1]))
                i = j
            else:
                i += 1
        if not evs:
            pr("    %-6s | %6.1f %7.1f |" % (n, mins, 0.0)); continue
        E = np.array(evs)
        du_dir = np.abs(E[:, 1])
        pr("    %-6s | %6.1f %7.1f | %8.2f %8.4f %8.2f | %8.2f %8.2f | %8.3f %8.3f %8.3f"
           % (n, mins, len(evs) / mins, np.median(E[:, 0]), np.median(du_dir), np.median(du_dir) / 0.015,
              np.median(np.abs(E[:, 2])), np.median(np.abs(E[:, 2]) / np.maximum(np.abs(E[:, 3]), 0.05)),
              np.median(np.abs(E[:, 4])), np.median(np.abs(E[:, 5])), np.median(np.abs(E[:, 6]))))
    # rate roughness on hard turns (the operator's "jerky")
    pr("    hard turns (|planner| > 1.5 m/s^2 or |angle| > 60 deg): 0.5-5 Hz rate rms, |rate|>80 bursts/min, reversals/min, honda-cap frames")
    cmd = R.g["cmd"]
    for n, (lo, hi) in [("v<10", (0, 10)), ("10-20", (10, 20)), (">20", (20, 99))]:
        m = R.eng & (v >= lo) & (v < hi) & ((np.abs(R.des) > 1.5) | (np.abs(th) > 60))
        if m.sum() * DT < 5:
            continue
        rb = bp(np.nan_to_num(thd), 0.5, 5.0)
        step = np.abs(np.diff(np.nan_to_num(cmd), prepend=cmd[0]))
        bursts = np.sum(np.diff((np.abs(thd) > (80 if hi <= 10 else 40)).astype(int)[m] > 0)) / (m.sum() * DT / 60)
        sgn = np.sign(thd); rev = np.sum((np.diff(sgn) != 0)[m[1:]] & (np.abs(thd[1:]) > 2)[m[1:]]) / (m.sum() * DT / 60)
        pr("    %-6s %5.0f s | rate rms %5.1f deg/s | bursts %6.1f /min | reversals %6.1f /min | cap %.1f %%"
           % (n, m.sum() * DT, np.sqrt(np.mean(rb[m] ** 2)), bursts, rev, 100 * np.mean(step[m] >= 120)))


def n3(R):
    pr("\nN3. THE INTEGRATOR and the 0.2-1 Hz band  (hands-off curves |planner| > 0.3 m/s^2 at v > 15)")
    v = R.v
    for n, (lo, hi) in zip(IBN, IB):
        m = R.hoff & (v >= lo) & (v < hi)
        if m.sum() * DT < 20:
            continue
        tot = np.abs(R.p[m]) + np.abs(R.i[m]) + np.abs(R.f[m])
        pr("    %-6s | |i| share %.2f  |p| share %.2f  |f| share %.2f | rms i %.3f p %.3f f %.3f (lat-accel units)"
           % (n, np.mean(np.abs(R.i[m]) / np.maximum(tot, 1e-6)), np.mean(np.abs(R.p[m]) / np.maximum(tot, 1e-6)),
              np.mean(np.abs(R.f[m]) / np.maximum(tot, 1e-6)), np.sqrt(np.mean(R.i[m] ** 2)), np.sqrt(np.mean(R.p[m] ** 2)), np.sqrt(np.mean(R.f[m] ** 2))))
    m = R.hoff & (v > 15) & (np.abs(R.des) > 0.3)
    segs = stretches(m, int(8 * FS))
    if segs:
        e = np.concatenate([signal.detrend(R.des[a:b] - R.act[a:b]) for a, b in segs])
        ii = np.concatenate([signal.detrend(R.i[a:b]) for a, b in segs])
        f, Pe = signal.welch(e, fs=FS, nperseg=1024); _, Pi = signal.welch(ii, fs=FS, nperseg=1024)
        def band_rms(P, lo, hi):
            s = (f >= lo) & (f < hi); return math.sqrt(np.trapezoid(P[s], f[s]))
        pr("    curves > 15 m/s, %d stretches %.0f s: planner-error rms by band  <0.2 %.3f | 0.2-0.4 %.3f | 0.4-0.8 %.3f | 0.8-1.5 %.3f | >1.5 %.3f  m/s^2"
           % (len(segs), len(e) / FS, band_rms(Pe, 0.02, 0.2), band_rms(Pe, 0.2, 0.4), band_rms(Pe, 0.4, 0.8), band_rms(Pe, 0.8, 1.5), band_rms(Pe, 1.5, 10)))
        pr("    i-term rms by band                                 <0.2 %.3f | 0.2-0.4 %.3f | 0.4-0.8 %.3f | 0.8-1.5 %.3f"
           % (band_rms(Pi, 0.02, 0.2), band_rms(Pi, 0.2, 0.4), band_rms(Pi, 0.4, 0.8), band_rms(Pi, 0.8, 1.5)))
        k = np.argmax(Pe[(f > 0.2) & (f < 1.0)]); fpk = f[(f > 0.2) & (f < 1.0)][k]
        pr("    error spectrum peak in 0.2-1 Hz at %.2f Hz, %.1f dB above the 0.1-0.2 Hz median" % (fpk, 10 * np.log10(Pe[(f > 0.2) & (f < 1.0)][k] / np.median(Pe[(f > 0.1) & (f < 0.2)]))))


def n4(R):
    pr("\nN4. COMMAND-PROPORTIONAL FRICTION  residual r = u(t-Td) - [hold(th) + b_id th' + J th''] on hands-off stretches >= 4 s, 5 Hz LPF;")
    pr("    r ~ c0 + cF sign(th') + cU sign(th')|u| + cB th'|u| + cS hold(th)   (cU < 0 = the EPS adds torque along the motion in proportion to |u|)")
    v = R.v; th = R.th; thd = R.thd; u = R.u
    nd = int(round(TD / DT))
    for n, (lo, hi) in zip(IBN, IB):
        m = R.hoff & (v >= lo) & (v < hi)
        segs = stretches(m, int(4 * FS))
        if not segs:
            continue
        X = []; Y = []
        for a, b in segs:
            vv = float(np.median(v[a:b]))
            bb = float(np.interp(vv, B_IDENT_BP, B_IDENT_V))
            t_ = lp(th[a:b], 5.0); r_ = lp(thd[a:b], 5.0); acc = np.gradient(r_, DT)
            ud = np.roll(lp(u[a:b], 5.0), nd)[nd:]
            hold = np.array([R3.hold_torque(x, vv) for x in t_])[nd:]
            res = ud - (hold + bb * r_[nd:] + J_ID * acc[nd:])
            sg = np.tanh(r_[nd:] / 1.0)          # smooth sign, 1 deg/s
            X.append(np.column_stack([np.ones(len(res)), sg, sg * np.abs(ud), r_[nd:] * np.abs(ud), hold]))
            Y.append(res)
        X = np.vstack(X); Y = np.concatenate(Y)
        beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        yh = X @ beta
        # a second fit WITHOUT the |u| terms, for the F alone
        X0 = X[:, [0, 1, 4]]; b0, *_ = np.linalg.lstsq(X0, Y, rcond=None)
        pr("    %-6s n %6d | c0 %+.4f  F %+.4f  cU %+.4f  cB %+.5f  cS %+.3f | R2 %.3f | F-only fit: F %+.4f  cS %+.3f R2 %.3f | rms u %.3f, med |u| %.3f"
           % (n, len(Y), *beta, L.r2(Y, yh), b0[1], b0[2], L.r2(Y, X0 @ b0), np.sqrt(np.mean(X[:, 2] ** 2 / np.maximum(np.abs(X[:, 1]) ** 2, 1e-9))) if False else np.sqrt(np.mean((np.abs(X[:, 2]))**2)), np.median(np.abs(X[:, 2]))))


def n5(R):
    pr("\nN5. ROAD CROWN  low-frequency (0.5 Hz LPF) residual u - hold(th) vs roll, hands-off, still-ish (|rate| < 10 deg/s)")
    v = R.v
    for n, (lo, hi) in zip(IBN, IB):
        m = R.hoff & (v >= lo) & (v < hi) & (np.abs(R.thd) < 10)
        if m.sum() * DT < 20:
            continue
        vv = np.median(v[m])
        hold = np.array([R3.hold_torque(x, vv) for x in R.th[m]])
        res = R.u[m] - hold
        roll = R.roll[m]
        X = np.column_stack([np.ones(m.sum()), roll, hold])
        beta, *_ = np.linalg.lstsq(X, res, rcond=None)
        pr("    %-6s %5.0f s | roll med %+.2f deg (IQR %+.2f..%+.2f) | res = %+.4f %+.3f*roll(rad) %+.3f*hold | R2 %.2f | rms res %.4f -> after roll %.4f"
           % (n, m.sum() * DT, np.degrees(np.median(roll)), *np.degrees(np.percentile(roll, [25, 75])), *beta, L.r2(res, X @ beta),
              np.sqrt(np.mean(res ** 2)), np.sqrt(np.mean((res - X @ beta) ** 2))))


def n6(R):
    pr("\nN6. TRACKING vs THE PLANNER (hands-off, stretches >= 10 s): gain (lstsq act on des), lag (ncc), rms error, |H| coh at 0.2 Hz; error energy by band")
    v = R.v
    pr("    %-6s | %5s | %5s %6s %6s | %6s %6s | %s" % ("band", "s", "gain", "lag s", "rms e", "|H|.2", "coh.2", "error energy <0.3 / 0.3-1 / >1 Hz %"))
    for n, (lo, hi) in zip(IBN, IB):
        m = R.hoff & (v >= lo) & (v < hi)
        segs = stretches(m, int(10 * FS))
        if not segs:
            continue
        d = np.concatenate([signal.detrend(R.des[a:b]) for a, b in segs]); y = np.concatenate([signal.detrend(R.act[a:b]) for a, b in segs])
        e = d - y
        gain = float(np.dot(d, y) / max(np.dot(d, d), 1e-9))
        lag, _ = L.ncc_lag(d, y, lo=0.0, hi=1.0)
        f, Pdd, Pyy, Pdy, coh = L.welch_cross(d, y, nper=2048)
        H = np.abs(Pdy) / np.maximum(Pdd, 1e-30)
        k = int(np.argmin(np.abs(f - 0.2)))
        _, Pe = signal.welch(e, fs=FS, nperseg=2048)
        tot = np.trapezoid(Pe, f)
        def frac(lo_, hi_):
            s = (f >= lo_) & (f < hi_); return 100 * np.trapezoid(Pe[s], f[s]) / tot
        pr("    %-6s | %5.0f | %5.2f %6.2f %6.3f | %6.2f %6.2f | %4.0f / %4.0f / %4.0f"
           % (n, len(d) / FS, gain, lag, np.sqrt(np.mean(e ** 2)), H[k], coh[k], frac(0.02, 0.3), frac(0.3, 1.0), frac(1.0, 10)))


def main():
    tags = sys.argv[1:] or ["r75_v293r4", "r72_v293r3", "r73_v293r3"]
    for tag in tags:
        R = load(tag)
        n0(R); n1(R); n2(R); n3(R); n4(R); n5(R); n6(R)
    out = os.path.join(HERE, "V293-REV5-READ-%s-2026-09-15.txt" % "-".join(t.split("_")[0] for t in tags))
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)


if __name__ == "__main__":
    main()
