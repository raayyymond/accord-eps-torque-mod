# -*- coding: utf-8 -*-
"""oversteer_r62_r63.py -- the OVERSTEER read on the CURRENT fork HEAD (0f98d8c75) toggles.

r62 / r63: rate-plant FF ON, variable-SR map at LEVEL 16.33, LAF 6.0, friction 0.01,
SteerKP 0.9, AccordTorqueKi 0.30, ForceAutoTune OFF, SteerDelay 0.2.
Method copied from straight_understeer_sr.py (section F) and oversteer_v282_r39.py (R_road).
Everything on the achieved side is SR-FREE (v * calibrated yaw rate).
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OPT = os.path.join(ROOT, "analysis-2020accord", "studies", "optune")
sys.path.insert(0, OPT)
sys.path.insert(0, os.path.join(ROOT, "rlog-tools"))
import backcalc_laf_friction as B  # noqa: E402

G = 9.81
FS = B.FS
MAP_BP = [0.0, 48.0, 60.0, 76.0, 95.0, 121.0, 191.0, 236.0, 303.0, 380.0]
MAP_V = [16.00, 16.00, 16.00, 15.83, 15.23, 14.99, 14.72, 13.96, 12.72, 12.06]
NOMINAL, LEVEL = 16.00, 16.33
L = []


def pr(s=""):
    print(s, flush=True)
    L.append(s)


def tls_slope(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 50:
        return np.nan, len(x)
    P = np.stack([x, y], 1)
    _, _, V = np.linalg.svd(P, full_matrices=False)
    n = V[-1]
    return float(-n[0] / n[1]), len(x)


def boot_ci(vals, n=2000, seed=0):
    vals = np.asarray(vals, float)
    vals = vals[np.isfinite(vals)]
    if len(vals) < 3:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    bs = np.median(vals[rng.integers(0, len(vals), (n, len(vals)))], 1)
    return float(np.median(vals)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


TAGS = ["r62", "r63"]
OUT = {}


def main():
    for tag in TAGS:
        D = B.load(tag)
        g = B.grid(D)
        cp = D["cp"]
        m_, l_, aF = cp["mass"], cp["wheelbase"], cp["centerToFront"]
        cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]
        aR = l_ - aF
        sf = m_ * (cF * aF - cR * aR) / (l_ ** 2 * cF * cR)
        v = g["v"]
        cfac = 1.0 / (1.0 - sf * v ** 2) / l_
        rollc = (G * g["proll"]) / ((1.0 / sf) - v ** 2)
        sa_deg = g["ang"] - g["aoff"]
        sa = np.radians(sa_deg)
        curv_road = -g["yaw_cal"] / np.maximum(v, 1e-3)
        denom = curv_road - rollc
        j = np.clip(np.searchsorted(g["lp_t"], g["t"]) - 1, 0, len(g["lp_t"]) - 1)
        calok = g["lp_calok"][j]
        eng = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & calok
        sr_served = np.interp(np.abs(sa_deg), MAP_BP, MAP_V) * (LEVEL / NOMINAL)

        pr("=" * 128)
        pr("ROUTE %s  build=%s  engaged(not pressed) %.0f s of %.0f s" % (tag, str(D["build"]), eng.sum() / FS, len(g["t"]) / FS))
        pr("=" * 128)

        pr("A  TRUE STEERING RATIO (SR-free) vs the ratio the fork map SERVED at the same angle")
        pr("   sR_true = cfac(v)*sa / (yaw/v - rollcomp), TLS through origin; engaged, |rate|<10 deg/s, |sa|>1.5 deg")
        pr("   %-14s %8s %8s %8s %8s %10s" % ("band", "n(s)", "sR_true", "sR_srvd", "bias", "road/asked"))
        rows = []
        bands = (("v>15 all", eng & (v > 15.0)),
                 ("v 8-15", eng & (v > 8.0) & (v <= 15.0)),
                 ("v 4-8", eng & (v > 4.0) & (v <= 8.0)),
                 ("|sa| 1.5-5", eng & (v > 15.0) & (np.abs(sa_deg) < 5)),
                 ("|sa| 5-15", eng & (v > 12.0) & (np.abs(sa_deg) >= 5) & (np.abs(sa_deg) < 15)),
                 ("|sa| 15-45", eng & (np.abs(sa_deg) >= 15) & (np.abs(sa_deg) < 45)),
                 ("|sa| >45", eng & (np.abs(sa_deg) >= 45)))
        for lbl, mm in bands:
            ok = mm & (np.abs(g["rate"]) < 10.0) & (np.abs(sa_deg) > 1.5) & np.isfinite(denom)
            srt, n = tls_slope(denom[ok], cfac[ok] * sa[ok])
            srv = float(np.median(sr_served[ok])) if ok.sum() else np.nan
            bias = srt / srv if np.isfinite(srt) else np.nan
            pr("   %-14s %8.0f %8.2f %8.2f %8.3f %10.3f" % (lbl, ok.sum() / FS, srt, srv, bias, (1.0 / bias) if np.isfinite(bias) and bias else np.nan))
            rows.append((lbl, ok.sum() / FS, srt, srv, bias))
        OUT.setdefault(tag, {})["sr"] = rows

        asked = g["descurv"] * v ** 2
        achieved = v * g["yaw_cal"]
        pr("")
        pr("B  DELIVERED / ASKED lateral accel, SR-free on the achieved side (asked = desiredCurvature*v^2)")
        pr("   frames: engaged, not pressed, calibrated, |asked| > 0.7 m/s2, quasi-steady |d(asked)/dt| < 0.5 m/s3")
        dasked = np.gradient(asked, 1.0 / FS)
        st = eng & (np.abs(asked) > 0.7) & (np.abs(dasked) < 0.5) & np.isfinite(achieved)
        pr("   %-14s %8s %8s %14s" % ("band", "n(s)", "R", "95% CI"))
        Rrows = []
        for lbl, mm in (("all", st),
                        ("v 4-8 m/s", st & (v > 4) & (v <= 8)),
                        ("v 8-12", st & (v > 8) & (v <= 12)),
                        ("v 12-18", st & (v > 12) & (v <= 18)),
                        ("v 18-40", st & (v > 18))):
            r = (achieved / np.where(np.abs(asked) > 0.7, asked, np.nan))[mm]
            md, lo, hi = boot_ci(r[::10])
            pr("   %-14s %8.0f %8.3f  [%.3f, %.3f]" % (lbl, mm.sum() / FS, md, lo, hi))
            Rrows.append((lbl, mm.sum() / FS, md, lo, hi))
        OUT[tag]["R"] = Rrows

        pr("")
        pr("C  ROUNDABOUT-SHAPED EVENTS: engaged, v 4-14 m/s, |asked| crosses 2.0 m/s2, 6 s window from onset")
        onset = eng & (np.abs(asked) > 2.0) & (v > 4) & (v < 14)
        idx = np.flatnonzero(onset[1:] & ~onset[:-1]) + 1
        ev = []
        for i in idx:
            w = slice(i, min(i + int(6 * FS), len(v)))
            if not eng[w].all():
                continue
            a_, c_ = asked[w], achieved[w]
            if len(a_) < int(4 * FS) or not np.isfinite(c_).all():
                continue
            s = np.sign(np.median(a_))
            pk_a = s * np.max(s * a_)
            pk_c = s * np.max(s * c_)
            k = int(2 * FS)
            ss = float(np.median(c_[-k:]) / np.median(a_[-k:])) if abs(np.median(a_[-k:])) > 0.7 else np.nan
            aa = a_ - a_.mean()
            cc = c_ - c_.mean()
            lags = np.arange(-int(1.2 * FS), int(1.2 * FS) + 1)
            xc = []
            for lg in lags:
                if lg >= 0:
                    xc.append(float(np.dot(aa[:len(aa) - lg], cc[lg:])))
                else:
                    xc.append(float(np.dot(aa[-lg:], cc[:len(cc) + lg])))
            lead = -lags[int(np.argmax(xc))] / FS
            ev.append(dict(t=float(g["t"][i]), v=float(np.median(v[w])), pk_a=float(pk_a), pk_c=float(pk_c),
                           ovr=float(pk_c / pk_a), ss=ss, lead=float(lead)))
        pr("   n events = %d" % len(ev))
        if ev:
            for k, lbl in (("ovr", "peak achieved / peak asked"), ("ss", "steady achieved / asked"), ("lead", "achieved LEAD over asked (s)")):
                md, lo, hi = boot_ci([e[k] for e in ev])
                pr("   %-32s median %7.3f  95%% CI [%7.3f, %7.3f]" % (lbl, md, lo, hi))
            pr("   median v %.1f m/s, median |peak asked| %.2f m/s2" % (np.median([e["v"] for e in ev]), np.median([abs(e["pk_a"]) for e in ev])))
        OUT[tag]["events"] = ev

        pr("")
        pr("D  FEEDFORWARD vs INTEGRATOR (lat-accel space, as logged). med(i*sign(f)) < 0 = i is CANCELLING ff")
        f_, i_, p_, d_, o_ = g["f"], g["i"], g["p"], g["d"], g["output"]
        s = np.sign(f_)
        for lbl, mm in (("straight |asked|<0.3", eng & (np.abs(asked) < 0.3) & (np.abs(f_) > 0.05)),
                        ("curve |asked|>1.5", eng & (np.abs(asked) > 1.5) & (np.abs(f_) > 0.05)),
                        ("roundabout v4-14 ask>2", eng & (v > 4) & (v < 14) & (np.abs(asked) > 2.0) & (np.abs(f_) > 0.05))):
            if mm.sum() < 100:
                continue
            pr("   %-24s n=%6.0fs |f|=%7.3f p*sgnf=%7.3f i*sgnf=%7.3f d*sgnf=%7.3f out/f=%7.3f" % (
                lbl, mm.sum() / FS, np.nanmedian(np.abs(f_[mm])), np.nanmedian((p_ * s)[mm]),
                np.nanmedian((i_ * s)[mm]), np.nanmedian((d_ * s)[mm]),
                np.nanmedian((o_ / np.where(np.abs(f_) > 0.05, f_, np.nan))[mm])))
        pr("   max |i| = %.3f   p90 |i| = %.3f   p99 |output| = %.3f" % (
            np.nanmax(np.abs(i_[eng])), np.nanpercentile(np.abs(i_[eng]), 90), np.nanpercentile(np.abs(o_[eng]), 99)))
        pr("   openpilot torque: p99 |tq| = %.3f, frac |tq|>0.95 = %.4f, frac saturated flag = %.4f" % (
            np.nanpercentile(np.abs(g["tq"][eng]), 99), np.mean(np.abs(g["tq"][eng]) > 0.95), np.nanmean(g["saturated"][eng]) if "saturated" in g else np.nan))

        pr("")
        pr("E  liveTorqueParameters (learner runs but is NOT in the loop: ForceAutoTune off)")
        pr("   LAFfilt %.3f  frictionFilt %.4f  latAccelOffsetFilt %.4f  calPerc %.0f" % (
            np.nanmedian(g["ltpv_latAccelFactorFiltered"]), np.nanmedian(g["ltpv_frictionCoefficientFiltered"]),
            np.nanmedian(g["ltpv_latAccelOffsetFiltered"]), np.nanmedian(g["ltpv_calPerc"])))
        pr("")

    with open(os.path.join(HERE, "_scratch", "oversteer_r62_r63.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(HERE, "oversteer_r62_r63.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, default=float)


if __name__ == "__main__":
    main()
