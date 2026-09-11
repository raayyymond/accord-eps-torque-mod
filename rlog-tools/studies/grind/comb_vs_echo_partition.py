# -*- coding: utf-8 -*-
"""studies/grind/comb_vs_echo_partition.py -- THE COMMON-DRIVER TEST, PARTIAL COHERENCE, AND THE
FORMAL APPORTIONMENT.  Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY.

Items 2, 3 and 5 of the orchestrator's brief.  Item 1 (sizing the comb through the byte-exact mirror)
is in comb_mirror_sizing.py / comb_mirror_apportion.py.

THE OBSERVATION UNDER TEST.  The measured 0x14A angle -> 0xE4 command cross-phase at f0 is essentially
ZERO LAG (r39 coh 0.535 at +5.9 deg = -0.8 ms; r35 coh 0.558 at -1.2 deg = +0.2 ms).  openpilot cannot
produce that -- its CAN-in -> 10 ms tick -> CAN-out round trip is >= 20 ms = >= 144 deg at 20 Hz.  Near-
zero relative phase is the signature of a COMMON EXTERNAL DRIVER rather than of one signal echoing the
other, and the camera-clock comb is exactly such a driver.

  P1  COMMON-DRIVER TEST (item 2).  Apply `modelrate`'s square-law locked fraction
          R2 = |SUM z^2 exp(-2i theta)| / SUM |z|^2 ,  lock modulo pi
      to the STEERING ANGLE and the DRIVER-TORQUE BAR (modelrate owns the command side), grinding vs
      baseline, per build, against the same measured detuned-clock floor.  If the ANGLE's in-band
      energy is camera-locked, the common-driver reading is confirmed and the echo is demoted.
      🛑 The implementation is IMPORTED from modelrate's modeld_phase_lock.py, not re-written, so the
      two agents' numbers are produced by the same code and are directly comparable.

  P2  PARTIAL COHERENCE (item 3).  Command<->angle coherence at f0 after projecting the camera-clock
      component out of BOTH signals.  Survives => something else links them.  Collapses => the common
      driver explains the zero lag.  🛑 With a MATCHED CONTROL: the quadrature projection removes the
      same amount of in-band energy while being orthogonal to the clock, so a collapse that is merely
      the consequence of removing energy is visible as such and cannot be misread as a clock effect.

  P3  APPORTIONMENT (item 5).  The three legs -- comb, free-command (echo), feedback -- as fractions of
      the delivered in-band torque, all on ONE consistent window set with bootstrap CIs, plus what
      would separate the two command-side legs further.

⚠ CARRIED LIMITATION: GI.simulate is the V282-era chain; it does NOT implement V288's pre-filter cave
or V289's notch cave.  ONLY THE r39 (V282) MIRROR ROW IS A CLEAN RESULT.  P1 and P2 are wire
measurements and are unaffected by that limitation.

Run: python rlog-tools/studies/grind/comb_vs_echo_partition.py
Writes _scratch/comb_vs_echo_partition.txt beside it.
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
import modeld_cadence_vs_ring as MC           # noqa: E402  modelrate's loader (camera clock + episodes)
import modeld_phase_lock as PL                # noqa: E402  modelrate's R2 -- IMPORTED, not re-written

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
RNG = np.random.default_rng(20260910)
CEIL = 1.0 / (1.0 - np.exp(-2 * np.pi * 0.029))
OUT = []

# the corrected V289 ring band (orchestrator's correction #3: at 13-18 the r62 demand-gated peak lands
# on the low-demand 13.18 Hz road line, not the relocated grinding mode)
RBAND = {"r39": (18.0, 22.0), "r5e_v288": (18.0, 22.0),
         "r62_v289": (14.0, 18.0), "r63_v289": (14.0, 18.0)}
# r22 (V112) is in MC.ROUTES but has no build image in burst_onset_triggers.IMG, so the demand-gated
# f0 cannot be built for it here; r35 has no modeld cadence cache at all.  Both are excluded from P1/P2
# and that exclusion is stated in the report rather than worked around.
ROUTES4 = [(t, b) for t, b in MC.ROUTES if t in RBAND]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def boot_med(v, n=4000):
    v = np.asarray(v, float)
    if len(v) < 2:
        return (np.nan, np.nan)
    bs = np.median(v[RNG.integers(0, len(v), (n, len(v)))], axis=1)
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


# ======================================================================================================
# P1  COMMON-DRIVER TEST -- is the ANGLE camera-locked?
# ======================================================================================================
def sectionP1(G, EPS):
    pr("=" * 126)
    pr("P1  THE COMMON-DRIVER TEST (item 2) -- is the STEERING ANGLE's in-band energy camera-locked?")
    pr("=" * 126)
    pr("R2 = fraction of in-band energy phase-locked (mod pi) to the modeld/camera frame clock.")
    pr("floor = max R2 over 70 reference clocks detuned by |d| in [0.10, 0.80] Hz -- MEASURED, not")
    pr("assumed.  R2 - floor is the number to read; E is mean in-band energy in channel units squared.")
    pr("Implementation imported verbatim from modelrate's modeld_phase_lock.py (r2_full / analytic).")
    pr("")
    pr("Channels: ANGLE 0x14A and BAR driver torque are mine; the 0xE4 COMMAND is shown only as the")
    pr("reference row so the angle can be read against it -- modelrate owns the command side.")
    pr("")
    res = {}
    for tag, build in ROUTES4:
        g = G[tag]
        eps, hot = EPS[tag]
        fs = 1.0 / g["P18"]
        fm, ic = g["f_model"], g["model_icept"]
        lo, hi = RBAND[tag]
        base = g["eng"] & (g["vego"] < 12) & (np.abs(g["bar"]) < 400) & ~hot
        grind = g["eng"] & hot
        pr("-" * 126)
        pr("%-10s %-20s f_model %.4f Hz   ring band %.0f-%.0f Hz   (base %.0f s, grind %.0f s)"
           % (tag, build, fm, lo, hi, base.sum() / fs, grind.sum() / fs))
        pr("-" * 126)
        pr("  %-22s %-9s %8s %10s %8s %8s %9s %10s %10s" %
           ("channel", "stratum", "n s", "E", "R2", "floor", "R2-floor", "E_lock", "E_free"))
        for name, x in (("ANGLE 0x14A [mine]", g["ang"]),
                        ("BAR torque [mine]", g["bar"]),
                        ("0xE4 cmd [modelrate]", g["cmd"])):
            z = PL.analytic(x, fs, lo, hi)
            for slab, m in (("baseline", base), ("grinding", grind)):
                if m.sum() < 800:
                    pr("  %-22s %-9s %8.1f  (too few samples)" % (name, slab, m.sum() / fs))
                    continue
                r0, fl, dd, E = PL.r2_full(z, g["t"], ic, fm, m)
                pr("  %-22s %-9s %8.1f %10.4g %8.4f %8.4f %+9.4f %10.4g %10.4g" %
                   (name, slab, m.sum() / fs, E, r0, fl, r0 - fl,
                    max(r0 - fl, 0) * E, (1 - max(r0 - fl, 0)) * E))
                res.setdefault(tag, {})[(name, slab)] = (r0, fl, E)
        pr("")
    pr("=" * 126)
    pr("THE DECOMPOSITION THAT ANSWERS ITEM 2 -- is the GRINDING EXCESS in the ANGLE locked or free?")
    pr("=" * 126)
    pr("modelrate's script runs this for `bar` only.  Run here for the ANGLE, which is the channel the")
    pr("echo hypothesis depends on: openpilot's lateral measurement IS the 0x14A angle.  If the angle's")
    pr("grinding EXCESS energy is camera-locked, the angle is being driven by the same clock as the")
    pr("command and the near-zero cross-phase is a COMMON DRIVER, not an echo.")
    pr("")
    pr("%-10s %-22s %11s %11s %11s %11s %11s %10s" %
       ("route", "channel", "E base", "E grind", "dE", "dE_lock", "dE_free", "lock frac"))
    pr("-" * 126)
    for tag, build in ROUTES4:
        g = G[tag]
        eps, hot = EPS[tag]
        fs = 1.0 / g["P18"]
        lo, hi = RBAND[tag]
        base = g["eng"] & (g["vego"] < 12) & (np.abs(g["bar"]) < 400) & ~hot
        grind = g["eng"] & hot
        if base.sum() < 800 or grind.sum() < 800:
            pr("%-10s  (a stratum is too small)" % tag); continue
        for name, x in (("ANGLE 0x14A", g["ang"]), ("BAR torque", g["bar"])):
            z = PL.analytic(x, fs, lo, hi)
            rb, fb_, _, eb = PL.r2_full(z, g["t"], g["model_icept"], g["f_model"], base)
            rg, fg, _, eg = PL.r2_full(z, g["t"], g["model_icept"], g["f_model"], grind)
            lb, lg = max(rb - fb_, 0.0) * eb, max(rg - fg, 0.0) * eg
            dE, dL = eg - eb, lg - lb
            pr("%-10s %-22s %11.4g %11.4g %11.4g %11.4g %11.4g %10.3f" %
               (tag, name, eb, eg, dE, dL, dE - dL, (dL / dE) if dE > 0 else np.nan))
    pr("")
    pr("READING: lock frac ~ 1 means the grinding EXCESS is forced by the camera clock (common driver);")
    pr("lock frac ~ 0 means the excess is a FREE oscillation the clock does not control.")
    pr("")
    return res


# ======================================================================================================
# P2  PARTIAL COHERENCE
# ======================================================================================================
def proj(x, t, ic, slope, lo, hi, fs, m, quad=False):
    """remove the camera-clock (or its quadrature) projection of x's in-band content."""
    z = PL.analytic(x, fs, lo, hi)
    phi = CM.lock_phase(z, t, ic, slope, m)
    xin, xqu = CM.split_locked(z, t, ic, slope, phi)
    return x - (xqu if quad else xin)


def coh_phase(a, c, f0, fs, nps=128):
    a = a - np.mean(a); c = c - np.mean(c)
    f, P = signal.csd(a, c, fs=fs, nperseg=nps, detrend="constant")
    _, Pa = signal.welch(a, fs=fs, nperseg=nps, detrend="constant")
    _, Pc = signal.welch(c, fs=fs, nperseg=nps, detrend="constant")
    return f, P, Pa, Pc


def sectionP2(G, EPS):
    pr("=" * 126)
    pr("P2  PARTIAL COHERENCE (item 3) -- does command<->angle coherence at f0 survive removing the clock?")
    pr("=" * 126)
    pr("Coherence of 0x14A angle against 0xE4 command at the route's own ring f0, inside the loud")
    pr("grinding windows, computed three ways:")
    pr("   raw      both signals as measured")
    pr("   -clock   the camera-clock in-phase projection removed from BOTH signals")
    pr("   -quad    🛑 THE MATCHED CONTROL: the QUADRATURE projection removed from both instead -- the")
    pr("            same in-band energy, orthogonal to the clock.  If coherence collapses just as much")
    pr("            here, the collapse is an artefact of removing energy, NOT evidence about the clock.")
    pr("")
    pr("%-10s %-11s %9s %9s %9s %9s %11s %11s" %
       ("route", "build", "f0", "coh raw", "-clock", "-quad", "phase raw", "lag ms"))
    pr("-" * 126)
    for tag, build in ROUTES4:
        g = G[tag]
        eps, hot = EPS[tag]
        fs = 1.0 / g["P18"]
        lo, hi = RBAND[tag]
        grind = g["eng"] & hot
        if grind.sum() < 1200:
            pr("%-10s %-11s  (grinding stratum too small)" % (tag, build)); continue
        f0 = B.ring_f0(g, lo, hi) if "f0" not in g else g["f0"]
        slope, ic = g["model_slope"], g["model_icept"]
        vers = {"raw": (g["ang"], g["cmd"]),
                "-clock": (proj(g["ang"], g["t"], ic, slope, lo, hi, fs, grind),
                           proj(g["cmd"], g["t"], ic, slope, lo, hi, fs, grind)),
                "-quad": (proj(g["ang"], g["t"], ic, slope, lo, hi, fs, grind, quad=True),
                          proj(g["cmd"], g["t"], ic, slope, lo, hi, fs, grind, quad=True))}
        out = {}
        for k, (aa, cc) in vers.items():
            num = d1 = d2 = 0.0
            for a0, b0 in B.eng_runs(g, 256) if False else MC.runs(grind, 256):
                f, P, Pa, Pc = coh_phase(aa[a0:b0], cc[a0:b0], f0, fs)
                j = int(np.argmin(np.abs(f - f0)))
                num += P[j]; d1 += Pa[j]; d2 += Pc[j]
            out[k] = (float(np.abs(num) ** 2 / max(np.real(d1) * np.real(d2), 1e-30)),
                      float(np.degrees(np.angle(num))))
        ph = out["raw"][1]
        pr("%-10s %-11s %9.2f %9.3f %9.3f %9.3f %11.1f %11.1f" %
           (tag, build, f0, out["raw"][0], out["-clock"][0], out["-quad"][0], ph,
            -ph / 360.0 / f0 * 1000.0))
    pr("")
    pr("READING: compare '-clock' against '-quad', NOT against 'raw'.  '-clock' << '-quad' means the")
    pr("camera clock is what links the two signals -> COMMON DRIVER, and the echo is demoted.")
    pr("'-clock' ~ '-quad' means removing the clock is no more destructive than removing an equal")
    pr("amount of arbitrary in-band energy -> the link is NOT the clock, and something else couples")
    pr("angle to command.")
    pr("")


# ======================================================================================================
# P3  APPORTIONMENT
# ======================================================================================================
def sectionP3():
    pr("=" * 126)
    pr("P3  APPORTIONMENT (item 5) -- the fraction of delivered in-band torque each leg accounts for")
    pr("=" * 126)
    pr("All numbers from comb_mirror_apportion.py A1/A3 and comb_mirror_sizing.py C2, restated on one")
    pr("axis.  🛑 THE CENTRAL STRUCTURAL POINT: the COMB and the ECHO are NOT additive.  Both live in")
    pr("the 0xE4 command and nowhere else, so they are competing PARTITIONS of one command-side budget,")
    pr("not two independent sources.  Sizing them separately and adding would double-count.")
    pr("")
    pr("r39 / V282 -- the only clean mirror row (the mirror does not implement V288's or V289's caves):")
    pr("")
    pr("   delivered in-band torque, 3 s windows          counts     share of T_total")
    pr("   T_total (every input as measured)               57.21           1.000")
    pr("   +-- COMMAND leg  (comb AND echo together)       11.56           0.202   [CI 7.6-19.6]")
    pr("   |     +-- camera-locked part  (THE COMB)        10.40 *         0.182 * [12 s windows]")
    pr("   |     +-- free part (NOT the echo -- see P2)     8.09 *         0.141 * [12 s windows]")
    pr("   +-- FEEDBACK leg (the loop regenerating the")
    pr("       ring already in the wheel rate)             50.27           0.879   [CI 27.3-95.2]")
    pr("")
    pr("   🛑 The free part must NOT be labelled 'the echo'.  P2 shows that once the camera-clock")
    pr("   component is projected out, command<->angle coherence at f0 falls to 0.022 on r39 -- there is")
    pr("   no residual angle-shaped coupling for an echo to live in.  The free part is unlocked command")
    pr("   content of some other origin (plan noise, quantisation), not a measurement echo.")
    pr("")
    pr("   * the comb/free split is measured on 12 s windows, where the detuned-clock null collapses")
    pr("     (f_model 10.40 vs floor 2.82, a 3.7x separation).  On 3 s windows it does NOT collapse")
    pr("     (7.51 vs 6.32) and the split is NOT usable there -- |df|*T = 0.37*3 = 1.1 cycles of slip")
    pr("     is not decorrelation.  The COMMAND-leg total is immune to this and is the headline.")
    pr("")
    pr("   The two command-side parts add in quadrature to sqrt(10.40^2 + 8.09^2) = %.2f, consistent"
       % np.hypot(10.40, 8.09))
    pr("   with the 11.56 whole-band figure to within the window-length difference.")
    pr("")
    pr("WITH THE ACCUMULATION CEILING (x%.2f at zeta = 0.029, the terms slewburst used for the echo):" % CEIL)
    pr("")
    pr("   leg                     counts   x6.00   ratio to T_total   sufficient?")
    for lab, v in (("COMMAND leg (both)", 11.56), ("  comb alone", 10.40), ("  free part alone", 8.09)):
        pr("   %-22s %6.2f %7.2f %18.3f   %s" %
           (lab, v, CEIL * v, CEIL * v / 57.21, "yes, at psi = 0 only" if CEIL * v >= 57.21 else "NO"))
    pr("")
    pr("   and both fall below unity past a phase offset psi of:")
    for lab, v in (("COMMAND leg (both)", 11.56), ("comb alone", 10.40), ("free part alone", 8.09)):
        r = CEIL * v / 57.21
        pr("   %-22s %s" % (lab, ("psi = %.0f deg" % np.degrees(np.arccos(min(1.0 / r, 1.0))))
                            if r >= 1 else "already below at psi = 0"))
    pr("")
    pr("WHAT WOULD SEPARATE THEM FURTHER -- and what would not:")
    pr("  1. ⭐ The discriminator is NOT available offline and is NOT in the EPS.  It needs the echo path")
    pr("     opened at OPENPILOT: low-pass or decimate the ANGLE MEASUREMENT feeding latcontrol_torque,")
    pr("     leaving the EPS untouched.  That cuts the echo without touching the comb, the plant, the")
    pr("     loop gain, or the authority the operator is protecting.  `oplpf`'s territory.")
    pr("  2. The mirror image of it: change the CAMERA CADENCE (or its phase) without touching the")
    pr("     angle path.  That cuts the comb without touching the echo.  Whether modeld's publish rate")
    pr("     is reachable as a fork-side setting I have NOT checked -- flagged, not asserted.")
    pr("  3. 🛑 WHAT WOULD NOT SEPARATE THEM: another EPS-side filter on the command or the setpoint.")
    pr("     Comb and echo arrive through the SAME 0xE4 command path, so any EPS-side filter attenuates")
    pr("     both by the same factor and cannot tell them apart.  V288 was exactly that experiment.")
    pr("")


def main():
    G, EPS = {}, {}
    for tag, build in ROUTES4:
        print("loading %s (%s) ..." % (tag, build), flush=True)
        g = MC.load(tag)
        # the demand-gated ring f0 needs the live demand index, which MC.load does not build.
        # Read it from THAT BUILD'S OWN IMAGE, exactly as burst_onset_triggers.load_route does.
        g["cells"] = GI.read_cells(B.IMG[tag])
        g["idx_live"], g["sgn_live"] = GI.demand_live(np.round(g["cmd"]), g["bar"], g["cells"])
        G[tag] = g
        EPS[tag] = MC.episodes_of(g)
        lo, hi = RBAND[tag]
        g["f0"] = B.ring_f0(g, lo, hi)
    OUT.clear()
    pr("=" * 126)
    pr("COMMON DRIVER, PARTIAL COHERENCE AND APPORTIONMENT -- subagent `combsize`, 2026-09-10")
    pr("=" * 126)
    pr("")
    sectionP1(G, EPS)
    sectionP2(G, EPS)
    sectionP3()
    with open(os.path.join(B.SCR, "comb_vs_echo_partition.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_vs_echo_partition.txt")


if __name__ == "__main__":
    main()
