# -*- coding: utf-8 -*-
"""driver_torque_contamination_r62_r63.py

The operator counteracts the oversteer on roundabouts by hand, so every "engaged, not pressed"
mask in the other r62/r63 scripts BOTH drops the frames he is fighting AND leaves sub-threshold
counter-torque in the frames it keeps.  Two questions:

  Q1  How much of the engaged corner time carries driver torque, at what magnitude, and is it
      OPPOSING the command (counteracting) or with it?
  Q2  Which conclusions survive?
      - sR_true is a KINEMATIC relation (wheel angle -> yaw rate).  Who supplies the torque does
        not enter it, so it should be invariant to driver torque.  TESTED here by splitting it.
      - R_road / R_ctl are TRACKING ratios and are contaminated: a hand fighting the car REDUCES
        achieved yaw, so the measured over-delivery is a LOWER BOUND.  Sized here.
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord", "studies", "optune"))
sys.path.insert(0, os.path.join(ROOT, "rlog-tools"))
import backcalc_laf_friction as B  # noqa: E402

G = 9.81
FS = B.FS
MAP_BP = [0.0, 48.0, 60.0, 76.0, 95.0, 121.0, 191.0, 236.0, 303.0, 380.0]
MAP_V = [16.00, 16.00, 16.00, 15.83, 15.23, 14.99, 14.72, 13.96, 12.72, 12.06]
L = []


def pr(s=""):
    print(s, flush=True)
    L.append(s)


def tls(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 100:
        return np.nan, len(x)
    _, _, V = np.linalg.svd(np.stack([x, y], 1), full_matrices=False)
    n = V[-1]
    return float(-n[0] / n[1]), len(x)


def prep(tag, level=16.33):
    D = B.load(tag); g = B.grid(D); cp = D["cp"]
    m_, l_, aF = cp["mass"], cp["wheelbase"], cp["centerToFront"]
    cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]
    aR = l_ - aF
    sf = m_ * (cF * aF - cR * aR) / (l_ ** 2 * cF * cR)
    v = g["v"]
    g["cfac"] = 1.0 / (1.0 - sf * v ** 2) / l_
    g["rollc"] = (G * g["proll"]) / ((1.0 / sf) - v ** 2)
    g["sa_deg"] = g["ang"] - g["aoff"]
    g["sa"] = np.radians(g["sa_deg"])
    g["denom"] = (-g["yaw_cal"] / np.maximum(v, 1e-3)) - g["rollc"]
    j = np.clip(np.searchsorted(g["lp_t"], g["t"]) - 1, 0, len(g["lp_t"]) - 1)
    g["engaged_any"] = (g["lat"] > 0.5) & (g["active"] > 0.5) & g["lp_calok"][j]
    g["srv"] = np.interp(np.abs(g["sa_deg"]), MAP_BP, MAP_V) * (level / 16.00)
    g["tag"] = tag
    return g


def main():
    gs = [prep("r62"), prep("r63")]

    pr("=" * 122)
    pr("Q1  HOW MUCH DRIVER TORQUE IS IN THE ENGAGED CORNER FRAMES?")
    pr("    drv = carState.steeringTorque (raw sensor).  OPPOSING = sign(drv) != sign(desiredCurvature).")
    pr("    `pressed` is carState.steeringPressed, the flag every other mask in this study uses.")
    pr("=" * 122)
    pr("   %-6s %-26s %7s %8s %9s %9s %9s %9s" % ("route", "band", "n(s)", "pressed", "med|drv|", "p90|drv|", "opposing", "|drv|>150"))
    for g in gs:
        v = g["v"]
        asked = g["descurv"] * v ** 2
        for lbl, mm in (("all engaged", g["engaged_any"]),
                        ("corner |asked|>1.5", g["engaged_any"] & (np.abs(asked) > 1.5)),
                        ("roundabout v4-14 ask>2", g["engaged_any"] & (v > 4) & (v < 14) & (np.abs(asked) > 2.0)),
                        ("|wheel|>45 deg", g["engaged_any"] & (np.abs(g["sa_deg"]) > 45))):
            if mm.sum() < 50:
                continue
            drv = g["drv"][mm]
            opp = np.mean(np.sign(drv) * np.sign(asked[mm]) < 0)
            pr("   %-6s %-26s %7.0f %8.3f %9.0f %9.0f %9.3f %9.3f" % (
                g["tag"], lbl, mm.sum() / FS, float(np.mean(g["pressed"][mm] > 0.5)),
                float(np.median(np.abs(drv))), float(np.percentile(np.abs(drv), 90)), opp,
                float(np.mean(np.abs(drv) > 150))))
        pr("")

    pr("=" * 122)
    pr("Q2a sR_true SPLIT BY DRIVER TORQUE -- if it is really kinematic, the columns must agree.")
    pr("    Pooled r62+r63, engaged (pressed ALLOWED), |steeringRateDeg| < 20, |sa| > 2 deg.")
    pr("=" * 122)
    keys = ["cfac", "denom", "sa", "sa_deg", "v", "rate", "engaged_any", "srv", "descurv", "yaw_cal", "drv", "pressed"]
    P = {k: np.concatenate([g[k] for g in gs]) for k in keys}
    base = P["engaged_any"] & (np.abs(P["rate"]) < 20.0) & np.isfinite(P["denom"]) & (np.abs(P["sa_deg"]) > 2.0)
    ad = np.abs(P["drv"])
    pr("   %-12s %24s %24s %24s" % ("|sa| deg", "|drv| < 30 (hands off)", "30 <= |drv| < 150", "|drv| >= 150 (fighting)"))
    for lo, hi in ((2, 12), (12, 45), (45, 400)):
        cells = []
        for dlo, dhi in ((0, 30), (30, 150), (150, 1e9)):
            ok = base & (np.abs(P["sa_deg"]) >= lo) & (np.abs(P["sa_deg"]) < hi) & (ad >= dlo) & (ad < dhi)
            s, n = tls(P["denom"][ok], P["cfac"][ok] * P["sa"][ok])
            cells.append("%24s" % ("%.2f  (%.0f s)" % (s, n / FS) if np.isfinite(s) else "-- (%.0f s)" % (ok.sum() / FS)))
        pr("   %-12s %s" % ("%d-%d" % (lo, hi), "".join(cells)))
    pr("")
    pr("   served by the map over the same bins: %s" % ", ".join(
        "%d-%d deg -> %.2f" % (lo, hi, float(np.median(P["srv"][base & (np.abs(P["sa_deg"]) >= lo) & (np.abs(P["sa_deg"]) < hi)])))
        for lo, hi in ((2, 12), (12, 45), (45, 400))))

    pr("")
    pr("=" * 122)
    pr("Q2b R_road SPLIT BY DRIVER TORQUE -- a hand fighting the car cuts achieved yaw, so the")
    pr("    hands-off column is the honest one and the fighting column is a LOWER BOUND.")
    pr("=" * 122)
    pr("   %-6s %-22s %-22s %9s %9s %9s" % ("route", "band", "driver torque", "n(s)", "R_road", "R_ctl"))
    for g in gs:
        v = g["v"]
        asked = g["descurv"] * v ** 2
        road = v * g["yaw_cal"]
        dask = np.gradient(asked, 1.0 / FS)
        for lbl, mm0 in (("v 4-12 roundabout", g["engaged_any"] & (v > 4) & (v <= 12)),
                         ("|wheel| > 45 deg", g["engaged_any"] & (np.abs(g["sa_deg"]) > 45))):
            for dl, (dlo, dhi) in (("hands off |drv|<30", (0, 30)), ("light 30-150", (30, 150)), ("fighting >=150", (150, 1e9))):
                mm = mm0 & (np.abs(asked) > 1.0) & (np.abs(dask) < 1.0) & (np.abs(g["drv"]) >= dlo) & (np.abs(g["drv"]) < dhi)
                if mm.sum() < 100:
                    continue
                r_road = np.nanmedian((road / np.where(np.abs(asked) > 0.7, asked, np.nan))[mm])
                r_ctl = np.nanmedian((g["actualLateralAccel"] / np.where(np.abs(g["desiredLateralAccel"]) > 0.7, g["desiredLateralAccel"], np.nan))[mm])
                pr("   %-6s %-22s %-22s %9.0f %9.3f %9.3f" % (g["tag"], lbl, dl, mm.sum() / FS, r_road, r_ctl))
        pr("")

    with open(os.path.join(HERE, "_scratch", "driver_torque_contamination_r62_r63.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
