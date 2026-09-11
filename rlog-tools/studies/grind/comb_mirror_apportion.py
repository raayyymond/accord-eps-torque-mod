# -*- coding: utf-8 -*-
"""studies/grind/comb_mirror_apportion.py -- THE METHOD-INDEPENDENT APPORTIONMENT.
Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY.

WHY THIS FILE EXISTS -- a control that came back BAD, and the fix.  comb_mirror_controls.py K1 ran the
in-phase/quadrature comb ablation against DETUNED reference clocks, where no line exists, and the null
did NOT collapse on r39: net 6.32 at a -0.37 Hz detuning against 7.51 at f_model.  The cause is
structural, not a bug -- delivery is measured in 3 s windows, and |df|*T = 0.37*3 = 1.1 cycles of phase
slip is not enough to decorrelate a projection INSIDE the window.  ⇒ THE LOCKED/FREE SPLIT CANNOT
SEPARATE THE COMB FROM THE ECHO AT r39'S SIGNAL LEVEL, and the C2 "COMB net" number must be quoted as
an upper bound, not a point estimate.

So this file answers the orchestrator's question a way that does NOT depend on the split at all:

    Ablate the ENTIRE ring band from the COMMAND        -> the whole command-side leg
                                    from the WHEEL RATE -> the whole feedback leg
    and compare both against T_total.

That bounds the COMB and the ECHO TOGETHER, because both live in the command and nowhere else.  If the
combined command leg is small against T_total, then NEITHER mechanism is sufficient and the arithmetic
says so without any assumption about phase, clocks or locking.  That is a first-class null.

A1  the three legs, per route, 10 loudest 3 s engaged windows, median + IQR + bootstrap CI
A2  a positive control on the feedback ablation (does the mirror reproduce the measured torque at all?)
A3  the LONG-WINDOW detuned null -- K1 redone at |df|*T >> 1 so the null can actually decorrelate

Run: python rlog-tools/studies/grind/comb_mirror_apportion.py
Writes _scratch/comb_mirror_apportion.txt beside it.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_onset_triggers as B              # noqa: E402
import burst_echo_sizing as ES                # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import comb_mirror_sizing as CM               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
RNG = np.random.default_rng(20260910)
CEIL = 1.0 / (1.0 - np.exp(-2 * np.pi * 0.029))
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def boot(v, n=4000):
    v = np.asarray(v, float)
    bs = np.median(v[RNG.integers(0, len(v), (n, len(v)))], axis=1)
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def bandstop(x, lo, hi, fs=FS):
    sos = signal.butter(4, [lo, hi], btype="bandstop", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, np.asarray(x, float))


def main():
    G = {}
    for tag in B.ROUTES:
        print("loading %s ..." % tag, flush=True)
        g = B.load_route(tag)
        lo, hi = B.BAND[tag]
        g["f0"] = B.ring_f0(g, lo, hi)
        g["env"] = B.demod_env(g["bar"], g["f0"], FS)
        on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
        g["on"], g["pk"], g["amp"] = on, pk, amp
        if tag in CM.COMB_ROUTES:
            fm, sl, ic, M = CM.model_clock(tag)
            g["f_model"], g["slope"], g["icept"] = fm, sl, ic
        G[tag] = g

    OUT.clear()
    pr("=" * 122)
    pr("THE METHOD-INDEPENDENT APPORTIONMENT -- subagent `combsize`, 2026-09-10")
    pr("=" * 122)
    pr("")
    pr("=" * 122)
    pr("A1  THE THREE LEGS -- delivered in-band torque counts, byte-exact 1 kHz mirror")
    pr("=" * 122)
    pr("Each leg is  dT = T(input ablated) - T(as measured),  band-passed to the route's own ring band")
    pr("and reported as sqrt(2)*rms -- THE SAME MEASURE as slewburst's capped-step (4.4-6.8) and echo")
    pr("(8-31) rows and as T_total (57-128).  10 loudest 3 s engaged windows, median, IQR, bootstrap CI.")
    pr("")
    pr("  CMD leg   the whole ring band notched out of the 0xE4 command.  This is an UPPER BOUND on the")
    pr("            COMB AND THE ECHO TOGETHER -- both live in the command and nowhere else, so neither")
    pr("            can exceed it, and the bound needs no assumption about clocks, phase or locking.")
    pr("  FB leg    the whole ring band notched out of the measured 0x18F wheel rate feeding the")
    pr("            feedback path.  This is the loop's own regeneration of the ring already present.")
    pr("")
    pr("%-10s %-11s %9s %9s %8s %-15s %8s %8s %-15s %8s" %
       ("route", "build", "T_total", "CMD leg", "share", "  95% CI", "FB leg", "share", "  95% CI", "quad sum"))
    pr("-" * 122)
    R = {}
    for tag in B.ROUTES:
        g = G[tag]
        lo, hi = B.BAND[tag]
        wins = ES.loud_windows(g)
        cmd_flat = bandstop(g["cmd"], lo, hi)
        wire_flat = bandstop(g["wire"].astype(float), lo, hi)
        vt, vc, vf = [], [], []
        for a0, b0, p0 in wins:
            S0 = GI.simulate(g, a0, b0, g["cells"])
            vt.append(ES.band_amp(S0["T"], lo, hi, FS1K))
            g2 = dict(g); g2["cmd"] = cmd_flat
            vc.append(ES.band_amp(GI.simulate(g2, a0, b0, g["cells"])["T"] - S0["T"], lo, hi, FS1K))
            g3 = dict(g); g3["wire"] = wire_flat
            vf.append(ES.band_amp(GI.simulate(g3, a0, b0, g["cells"])["T"] - S0["T"], lo, hi, FS1K))
        T0, C0, F0 = np.median(vt), np.median(vc), np.median(vf)
        cl, ch = boot(vc); fl, fh = boot(vf)
        R[tag] = dict(T0=float(T0), C=float(C0), F=float(F0), ci=(cl, ch))
        pr("%-10s %-11s %9.2f %9.2f %8.3f %-15s %8.2f %8.3f %-15s %8.2f" %
           (tag, B.BUILD[tag], T0, C0, C0 / T0, "[%.1f, %.1f]" % (cl, ch), F0, F0 / T0,
            "[%.1f, %.1f]" % (fl, fh), np.hypot(C0, F0)))
    pr("")
    pr("The 'quad sum' column is sqrt(CMD^2 + FB^2).  It should land near T_total if the two legs are")
    pr("roughly orthogonal and the chain is near-linear in each perturbation -- a consistency check on")
    pr("the decomposition, not an assumption built into it.")
    pr("")

    pr("=" * 122)
    pr("A2  WHAT THE CMD LEG MEANS AGAINST THE ACCUMULATION CEILING")
    pr("=" * 122)
    pr("The CMD leg is the EXOGENOUS in-band drive the command lands on the plant each cycle.  A")
    pr("perfectly phase-locked drive at f0 accumulates by at most 1/(1-exp(-2*pi*zeta)) = %.2f at" % CEIL)
    pr("zeta = 0.029, degraded by |cos psi| at a phase offset psi against the ring velocity.  🛑 That")
    pr("ceiling belongs on the COMMAND leg ONLY -- the FB leg IS the measured regeneration, so applying")
    pr("the ceiling to it as well would count the loop's gain twice.")
    pr("")
    pr("%-10s %-11s %10s %10s %13s %10s %s" %
       ("route", "build", "CMD leg", "T_total", "x%.2f ceiling" % CEIL, "ratio", "verdict (psi = 0, best case)"))
    pr("-" * 122)
    for tag in B.ROUTES:
        d = R[tag]
        c = CEIL * d["C"]
        pr("%-10s %-11s %10.2f %10.2f %13.2f %10.3f %s" %
           (tag, B.BUILD[tag], d["C"], d["T0"], c, c / d["T0"],
            "SUFFICIENT" if c >= d["T0"] else "SHORT by x%.1f" % (d["T0"] / c)))
    pr("")
    pr("%-10s %s" % ("psi ->", "  ".join("%8d deg" % p for p in (0, 30, 45, 60, 90))))
    for tag in B.ROUTES:
        d = R[tag]
        pr("%-10s %s" % (tag, "  ".join("%12.3f" % (CEIL * abs(np.cos(np.radians(p))) * d["C"] / d["T0"])
                                        for p in (0, 30, 45, 60, 90))))
    pr("")

    pr("=" * 122)
    pr("A3  THE LONG-WINDOW DETUNED NULL -- K1 redone where the null can actually decorrelate")
    pr("=" * 122)
    pr("K1's null floor was contaminated because |df|*T = 0.37 Hz * 3 s = 1.1 cycles of slip inside the")
    pr("measurement window is not decorrelation.  Redone on 12 s windows (|df|*T = 4.4 at 0.37 Hz) and")
    pr("with detunings out to 1.6 Hz.  If the null collapses here and f_model does not, the comb is")
    pr("separable after all -- at the cost of a coarser window.  If the null does NOT collapse, the")
    pr("locked/free split is simply unable to separate comb from echo in this corpus, and the A1 bound")
    pr("is the only honest answer.")
    pr("")
    pr("%-10s %10s %9s %10s %10s %10s %10s" %
       ("route", "clock", "detune", "in-phase", "quadrature", "NET", "net/T_tot"))
    pr("-" * 122)
    for tag in ("r39", "r63_v289"):
        g = G[tag]
        lo, hi = B.BAND[tag]
        wins = ES.loud_windows(g, n=8, half=600)          # 12 s windows
        if not wins:
            pr("%-10s  (no 12 s engaged window survives)" % tag); continue
        T0 = float(np.median([ES.band_amp(GI.simulate(g, a0, b0, g["cells"])["T"], lo, hi, FS1K)
                              for a0, b0, p0 in wins]))
        nulls = []
        for d in (0.0, -1.60, -0.90, -0.37, 0.37, 0.90, 1.60):
            fref = g["f_model"] + d
            z = CM.analytic(g["cmd"], fref - CM.COMB_HW, fref + CM.COMB_HW)
            _, grind = CM.strata(g)
            phi = CM.lock_phase(z, g["t"], g["icept"], 1.0 / fref, grind)
            xin, xqu = CM.split_locked(z, g["t"], g["icept"], 1.0 / fref, phi)
            vi, vq = [], []
            for a0, b0, p0 in wins:
                S0 = GI.simulate(g, a0, b0, g["cells"])
                for arr, acc in ((xin, vi), (xqu, vq)):
                    g2 = dict(g); g2["cmd"] = g["cmd"] - arr
                    acc.append(ES.band_amp(GI.simulate(g2, a0, b0, g["cells"])["T"] - S0["T"], lo, hi, FS1K))
            mi, mq = float(np.median(vi)), float(np.median(vq))
            net = float(np.sqrt(max(mi ** 2 - mq ** 2, 0.0)))
            pr("%-10s %10s %+9.2f %10.2f %10.2f %10.2f %10.3f" %
               (tag, "f_model" if d == 0 else "detuned", d, mi, mq, net, net / T0))
            if d != 0.0:
                nulls.append(net)
        pr("%-10s %10s %9s %10s %10s %10.2f %10.3f   <== NULL FLOOR (max over 6 detunings)" %
           (tag, "", "", "", "", max(nulls), max(nulls) / T0))
        pr("")
    with open(os.path.join(B.SCR, "comb_mirror_apportion.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_mirror_apportion.txt")


if __name__ == "__main__":
    main()
