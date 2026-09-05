# -*- coding: utf-8 -*-
"""studies/osc-highangle/roll_adjudication_r3a3c.py -- IS MY SPEED-DEPENDENT 1/rho THE ROLL MODEL?

team-lead's adjudication: my measured 1/rho swings 0.927 -> 1.058 across speed on r39 (spread 0.131)
while tunepath, on the |angle| 1.5-48 deg near-centre stratum, gets 0.995 -> 1.037 (spread 0.042).
Same direction, 3x apart on size.  Candidate artefact: openpilot's roll compensation.

THE ARITHMETIC, from the flown vehicle_model.py (verified against my own reconstruction, which
reproduces the logged actualLateralAccel with TLS slope 0.99997 / r = 1.000000):

    m = -( cfac(v) * sa / sR_served  +  rollcomp ) * v^2
    rollcomp = (g * roll) / ((1/sf) - v^2),   sf = -6.9999e-4  =>  1/sf = -1428.6

  so the ROLL CONTRIBUTION TO THE MEASUREMENT is   Rm = -rollcomp * v^2 = g*roll*v^2 / (1428.6 + v^2),
  which for roll > 0 is POSITIVE and grows with speed:
       v      5      10      15      20      25      30   m/s
       Rm/roll  0.169   0.653   1.352   2.144   2.976   3.791   (m/s^2 per rad)
  i.e. x22 from 5 to 30 m/s, against a median |ask| that is roughly FLAT in speed (0.66 -> 0.63 on r39).

  ==> team-lead is RIGHT and my earlier sentence was WRONG: the roll term's FRACTIONAL weight is
      SMALLEST at low speed and LARGEST at high speed.  Corrected here, with the arithmetic.

CRITICAL STRUCTURE: Rm is an ADDITIVE OFFSET on a SIGNED measurement, not a scale.  Unfolded it
partly cancels between left and right turns.  It biases a ratio only through the part that CORRELATES
WITH TURN DIRECTION, i.e. through  mean(roll * sign(turn)), not through mean(roll).  Roads bank INTO
the curve, so that correlation is expected and is exactly what section 2 measures.

Tests (team-lead's numbering)
  1  1/rho by speed band with the roll term IN and OUT of the measurement, side by side
  2  mean(roll) vs mean(roll*sign(turn)) per band, and the implied multiplicative bias on 1/rho
  3  my estimator re-run on tunepath's |sa| 1.5-48 deg stratum -- do I recover 0.042 or 0.131?
  4  the folded-vs-unfolded question, stated explicitly

Run: python rlog-tools/studies/osc-highangle/roll_adjudication_r3a3c.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oversteer_v282_r3a3c as X  # noqa: E402
import sr_speed_split_r3a3c as S  # noqa: E402

M = X.M
FS = X.FS
G = 9.81
LINES = []
ALLT = ("r35", "r39", "r3c", "r3a")
NEW = ("r39", "r3c", "r3a")
VB = ((3, 7), (7, 11), (11, 16), (16, 22), (22, 30), (30, 40))


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def prep(t):
    g, cp = X.gof(t)
    s = S.stratum(g)
    # the roll contribution to the MEASUREMENT, in m/s^2, signed as it enters m
    Rm = -g["rollcomp"] * g["v"] ** 2
    # the measurement with the roll term removed, and the reconstruction check
    m_rec = -(g["cfac"] * g["sa"] / g["sr_map"] + g["rollcomp"]) * g["v"] ** 2
    m_nr = -(g["cfac"] * g["sa"] / g["sr_map"]) * g["v"] ** 2
    return g, s, Rm, m_rec, m_nr


def tls_ci(x, y, blk, n=1500, seed=13):
    return S.tls_ci(x, y, blk, n=n, seed=seed)


def turn_sign(g):
    """Direction of the manoeuvre, from the ROAD (yaw), so it carries no model and no roll."""
    return np.sign(g["vyaw"])


def main():
    pr("=" * 176)
    pr("SECTION 0 -- THE RECONSTRUCTION IS FAITHFUL, so 'roll removed' means what it says.")
    pr("  TLS of the logged actualLateralAccel on my reconstruction -(cfac*sa/sR_map + rollcomp)*v^2.")
    pr("  1.000 means I can legitimately rebuild the measurement with the roll term deleted.")
    pr("=" * 176)
    P = {}
    for t in ALLT:
        g, s, Rm, m_rec, m_nr = prep(t)
        P[t] = (g, s, Rm, m_rec, m_nr)
        ok = s & np.isfinite(m_rec) & np.isfinite(g["actualLateralAccel"])
        b, l, h, n = tls_ci(m_rec[ok], g["actualLateralAccel"][ok], (g["t"][ok] / 10.0).astype(int))
        pr("  %-5s slope %.5f [%.5f, %.5f]   resid sd %.4f m/s^2   n %.0f s" % (
            t, b, l, h, float(np.std(g["actualLateralAccel"][ok] - m_rec[ok])), ok.sum() / FS))

    pr()
    pr("=" * 176)
    pr("TEST 1 -- 1/rho BY SPEED BAND, ROLL TERM IN vs OUT OF THE MEASUREMENT.")
    pr("  'IN'  = the logged actualLateralAccel (what the controller acted on).  This is my published table.")
    pr("  'OUT' = -(cfac*sa/sR_map)*v^2, the same measurement with the roll compensation deleted.")
    pr("  Both are TLS of the measurement on the road (v*yaw_cal), through the origin, 10 s block bootstrap.")
    pr("  If the spread collapses when the roll term is removed, my sign flip is largely the roll model.")
    pr("=" * 176)
    pr("  %-5s %-12s %8s %-24s %-24s %10s" % (
        "route", "v band", "secs", "1/rho  ROLL IN", "1/rho  ROLL OUT", "difference"))
    SPREAD = {}
    for t in NEW:
        g, s, Rm, m_rec, m_nr = P[t]
        ins, outs = [], []
        for lo, hi in VB:
            sel = s & (g["v"] >= lo) & (g["v"] < hi) & (np.abs(g["vyaw"]) > 0.3) & np.isfinite(m_nr)
            if sel.sum() < 300:
                continue
            blk = (g["t"][sel] / 10.0).astype(int)
            a1, l1, h1, _ = tls_ci(g["vyaw"][sel], g["actualLateralAccel"][sel], blk)
            a2, l2, h2, _ = tls_ci(g["vyaw"][sel], m_nr[sel], blk)
            i1, i2 = 1.0 / a1, 1.0 / a2
            ins.append(i1)
            outs.append(i2)
            pr("  %-5s %-12s %8.0f %8.3f [%.3f, %.3f]  %8.3f [%.3f, %.3f]  %10.3f" % (
                t, "%g-%g m/s" % (lo, hi), sel.sum() / FS, i1, 1 / h1, 1 / l1, i2, 1 / h2, 1 / l2, i2 - i1))
        if len(ins) >= 3:
            SPREAD[t] = (max(ins) - min(ins), max(outs) - min(outs))
            pr("  %-5s %-12s SPREAD across bands:  ROLL IN %.3f   ROLL OUT %.3f   -> %.0f %% of the spread %s" % (
                t, "", SPREAD[t][0], SPREAD[t][1], 100.0 * SPREAD[t][1] / SPREAD[t][0],
                "SURVIVES" if SPREAD[t][1] > 0.5 * SPREAD[t][0] else "COLLAPSES"))
        pr()

    pr("=" * 176)
    pr("TEST 2 -- THE ROLL SIGNAL ITSELF, AND THE ONLY PART OF IT THAT CAN BIAS A RATIO.")
    pr("  Rm = -rollcomp*v^2 = the roll term's contribution to the measurement, m/s^2.")
    pr("  UNFOLDED mean(Rm) is an offset on a signed quantity and largely cancels between L and R turns.")
    pr("  FOLDED mean(Rm*sign(turn)) is the part that acts like a SCALE and biases 1/rho by")
    pr("      bias factor = 1 / (1 + folded Rm / folded m_nr).")
    pr("  turn sign is taken from the ROAD (sign of v*yaw_cal) so it carries no model and no roll.")
    pr("=" * 176)
    pr("  %-5s %-12s %8s %11s %13s %11s %13s %12s %12s" % (
        "route", "v band", "secs", "mean roll", "mean roll*sgn", "mean Rm", "folded Rm", "folded m_nr", "bias factor"))
    for t in NEW:
        g, s, Rm, m_rec, m_nr = P[t]
        for lo, hi in VB:
            sel = s & (g["v"] >= lo) & (g["v"] < hi) & (np.abs(g["vyaw"]) > 0.3) & np.isfinite(m_nr)
            if sel.sum() < 300:
                continue
            d = turn_sign(g)[sel]
            fr = float(np.mean(Rm[sel] * d))
            fm = float(np.mean(m_nr[sel] * d))
            pr("  %-5s %-12s %8.0f %11.4f %13.4f %11.4f %13.4f %12.4f %12.4f" % (
                t, "%g-%g m/s" % (lo, hi), sel.sum() / FS,
                float(np.mean(g["proll"][sel])), float(np.mean(g["proll"][sel] * d)),
                float(np.mean(Rm[sel])), fr, fm, 1.0 / (1.0 + fr / fm) if fm else np.nan))
        pr()
    pr("  ROUTE-WIDE mean(liveParameters.roll), engaged: " + " | ".join(
        "%s %+.4f rad" % (t, float(np.mean(P[t][0]["proll"][P[t][1]]))) for t in ALLT))

    pr()
    pr("=" * 176)
    pr("TEST 3 -- MY ESTIMATOR ON tunepath's STRATUM.  Restrict to |sa| 1.5-48 deg (the near-centre band,")
    pr("  below the SR map's first breakpoint, so the map serves a flat 16.00 throughout).  tunepath reports")
    pr("  0.995 / 1.021 / 1.031 / 1.016 / 1.037, spread 0.042.  Do I recover that, or my 0.131?")
    pr("=" * 176)
    pr("  %-5s %-12s %8s %-24s %-24s %12s" % (
        "route", "v band", "secs", "1/rho  (my stratum)", "1/rho  (|sa| 1.5-48)", "med |sa|"))
    for t in NEW:
        g, s, Rm, m_rec, m_nr = P[t]
        mine, tp = [], []
        for lo, hi in VB:
            base = s & (g["v"] >= lo) & (g["v"] < hi) & (np.abs(g["vyaw"]) > 0.3)
            narrow = base & (np.abs(g["sa_deg"]) >= 1.5) & (np.abs(g["sa_deg"]) < 48.0)
            c = []
            for sel in (base, narrow):
                if sel.sum() < 300:
                    c.append(None)
                    continue
                a, l, h, _ = tls_ci(g["vyaw"][sel], g["actualLateralAccel"][sel], (g["t"][sel] / 10.0).astype(int))
                c.append((1.0 / a, 1.0 / h, 1.0 / l, sel.sum() / FS))
            if c[0]:
                mine.append(c[0][0])
            if c[1]:
                tp.append(c[1][0])
            pr("  %-5s %-12s %8s %-24s %-24s %12.0f" % (
                t, "%g-%g m/s" % (lo, hi), "%.0f" % (base.sum() / FS),
                "--" if not c[0] else "%.3f [%.3f, %.3f]" % c[0][:3],
                "--" if not c[1] else "%.3f [%.3f, %.3f] %.0fs" % c[1],
                X.med(np.abs(g["sa_deg"][base])) if base.sum() else np.nan))
        if len(mine) >= 3 and len(tp) >= 3:
            pr("  %-5s SPREAD: my stratum %.3f   |sa| 1.5-48 stratum %.3f" % (t, max(mine) - min(mine), max(tp) - min(tp)))
        pr()

    pr("=" * 176)
    pr("TEST 4 -- WAS MY STATISTIC FOLDED?  STATED EXPLICITLY: NO.")
    pr("  My published 1/rho is an UNFOLDED TLS of the measurement on the road, through the origin, over")
    pr("  frames of BOTH turn directions.  A pure offset therefore partly self-cancels in it; a")
    pr("  direction-CORRELATED offset does not.  Here it is computed BOTH ways, so the difference is visible.")
    pr("=" * 176)
    pr("  %-5s %-12s %8s %12s %12s %12s %10s %10s" % (
        "route", "v band", "secs", "1/rho unfold", "1/rho FOLDED", "roll-out fold", "L secs", "R secs"))
    for t in NEW:
        g, s, Rm, m_rec, m_nr = P[t]
        for lo, hi in VB:
            sel = s & (g["v"] >= lo) & (g["v"] < hi) & (np.abs(g["vyaw"]) > 0.3) & np.isfinite(m_nr)
            if sel.sum() < 300:
                continue
            d = turn_sign(g)[sel]
            blk = (g["t"][sel] / 10.0).astype(int)
            a0, *_ = tls_ci(g["vyaw"][sel], g["actualLateralAccel"][sel], blk)
            a1, *_ = tls_ci(g["vyaw"][sel] * d, g["actualLateralAccel"][sel] * d, blk)
            a2, *_ = tls_ci(g["vyaw"][sel] * d, m_nr[sel] * d, blk)
            pr("  %-5s %-12s %8.0f %12.3f %12.3f %12.3f %10.0f %10.0f" % (
                t, "%g-%g m/s" % (lo, hi), sel.sum() / FS, 1 / a0, 1 / a1, 1 / a2,
                (d > 0).sum() / FS, (d < 0).sum() / FS))
        pr()

    out = os.path.join(HERE, "_scratch", "roll_adjudication_r3a3c.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES))
    pr("wrote %s" % out)


if __name__ == "__main__":
    main()
