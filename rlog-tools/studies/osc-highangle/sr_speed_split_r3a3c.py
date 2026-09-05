# -*- coding: utf-8 -*-
"""studies/osc-highangle/sr_speed_split_r3a3c.py -- IS THE ANGLE->CURVATURE MISMATCH A FLAT SCALE ERROR
OR A SPEED-DEPENDENT ONE?

team-lead's ruling, 2026-09-04: the operator reports UNDERSTEER below 20 mph and OVERSTEER above, and
"a single flat steer-ratio number cannot produce a sign flip across speed".  Correct.  So the question
is how the controller's measurement error splits into

  (1) a FLAT SCALE component  -- the steering ratio itself.  Reachable by the SR level / the SR map.
  (2) a SPEED-DEPENDENT component -- openpilot's own slip / understeer term.  Reachable ONLY by the
      tyre-stiffness numbers, never by a ratio.

THE ARITHMETIC, from opendbc/car/vehicle_model.py (calc_curvature / curvature_factor), unchanged:

    curvature = (sa / sR) * cfac(v) + roll_compensation
    cfac(v)   = 1 / (1 - sf * v^2) / L        sf = m*(cF*aF - cR*aR) / (L^2 * cF * cR)

Invert it against the ROAD (yaw_cal / v, which carries no steering ratio and no tyre model):

    denom := curv_road - rollcomp = sa / (sR_true * L * (1 - sf_true * v^2))
    ==>  Z(v) := sa / (L * denom) = sR_true - (sR_true * sf_true) * v^2         <-- LINEAR IN v^2

So one straight-line fit of Z on v^2 separates the two components with no assumption at all:
    intercept  = sR_true      -> compare to the ratio the MAP actually served  (the FLAT component)
    -slope/int = sf_true      -> compare to the sf the shipped carParams imply (the SPEED component)

Sections
  A  the stratum, and sR_eff by speed band with block-bootstrap CIs
  B  the Z-vs-v^2 fit: sR_true and sf_true, per route, with CIs; against the shipped values
  C  the DECOMPOSITION -- how much of the measured 1/rho spread across speed each component explains
  D  the COUNTERFACTUAL -- what a flat SR change does to every band at once

Run: python rlog-tools/studies/osc-highangle/sr_speed_split_r3a3c.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oversteer_v282_r3a3c as X  # noqa: E402

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


def stratum(g):
    """Quasi-steady, well-conditioned, laterally engaged frames where the kinematic relation holds.
    - lateral engagement is cc_lat AND the 0x18F SCA bit, so r3c's 1.05 s seg-7 EPS control drop
      (latActive TRUE while STEER_CONTROL_ACTIVE = 0) is excluded, as extract3a3c required.
    - |steeringRate| < 20 deg/s keeps it quasi-steady: the kinematic bicycle relation is a steady-state
      identity and does not hold through a fast transient.
    - the r3a segment-10 hole is excluded by gapok.
    """
    j = np.clip(np.searchsorted(g["lp_t"], g["t"]) - 1, 0, len(g["lp_t"]) - 1)
    return (X.curve_mask(g) & (g["sca"] > 0.5) & g["lp_calok"][j]
            & (np.abs(g["sa_deg"]) > 2.0) & (np.abs(g["rate"]) < 20.0)
            & np.isfinite(g["yaw_cal"]) & np.isfinite(g["rollcomp"]))


def parts(t):
    g, cp = X.gof(t)
    L = cp["wheelbase"]
    aF = cp["centerToFront"]
    aR = L - aF
    cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]
    sf = cp["mass"] * (cF * aF - cR * aR) / (L ** 2 * cF * cR)
    s = stratum(g)
    curv_road = -g["yaw_cal"] / np.maximum(g["v"], 1e-3)
    denom = curv_road - g["rollcomp"]
    return dict(g=g, cp=cp, L=L, sf=sf, s=s, denom=denom, curv_road=curv_road)


def tls_ci(x, y, blk, n=2000, seed=13):
    """TLS slope of y on x (through the origin, the same estimator section A uses), with a 10 s
    contiguous-block bootstrap."""
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, blk = x[ok], y[ok], blk[ok]
    if len(x) < 100:
        return np.nan, np.nan, np.nan, len(x)

    def sl(xx, yy):
        sxx, syy, sxy = float(xx @ xx), float(yy @ yy), float(xx @ yy)
        return float((syy - sxx + np.hypot(syy - sxx, 2 * sxy)) / (2 * sxy)) if sxy else np.nan

    base = sl(x, y)
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    st = np.searchsorted(inv[order], np.arange(len(ub)))
    en = np.r_[st[1:], len(order)]
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for k in range(n):
        p = rng.integers(0, len(ub), len(ub))
        ii = np.concatenate([order[st[j]:en[j]] for j in p])
        out[k] = sl(x[ii], y[ii])
    return base, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(x)


def main():
    P = {t: parts(t) for t in ALLT}

    pr("=" * 176)
    pr("SECTION A -- sR_eff BY SPEED BAND.  'The steering ratio that WOULD have made the controller's")
    pr("  measurement equal the road', solved from the wire.  TLS of cfac(v)*sa on (curv_road - rollcomp),")
    pr("  10 s contiguous-block bootstrap.  cfac is the SHIPPED one, so sR_eff absorbs any slip-model error --")
    pr("  which is exactly why its variation ACROSS SPEED is the speed-dependent component made visible.")
    pr("  Stratum: laterally engaged (cc_lat AND 0x18F SCA), not pressed, calibrated, |sa| > 2 deg,")
    pr("  |steeringRate| < 20 deg/s, r3a's segment-10 hole excluded.")
    pr("=" * 176)
    pr("  shipped vehicle model: " + " | ".join(
        "%s L %.3f sf %.3e" % (t, P[t]["L"], P[t]["sf"]) for t in ALLT))
    pr()
    pr("  DIRECTION, derived once so it cannot be got backwards:  the controller computes")
    pr("     curv_meas = cfac_ship(v) * sa / SR_served, and sR_eff is DEFINED by curv_road = cfac_ship*sa/sR_eff.")
    pr("     ==>  rho = curv_meas / curv_road = sR_eff / SR_served,  and  1/rho = road/measurement = SR_served / sR_eff.")
    pr("     1/rho > 1 : the road turns MORE than the controller measures -> it UNDER-reads -> it pushes -> OVER-delivery.")
    pr("     1/rho < 1 : it OVER-reads -> it backs off -> UNDER-delivery.")
    pr("  %-5s %-12s %8s %12s %-20s %12s %12s %12s" % (
        "route", "v band", "secs", "sR_eff", "sR_eff 95% CI", "SR map served", "1/rho", "med |sa| deg"))
    SR = {}
    for t in ALLT:
        p = P[t]
        g = p["g"]
        for lo, hi in VB:
            s = p["s"] & (g["v"] >= lo) & (g["v"] < hi)
            if s.sum() < 300:
                continue
            b, l, h, n = tls_ci(p["denom"][s], (g["cfac"] * g["sa"])[s], (g["t"][s] / 10.0).astype(int))
            srm = X.med(g["sr_map"][s])
            SR[(t, lo)] = (b, l, h, srm, s.sum() / FS)
            pr("  %-5s %-12s %8.0f %12.2f [%7.2f, %7.2f]  %12.2f %12.3f %12.0f" % (
                t, "%g-%g m/s" % (lo, hi), s.sum() / FS, b, l, h, srm, srm / b if b else np.nan,
                X.med(np.abs(g["sa_deg"][s]))))
        pr()
    pr("  A crossing of 1.00 across speed IS a sign flip, and NO flat ratio can produce one: scaling the served")
    pr("  ratio by k multiplies EVERY band's 1/rho by the same k.  Section D prices that out.")

    pr()
    pr("=" * 176)
    pr("SECTION B -- THE FIT THAT SEPARATES THEM.   Z(v) = sa / (L * denom) = sR_true - sR_true*sf_true*v^2")
    pr("  Z is estimated per speed band by the SAME TLS (of sa/L on denom), then a straight line is fitted")
    pr("  across bands against the band's median v^2.  intercept = sR_true (FLAT); slope -> sf_true (SPEED).")
    pr("=" * 176)
    FIT = {}
    for t in ALLT:
        p = P[t]
        g = p["g"]
        pts = []
        for lo, hi in VB:
            s = p["s"] & (g["v"] >= lo) & (g["v"] < hi)
            if s.sum() < 300:
                continue
            b, l, h, n = tls_ci(p["denom"][s], (g["sa"] / p["L"])[s], (g["t"][s] / 10.0).astype(int), n=800)
            if not np.isfinite(b):
                continue
            pts.append((float(np.median(g["v"][s]) ** 2), b, max((h - l) / 3.92, 1e-6), s.sum() / FS))
        if len(pts) < 3:
            pr("  %-5s  only %d usable bands -- cannot fit" % (t, len(pts)))
            continue
        v2 = np.array([q[0] for q in pts])
        z = np.array([q[1] for q in pts])
        w = 1.0 / np.array([q[2] for q in pts]) ** 2
        A = np.c_[np.ones_like(v2), v2]
        W = np.diag(w)
        cov = np.linalg.inv(A.T @ W @ A)
        coef = cov @ (A.T @ W @ z)
        se = np.sqrt(np.diag(cov))
        sR_true, slope = float(coef[0]), float(coef[1])
        sf_true = -slope / sR_true
        # propagate: sf = -b/a  ->  var ~ (1/a)^2 var_b + (b/a^2)^2 var_a  (cov term included)
        dsf = np.array([slope / sR_true ** 2, -1.0 / sR_true])
        sf_se = float(np.sqrt(dsf @ cov @ dsf))
        resid = float(np.std(z - A @ coef))
        FIT[t] = dict(sR_true=sR_true, sR_se=float(se[0]), sf_true=sf_true, sf_se=sf_se,
                      sf_ship=P[t]["sf"], bands=len(pts), resid=resid, zspread=float(z.max() - z.min()))
        pr("  %-5s  bands %d | sR_true %6.2f +- %.2f | sf_true %+.3e +- %.1e | sf SHIPPED %+.3e | ratio sf_true/sf_ship %6.2f"
           % (t, len(pts), sR_true, se[0], sf_true, sf_se, P[t]["sf"], sf_true / P[t]["sf"]))
        pr("         Z by band: " + "  ".join("v^2 %5.0f: %6.2f (%3.0fs)" % (q[0], q[1], q[3]) for q in pts))
    pr()
    pr("  The shipped sf is NEGATIVE (understeer): cfac(v) = 1/((1 - sf v^2) L) DECREASES with speed, i.e. the")
    pr("  model says a given steering angle buys LESS curvature the faster you go.  If sf_true is MORE negative")
    pr("  than shipped, the real car understeers MORE than the model and the controller OVER-reads at speed;")
    pr("  if LESS negative, the controller UNDER-reads at speed and pushes -> the high-speed over-delivery.")

    pr()
    pr("=" * 176)
    pr("SECTION C -- THE DECOMPOSITION team-lead ASKED FOR, stated without leaning on the parametric fit.")
    pr("  Every band's 1/rho is  (a FLAT level)  x  (a SPEED-DEPENDENT shape).  Split them by construction:")
    pr("     FLAT  = the exposure-weighted geometric mean of 1/rho over the bands  -- ALL of it is reachable")
    pr("             by the steering-ratio level, because scaling served SR by k scales every band equally.")
    pr("     SHAPE = 1/rho(band) / FLAT                                            -- NONE of it is reachable")
    pr("             by any ratio; only the slip / tyre-stiffness term (sf) moves it.")
    pr("  The two magnitudes to compare are  |FLAT - 1|  against the SHAPE's spread (max - min).")
    pr("=" * 176)
    pr("  %-5s %10s %12s %14s %14s %12s %16s" % (
        "route", "bands", "FLAT (1/rho)", "|FLAT - 1|", "SHAPE spread", "ratio", "verdict"))
    for t in ALLT:
        rows = [(lo, hi, SR[(t, lo)]) for lo, hi in VB if (t, lo) in SR]
        if len(rows) < 3:
            continue
        inv = np.array([r[2][3] / r[2][0] for r in rows])          # 1/rho = SR_served / sR_eff
        wts = np.array([r[2][4] for r in rows])
        flat = float(np.exp(np.sum(wts * np.log(inv)) / wts.sum()))
        shape = inv / flat
        pr("  %-5s %10d %12.3f %14.3f %14.3f %12.1fx %16s" % (
            t, len(rows), flat, abs(flat - 1.0), float(shape.max() - shape.min()),
            (shape.max() - shape.min()) / max(abs(flat - 1.0), 1e-6),
            "SPEED dominates" if (shape.max() - shape.min()) > abs(flat - 1.0) else "FLAT dominates"))
    pr()
    pr("  C.0 the per-band SHAPE, so the sign pattern is visible (1.000 = this band is at the route's own level):")
    pr("      %-5s" % "route" + "".join("%12s" % ("%g-%g" % (lo, hi)) for lo, hi in VB))
    for t in ALLT:
        rows = {lo: SR[(t, lo)] for lo, hi in VB if (t, lo) in SR}
        if len(rows) < 3:
            continue
        inv = {lo: rows[lo][3] / rows[lo][0] for lo in rows}
        wts = np.array([rows[lo][4] for lo in rows])
        flat = float(np.exp(np.sum(wts * np.log(np.array(list(inv.values())))) / wts.sum()))
        pr("      %-5s" % t + "".join(("%12.3f" % (inv[lo] / flat)) if lo in inv else "%12s" % "--"
                                      for lo, hi in VB))
    pr()
    pr("  C.1 THE PARAMETRIC VERSION, and its LIMIT.  If the shape were purely a slip-model error it would be")
    pr("      exactly linear in v^2.  Residual of the weighted straight-line fit of Z on v^2, per route:")
    for t in ALLT:
        if t not in FIT:
            continue
        f = FIT[t]
        pr("      %-5s sR_true %6.2f +- %.2f | sf_true %+.3e +- %.1e | shipped %+.3e | x%.2f | fit resid sd %.3f (Z units)"
           % (t, f["sR_true"], f["sR_se"], f["sf_true"], f["sf_se"], f["sf_ship"],
              f["sf_true"] / f["sf_ship"], f["resid"]))
    pr("      A residual comparable to the band-to-band spread of Z means the 2-parameter (sR, sf) model is")
    pr("      MISSPECIFIED and sf_true must be quoted as an effective, not a physical, tyre number.")
    pr()

    pr("  C.2 THE MEASURED rho, for comparison -- TLS of the controller's own actualLateralAccel on the road")

    pr("      (v*yaw_cal), same stratum and same block bootstrap.  This is the thing the model above predicts.")
    pr("      %-5s %-12s %8s %10s %-20s %12s" % ("route", "v band", "secs", "rho", "rho 95% CI", "1/rho"))
    MEAS = {}
    for t in ALLT:
        p = P[t]
        g = p["g"]
        for lo, hi in VB:
            s = p["s"] & (g["v"] >= lo) & (g["v"] < hi) & np.isfinite(g["actualLateralAccel"]) & (np.abs(g["vyaw"]) > 0.3)
            if s.sum() < 300:
                continue
            b, l, h, n = tls_ci(g["vyaw"][s], g["actualLateralAccel"][s], (g["t"][s] / 10.0).astype(int))
            if not np.isfinite(b) or b <= 0:
                continue
            MEAS[(t, lo)] = (1.0 / b, 1.0 / h, 1.0 / l, s.sum() / FS)
            pr("      %-5s %-12s %8.0f %10.3f [%7.3f, %7.3f] %12.3f" % (
                t, "%g-%g m/s" % (lo, hi), s.sum() / FS, b, l, h, 1.0 / b))
        pr()
    pr("  🛑 C.3 THIS MEASURED 1/rho IS THE PRIMARY INSTRUMENT, NOT SECTION A's RECONSTRUCTION.  It is the same")
    pr("     construction STATE.md and oversteer_v282_r39.py section G use (road / the controller's own")
    pr("     actualLateralAccel).  It DISAGREES with A's sR_eff at low speed -- A reconstructs the road side as")
    pr("     (curv_road - rollcomp) while this compares the LOGGED measurement against the raw road, so the two")
    pr("     differ by exactly how the roll term is handled, which is a large share of the signal below 7 m/s.")
    pr("     Where they disagree, the LOGGED channel wins: it is what the controller actually acted on.")
    pr()
    pr("  C.4 THE DECOMPOSITION, redone on the MEASURED 1/rho.")
    pr("      %-5s %8s %13s %13s %14s %11s %18s" % (
        "route", "bands", "FLAT (1/rho)", "|FLAT - 1|", "SHAPE spread", "ratio", "verdict"))
    for t in ALLT:
        rows = [(lo, hi, MEAS[(t, lo)]) for lo, hi in VB if (t, lo) in MEAS]
        if len(rows) < 3:
            continue
        inv = np.array([r[2][0] for r in rows])
        wts = np.array([r[2][3] for r in rows])
        flat = float(np.exp(np.sum(wts * np.log(inv)) / wts.sum()))
        shape = inv / flat
        pr("      %-5s %8d %13.3f %13.3f %14.3f %10.1fx %18s" % (
            t, len(rows), flat, abs(flat - 1.0), float(shape.max() - shape.min()),
            (shape.max() - shape.min()) / max(abs(flat - 1.0), 1e-6),
            "SPEED dominates" if (shape.max() - shape.min()) > abs(flat - 1.0) else "FLAT dominates"))
    pr()
    pr("  C.5 the measured 1/rho laid out band by band, with the crossing of 1.000 marked.")
    pr("      %-5s" % "route" + "".join("%16s" % ("%g-%g m/s" % (lo, hi)) for lo, hi in VB))
    for t in ALLT:
        cells = []
        for lo, hi in VB:
            if (t, lo) not in MEAS:
                cells.append("%16s" % "--")
                continue
            b, l, h, secs = MEAS[(t, lo)]
            mark = "UNDER" if h < 1.0 else ("OVER" if l > 1.0 else "-")
            cells.append("%16s" % ("%.3f %s" % (b, mark)))
        pr("      %-5s" % t + "".join(cells))
    pr("      UNDER = the whole 95%% CI is below 1.00 (controller over-reads -> it backs off -> under-delivery).")
    pr("      OVER  = the whole CI is above 1.00 (it under-reads -> it pushes -> over-delivery).")
    pr()

    pr("=" * 176)
    pr("SECTION D -- THE COUNTERFACTUAL.  Scale the SERVED steering ratio by k.  1/rho(band) -> k * 1/rho(band)")
    pr("  at EVERY speed: the curve slides, the shape does not change.  For each band, the k that would put")
    pr("  THAT band at 1.000, and what the same k then does to every other band.")
    pr("  Values > 1.000 = the controller under-reads there -> it pushes -> OVER-delivery (the operator's oversteer).")
    pr("  Values < 1.000 = it over-reads -> it backs off -> UNDER-delivery (his understeer).")
    pr("=" * 176)
    pr("  D.0 ON THE PRIMARY (MEASURED) INSTRUMENT -- this is the table that decides the recommendation.")
    for t in ALLT:
        rows = [(lo, hi, MEAS[(t, lo)]) for lo, hi in VB if (t, lo) in MEAS]
        if len(rows) < 3:
            continue
        pr("      --- %s" % t)
        pr("          %-18s %9s | %s" % ("k aimed at band", "k x 16.00", "  ".join(
            "%10s" % ("%g-%g" % (lo, hi)) for lo, hi, _ in rows)))
        pr("          %-18s %9s | %s" % ("TODAY", "16.00",
                                         "  ".join("%10.3f" % r[2][0] for r in rows)))
        for lo, hi, (b, l, h, secs) in rows:
            k = 1.0 / b
            cells = ["%10.3f" % (k * r[2][0]) for r in rows]
            worst = max(abs(k * r[2][0] - 1.0) for r in rows)
            pr("          %-18s %9.2f | %s   worst residual %+.3f" % (
                "%g-%g m/s" % (lo, hi), k * 16.0, "  ".join(cells), worst))
        pr()
    pr("  D.1 the same, on section A's RECONSTRUCTED sR_eff (secondary; see C.3 for why it differs):")
    for t in NEW:
        rows = [(lo, hi, SR[(t, lo)]) for lo, hi in VB if (t, lo) in SR]
        if len(rows) < 3:
            continue
        pr("  --- %s   (today, k = 1.000, served SR = 16.00 in this stratum)" % t)
        pr("      %-16s %9s | %s" % ("k aimed at band", "k", "resulting 1/rho in each band"))
        pr("      %-16s %9s | %s" % ("", "", "  ".join("%10s" % ("%g-%g" % (lo, hi)) for lo, hi, _ in rows)))
        pr("      %-16s %9.3f | %s" % ("TODAY", 1.0,
                                       "  ".join("%10.3f" % (r[2][3] / r[2][0]) for r in rows)))
        for lo, hi, (b, l, h, srm, secs) in rows:
            k = b / srm                                   # scale on served SR that puts THIS band at 1.000
            cells = ["%10.3f" % (k * (r[2][3] / r[2][0])) for r in rows]
            pr("      %-16s %9.3f | %s" % ("%g-%g m/s" % (lo, hi), k, "  ".join(cells)))
        pr("      (equivalently: k x 16.00 = the flat ratio that band wants.  A row that is 1.000 in its own")
        pr("       column and far from 1.000 elsewhere is the proof that no single ratio fixes both ends.)")
        pr()

    out = os.path.join(HERE, "_scratch", "sr_speed_split_r3a3c.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES))
    pr("wrote %s" % out)


if __name__ == "__main__":
    main()
