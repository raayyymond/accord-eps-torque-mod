# -*- coding: utf-8 -*-
"""studies/grind/modeld_phase_lock.py -- SECTION 5 REDONE.  The phase-lock discriminator between a
line FORCED by modeld's 20 Hz frame clock and a plant resonance that merely sits near 20 Hz.
Subagent `modelrate`, 2026-09-10.  ANALYSIS ONLY.

WHY THIS FILE EXISTS -- a method failure, recorded.  `modeld_cadence_vs_ring.py` SS 5 used the
amplitude-weighted circular mean of (instantaneous phase - model phase).  It FAILED ITS OWN POSITIVE
CONTROL: `controlsState.desiredCurvature`, a signal generated ON the model clock, scored R = 0.060
against a detuned null of 0.163.  The reason is structural, not a bug: the 20 Hz component of a
staircase is a sawtooth whose amplitude CHANGES SIGN whenever the plan's slope changes sign, so its
phase hops by pi at random and the plain circular mean cancels to zero.  A locked line with random
sign is locked MODULO PI, and the detector for that is the SQUARE LAW:

    R2 = | SUM z(t)^2 * exp(-2i*theta(t)) |  /  SUM |z(t)|^2 ,
    z = analytic signal of the band-passed channel, theta = 2*pi*(model frame index at t).

R2 has a clean physical reading.  Split z into a part locked to theta (any real, sign-changing
amplitude along one phase axis) plus a part with uniformly distributed phase; then
E_inphase - E_quadrature = E_locked, and R2 = E_locked / E_total EXACTLY.  So R2 IS THE FRACTION OF
IN-BAND ENERGY THAT IS PHASE-LOCKED TO THE CAMERA CLOCK, and (1 - R2) is the free fraction.
R2 = 1 is a pure forced line; R2 = 0 is a free oscillation.  The finite-sample floor is measured, not
assumed: the same statistic against reference clocks detuned by |delta| >= 0.10 Hz.

Run: python modeld_phase_lock.py       (writes _scratch/modeld_phase_lock.txt)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import modeld_cadence_vs_ring as MC   # noqa: E402  (load, episodes_of, model_phase, ROUTES, BAND)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []
DET = np.r_[np.arange(-0.80, -0.099, 0.02), np.arange(0.10, 0.801, 0.02)]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def analytic(x, fs, lo, hi, ntap=257):
    b = signal.firwin(ntap, [lo, hi], fs=fs, pass_zero=False)
    return signal.hilbert(signal.filtfilt(b, [1.0], np.asarray(x, float) - np.mean(x)))


def r2_at(z, t, ic, f, m):
    z2 = z[m] ** 2
    den = (np.abs(z[m]) ** 2).sum()
    th = 2 * np.pi * ((t[m] - ic) * f)
    return float(np.abs((z2 * np.exp(-2j * th)).sum()) / max(den, 1e-300))


def r2_full(z, t, ic, fm, m):
    """returns (R2 at f_model, max R2 over detunings, argmax detuning, mean in-band energy)."""
    r0 = r2_at(z, t, ic, fm, m)
    rd = [r2_at(z, t, ic, fm + d, m) for d in DET]
    i = int(np.argmax(rd))
    e = float(np.mean(np.abs(z[m]) ** 2))
    return r0, float(rd[i]), float(DET[i]), e


def main():
    G, EPS = {}, {}
    for tag, build in MC.ROUTES:
        pr("loading %s (%s) ..." % (tag, build))
        G[tag] = MC.load(tag)
        EPS[tag] = MC.episodes_of(G[tag])
        pr("  %d episodes, %.1f s hot" % (len(EPS[tag][0]), EPS[tag][1].sum() * G[tag]["P18"]))

    pr()
    pr("=" * 126)
    pr("PHASE LOCK TO THE CAMERA / modeld FRAME CLOCK -- square-law detector")
    pr("=" * 126)
    pr("R2 = fraction of in-band energy phase-locked (mod pi) to the model frame clock.")
    pr("floor = max R2 over 70 reference clocks detuned by |delta| in [0.10, 0.80] Hz -- the measured")
    pr("finite-sample floor, not an assumption.  E = mean in-band energy (channel units squared).")
    pr("E_lock = R2 * E is the absolute locked energy; E_free = (1 - R2) * E.")
    pr()
    pr("Strata: baseline = engaged & v < 12 m/s & |bar| < 400 raw & OUTSIDE every census episode;")
    pr("        grinding = engaged & inside an episode (grind1_census_v282.py's recipe).")
    pr()
    for tag, build in MC.ROUTES:
        g = G[tag]
        eps, hot = EPS[tag]
        fs = 1.0 / g["P18"]
        fm, ic = g["f_model"], g["model_icept"]
        t = g["t"]
        M = g["M"]
        base = g["eng"] & (g["vego"] < 12) & (np.abs(g["bar"]) < 400) & ~hot
        grind = g["eng"] & hot
        chans = [("desiredCurvature*", np.interp(t, M["cs_t"], M["cs_descurv"]) * 1e4),
                 ("op torque cmd*", np.interp(t, M["cc_t"], M["cc_torque"]) * 1e3),
                 ("0xE4 command", g["cmd"]),
                 ("bar driver torque", g["bar"]),
                 ("wheel rate 0x18F", g["wire"].astype(float)),
                 ("angle 0x14A", g["ang"])]
        bands = [(18.0, 22.0, "18-22 (the V282 band)")]
        if MC.BAND[tag] != (18.0, 22.0):
            bands.append((MC.BAND[tag][0], MC.BAND[tag][1], "%g-%g (this build's line)" % MC.BAND[tag]))
        pr("-" * 126)
        pr("%s   %s   f_model = %.6f Hz   (episodes %d, %.1f s hot)"
           % (tag, build, fm, len(eps), hot.sum() * g["P18"]))
        pr("-" * 126)
        for lo, hi, blab in bands:
            pr("  band %s" % blab)
            pr("  %-20s %-9s %7s %10s %8s %8s %8s %10s %10s" %
               ("channel", "stratum", "n s", "E", "R2", "floor", "R2-fl", "E_lock", "E_free"))
            for name, x in chans:
                z = analytic(x, fs, lo, hi)
                for slab, m in (("baseline", base), ("grinding", grind)):
                    if m.sum() < 800:
                        pr("  %-20s %-9s %7.1f   (too few samples)" % (name, slab, m.sum() * g["P18"]))
                        continue
                    r0, rd, dd, e = r2_full(z, t, ic, fm, m)
                    pr("  %-20s %-9s %7.1f %10.4g %8.4f %8.4f %+8.4f %10.4g %10.4g" %
                       (name, slab, m.sum() * g["P18"], e, r0, rd, r0 - rd, r0 * e, (1 - r0) * e))
            pr()
    pr("=" * 126)
    pr("THE DECOMPOSITION THAT ANSWERS THE QUESTION")
    pr("=" * 126)
    pr("If the grinding line is the FORCED response to the camera clock, then the grinding EXCESS")
    pr("energy in `bar` must be LOCKED energy: dE_lock/dE_total ~ 1.  If it is a plant resonance that")
    pr("the loop de-damps, the excess is FREE: dE_lock/dE_total ~ 0.")
    pr()
    pr("%-10s %-22s %10s %10s %10s %10s %10s %9s" %
       ("route", "band", "E base", "E grind", "dE", "dE_lock", "dE_free", "lock frac"))
    pr("-" * 126)
    for tag, build in MC.ROUTES:
        g = G[tag]
        eps, hot = EPS[tag]
        fs = 1.0 / g["P18"]
        base = g["eng"] & (g["vego"] < 12) & (np.abs(g["bar"]) < 400) & ~hot
        grind = g["eng"] & hot
        if base.sum() < 800 or grind.sum() < 800:
            pr("%-10s  (a stratum is too small: base %.1f s, grind %.1f s)"
               % (tag, base.sum() * g["P18"], grind.sum() * g["P18"]))
            continue
        bands = [(18.0, 22.0)] + ([MC.BAND[tag]] if MC.BAND[tag] != (18.0, 22.0) else [])
        for lo, hi in bands:
            z = MC_analytic(g["bar"], fs, lo, hi)
            rb, fb, _, eb = r2_full(z, g["t"], g["model_icept"], g["f_model"], base)
            rg, fg, _, eg = r2_full(z, g["t"], g["model_icept"], g["f_model"], grind)
            lb, lg = max(rb - fb, 0.0) * eb, max(rg - fg, 0.0) * eg
            dE, dL = eg - eb, lg - lb
            pr("%-10s %-22s %10.4g %10.4g %10.4g %10.4g %10.4g %9.3f" %
               (tag, "bar %g-%g Hz" % (lo, hi), eb, eg, dE, dL, dE - dL,
                (dL / dE) if dE > 0 else np.nan))
    with open(os.path.join(HERE, "_scratch", "modeld_phase_lock.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/modeld_phase_lock.txt")


MC_analytic = analytic

if __name__ == "__main__":
    main()
