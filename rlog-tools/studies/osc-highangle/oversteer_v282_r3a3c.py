# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v282_r3a3c.py -- THE LAF DOSE-RESPONSE READ.

Firmware V282 UNCHANGED on all three drives; only the openpilot tune moved:
    r39  SteerLatAccel 2.11   (the baseline, fully characterised: R_road 1.116 / R_m 1.123 / 1/rho 0.988)
    r3c  SteerLatAccel 3.6
    r3a  SteerLatAccel 4.0
Operator, verbatim: "I wasn't able to tell the difference between the two, not even sure if it helped at
all relative to lat accel = 2.11" / "we understeer on hard turns around corners <20 mph" / "at 20+ mph,
we oversteer" / "the most desirable thing is to stop the consistent oversteer at 20+ mph".

Every stratum, bias correction, curve definition and estimator is IMPORTED from oversteer_v282_r39.py,
so it is literally the same object.  Two changes, both declared:
  (1) TAGS/TUNE extended with r3a and r3c;
  (2) curve_mask gains a DATA-GAP guard -- r3a is missing segment 10 on disk, and the 100 Hz grid is built
      from first-to-last timestamp, so without the guard a ~60 s hole would be bridged by hold()/interp().

Sections
  R  REPRODUCTION -- r39's published numbers re-derived by this code path before anything else is trusted
  1  the pre-registered discriminator: R_road, R_m, 1/rho, both arrays, with CIs
  2  SPEED-STRATIFIED R_road / R_m / excess yaw rate -- the operator's actual under/over claim
  3  the dose-response: R_m, f/p/i/d, integrator headroom + saturation, commanded torque
  4  the curve time-course (fixed cohort, >= 5 s)
  5  sanity gates: engagement, latActive vs wire, saturation, gaps, exposure

Run: python rlog-tools/studies/osc-highangle/oversteer_v282_r3a3c.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "optune"))
import oversteer_v282_r39 as M  # noqa: E402
import backcalc_laf_friction as B  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = M.FS
G = 9.81
LINES = []
NEW = ("r39", "r3c", "r3a")                      # dose order: 2.11 -> 3.6 -> 4.0
ALLT = ("r34", "r35", "r39", "r3c", "r3a")
V_BANDS = ((0, 4), (4, 9), (9, 16), (16, 22), (22, 40))

M.TUNE.update({
    "r3a": dict(kp=0.8, laf=4.0, fric=0.03, sr="MAP", note="V282 LAF4.0"),
    "r3c": dict(kp=0.8, laf=3.6, fric=0.03, sr="MAP", note="V282 LAF3.6"),
})
M.TAGS = list(ALLT)


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


# ---------------------------------------------------------------- the DATA-GAP guard (r3a seg 10 missing)
_gof0 = M.gof
GAPS = {}


def gof(tag):
    g, cp = _gof0(tag)
    if "gapok" not in g:
        D = B.load(tag)
        ct = D["co_t"] - D["co_t"][0]
        ok = np.ones(len(g["t"]), bool)
        holes = []
        for i in np.where(np.diff(ct) > 1.0)[0]:
            a, b = float(ct[i]), float(ct[i + 1])
            holes.append((a, b))
            ok &= ~((g["t"] > a - 0.5) & (g["t"] < b + 0.5))
        g["gapok"] = ok
        GAPS[tag] = holes
    return g, cp


M.gof = gof

_cm0 = M.curve_mask


def curve_mask(g):
    return _cm0(g) & g["gapok"]


M.curve_mask = curve_mask


def med(x):
    return M.med(x)


def boot(vals, n=4000, seed=7):
    return M.boot_ci(vals, n, seed)


def decomp(t, rows, key="vyaw", vlo=None, vhi=None):
    """Section G's decomposition, verbatim, optionally restricted to a speed band."""
    g, _ = gof(t)
    des = g["desiredLateralAccel"]
    sb = M.straight_bias(g)
    out = dict(rm=[], rr=[], ri=[], v=[], n=[])
    for r in rows:
        if r["des"] <= 0.5 or r["b"] - r["a"] < int(2.5 * FS):
            continue
        sl = slice(r["a"] + 150, r["b"])
        big = np.abs(des[sl]) > 0.5
        if vlo is not None:
            big = big & (g["v"][sl] >= vlo) & (g["v"][sl] < vhi)
        if big.sum() < 10:
            continue
        m_ = g["actualLateralAccel"][sl][big] - sb["m"]
        rd = (g["vyaw"] if key == "vyaw" else g["pose"])[sl][big] - sb[key]
        dd = des[sl][big]
        out["rm"].append(med(m_ / dd))
        out["rr"].append(med(rd / dd))
        out["ri"].append(med(rd / m_))
        out["v"].append(med(g["v"][sl][big]))
        out["n"].append(int(big.sum()))
    return out


# ================================================================================================== R
def sectionR(C):
    pr("=" * 172)
    pr("SECTION R -- REPRODUCTION CHECK.  Before r3a/r3c are trusted, this code path must re-derive r39's")
    pr("  PUBLISHED numbers (STATE.md: R_road 1.116 [1.029,1.205], R_m 1.123 [1.083,1.180], 1/rho 0.988).")
    pr("  A check that condemns a known-truth route is broken.")
    pr("=" * 172)
    d = decomp("r39", C["r39"])
    lo1, hi1 = boot(d["rm"])
    lo2, hi2 = boot(d["rr"])
    pr("  r39 via THIS script: n %d curves | R_m %.3f [%.3f,%.3f] | R_road %.3f [%.3f,%.3f] | 1/rho %.3f"
       % (len(d["rm"]), med(d["rm"]), lo1, hi1, med(d["rr"]), lo2, hi2, med(d["ri"])))
    pr("  PUBLISHED           : n 20 curves | R_m 1.123 [1.083,1.180] | R_road 1.116 [1.029,1.205] | 1/rho 0.988")
    ok = (abs(med(d["rm"]) - 1.123) < 0.0005 and abs(med(d["rr"]) - 1.116) < 0.0005
          and abs(med(d["ri"]) - 0.988) < 0.0005 and len(d["rm"]) == 20
          and abs(lo1 - 1.083) < 0.0005 and abs(hi1 - 1.180) < 0.0005
          and abs(lo2 - 1.029) < 0.0005 and abs(hi2 - 1.205) < 0.0005)
    pr("  ==> %s" % ("REPRODUCED TO THE DIGIT, point estimates AND CIs."
                     if ok else "*** MISMATCH -- do not trust anything below ***"))
    return ok


# ================================================================================================== 1
def section1(C):
    pr("")
    pr("=" * 172)
    pr("SECTION 1 -- THE PRE-REGISTERED DISCRIMINATOR, SCORED AS WRITTEN.   R_road = R_m x (1/rho)")
    pr("  Tight-curve steady stratum (|des| > 0.5, >= 1.5 s into the curve), curve as the unit, bias-corrected.")
    pr("  PRIMARY instrument = PATH (vyaw = v*yaw_cal, no roll term).  SENSITIVITY = specific force (pose).")
    pr("  Prereg (STATE.md): 'score on R_m -- does it fall toward 1.00?'")
    pr("=" * 172)
    res = {}
    for key in ("vyaw", "pose"):
        pr("  --- achieved-side array: %s %s" % (key, "(PRIMARY)" if key == "vyaw" else "(sensitivity)"))
        pr("  %-5s %-18s %7s %9s %9s %9s %9s | %-18s %-18s" % (
            "route", "SteerLatAccel", "curves", "R_m", "R_road", "1/rho", "Rm*1/rho", "R_m 95% CI", "R_road 95% CI"))
        for t in ALLT:
            d = decomp(t, C[t], key=key)
            res[(key, t)] = d
            lo1, hi1 = boot(d["rm"])
            lo2, hi2 = boot(d["rr"])
            pr("  %-5s %-18s %7d %9.3f %9.3f %9.3f %9.3f | [%.3f, %.3f]     [%.3f, %.3f]" % (
                t, "%.2f (%s)" % (M.TUNE[t]["laf"], M.TUNE[t]["note"]), len(d["rm"]),
                med(d["rm"]), med(d["rr"]), med(d["ri"]), med(d["rm"]) * med(d["ri"]), lo1, hi1, lo2, hi2))
        pr()
    pr("  1.1 PAIRWISE DELTAS (4000-resample bootstrap over curves, independent arms).")
    pr("      A CI excluding 0 is a resolved change; one straddling 0 is not.")
    pr("      %-6s %-10s %-26s %-26s" % ("array", "pair", "dR_m", "dR_road"))
    rng = np.random.default_rng(11)
    for key in ("vyaw", "pose"):
        for hi_t, lo_t in (("r3c", "r39"), ("r3a", "r39"), ("r3a", "r3c")):
            cells = []
            for fld in ("rm", "rr"):
                a = np.array(res[(key, hi_t)][fld], float)
                b = np.array(res[(key, lo_t)][fld], float)
                bs = (np.median(a[rng.integers(0, len(a), (4000, len(a)))], 1)
                      - np.median(b[rng.integers(0, len(b), (4000, len(b)))], 1))
                cells.append("%+.3f [%+.3f, %+.3f]" % (med(a) - med(b),
                                                       np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
            pr("      %-6s %-10s %-26s %-26s" % (key, "%s-%s" % (hi_t, lo_t), cells[0], cells[1]))
    return res


# ================================================================================================== 2
def section2(C):
    pr("")
    pr("=" * 172)
    pr("SECTION 2 -- SPEED-STRATIFIED.  THE OPERATOR'S ACTUAL CLAIM: understeer on hard turns < 20 mph (< 9 m/s),")
    pr("  oversteer at 20+ mph (> 9 m/s).  Does the SIGN of the error flip across that boundary?")
    pr("  Curve as the unit: a curve contributes to a band if it has >= 10 steady frames with |des| > 0.5 in it.")
    pr("  R < 1 = the car turned LESS than asked (UNDER-delivery); R > 1 = MORE (OVER-delivery).")
    pr("=" * 172)
    for t in NEW + ("r35",):
        pr("  --- %s   SteerLatAccel %.2f   (%s)" % (t, M.TUNE[t]["laf"], M.TUNE[t]["note"]))
        pr("      %-12s %7s %8s %9s %-18s %9s %-18s %9s %11s" % (
            "v band", "curves", "secs", "R_m", "R_m 95% CI", "R_road", "R_road 95% CI", "1/rho", "os deg/s"))
        g, _ = gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        stm = np.zeros(len(des), bool)
        dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
            dirf[r["a"]:r["b"]] = r["dir"]
        stm &= g["gapok"]
        for lo, hi in V_BANDS:
            d = decomp(t, C[t], vlo=lo, vhi=hi)
            s = stm & (g["v"] >= lo) & (g["v"] < hi)
            secs = s.sum() / FS
            if len(d["rm"]) < 3:
                pr("      %-12s %7d %8.0f   (too few curves to bootstrap)" % ("%g-%g m/s" % (lo, hi), len(d["rm"]), secs))
                continue
            l1, h1 = boot(d["rm"])
            l2, h2 = boot(d["rr"])
            dd = dirf[s]
            os_a = med((g["vyaw"][s] - des[s]) * dd - sb["vyaw"] * dd)
            os_w = np.degrees(os_a / max(med(g["v"][s]), 0.5))
            pr("      %-12s %7d %8.0f %9.3f [%.3f, %.3f]  %9.3f [%.3f, %.3f]  %9.3f %+11.2f" % (
                "%g-%g m/s" % (lo, hi), len(d["rm"]), secs, med(d["rm"]), l1, h1,
                med(d["rr"]), l2, h2, med(d["ri"]), os_w))
        pr()
    pr("  2.1 SPEED-MATCHED CONTRAST -- the same band, r39 vs r3c vs r3a (R_road primary).")
    pr("      The three routes are NOT a matched pair: different roads, different exposure.  Matching on speed")
    pr("      removes the EXPOSURE share of that confound, not the road-geometry share.")
    pr("      %-12s" % "v band" + "".join("%26s" % ("%s R_road [CI] n" % t) for t in NEW)
       + "%22s" % "R_m 39/3c/3a")
    for lo, hi in V_BANDS:
        cells, rms = [], []
        for t in NEW:
            d = decomp(t, C[t], vlo=lo, vhi=hi)
            if len(d["rm"]) < 3:
                cells.append("%26s" % "--")
                rms.append("--")
                continue
            l2, h2 = boot(d["rr"])
            cells.append("%26s" % ("%.3f [%.2f,%.2f] %d" % (med(d["rr"]), l2, h2, len(d["rr"]))))
            rms.append("%.3f" % med(d["rm"]))
        pr("      %-12s" % ("%g-%g" % (lo, hi)) + "".join(cells) + "%22s" % ("/".join(rms)))
    pr()
    pr("  2.2 ANGLE-stratified inside the LOW-speed band (his 'hard turns around corners < 20 mph'), frame-pooled:")
    pr("      %-5s %-18s %8s %9s %9s %11s" % ("route", "v<9 & |ang| band", "secs", "R_m", "R_road", "os m/s^2"))
    for t in NEW:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        stm = np.zeros(len(des), bool)
        dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
            dirf[r["a"]:r["b"]] = r["dir"]
        stm &= g["gapok"]
        for alo, ahi in ((0, 30), (30, 90), (90, 1e9)):
            s = stm & (g["v"] < 9) & (np.abs(g["ang"]) >= alo) & (np.abs(g["ang"]) < ahi) & (np.abs(des) > 0.5)
            if s.sum() < 100:
                continue
            dd = dirf[s]
            pr("      %-5s %-18s %8.0f %9.3f %9.3f %+11.3f" % (
                t, "|ang| %g-%s" % (alo, "inf" if ahi > 1e8 else "%g" % ahi), s.sum() / FS,
                med((g["actualLateralAccel"][s] - sb["m"]) / des[s]),
                med((g["vyaw"][s] - sb["vyaw"]) / des[s]),
                med((g["vyaw"][s] - des[s]) * dd - sb["vyaw"] * dd)))


# ================================================================================================== 3
def section3(C):
    pr("")
    pr("=" * 172)
    pr("SECTION 3 -- DID THE LAF CHANGE DO ANYTHING MEASURABLE?  The dose-response across 2.11 -> 3.6 -> 4.0.")
    pr("  LAF is a DIVISOR (interfaces.py:329): out_torque = (kp*e_lsf + ki*I + ff)/LAF.  The PID clamp is +-LAF.")
    pr("  A MONOTONE response is the finding; a FLAT one is a bigger finding.")
    pr("=" * 172)
    pr("  3.0 IS THE TOGGLE ACTUALLY LIVE ON THE WIRE?  LAF back-solved from the logged PID terms, per route:")
    pr("      %-5s %13s %15s %13s %13s %11s" % (
        "route", "LAF (label)", "LAF (wire p50)", "kp (wire)", "fric (wire)", "lpar_sr"))
    for t in ALLT:
        g, _ = gof(t)
        o = B.live_values(g)
        pr("      %-5s %13.2f %15.3f %13.3f %13.3f %11.2f" % (
            t, M.TUNE[t]["laf"], o.get("LAF_from_pid_p50", np.nan), o.get("kp_p50", np.nan),
            o.get("friction_from_f", np.nan), med(g["lpar_sr"])))
    pr()
    pr("  3.1 f / p / i / d IN THE CURVE-STEADY STRATUM (direction-folded medians, LATERAL-ACCEL units).")
    pr("      r39's registered row: f/p/i/d = +0.465 / -0.119 / -0.215 / 0.000; i opposes f in 81.4 % of frames.")
    pr("      %-5s %6s %8s %8s %8s %8s %8s %8s %10s %12s" % (
        "route", "LAF", "secs", "f", "p", "i", "d", "sum", "ff share", "i fights f"))
    for t in ALLT:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]
        stm = np.zeros(len(des), bool)
        dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
            dirf[r["a"]:r["b"]] = r["dir"]
        stm &= g["gapok"]
        d = dirf[stm]
        f_, p_, i_, d_ = g["f"][stm] * d, g["p"][stm] * d, g["i"][stm] * d, g["d"][stm] * d
        tot = f_ + p_ + i_ + d_
        ok2 = np.abs(tot) > 0.05
        pr("      %-5s %6.2f %8.0f %+8.3f %+8.3f %+8.3f %+8.3f %+8.3f %10.2f %12.3f" % (
            t, M.TUNE[t]["laf"], stm.sum() / FS, med(f_), med(p_), med(i_), med(d_), med(tot),
            med(f_[ok2] / tot[ok2]), float(np.mean((np.sign(i_) == -np.sign(f_)) & (np.abs(f_) > 0.05)))))
    pr("      NOTE: f, p, i are in LAT-ACCEL units.  The DELIVERED torque is (f+p+i+d)/LAF, so a term FLAT in this")
    pr("      table is a term whose TORQUE contribution fell by the full LAF ratio.  Both are reported (3.3).")
    pr()
    pr("  3.2 THE OUTER INTEGRATOR: headroom, saturation, and the share of itself spent cancelling the FF.")
    pr("      %-5s %10s %8s %8s %8s %8s %11s %11s %11s" % (
        "route", "engaged s", "bound", "max|i|", "p90|i|", "p50|i|", "% of bound", "saturated", "i fights f"))
    for t in ALLT:
        g, _ = gof(t)
        ok = curve_mask(g)
        i_ = g["i"][ok]
        f_ = g["f"][ok]
        laf = M.TUNE[t]["laf"]
        imax = float(np.nanmax(np.abs(i_)))
        pr("      %-5s %10.0f %8.3f %8.3f %8.3f %8.3f %11.1f %11.4f %11.3f" % (
            t, ok.sum() / FS, laf, imax, M.q(np.abs(i_), 90), M.q(np.abs(i_), 50), 100 * imax / laf,
            float(np.mean(g["saturated"][ok] > 0.5)),
            float(np.mean((np.sign(i_) == -np.sign(f_)) & (np.abs(f_) > 0.05)))))
    pr()
    pr("  3.3 THE DELIVERED SURFACE -- commanded torque, the thing LAF actually divides.")
    pr("      tq = carOutput.actuatorsOutput.torque (openpilot units, +-1); can = torqueOutputCan (EPS counts).")
    pr("      %-5s %6s %9s %10s %10s %10s %10s %12s %11s" % (
        "route", "LAF", "secs", "p50|tq|", "p90|tq|", "p99|tq|", "max|tq|", "p50|f|/LAF", "p50|can|"))
    for t in ALLT:
        g, _ = gof(t)
        ok = curve_mask(g) & (np.abs(g["desiredLateralAccel"]) > 0.3)
        tq = np.abs(g["tq"][ok])
        laf = M.TUNE[t]["laf"]
        pr("      %-5s %6.2f %9.0f %10.4f %10.4f %10.4f %10.4f %12.4f %11.1f" % (
            t, laf, ok.sum() / FS, M.q(tq, 50), M.q(tq, 90), M.q(tq, 99), float(np.nanmax(tq)),
            med(np.abs(g["f"][ok])) / laf, M.q(np.abs(g["can"][ok]), 50)))
    pr()
    pr("  3.4 SPEED-MATCHED delivered torque (removes the exposure confound between the three roads):")
    pr("      %-12s" % "v band" + "".join("%28s" % ("%s p50|tq| (secs)" % t) for t in NEW))
    for lo, hi in V_BANDS:
        cells = []
        for t in NEW:
            g, _ = gof(t)
            ok = curve_mask(g) & (np.abs(g["desiredLateralAccel"]) > 0.5) & (g["v"] >= lo) & (g["v"] < hi)
            if ok.sum() < 100:
                cells.append("%28s" % "--")
                continue
            cells.append("%28s" % ("%.4f  (%.0f s)" % (M.q(np.abs(g["tq"][ok]), 50), ok.sum() / FS)))
        pr("      %-12s" % ("%g-%g" % (lo, hi)) + "".join(cells))


# ================================================================================================== 4
def section4(C):
    pr("")
    pr("=" * 172)
    pr("SECTION 4 -- THE CURVE TIME-COURSE (fixed cohort: only curves surviving to 5.0 s, so the same curves are")
    pr("  in every column).  r39's registered shape: R = 0.90 0.92 0.98 1.04 1.07 1.14 1.11 1.06 1.25 1.09 at")
    pr("  t = 0.25 ... 5.0 s -- starts UNDER, crosses 1.00 at ~0.8 s, stays 5-25 % over.")
    pr("=" * 172)
    TT = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)
    for t in NEW:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        rows = [r for r in C[t] if r["dur"] >= 5.0]
        cr, cm, co = [], [], []
        for tt in TT:
            k = int(tt * FS)
            vr, vm, vo = [], [], []
            for r in rows:
                j = r["a"] + k
                if j >= r["b"] or not g["gapok"][j]:
                    continue
                d = r["dir"]
                vo.append((g["vyaw"][j] - des[j]) * d - sb["vyaw"] * d)
                if abs(des[j]) > 0.4:
                    vr.append((g["vyaw"][j] - sb["vyaw"]) / des[j])
                    vm.append((g["actualLateralAccel"][j] - sb["m"]) / des[j])
            cr.append(np.nanmedian(vr) if len(vr) > 3 else np.nan)
            cm.append(np.nanmedian(vm) if len(vm) > 3 else np.nan)
            co.append(np.nanmean(vo) if vo else np.nan)
        pr("      %-5s n=%2d  R_road " % (t, len(rows)) + " ".join("%7.3f" % x for x in cr))
        pr("      %-5s        R_m    " % "" + " ".join("%7.3f" % x for x in cm))
        pr("      %-5s        os_vyaw" % "" + " ".join("%+7.3f" % x for x in co))
        cross = next((TT[i] for i in range(len(TT)) if np.isfinite(cr[i]) and cr[i] >= 1.0), None)
        pr("      %-5s        R_road first >= 1.00 at t = %s" % ("", ("%.2f s" % cross) if cross else "never in window"))
    pr("      t (s)               " + " ".join("%7.2f" % x for x in TT))
    pr()
    pr("  4.1 QUASI-STATIC vs TRANSIENT (oversteer_v283 9.3's definition, verbatim):")
    pr("      quasi-static = >= 1.0 s into the curve AND |d(des)/dt| < 0.20 ; transient = first 1.0 s OR |d(des)/dt| >= 0.50")
    pr("      %-5s %30s %30s %16s" % ("route", "quasi-static os_vyaw (frac>0)", "transient os_vyaw (frac>0)", "qs - transient"))
    for t in ALLT:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        dd = np.r_[0.0, np.diff(des)] * FS
        into = np.zeros(len(des))
        dirf = np.zeros(len(des))
        inc = np.zeros(len(des), bool)
        for r in C[t]:
            a, b = r["a"], r["b"]
            into[a:b] = np.arange(b - a) / FS
            dirf[a:b] = r["dir"]
            inc[a:b] = True
        inc &= g["gapok"]
        os_f = (g["vyaw"] - des) * dirf - sb["vyaw"] * dirf
        qs = inc & (into >= 1.0) & (np.abs(dd) < 0.20)
        tr = inc & ((into < 1.0) | (np.abs(dd) >= 0.50))
        pr("      %-5s %18.3f (%5.2f)            %18.3f (%5.2f)   %+16.3f" % (
            t, med(os_f[qs]), float(np.mean(os_f[qs] > 0)), med(os_f[tr]), float(np.mean(os_f[tr] > 0)),
            med(os_f[qs]) - med(os_f[tr])))
    pr()
    pr("  4.2 THE RATIO-FREE SHAPE STATISTIC (supp K.2, verbatim): peak / settled of the ACHIEVED channel against")
    pr("      its OWN final value.  No ask, no ratio, no vehicle model: >>1 decaying = transient; ~1 = displaced level.")
    pr("      %-5s %8s %14s %10s %10s %12s" % ("route", "n", "peak/settled", "p25", "p75", "t_peak (s)"))
    for t in ALLT:
        g, _ = gof(t)
        sb = M.straight_bias(g)
        rows = [r for r in C[t] if r["dur"] >= 4.0 and r["des"] > 0.4]
        rat, tpk = [], []
        for r in rows:
            ach = (g["vyaw"][r["a"]:r["b"]] - sb["vyaw"]) * r["dir"]
            settled = np.nanmedian(ach[int(2.5 * FS):])
            if not np.isfinite(settled) or settled < 0.3:
                continue
            w = ach[:int(2.5 * FS)]
            rat.append(float(np.nanmax(w)) / settled)
            tpk.append(float(np.nanargmax(w)) / FS)
        if len(rat) < 3:
            pr("      %-5s %8d   (too few)" % (t, len(rat)))
            continue
        pr("      %-5s %8d %14.3f %10.3f %10.3f %12.2f" % (
            t, len(rat), med(rat), np.percentile(rat, 25), np.percentile(rat, 75), med(tpk)))


# ================================================================================================== 5
def section5(C):
    pr("")
    pr("=" * 172)
    pr("SECTION 5 -- SANITY GATES")
    pr("=" * 172)
    pr("  5.1 ENGAGEMENT and CONTAMINATION")
    pr("      %-5s %10s %12s %8s %12s %12s %12s %11s" % (
        "route", "wall s", "latActive s", "%", "lat!=wire", "pressed", "outer sat", "v<0.5"))
    for t in ALLT:
        g, _ = gof(t)
        wall = len(g["t"]) / FS
        lat = g["lat"] > 0.5
        wire = (g["sca"] > 0.5) & (g["req"] > 0.5)
        pr("      %-5s %10.1f %12.1f %8.1f %12.4f %12.4f %12.4f %11.4f" % (
            t, wall, lat.sum() / FS, 100.0 * lat.mean(), float(np.mean(lat != wire)),
            float(np.mean((g["pressed"] > 0.5)[lat])), float(np.mean((g["saturated"] > 0.5)[lat])),
            float(np.mean(g["v"][lat] < 0.5))))
    pr("      (lat!=wire uses backcalc_extract's KNOWN-CONTAMINATED 0x0E4 src>=128 filter -- STATE.md defect 3.")
    pr("       It mixes the stock camera (src 128, STEER_REQUEST always 0) with openpilot (src 129) at ~200 Hz,")
    pr("       so this column is an UPPER BOUND on disagreement, not a measurement.  No gate below uses it.)")
    pr()
    pr("  5.2 DATA GAPS on the 100 Hz grid (r3a is missing segment 10 on disk).  Every statistic above excludes these.")
    for t in ALLT:
        h = GAPS.get(t, [])
        pr("      %-5s %d gap(s)%s" % (t, len(h), "".join("   [%.1f - %.1f s] = %.1f s" % (a, b, b - a) for a, b in h)))
    pr()
    pr("  5.3 THE ANALYSED CURVE STRATUM")
    pr("      %-5s %12s %10s %14s %14s %12s" % ("route", "curve secs", "curves", "min v (m/s)", "max |ang| deg", "max |des|"))
    for t in ALLT:
        rows = C[t]
        pr("      %-5s %12.0f %10d %14.2f %14.0f %12.2f" % (
            t, sum(r["dur"] for r in rows), len(rows),
            min([r["v"] for r in rows]) if rows else np.nan,
            max([r["ang_max"] for r in rows]) if rows else np.nan,
            max([r["des_max"] for r in rows]) if rows else np.nan))
    pr()
    pr("  5.4 EXPOSURE -- the routes are NOT matched.  Engaged curve-STEADY time by speed band, per route:")
    pr("      %-5s" % "route" + "".join("%14s" % ("%g-%g m/s" % b) for b in V_BANDS) + "%12s" % "total s")
    for t in ALLT:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]
        stm = np.zeros(len(des), bool)
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
        stm &= g["gapok"]
        cells = ["%14.0f" % (((g["v"] >= lo) & (g["v"] < hi) & stm).sum() / FS) for lo, hi in V_BANDS]
        pr("      %-5s" % t + "".join(cells) + "%12.0f" % (stm.sum() / FS))


# ================================================================================================== 6
def band_frames(t, lo, hi, des_thr=0.2):
    """EVERY engaged, un-pressed, gap-free frame in a speed band with a real ask.  Direction-folded and
    bias-corrected.  This is the HIGH-POWER estimator: the curve-as-unit statistic in sections 1-2 needs
    |des| > 0.5 AND a 2.5 s run, which at highway speed discards nearly everything -- exactly the regime
    the operator is complaining about.  Returns x = asked, y = road achieved, m = controller achieved."""
    g, _ = gof(t)
    des = g["desiredLateralAccel"]
    sb = M.straight_bias(g)
    sel = (curve_mask(g) & (np.abs(des) > des_thr) & (g["v"] >= lo) & (g["v"] < hi)
           & np.isfinite(g["vyaw"]) & np.isfinite(g["actualLateralAccel"]))
    d = np.sign(des[sel])
    return dict(x=np.abs(des[sel]),
                y=(g["vyaw"][sel] - sb["vyaw"]) * d,
                m=(g["actualLateralAccel"][sel] - sb["m"]) * d,
                blk=(g["t"][sel] / 10.0).astype(int), n=int(sel.sum()), v=med(g["v"][sel]))


def block_slope_ci(x, y, blk, n=2000, seed=17):
    """Slope through the origin, with a 10 s CONTIGUOUS-BLOCK bootstrap (frames are autocorrelated;
    an iid frame bootstrap would give a CI ~30x too narrow)."""
    if len(x) < 50:
        return np.nan, np.nan, np.nan, 0
    sl = float(x @ y / (x @ x))
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    starts = np.searchsorted(inv[order], np.arange(len(ub)))
    ends = np.r_[starts[1:], len(order)]
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for k in range(n):
        pick = rng.integers(0, len(ub), len(ub))
        idx = np.concatenate([order[starts[j]:ends[j]] for j in pick])
        xx, yy = x[idx], y[idx]
        out[k] = xx @ yy / (xx @ xx)
    return sl, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(ub)


def section6():
    pr("")
    pr("=" * 172)
    pr("SECTION 6 -- THE HIGH-POWER SPEED READ.  Sections 1-2 need |des| > 0.5 and a 2.5 s run; at 20+ mph almost")
    pr("  nothing qualifies (r3a: 6 tight curves route-wide, 3 s above 16 m/s).  Here EVERY engaged, un-pressed,")
    pr("  gap-free frame with |des| > 0.2 enters, direction-folded and bias-corrected, and the statistic is the")
    pr("  SLOPE of achieved on asked through the origin -- a pure SCALE, which is what an equilibrium error is.")
    pr("  CI = 10 s CONTIGUOUS-BLOCK bootstrap (2000 resamples); frames are autocorrelated, an iid bootstrap lies.")
    pr("  slope > 1 = the car turns MORE than asked (over-delivery); < 1 = LESS (under-delivery).")
    pr("=" * 172)
    pr("  6.1 R_road (road / asked), by speed band")
    pr("      %-12s" % "v band" + "".join("%30s" % ("%s (LAF %.2f)" % (t, M.TUNE[t]["laf"])) for t in NEW)
       + "%26s" % "r35 (LAF 2.11, SR 12.5)")
    for lo, hi in V_BANDS:
        cells = []
        for t in NEW + ("r35",):
            F = band_frames(t, lo, hi)
            s, l, h, nb = block_slope_ci(F["x"], F["y"], F["blk"])
            w = "%26s" if t == "r35" else "%30s"
            cells.append(w % ("--" if not np.isfinite(s) else
                              "%.3f [%.3f,%.3f] %.0fs" % (s, l, h, F["n"] / FS)))
        pr("      %-12s" % ("%g-%g m/s" % (lo, hi)) + "".join(cells))
    pr()
    pr("  6.2 R_m (controller's OWN measurement / asked) -- the pre-registered discriminator, same frames")
    pr("      %-12s" % "v band" + "".join("%30s" % ("%s (LAF %.2f)" % (t, M.TUNE[t]["laf"])) for t in NEW)
       + "%26s" % "r35 (LAF 2.11, SR 12.5)")
    for lo, hi in V_BANDS:
        cells = []
        for t in NEW + ("r35",):
            F = band_frames(t, lo, hi)
            s, l, h, nb = block_slope_ci(F["x"], F["m"], F["blk"])
            w = "%26s" if t == "r35" else "%30s"
            cells.append(w % ("--" if not np.isfinite(s) else
                              "%.3f [%.3f,%.3f] %.0fs" % (s, l, h, F["n"] / FS)))
        pr("      %-12s" % ("%g-%g m/s" % (lo, hi)) + "".join(cells))
    pr()
    pr("  6.3 THE POOLED RAISED-LAF ARM (r3a + r3c, 3.6-4.0) vs r39 (2.11).  Same firmware, same SR map, same")
    pr("      SteerKP; the ONLY declared difference is LAF.  Pooling buys the power neither route has alone.")
    pr("      %-12s %-30s %-30s %-26s" % ("v band", "r39 R_road", "r3a+r3c R_road", "delta [95% CI]"))
    rng = np.random.default_rng(23)
    for lo, hi in V_BANDS:
        A = band_frames("r39", lo, hi)
        Bs = [band_frames(t, lo, hi) for t in ("r3c", "r3a")]
        x2 = np.concatenate([b["x"] for b in Bs])
        y2 = np.concatenate([b["y"] for b in Bs])
        b2 = np.concatenate([b["blk"] + 100000 * i for i, b in enumerate(Bs)])
        s1, l1, h1, _ = block_slope_ci(A["x"], A["y"], A["blk"])
        s2, l2, h2, _ = block_slope_ci(x2, y2, b2)
        if not (np.isfinite(s1) and np.isfinite(s2)):
            pr("      %-12s %-30s %-30s %-26s" % ("%g-%g" % (lo, hi),
                                                  "--" if not np.isfinite(s1) else "%.3f" % s1,
                                                  "--" if not np.isfinite(s2) else "%.3f" % s2, "--"))
            continue
        # delta CI: independent block bootstraps differenced
        def bs(x, y, blk, seed):
            ub, inv = np.unique(blk, return_inverse=True)
            order = np.argsort(inv, kind="stable")
            st = np.searchsorted(inv[order], np.arange(len(ub)))
            en = np.r_[st[1:], len(order)]
            r = np.random.default_rng(seed)
            o = np.empty(2000)
            for k in range(2000):
                p = r.integers(0, len(ub), len(ub))
                ii = np.concatenate([order[st[j]:en[j]] for j in p])
                o[k] = x[ii] @ y[ii] / (x[ii] @ x[ii])
            return o
        d = bs(x2, y2, b2, 31) - bs(A["x"], A["y"], A["blk"], 41)
        pr("      %-12s %-30s %-30s %-26s" % (
            "%g-%g" % (lo, hi), "%.3f [%.3f,%.3f] %.0fs" % (s1, l1, h1, A["n"] / FS),
            "%.3f [%.3f,%.3f] %.0fs" % (s2, l2, h2, len(x2) / FS),
            "%+.3f [%+.3f,%+.3f]" % (s2 - s1, np.percentile(d, 2.5), np.percentile(d, 97.5))))
    pr()
    pr("  6.4 THE SAME EXCESS AS A YAW RATE -- what 'the car rotated more than I wanted' actually is.")
    pr("      os deg/s = (achieved - asked) / v, in degrees; os deg(2 s) = the heading error it builds in 2 s.")
    pr("      %-5s %-12s %8s %9s %11s %11s %13s" % ("route", "v band", "secs", "|des|", "os m/s^2", "os deg/s", "os deg (2 s)"))
    for t in NEW + ("r35",):
        for lo, hi in V_BANDS:
            F = band_frames(t, lo, hi)
            if F["n"] < 200:
                continue
            os_a = float(np.median(F["y"] - F["x"]))
            os_w = np.degrees(os_a / max(F["v"], 0.5))
            pr("      %-5s %-12s %8.0f %9.2f %+11.3f %+11.2f %+13.2f" % (
                t, "%g-%g m/s" % (lo, hi), F["n"] / FS, float(np.median(F["x"])), os_a, os_w, os_w * 2))
        pr()


# ================================================================================================== 7
def section7():
    pr("")
    pr("=" * 172)
    pr("SECTION 7 -- HIS EXACT SPLIT, TESTED DIRECTLY.  'we understeer on HARD TURNS around corners < 20 mph'")
    pr("  and 'at 20+ mph we oversteer'.  A hard turn is a LARGE ASK, so this stratifies on |des| inside each")
    pr("  speed band -- the same frames and slope estimator as section 6, with the 10 s block bootstrap.")
    pr("=" * 172)
    DB = ((0.2, 0.6), (0.6, 1.2), (1.2, 9.0))
    for lo, hi in ((0, 9), (9, 40)):
        pr("  --- %s   (%s)" % ("v < 9 m/s  = his '< 20 mph'" if lo == 0 else "v >= 9 m/s = his '20+ mph'",
                                "understeer claimed" if lo == 0 else "oversteer claimed"))
        pr("      %-16s" % "|des| band" + "".join("%32s" % ("%s R_road" % t) for t in NEW))
        for dlo, dhi in DB:
            cells = []
            for t in NEW:
                g, _ = gof(t)
                des = g["desiredLateralAccel"]
                sb = M.straight_bias(g)
                sel = (curve_mask(g) & (np.abs(des) >= dlo) & (np.abs(des) < dhi)
                       & (g["v"] >= lo) & (g["v"] < hi) & np.isfinite(g["vyaw"]))
                d = np.sign(des[sel])
                x = np.abs(des[sel])
                y = (g["vyaw"][sel] - sb["vyaw"]) * d
                blk = (g["t"][sel] / 10.0).astype(int)
                s, l, h, nb = block_slope_ci(x, y, blk)
                cells.append("%32s" % ("--" if not np.isfinite(s) else
                                       "%.3f [%.3f,%.3f] %.0fs" % (s, l, h, sel.sum() / FS)))
            pr("      %-16s" % ("%.1f-%.1f m/s^2" % (dlo, dhi)) + "".join(cells))
        pr()
    pr("  7.1 THE SAME, ON THE CONTROLLER'S OWN MEASUREMENT (R_m) -- if R_road and R_m disagree in a cell, the")
    pr("      error there is a MEASUREMENT-SCALE (ratio/tyre) error, not a loop-gain one.")
    for lo, hi in ((0, 9), (9, 40)):
        pr("  --- %s" % ("v < 9 m/s" if lo == 0 else "v >= 9 m/s"))
        pr("      %-16s" % "|des| band" + "".join("%32s" % ("%s R_m" % t) for t in NEW))
        for dlo, dhi in DB:
            cells = []
            for t in NEW:
                g, _ = gof(t)
                des = g["desiredLateralAccel"]
                sb = M.straight_bias(g)
                sel = (curve_mask(g) & (np.abs(des) >= dlo) & (np.abs(des) < dhi)
                       & (g["v"] >= lo) & (g["v"] < hi) & np.isfinite(g["actualLateralAccel"]))
                d = np.sign(des[sel])
                x = np.abs(des[sel])
                y = (g["actualLateralAccel"][sel] - sb["m"]) * d
                blk = (g["t"][sel] / 10.0).astype(int)
                s, l, h, nb = block_slope_ci(x, y, blk)
                cells.append("%32s" % ("--" if not np.isfinite(s) else
                                       "%.3f [%.3f,%.3f] %.0fs" % (s, l, h, sel.sum() / FS)))
            pr("      %-16s" % ("%.1f-%.1f m/s^2" % (dlo, dhi)) + "".join(cells))
        pr()


def main():
    C = {t: M.curves(t)[0] for t in ALLT}
    ok = sectionR(C)
    res = section1(C)
    section2(C)
    section3(C)
    section4(C)
    section5(C)
    section6()
    section7()
    out = os.path.join(HERE, "_scratch", "oversteer_v282_r3a3c.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES))
    json.dump({"repro_ok": bool(ok),
               "decomp": {"%s|%s" % (k[0], k[1]): {kk: list(map(float, vv)) for kk, vv in v.items()}
                          for k, v in res.items()},
               "curves": {t: C[t] for t in ALLT}},
              open(os.path.join(HERE, "oversteer_v282_r3a3c.json"), "w"), indent=1,
              default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    pr("\nwrote %s" % out)


if __name__ == "__main__":
    main()
