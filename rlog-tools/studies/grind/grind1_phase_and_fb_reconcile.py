# -*- coding: utf-8 -*-
"""studies/grind/grind1_phase_and_fb_reconcile.py -- closes open items 2 and 3 of
GRIND1-LOOP-SHAPE-V287-2026-09-06.md, on EXISTING logs.  Subagent `shape`, 2026-09-06.

ANALYSIS ONLY.  Builds nothing, sends nothing, flashes nothing.

ITEM 2  the T-re-rate phase at 20.3 Hz: -115 deg (mine) vs -69 deg (grind_loop_shape.py).
        Both estimators on the IDENTICAL pool, plus a delay/offset decomposition that decides which.
ITEM 3  the feedback filter's rectified/multiplicative form: does the fb pole have ANY phase effect in
        the engaged hands-off creep stratum?  Tested by stratifying on the MEAN wheel rate.

Run: python grind1_phase_and_fb_reconcile.py   (writes _scratch/grind1_phase_and_fb_reconcile.txt)
"""
import os
import sys
import math
import cmath
import struct

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


ROOT = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMG = ROOT + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
B = open(IMG, "rb").read()
u16 = lambda a: struct.unpack_from("<H", B, a)[0]
LAG_A, LAG_B = u16(0xC63EC), u16(0xC63EE)
FB_A, FB_B = u16(0xC63E8), u16(0xC63EA)
FS, FST, T = 100.0, 50.0, 1e-3

z = lambda f: cmath.exp(2j * math.pi * f * T)
Hlag = lambda f, a2=LAG_A, b2=LAG_B: (b2 / 32768.0) * (1 + 1 / z(f)) / (1 - (a2 / 1024.0) / z(f))
Hfb = lambda f, a=FB_A, b=FB_B: (b / 1024.0) * (1 + 1 / z(f)) / (1 - (a / 1024.0) / z(f))
Cc = lambda f, kp=248.0, kd=128.0: kp / 256.0 + (kd / 8.0) * (1 - 1 / z(f))
dg = lambda c: math.degrees(cmath.phase(c))

ROUTES = ["r39", "r3a", "r3c"]
G = {}
for tag in ROUTES:
    try:
        C20.BUILD[tag] = "V282"
    except Exception:
        pass
    G[tag] = C20.load(tag)
    G[tag]["tr"] = G[tag]["t"] - G[tag]["t"][0]

CREEP = lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)

pr("=" * 150)
pr("ITEM 2 -- RECONCILING THE 427-TAP PHASE RE THE WHEEL RATE AT 20.3 Hz:  -115 deg (mine) vs -69 deg (the record)")
pr("=" * 150)
pr("""
  🛑 THE ANSWER IS IN THE RECORD'S OWN SOURCE, AND IT IS NOT A MEASUREMENT DISAGREEMENT.
  `grind_loop_shape.py:380` reads, verbatim:

        Tp = abs(Cm[i]) * np.exp(1j * np.angle(C[i]))   # magnitude MEASURED, phase MODELLED

  `Cm` is the MEASURED tap transfer (rate -> T) and `C` is `C_lkas`, the modelled controller.  The deep
  analysis's sec2 phasor table therefore carries a MEASURED MAGNITUDE with a MODELLED PHASE, and -69 deg
  is `angle(C_lkas(20 Hz))`, not anything read off the wire.  The two numbers were never two measurements.
  [EVIDENCE -- the line is in the file, and the comment says so.]

  So the real question is: DOES THE MODEL'S PHASE MATCH THE WIRE?  Below I put both on the identical pool
  and decompose the residual into a pure DELAY (which ramps with frequency) and a CONSTANT model error
  (which does not).  That is the same control the r24-sign read used, and it is the only thing that can
  separate an inter-stream timing artefact from a wrong controller model.
""")


def pool_creep(tags, resampler="native", mask_extra=None):
    P = C20.Pool(FST, 64)
    secs = 0.0
    for tag in tags:
        g = G[tag]
        m = CREEP(g)
        if mask_extra is not None:
            m = m & mask_extra(g)
        d = np.diff(np.r_[0, m.astype(int), 0])
        for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
            if b_ - a_ < 80:
                continue
            if resampler == "native":
                o = C20.native_tap_segment(g, a_, b_)
                if o is None or len(o["T"]) < 64:
                    continue
                P.add({"T": o["T"], "rate": o["r"]})
                secs += len(o["T"]) / FST
            else:
                tm = (g["T_t"] >= g["t"][a_]) & (g["T_t"] <= g["t"][b_ - 1])
                if tm.sum() < 64:
                    continue
                P.add({"T": g["T"][tm], "rate": np.interp(g["T_t"][tm], g["t"], g["rate_x"])})
                secs += tm.sum() / FST
    return P, secs


FSHOW = [5.5, 7.0, 8.6, 10.9, 13.3, 15.6, 18.0, 19.5, 20.3, 21.1, 22.7]
for res in ("native", "interp"):
    P, secs = pool_creep(ROUTES, res)
    f, H, coh = P.f, P.tf("rate", "T"), P.coh("rate", "T")
    pr("  ESTIMATOR: %s resampling of the 100 Hz rate onto the tap's own 50 Hz instants   (%d windows, %.1f s)" % (
        res, P.n, secs))
    pr("    %-22s" % "f Hz" + "".join("%8.4g" % x for x in FSHOW))
    pr("    %-22s" % "measured angle(T/rate)" + "".join("%8.0f" % dg(np.interp(x, f, H.real) + 1j * np.interp(x, f, H.imag)) for x in FSHOW))
    pr("    %-22s" % "coherence" + "".join("%8.2f" % np.interp(x, f, coh) for x in FSHOW))
    if res == "native":
        Hn, fn, cn = H, f, coh
pr("")
pr("    %-22s" % "MODEL angle(C.Hlag.Hfb)" + "".join(
    "%8.0f" % (dg(Cc(x)) + dg(Hlag(x)) + dg(Hfb(x))) for x in FSHOW))
pr("      (Kp 248 flat, Kd 128, Ki 0 -- V282's actual cells, read from the image)")

pr("")
pr("  RESIDUAL DECOMPOSITION  (measured - model), regressed on frequency over 5-23 Hz.")
pr("  A pure inter-stream DELAY tau gives a residual that RAMPS at -360*tau deg/Hz with ZERO intercept.")
pr("  A wrong controller MODEL gives a constant INTERCEPT.  Only the two together explain both.")
fr = np.arange(5.0, 23.01, 0.5)
meas = np.array([dg(np.interp(x, fn, Hn.real) + 1j * np.interp(x, fn, Hn.imag)) for x in fr])
mod = np.array([dg(Cc(x)) + dg(Hlag(x)) + dg(Hfb(x)) for x in fr])
res_ = np.unwrap(np.radians(meas - mod)) * 180 / np.pi
w = np.array([np.interp(x, fn, cn) for x in fr])
sl, ic, r, pv, se = stats.linregress(fr, res_)
wsl = np.polyfit(fr, res_, 1, w=w)
pr("    unweighted:  slope %+.3f deg/Hz  intercept %+.1f deg   r %.3f   p %.1e" % (sl, ic, r, pv))
pr("    coh-weighted: slope %+.3f deg/Hz  intercept %+.1f deg" % (wsl[0], wsl[1]))
tau_ms = -sl / 360.0 * 1000.0
pr("    => implied inter-stream delay tau = %.2f ms   (the record's grind_loop_shape.py hard-codes TAU = 3.90 ms)" % tau_ms)
pr("    => residual CONSTANT model error  = %+.1f deg  (this is NOT removable by any timing correction)" % ic)
pr("")
pr("  THE THREE CANDIDATE PHASES AT 20.3 Hz, and what each implies for the LKAS lane's damping:")
i20 = 20.3
m20 = dg(np.interp(i20, fn, Hn.real) + 1j * np.interp(i20, fn, Hn.imag))
mod20 = dg(Cc(i20)) + dg(Hlag(i20)) + dg(Hfb(i20))
tau_rec = 3.9e-3
cand = [("raw measured (no timing correction)", m20),
        ("measured, record's TAU = 3.90 ms removed", m20 + 360 * tau_rec * i20),
        ("measured, MY fitted tau = %.2f ms removed" % tau_ms, m20 + 360 * (tau_ms / 1000.0) * i20),
        ("the record's number: MODELLED angle(C) at Kp 248", mod20),
        ("the record's sec2 table value (Kp 664, V280r2 era)", dg(Cc(i20, 664.0)) + dg(Hlag(i20)) + dg(Hfb(i20)))]
pr("    %-52s %10s %12s %14s" % ("phase estimate", "deg", "cos", "Re at |T|=1.90"))
for lbl, ph in cand:
    pr("    %-52s %+10.1f %12.3f %14.2f" % (lbl, ph, math.cos(math.radians(ph)), 1.90 * math.cos(math.radians(ph))))

pr("")
pr("  CORRECTED CREEP-STRATUM PHASOR TABLE  (|T| = 1.90 measured, r24 |.| = 3.23 x s, s = 0.43 measured)")
for lbl, ph20, ph7 in [("record as published (MODELLED phase)", -69.0, -62.0),
                       ("measured, TAU 3.90 ms removed", m20 + 360 * tau_rec * i20, None),
                       ("measured, fitted tau %.2f ms removed" % tau_ms, m20 + 360 * (tau_ms / 1000.0) * i20, None)]:
    Ts = 1.90 * cmath.exp(1j * math.radians(ph20))
    Rr = 3.23 * 0.43 * cmath.exp(1j * math.radians(5.0))
    pr("    %-44s  LKAS %5.2f at %+7.1f (Re %+5.2f)   r24 %5.2f at %+5.1f (Re %+5.2f)   SUM Re %+5.2f" % (
        lbl, abs(Ts), ph20, Ts.real, abs(Rr), 5.0, Rr.real, (Ts + Rr).real))

# ---------------------------------------------------------------- ITEM 3
pr("")
pr("=" * 150)
pr("ITEM 3 -- DOES THE FEEDBACK FILTER HAVE ANY PHASE EFFECT IN THE GRIND STRATUM?")
pr("=" * 150)
pr("""
  THE STRUCTURE (section 1a of the main doc, EVIDENCE from bytes).  The fb filter's output is quantised
  and then RECTIFIED (`bp / subr r0,r16` at 0x00028FC4) and enters the forward path as a MULTIPLIER:
        v = lag_out * |q32(H_fb * rate)| / 32768
  Linearising: delta_v = (G_fb0/32768)*lag(delta_u) + (lag_u0/32768) * sign(rate_slow) * H_fb(f) * delta_rate.
  The SECOND term is the only route by which the fb pole's PHASE can reach the loop, and it is
  proportional to sign(rate_slow) -- so it vanishes as the mean rate goes to zero, and its SIGN FLIPS
  with turn direction.

  THE TEST.  Stratify the engaged hands-off creep frames on |mean wheel rate| over the window.  If the fb
  path is linear in the loop, angle(T/rate) at 20 Hz must DIFFER between high-mean and near-zero-mean
  windows (the second term is present in one and absent in the other).  If it does not differ, the fb
  path contributes GAIN only, and shape 4 is not a phase lever in this stratum.
""")


def meanrate_mask(g, lo, hi):
    """window-local |mean rate| over a 1.28 s box, mapped to the frame axis."""
    n = int(1.28 * FS)
    k = np.ones(n) / n
    mr = np.abs(np.convolve(g["rate_x"], k, mode="same"))
    return (mr >= lo) & (mr < hi)


BINS = [("near-zero mean |rate| < 2 deg/s", 0.0, 2.0),
        ("low        2-5 deg/s", 2.0, 5.0),
        ("mid        5-12 deg/s", 5.0, 12.0),
        ("high       > 12 deg/s", 12.0, 1e9)]
pr("  %-34s %8s %8s %10s %10s %10s %10s" % (
    "stratum", "wins", "s", "|T/rate|20", "angle 20", "coh 20", "angle 7"))
rows = []
for lbl, lo, hi in BINS:
    P, secs = pool_creep(ROUTES, "native", mask_extra=lambda g, lo=lo, hi=hi: meanrate_mask(g, lo, hi))
    if P.n == 0:
        pr("  %-34s %8s" % (lbl, "no data"))
        continue
    f, H, coh = P.f, P.tf("rate", "T"), P.coh("rate", "T")
    hv = np.interp(20.3, f, H.real) + 1j * np.interp(20.3, f, H.imag)
    h7 = np.interp(7.0, f, H.real) + 1j * np.interp(7.0, f, H.imag)
    rows.append((lbl, abs(hv), dg(hv), np.interp(20.3, f, coh), dg(h7)))
    pr("  %-34s %8d %8.1f %10.2f %+10.1f %10.2f %+10.1f" % (
        lbl, P.n, secs, abs(hv), dg(hv), np.interp(20.3, f, coh), dg(h7)))
if len(rows) >= 2:
    ph = [r[2] for r in rows]
    mg = [r[1] for r in rows]
    pr("")
    pr("  SPREAD ACROSS THE MEAN-RATE STRATA:  phase %.1f deg (min %+.1f, max %+.1f) ; magnitude x%.2f" % (
        max(ph) - min(ph), min(ph), max(ph), max(mg) / min(mg)))
    pr("  PREDICTED phase difference IF the fb path were linear: the second term would add")
    pr("  (lag_u0/32768)*H_fb(20) with angle %+.1f deg on top of the first term's %+.1f deg -- i.e. tens of" % (
        dg(Hfb(20.3)), dg(Hlag(20.3))))
    pr("  degrees between a high-mean and a zero-mean window, in OPPOSITE directions for left and right turns.")

pr("""
  VERDICT [BELIEF, from the byte-exact structure plus the stratified measurement above].  Read the phase
  column: if it is flat across the mean-rate strata to within the coherence-limited scatter, the fb path
  is contributing GAIN and not PHASE in this stratum, and the deep analysis's shape 4 -- which ranks the
  fb pole as a phase lever worth Re@20 4.04 -- is ranked optimistically.  Under the gain-only reading the
  fb pole at 33 Hz buys x1.34 of lane gain at 20 Hz and NO rotation, which is a pure loop-gain rise: the
  same class of change as the pole raise but with none of the phase benefit.  That is why I do not pick
  it, independently of the ranking.
""")

with open(os.path.join(SCR, "grind1_phase_and_fb_reconcile.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT) + "\n")
pr("[written to _scratch/grind1_phase_and_fb_reconcile.txt]")
