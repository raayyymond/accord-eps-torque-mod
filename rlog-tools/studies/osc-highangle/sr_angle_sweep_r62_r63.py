# -*- coding: utf-8 -*-
"""sr_angle_sweep_r62_r63.py -- the SR-free true rack ratio as a function of |wheel angle|,
on the current fork HEAD toggles (r62/r63) with r39/r3a/r3c as controls.

The instrument (straight_understeer_sr.py section F) inverts openpilot's own vehicle model:
    sR_true = curvature_factor(v) * sa / (-yaw_cal/v - roll_comp)
The right-hand side contains NO steering ratio, so it adjudicates "is the desired plan itself
being delivered" independently of whatever SR the controller believes.

Also: the CONTROLLER's own error (desired vs its vehicle-model measurement) beside the ROAD's
error (desired vs yaw-derived), on the same frames -- the whole point being that the first can
read ~0 while the second does not.
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
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 100:
        return np.nan, len(x)
    _, _, V = np.linalg.svd(np.stack([x, y], 1), full_matrices=False)
    n = V[-1]
    return float(-n[0] / n[1]), len(x)


def tls_ci(x, y, nboot=400, seed=0):
    s, n = tls(x, y)
    if not np.isfinite(s):
        return s, n, np.nan, np.nan
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    # block bootstrap, 2 s blocks, to respect autocorrelation
    blk = int(2 * FS)
    nb = max(len(x) // blk, 2)
    out = []
    for _ in range(nboot):
        pick = rng.integers(0, nb, nb)
        idx = np.concatenate([np.arange(p * blk, min((p + 1) * blk, len(x))) for p in pick])
        s2, _ = tls(x[idx], y[idx])
        out.append(s2)
    out = np.asarray(out, float); out = out[np.isfinite(out)]
    return s, n, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


# tag -> the SR the controller actually served that route.  "map" = the fork's angle map
SERVED = {"r62": "map16.33", "r63": "map16.33", "r39": "map16.00", "r3a": "map16.00", "r3c": "map16.00"}
LEVEL = {"r62": 16.33, "r63": 16.33, "r39": 16.00, "r3a": 16.00, "r3c": 16.00}


def prep(tag):
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
    g["eng"] = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & g["lp_calok"][j]
    g["srv"] = np.interp(np.abs(g["sa_deg"]), MAP_BP, MAP_V) * (LEVEL[tag] / 16.00)
    return g


def main():
    tags = ["r62", "r63", "r39", "r3a", "r3c"]
    gs = {t: prep(t) for t in tags}

    pr("=" * 120)
    pr("A  TRUE RACK RATIO BY |WHEEL ANGLE| -- SR-free, TLS through the origin, block-bootstrap CI")
    pr("   frames: laterally engaged, not pressed, calibrated, v > 4 m/s, |steeringRateDeg| < 20, |sa| > 2 deg")
    pr("=" * 120)
    BINS = [(2, 5), (5, 10), (10, 20), (20, 35), (35, 50), (50, 75), (75, 120), (120, 400)]
    pr("   %-6s %-10s %7s %8s %8s %-16s %8s" % ("route", "|sa| bin", "n(s)", "sR_true", "served", "95% CI", "road/ask"))
    for t in tags:
        g = gs[t]
        for lo, hi in BINS:
            ok = (g["eng"] & (g["v"] > 4.0) & (np.abs(g["rate"]) < 20.0)
                  & (np.abs(g["sa_deg"]) >= lo) & (np.abs(g["sa_deg"]) < hi) & np.isfinite(g["denom"]))
            if ok.sum() < 200:
                continue
            s, n, clo, chi = tls_ci(g["denom"][ok], g["cfac"][ok] * g["sa"][ok])
            srv = float(np.median(g["srv"][ok]))
            pr("   %-6s %-10s %7.0f %8.2f %8.2f  [%5.2f, %5.2f] %8.3f"
               % (t, "%d-%d" % (lo, hi), n / FS, s, srv, clo, chi, srv / s if s else np.nan))
        pr("")

    pr("=" * 120)
    pr("B  THE CONTROLLER'S OWN ERROR vs THE ROAD'S ERROR, SAME FRAMES")
    pr("   ctl  = desiredLateralAccel - actualLateralAccel   (both from the vehicle model -> uses SR)")
    pr("   road = desiredCurvature*v^2 - v*yaw_cal           (asked is SR-free; achieved is SR-free)")
    pr("   Per colleague 2: a mis-tuned SR makes `road` non-zero while `ctl` stays ~0.  Tested here.")
    pr("=" * 120)
    pr("   %-6s %-14s %7s %9s %9s %9s %9s" % ("route", "band", "n(s)", "med ctl", "med road", "R_ctl", "R_road"))
    for t in tags:
        g = gs[t]
        v = g["v"]
        asked = g["descurv"] * v ** 2
        road = v * g["yaw_cal"]
        ctl_des, ctl_act = g["desiredLateralAccel"], g["actualLateralAccel"]
        dask = np.gradient(asked, 1.0 / FS)
        base = g["eng"] & (np.abs(asked) > 1.0) & (np.abs(dask) < 1.0)
        for lbl, mm in (("v 4-10 (rndabt)", base & (v > 4) & (v <= 10)),
                        ("v 10-16", base & (v > 10) & (v <= 16)),
                        ("v 16-40", base & (v > 16)),
                        ("|sa| > 45 deg", base & (np.abs(g["sa_deg"]) > 45))):
            if mm.sum() < 100:
                continue
            e_ctl = np.nanmedian((ctl_des - ctl_act)[mm] * np.sign(asked[mm]))
            e_road = np.nanmedian((asked - road)[mm] * np.sign(asked[mm]))
            r_ctl = np.nanmedian((ctl_act / np.where(np.abs(ctl_des) > 0.7, ctl_des, np.nan))[mm])
            r_road = np.nanmedian((road / np.where(np.abs(asked) > 0.7, asked, np.nan))[mm])
            pr("   %-6s %-14s %7.0f %9.3f %9.3f %9.3f %9.3f" % (t, lbl, mm.sum() / FS, e_ctl, e_road, r_ctl, r_road))
        pr("")

    with open(os.path.join(HERE, "_scratch", "sr_angle_sweep_r62_r63.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
