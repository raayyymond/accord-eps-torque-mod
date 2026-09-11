# -*- coding: utf-8 -*-
"""studies/grind/comb_crux_checks.py -- THE THREE CRUX CHECKS on COMB-VS-ECHO-SIZING.
Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY.

The orchestrator will not relay the sizing result until three things are nailed.  Each is an attempt to
BREAK a claim of mine, and each is written so that it CAN come back against me.

  X1  BANDWIDTH NORMALISATION.  My headline falsifier is that r63 carries 125.86 in-band counts against
      r39's 57.21 (x2.2) on a command leg of 5.21 against 11.56.  But r63 is scored in V289's 14-18 Hz
      band and r39 in V282's 18-22 Hz band.  Both happen to be 4.0 Hz wide, but their FRACTIONAL
      bandwidths differ (4/16 = 0.25 vs 4/20 = 0.20) and a Butterworth's shape depends on that, so
      `sqrt(2)*rms of band-passed dT` is not obviously the same quantity on the two routes.  Redone with
      EQUAL-BANDWIDTH filters centred on each route's OWN f0, at three widths, and as a bandwidth-
      normalised power density.  🛑 IF THE x2.2 DOES NOT SURVIVE, THE FALSIFIER IS WITHDRAWN.

  X2  STRATA MATCHING.  If r63's loud windows sit at systematically higher demand, speed or load than
      r39's, the cross-build contrast is confounded and says nothing about the command leg.  Reported
      per route, then the contrast recomputed inside matched speed x demand cells.

  X3  ZETA SENSITIVITY -- the check that runs AGAINST my own conclusion.  Every "sufficient / short"
      verdict rests on the accumulation ceiling 1/(1-exp(-2 pi zeta)) at zeta = 0.029.  `cyclekind`
      measures coherence times implying zeta 0.0091-0.0224 across the corpus -- LOWER than 0.029, which
      RAISES the ceiling and makes the command side MORE capable.  At what zeta does each route's
      command leg become sufficient?  If r63 crosses unity inside the measured range, my strongest
      exclusion weakens and I must say so.

  X4  modelrate's CROSS-CHECK.  It measured bar_locked/cmd_locked during grinding = 2.27 (V282),
      0.30 (r62), 0.00 (r63) and said: if the mirror is right it should reproduce ~2.3 for V282 and
      ~0.3 for V289.  Tested here as the mirror's own command->delivered-torque gain at f0, per build.

Run: python rlog-tools/studies/grind/comb_crux_checks.py
Writes _scratch/comb_crux_checks.txt beside it.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
RNG = np.random.default_rng(20260910)
OUT = []
ROUTES = ("r39", "r5e_v288", "r62_v289", "r63_v289", "r35")


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


def ceiling(z):
    return 1.0 / (1.0 - np.exp(-2 * np.pi * z))


def main():
    G = {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        g = B.load_route(tag)
        lo, hi = B.BAND[tag]
        g["f0"] = B.ring_f0(g, lo, hi)
        g["env"] = B.demod_env(g["bar"], g["f0"], FS)
        on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
        g["on"], g["pk"], g["amp"] = on, pk, amp
        G[tag] = g

    OUT.clear()
    pr("=" * 124)
    pr("THE THREE CRUX CHECKS -- subagent `combsize`, 2026-09-10")
    pr("=" * 124)
    pr("")

    # ==================================================================================================
    pr("=" * 124)
    pr("X1  BANDWIDTH NORMALISATION -- does the r63-vs-r39 falsifier survive equal-bandwidth scoring?")
    pr("=" * 124)
    pr("The published rows used each build's own census band: 18-22 Hz (V282/V288/V281r3) and 14-18 Hz")
    pr("(V289).  Both are 4.0 Hz wide, but the FRACTIONAL bandwidth differs (0.20 vs 0.25) and a 4th-")
    pr("order Butterworth's shape follows the fractional width, so the two are not automatically the")
    pr("same measurement.  Redone below with filters of EQUAL ABSOLUTE WIDTH centred on each route's")
    pr("OWN measured f0, at three widths, plus the bandwidth-normalised density (counts / sqrt(Hz)).")
    pr("")
    res = {}
    for W in (2.0, 3.0, 4.0):
        pr("--- equal bandwidth %.1f Hz, centred on each route's own f0 ---" % W)
        pr("%-10s %-11s %8s %10s %10s %9s %12s %12s" %
           ("route", "build", "f0", "T_total", "CMD leg", "share", "T/sqrt(Hz)", "CMD/sqrt(Hz)"))
        pr("-" * 124)
        for tag in ROUTES:
            g = G[tag]
            f0 = g["f0"]
            lo, hi = f0 - W / 2, f0 + W / 2
            wins = ES.loud_windows(g)
            cmd_flat = bandstop(g["cmd"], lo, hi)
            vt, vc = [], []
            for a0, b0, p0 in wins:
                S0 = GI.simulate(g, a0, b0, g["cells"])
                vt.append(ES.band_amp(S0["T"], lo, hi, FS1K))
                g2 = dict(g); g2["cmd"] = cmd_flat
                vc.append(ES.band_amp(GI.simulate(g2, a0, b0, g["cells"])["T"] - S0["T"], lo, hi, FS1K))
            T0, C0 = float(np.median(vt)), float(np.median(vc))
            res.setdefault(W, {})[tag] = (T0, C0, vt, vc)
            pr("%-10s %-11s %8.2f %10.2f %10.2f %9.3f %12.2f %12.2f" %
               (tag, B.BUILD[tag], f0, T0, C0, C0 / T0, T0 / np.sqrt(W), C0 / np.sqrt(W)))
        r63, r39 = res[W]["r63_v289"], res[W]["r39"]
        pr("")
        pr("   r63 / r39 ring ratio = %.2f   (published, per-build bands: 2.20)" % (r63[0] / r39[0]))
        pr("   r63 / r39 CMD ratio  = %.2f   (published: 0.45);  share 0.041 -> %.3f vs r39 %.3f"
           % (r63[1] / r39[1], r63[1] / r63[0], r39[1] / r39[0]))
        pr("")
    pr("🛑 VERDICT ON X1 is the 'r63 / r39 ring ratio' line: if it stays near 2.2 with equal bandwidth,")
    pr("the falsifier is not a filter artefact.  If it collapses toward 1, the claim is WITHDRAWN.")
    pr("")

    # ==================================================================================================
    pr("=" * 124)
    pr("X2  STRATA MATCHING -- are r39's and r63's loud windows the same kind of driving?")
    pr("=" * 124)
    pr("%-10s %-11s %7s %9s %9s %9s %9s %9s" %
       ("route", "build", "n win", "v p50", "v IQR", "idx p50", "idx IQR", "|bar| p50"))
    pr("-" * 124)
    prof = {}
    for tag in ROUTES:
        g = G[tag]
        wins = ES.loud_windows(g)
        v = np.array([np.median(g["vego"][a:b]) for a, b, p in wins])
        ix = np.array([np.median(g["idx_live"][a:b]) for a, b, p in wins])
        bb = np.array([np.median(np.abs(g["bar"][a:b])) for a, b, p in wins])
        prof[tag] = (v, ix, bb)
        pr("%-10s %-11s %7d %9.1f %9s %9.1f %9s %9.0f" %
           (tag, B.BUILD[tag], len(wins), np.median(v),
            "%.1f-%.1f" % (np.percentile(v, 25), np.percentile(v, 75)), np.median(ix),
            "%.0f-%.0f" % (np.percentile(ix, 25), np.percentile(ix, 75)), np.median(bb)))
    pr("")
    pr("MATCHED CONTRAST -- the whole-route in-band ring amplitude of the BAR, inside matched")
    pr("speed x demand cells, so the cross-build comparison cannot be a driving-regime artefact.")
    pr("Cells requiring >= 8 s of engaged time in BOTH r39 and r63.")
    pr("")
    pr("%-14s %10s %10s %10s %10s %10s" %
       ("cell", "r39 s", "r63 s", "r39 ring", "r63 ring", "r63/r39"))
    pr("-" * 124)
    g39, g63 = G["r39"], G["r63_v289"]
    rr, ww = [], []
    for v0, v1 in ((0, 5), (5, 10), (10, 15), (15, 25)):
        for i0, i1 in ((0, 5), (5, 20), (20, 60), (60, 1e9)):
            m39 = g39["eng"] & (g39["vego"] >= v0) & (g39["vego"] < v1) & \
                (g39["idx_live"] >= i0) & (g39["idx_live"] < i1)
            m63 = g63["eng"] & (g63["vego"] >= v0) & (g63["vego"] < v1) & \
                (g63["idx_live"] >= i0) & (g63["idx_live"] < i1)
            if m39.sum() < 800 or m63.sum() < 800:
                continue
            a39 = ES.band_amp(g39["bar"][m39], g39["f0"] - 1.5, g39["f0"] + 1.5, FS)
            a63 = ES.band_amp(g63["bar"][m63], g63["f0"] - 1.5, g63["f0"] + 1.5, FS)
            rr.append(a63 / a39); ww.append(min(m39.sum(), m63.sum()))
            pr("%-14s %10.0f %10.0f %10.1f %10.1f %10.2f" %
               ("v%d-%d i%d-%s" % (v0, v1, i0, "inf" if i1 > 1e8 else str(int(i1))),
                m39.sum() / FS, m63.sum() / FS, a39, a63, a63 / a39))
    if rr:
        w = np.array(ww, float); w /= w.sum()
        pr("")
        pr("   weighted mean matched r63/r39 ring ratio = %.2f  over %d cells" % (np.array(rr) @ w, len(rr)))
    pr("")

    # ==================================================================================================
    pr("=" * 124)
    pr("X3  ZETA SENSITIVITY -- the check that runs AGAINST my own conclusion")
    pr("=" * 124)
    pr("Every verdict rests on the accumulation ceiling 1/(1-exp(-2 pi zeta)).  I used zeta = 0.029.")
    pr("`cyclekind` measures phase coherence times implying zeta 0.0091-0.0224 -- LOWER, which RAISES")
    pr("the ceiling and makes the command side MORE capable.  A lower zeta is therefore adverse to my")
    pr("conclusion, so it must be swept rather than assumed.")
    pr("")
    pr("ratio = ceiling(zeta) * CMD_leg / T_total;  >= 1 means the command side can sustain the ring.")
    pr("")
    Z = (0.005, 0.0091, 0.015, 0.0224, 0.029, 0.040)
    pr("%-10s %-11s %9s %9s %s" % ("route", "build", "CMD", "T_total",
                                   "  ".join("z=%.4f" % z for z in Z)))
    pr("-" * 124)
    PUB = {"r39": (11.56, 57.21), "r5e_v288": (6.98, 52.61), "r62_v289": (6.03, 66.00),
           "r63_v289": (5.21, 125.86), "r35": (5.83, 21.50)}
    for tag in ROUTES:
        C0, T0 = PUB[tag]
        pr("%-10s %-11s %9.2f %9.2f %s" %
           (tag, B.BUILD[tag], C0, T0, "  ".join("%8.3f" % (ceiling(z) * C0 / T0) for z in Z)))
    pr("")
    pr("%-10s %-11s %s" % ("route", "build", "zeta at which the command leg becomes SUFFICIENT (psi = 0)"))
    pr("-" * 124)
    for tag in ROUTES:
        C0, T0 = PUB[tag]
        need = T0 / C0                                     # required ceiling
        if need <= 1.0:
            pr("%-10s %-11s  sufficient at any zeta" % (tag, B.BUILD[tag])); continue
        zc = -np.log(1.0 - 1.0 / need) / (2 * np.pi)
        pr("%-10s %-11s  zeta <= %.4f   (%s the measured corpus range 0.0091-0.029)" %
           (tag, B.BUILD[tag], zc,
            "INSIDE" if 0.0091 <= zc <= 0.029 else ("BELOW" if zc < 0.0091 else "ABOVE")))
    pr("")

    # ==================================================================================================
    pr("=" * 124)
    pr("X4  modelrate's CROSS-CHECK -- the mirror's command->torque gain at f0, per build")
    pr("=" * 124)
    pr("modelrate measured bar_locked/cmd_locked during grinding = 5.27 (V112) / 2.91 (V281r3) /")
    pr("2.27 (V282) / 1.34 (V288) / 0.30 (r62) / 0.00 (r63), and predicted: if the mirror is right it")
    pr("should reproduce ~2.3 for V282 and ~0.3 for V289.")
    pr("⚠ NOT THE SAME QUANTITY, and I say so before quoting it: modelrate's ratio is command -> BAR,")
    pr("which runs through the physical column; the mirror gives command -> DELIVERED MOTOR TORQUE and")
    pr("stops at the plant.  So the levels are not comparable -- only the ORDERING across builds is.")
    pr("")
    pr("%-10s %-11s %10s %12s %14s %12s" %
       ("route", "build", "f0", "CMD leg", "cmd in-band", "gain T/cmd"))
    pr("-" * 124)
    gains = {}
    for tag in ROUTES:
        g = G[tag]
        f0 = g["f0"]
        lo, hi = f0 - 1.5, f0 + 1.5
        wins = ES.loud_windows(g)
        cmd_flat = bandstop(g["cmd"], lo, hi)
        vc, vi = [], []
        for a0, b0, p0 in wins:
            S0 = GI.simulate(g, a0, b0, g["cells"])
            g2 = dict(g); g2["cmd"] = cmd_flat
            vc.append(ES.band_amp(GI.simulate(g2, a0, b0, g["cells"])["T"] - S0["T"], lo, hi, FS1K))
            vi.append(ES.band_amp(g["cmd"][a0:b0], lo, hi, FS))
        C0, I0 = float(np.median(vc)), float(np.median(vi))
        gains[tag] = C0 / max(I0, 1e-9)
        pr("%-10s %-11s %10.2f %12.2f %14.2f %12.3f" % (tag, B.BUILD[tag], f0, C0, I0, C0 / I0))
    pr("")
    pr("   ordering by the mirror :  %s" %
       " > ".join("%s %.3f" % (t, gains[t]) for t in sorted(gains, key=gains.get, reverse=True)))
    pr("   ordering by modelrate  :  r35 2.91 > r39 2.27 > r5e 1.34 > r62 0.30 > r63 0.00")
    pr("")
    with open(os.path.join(B.SCR, "comb_crux_checks.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_crux_checks.txt")


if __name__ == "__main__":
    main()
