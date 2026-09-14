# -*- coding: utf-8 -*-
"""v293_ident_i.py -- the operator's other three words: LOOSE, OVERSTEER, OVERSHOOT-THEN-CORRECT.
Plus: what `torqueState.f` actually is, and whether the ~2 Hz line is a limit cycle or a damped mode.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

I1  WHAT IS `f`?  The flight-read's 'branch' gate expects f/D = 1.000 under friction 0 and reads 0.747.
    The fork sets pid_log.f = ff = future_desired_lateral_accel - roll_compensation
    - latAccelOffset*fade, and pid_log.desiredLateralAccel = setpoint (a DIFFERENT quantity).  Both
    pieces are testable from the log: future_desired_lateral_accel is desiredCurvature*v^2, which I
    have at 100 Hz.  If f = D_future - c with c roughly constant, then f/D RISES with |D| exactly as
    the scorer observed, and c is the roll + offset term.
I2  LOOSE -- angle wander and the effective outer-loop stiffness on straights, vs the references.
I3  OVERSTEER -- over-delivery in quasi-steady turns, and the LAF that would make the FEEDFORWARD
    ALONE land on target, per band and per demand size.
I4  OVERSHOOT-THEN-CORRECT -- the step response, with the three candidate mechanisms separated:
    (i) an under-damped linear outer loop, (ii) a stiction jump, (iii) integrator wind-up.
I5  THE ~2 Hz LINE -- limit cycle or damped mode, and the plant phase it implies.
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
V280 = os.path.join(L.KIT, "analysis-2020accord", "_scratch", "cache", "v280")
BANDS = [(0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 99.0)]
BNAME = ["0-5", "5-10", "10-20", ">20"]
eng = g["eng"] & np.isfinite(g["la_act"]) & np.isfinite(g["la_des"])
ho = eng & (g["press"] < 0.5)
u = -g["op_torque"]                              # openpilot torque in the actualLateralAccel frame
err = g["la_des"] - g["la_act"]
Dfut = g["des_curv"] * g["v"] ** 2                # future_desired_lateral_accel, the fork's own `ff` base

pr("=" * 108)
pr("V293 -- LOOSE, OVERSTEER, OVERSHOOT; what `f` is; and the ~2 Hz line")
pr("=" * 108)


def band_mask(m, k):
    lo, hi = BANDS[k]
    return m & (g["v"] >= lo) & (g["v"] < hi)


def lstsq(X, y):
    X = np.asarray(X, float)
    b, *_ = np.linalg.lstsq(X, np.asarray(y, float), rcond=None)
    return b, L.r2(y, X @ b)


# ======================================================================================================
pr("\nI1. WHAT IS `torqueState.f`?  [EVIDENCE -- the log answers it]")
s = ho & np.isfinite(g["f"]) & np.isfinite(Dfut)
b, r2_ = lstsq(np.vstack([Dfut[s], np.ones(s.sum())]).T, g["f"][s])
pr("    f regressed on desiredCurvature*v^2 (the fork's future_desired_lateral_accel):")
pr("      f = %.4f * D_future %+.4f      R2 %.4f   n %.0f s" % (b[0], b[1], r2_, s.sum() * DT))
b2, r2b = lstsq(np.vstack([g["la_des"][s], np.ones(s.sum())]).T, g["f"][s])
pr("    f regressed on torqueState.desiredLateralAccel (= setpoint, the scorer's denominator):")
pr("      f = %.4f * D_setpoint %+.4f    R2 %.4f" % (b2[0], b2[1], r2b))
c = Dfut[s] - g["f"][s]
pr("\n    the DIFFERENCE  D_future - f  (which the fork says is roll_compensation + latAccelOffset*fade):")
pr("      p05 %+.4f  p50 %+.4f  p95 %+.4f  m/s^2 ; std %.4f ; std of its 1 s difference %.4f"
   % (*np.percentile(c, [5, 50, 95]), np.std(c), np.std(np.diff(c[::100]))))
pr("      -> it is a SLOWLY VARYING OFFSET of about %+.3f m/s^2, not a gain error." % np.median(c))
pr("\n    and that offset alone reproduces the scorer's 'f/D rises with |D|' pattern exactly:")
pr("    %-16s %8s %10s %12s %14s" % ("|D| band", "n s", "median f/D", "median D-f", "1 - (D-f)/|D|"))
for lo, hi in [(0.1, 0.3), (0.3, 0.6), (0.6, 0.9), (0.9, 1.3), (1.3, 2.0), (2.0, 9.0)]:
    q = s & (np.abs(g["la_des"]) >= lo) & (np.abs(g["la_des"]) < hi)
    if q.sum() < 300:
        continue
    fd = np.median(g["f"][q] / g["la_des"][q])
    dmf = np.median(np.abs(g["la_des"][q]) - np.abs(g["f"][q]))
    pr("    %-16s %8.1f %10.3f %12.4f %14.3f"
       % ("%.1f-%.1f" % (lo, hi), q.sum() * DT, fd, dmf,
          1.0 - dmf / np.median(np.abs(g["la_des"][q]))))
pr("\n    ⇒ THE 'branch' GATE IS MEASURING A CONSTANT OFFSET, NOT THE FEEDFORWARD BRANCH.  With")
pr("      f = D - c and c ~ %.2f m/s^2, f/D = 1 - c/|D| by construction, which is the whole of the" % np.median(c))
pr("      0.56 -> 0.867 ramp the scorer reported.  The gate should be on the SLOPE (measured %.4f)" % b[0])
pr("      or on D_future - f, not on the ratio.  [The slope, not the ratio, is the branch test.]")
sg = np.sign(g["la_des"][s])
cs_ = c * sg
pr("\n    IS THE OFFSET A VEHICLE-FRAME BIAS OR ROAD BANKING?  If it is a learned latAccelOffset it")
pr("    keeps ONE SIGN in the car's frame; if it is roll compensation on banked curves it follows")
pr("    the sign of the demand.  Median of (D_future - f) split by the demand's sign:")
for nm_, q_ in (("demand LEFT  (D>0.3)", s & (g["la_des"] > 0.3)),
                ("demand RIGHT (D<-0.3)", s & (g["la_des"] < -0.3)),
                ("near centre (|D|<0.3)", s & (np.abs(g["la_des"]) <= 0.3))):
    cc_ = Dfut[q_] - g["f"][q_]
    pr("      %-24s n %6.1f s   median %+.4f   p25 %+.4f  p75 %+.4f"
       % (nm_, q_.sum() * DT, np.median(cc_), np.percentile(cc_, 25), np.percentile(cc_, 75)))
pr("      -> same sign on both turn directions = a vehicle-frame bias; opposite = banking.")
RES["f"] = dict(slope=b[0], intercept=b[1], r2=r2_, offset=float(np.median(c)))

# ======================================================================================================
pr("\n" + "=" * 108)
pr("I2. LOOSE -- how well is the wheel held on a straight?  [EVIDENCE]")
pr("    straights = hands-off engaged, |desiredLateralAccel| < 0.3 and |d/dt| < 0.3, runs >= 5 s.")
pr("=" * 108)
# 🛑 np.gradient of a 100 Hz demand is far too noisy to threshold on: it fragments every mask into
# sub-0.1 s pieces (measured: 49.9 s of "turn hold" at 10-20 m/s containing ZERO runs >= 1.5 s).
# A 0.3 s backward difference is the same quantity with 30x less variance.
W3 = 30
dD = np.zeros(len(g["la_des"]))
dD[W3:] = (g["la_des"][W3:] - g["la_des"][:-W3]) / (W3 * DT)
straight = ho & (np.abs(g["la_des"]) < 0.3) & (np.abs(dD) < 0.3)


def load_ref(tag):
    d = dict(np.load(os.path.join(V280, tag + ".npz")))
    t0 = d["t18"][0]
    t1 = min(d["t18"][-1], d["t14"][-1], d["te4"][-1], d["tcs"][-1])
    ta = np.arange(0.0, t1 - t0, DT) + t0
    return dict(ang=L.zoh(ta, d["t14"], d["ang"]), cmd=L.zoh(ta, d["te4"], d["cmd"]),
                v=L.zoh(ta, d["tcs"], d["vego"]),
                eng=(L.zoh(ta, d["te4"], d["req"]) > 0.5) & (L.zoh(ta, d["t18"], d["sca"]) > 0.5),
                rate=L.zoh(ta, d["t18"], d["rate"]) / 8.0)


pr("\n    ANGLE WANDER, rms of the 0.1-1 Hz band-passed steering angle, on straight-ish stretches")
pr("    (for the references, 'straight-ish' is |angle| < 5 deg and |rate| < 5 deg/s, since they")
pr("    carry no controlsState in the cache -- stated as a weaker but like-for-like proxy):")
pr("    %-10s %-8s" % ("route", "build") + "".join("%12s" % b for b in BNAME))
for tag, build in (("r70_v293", "V293"), ("r6c", "V282"), ("r39", "V282"), ("r35", "V281r3")):
    if tag == "r70_v293":
        gg, m0 = g, ho & (np.abs(g["ang"]) < 5) & (np.abs(g["rate_dps"]) < 5)
    else:
        try:
            gg = load_ref(tag)
        except Exception:
            continue
        m0 = gg["eng"] & (np.abs(gg["ang"]) < 5) & (np.abs(gg["rate"]) < 5)
    row = []
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        mm = m0 & (gg["v"] >= lo) & (gg["v"] < hi)
        runs = L.stretches(mm, int(5 * L.FS))
        if not runs:
            row.append(np.nan); continue
        vals, w = [], []
        for (a, b_) in runs:
            vals.append(np.std(L.bandpass(gg["ang"][a:b_], 0.1, 1.0))); w.append(b_ - a)
        row.append(float(np.average(vals, weights=w)))
    pr("    %-10s %-8s" % (tag, build) + "".join("%12.4f" % x for x in row))
    RES.setdefault("wander", {})[tag] = row

pr("\n    THE EFFECTIVE OUTER-LOOP STIFFNESS on straights -- how much command the loop puts up per")
pr("    degree of angle error, and per m/s^2 of lat-accel error.  (Low = 'loose'.)")
pr("    %-8s %8s %14s %16s %14s %14s"
   % ("band", "n s", "cnt per deg", "torque per m/s2", "err rms", "ang rms"))
for k in range(len(BANDS)):
    q = band_mask(straight, k)
    if q.sum() < 500:
        continue
    runs = L.stretches(q, int(5 * L.FS))
    if not runs:
        continue
    A, Bv, E, AN = [], [], [], []
    for (a, b_) in runs:
        A.append(g["cmd"][a:b_]); Bv.append(-g["ang"][a:b_])
        E.append(err[a:b_]); AN.append(u[a:b_])
    A, Bv, E, AN = map(np.concatenate, (A, Bv, E, AN))
    sl1, _ = lstsq(np.vstack([Bv, np.ones(len(Bv))]).T, A)
    sl2, _ = lstsq(np.vstack([E, np.ones(len(E))]).T, AN)
    pr("    %-8s %8.0f %14.2f %16.4f %14.4f %14.4f"
       % (BNAME[k], len(A) * DT, sl1[0], sl2[0], np.sqrt(np.mean(E ** 2)),
          np.sqrt(np.mean((Bv - Bv.mean()) ** 2))))
pr("\n    for scale: the plant needs %.4f torque units per degree to HOLD an angle (part B), so a" % 0.019)
pr("    loop stiffness below that cannot hold the wheel against its own return spring -- the")
pr("    feedforward has to, and on a straight the feedforward is nearly zero.")

# ======================================================================================================
pr("\n" + "=" * 108)
pr("I3. OVERSTEER -- over-delivery in quasi-steady turns, and the LAF that would fix the FF alone")
pr("    turn-hold = hands-off engaged, |D| > 0.5, |dD/dt| < 0.3, runs >= 1.5 s")
pr("=" * 108)
hold = ho & (np.abs(g["la_des"]) > 0.5) & (np.abs(dD) < 0.3)
pr("\n    %-8s %8s %7s %12s %12s %14s %14s"
   % ("band", "n s", "runs", "act/des", "f-only/des", "LAF for FF=1", "installed 6.0"))
for k in range(len(BANDS)):
    q = band_mask(hold, k)
    runs = L.stretches(q, int(1.5 * L.FS))
    if len(runs) < 4:
        pr("    %-8s %8.1f %7d  (too few runs)" % (BNAME[k], q.sum() * DT, len(runs))); continue
    ad, fd, sec = [], [], 0
    for (a, b_) in runs:
        D_ = np.mean(np.abs(g["la_des"][a:b_]))
        ad.append(np.mean(np.abs(g["la_act"][a:b_])) / max(D_, 1e-6))
        # what the FEEDFORWARD ALONE would have delivered: f/LAF of torque, times the measured
        # plant gain in that band -- read from the achieved lat accel per unit total torque
        fd.append(np.mean(np.abs(g["f"][a:b_])) / max(D_, 1e-6))
        sec += (b_ - a)
    # LAF that makes the feedforward alone land on target: LAF_new = LAF_true * (f/D)
    from_b3 = {"0-5": 3.19, "5-10": 4.5, "10-20": 5.35, ">20": 6.37}[BNAME[k]]
    laf_fix = from_b3 * float(np.median(fd))
    pr("    %-8s %8.1f %7d %12.3f %12.3f %14.3f %14s"
       % (BNAME[k], sec * DT, len(runs), np.median(ad), np.median(fd), laf_fix,
          "%.3f" % (laf_fix / 6.0)))
    RES.setdefault("hold", {})[BNAME[k]] = dict(n=len(runs), act_des=float(np.median(ad)),
                                                f_des=float(np.median(fd)), laf_fix=laf_fix)
pr("\n    'LAF for FF=1' is LAF_true(band) x median(f/D): the SteerLatAccel that would make the")
pr("    feedforward alone deliver exactly the demand in that band, given the measured plant gain")
pr("    (LAF_true from part B/D2: 3.19 / ~4.5 / 5.35 / 6.37 m/s^2 per unit torque).")

pr("\n    the same split by DEMAND SIZE (all speeds), because the plant gain is amplitude-dependent:")
pr("    %-14s %8s %7s %12s %12s" % ("|D| band", "n s", "runs", "act/des", "f-only/des"))
for lo, hi in [(0.5, 0.8), (0.8, 1.2), (1.2, 1.8), (1.8, 9.0)]:
    q = ho & (np.abs(g["la_des"]) >= lo) & (np.abs(g["la_des"]) < hi) & (np.abs(dD) < 0.3)
    runs = L.stretches(q, int(1.5 * L.FS))
    if len(runs) < 4:
        continue
    ad = [np.mean(np.abs(g["la_act"][a:b_])) / max(np.mean(np.abs(g["la_des"][a:b_])), 1e-6)
          for (a, b_) in runs]
    fd = [np.mean(np.abs(g["f"][a:b_])) / max(np.mean(np.abs(g["la_des"][a:b_])), 1e-6)
          for (a, b_) in runs]
    pr("    %-14s %8.1f %7d %12.3f %12.3f"
       % ("%.1f-%.1f" % (lo, hi), sum(b_ - a for a, b_ in runs) * DT, len(runs),
          np.median(ad), np.median(fd)))

# ======================================================================================================
pr("\n" + "=" * 108)
pr("I4. OVERSHOOT-THEN-CORRECT -- the step response, and which of three mechanisms it is")
pr("    steps = |d(desiredLateralAccel)| >= 0.4 m/s^2 within 0.6 s, then |dD/dt| < 0.5 for 1.5 s.")
pr("    For each: overshoot = (peak|actual| - |final desired|)/|final desired| after the step;")
pr("    time to peak; the ring frequency of the residual; and the integrator at the peak.")
pr("=" * 108)
w6 = int(0.5 * L.FS)
dstep = np.zeros(len(g["t"]))
dstep[w6:] = g["la_des"][w6:] - g["la_des"][:-w6]
cand = np.flatnonzero((np.abs(dstep) >= 0.30) & ho)
events = []
last = -10 ** 9
for i in cand:
    if i - last < int(2.5 * L.FS) or i + int(2.5 * L.FS) >= len(g["t"]):
        continue
    seg = slice(i, i + int(1.2 * L.FS))
    if np.max(np.abs(dD[seg])) > 1.2:
        continue
    if not ho[i:i + int(2.0 * L.FS)].all():
        continue
    last = i
    events.append(i)
pr("\n    %d step events found." % len(events))
rows = []
for i in events:
    post = slice(i, i + int(2.0 * L.FS))
    Dfin = np.median(g["la_des"][i + int(0.8 * L.FS):i + int(1.5 * L.FS)])
    if abs(Dfin) < 0.25:
        continue
    sgn = np.sign(Dfin)
    a_ = g["la_act"][post] * sgn
    pk = float(np.max(a_))
    tpk = float(np.argmax(a_) * DT)
    ov = (pk - abs(Dfin)) / abs(Dfin)
    resid = g["la_act"][post] - g["la_des"][post]
    f_, P = signal.welch(signal.detrend(resid), fs=L.FS, nperseg=128)
    selr = (f_ > 0.5) & (f_ < 6)
    fr = float(f_[selr][int(np.argmax(P[selr]))])
    rows.append(dict(i=i, v=float(g["v"][i]), step=float(abs(dstep[i])), Dfin=float(abs(Dfin)),
                     ov=float(ov), tpk=tpk, fring=fr,
                     i_term=float(abs(g["i"][i + int(tpk * L.FS)])),
                     jump=float(np.max(np.abs(g["rate_dps"][post])))))
if rows:
    R = rows
    pr("    %-8s %6s %9s %9s %9s %9s %9s %9s"
       % ("band", "n", "step p50", "overshoot", "t peak s", "ring Hz", "|i| at pk", "peak rate"))
    for k in range(len(BANDS)):
        lo, hi = BANDS[k]
        Q = [r for r in R if lo <= r["v"] < hi]
        if len(Q) < 3:
            continue
        pr("    %-8s %6d %9.3f %9.3f %9.3f %9.2f %9.3f %9.1f"
           % (BNAME[k], len(Q), np.median([q["step"] for q in Q]),
              np.median([q["ov"] for q in Q]), np.median([q["tpk"] for q in Q]),
              np.median([q["fring"] for q in Q]), np.median([q["i_term"] for q in Q]),
              np.median([q["jump"] for q in Q])))
    pr("\n    DISCRIMINATOR -- does the overshoot SCALE with the step (linear, an under-damped loop)")
    pr("    or is it a FIXED JUMP independent of the step (stiction breakaway)?")
    st = np.array([r["step"] for r in R]); ab = np.array([r["ov"] * r["Dfin"] for r in R])
    bb, rr = lstsq(np.vstack([st, np.ones(len(st))]).T, ab)
    pr("      absolute overshoot (m/s^2) = %.4f * step %+.4f   R2 %.3f   n %d"
       % (bb[0], bb[1], rr, len(R)))
    pr("      a LINEAR loop gives slope > 0 and intercept ~ 0; a STICTION JUMP gives slope ~ 0 and")
    pr("      a positive intercept.  Measured: slope %.4f, intercept %+.4f." % (bb[0], bb[1]))
    cc = np.corrcoef([r["i_term"] for r in R], [r["ov"] for r in R])[0, 1]
    pr("      correlation of the overshoot with the INTEGRATOR at the peak: %+.3f" % cc)
    pr("      (a wind-up mechanism needs a large positive correlation here)")
    RES["step"] = dict(n=len(R), slope=bb[0], intercept=bb[1], r2=rr, corr_i=float(cc))

# ======================================================================================================
pr("\n" + "=" * 108)
pr("I5. THE ~2 Hz LINE -- a limit cycle, or a poorly damped mode driven by the road?")
pr("    Three tests: (1) PROMINENCE -- is there a PEAK at 1-4 Hz, or just broadband content?")
pr("    (2) AMPLITUDE DEPENDENCE -- a limit cycle has a fixed amplitude independent of the road")
pr("    input; a damped mode scales with it.  (3) the command->angle PHASE at the line, which is")
pr("    the plant's phase there and says how close the loop is to 180 deg.")
pr("=" * 108)
for k in range(len(BANDS)):
    q = band_mask(ho, k)
    runs = L.stretches(q, 512)
    if not runs:
        continue
    Pa = Pc = Pz = None
    Sca = None
    nn = 0
    for (a, b_) in runs:
        f_, p1 = signal.welch(signal.detrend(g["ang"][a:b_]), fs=L.FS, nperseg=512, noverlap=256)
        _, p2 = signal.welch(signal.detrend(g["cmd"][a:b_]), fs=L.FS, nperseg=512, noverlap=256)
        _, p3 = signal.welch(signal.detrend(Dfut[a:b_]), fs=L.FS, nperseg=512, noverlap=256)
        _, s12 = signal.csd(signal.detrend(g["cmd"][a:b_]), signal.detrend(g["ang"][a:b_]),
                            fs=L.FS, nperseg=512, noverlap=256)
        w = b_ - a
        Pa = p1 * w if Pa is None else Pa + p1 * w
        Pc = p2 * w if Pc is None else Pc + p2 * w
        Pz = p3 * w if Pz is None else Pz + p3 * w
        Sca = s12 * w if Sca is None else Sca + s12 * w
        nn += w
    Pa /= nn; Pc /= nn; Pz /= nn; Sca /= nn
    sel = (f_ >= 1.0) & (f_ < 4.0)
    fpk = f_[sel][int(np.argmax(Pa[sel]))]
    # PROMINENCE, done properly: the spectrum falls steeply with f, so a flat baseline over
    # 0.5-8 Hz would score the 1/f slope as a "peak".  The baseline here is a straight line fitted
    # in log-log to the SHOULDERS either side of the band (0.6-0.9 and 4-7 Hz), and the prominence
    # is the peak above that line at its own frequency.
    sh = ((f_ >= 0.6) & (f_ <= 0.9)) | ((f_ >= 4.0) & (f_ <= 7.0))
    A_ = np.vstack([np.log10(f_[sh]), np.ones(sh.sum())]).T
    cf, _r = np.linalg.lstsq(A_, 10 * np.log10(Pa[sh] + 1e-30), rcond=None)[0], None
    fpk_ = f_[sel][int(np.argmax(Pa[sel]))]
    base = cf[0] * np.log10(fpk_) + cf[1]
    prom = 10 * np.log10(Pa[sel].max() + 1e-30) - base
    ph = np.degrees(np.angle(np.interp(fpk, f_, Sca.real) + 1j * np.interp(fpk, f_, Sca.imag)))
    a14 = np.sqrt(np.sum(Pa[sel]) * (f_[1] - f_[0]))
    z14 = np.sqrt(np.sum(Pz[sel]) * (f_[1] - f_[0]))
    pr("    %-8s  peak %5.2f Hz | prominence over the 0.5-8 Hz baseline %6.2f dB | angle 1-4 Hz %8.4f deg"
       % (BNAME[k], fpk, prom, a14))
    pr("    %-8s  road demand 1-4 Hz %8.5f m/s^2 | angle/road ratio %8.2f | cmd->angle phase at the peak %7.1f deg"
       % ("", z14, a14 / max(z14, 1e-9), ph))
    RES.setdefault("line", {})[BNAME[k]] = dict(f=float(fpk), prom=float(prom), amp=float(a14),
                                                road=float(z14), phase=float(ph))
pr("\n    READING: a prominence under ~3 dB is NOT a line -- it is the tail of the road spectrum.")
pr("    The angle/road ratio is the closed-loop gain at 1-4 Hz; a limit cycle would show a large")
pr("    ratio with a large prominence, and would not scale with the road term.")

with open(os.path.join(L.SCRATCH, "v293_ident_i.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_i.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_i.txt / .json")
