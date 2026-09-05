# -*- coding: utf-8 -*-
"""studies/osc-highangle/error_units_and_ki_r3a3c.py -- THE CRUX CHECK, THEN THE ki PRICING.

team-lead's crux: is the standing curve error real in the CONTROLLER'S OWN terms, or an artefact of
comparing the wrong two quantities?

RESOLVED FROM SOURCE FIRST (openpilots/StarPilot @ 3d4c625de, branch Dom -- the flown commit),
`selfdrive/controls/lib/latcontrol_torque.py`:

  233  measurement                = measured_curvature * vEgo**2
  234  future_desired_lateral_accel = desired_curvature * vEgo**2
  271  setpoint                   = expected_lateral_accel + desired_lateral_jerk * lat_delay
  283  low_speed_factor           = (interp(vEgo,[0,10,20,30],[12,10.5,8,5]) / max(vEgo, 1.0))**2
  284  current_kp                 = interp(vEgo, pid._k_p)          # flat 0.8, SteerKP overwrite
  285  error                      = setpoint - measurement
  286  error_with_lsf             = error * (1 + low_speed_factor / max(current_kp, 1e-3))
  293  pid_log.error              = float(error_with_lsf)           <-- THE LOGGED CHANNEL
  546  freeze_integrator          = steer_limited_by_safety or steeringPressed
                                    or vEgo < low_speed_reset_threshold or unwind_detected
  547  output_lataccel            = pid.update(pid_log.error, error_rate=-measurement_rate, ...)
  669  pid_log.actualLateralAccel = float(measurement)              <-- so `m` IS the measurement
  670  pid_log.desiredLateralAccel= float(setpoint)                 <-- so `des` IS the SETPOINT
  275  unwind_detected            = (d(setpoint)/dt < -1.0) and (abs(setpoint) < 0.3)
  543  if vEgo < low_speed_reset_threshold: pid.reset()             # a RESET, not a freeze
   48  MIN_LATERAL_CONTROL_SPEED  = 0.3 ; low_speed_reset_threshold = max(CP.minSteerSpeed, 0.3)
common/pid.py: p = k_p*error ; i += k_i*(1/100)*error ; anti-windup clips i, never the reverse.

TWO CONSEQUENCES THAT ANSWER THE CRUX BEFORE A SINGLE NUMBER IS COMPUTED:
  (a) `desiredLateralAccel` IS the controller's own setpoint and `actualLateralAccel` IS its own
      measurement, so `R_m = m/des` is EXACTLY the ratio the loop is nulling.  It is NOT a comparison
      of the wrong two quantities.  R_m - 1 = -(raw error)/setpoint, identically.
  (b) The LOGGED error is `error_with_lsf`, i.e. ALREADY multiplied by (1 + lsf/kp).  So the
      -0.409 / -0.775 / -0.694 folded curve errors I reported earlier are in LSF-SCALED units and
      OVERSTATE the physical lateral-accel error by 1.04x at 30 m/s and 7.3x at 5 m/s.
  ==> team-lead's premise that the setpoint carries an additive `lsf * desired_curvature` term is the
      UPSTREAM openpilot form.  StarPilot uses the MULTIPLICATIVE form above.  Corrected here.

Everything below verifies (a) and (b) on the wire, then prices ki.

Sections
  1  WIRE VERIFICATION of the three identities (p/error, di/dt/error, error/(des-m))
  2  THE RAW ERROR in curves vs straights, per speed band, per route -- the crux, scored
  3  k_i_eff(v) measured against team-lead's table
  4  THE DIMENSIONLESS GROUP  k_i_eff x T_curve  vs over-delivery, pooled over all five arms
  5  integrator convergence inside curves: is `i` still moving at curve exit?
  6  freeze_integrator: every term's duty, reconstructed from source
  7  direction symmetry -- can the integrator pre-charge across curves?
  8  PRICING ki = 0.25 / 0.35 / 0.50
  9  the SR map above 48 deg vs the inner-loop deadband, separated on the low-speed stratum

Run: python rlog-tools/studies/osc-highangle/error_units_and_ki_r3a3c.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oversteer_v282_r3a3c as X  # noqa: E402

M = X.M
B = X.B
FS = X.FS
LINES = []
ALLT = ("r34", "r35", "r39", "r3c", "r3a")
NEW = ("r39", "r3c", "r3a")
VB = ((0, 4), (4, 9), (9, 16), (16, 22), (22, 40))
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
MIN_SPEED = 1.0
KP_WIRE = 0.8            # measured on the wire on r39/r3c/r3a; 0.6 on r34/r35
KI = 0.15
RESET_V = 0.3
UNWIND_D = -1.0
UNWIND_NEAR_ZERO = 0.3


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def lsf(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2


def kp_of(t):
    return 0.8 if t in ("r39", "r3c", "r3a") else 0.6


def ki_eff(v, kp):
    """The effective integral gain ON THE PHYSICAL lateral-accel error, m/s^2 per s per m/s^2."""
    return KI * (1.0 + lsf(v) / kp)


def blk_ci(x, blk, n=2000, seed=19, stat=np.median):
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    x, blk = x[ok], np.asarray(blk)[ok]
    if len(x) < 50:
        return np.nan, np.nan, np.nan, len(x)
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    st = np.searchsorted(inv[order], np.arange(len(ub)))
    en = np.r_[st[1:], len(order)]
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for k in range(n):
        p = rng.integers(0, len(ub), len(ub))
        out[k] = stat(x[np.concatenate([order[st[j]:en[j]] for j in p])])
    return float(stat(x)), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(x)


# =================================================================================================== 1
def section1():
    pr("=" * 176)
    pr("SECTION 1 -- WIRE VERIFICATION OF THE THREE IDENTITIES.  If these hold, the source reading above is")
    pr("  confirmed on the flown data and the crux is closed.  Computed on the RAW controlsState event stream")
    pr("  (not the 100 Hz grid), engaged frames only, so consecutive samples are consecutive controller frames.")
    pr("=" * 176)
    pr("  identity 1:  p / error_logged  == k_p   (flat, 0.8 on the V282 arms; 0.6 on r34/r35)")
    pr("  identity 2:  di/dt / error_logged == k_i == 0.15   (on frames where the integrator is NOT frozen)")
    pr("  identity 3:  error_logged / (des - m) == 1 + lsf/k_p   <-- THE ONE THAT SETTLES THE UNITS")
    pr()
    pr("  %-5s %-12s %10s %12s %12s %14s %14s %10s" % (
        "route", "v band", "n frames", "p/err", "di/dt/err", "err/(des-m)", "1+lsf/kp pred", "ratio"))
    RAW = {}
    for t in ALLT:
        D = B.load(t)
        ct = D["ctl_t"]
        e = D["ctl_error"]
        p = D["ctl_p"]
        i = D["ctl_i"]
        act = D["ctl_active"]
        des = D["ctl_desiredLateralAccel"]
        m = D["ctl_actualLateralAccel"]
        # vEgo onto the controlsState event clock
        v = np.interp(ct, D["cs_t"], D["cs_v"])
        prs = B.hold(D["cs_t"], D["cs_pressed"], ct)
        dt = np.r_[np.nan, np.diff(ct)]
        di = np.r_[np.nan, np.diff(i)]
        good = (act > 0.5) & np.isfinite(e) & (dt > 0.005) & (dt < 0.02)
        RAW[t] = dict(t=ct, e=e, p=p, i=i, v=v, des=des, m=m, di=di, dt=dt, good=good, prs=prs)
        kp = kp_of(t)
        for lo, hi in VB:
            s = good & (v >= lo) & (v < hi)
            if s.sum() < 500:
                continue
            big = s & (np.abs(e) > 0.05)
            raw = des - m
            bigr = s & (np.abs(raw) > 0.02) & np.isfinite(raw)
            # identity 2 only on non-frozen frames: di != 0 exactly, not pressed, v above reset
            nf = big & (np.abs(di) > 0) & (prs < 0.5) & (v > RESET_V)
            pred = 1.0 + lsf(np.median(v[s])) / kp
            r3 = np.median((e[bigr] / raw[bigr]))
            pr("  %-5s %-12s %10d %12.4f %12.4f %14.4f %14.4f %10.4f" % (
                t, "%g-%g m/s" % (lo, hi), s.sum(),
                np.median(p[big] / e[big]),
                np.median(di[nf] / dt[nf] / e[nf]) if nf.sum() > 100 else np.nan,
                r3, pred, r3 / pred))
        pr()
    pr("  ==> identity 3's last column is the verdict: 1.000 means the LOGGED error is error_with_lsf and the")
    pr("      physical lateral-accel error is (des - m), exactly as the source says.")
    return RAW


# =================================================================================================== 2
def section2(C, RAW):
    pr("=" * 176)
    pr("SECTION 2 -- THE CRUX, SCORED.  The folded error in curves vs straights, per speed band, BOTH ways:")
    pr("    RAW  = (setpoint - measurement) = des - m, in m/s^2.  The physical error.  R_m - 1 = -RAW/des.")
    pr("    LOG  = torqueState.error = RAW * (1 + lsf/kp).  What the PID actually integrates.")
    pr("  Folded on the curve direction.  A standing NEGATIVE folded RAW error = the loop sits ABOVE its own")
    pr("  setpoint = over-delivery.  If the RAW error is ~0 in curves, my headline collapses.")
    pr("=" * 176)
    for t in NEW:
        g, _ = X.gof(t)
        des = g["desiredLateralAccel"]
        stm = np.zeros(len(des), bool)
        dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
            dirf[r["a"]:r["b"]] = r["dir"]
        stm &= g["gapok"]
        ok = X.curve_mask(g)
        st = ok & (np.abs(des) < 0.2) & (g["v"] > 10)
        raw = des - g["actualLateralAccel"]
        pr("  --- %s   (SteerLatAccel %.2f, kp %.1f)" % (t, M.TUNE[t]["laf"], kp_of(t)))
        pr("      %-14s %8s %12s %-20s %12s %12s %12s" % (
            "stratum", "secs", "RAW m/s^2", "RAW 95% CI", "LOG (lsf)", "1+lsf/kp", "RAW/|des|"))
        for lo, hi in VB:
            s = stm & (g["v"] >= lo) & (g["v"] < hi)
            if s.sum() < 300:
                continue
            f = raw[s] * dirf[s]
            b, l, h, n = blk_ci(f, (g["t"][s] / 10.0).astype(int))
            pr("      %-14s %8.0f %12.4f [%8.4f,%8.4f] %12.4f %12.2f %12.4f" % (
                "curve %g-%g" % (lo, hi), s.sum() / FS, b, l, h,
                X.med(g["error"][s] * dirf[s]), 1 + lsf(X.med(g["v"][s])) / kp_of(t),
                b / max(X.med(np.abs(des[s])), 1e-6)))
        sgn = np.sign(g["f"])
        b, l, h, n = blk_ci((raw * sgn)[st], (g["t"][st] / 10.0).astype(int))
        pr("      %-14s %8.0f %12.4f [%8.4f,%8.4f] %12.4f" % (
            "STRAIGHT >10", st.sum() / FS, b, l, h, X.med((g["error"] * sgn)[st])))
        pr()
    pr("  VERDICT LINE: the RAW curve error is the physical over-delivery.  Compare it to the straight-road")
    pr("  row on the same route: if curves carry a standing negative error and straights do not, the loop")
    pr("  really does sit above its setpoint inside curves and pays it back outside them.")


# =================================================================================================== 3
def section3(RAW):
    pr()
    pr("=" * 176)
    pr("SECTION 3 -- k_i_eff(v) MEASURED AGAINST team-lead's TABLE.  k_i_eff = 0.15 * (1 + lsf(v)/kp), the")
    pr("  integral gain on the PHYSICAL lateral-accel error.  Wire column = median of (di/dt)/(des-m) over")
    pr("  non-frozen engaged frames in that band -- an entirely independent route to the same number.")
    pr("=" * 176)
    pr("  %8s %6s %14s %14s %16s %16s" % ("v (m/s)", "mph", "1+lsf/0.8", "k_i_eff pred", "k_i_eff WIRE r39", "wire/pred"))
    R = RAW["r39"]
    for v in (5, 10, 15, 20, 25, 30):
        pred = ki_eff(v, 0.8)
        s = (R["good"] & (R["v"] >= v - 2.5) & (R["v"] < v + 2.5) & (np.abs(R["di"]) > 0)
             & (R["prs"] < 0.5) & (R["v"] > RESET_V) & (np.abs(R["des"] - R["m"]) > 0.05))
        w = np.median(R["di"][s] / R["dt"][s] / (R["des"] - R["m"])[s]) if s.sum() > 200 else np.nan
        pr("  %8.0f %6.0f %14.3f %14.3f %16.3f %16.3f" % (
            v, v * 2.23694, 1 + lsf(v) / 0.8, pred, w, w / pred))
    pr("  ==> the integrator is %.1fx weaker at 25 m/s than at 5 m/s, by construction." % (ki_eff(5, 0.8) / ki_eff(25, 0.8)))
    pr("      Time to build i by 0.20 (a typical curve's worth) at a standing raw error of 0.15 m/s^2:")
    for v in (5, 10, 15, 20, 25, 30):
        pr("        v %2d m/s : di/dt = %.4f /s  ->  %5.1f s" % (v, ki_eff(v, 0.8) * 0.15, 0.20 / (ki_eff(v, 0.8) * 0.15)))


# =================================================================================================== 4
def section4(C):
    pr()
    pr("=" * 176)
    pr("SECTION 4 -- THE DIMENSIONLESS GROUP.  If team-lead's mechanism is right, the residual over-delivery")
    pr("  should collapse against  G = k_i_eff(v) x T_curve  -- the integrator's chance to converge inside the")
    pr("  curve it is in.  Pooled over ALL FIVE arms and all speeds; the curve is the unit.")
    pr("  over-delivery = R_m - 1 = (m - des)/des in the curve-steady window, direction-folded.")
    pr("=" * 176)
    rows = []
    for t in ALLT:
        g, _ = X.gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        kp = kp_of(t)
        for r in C[t]:
            if r["b"] - r["a"] < int(2.5 * FS) or r["des"] <= 0.4:
                continue
            sl = slice(r["a"] + 150, r["b"])
            big = np.abs(des[sl]) > 0.4
            if big.sum() < 10 or not g["gapok"][r["a"]:r["b"]].all():
                continue
            rm = X.med((g["actualLateralAccel"][sl][big] - sb["m"]) / des[sl][big])
            rows.append(dict(tag=t, G=ki_eff(r["v"], kp) * r["dur"], rm=rm, v=r["v"], dur=r["dur"],
                             kie=ki_eff(r["v"], kp)))
    rows = [r for r in rows if np.isfinite(r["rm"])]
    pr("  n curves pooled: %d   (r34 %d, r35 %d, r39 %d, r3c %d, r3a %d)" % (
        len(rows), *[sum(1 for r in rows if r["tag"] == t) for t in ALLT]))
    pr()
    pr("  %-18s %8s %10s %10s %14s %-22s" % ("G = k_i_eff x T", "curves", "med v", "med T", "R_m - 1", "95% CI"))
    edges = [0, 0.5, 1.0, 2.0, 4.0, 8.0, 1e9]
    for a, b in zip(edges[:-1], edges[1:]):
        sel = [r for r in rows if a <= r["G"] < b]
        if len(sel) < 5:
            pr("  %-18s %8d  (too few)" % ("%.1f - %s" % (a, "inf" if b > 1e8 else "%.1f" % b), len(sel)))
            continue
        vals = np.array([r["rm"] - 1 for r in sel])
        rng = np.random.default_rng(3)
        bs = np.median(vals[rng.integers(0, len(vals), (4000, len(vals)))], axis=1)
        pr("  %-18s %8d %10.1f %10.1f %14.4f [%+.4f, %+.4f]" % (
            "%.1f - %s" % (a, "inf" if b > 1e8 else "%.1f" % b), len(sel),
            np.median([r["v"] for r in sel]), np.median([r["dur"] for r in sel]),
            np.median(vals), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
    x = np.log(np.array([r["G"] for r in rows]))
    y = np.array([r["rm"] - 1 for r in rows])
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    pr()
    pr("  Spearman rho(over-delivery, G) over the pooled curves = %+.3f   (n %d)" % (
        float(np.corrcoef(rx, ry)[0, 1]), len(rows)))
    pr("  Spearman rho(over-delivery, curve v)                  = %+.3f" % (
        float(np.corrcoef(np.argsort(np.argsort([r["v"] for r in rows])), ry)[0, 1])))
    pr("  Spearman rho(over-delivery, curve duration)           = %+.3f" % (
        float(np.corrcoef(np.argsort(np.argsort([r["dur"] for r in rows])), ry)[0, 1])))
    pr("  (a NEGATIVE rho against G is the prediction: more integrator-chance -> less residual over-delivery.")
    pr("   If rho against G is no stronger than against v alone, G adds nothing and the mechanism is unproven.)")


# =================================================================================================== 5
def section5(C):
    pr()
    pr("=" * 176)
    pr("SECTION 5 -- IS THE INTEGRATOR STILL MOVING AT CURVE EXIT?  If `i` has flattened while the raw error")
    pr("  is still non-zero, team-lead's slow-convergence mechanism is WRONG and something else pins it.")
    pr("  'Still moving' = the mean di/dt over the last 1.0 s has the same sign as over the whole curve AND")
    pr("  |mean di/dt| in the last second is > 25 % of |mean di/dt| over the curve.")
    pr("=" * 176)
    pr("  %-5s %-12s %8s %14s %16s %16s %14s" % (
        "route", "v band", "curves", "still moving", "med |di/dt| curve", "med |di/dt| last 1s", "med raw err end"))
    for t in NEW:
        g, _ = X.gof(t)
        des = g["desiredLateralAccel"]
        raw = des - g["actualLateralAccel"]
        di = np.r_[0.0, np.diff(g["i"])] * FS
        for lo, hi in VB:
            sel = [r for r in C[t] if r["dur"] >= 3.0 and lo <= r["v"] < hi and r["des"] > 0.4
                   and g["gapok"][r["a"]:r["b"]].all()]
            if len(sel) < 4:
                continue
            mv, dc, dl, re_ = [], [], [], []
            for r in sel:
                d = r["dir"]
                whole = di[r["a"] + 50:r["b"]] * d
                last = di[max(r["a"], r["b"] - 100):r["b"]] * d
                a1, a2 = float(np.nanmean(whole)), float(np.nanmean(last))
                mv.append(np.sign(a1) == np.sign(a2) and abs(a2) > 0.25 * abs(a1))
                dc.append(abs(a1))
                dl.append(abs(a2))
                re_.append(float(np.nanmedian(raw[max(r["a"], r["b"] - 100):r["b"]] * d)))
            pr("  %-5s %-12s %8d %13.2f  %16.4f %16.4f %14.4f" % (
                t, "%g-%g m/s" % (lo, hi), len(sel), float(np.mean(mv)),
                float(np.median(dc)), float(np.median(dl)), float(np.median(re_))))
        pr()
    pr("  5.1 THE CLOSED-LOOP TIME CONSTANT of the folded RAW error inside curves (fixed cohort, curves >= 5 s).")
    pr("      Cohort-mean e(t) fitted as e_inf + (e0 - e_inf)*exp(-t/tau) by grid search on tau.")
    pr("      %-5s %-12s %8s %10s %10s %10s %14s" % ("route", "v band", "curves", "e0", "e_inf", "tau (s)", "med T_curve"))
    for t in NEW:
        g, _ = X.gof(t)
        raw = g["desiredLateralAccel"] - g["actualLateralAccel"]
        for lo, hi in VB:
            sel = [r for r in C[t] if r["dur"] >= 5.0 and lo <= r["v"] < hi and r["des"] > 0.4
                   and g["gapok"][r["a"]:r["b"]].all()]
            if len(sel) < 4:
                continue
            n = int(5.0 * FS)
            traj = np.nanmean(np.stack([raw[r["a"]:r["a"] + n] * r["dir"] for r in sel]), axis=0)
            tt = np.arange(n) / FS
            best = (1e18, np.nan, np.nan, np.nan)
            for tau in np.arange(0.2, 12.0, 0.05):
                A = np.c_[np.ones(n), np.exp(-tt / tau)]
                co, *_ = np.linalg.lstsq(A, traj, rcond=None)
                r2 = float(np.sum((traj - A @ co) ** 2))
                if r2 < best[0]:
                    best = (r2, float(co[0] + co[1]), float(co[0]), tau)
            pr("      %-5s %-12s %8d %10.4f %10.4f %10.2f %14.1f" % (
                t, "%g-%g m/s" % (lo, hi), len(sel), best[1], best[2], best[3],
                float(np.median([r["dur"] for r in sel]))))
        pr()
    pr("      CURVE-DURATION DISTRIBUTION (all curves, |des| > 0.4), the thing tau must be compared against:")
    for t in NEW:
        d = [r["dur"] for r in C[t] if r["des"] > 0.4]
        if not d:
            continue
        pr("      %-5s n %3d  p25 %.1f  p50 %.1f  p75 %.1f  p90 %.1f  max %.1f s" % (
            t, len(d), *np.percentile(d, [25, 50, 75, 90]), max(d)))


# =================================================================================================== 6
def section6(C, RAW):
    pr()
    pr("=" * 176)
    pr("SECTION 6 -- freeze_integrator, EVERY TERM.  Source (line 546):")
    pr("    freeze = steer_limited_by_safety  or  steeringPressed  or  vEgo < 0.3  or  unwind_detected")
    pr("  and line 543 additionally RESETS the whole PID below 0.3 m/s.  unwind_detected is reconstructed")
    pr("  exactly from the LOGGED setpoint (line 275: d(setpoint)/dt < -1.0 AND |setpoint| < 0.3), since")
    pr("  `desiredLateralAccel` IS that setpoint.  steer_limited_by_safety is NOT logged; instead the")
    pr("  EMPIRICAL freeze is measured directly -- frames where `i` did not change at all while |error| > 0.05.")
    pr("=" * 176)
    pr("  %-5s %11s %12s %12s %12s %14s %16s" % (
        "route", "engaged fr", "pressed", "v < 0.3", "unwind", "any of the 3", "EMPIRICAL freeze"))
    for t in NEW:
        R = RAW[t]
        ok = R["good"]
        des = R["des"]
        dsdt = np.r_[0.0, np.diff(des)] / np.where(R["dt"] > 0, R["dt"], np.nan)
        unwind = (dsdt < UNWIND_D) & (np.abs(des) < UNWIND_NEAR_ZERO)
        prs = R["prs"] > 0.5
        slow = R["v"] < RESET_V
        anyf = prs | slow | unwind
        emp = ok & (np.abs(R["e"]) > 0.05) & (R["di"] == 0)
        base = ok & (np.abs(R["e"]) > 0.05)
        pr("  %-5s %11d %12.4f %12.4f %12.4f %14.4f %16.4f" % (
            t, ok.sum(), float(np.mean(prs[ok])), float(np.mean(slow[ok])), float(np.mean(unwind[ok])),
            float(np.mean(anyf[ok])), float(emp.sum() / max(base.sum(), 1))))
    pr()
    pr("  6.1 THE SAME, INSIDE CURVES ONLY (the stratum the standing error lives in), on the 100 Hz grid:")
    pr("  %-5s %10s %12s %12s %12s %14s" % ("route", "curve s", "pressed", "v < 0.3", "unwind", "any"))
    for t in NEW:
        g, _ = X.gof(t)
        des = g["desiredLateralAccel"]
        stm = np.zeros(len(des), bool)
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
        stm &= g["gapok"]
        dsdt = np.r_[0.0, np.diff(des)] * FS
        unwind = (dsdt < UNWIND_D) & (np.abs(des) < UNWIND_NEAR_ZERO)
        prs = g["pressed"] > 0.5
        slow = g["v"] < RESET_V
        pr("  %-5s %10.0f %12.4f %12.4f %12.4f %14.4f" % (
            t, stm.sum() / FS, float(np.mean(prs[stm])), float(np.mean(slow[stm])),
            float(np.mean(unwind[stm])), float(np.mean((prs | slow | unwind)[stm]))))
    pr()
    pr("  6.1b THE EMPIRICAL FREEZE INSIDE CURVES, and its attribution.  `di == 0` exactly while |error| > 0.05.")
    pr("      Anti-windup (common/pid.py) freezes i whenever the TEST CONTROL p+i+d+f leaves [-LAF, +LAF],")
    pr("      so that column is the candidate explanation for any freeze the three named terms do not cover.")
    pr("      %-5s %10s %14s %14s %16s %18s" % (
        "route", "curve s", "empirical", "named 3 cover", "UNEXPLAINED", "|p+i+d+f| >= LAF"))
    for t in NEW:
        g, _ = X.gof(t)
        des = g["desiredLateralAccel"]
        stm = np.zeros(len(des), bool)
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
        stm &= g["gapok"]
        dsdt = np.r_[0.0, np.diff(des)] * FS
        named = ((g["pressed"] > 0.5) | (g["v"] < RESET_V)
                 | ((dsdt < UNWIND_D) & (np.abs(des) < UNWIND_NEAR_ZERO)))
        di = np.r_[0.0, np.diff(g["i"])]
        tc = np.abs(g["f"] + g["p"] + g["i"] + g["d"])
        base = stm & (np.abs(g["error"]) > 0.05)
        emp = base & (di == 0)
        pr("      %-5s %10.0f %14.4f %14.4f %16.4f %18.4f" % (
            t, stm.sum() / FS, emp.sum() / max(base.sum(), 1),
            float(np.mean(named[emp])) if emp.any() else np.nan,
            float(np.mean(~named[emp])) * emp.sum() / max(base.sum(), 1) if emp.any() else np.nan,
            float(np.mean(tc[base] >= M.TUNE[t]["laf"]))))
    pr()
    pr("  6.2 WHERE unwind FIRES, route-wide: it needs |setpoint| < 0.3, i.e. NEAR-STRAIGHT, and a falling")
    pr("      setpoint -- so by construction it cannot be freezing the integrator INSIDE a loaded curve.")
    for t in NEW:
        R = RAW[t]
        ok = R["good"]
        dsdt = np.r_[0.0, np.diff(R["des"])] / np.where(R["dt"] > 0, R["dt"], np.nan)
        u = ok & (dsdt < UNWIND_D) & (np.abs(R["des"]) < UNWIND_NEAR_ZERO)
        pr("      %-5s unwind frames %6d (%.4f of engaged) ; med |setpoint| there %.3f ; med v %.1f m/s" % (
            t, u.sum(), u.sum() / max(ok.sum(), 1),
            float(np.median(np.abs(R["des"][u]))) if u.any() else np.nan,
            float(np.median(R["v"][u])) if u.any() else np.nan))


# =================================================================================================== 7
def section7(C):
    pr()
    pr("=" * 176)
    pr("SECTION 7 -- CAN THE INTEGRATOR PRE-CHARGE ACROSS CURVES?  It accumulates the UNFOLDED error, so it")
    pr("  can only carry a bias that is CONSTANT in sign.  A bias that reverses with turn direction cancels")
    pr("  in its accumulator.  Folded vs unfolded, over the whole drive and in curves.")
    pr("=" * 176)
    pr("  %-5s %14s %14s %14s %14s %10s %10s" % (
        "route", "FOLDED err", "UNFOLDED err", "FOLDED i", "UNFOLDED i", "L curves", "R curves"))
    for t in NEW:
        g, _ = X.gof(t)
        des = g["desiredLateralAccel"]
        raw = des - g["actualLateralAccel"]
        stm = np.zeros(len(des), bool)
        dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
            dirf[r["a"]:r["b"]] = r["dir"]
        stm &= g["gapok"]
        nl = sum(1 for r in C[t] if r["dir"] > 0)
        nr = sum(1 for r in C[t] if r["dir"] < 0)
        pr("  %-5s %14.4f %14.4f %14.4f %14.4f %10d %10d" % (
            t, float(np.nanmean((raw * dirf)[stm])), float(np.nanmean(raw[stm])),
            float(np.nanmean((g["i"] * dirf)[stm])), float(np.nanmean(g["i"][stm])), nl, nr))
    pr("  ==> a large FOLDED error with a near-zero UNFOLDED error is the signature of a DIRECTION-REVERSING")
    pr("      bias: the integrator cannot pre-charge against it, because left and right curves cancel.")


# =================================================================================================== 8
def section8(C):
    pr()
    pr("=" * 176)
    pr("SECTION 8 -- PRICING ki.  REACHABILITY FIRST: ki is NOT a Galaxy toggle.  It is the module constant")
    pr("  HONDA_ACCORD_TORQUE_KI = 0.15 at selfdrive/controls/lib/latcontrol_vehicle_tunes.py:78 (verified in")
    pr("  the flown tree, openpilots/StarPilot @ 3d4c625de).  controlsd overwrites only _k_p (SteerKP); there")
    pr("  is no _k_i overwrite, so changing it requires a ONE-LINE FORK EDIT.  I have not made it.")
    pr("=" * 176)
    pr("  8.1 CONVERGENCE.  Time for the integrator to supply the standing raw curve error at each ki,")
    pr("      against that band's median curve duration.  t_needed = |raw err| / (ki_eff * |raw err|) is")
    pr("      independent of the error size to first order = 1/k_i_eff; the table gives 1/k_i_eff directly.")
    pr("      %-12s %14s %14s %14s %14s %16s" % (
        "v (m/s)", "ki=0.15 (now)", "ki=0.25", "ki=0.35", "ki=0.50", "med T_curve r39"))
    durs = {}
    g39, _ = X.gof("r39")
    for lo, hi in VB:
        d = [r["dur"] for r in C["r39"] if lo <= r["v"] < hi and r["des"] > 0.4]
        durs[lo] = float(np.median(d)) if d else np.nan
    for v, lo in ((5, 4), (9, 4), (13, 9), (19, 16), (26, 22)):
        cells = [1.0 / (k * (1 + lsf(v) / 0.8)) for k in (0.15, 0.25, 0.35, 0.50)]
        pr("      %-12.0f %14.2f %14.2f %14.2f %14.2f %16.1f" % (v, *cells, durs.get(lo, np.nan)))
    pr("      (units: seconds of 1/e closure.  A cell far ABOVE the T_curve column is an integrator that")
    pr("       cannot converge inside the curve it is in.)")
    pr()
    pr("  8.2 INTEGRATOR HEADROOM.  Open-loop upper bound: scaling ki by x scales the accumulated i by x for")
    pr("      the same error trajectory.  This OVERSTATES the real rise (the loop closes and the error falls),")
    pr("      so read it as a ceiling, not a prediction.")
    pr("      %-5s %8s %10s %12s %12s %12s %12s" % ("route", "bound", "max|i| now", "x1.67 (.25)", "x2.33 (.35)", "x3.33 (.50)", "first breach"))
    for t in NEW:
        g, _ = X.gof(t)
        ok = X.curve_mask(g)
        imax = float(np.nanmax(np.abs(g["i"][ok])))
        bound = M.TUNE[t]["laf"]
        proj = [imax * k / 0.15 for k in (0.25, 0.35, 0.50)]
        first = next((k for k, p in zip((0.25, 0.35, 0.50), proj) if p > bound), None)
        pr("      %-5s %8.3f %10.3f %12.3f %12.3f %12.3f %12s" % (
            t, bound, imax, *proj, ("ki=%.2f" % first) if first else "none <= 0.50"))
    pr("      NOTE: anti-windup (common/pid.py) CLIPS i at the bound, it does not unwind the loop, and")
    pr("      `saturated` is 0.0000 on all three routes today, so a breach means clipping, not instability.")
    pr()
    pr("  8.3 STABILITY COST, COMPUTED.  A PI controller's phase is -90 + atan(w/wz) with the zero at")
    pr("      wz = k_i/k_p rad/s (the lsf factor multiplies BOTH p and i, so it cancels out of the zero).")
    pr("      wz(0.15) = 0.15/0.8 = 0.1875 rad/s = 0.0298 Hz.  Added lag = phase(ki_new) - phase(ki_now):")
    pr("      %-12s" % "freq (Hz)" + "".join("%16s" % ("ki=%.2f" % k) for k in (0.25, 0.35, 0.50)))
    for f in (0.1, 0.3, 0.5, 0.75, 1.0, 2.0, 5.05, 7.3, 20.3):
        w = 2 * np.pi * f
        base = np.degrees(np.arctan(w / (0.15 / 0.8)))
        cells = ["%16.3f" % (np.degrees(np.arctan(w / (k / 0.8))) - base) for k in (0.25, 0.35, 0.50)]
        pr("      %-12s" % ("%.2f%s" % (f, {5.05: " (lag pole)", 7.3: " (RING)", 20.3: " (grind)"}.get(f, "")))
           + "".join(cells))
    pr("      (negative = ADDED LAG, in degrees.  The command band is 0-0.75 Hz; the 7.3 Hz ring sits at")
    pr("       |L| = 0.980, so the number in the RING row is the one that must be small.)")


# =================================================================================================== 9
def section9(C):
    pr()
    pr("=" * 176)
    pr("SECTION 9 -- THE TWO CANDIDATE CAUSES OF THE LOW-SPEED SHORTFALL, SEPARATED.")
    pr("  (i)  tunepath's finding: the SR map is ~8-9 % too aggressive ABOVE 48 deg.  A MAP error moves the")
    pr("       MEASUREMENT, so it shows in 1/rho = road/m and NOT in R_m.")
    pr("  (ii) the inner-loop P-only deadband: the wheel stalls against stiction.  A DELIVERY failure shows")
    pr("       in R_m = m/des (the loop cannot reach its own setpoint) and NOT in 1/rho.")
    pr("  They are orthogonal on these two instruments, so the split is identifiable.  v < 9 m/s only.")
    pr("=" * 176)
    pr("  %-5s %-18s %8s %10s %10s %10s %12s" % (
        "route", "|sa| stratum", "secs", "R_m", "1/rho", "R_road", "med |sa| deg"))
    for t in NEW:
        g, _ = X.gof(t)
        des = g["desiredLateralAccel"]
        sb = M.straight_bias(g)
        stm = np.zeros(len(des), bool)
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
        stm &= g["gapok"] & (g["v"] < 9) & (np.abs(des) > 0.4)
        for nm, sel0 in (("|sa| < 48 (flat 16)", np.abs(g["sa_deg"]) < 48),
                         ("|sa| >= 48 (mapped)", np.abs(g["sa_deg"]) >= 48),
                         ("|sa| >= 121", np.abs(g["sa_deg"]) >= 121)):
            s = stm & sel0
            if s.sum() < 150:
                continue
            m_ = g["actualLateralAccel"][s] - sb["m"]
            rd = g["vyaw"][s] - sb["vyaw"]
            pr("  %-5s %-18s %8.0f %10.3f %10.3f %10.3f %12.0f" % (
                t, nm, s.sum() / FS, X.med(m_ / des[s]), X.med(rd / m_), X.med(rd / des[s]),
                X.med(np.abs(g["sa_deg"][s]))))
        pr()
    pr("  READ: if 1/rho FALLS below 1 in the |sa| >= 48 rows while R_m holds, that is the MAP being too")
    pr("  aggressive (tunepath's ~9 %).  If R_m falls while 1/rho holds, that is the DEADBAND.  Both falling")
    pr("  means both contribute and the low-speed shortfall has two independent causes.")


# =================================================================================================== 10
def section10(C):
    pr()
    pr("=" * 176)
    pr("SECTION 10 -- DOES THE INTEGRATOR'S RAMP REACH THE ROAD?  THE DECISIVE TEST.")
    pr("  Section 5 says the raw error settles in tau ~ 0.9 s to a NON-ZERO asymptote inside curves that last")
    pr("  5-6 s, while section 5's own di/dt column says `i` is STILL RAMPING at curve exit in 58-75 % of them.")
    pr("  Those two facts together are NOT slow convergence -- they are an integrator that is ramping while")
    pr("  the error ignores it.  Per curve: how much did i move, how much did the delivered torque move, and")
    pr("  how much did the error and the measurement move?  If d(error) does not track d(i), the outer")
    pr("  integrator is not the thing pinning the equilibrium.")
    pr("=" * 176)
    pr("  Windows: first 1.0 s of the steady stratum vs last 1.0 s of the curve, curves >= 4 s, |des| > 0.4.")
    pr("  %-5s %8s %12s %12s %12s %12s %14s %14s" % (
        "route", "curves", "d i", "d |tq|", "d raw err", "d m", "rho(di,derr)", "rho(di,dm)"))
    POOL = []
    for t in NEW:
        g, _ = X.gof(t)
        des = g["desiredLateralAccel"]
        raw = des - g["actualLateralAccel"]
        rows = []
        for r in C[t]:
            if r["dur"] < 4.0 or r["des"] <= 0.4 or not g["gapok"][r["a"]:r["b"]].all():
                continue
            d = r["dir"]
            w1 = slice(r["a"] + 150, r["a"] + 250)
            w2 = slice(max(r["a"] + 250, r["b"] - 100), r["b"])
            if w2.stop - w2.start < 50:
                continue
            rows.append(dict(
                di=float(np.nanmean(g["i"][w2] * d) - np.nanmean(g["i"][w1] * d)),
                dq=float(np.nanmean(np.abs(g["tq"][w2])) - np.nanmean(np.abs(g["tq"][w1]))),
                de=float(np.nanmean(raw[w2] * d) - np.nanmean(raw[w1] * d)),
                dm=float(np.nanmean(g["actualLateralAccel"][w2] * d) - np.nanmean(g["actualLateralAccel"][w1] * d)),
                dd=float(np.nanmean(des[w2] * d) - np.nanmean(des[w1] * d))))
        if len(rows) < 5:
            pr("  %-5s %8d  (too few curves)" % (t, len(rows)))
            continue
        POOL += rows
        di = np.array([r["di"] for r in rows])
        de = np.array([r["de"] for r in rows])
        dm = np.array([r["dm"] for r in rows])

        def sp(a, b):
            return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])

        pr("  %-5s %8d %12.4f %12.4f %12.4f %12.4f %14.3f %14.3f" % (
            t, len(rows), float(np.median(di)), float(np.median([r["dq"] for r in rows])),
            float(np.median(de)), float(np.median(dm)), sp(di, de), sp(di, dm)))
    if len(POOL) >= 12:
        di = np.array([r["di"] for r in POOL])
        de = np.array([r["de"] for r in POOL])
        dm = np.array([r["dm"] for r in POOL])
        dd = np.array([r["dd"] for r in POOL])

        def sp(a, b):
            return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])

        pr()
        pr("  POOLED over the three V282 arms, n = %d curves:" % len(POOL))
        pr("    rho(d i, d raw error) = %+.3f   <-- STRONGLY NEGATIVE is 'the integrator is working'" % sp(di, de))
        pr("    rho(d i, d measurement) = %+.3f <-- POSITIVE is 'the integrator reaches the road'" % sp(di, dm))
        pr("    rho(d i, d setpoint)  = %+.3f   <-- if this dominates, i is just tracking the ASK, not correcting" % sp(di, dd))
        gain = float(dm @ di / (di @ di)) if di @ di else np.nan
        pr("    closed-loop gain  d(measurement) / d(i)  = %+.3f  (1.0 would be full authority in lat-accel units)" % gain)
        pr("    median |d i| = %.4f over a curve, against a standing raw error of ~0.10-0.13 m/s^2." % np.median(np.abs(di)))


def main():
    C = {t: M.curves(t)[0] for t in ALLT}
    RAW = section1()
    section2(C, RAW)
    section3(RAW)
    section4(C)
    section5(C)
    section6(C, RAW)
    section7(C)
    section8(C)
    section9(C)
    section10(C)
    out = os.path.join(HERE, "_scratch", "error_units_and_ki_r3a3c.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES))
    pr("\nwrote %s" % out)


if __name__ == "__main__":
    main()
