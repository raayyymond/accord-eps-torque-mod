# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v282_r39_supp.py -- the three supplementary reads that decide
Q1 and Q2 in OVERSTEER-V282-r39-2026-09-04.md.  Companion to oversteer_v282_r39.py (imported, so
every stratum, bias correction and curve definition is literally the same object).

  H  the excess expressed as LATERAL ACCEL, as a RATIO, and as a YAW RATE -- the last is the one the
     driver feels as "the car rotated too much", and it is the only one with a 20 mph maximum.
  I  the curve/straight balance of the outer integrator: WHY R_m > 1 in curves on every arm, and why
     that term is NOT what changed between r35 and r39.
  J  the operator's own bookmarks, aligned onto the analysis clock.

Run: python rlog-tools/studies/osc-highangle/oversteer_v282_r39_supp.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                                "analysis-2020accord", "studies", "optune"))
import oversteer_v282_r39 as M  # noqa: E402
import backcalc_laf_friction as B  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = M.FS
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def steady_masks(g, rows):
    des = g["desiredLateralAccel"]
    stm = np.zeros(len(des), bool)
    dirf = np.zeros(len(des))
    for r in rows:
        stm[r["a"] + 150:r["b"]] = True
        dirf[r["a"]:r["b"]] = r["dir"]
    return stm, dirf


def dilate(m, sec):
    n = int(sec * FS)
    return np.convolve(m.astype(int), np.ones(2 * n + 1, int), "same") > 0


def sectionK():
    """K -- ROBUSTNESS: the override confound, and the ratio-free shape statistic.
    Added 2026-09-04 after team-lead flagged 238 steerOverride events and asked for an SR-free Q1 test."""
    pr("")
    pr("=" * 150)
    pr("SECTION K -- ROBUSTNESS OF THE Q1 ANSWER")
    pr("  K.1 the OVERRIDE confound.  The base stratum already drops carState.steeringPressed; here it is re-run with a")
    pr("      +-2 s GUARD BAND around every pressed frame, and separately with a |driver torque| < 200 raw cut.")
    pr("=" * 150)
    pr("  %-5s %-24s %7s %7s %11s %10s %10s" % ("route", "variant", "curves", "secs", "steady os", "R_vyaw", "frac over"))
    for t in M.TAGS:
        g, _ = M.gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        guard = dilate(g["pressed"] > 0.5, 2.0)
        quiet = np.abs(g["drv"]) < 200
        base = M.curve_mask(g)
        lat = (g["lat"] > 0.5) & (g["active"] > 0.5)          # WITHOUT the pressed exclusion
        for nm, extra in (("base (pressed excl.)", np.ones(len(des), bool)),
                          ("+ 2 s guard band", ~guard),
                          ("+ |drv| < 200", quiet),
                          ("+ both", (~guard) & quiet)):
            runs = M.merge_runs(base & extra & (np.abs(des) > M.DES_THR), int(1.5 * FS), int(0.3 * FS))
            os_, R_ = [], []
            for a, b in runs:
                if b - a < int(2.5 * FS):
                    continue
                d = np.sign(np.median(des[a:b])) or 1.0
                sl = slice(a + 150, b)
                big = np.abs(des[sl]) > 0.5
                os_.append(M.med((g["vyaw"][sl] - des[sl]) * d - sb["vyaw"] * d))
                if big.sum() > 10:
                    R_.append(M.med((g["vyaw"][sl][big] - sb["vyaw"]) / des[sl][big]))
            pr("  %-5s %-24s %7d %7.0f %+11.3f %10.3f %10.2f" % (
                t, nm, len(os_), sum(b - a for a, b in runs) / FS, M.med(os_), M.med(R_),
                float(np.mean(np.array(os_) > 0)) if os_ else np.nan))
        pr("        steeringPressed duty over LATERALLY ENGAGED time (before the exclusion): %.4f = %.1f s of %.0f s"
           % (float(np.mean((g["pressed"] > 0.5)[lat])), float((g["pressed"] > 0.5)[lat].sum() / FS), lat.sum() / FS))

    pr("")
    pr("  K.2 THE RATIO-FREE SHAPE STATISTIC (team-lead's suggestion): peak / settled of the ACHIEVED channel against")
    pr("      its OWN final value.  No ask, no ratio, no vehicle model anywhere in it, so the steering ratio divides out.")
    pr("      >> 1 and decaying = TRANSIENT OVERSHOOT.  ~ 1 = the whole trace is displaced = EQUILIBRIUM SCALE ERROR.")
    pr("      Curves >= 4 s with |des| > 0.4; peak taken over the first 2.5 s, settled = median from 2.5 s on.")
    pr("      %-5s %8s %13s %10s %10s %12s" % ("route", "n", "peak/settled", "p25", "p75", "t_peak (s)"))
    for t in M.TAGS:
        g, _ = M.gof(t)
        sb = M.straight_bias(g)
        rows = [r for r in M.curves(t)[0] if r["dur"] >= 4.0 and r["des"] > 0.4]
        rat, tpk = [], []
        for r in rows:
            ach = (g["vyaw"][r["a"]:r["b"]] - sb["vyaw"]) * r["dir"]
            settled = np.nanmedian(ach[int(2.5 * FS):])
            if not np.isfinite(settled) or settled < 0.3:
                continue
            w = ach[:int(2.5 * FS)]
            rat.append(float(np.nanmax(w)) / settled)
            tpk.append(float(np.nanargmax(w)) / FS)
        pr("      %-5s %8d %13.3f %10.3f %10.3f %12.2f" % (
            t, len(rat), M.med(rat), np.percentile(rat, 25), np.percentile(rat, 75), M.med(tpk)))
    pr("      => r39 1.171 and r35 1.173 are the SAME to 0.2 %: the transient SHAPE did not change between the drives,")
    pr("         while the LEVEL moved from R 0.923 to 1.116.  That is 'the whole trace is displaced', on a statistic")
    pr("         with no ratio in it.  (Per-curve spread is wide and t_peak is late, so read the r39-vs-r35 CONTRAST,")
    pr("         which is like-for-like, not the absolute value of either.)")


def main():
    C = {t: M.curves(t)[0] for t in M.TAGS}

    pr("=" * 150)
    pr("SECTION H -- Q2: THE SAME EXCESS, EXPRESSED THREE WAYS.  Curve-steady, direction-folded, bias-corrected.")
    pr("  os m/s^2 = achieved - asked lateral accel (SR-free).  R = achieved / asked.")
    pr("  os deg/s = os / v, i.e. the EXCESS YAW RATE -- what 'the car rotated more than I wanted' actually is.")
    pr("  os deg(2s) = the heading error that excess builds in two seconds.")
    pr("=" * 150)
    pr("  %-5s %-12s %7s %9s %11s %9s %11s %12s" % (
        "route", "v bin", "secs", "|des|", "os m/s^2", "R", "os deg/s", "os deg (2 s)"))
    for t in M.TAGS:
        g, _ = M.gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        stm, dirf = steady_masks(g, C[t])
        for lo, hi in ((0, 7), (7, 11), (11, 16), (16, 22), (22, 40)):
            s = stm & (g["v"] >= lo) & (g["v"] < hi)
            if s.sum() < 200:
                continue
            d = dirf[s]
            os_a = M.med((g["vyaw"][s] - des[s]) * d - sb["vyaw"] * d)
            big = np.abs(des[s]) > 0.5
            R = M.med((g["vyaw"][s][big] - sb["vyaw"]) / des[s][big]) if big.sum() > 20 else np.nan
            os_w = np.degrees(os_a / M.med(g["v"][s]))
            pr("  %-5s %-12s %7.0f %9.2f %+11.3f %9.3f %+11.2f %+12.2f" % (
                t, "%g-%g m/s" % (lo, hi), s.sum() / FS, M.med(np.abs(des[s])), os_a, R, os_w, os_w * 2))
    pr("  => the LATERAL-ACCEL excess is ~flat in speed (+0.08 to +0.16 on r39); the YAW-RATE excess is 2.5-3.7x")
    pr("     larger below 11 m/s than above 16.  r35's row is the same magnitude with the sign flipped.")

    pr()
    pr("=" * 150)
    pr("SECTION I -- WHY R_m > 1 IN CURVES ON EVERY ARM, and why that term is not the r35 -> r39 delta")
    pr("  error = pid_log.error = error_with_lsf = (setpoint - measurement) * (1 + lsf/kp).  The integrator zeroes its")
    pr("  TIME INTEGRAL over the whole drive, not within a stratum.  Folded on the curve direction:")
    pr("=" * 150)
    pr("  %-5s | %12s %8s | %12s %8s | %10s %10s | %9s" % (
        "route", "curve err", "secs", "straight err", "secs", "curve i", "straight i", "frozen"))
    for t in M.TAGS:
        g, _ = M.gof(t)
        des = g["desiredLateralAccel"]
        stm, dirf = steady_masks(g, C[t])
        ok = M.curve_mask(g)
        st = ok & (np.abs(des) < 0.2) & (g["v"] > 10)
        sgn = np.sign(g["f"])
        frz = ok & ((g["pressed"] > 0.5) | (g["v"] < 3.0) | (g["saturated"] > 0.5))
        pr("  %-5s | %+12.4f %8.0f | %+12.4f %8.0f | %+10.4f %+10.4f | %9.3f" % (
            t, float(np.nanmean(g["error"][stm] * dirf[stm])), stm.sum() / FS,
            float(np.nanmean(g["error"][st] * sgn[st])), st.sum() / FS,
            float(np.nanmean(g["i"][stm] * dirf[stm])), float(np.nanmean(g["i"][st] * sgn[st])),
            float(frz.sum() / max(ok.sum(), 1))))
    pr("  => a standing NEGATIVE folded error in curves (-0.41 to -0.49) on ALL THREE arms, against ~-0.03..-0.08 on")
    pr("     straights.  The loop always sits above its own setpoint inside a curve and pays it back on the straight.")
    pr("     That is the R_m ~ 1.09-1.18 term.  It is present at kp 0.6 and at kp 0.8, at SR 12.5 and under the map,")
    pr("     so it is NOT what changed on r39 -- and no tune move in this session's reach was shown to touch it.")

    pr()
    pr("  I.1 R_m / R_road / 1/rho by SPEED (tight curves only) -- where the map over- and under-corrects:")
    pr("      %-5s %-10s %7s %9s %9s %9s %10s" % ("route", "v bin", "secs", "R_m", "R_road", "1/rho", "SR served"))
    for t in ("r35", "r39"):
        g, _ = M.gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        stm, dirf = steady_masks(g, C[t])
        for lo, hi in ((0, 10), (10, 20), (20, 40)):
            s = stm & (g["v"] >= lo) & (g["v"] < hi) & (np.abs(des) > 0.5)
            if s.sum() < 200:
                continue
            m_ = g["actualLateralAccel"][s] - sb["m"]
            rd = g["vyaw"][s] - sb["vyaw"]
            pr("      %-5s %-10s %7.0f %9.3f %9.3f %9.3f %10.2f" % (
                t, "%g-%g m/s" % (lo, hi), s.sum() / FS, M.med(m_ / des[s]), M.med(rd / des[s]),
                M.med(rd / m_), M.med(g["sr_map"][s])))

    pr()
    pr("=" * 150)
    pr("SECTION J -- THE OPERATOR'S OWN BOOKMARKS ('userBookmark' events), aligned onto the analysis clock")
    pr("  He said he pressed them A LITTLE AFTER the event, so read the 6 s BEFORE each mark.")
    pr("=" * 150)
    D = B.load("r39")
    co0 = float(D["co_t"][0])
    mono0 = 26.279753999          # first logMonoTime of segment 0 (the clock the bookmark scan used)
    off = mono0 - co0
    g, _ = M.gof("r39")
    pr("  clock offset: grid_t = rlog_t %+0.3f s" % off)
    for bt in (689.63, 927.67):
        gt = bt + off
        j = int(np.clip(gt * FS, 0, len(g["t"]) - 1))
        w = slice(max(0, j - int(6 * FS)), j)
        pr("  rlog t %8.2f -> grid t %8.2f | at the mark: v %5.1f m/s, |ang| %4.0f deg, latActive %d" % (
            bt, gt, g["v"][j], abs(g["ang"][j]), g["lat"][j] > 0.5))
        pr("      the 6 s before: v p50 %5.1f m/s, max |ang| %4.0f deg, max |des| %5.2f m/s^2, latActive duty %.2f" % (
            M.med(g["v"][w]), float(np.abs(g["ang"][w]).max()), float(np.abs(g["desiredLateralAccel"][w]).max()),
            float(np.mean(g["lat"][w] > 0.5))))
        for r in C["r39"]:
            if r["t0"] - 8 <= gt <= r["t0"] + r["dur"] + 3:
                pr("      overlapping curve: t0 %.1f dur %.1f v %.1f |ang| %.0f |des| %.2f  steady os %+.3f  R %.3f" % (
                    r["t0"], r["dur"], r["v"], r["ang"], r["des"], r["steady_os_vyaw"], r["steady_R_vyaw"]))

    sectionK()

    out = os.path.join(HERE, "_scratch", "oversteer_v282_r39_supp.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES))
    pr("\nwrote %s" % out)


if __name__ == "__main__":
    main()
