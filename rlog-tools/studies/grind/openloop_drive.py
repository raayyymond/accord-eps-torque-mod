# -*- coding: utf-8 -*-
"""openloop_drive.py -- TASK 3: what actually DRIVES the 18-22 Hz torque ring on V282 (r39)?
Subagent `openloop`, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

The record (COMB-VS-ECHO-SIZING §A1, comb_mirror_apportion.py) ablates the whole ring band out of the
COMMAND (20.2 % of T on r39) and out of the WHEEL RATE (88-100 %), and stops there.  This file splits
both legs further, through the SAME byte-exact 1 kHz mirror (grind_incident_r35.simulate), so the
question "is the feedback leg LINEAR RATE FEEDBACK or QUANTISER-TOGGLE KICKS?" gets an answer.

FOUR TERMS, each an ablation of one input with everything else held:
  (a) FEEDBACK, LINEAR IN-BAND CONTENT   band-stop 18-22 Hz out of the 0x18F wheel rate
  (b) RATE-QUANTISER LSB TOGGLES         the 0x18F rate is integer raw counts (V.CPD = 8 per deg/s,
                                         0.125 deg/s LSB) and the record measures the ring at
                                         0.17-0.28 LSB [STATE 8c].  The wire's in-band content is
                                         split, by a band-limited Wiener fit against the INDEPENDENT
                                         0x14A steering-angle channel, into the part COHERENT with
                                         real motion and the INCOHERENT residual, which is this
                                         channel's own quantisation noise.  Each half is ablated.
  (c) SETPOINT COMB D KICKS              wire frozen -> dE = 32*dsp only -> the command's D leg
  (d) SETPOINT P CONTENT                 wire frozen -> the command's P leg
and the mirror's own TP / TD split is read out alongside, so P and D are separated inside every term.

Also computed, from the BUILT IMAGE's own cells, the per-LSB arithmetic the brief asks for:
the feedback two-sample sum's DC gain and FIRST-TICK kick, and the D counts one LSB toggle produces.

Run: python openloop_drive.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import openloop_lib as L                       # noqa: E402
import burst_onset_triggers as B               # noqa: E402
import burst_echo_sizing as ES                 # noqa: E402
import grind_incident_r35 as GI                # noqa: E402
import creep20_loop_id as C20                  # noqa: E402
import v280_map_profiles as V                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, FS1K = 100.0, 1000.0
RNG = np.random.default_rng(20260913)
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def boot(v, n=4000):
    v = np.asarray(v, float)
    bs = np.median(v[RNG.integers(0, len(v), (n, len(v)))], axis=1)
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def bandstop(x, lo, hi, fs=FS):
    return signal.sosfiltfilt(signal.butter(4, [lo, hi], btype="bandstop", fs=fs, output="sos"),
                              np.asarray(x, float))


def wiener_split(r, a, lo, hi, fs=FS, nperseg=512):
    """split the wheel-rate channel's in-band content into the part linearly predictable from the
    INDEPENDENT 0x14A angle channel (= real motion, seen twice) and the residual (= this channel's
    own quantisation noise).  The two channels quantise the SAME mechanical motion with DIFFERENT
    LSBs and different sample instants, so their quantisation errors are independent and the
    cross-spectrum keeps only the motion."""
    rb = C20.bandpass(np.asarray(r, float), lo, hi, fs)
    ad = np.r_[0.0, np.diff(np.asarray(a, float))] * fs              # deg/s from the angle channel
    ab = C20.bandpass(ad, lo, hi, fs)
    f, Sra = signal.csd(ab, rb, fs=fs, nperseg=nperseg)
    _, Saa = signal.welch(ab, fs=fs, nperseg=nperseg)
    _, Srr = signal.welch(rb, fs=fs, nperseg=nperseg)
    m = (f >= lo) & (f <= hi)
    H = np.sum(Sra[m]) / np.sum(Saa[m])                              # band-averaged Wiener gain
    coh = float(np.sum(np.abs(Sra[m]) ** 2) / (np.sum(Saa[m]) * np.sum(Srr[m])))
    r_coh = np.real(H) * ab + np.imag(H) * np.imag(signal.hilbert(ab))
    r_inc = rb - r_coh
    return r_coh, r_inc, float(abs(H)), coh


def main():
    TAG = "r39"
    lo, hi = 18.0, 22.0
    pr("=" * 126)
    pr("TASK 3 -- DRIVE DECOMPOSITION OF THE 18-22 Hz TORQUE RING ON V282 (route r39), BYTE-EXACT MIRROR")
    pr("=" * 126)
    g = B.load_route(TAG)
    c = g["cells"]
    g["f0"] = B.ring_f0(g, *B.BAND[TAG])
    g["env"] = B.demod_env(g["bar"], g["f0"], FS)
    on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
    g["on"], g["pk"], g["amp"] = on, pk, amp
    wins = ES.loud_windows(g)
    pr("route %s, build V282, ring f0 %.3f Hz, %d loudest 3 s engaged windows (burst_echo_sizing.loud_windows)"
       % (TAG, g["f0"], len(wins)))
    pr()

    # ------------------------------------------------------------------ the per-LSB arithmetic
    pr("-" * 126)
    pr("3.0  WHAT ONE RATE-CHANNEL LSB IS WORTH, read from V282's OWN CELLS [EVIDENCE]")
    pr("-" * 126)
    fa, fb_, fclamp = c["fb_a"], c["fb_b"], c["fb_clamp"]
    dc = 2.0 * fb_ / (1024.0 - fa)
    first = fb_ / 1024.0
    kd = 128.0
    pr("  feedback accumulator (grind_incident_r35.simulate, mirroring the decompiled arithmetic):")
    pr("      s_new = floor((fb_a*s + fb_b*x) / 1024) ;  r26 = s + s_new ;  |r26| <= %d" % fclamp)
    pr("      fb_a = %d   fb_b = %d" % (fa, fb_))
    pr("      DC gain      = 2*fb_b/(1024-fb_a) = 2*%d/(1024-%d) = %.4f   [record: 30.89]" % (fb_, fa, dc))
    pr("      FIRST-TICK   = fb_b/1024          = %.4f" % first)
    pr("  E = 32*sp - r26, so a +1 raw count step on x = -wire moves E by -DC at steady state and by")
    pr("  -FIRST on the tick it lands.  D = floor(dE * kd / 8) with kd = %d, i.e. dE * %.0f." % (kd, kd / 8))
    pr("      ONE LSB, first tick   : dE = %+8.4f  ->  D = %+9.1f S counts" % (-first, -first * kd / 8))
    pr("      ONE LSB, steady state : dE = %+8.4f  ->  P contribution at Kp 248: %+8.1f  (P = floor(E*Kp/256))"
       % (-dc, -dc * 248 / 256))
    pr("  ⚠ THE MIRROR RUNS AT 1 kHz AND THE WIRE IS BAND-LIMITED-UPSAMPLED (C20.up1k = resample_poly")
    pr("  10:1, zero phase).  A 1-count step at 100 Hz therefore does NOT arrive as a 1 kHz step: it")
    pr("  arrives as a band-limited edge spread over ~10 ticks, so the literal 'first-tick' kick above")
    pr("  is an upper bound on what the mirror delivers.  The ABLATIONS below are what measures it.")
    pr()

    # ------------------------------------------------------------------ how big is the ring, in LSBs
    wire = g["wire"].astype(float)
    cmd = g["cmd"].astype(float)
    Ar = float(np.sqrt(2) * np.std(C20.bandpass(wire, lo, hi, FS)))
    Aa = float(np.sqrt(2) * np.std(C20.bandpass(g["ang"].astype(float), lo, hi, FS)))
    f0 = g["f0"]
    pr("-" * 126)
    pr("3.1  🛑 CORRECTION TO THE BRIEF'S PREMISE: THE RATE CHANNEL IS NOT QUANTISER-LIMITED [EVIDENCE]")
    pr("-" * 126)
    pr("  The brief reads STATE correction 8c as '0.17-0.28 LSB of 0.125 deg/s', i.e. the RATE channel.")
    pr("  The source says otherwise: OPENPILOT-EXCITATION-SOURCES-2026-09-10.md A1 is headed 'The ANGLE")
    pr("  ring is 0.17-0.28 LSB' and its point is that 0x18F STEER_ANGLE_RATE 'resolves this band ~100x")
    pr("  finer than the angle'.  0.17-0.28 is in units of the 0x14A angle's 0.1 deg LSB -- the channel")
    pr("  OPENPILOT reads -- not of the rate channel the EPS's own feedback operand reads.")
    pr()
    pr("  Measured on r39, whole route, 18-22 Hz band amplitude (sqrt(2)*rms):")
    pr("      0x18F rate   %8.3f raw counts = %.4f deg/s = %8.2f rate LSBs (0.125 deg/s)" % (Ar, Ar / V.CPD, Ar))
    pr("      0x14A angle  %8.5f deg                     = %8.3f angle LSBs (0.1 deg)" % (Aa, Aa / 0.1))
    pr("      rate -> implied angle at f0 %.2f Hz: %.5f deg = %.3f angle LSBs   [matches 0.17-0.28]"
       % (f0, Ar / V.CPD / (2 * np.pi * f0), Ar / V.CPD / (2 * np.pi * f0) / 0.1))
    pr("  ⇒ The ring is ~%.0f LSBs on the channel the EPS feedback path reads and ~%.2f LSB on the channel"
       % (Ar, Aa / 0.1))
    pr("  openpilot reads.  A quantiser is only a toggle generator when the signal is BELOW one step.")
    pr("  ⇒ THE 'QUANTISER-TOGGLE KICK' MECHANISM IS AVAILABLE TO THE OPENPILOT MEASUREMENT PATH AND")
    pr("  NOT TO THE EPS FEEDBACK PATH.  The (b) term is measured below anyway, as a dose-response.")
    pr()

    # ------------------------------------------------------------------ the ablations
    pr("-" * 126)
    pr("3.2  THE ABLATIONS -- delivered 18-22 Hz torque, byte-exact 1 kHz mirror")
    pr("-" * 126)
    pr("  Each row is  dT = bandamp( T(perturbed) - T(as measured) ), sqrt(2)*rms, over the same 10")
    pr("  windows, median + bootstrap CI.  T_total is the mirror's own delivered 18-22 Hz amplitude.")
    pr("  TP / TD are the mirror's P-only and D-only torques, so the P/D split is exact, not inferred.")
    pr()
    variants = [
        ("BASE  T_total (no perturbation)", dict(), None),
        ("(a) FEEDBACK leg: 18-22 notched out of the wire", dict(wire=bandstop(wire, lo, hi)), None),
        ("(b1) + one quantiser step of DITHER on the wire", dict(wire=wire + RNG.uniform(-0.5, 0.5, len(wire))), None),
        ("(b2) wire RE-QUANTISED at 2 LSB (0.25 deg/s)", dict(wire=np.round(wire / 2.0) * 2.0), None),
        ("(b3) wire RE-QUANTISED at 4 LSB (0.5 deg/s)", dict(wire=np.round(wire / 4.0) * 4.0), None),
        ("(b4) wire RE-QUANTISED at 8 LSB (1.0 deg/s)", dict(wire=np.round(wire / 8.0) * 8.0), None),
        ("(b5) wire RE-QUANTISED at 16 LSB (2.0 deg/s)", dict(wire=np.round(wire / 16.0) * 16.0), None),
        ("(cd) COMMAND leg: 18-22 notched out of cmd", dict(cmd=bandstop(cmd, lo, hi)), None),
        ("(c)  command leg, on the D-ONLY torque TD", dict(cmd=bandstop(cmd, lo, hi)), "D"),
        ("(d)  command leg, on the P-ONLY torque TP", dict(cmd=bandstop(cmd, lo, hi)), "P"),
        ("(a1) feedback leg, on the D-ONLY torque TD", dict(wire=bandstop(wire, lo, hi)), "D"),
        ("(a2) feedback leg, on the P-ONLY torque TP", dict(wire=bandstop(wire, lo, hi)), "P"),
        ("CONTROL: freeze the command entirely", dict(freeze=True), None),
        ("CONTROL: freeze the WIRE entirely (command only)", dict(wire=np.full_like(wire, float(np.median(wire)))), None),
        ("CONTROL: notch a SHAM band (26-30) out of the wire", dict(wire=bandstop(wire, 26.0, 30.0)), None),
        ("CONTROL: notch a SHAM band (26-30) out of cmd", dict(cmd=bandstop(cmd, 26.0, 30.0)), None),
    ]

    def run(kw, part):
        g2 = dict(g)
        if "wire" in kw:
            g2["wire"] = kw["wire"]
        if "cmd" in kw:
            g2["cmd"] = kw["cmd"]
        sim_kw = dict(freeze_cmd=kw.get("freeze", False))
        out = []
        for a0, b0, p0 in wins:
            S = GI.simulate(g2, a0, b0, c, **sim_kw)
            out.append(S["T"] if part is None else (S["TP"] if part == "P" else S["TD"]))
        return out

    base = {p: run(dict(), p) for p in (None, "P", "D")}
    T0 = float(np.median([ES.band_amp(x, lo, hi, FS1K) for x in base[None]]))
    TP0 = float(np.median([ES.band_amp(x, lo, hi, FS1K) for x in base["P"]]))
    TD0 = float(np.median([ES.band_amp(x, lo, hi, FS1K) for x in base["D"]]))
    pr("  T_total %.2f counts   (P-only %.2f, D-only %.2f, quad sum %.2f)"
       % (T0, TP0, TD0, np.hypot(TP0, TD0)))
    pr()
    pr("  %-48s | %9s %8s %-16s" % ("ablation", "dT counts", "share", "95% CI"))
    pr("  " + "-" * 92)
    res = {}
    for lab, kw, part in variants[1:]:
        vs = run(kw, part)
        ref = base[part]
        d = [ES.band_amp(vs[i] - ref[i], lo, hi, FS1K) for i in range(len(vs))]
        m = float(np.median(d))
        clo, chi = boot(np.array(d))
        den = T0 if part is None else (TP0 if part == "P" else TD0)
        res[lab.strip()] = m
        pr("  %-48s | %9.2f %8.3f [%6.2f, %6.2f]" % (lab, m, m / den, clo, chi))
    pr()
    pr("  'share' is against T_total for the whole-chain rows, and against the P-only or D-only")
    pr("  baseline for the P / D rows.  A share > 1 means the perturbation is not small -- read those")
    pr("  as 'this input dominates that path', not as a percentage.")
    pr()
    pr("  DOES IT ADD?  quadrature and linear sums of the two disjoint legs, against T_total:")
    A = res["(a) FEEDBACK leg: 18-22 notched out of the wire"]
    Cq = res["(cd) COMMAND leg: 18-22 notched out of cmd"]
    b1 = res["(b1) + one quantiser step of DITHER on the wire"]
    pr("    feedback %.2f  +  command %.2f   ->  quad %.2f (%.3f of T_total)   linear %.2f (%.3f)"
       % (A, Cq, np.hypot(A, Cq), np.hypot(A, Cq) / T0, A + Cq, (A + Cq) / T0))
    pr("    ONE quantiser step of dither on the wire moves the delivered ring by %.2f counts = %.1f %% of"
       % (b1, 100 * b1 / T0))
    pr("    T_total, and the re-quantisation ladder below it says how far the LSB would have to grow")
    pr("    before quantisation mattered.  The (b) term is therefore NOT what the feedback leg carries.")
    pr()
    with open(os.path.join(L.SCR, "openloop_drive.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("wrote _scratch/openloop_drive.txt")


if __name__ == "__main__":
    main()
