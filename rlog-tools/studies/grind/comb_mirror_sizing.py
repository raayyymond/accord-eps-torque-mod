# -*- coding: utf-8 -*-
"""studies/grind/comb_mirror_sizing.py -- SIZE THE COMB THROUGH THE BYTE-EXACT 1 kHz MIRROR.
Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

THE QUESTION the orchestrator set: `slewburst` sized the ECHO (a sustained sinusoid at f0) and the
CAPPED STEP (an impulse) through `GI.simulate`, the byte-exact 1 kHz mirror, and reported delivered
in-band torque counts of 8-31 and 4.4-6.8 against a measured 57-128.  The third candidate -- `modelrate`'s
COMB, the camera-clock line at modeld's 19.9997 Hz frame rate -- has never been put on that same axis.
Put it there.

METHOD -- ABLATION, not injection.  The comb is ALREADY in the measured command.  So rather than
guessing a waveform, decompose the measured command's in-band content into the part PHASE-LOCKED to
the camera clock and the part that is not, remove each in turn, and run the mirror on both.  The
difference in delivered in-band torque IS that leg's contribution, on exactly the measure `slewburst`
used (sqrt(2) x rms of the band-passed dT).

THE LOCKED/FREE SPLIT, and why it is done mod pi.  `modelrate` established that the plain circular
mean fails its own positive control: the 20 Hz component of a staircase flips sign with the plan's
slope, so its phase hops by pi.  The locked component is therefore  z_L(t) = a(t) * u(t)  with a REAL
(sign-changing) and u = exp(i*(theta + phi)), theta = 2*pi*(model frame index).  Its estimator is the
IN-PHASE PROJECTION  a(t) = Re(z * conj(u)).  That projection also catches HALF of any free (isotropic)
in-band content, so it is not used alone: the QUADRATURE projection  Im(z * conj(u))  catches the other
half of the free content and NONE of the locked content, and is used throughout as a MATCHED CONTROL.

    E_inphase - E_quadrature = E_locked        (exactly; this is modelrate's R2 x E_total)
    E_quadrature             = E_free / 2

So the three numbers reported per route are the delivery of the in-phase ablation, the delivery of the
quadrature ablation (the control), and their difference -- which is the COMB's attributable delivery
with the free content differenced out.  A comb that is not there returns in-phase == quadrature.

🛑 A NULL IS A FIRST-CLASS RESULT.  If the comb's delivered counts come in far below the measured ring,
that is reported as plainly as a positive.

⚠ CARRIED LIMITATION, stated by `slewburst` against its own numbers and restated here: `GI.simulate`
is the V282-era chain.  It reads each build's cal cells from that build's image but does NOT implement
V288's pre-filter cave or V289's notch cave.  ONLY THE r39 (V282) ROW IS A CLEAN MIRROR RESULT.

🛑 AND THE BAND DISTINCTION THAT MATTERS ON V289.  The comb sits at f_model ~ 19.9997 Hz on every
build.  The RING sits at 18-22 Hz on V282/V288 -- overlapping the comb -- but at 14-18 Hz on V289,
3.5 Hz away.  So delivery is measured in BOTH bands: the route's own ring band (the number that
answers the question) and a narrow band on the camera clock (what the comb puts out regardless).

Sections
  C1  COMB ON THE WIRE   the comb's amplitude in RAW 0xE4 COUNTS (not a ratio), and its locked energy
                         fraction R2, per route, grinding vs baseline.  This is the numerator the
                         orchestrator asked for.
  C2  THE HEADLINE       three-leg ablation through the mirror: total delivered in-band torque, and how
                         much of it is the COMB leg, the FREE-COMMAND leg, and the FEEDBACK leg.
  C3  CROSS-CHECK        the same comb waveform INJECTED (rather than ablated), to confirm the chain is
                         near-linear in the perturbation and the two methods agree.

Run: python rlog-tools/studies/grind/comb_mirror_sizing.py
Writes _scratch/comb_mirror_sizing.txt beside it.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_onset_triggers as B              # noqa: E402  loader + detector, reused verbatim
import burst_echo_sizing as ES                # noqa: E402  band_amp + loud_windows, reused verbatim
import grind_incident_r35 as GI               # noqa: E402  the byte-exact 1 kHz mirror

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
MDIR = os.path.join(HERE, "_scratch", "modeld")
RNG = np.random.default_rng(20260910)
OUT = []

# routes that have a modeld cadence cache (modelrate's extractor).  r35 has none -> no camera clock.
COMB_ROUTES = ("r39", "r5e_v288", "r62_v289", "r63_v289")
COMB_HW = 1.5                      # half-width of the narrow band placed on the camera clock, Hz
DET = np.r_[np.arange(-0.80, -0.099, 0.02), np.arange(0.10, 0.801, 0.02)]   # modelrate's detuned null


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ======================================================================================================
# the camera clock, and the mod-pi locked/free split
# ======================================================================================================
def model_clock(tag):
    """(f_model, slope, intercept) from a least-squares fit of modelV2 logMonoTime on frameId.

    Same construction as modeld_cadence_vs_ring.load, and the same clock as the v280 CAN cache:
    both store raw logMonoTime seconds with no t0 subtraction, so g['t'] and mdl_t are directly
    comparable with no reconciliation step.  [modelrate's EVIDENCE, restated]
    """
    M = dict(np.load(os.path.join(MDIR, tag + "_cad.npz"), allow_pickle=True))
    sl, ic = np.polyfit(M["mdl_fid"], M["mdl_t"], 1)
    return 1.0 / sl, sl, ic, M


def analytic(x, lo, hi, fs=FS, ntap=257):
    b = signal.firwin(ntap, [lo, hi], fs=fs, pass_zero=False)
    return signal.hilbert(signal.filtfilt(b, [1.0], np.asarray(x, float) - np.mean(x)))


def split_locked(z, t, ic, slope, phi):
    """mod-pi projection onto the camera clock.  Returns the two REAL waveforms (in-phase, quadrature).

    u = exp(i*(theta + phi)) with theta = 2*pi*(t - ic)/slope.  The in-phase projection carries the
    locked energy plus half the free energy; the quadrature projection carries the other half of the
    free energy and none of the locked energy.  Both are real band-limited signals that can be
    subtracted from the command.
    """
    th = 2.0 * np.pi * (t - ic) / slope + phi
    u = np.exp(1j * th)
    w = z * np.conj(u)
    return np.real(np.real(w) * u), np.real(1j * np.imag(w) * u)


def lock_phase(z, t, ic, slope, m):
    """phi = 0.5 * arg( SUM z^2 exp(-2i theta) ) -- the axis the locked component lies along."""
    th = 2.0 * np.pi * (t[m] - ic) / slope
    return 0.5 * float(np.angle((z[m] ** 2 * np.exp(-2j * th)).sum()))


def r2_at(z, t, ic, f, m):
    """modelrate's square-law locked fraction, at an arbitrary reference frequency f."""
    th = 2.0 * np.pi * (t[m] - ic) * f
    den = float((np.abs(z[m]) ** 2).sum())
    return float(np.abs((z[m] ** 2 * np.exp(-2j * th)).sum()) / max(den, 1e-300))


def r2_full(z, t, ic, fm, m):
    r0 = r2_at(z, t, ic, fm, m)
    rd = [r2_at(z, t, ic, fm + d, m) for d in DET]
    return r0, float(np.max(rd)), float(np.mean(np.abs(z[m]) ** 2))


# ======================================================================================================
def load_all():
    G = {}
    for tag in B.ROUTES:
        pr("loading %s ..." % tag)
        g = B.load_route(tag)
        lo, hi = B.BAND[tag]
        g["f0"] = B.ring_f0(g, lo, hi)
        g["env"] = B.demod_env(g["bar"], g["f0"], FS)
        on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
        g["on"], g["pk"], g["amp"] = on, pk, amp
        g["runs"] = B.eng_runs(g)
        g["eng_s"] = float(g["eng"].sum()) / FS
        if tag in COMB_ROUTES:
            fm, sl, ic, M = model_clock(tag)
            g["f_model"], g["slope"], g["icept"], g["M"] = fm, sl, ic, M
        G[tag] = g
    return G


def strata(g):
    """grinding = inside a detected burst (peak +- 0.5 s); baseline = engaged, outside, v < 12."""
    n = len(g["t"])
    hot = np.zeros(n, bool)
    for p in g["pk"]:
        hot[max(0, p - 50):min(n, p + 50)] = True
    grind = g["eng"] & hot
    base = g["eng"] & ~hot & (g["vego"] < 12)
    return base, grind


# ======================================================================================================
# C1  THE COMB ON THE WIRE -- in RAW COUNTS, not a ratio
# ======================================================================================================
def sectionC1(G):
    pr("=" * 122)
    pr("C1  THE COMB ON THE WIRE -- amplitude in RAW 0xE4 COUNTS, and its locked energy fraction")
    pr("=" * 122)
    pr("`modelrate` reported the comb as a RATIO to the band median (2.4-9.8 quiet -> 38.6-68.8 grinding).")
    pr("The mirror needs the NUMERATOR.  Measured here as the in-band amplitude sqrt(2)*rms of the 0xE4")
    pr("command band-passed to a %.1f Hz half-width band on the camera clock, split into the LOCKED part" % COMB_HW)
    pr("(in-phase minus quadrature energy = modelrate's R2 x E) and the FREE part.")
    pr("R2 floor = max over 70 reference clocks detuned by |d| in [0.10, 0.80] Hz -- measured, not assumed.")
    pr("")
    pr("%-10s %-11s %-9s %7s %9s %9s %8s %8s %9s %10s %10s" %
       ("route", "build", "stratum", "n s", "f_model", "A_inband", "R2", "floor", "R2-floor",
        "A_locked", "A_free"))
    pr("-" * 122)
    res = {}
    for tag in COMB_ROUTES:
        g = G[tag]
        fm = g["f_model"]
        z = analytic(g["cmd"], fm - COMB_HW, fm + COMB_HW)
        base, grind = strata(g)
        for slab, m in (("baseline", base), ("grinding", grind)):
            if m.sum() < 800:
                pr("%-10s %-11s %-9s %7.1f  (too few samples)" % (tag, B.BUILD[tag], slab, m.sum() / FS))
                continue
            r0, fl, E = r2_full(z, g["t"], g["icept"], fm, m)
            A = np.sqrt(2.0 * E)                       # in-band amplitude in raw counts
            lock = max(r0 - fl, 0.0)
            pr("%-10s %-11s %-9s %7.1f %9.4f %9.2f %8.4f %8.4f %+9.4f %10.2f %10.2f" %
               (tag, B.BUILD[tag], slab, m.sum() / FS, fm, A, r0, fl, r0 - fl,
                A * np.sqrt(lock), A * np.sqrt(max(1.0 - lock, 0.0))))
            res.setdefault(tag, {})[slab] = dict(A=A, R2=r0, floor=fl, E=E)
        pr("")
    pr("READING: A_locked is the amplitude of the camera-clock-locked component of the command, in raw")
    pr("0xE4 counts.  That is the comb, and it is the waveform C2 ablates.  A_free is everything else")
    pr("in the same band -- which is where an ECHO would live if it is not clock-locked.")
    pr("")
    return res


# ======================================================================================================
# C2  THE HEADLINE -- three-leg ablation through the byte-exact mirror
# ======================================================================================================
def sectionC2(G):
    pr("=" * 122)
    pr("C2  🛑 THE HEADLINE -- DELIVERED IN-BAND TORQUE COUNTS, decomposed by source")
    pr("=" * 122)
    pr("Byte-exact 1 kHz mirror (GI.simulate), 10 loudest 3 s engaged windows per route, median over")
    pr("windows with the inter-window IQR.  Delivery measured as sqrt(2)*rms of the band-passed dT --")
    pr("THE SAME MEASURE as slewburst's capped-step row (4.4-6.8) and echo row (8-31), so all three")
    pr("candidates sit on one axis.")
    pr("")
    pr("  T_total   delivered in-band torque with every input exactly as measured  (slewburst's 57-128)")
    pr("  COMB      dT when the camera-clock-LOCKED part of the command is removed (in-phase ablation)")
    pr("  ctrl      dT for the QUADRATURE ablation -- the matched control: same band, same amplitude,")
    pr("            orthogonal to the camera clock.  Carries half the FREE content and none of the comb.")
    pr("  COMB net  in-phase energy minus quadrature energy, back to an amplitude.  THIS is the comb's")
    pr("            attributable delivery with the free content differenced out.  ctrl ~= COMB means")
    pr("            NO COMB EFFECT -- the ablation removed ordinary in-band content, not a clock line.")
    pr("  FB leg    dT when the RING BAND is notched out of the measured 0x18F wheel rate feeding the")
    pr("            feedback path -- i.e. the plant-mode / de-damping leg.")
    pr("")
    rows = {}
    for tag in B.ROUTES:
        g = G[tag]
        lo, hi = B.BAND[tag]
        wins = ES.loud_windows(g)
        has_comb = tag in COMB_ROUTES
        fm = g.get("f_model", np.nan)
        pr("-" * 122)
        pr("%-10s %-11s  ring band %.0f-%.0f Hz (f0 %.2f)   camera clock %s   %d windows" %
           (tag, B.BUILD[tag], lo, hi, g["f0"],
            ("%.4f Hz" % fm) if has_comb else "NO modeld CACHE", len(wins)))
        pr("-" * 122)

        # --- build the ablated command arrays once, over the whole route ---
        cmd0 = g["cmd"]
        if has_comb:
            z = analytic(cmd0, fm - COMB_HW, fm + COMB_HW)
            _, grind = strata(g)
            phi = lock_phase(z, g["t"], g["icept"], g["slope"], grind)
            xin, xqu = split_locked(z, g["t"], g["icept"], g["slope"], phi)
            cmd_nocomb = cmd0 - xin
            cmd_noquad = cmd0 - xqu
        # --- feedback-leg ablation: notch the ring band out of the measured wheel rate ---
        sos = signal.butter(4, [lo, hi], btype="bandstop", fs=FS, output="sos")
        wire_flat = signal.sosfiltfilt(sos, g["wire"].astype(float))

        acc = {k: [] for k in ("T0", "comb", "ctrl", "fb", "combF", "ctrlF")}
        for a0, b0, p0 in wins:
            S0 = GI.simulate(g, a0, b0, g["cells"])
            acc["T0"].append(ES.band_amp(S0["T"], lo, hi, FS1K))
            if has_comb:
                for key, arr in (("comb", cmd_nocomb), ("ctrl", cmd_noquad)):
                    g2 = dict(g); g2["cmd"] = arr
                    S1 = GI.simulate(g2, a0, b0, g["cells"])
                    d = S1["T"] - S0["T"]
                    acc[key].append(ES.band_amp(d, lo, hi, FS1K))
                    acc[key + "F"].append(ES.band_amp(d, fm - COMB_HW, fm + COMB_HW, FS1K))
            g3 = dict(g); g3["wire"] = wire_flat
            S3 = GI.simulate(g3, a0, b0, g["cells"])
            acc["fb"].append(ES.band_amp(S3["T"] - S0["T"], lo, hi, FS1K))

        def q(k):
            v = np.array(acc[k], float)
            return (np.median(v), np.percentile(v, 25), np.percentile(v, 75)) if len(v) else (np.nan,) * 3

        T0, T0a, T0b = q("T0")
        pr("  %-26s %9s %14s %10s" % ("leg", "counts", "IQR", "share of T_total"))
        pr("  %-26s %9.2f %14s %10s" % ("T_total (as measured)", T0, "%.1f-%.1f" % (T0a, T0b), "1.000"))
        if has_comb:
            for key, lab in (("comb", "COMB  (in-phase abl.)"), ("ctrl", "ctrl  (quadrature abl.)")):
                m, a, b = q(key)
                pr("  %-26s %9.2f %14s %10.3f" % (lab, m, "%.1f-%.1f" % (a, b), m / T0))
            mc, _, _ = q("comb"); mq, _, _ = q("ctrl")
            net = np.sqrt(max(mc ** 2 - mq ** 2, 0.0))
            pr("  %-26s %9.2f %14s %10.3f   <== THE COMB'S ATTRIBUTABLE DELIVERY" %
               ("COMB net (in-ph - quad)", net, "-", net / T0))
            mcf, _, _ = q("combF"); mqf, _, _ = q("ctrlF")
            netf = np.sqrt(max(mcf ** 2 - mqf ** 2, 0.0))
            pr("  %-26s %9.2f %14s %10s   (delivery at the camera clock itself, %.1f+-%.1f Hz)" %
               ("COMB net @ f_model", netf, "-", "-", fm, COMB_HW))
        mf, fa, fb_ = q("fb")
        pr("  %-26s %9.2f %14s %10.3f" % ("FEEDBACK leg", mf, "%.1f-%.1f" % (fa, fb_), mf / T0))
        rows[tag] = dict(T0=T0, comb=q("comb")[0], ctrl=q("ctrl")[0], fb=mf,
                         net=(np.sqrt(max(q("comb")[0] ** 2 - q("ctrl")[0] ** 2, 0.0)) if has_comb else np.nan))
        pr("")
    return rows


# ======================================================================================================
# C3  CROSS-CHECK -- inject the same comb waveform instead of ablating it
# ======================================================================================================
def sectionC3(G, rows):
    pr("=" * 122)
    pr("C3  CROSS-CHECK -- INJECT the extracted comb rather than ablating it")
    pr("=" * 122)
    pr("If the chain is near-linear in the perturbation (slewburst measured A x4.0 -> dT x3.69), then")
    pr("adding the comb waveform back on top of the measured command must deliver the same in-band")
    pr("torque that removing it takes away.  Agreement validates the ablation; disagreement would mean")
    pr("the quantiser is doing something amplitude-dependent and the ablation number needs a caveat.")
    pr("")
    pr("%-10s %12s %12s %12s %10s" % ("route", "ablate", "inject", "ratio", "T_total"))
    pr("-" * 122)
    for tag in COMB_ROUTES:
        g = G[tag]
        lo, hi = B.BAND[tag]
        fm = g["f_model"]
        z = analytic(g["cmd"], fm - COMB_HW, fm + COMB_HW)
        _, grind = strata(g)
        phi = lock_phase(z, g["t"], g["icept"], g["slope"], grind)
        xin, _ = split_locked(z, g["t"], g["icept"], g["slope"], phi)
        vals = []
        for a0, b0, p0 in ES.loud_windows(g):
            S0 = GI.simulate(g, a0, b0, g["cells"])
            g2 = dict(g); g2["cmd"] = g["cmd"] + xin
            S1 = GI.simulate(g2, a0, b0, g["cells"])
            vals.append(ES.band_amp(S1["T"] - S0["T"], lo, hi, FS1K))
        inj = float(np.median(vals))
        abl = rows[tag]["comb"]
        pr("%-10s %12.2f %12.2f %12.3f %10.2f" % (tag, abl, inj, inj / max(abl, 1e-9), rows[tag]["T0"]))
    pr("")


def main():
    G = load_all()
    OUT.clear()
    pr("=" * 122)
    pr("SIZING THE COMB THROUGH THE BYTE-EXACT 1 kHz MIRROR -- subagent `combsize`, 2026-09-10")
    pr("=" * 122)
    pr("")
    sectionC1(G)
    rows = sectionC2(G)
    sectionC3(G, rows)
    with open(os.path.join(B.SCR, "comb_mirror_sizing.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_mirror_sizing.txt")


if __name__ == "__main__":
    main()
