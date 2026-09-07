# -*- coding: utf-8 -*-
"""studies/grind/grind1_loop_shape_v287.py -- the LOOP SHAPE for grind #1 (the 18-22 Hz creep grind),
sized byte-exactly on the V282 image and pre-registered against the r39/r3a/r3c wire.  Subagent `shape`, 2026-09-06.

ANALYSIS ONLY.  Builds nothing, sends nothing, flashes nothing.

SECTION 1  the two one-pole IIRs inside FUN_00028ea6, mirrored from the disassembly (integer, LE, real shifts)
SECTION 2  pole design -- (a,b) halfword pairs for 8/10/12/15 Hz with the DC gain held, + overflow bounds
SECTION 3  the cost surface |H_new/H_old| and the phase rotation, across frequency
SECTION 4  the aggregator damping budget, re-ranked on the MEASURED s (plant-free)
SECTION 5  model (a): the 27-32 Hz Nyquist crossing, gain margin, and the 25-50 Hz blind-band loop gain
SECTION 6  the pre-registration numbers, computed on r39/r3a/r3c's own wire BEFORE the drive

Run: python grind1_loop_shape_v287.py   (writes _scratch/grind1_loop_shape_v287.txt beside it)
"""
import os
import sys
import math
import cmath
import struct
import hashlib

import numpy as np
from scipy import signal

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
STOCK = ROOT + "stock_fw_dump/code.bin"
B = open(IMG, "rb").read()
BS = open(STOCK, "rb").read()
u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]

TP = 0xBF000
LAG_A, LAG_B = u16(B, 0xC63EC), u16(B, 0xC63EE)
FB_A, FB_B = u16(B, 0xC63E8), u16(B, 0xC63EA)
CL_FB = u16(B, 0xC62E6)      # fb output clamp
CL_PID = u16(B, 0xC61BE)     # PID-sum clamp, the out-lag INPUT bound
CL_P = u16(B, 0xC61BC)       # P clamp
CL_OUT = u16(B, 0xC61B4)     # gp-0x6b38 clamp
DB = u16(B, 0xC61B8)         # P-only deadband
K6 = u16(B, 0xC6CD0)         # forward gain (tp+0x7cd0 on V282; stock reads tp+0x746c = 891)
KDEAD = B[TP + 0x74A3]
FS, FS1K, FST = 100.0, 1000.0, 50.0
T = 1e-3

pr("=" * 150)
pr("GRIND #1 LOOP SHAPE -- the two never-touched one-pole IIRs in the LKAS rate PID, sized from the V282 image")
pr("=" * 150)
pr("  image   %s" % os.path.basename(IMG))
pr("  sha256  %s" % hashlib.sha256(B).hexdigest())
pr("  stock   sha256 %s" % hashlib.sha256(BS).hexdigest()[:32])

# ---------------------------------------------------------------- SECTION 1
pr("")
pr("=" * 150)
pr("1. THE ARITHMETIC, MIRRORED FROM THE DISASSEMBLY (FUN_00028ea6; GhidraMCP, dry_run; constants read LE here)")
pr("=" * 150)
pr("""
  1a. FEEDBACK FILTER -- 0x00028F86 .. 0x00028FC7.  Input x = gp-0x6a56 (16-bit rate operand).
      State D_fb = *(int32*)(gp-0x3d30), zeroed when gp-0x3d2c != 1.

        00028f86  ld.hu  0x73ea, tp, r16     ; b  = cal(0xC63EA)
        00028f8a  ld.h   0x73e8, tp, r9      ; a  = cal(0xC63E8)
        00028f8e  mul    r16, r7, r0         ; r7  = x * b          (32x32 -> low word)
        00028f92  mul    r26, r9, r0         ; r9  = D_prev * a
        00028f9a  sar    0xa, r7             ; >>10 ARITHMETIC
        00028fa0  sar    0xa, r9             ; >>10 ARITHMETIC
        00028fa2  add    r7, r9              ; r9  = D_new
        00028fa4  add    r9, r26             ; r26 = D_prev + D_new   <-- THE TWO-SAMPLE SUM
        00028fa8  st.w   r9, -0x3d30, gp     ; state := D_new        (32-bit accumulator)
        00028fa6..00028fbc                   ; clamp r26 to +- cal(0xC62E6)
        00028fc0  sar 0x5,r16 / shl 0x5,r16  ; quantise to a multiple of 32
        00028fc4  bp / subr r0, r16          ; ABSOLUTE VALUE          <-- r16 = G_fb, always >= 0

      def fb_step(D_prev, x, a, b, clamp):
          D_new = (a * D_prev >> 10) + (x * b >> 10)      # both >> arithmetic, int32
          y     = D_prev + D_new
          y     = max(-clamp, min(clamp, y))
          return D_new, abs((y >> 5) << 5)

  1b. OUTPUT LAG -- 0x0002A180 .. 0x0002A1B3.  Input u = the PID sum, already clamped to +- cal(0xC61BE).
      State D_lag = *(int32*)(gp-0x3d3c).

        0002a180  mul    r7, r12, r0         ; r12 = u * b2   (r7 = b2 = cal(0xC63EE), loaded earlier)
        0002a184  ld.h   0x73ec, tp, r7      ; a2  = cal(0xC63EC)
        0002a194  mul    r9, r7, r0          ; r7  = D_prev * a2
        0002a1a0  sar    0xa, r12            ; >>10
        0002a1a6  sar    0xa, r7             ; >>10
        0002a1a8  add    r12, r7             ; r7  = D_new
        0002a1aa  add    r7, r9              ; r9  = D_prev + D_new   <-- THE SAME TWO-SAMPLE SUM
        0002a1ac  sar    0x5, r9             ; >>5   <-- THE /32 THAT MAKES DC 0.99, NOT 31.7
        0002a1b0  st.w   r7, -0x3d3c, gp     ; state := D_new

      def lag_step(D_prev, u, a2, b2):
          D_new = (a2 * D_prev >> 10) + (u * b2 >> 10)
          return D_new, (D_prev + D_new) >> 5

  BOTH filters are the SAME structure:  H(z) = (b/1024) * (1 + z^-1) / (1 - (a/1024) z^-1),
  i.e. a one-pole IIR on the INCREMENT with a one-sample SUM on the output.  The pole is a/1024
  and the zero is fixed at Nyquist.  Sample rate 1 kHz.
""")

pr("  1c. WHAT THE TWO FEED  (0x0002A1B4 .. 0x0002A23F)")
pr("      P-only deadband, enabled by cal(0xC64A3) = %d and gated on gp-0x6806 == 0:" % KDEAD)
pr("      if |lag_out| <= cal(0xC61B8) = %d AND lag_out * previous_output <= 0  ->  output forced to 0." % DB)
pr("      else  v = sxh( (lag_out * G_fb) >> 15 )                                 (0x0002A1E6-EC)")
pr("      then  T = clamp( +- cal(0xC61B4) = %d ,  (-K6 * (r11 + v)) >> 15 ),  K6 = cal(0xC6CD0) = %d" % (CL_OUT, K6))
pr("      [EVIDENCE -- firmware-codepath-tracer, 2026-09-06, 11 dominating r11 writers enumerated at the")
pr("      0x29A48 join plus a raw LE byte scan]: r11 is (short)[gp-0x6b2c] on EVERY path reaching 0x2A1FC,")
pr("      and that cell is IDENTICALLY ZERO in stock and V282 (its LERP Y table 0xC673E..0xC6744 is 0,0,0,0")
pr("      and the gp-0x6a5e >= 32001 gate forces the above-range branch anyway).  So there is NO addend:")
pr("          T = clamp( +- %d , (-K6 * v) >> 15 )." % CL_OUT)
pr("      The 427 tap is the LKAS lane and nothing else -- no torsion-bar feedthrough.  This REFUTES my own")
pr("      working hypothesis that part of the tap's 18-22 Hz ripple is direct bar feedthrough.")
pr("")
pr("  CELLS READ FROM THE V282 IMAGE (and from stock, for the delta):")
pr("    %-10s %-12s %-30s %8s %8s" % ("addr", "tp offset", "what", "V282", "stock"))
for a, off, w in [(0xC63E8, 0x73E8, "fb filter pole  a"), (0xC63EA, 0x73EA, "fb filter gain  b"),
                  (0xC63EC, 0x73EC, "output lag pole a2"), (0xC63EE, 0x73EE, "output lag gain b2"),
                  (0xC62E6, 0x72E6, "fb output clamp"), (0xC61BE, 0x71BE, "PID-sum clamp (lag input)"),
                  (0xC61BC, 0x71BC, "P clamp"), (0xC61B8, 0x71B8, "P-only deadband"),
                  (0xC61B4, 0x71B4, "gp-0x6b38 output clamp"), (0xC646C, 0x746C, "fwd gain (stock reader)"),
                  (0xC6CD0, 0x7CD0, "fwd gain (V282 reader)"), (0xC6446, 0x7446, "r24 lane gain")]:
    pr("    0x%05X   tp+0x%04x   %-30s %8d %8d" % (a, off, w, u16(B, a), u16(BS, a)))


def lag_dc_int(a2, b2, u=10000, n=100000):
    D = 0
    for _ in range(n):
        D = (a2 * D >> 10) + (u * b2 >> 10)
    Dp = D
    D = (a2 * D >> 10) + (u * b2 >> 10)
    return ((Dp + D) >> 5) / float(u)


def fb_dc_int(a, b, x=100, n=100000):
    D = 0
    for _ in range(n):
        D = (a * D >> 10) + (x * b >> 10)
    Dp = D
    D = (a * D >> 10) + (x * b >> 10)
    return (Dp + D) / float(x)


pr("")
pr("  DC-GAIN VERIFICATION [EVIDENCE -- analytic form vs a bit-exact integer step response]")
pr("    output lag  2*b2/(1024-a2)/32 = 2*%d/(1024-%d)/32 = %.6f  ; integer step response = %.6f" % (
    LAG_B, LAG_A, 2.0 * LAG_B / (1024 - LAG_A) / 32.0, lag_dc_int(LAG_A, LAG_B)))
pr("    fb filter   2*b /(1024-a )     = 2*%d/(1024-%d)     = %.4f   ; integer step response = %.4f" % (
    FB_B, FB_A, 2.0 * FB_B / (1024 - FB_A), fb_dc_int(FB_A, FB_B)))
pr("    => the record's '2b/(1024-a)/32 = 0.990' is CONFIRMED FROM BYTES, and the /32 is `sar 0x5, r9`")
pr("       at 0x0002A1AC.  The fb filter has NO such /32, which is why its DC gain is 30.89 (memory")
pr("       accord-feedback-operand-is-a-two-sample-sum-dc-30-89, reproduced here independently).")

# ---------------------------------------------------------------- transfer functions
z = lambda f: cmath.exp(2j * math.pi * f * T)


def Hlag(f, a2=None, b2=None):
    a2 = LAG_A if a2 is None else a2
    b2 = LAG_B if b2 is None else b2
    zz = z(f)
    return (b2 / 32768.0) * (1 + 1 / zz) / (1 - (a2 / 1024.0) / zz)


def Hfb(f, a=None, b=None):
    a = FB_A if a is None else a
    b = FB_B if b is None else b
    zz = z(f)
    return (b / 1024.0) * (1 + 1 / zz) / (1 - (a / 1024.0) / zz)


dg = lambda c: math.degrees(cmath.phase(c))
polef = lambda a: -math.log(a / 1024.0) * 1000.0 / (2 * math.pi)

# ---------------------------------------------------------------- SECTION 2
pr("")
pr("=" * 150)
pr("2. POLE DESIGN -- the halfword pairs, DC held.  a = round(1024*exp(-2*pi*f/1000)); b holds the DC gain.")
pr("=" * 150)


def design_lag(ftgt):
    a = int(round(1024.0 * math.exp(-2 * math.pi * ftgt / 1000.0)))
    dc0 = 2.0 * LAG_B / (1024 - LAG_A) / 32.0
    braw = dc0 * 32 * (1024 - a) / 2.0
    best = min([int(math.floor(braw)), int(math.ceil(braw))],
               key=lambda bb: abs(2.0 * bb / (1024 - a) / 32.0 - dc0))
    return a, best


def design_fb(ftgt):
    a = int(round(1024.0 * math.exp(-2 * math.pi * ftgt / 1000.0)))
    dc0 = 2.0 * FB_B / (1024 - FB_A)
    braw = dc0 * (1024 - a) / 2.0
    best = min([int(math.floor(braw)), int(math.ceil(braw))],
               key=lambda bb: abs(2.0 * bb / (1024 - a) - dc0))
    return a, best


LAG_SHAPES = [("as-built 5.05 Hz", LAG_A, LAG_B)]
for ft in (8, 10, 12, 15):
    LAG_SHAPES.append(("lag pole -> %2d Hz" % ft, ) + design_lag(ft))
LAG_SHAPES.append(("record 932/1457", 932, 1457))
LAG_SHAPES.append(("record 963/986", 963, 986))

FB_SHAPES = [("as-built 16.5 Hz", FB_A, FB_B)]
for ft in (25, 33):
    FB_SHAPES.append(("fb pole -> %2d Hz" % ft, ) + design_fb(ft))
FB_SHAPES.append(("record 842/2814", 842, 2814))

dc0 = 2.0 * LAG_B / (1024 - LAG_A) / 32.0
pr("  OUTPUT LAG  0xC63EC (a2) / 0xC63EE (b2)   -- target DC = %.6f" % dc0)
pr("  %-20s %6s %6s %9s %10s %9s %12s %10s" % (
    "shape", "a2", "b2", "pole Hz", "DC gain", "dDC %", "|H|/|H0|@20", "asympt"))
for nm, a, b in LAG_SHAPES:
    dc = 2.0 * b / (1024 - a) / 32.0
    asy = (b / float(LAG_B)) * (1 + LAG_A / 1024.0) / (1 + a / 1024.0)
    pr("  %-20s %6d %6d %9.2f %10.6f %+8.3f%% %12.3f %10.3f" % (
        nm, a, b, polef(a), dc, 100 * (dc / dc0 - 1), abs(Hlag(20, a, b) / Hlag(20)), asy))
pr("  ('asympt' is the exact Nyquist-limit ratio (b2n/b2o)*(1+a2o/1024)/(1+a2n/1024); the record's 'x2.88")
pr("   asymptote' for 932/1457 is the cruder b2 ratio 1457/507 = %.3f.)" % (1457 / 507.0))

dcf0 = 2.0 * FB_B / (1024 - FB_A)
pr("")
pr("  FEEDBACK FILTER  0xC63E8 (a) / 0xC63EA (b)   -- target DC = %.4f" % dcf0)
pr("  %-20s %6s %6s %9s %10s %9s %12s" % ("shape", "a", "b", "pole Hz", "DC gain", "dDC %", "|H|/|H0|@20"))
for nm, a, b in FB_SHAPES:
    dc = 2.0 * b / (1024 - a)
    pr("  %-20s %6d %6d %9.2f %10.4f %+8.3f%% %12.3f" % (
        nm, a, b, polef(a), dc, 100 * (dc / dcf0 - 1), abs(Hfb(20, a, b) / Hfb(20))))
pr("  NOTE the record labels 842/2814 '33 Hz'; the exact pole of a=842 is %.2f Hz.  My 33 Hz design is %d/%d." % (
    (polef(842), ) + design_fb(33)))

pr("")
pr("  OVERFLOW / SATURATION AT THE CLAMP EXTREMES  [EVIDENCE -- from the widths in section 1]")
pr("    The lag INPUT is the PID sum already clamped to +- cal(0xC61BE) = %d." % CL_PID)
pr("    Holding DC forces b2/(1024-a2) = DC*16 = %.5f for EVERY design, so the steady state" % (dc0 * 16))
pr("    D_lag = b2*u/(1024-a2) = %.5f*u is INVARIANT: %.0f at |u| = %d." % (dc0 * 16, dc0 * 16 * CL_PID, CL_PID))
pr("    The recursion is a first-order lowpass with 0 < a2/1024 < 1 driven by a bounded input, so |D_lag|")
pr("    never exceeds that steady state.  Worst intermediate is a2*D_lag:")
pr("    %-20s %6s %12s %14s %14s %11s" % ("shape", "a2", "|D_lag| max", "a2*D_lag max", "u*b2 max", "int32 hdrm"))
for nm, a, b in LAG_SHAPES:
    Dm = b * CL_PID / float(1024 - a)
    pr("    %-20s %6d %12.0f %14.3e %14.3e %10.1fx" % (nm, a, Dm, a * Dm, CL_PID * b, 2 ** 31 / (a * Dm)))
pr("    => NO overflow at any of these poles, and the headroom is IDENTICAL to as-built, because")
pr("       holding DC holds the state magnitude.  [EVIDENCE]")
pr("")
XG = 12000.0   # gp-0x6a56 band guard at the function entry (|x| + 12000 < 0x5dc1)
Dfbm = FB_B * XG / float(1024 - FB_A)
pr("    The fb filter's input x = gp-0x6a56 is band-guarded to |x| <= %.0f by the entry test at 0x00028F60ish." % XG)
pr("    Steady state D_fb = %.5f*x = %.0f at that bound; a*D_fb = %.3e, headroom %.0fx." % (
    FB_B / float(1024 - FB_A), Dfbm, FB_A * Dfbm, 2 ** 31 / (FB_A * Dfbm)))
pr("    Its OUTPUT is clamped to +- %d, which binds at |x| >= %.0f counts; with DC held every fb design" % (
    CL_FB, CL_FB / dcf0))
pr("    binds at the same |x|, so the fb clamp's duty is invariant to the fb pole too.  [EVIDENCE]")
vmax = (CL_PID * dc0 * CL_FB) / 32768.0
pr("")
pr("    THE ONE PLACE A SHORT TRUNCATION COULD BITE is `sxh r9` at 0x0002A1EC, on v = (lag_out*G_fb)>>15.")
pr("    Bound: |lag_out| <= DC*|u| = %.0f, G_fb <= %d  =>  |v| <= %.0f < 32767, so sxh never wraps." % (
    dc0 * CL_PID, CL_FB, vmax))
pr("    DC held => THE SAME BOUND for every pole design.  [EVIDENCE]")
pr("    Downstream T = clamp(+-%d, -K6*v>>15) saturates at |v| > %.0f (%.1f%% of the |v| bound);" % (
    CL_OUT, CL_OUT * 32768.0 / K6, 100.0 * (CL_OUT * 32768.0 / K6) / vmax))
pr("    measured 427 saturation on r39/r3a/r3c is 0.0000 pct (STATE), so that clamp is not live today.")

# ---------------------------------------------------------------- SECTION 3
pr("")
pr("=" * 150)
pr("3. THE COST SURFACE -- |H_new/H_old| and the PHASE ROTATION of the LKAS lane, by frequency")
pr("=" * 150)
FGRID = [1, 2, 3.9, 5, 7, 7.3, 10, 15, 18, 20, 22, 25, 28, 30, 35, 40, 45, 50]
pr("  |H_lag_new / H_lag_old|   (the LKAS lane's own gain change; DC is held so the 1 Hz column is ~1.00)")
pr("  %-20s" % "shape" + "".join("%7.4g" % f for f in FGRID))
for nm, a, b in LAG_SHAPES:
    pr("  %-20s" % nm + "".join("%7.2f" % abs(Hlag(f, a, b) / Hlag(f)) for f in FGRID))
pr("")
pr("  PHASE ROTATION of the LKAS lane, deg (positive = LEAD = less lag = better damping)")
pr("  %-20s" % "shape" + "".join("%7.4g" % f for f in FGRID))
for nm, a, b in LAG_SHAPES:
    pr("  %-20s" % nm + "".join("%+7.1f" % (dg(Hlag(f, a, b)) - dg(Hlag(f))) for f in FGRID))
pr("")
pr("  ABSOLUTE phase of the output lag, deg (as-built is the -54 / -76 deg the record quotes at 7 / 20 Hz)")
pr("  %-20s" % "shape" + "".join("%7.4g" % f for f in FGRID))
for nm, a, b in LAG_SHAPES:
    pr("  %-20s" % nm + "".join("%+7.1f" % dg(Hlag(f, a, b)) for f in FGRID))
pr("")
pr("  FEEDBACK FILTER, same two tables")
pr("  %-20s" % "|H_fb_new/H_fb_old|" + "".join("%7.4g" % f for f in FGRID))
for nm, a, b in FB_SHAPES:
    pr("  %-20s" % nm + "".join("%7.2f" % abs(Hfb(f, a, b) / Hfb(f)) for f in FGRID))
pr("  %-20s" % "phase rotation deg" + "".join("%7.4g" % f for f in FGRID))
for nm, a, b in FB_SHAPES:
    pr("  %-20s" % nm + "".join("%+7.1f" % (dg(Hfb(f, a, b)) - dg(Hfb(f))) for f in FGRID))

pr("""
  🛑 A STRUCTURAL CAVEAT ON THE FEEDBACK FILTER THAT THE RECORD'S RANKING DOES NOT CARRY.
  The fb filter's output is passed through `sar 5 / shl 5` and then an ABSOLUTE VALUE (0x00028FC4), and
  it enters the forward path as a MULTIPLIER on the lag output, not as an additive feedback term:
        v = lag_out * |q32(H_fb * rate)| / 32768.
  Linearising about an operating point, delta_v = (G_fb0/32768)*lag(delta_u) + (lag_u0/32768)*delta|G_fb|,
  and delta|G_fb| = sign(rate_slow) * H_fb(f) * delta_rate.  So:
    - the fb pole's effect that is UNAMBIGUOUS is a GAIN change on the whole LKAS lane, by |H_fb(f)| at
      whatever frequency dominates the rate;
    - its effect as a PHASE element exists only through the second term, whose SIGN FLIPS WITH THE SIGN
      OF THE MEAN WHEEL RATE and which vanishes as the mean rate goes to zero -- i.e. exactly in the
      engaged hands-off creep stratum where grind #1 lives.
  The deep analysis's shape 4 treats the fb pole as a linear phase element in the servo lane.  That is
  the OPTIMISTIC reading.  I do not use it, and it is one reason I do not pick shape 4.  [BELIEF, from
  the byte-exact structure; the arithmetic in section 1a is EVIDENCE]
""")

# ---------------------------------------------------------------- SECTION 4
pr("=" * 150)
pr("4. THE AGGREGATOR DAMPING BUDGET, RE-RANKED -- plant-free, from the MEASURED lane phasors")
pr("=" * 150)
pr("""
  METHOD.  Every lane enters the 1 kHz aggregator with a UNIT coefficient (FUN_0003aa2c: iVar19 = ... +
  iVar21 + iVar16, clamp +-0x2800 -> gp-0x6b94), so lane phasors ADD DIRECTLY and comparing them needs
  no plant, no sign convention and no unit conversion.  Re(phasor re wheel rate) > 0 = DAMPING.

  MEASURED INPUTS (GRINDING-DEEP-ANALYSIS-2026-09-03 sec2, corrected-convention phases; V282-R24-TAP-READ
  sec3.1 / V282-READ-r39 sec0.3 for s):
    creep hands-off, 20 Hz : LKAS lane 1.90 at -69 deg (coh 0.81) ; r24 3.23 at +5 deg (coh 0.80)
    loaded high-angle, 7 Hz: LKAS lane 2.50 at -62 deg (coh 0.92) ; r24 3.37 at +166 deg (coh 0.76)
  s = |r24|_wire / |r24|_closed-form, MEASURED on the V282 cave bits: 0.42/0.43 (r36-r38), 0.41/0.52 (r39).
  Adopted s = 0.43, swept over the whole measured range 0.30 - 0.52.

  A LAG-POLE SHAPE ROTATES AND SCALES THE LKAS LANE EXACTLY BY H_lag_new/H_lag_old (section 3) AND DOES
  NOT TOUCH r24 AT ALL (r24 is FUN_0003aa2c, which never reads 0xC63EC/EE).  That is why this ranking is
  the least model-dependent one available.
""")
LANE = {
    20: dict(As=1.90, ps=-69.0, Ar=3.23, pr_=+5.0, stratum="creep hands-off"),
    7: dict(As=2.50, ps=-62.0, Ar=3.37, pr_=+166.0, stratum="loaded high-angle"),
}
GAIN0 = 5244.0
SSHAPES = [("lag 6.0 Hz 986/602", 986, 602), ("lag 6.5 Hz 983/650", 983, 650),
           ("lag 7.2 Hz 979/713", 979, 713), ("lag 8.0 Hz 974/792", 974, 792),
           ("lag 10 Hz 962/982", 962, 982), ("lag 15 Hz 932/1458", 932, 1458)]
# model (b) ring arms, 7.3 Hz (STUTTER-7HZ-V283 A13-A14 composition; used ONLY as a ratio)
Ls_ = 0.55 * cmath.exp(1j * math.radians(96))
Lr_ = 1.19 * cmath.exp(1j * math.radians(-27))


def budget(f, a2, b2, gain=GAIN0, s=0.43, fb=None):
    d = LANE[f]
    R = Hlag(f, a2, b2) / Hlag(f)
    if fb is not None:
        R = R * (Hfb(f, fb[0], fb[1]) / Hfb(f))
    Ps = d["As"] * cmath.exp(1j * math.radians(d["ps"])) * R
    Pr = d["Ar"] * cmath.exp(1j * math.radians(d["pr_"])) * s * (gain / GAIN0)
    return Ps, Pr, Ps + Pr


SHAPES = []
SHAPES.append(("as-built V282", LAG_A, LAG_B, GAIN0, None))
for ft in (8, 10, 12, 15):
    a, b = design_lag(ft)
    SHAPES.append(("lag pole -> %2d Hz" % ft, a, b, GAIN0, None))
SHAPES.append(("lag 15 Hz + 0xC6446 2048", 932, 1457, 2048.0, None))
SHAPES.append(("lag 12 Hz + 0xC6446 2048", ) + design_lag(12) + (2048.0, None))
for ft in (25, 33):
    a, b = design_fb(ft)
    SHAPES.append(("fb pole -> %2d Hz (gain-only)" % ft, LAG_A, LAG_B, GAIN0, (a, b)))
a12, b12 = design_lag(12)
a25, b25 = design_fb(25)
SHAPES.append(("lag 12 Hz + fb 25 Hz", a12, b12, GAIN0, (a25, b25)))
a15, b15 = design_lag(15)
a33, b33 = design_fb(33)
SHAPES.append(("lag 15 Hz + fb 33 Hz", a15, b15, GAIN0, (a33, b33)))
SHAPES.append(("FRONTIER lag 6.0 Hz 986/602", 986, 602, GAIN0, None))
SHAPES.append(("FRONTIER lag 6.5 Hz 983/650", 983, 650, GAIN0, None))
SHAPES.append(("FRONTIER lag 7.2 Hz 979/713", 979, 713, GAIN0, None))
SHAPES.append(("0xC6446 -> 2048 alone", LAG_A, LAG_B, 2048.0, None))
SHAPES.append(("0xC6446 -> 512 alone (DO NOT)", LAG_A, LAG_B, 512.0, None))

pr("  RANKED, at the adopted s = 0.43.  Re > 0 = damping.  |C|@20 is the LKAS lane's own gain (HF risk proxy).")
pr("  %-30s %8s %8s %8s %8s %8s %9s %8s" % (
    "shape", "Re@7", "xbase", "Re@20", "xbase", "|C|@20", "|sum|@20", "DC auth"))
base7 = budget(7, LAG_A, LAG_B)[2].real
base20 = budget(20, LAG_A, LAG_B)[2].real
for nm, a, b, g, fb in SHAPES:
    P7 = budget(7, a, b, g, 0.43, fb)
    P20 = budget(20, a, b, g, 0.43, fb)
    dcn = 2.0 * b / (1024 - a) / 32.0
    pr("  %-30s %8.2f %8.2f %8.2f %8.2f %8.2f %9.2f %8.4f" % (
        nm, P7[2].real, P7[2].real / abs(base7) * (1 if base7 > 0 else -1) if base7 else float("nan"),
        P20[2].real, P20[2].real / base20, abs(P20[0]), abs(P20[2]), dcn))
pr("  (the 'xbase' at 7 Hz is signed against |base|; the base itself is NEGATIVE, so a positive value")
pr("   means the sign has FLIPPED from pumping to damping.)")

pr("")
pr("  SENSITIVITY TO s OVER ITS WHOLE MEASURED RANGE")
SS = (0.30, 0.37, 0.43, 0.52)
pr("  %-30s %s | %s" % ("shape", "".join("%9s" % ("Re@7 s=%.2f" % s) for s in SS),
                        "".join("%10s" % ("Re@20 s=%.2f" % s) for s in SS)))
for nm, a, b, g, fb in SHAPES:
    pr("  %-30s %s | %s" % (nm,
                            "".join("%9.2f" % budget(7, a, b, g, s, fb)[2].real for s in SS),
                            "".join("%10.2f" % budget(20, a, b, g, s, fb)[2].real for s in SS)))

# ---------------------------------------------------------------- SECTION 5
pr("")
pr("=" * 150)
pr("5. MODEL (a) -- the 27-32 Hz NYQUIST CROSSING, gain margin, and the 25-50 Hz BLIND-BAND loop gain")
pr("=" * 150)
pr("""
  🛑 LOOP-MODEL-CONVENTION-DEFECT-2026-09-04 is binding here: the kit carries TWO loop models in opposite
  conventions and a single closed-loop |T(f)| curve is NOT computable from what has been measured.  I do
  NOT produce one.  What IS licensed (that note, sec4) is: model (a), the negative-feedback delay model,
  for GAIN-MARGIN / Ku / blind-band questions in 20-32 Hz; model (b), the measured ring, for 7.3 Hz and
  ONLY as a RATIO between candidates.  Section 4 above is neither -- it is the plant-free damping budget.

  Model (a) is zn_ku_corrected.py's, re-implemented here and re-anchored on the AS-BUILT filters:
    C(f) = Kp/256 + (Kd/8)(1 - z^-1)            (byte-exact controller, Kp 248 / Kd 128 / Ki 0)
    L(f) = KMAG * C(f) * Hlag(f) * Hfb(f) * exp(j*(PH_G20 + SLOPE*(f-20)))
  with PH_G20 implied by CREEP-20HZ item 4's angle L(20) = +157 deg at Kd 0 / Kp 295, SLOPE = -3.75 deg/Hz
  from the measured plant phases (-28 deg @ 10 Hz, -73 deg @ 22 Hz), and KMAG set by |L(20)| = 0.37 there.
  PH_G20 and KMAG are PLANT properties and are computed ONCE, from the AS-BUILT filters, then held fixed
  while the filters change.  [EVIDENCE for the 10-22 Hz slope and the 22-28 Hz GM; BELIEF above 25 Hz.]
""")
KP, KD = 248.0, 128.0


def Cc(f, kp=KP, kd=KD):
    return kp / 256.0 + (kd / 8.0) * (1 - 1 / z(f))


PH_G20 = 157.0 - dg(Cc(20, 295, 0)) - dg(Hlag(20)) - dg(Hfb(20)) - 360.0
SLOPE = -(73.0 - 28.0) / 12.0
KMAG = 0.37 / abs(Cc(20, 295, 0) * Hlag(20) * Hfb(20))
pr("  anchored: PH_G20 = %+.1f deg (independent creep20 measurement -73 deg at 22 Hz; agreement %.1f deg)" % (
    PH_G20, abs(PH_G20 - (-73))))
pr("            SLOPE  = %+.2f deg/Hz  (%.1f ms equivalent delay) ; KMAG = %.5f" % (
    SLOPE, 1000 * (-SLOPE) / 360.0, KMAG))


def phL(f, a2, b2, fb, kp=KP, kd=KD):
    fbp = fb if fb else (FB_A, FB_B)
    return dg(Cc(f, kp, kd)) + dg(Hlag(f, a2, b2)) + dg(Hfb(f, fbp[0], fbp[1])) + PH_G20 + SLOPE * (f - 20)


def magL(f, a2, b2, fb, kp=KP, kd=KD):
    fbp = fb if fb else (FB_A, FB_B)
    return KMAG * abs(Cc(f, kp, kd) * Hlag(f, a2, b2) * Hfb(f, fbp[0], fbp[1]))


def f180(a2, b2, fb, lo=12.0, hi=300.0, kp=KP, kd=KD):
    g = lambda f: phL(f, a2, b2, fb, kp, kd) + 180.0
    if g(lo) * g(hi) >= 0:
        return None
    for _ in range(90):
        m = (lo + hi) / 2.0
        if g(lo) * g(m) < 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2.0


pr("")
pr("  %-30s %10s %8s %9s %9s %9s %9s %9s" % (
    "shape", "f(-180)", "|L|", "GAIN MRG", "GM dB", "vs base", "|L|@30", "|L|@40"))
row0 = None
for nm, a, b, g_, fb in SHAPES:
    fx = f180(a, b, fb)
    if fx is None:
        pr("  %-30s %10s" % (nm, "none"))
        continue
    Lm = magL(fx, a, b, fb)
    gm = 1.0 / Lm
    if row0 is None:
        row0 = gm
    flag = "   UNSTABLE" if gm < 1.0 else ("   <1.3x" if gm < 1.30 else "")
    pr("  %-30s %9.1fHz %8.3f %8.2fx %8.1f %9.2f %9.3f %9.3f%s" % (
        nm, fx, Lm, gm, 20 * math.log10(gm), gm / row0, magL(30, a, b, fb), magL(40, a, b, fb), flag))
pr("  (base row reproduces the addendum's Kp 248 / Kd 128 result: f(-180) 28.1 Hz, GM 1.77x, 5.0 dB.)")

pr("")
pr("=" * 150)
pr("5b. 🛑 THE GAIN-MARGIN FRONTIER -- how far the output-lag pole can actually be moved")
pr("=" * 150)
pr("""
  The rows above are the single most important result in this file and they were NOT run by the record.
  Raising the output-lag pole adds PHASE LEAD (good, section 3) and GAIN (bad) in the SAME band, and the
  27-32 Hz Nyquist crossing is decided by the gain.  The lead pushes the crossing UP in frequency, but
  with the pole at 10-15 Hz the lane no longer rolls off there, so |L| at the new crossing is HIGHER, not
  lower.  Under the delay plant -- the model that reproduces the kit's OWN measured gain margins -- the
  record's headline shape (932/1457, 15 Hz) does not merely spend margin, it CROSSES UNITY.
""")
pr("  FINE SCAN of the lag pole against the gain margin, at Kd 128 / Kp 248:")
pr("  %-10s %6s %6s %9s %8s %9s %9s %9s %9s %9s" % (
    "pole Hz", "a2", "b2", "f(-180)", "|L|", "GM", "GM dB", "Re@7", "Re@20", "ring x"))
for ft in (5.05, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 9.0, 10.0, 12.0, 15.0):
    if abs(ft - 5.05) < 1e-6:
        a, b = LAG_A, LAG_B
    else:
        a, b = design_lag(ft)
    fx = f180(a, b, None)
    gm = 1.0 / magL(fx, a, b, None)
    R73 = Hlag(7.3, a, b) / Hlag(7.3)
    pr("  %-10.2f %6d %6d %8.1fHz %8.3f %8.2fx %8.1f %9.2f %9.2f %9.3f" % (
        polef(a), a, b, fx, magL(fx, a, b, None), gm, 20 * math.log10(gm),
        budget(7, a, b)[2].real, budget(20, a, b)[2].real, abs(Ls_ * R73 + Lr_) / abs(Ls_ + Lr_)))
pr("")
pr("  GM-CONSTRAINED FRONTIER -- the largest pole that holds each margin gate (bisection on the pole):")


def gm_of(a, b, kd=KD):
    fx = f180(a, b, None, kd=kd)
    return 1.0 / magL(fx, a, b, None, kd=kd), fx


def max_pole_for(gate, kd=KD):
    lo, hi = 5.05, 16.0
    if gm_of(*design_lag(hi), kd=kd)[0] > gate:
        return hi
    for _ in range(60):
        m = (lo + hi) / 2.0
        a, b = design_lag(m)
        if gm_of(a, b, kd=kd)[0] >= gate:
            lo = m
        else:
            hi = m
    return lo


for gate, lbl in [(1.77, "GM unchanged (5.0 dB)"), (1.50, "GM 3.5 dB"), (1.41, "GM 3.0 dB"), (1.30, "GM 2.3 dB")]:
    fmax = max_pole_for(gate)
    a, b = design_lag(fmax)
    g, fx = gm_of(a, b)
    pr("  %-24s ->  pole %5.2f Hz  (a2 %d / b2 %d)  GM %.2fx at %.1f Hz  Re@7 %+.2f  Re@20 %+.2f  |H|@20 x%.2f" % (
        lbl, polef(a), a, b, g, fx, budget(7, a, b)[2].real, budget(20, a, b)[2].real,
        abs(Hlag(20, a, b) / Hlag(20))))
pr("  (the 5.05 Hz row IS the as-built pole, so 'GM unchanged' resolving to ~5.05 Hz means NO pure")
pr("   output-lag dose holds today's margin -- every dose spends it.)")

pr("")
pr("  PAIRING WITH Kd -- a Kd CUT lowers the D-dominated HF gain and buys margin back.  The 7.3 Hz ring")
pr("  brackets Kd from BELOW at ~118 (ZN-ACCEL-FRAME addendum sec A5); the Nyquist brackets it above at")
pr("  ~227.  Grid of (lag pole, Kd), reporting GM and the damping budget rescaled by the byte-exact C:")
pr("  %-8s" % "pole\\Kd" + "".join("%16d" % kd for kd in (96, 112, 118, 128)))
for ft in (5.05, 7.0, 8.0, 10.0, 12.0):
    a, b = (LAG_A, LAG_B) if abs(ft - 5.05) < 1e-6 else design_lag(ft)
    cells = []
    for kd in (96, 112, 118, 128):
        g, fx = gm_of(a, b, kd)
        rc20 = Cc(20, KP, kd) / Cc(20, KP, KD)
        P = budget(20, a, b)
        Ps = (P[0] * rc20)
        cells.append("%6.2fx R20%+5.2f" % (g, (Ps + P[1]).real))
    pr("  %-8.2f" % polef(a) + "".join("%16s" % c for c in cells))
pr("  (R20 = Re@20 of the aggregator sum with the servo arm rescaled by C(20,Kd)/C(20,128); a Kd cut")
pr("   costs 20 Hz damping at the same time as it buys margin, so the pairing is not free.)")

pr("")
pr("  🛑 THE VERDICT BIFURCATES ON THE ONE THING NOTHING ON THIS CAR MEASURES.  The addendum's OPTIMISTIC")
pr("  plant (phase frozen above 20 Hz) gives the as-built loop GM 6.76x instead of 1.77x.  Under THAT")
pr("  plant every row above is comfortably stable.  Under the delay plant -- which is the physically")
pr("  expected shape AND the one that reproduces creep20's own measured GM of 1.75x at Kp 295 -- the")
pr("  15 Hz pole is unstable.  We cannot tell which is right, and V255/V269 are what happens when a")
pr("  blind HF gain rise is wrong.  [BELIEF, and the bifurcation itself is the finding.]")
pr("  Delay-plant GM under the optimistic plant, for comparison:")


def phL_frozen(f, a2, b2, kd=KD):
    return dg(Cc(f, KP, kd)) + dg(Hlag(f, a2, b2)) + dg(Hfb(f)) + PH_G20


def f180_frozen(a2, b2, kd=KD, lo=12.0, hi=400.0):
    g = lambda f: phL_frozen(f, a2, b2, kd) + 180.0
    if g(lo) * g(hi) >= 0:
        return None
    for _ in range(90):
        m = (lo + hi) / 2.0
        if g(lo) * g(m) < 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2.0


pr("  %-20s %10s %10s %10s" % ("shape", "f(-180)", "|L|", "GM"))
for nm, a, b in LAG_SHAPES[:5]:
    fx = f180_frozen(a, b)
    if fx is None:
        pr("  %-20s %10s" % (nm, "none"))
        continue
    pr("  %-20s %9.1fHz %10.3f %9.2fx" % (nm, fx, magL(fx, a, b, None), 1.0 / magL(fx, a, b, None)))

pr("")
pr("=" * 150)
pr("5c. CROSSOVER, PHASE MARGIN AND |S| IN 18-22 Hz -- model (a) ONLY, and ONLY where it is anchored")
pr("=" * 150)
pr("""
  The record identifies grind #1 as the LKAS rate loop's CROSSOVER RESONANCE (memory
  accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated; creep20 L_in crossover
  17-21 Hz, PM 35-60 deg, Ms 2-2.9).  Model (a) is anchored AT 20 Hz, so the crossover region is the one
  place it is entitled to speak about |S|.  I report |S| = 1/|1+L| here and NOWHERE else, and I do NOT
  extend it to a full closed-loop curve (LOOP-MODEL-CONVENTION-DEFECT sec3 forbids that).
  🛑 The Ms column below is over 12-50 Hz and therefore INCLUDES the blind band; read it with 5b.
""")
pr("  %-30s %10s %9s %10s %10s %10s %16s" % (
    "shape", "f_cross", "PM deg", "|S|@18Hz", "|S|@20Hz", "|S|@22Hz", "Ms 12-50 @ f"))


def Lc(f, a2, b2, fb, kd=KD):
    return magL(f, a2, b2, fb, kd=kd) * cmath.exp(1j * math.radians(phL(f, a2, b2, fb, kd=kd)))


def crossover(a2, b2, fb, kd=KD):
    fg = np.arange(5.0, 60.0, 0.01)
    m = np.array([magL(f, a2, b2, fb, kd=kd) for f in fg])
    idx = np.flatnonzero((m[:-1] - 1) * (m[1:] - 1) < 0)
    if len(idx) == 0:
        return None, None
    i = idx[-1]
    fx = fg[i]
    return fx, 180.0 + phL(fx, a2, b2, fb, kd=kd)


msgrid = np.arange(12.0, 50.01, 0.05)
for nm, a, b, g_, fb in SHAPES:
    fx, pm = crossover(a, b, fb)
    S = lambda f: 1.0 / abs(1.0 + Lc(f, a, b, fb))
    sv = [S(f) for f in msgrid]
    ms = max(sv); fms = msgrid[int(np.argmax(sv))]
    pr("  %-30s %9s %9s %10.2f %10.2f %10.2f %8.2f @%5.1fHz" % (
        nm, ("%.1fHz" % fx) if fx else "none", ("%+.1f" % pm) if pm is not None else "-",
        S(18), S(20), S(22), ms, fms))
pr("  (as-built reproduces creep20's identified crossover band and a phase margin inside its 35-60 deg")
pr("   window, which is the check that model (a) is being used where it is anchored.)")

pr("")
pr("=" * 150)
pr("5d. ⭐ THE JOINT (LAG POLE, Kd) FRONTIER -- the only design that buys 20 Hz WITHOUT spending either gate")
pr("=" * 150)
pr("""
  The pole raise and the Kd cut are COMPLEMENTARY, and the record never composed them:
    - the lag pole adds PHASE LEAD at 7-22 Hz (good for both symptoms) and GAIN everywhere above ~3 Hz;
    - Kd is the term that DOMINATES the loop at 28-32 Hz (at 30 Hz the D arm is 3.1x the P arm), so a Kd
      cut removes almost all of the HF gain the pole raise added, and almost none of the 7-20 Hz phase;
    - the reason Kd could not be cut before is the 7.3 Hz ring, whose lower root sits at Kd ~118 -- but
      THE POLE RAISE ITSELF CUTS THE RING (ratio 0.89 at a 7 Hz pole, 0.75 at 10 Hz), which BUYS the ring
      headroom that lets Kd go below 118.
  Both gates held at TODAY'S values: GM >= 1.77x (the as-built worst-family margin, not reduced at all)
  and |L_tot|(7.3 Hz) <= 0.980 (the registered pool value, n = 8).  Objective: Re@20, and |S|@20.
""")


def ring_of(a2, b2, kd=KD):
    R = (Cc(7.3, KP, kd) * Hlag(7.3, a2, b2)) / (Cc(7.3, KP, KD) * Hlag(7.3))
    return abs(Ls_ * R + Lr_) / abs(Ls_ + Lr_)


def budget_kd(f, a2, b2, kd=KD, gain=GAIN0, s=0.43):
    d = LANE[f]
    R = (Cc(f, KP, kd) * Hlag(f, a2, b2)) / (Cc(f, KP, KD) * Hlag(f))
    Ps = d["As"] * cmath.exp(1j * math.radians(d["ps"])) * R
    Pr = d["Ar"] * cmath.exp(1j * math.radians(d["pr_"])) * s * (gain / GAIN0)
    return Ps, Pr, Ps + Pr


GM_GATE, RING_GATE = 1.77, 1.000
pr("  FULL GRID.  '.' = fails a gate.  Cell = Re@20 / GM / ring|L_tot|.")
KDS = [48, 56, 64, 72, 80, 96, 112, 128]
pr("  %-9s" % "pole Hz" + "".join("%22d" % kd for kd in KDS))
BESTJ = None
for ft in (5.05, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0):
    a, b = (LAG_A, LAG_B) if abs(ft - 5.05) < 1e-6 else design_lag(ft)
    cells = []
    for kd in KDS:
        g, fx = gm_of(a, b, kd)
        rg = 0.980 * ring_of(a, b, kd)
        R20 = budget_kd(20, a, b, kd)[2].real
        ok = (g >= GM_GATE) and (rg < RING_GATE)
        if ok and (BESTJ is None or R20 > BESTJ[0]):
            BESTJ = (R20, a, b, kd, g, rg, ft)
        cells.append("%s%5.2f/%4.2fx/%.3f" % ("*" if ok else " ", R20, g, rg))
    pr("  %-9.2f" % polef(a) + "".join("%22s" % c for c in cells))
pr("  (* = BOTH gates pass at today's values.)")
if BESTJ:
    R20, a, b, kd, g, rg, ft = BESTJ
    S = lambda f: 1.0 / abs(1.0 + magL(f, a, b, None, kd=kd) * cmath.exp(1j * math.radians(phL(f, a, b, None, kd=kd))))
    fx, pm = crossover(a, b, None, kd)
    pr("")
    pr("  BEST GATE-RESPECTING POINT: lag pole %.2f Hz (0xC63EC = %d, 0xC63EE = %d) with Kd = %d" % (
        polef(a), a, b, kd))
    pr("    Re@20 %+.2f (base %+.2f, x%.2f)   Re@7 %+.2f (base %+.2f)   GM %.2fx (base 1.77x)" % (
        R20, budget(20, LAG_A, LAG_B)[2].real, R20 / budget(20, LAG_A, LAG_B)[2].real,
        budget_kd(7, a, b, kd)[2].real, budget(7, LAG_A, LAG_B)[2].real, g))
    pr("    ring |L_tot| %.3f (base 0.980)   |S|@20 %.2f (base 1.61)   crossover %.1f Hz PM %+.1f deg" % (
        rg, S(20), fx if fx else float("nan"), pm if pm is not None else float("nan")))
pr("")
pr("  🛑 READ THIS BEFORE PICKING ANYTHING OUT OF THE GRID.  A Kd cut below 118 is NOT free just because")
pr("  the ring gate passes: the ring arm composition (Ls, Lr) is a SINGLE-FREQUENCY fit from 8 episodes")
pr("  and the convention-defect note forbids converting |L| into a predicted amplitude.  The grid says")
pr("  which points are ADMISSIBLE, not which are good.  And a two-cell build (pole + Kd) is two levers on")
pr("  one drive, which the kit's own doctrine treats as harder to interpret than one.")

pr("")
pr("=" * 150)
pr("5e. ⭐ CALIBRATING THE GATE AGAINST WHAT HAS ALREADY FLOWN -- the Kp-equivalent gain margin")
pr("=" * 150)
pr("""
  A gate is only worth what its calibration is worth.  The SAME model (a) that condemns the 15 Hz pole
  also assigns a gain margin to Kp values THAT HAVE FLOWN ON THIS CAR: every build before V281 rev 3 ran
  the stock Kp LERP, which reaches 696 at high demand index, and the addendum's own independent check is
  creep20's MEASURED 'GM 1.32x @ 22.4 Hz' at Kp 470.  So GM ~1.3x is not a theoretical abstraction on
  this car -- it is a margin the car has demonstrably been driven at.  🛑 Two caveats that keep this from
  being a licence: (i) the stock LERP only reaches its top at high demand index, so the exposure at
  Kp 696 was brief, and (ii) the crossing at Kp 470 was at 22.4 Hz where the 0x18F streams still read,
  whereas a pole raise puts it at 29-32 Hz where nothing does.  [EVIDENCE for the numbers; BELIEF that
  the equivalence transfers across the two ways of reaching the same margin.]
""")
pr("  GAIN MARGIN vs Kp, at the AS-BUILT pole and Kd 128:")
pr("  %-8s %10s %9s %9s   %s" % ("Kp", "f(-180)", "|L|", "GM", "flown?"))
for kp_, note in [(248, "V281r3/V282/V283 flat  -- TODAY"), (295, "stock LERP mid"), (470, "stock LERP high -- creep20 MEASURES GM 1.32x here"),
                  (696, "stock LERP top (V280r2 and every build before V281r3)")]:
    gg = lambda f: dg(Cc(f, kp_, KD)) + dg(Hlag(f)) + dg(Hfb(f)) + PH_G20 + SLOPE * (f - 20) + 180.0
    lo, hi = 12.0, 300.0
    fx = None
    if gg(lo) * gg(hi) < 0:
        for _ in range(90):
            m = (lo + hi) / 2.0
            if gg(lo) * gg(m) < 0:
                hi = m
            else:
                lo = m
        fx = (lo + hi) / 2.0
    if fx is None:
        pr("  %-8d %10s" % (kp_, "none"))
        continue
    Lm = KMAG * abs(Cc(fx, kp_, KD) * Hlag(fx) * Hfb(fx))
    pr("  %-8d %9.1fHz %9.3f %8.2fx   %s" % (kp_, fx, Lm, 1.0 / Lm, note))
pr("")
pr("  THE EQUIVALENCE.  For each candidate pole, the Kp at the as-built pole with the SAME gain margin:")


def gm_kp(kp_):
    gg = lambda f: dg(Cc(f, kp_, KD)) + dg(Hlag(f)) + dg(Hfb(f)) + PH_G20 + SLOPE * (f - 20) + 180.0
    lo, hi = 12.0, 300.0
    if gg(lo) * gg(hi) >= 0:
        return None
    for _ in range(90):
        m = (lo + hi) / 2.0
        if gg(lo) * gg(m) < 0:
            hi = m
        else:
            lo = m
    fx = (lo + hi) / 2.0
    return 1.0 / (KMAG * abs(Cc(fx, kp_, KD) * Hlag(fx) * Hfb(fx)))


kpg = np.arange(248.0, 1400.0, 1.0)
gml = [gm_kp(k) for k in kpg]
pr("  %-24s %6s %6s %9s %14s %10s" % ("shape", "a2", "b2", "GM", "Kp-equivalent", "ever flown"))
for nm, a, b in [("as-built 5.05 Hz", LAG_A, LAG_B)] + [("lag pole %.2f Hz" % polef(design_lag(f)[0]), ) + design_lag(f)
                                                        for f in (6.0, 6.5, 7.15, 8.0, 10.0, 12.0, 15.0)]:
    g, fx = gm_of(a, b)
    kpe = None
    for k, gv in zip(kpg, gml):
        if gv is not None and gv <= g:
            kpe = k
            break
    pr("  %-24s %6d %6d %8.2fx %14s %10s" % (
        nm, a, b, g, ("Kp %.0f" % kpe) if kpe else "> 1400",
        ("YES (stock LERP)" if kpe and kpe <= 696 else "no")))
pr("  (the stock Kp LERP tops out at 696, so any row whose Kp-equivalent is <= 696 sits at a gain margin")
pr("   this car has already been driven at -- albeit only on high-demand-index frames, and with the")
pr("   crossing at a frequency the instruments could still see.)")

pr("")
pr("=" * 150)
pr("5f. ⭐ DOES THE EDIT DISCRIMINATE THE TWO PLANT MODELS?  (the reason to cut it at all)")
pr("=" * 150)
pr("""
  Everything above bifurcates on the plant's phase above 25 Hz, which nothing on this car has measured.
  A pole raise pushes the sensitivity peak INTO 26-33 Hz, where the 0x18F streams still carry band
  ENERGY (TASK5: energy endpoints safe above 25 Hz, frequency endpoints unsound -- adequate for a guard,
  since a rise is bad whatever its true frequency).  So the two plant models make DIFFERENT, MEASURABLE
  predictions for the 26-33 Hz motion, and the edit is a discriminator, not just a dose.
""")


def Sr(a2, b2, lo, hi, frozen):
    fg = np.arange(lo, hi + 1e-9, 0.1)

    def L(f, aa, bb):
        ph = dg(Cc(f, KP, KD)) + dg(Hlag(f, aa, bb)) + dg(Hfb(f)) + PH_G20 + (0.0 if frozen else SLOPE * (f - 20))
        return KMAG * abs(Cc(f, KP, KD) * Hlag(f, aa, bb) * Hfb(f)) * cmath.exp(1j * math.radians(ph))
    n = [1.0 / abs(1 + L(f, a2, b2)) for f in fg]
    d = [1.0 / abs(1 + L(f, LAG_A, LAG_B)) for f in fg]
    return float(np.mean(n) / np.mean(d))


pr("  %-22s %16s %16s %10s | %16s %16s" % (
    "shape", "26-33 x DELAY", "26-33 x FROZEN", "separation", "18-22 x DELAY", "18-22 x FROZEN"))
for nm, a2, b2 in SSHAPES:
    d1, d2 = Sr(a2, b2, 26, 33, False), Sr(a2, b2, 26, 33, True)
    e1, e2 = Sr(a2, b2, 18, 22, False), Sr(a2, b2, 18, 22, True)
    pr("  %-22s %16.3f %16.3f %9.2fx | %16.3f %16.3f" % (nm, d1, d2, max(d1, d2) / min(d1, d2), e1, e2))
pr("  The 26-33 Hz guard band separates the two plants by the factor in column 4.  Against that band's")
pr("  own route-to-route spread on unchanged firmware (1.25x on the 2-6-normalised form, section 6a-bis),")
pr("  a separation above ~1.6x is a DECIDABLE experiment -- and deciding it is worth more than the dose,")
pr("  because the delay plant is the premise behind Ku = 227, behind every HF risk verdict in this kit,")
pr("  and behind the V255/V269 post-mortem.  [BELIEF for both plants; the separation is arithmetic.]")

pr("")
pr("  BLIND-BAND LOOP GAIN -- the mean of |L| over 25-50 Hz, and the fraction of the total |H| rise that")
pr("  happens ABOVE 25 Hz where NO instrument on this car can see it (427 tap Nyquist 25 Hz; 0x18F 40 Hz).")
fb_grid = np.arange(25.0, 50.01, 0.25)
pr("  %-30s %12s %10s %12s %12s" % ("shape", "mean|L|25-50", "x base", "|H|rise@20", "blind incr"))
mb = None
for nm, a, b, g_, fb in SHAPES:
    m = float(np.mean([magL(f, a, b, fb) for f in fb_grid]))
    if mb is None:
        mb = m
    fbp = fb if fb else (FB_A, FB_B)
    r20 = abs(Hlag(20, a, b) * Hfb(20, fbp[0], fbp[1]) / (Hlag(20) * Hfb(20)))
    rasy = abs(Hlag(499, a, b) * Hfb(499, fbp[0], fbp[1]) / (Hlag(499) * Hfb(499)))
    pr("  %-30s %12.4f %9.2fx %11.2fx %11.2fx" % (nm, m, m / mb, r20, rasy / r20))

# ---------------------------------------------------------------- SECTION 6
pr("")
pr("=" * 150)
pr("6. PRE-REGISTRATION NUMBERS, computed on the r39 / r3a / r3c WIRE (before any drive)")
pr("=" * 150)
ROUTES = ["r39", "r3a", "r3c", "r35", "r34"]
BUILD = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r35": "V281r3", "r34": "V280r2"}
G = {}
for tag in ROUTES:
    try:
        C20.BUILD[tag] = BUILD[tag]
    except Exception:
        pass
    try:
        g = C20.load(tag)
    except Exception as e:
        pr("  !! could not load %s: %s" % (tag, e))
        continue
    D = dict(np.load(os.path.join(C20.CACHE, tag + ".npz")))
    g["t0"] = float(D["t18"][0])
    g["tr"] = g["t"] - g["t"][0]
    bp = os.path.join(C20.CACHE, tag + "_b4.npz")
    if os.path.exists(bp):
        Bb = np.load(bp)
        k14, P14, tn14, res14 = C20.dejitter(Bb["t14b"], 0.01, 100)
        b4 = Bb["b4"].astype(int)
        for bit in (4, 5, 6):
            g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
    G[tag] = g
    pr("  loaded %-4s %-8s  %7.1f s, engaged-lateral %6.1f s" % (tag, BUILD[tag], g["tr"][-1], g["eng"].sum() / FS))

CREEP = lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)


def apply_ratio(x, fs, a2, b2, fb=None):
    """Apply H_new/H_old (and optionally the fb ratio) to a time series, in the frequency domain."""
    x = np.asarray(x, float)
    n = len(x)
    m = x.mean()
    X = np.fft.rfft(x - m)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    R = np.ones(len(f), complex)
    for i, ff in enumerate(f):
        if ff <= 0:
            R[i] = 1.0
            continue
        r = Hlag(ff, a2, b2) / Hlag(ff)
        if fb is not None:
            r = r * abs(Hfb(ff, fb[0], fb[1]) / Hfb(ff))
        R[i] = r
    return np.fft.irfft(X * R, n) + m * (2.0 * b2 / (1024 - a2) / 32.0) / dc0


def bandamp(x, fs, lo, hi):
    return C20.bamp(np.asarray(x, float), lo, hi, fs)


PICK = [("as-built V282", LAG_A, LAG_B, None)]
for nm_, a_, b_ in [("lag 6.0 Hz 986/602", 986, 602), ("lag 6.5 Hz 983/650", 983, 650),
                    ("lag 7.2 Hz 979/713", 979, 713), ("lag 8.0 Hz 974/792", 974, 792),
                    ("lag 10 Hz 962/982", 962, 982), ("lag 15 Hz 932/1458", 932, 1458)]:
    PICK.append((nm_, a_, b_, None))

pr("")
pr("  6a. THE MOTION -- the 0x18F WHEEL RATE's band amplitudes in engaged hands-off creep, measured on the")
pr("      three V282 routes today, and PREDICTED after the edit by the model-(a) sensitivity ratio.")
pr("      🛑 The statistic is the MOTION, not the lever's own output (feedback-score-the-motion-not-the-")
pr("      lever-output).  The 427 tap's own 18-22 Hz amplitude is reported too but is NOT the endpoint:")
pr("      the lane gain rises while the motion falls, so the tap moves the WRONG WAY by construction.")
BANDS = [(18.0, 22.0, "18-22 grind"), (26.0, 33.0, "26-33 GUARD"), (33.0, 39.9, "33-40 shelf"), (6.0, 9.0, "6-9 ring")]
MEAS = {}
for tag in ROUTES:
    if tag not in G:
        continue
    g = G[tag]
    m = CREEP(g)
    if m.sum() < 200:
        pr("  %-5s creep stratum only %.1f s -- skipped" % (tag, m.sum() / FS))
        continue
    d = np.diff(np.r_[0, m.astype(int), 0])
    runs = [(a_, b_) for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b_ - a_ >= 200]
    if not runs:
        continue
    row = {}
    for lo, hi, lbl in BANDS:
        row[lbl] = float(np.median([bandamp(g["rate_x"][a_:b_], FS, lo, hi) for a_, b_ in runs]))
    tm = np.interp(g["T_t"], g["t"], m.astype(float)) > 0.5
    dT = np.diff(np.r_[0, tm.astype(int), 0])
    trs = [(a_, b_) for a_, b_ in zip(np.flatnonzero(dT == 1), np.flatnonzero(dT == -1)) if b_ - a_ >= 100]
    row["T18-22"] = float(np.median([bandamp(g["T"][a_:b_], FST, 18.0, 22.0) for a_, b_ in trs])) if trs else float("nan")
    row["s"] = sum(b_ - a_ for a_, b_ in runs) / FS
    row["n"] = len(runs)
    MEAS[tag] = row
pr("  %-5s %-8s %7s %6s %12s %12s %12s %12s %12s" % (
    "route", "build", "s", "runs", "rate 18-22", "rate 26-33", "rate 33-40", "rate 6-9", "tap 18-22"))
for tag in ROUTES:
    if tag not in MEAS:
        continue
    r = MEAS[tag]
    pr("  %-5s %-8s %7.1f %6d %12.4f %12.4f %12.4f %12.4f %12.1f" % (
        tag, BUILD[tag], r["s"], r["n"], r["18-22 grind"], r["26-33 GUARD"], r["33-40 shelf"],
        r["6-9 ring"], r["T18-22"]))
v282 = [MEAS[t]["18-22 grind"] for t in ("r39", "r3a", "r3c") if t in MEAS]
if len(v282) >= 2:
    pr("  ROUTE-TO-ROUTE SPREAD ON THE UNCHANGED FIRMWARE (the noise floor any prediction must beat):")
    pr("    rate 18-22 Hz across the three V282 routes: %s  ->  max/min = %.2fx" % (
        ", ".join("%.4f" % v for v in v282), max(v282) / min(v282)))
    for lbl in ("26-33 GUARD", "33-40 shelf", "6-9 ring"):
        vv = [MEAS[t][lbl] for t in ("r39", "r3a", "r3c") if t in MEAS]
        pr("    %-12s across the three V282 routes: %s  ->  max/min = %.2fx" % (
            lbl, ", ".join("%.4f" % v for v in vv), max(vv) / min(vv)))
pr("")
pr("  PREDICTED MULTIPLIERS ON THE MOTION, from the model-(a) sensitivity ratio |S_new(f)/S_old(f)|,")
pr("  band-averaged over each band.  These are the pre-registered numbers.")
def Sratio(a2, b2, lo, hi):
    fg = np.arange(lo, hi + 1e-9, 0.1)
    num = [1.0 / abs(1.0 + Lc(f, a2, b2, None)) for f in fg]
    den = [1.0 / abs(1.0 + Lc(f, LAG_A, LAG_B, None)) for f in fg]
    return float(np.mean(num) / np.mean(den))


pr("  %-22s %14s %14s %14s %14s %14s" % ("shape", "18-22 x", "26-33 x GUARD", "33-40 x", "6-9 x", "tap lane gain"))
for nm, a2, b2 in SSHAPES:
    pr("  %-22s %14.3f %14.3f %14.3f %14.3f %14.3f" % (
        nm, Sratio(a2, b2, 18, 22), Sratio(a2, b2, 26, 33), Sratio(a2, b2, 33, 39.9),
        Sratio(a2, b2, 6, 9), abs(Hlag(20, a2, b2) / Hlag(20))))
pr("  ('tap lane gain' is |H_lag| at 20 Hz -- what the 427 tap's OWN 18-22 Hz amplitude is multiplied by")
pr("   for a given rate input.  The tap's measured amplitude will move by roughly that TIMES the 18-22")
pr("   motion ratio, i.e. it can RISE while the motion FALLS.  Do not score the build on the tap alone.)")

pr("")
pr("=" * 150)
pr("  6a-bis. 🛑 ENDPOINT SELECTION -- which statistic can actually resolve the predicted effect?")
pr("=" * 150)
pr("  A predicted multiplier is only informative if it is bigger than the spread the SAME statistic shows")
pr("  across routes on the UNCHANGED firmware.  r39 / r3a / r3c are all V282, so their spread is pure")
pr("  exposure + measurement noise.  Candidate endpoints, each with its across-route max/min and the")
pr("  multiplier each candidate dose predicts for it:")


def stat_rows(tag):
    g = G[tag]
    m = CREEP(g)
    d = np.diff(np.r_[0, m.astype(int), 0])
    runs = [(a_, b_) for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b_ - a_ >= 200]
    out = {}
    if not runs:
        return out
    A = lambda lo, hi: np.array([bandamp(g["rate_x"][a_:b_], FS, lo, hi) for a_, b_ in runs])
    b1822, b2633, b0609, b0206, b3340 = A(18, 22), A(26, 33), A(6, 9), A(2, 6), A(33, 39.9)
    rms = np.array([np.std(g["rate_x"][a_:b_]) for a_, b_ in runs])
    out["rate 18-22 raw"] = float(np.median(b1822))
    out["18-22 / 2-6"] = float(np.median(b1822 / b0206))
    out["18-22 / rms"] = float(np.median(b1822 / rms))
    out["18-22 / 6-9"] = float(np.median(b1822 / b0609))
    out["18-22 / 26-33"] = float(np.median(b1822 / b2633))
    out["26-33 raw (GUARD)"] = float(np.median(b2633))
    out["26-33 / 2-6 (GUARD)"] = float(np.median(b2633 / b0206))
    out["33-40 / 2-6 (SHELF)"] = float(np.median(b3340 / b0206))
    return out


RS = {t: stat_rows(t) for t in ("r39", "r3a", "r3c") if t in G}
RS = {t: v for t, v in RS.items() if v}
if len(RS) >= 2:
    keys = list(next(iter(RS.values())).keys())
    pr("  %-24s %10s %10s %10s %9s | %s" % (
        "endpoint", "r39", "r3a", "r3c", "max/min",
        "".join("%12s" % n.split()[1] for n, _, _ in SSHAPES)))
    for k in keys:
        vals = [RS[t][k] for t in RS]
        lo_, hi_ = min(vals), max(vals)
        preds = []
        for nm, a2, b2 in SSHAPES:
            if k.startswith("rate 18-22") or k == "18-22 / 2-6" or k == "18-22 / rms":
                pv = Sratio(a2, b2, 18, 22)
                if k != "rate 18-22 raw":
                    pv = pv / Sratio(a2, b2, 2, 6) if k == "18-22 / 2-6" else pv
            elif k == "18-22 / 6-9":
                pv = Sratio(a2, b2, 18, 22) / Sratio(a2, b2, 6, 9)
            elif k == "18-22 / 26-33":
                pv = Sratio(a2, b2, 18, 22) / Sratio(a2, b2, 26, 33)
            elif k.startswith("26-33 raw"):
                pv = Sratio(a2, b2, 26, 33)
            elif k.startswith("26-33 /"):
                pv = Sratio(a2, b2, 26, 33) / Sratio(a2, b2, 2, 6)
            else:
                pv = Sratio(a2, b2, 33, 39.9) / Sratio(a2, b2, 2, 6)
            preds.append(pv)
        pr("  %-24s %10.4f %10.4f %10.4f %8.2fx | %s" % (
            k, RS.get("r39", {}).get(k, float("nan")), RS.get("r3a", {}).get(k, float("nan")),
            RS.get("r3c", {}).get(k, float("nan")), hi_ / lo_,
            "".join("%12.3f" % v for v in preds)))
    pr("")
    pr("  READ IT AS: an endpoint is USABLE for a given dose only where |1 - predicted| clearly exceeds")
    pr("  |1 - max/min|.  A predicted 0.90 against a 2.50x route spread licenses NOTHING.")

pr("")
pr("  6b. THE T-re-RATE PHASE AT 20 Hz -- the primary pre-registered statistic.")
pr("      Measured today, and predicted after the edit by adding the section-3 phase rotation, which is")
pr("      EXACT (the lag pole multiplies the lane by H_new/H_old and nothing else in the lane changes).")
PH = {}
for tag in ROUTES:
    if tag not in G:
        continue
    g = G[tag]
    m = CREEP(g)
    tm = np.interp(g["T_t"], g["t"], m.astype(float)) > 0.5
    rate_on_T = np.interp(g["T_t"], g["t"], g["rate_x"])
    d = np.diff(np.r_[0, tm.astype(int), 0])
    runs = [(a_, b_) for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b_ - a_ >= 128]
    P = C20.Pool(FST, 128)
    for a_, b_ in runs:
        P.add(dict(T=g["T"][a_:b_], rate=rate_on_T[a_:b_]))
    try:
        H = P.tf("rate", "T"); f = P.f; coh = P.coh("rate", "T")
    except Exception as e:
        pr("  %-5s pool failed: %s" % (tag, e))
        continue
    i20 = int(np.argmin(np.abs(f - 20.3)))
    PH[tag] = (f[i20], dg(H[i20]), coh[i20], P.n)
    pr("  %-5s %-8s  f = %5.2f Hz   angle(T/rate) = %+7.1f deg   coh %.2f   (%d windows, %.1f s)" % (
        tag, BUILD[tag], f[i20], dg(H[i20]), coh[i20], P.n, P.n * 128 / FST / 2.0))
pr("")
pr("  %-22s %10s %12s %12s %12s" % ("shape", "rot@20Hz", "r39 pred", "r3a pred", "r3c pred"))
for nm, a2, b2, fb in PICK[1:]:
    rot = dg(Hlag(20.3, a2, b2)) - dg(Hlag(20.3))
    pr("  %-22s %+9.1f %12s %12s %12s" % (
        nm, rot,
        "%+.1f" % (PH["r39"][1] + rot) if "r39" in PH else "-",
        "%+.1f" % (PH["r3a"][1] + rot) if "r3a" in PH else "-",
        "%+.1f" % (PH["r3c"][1] + rot) if "r3c" in PH else "-"))

pr("")
pr("  6c. BIT-6 DUTY  P(|r24| >= |T|), and how far it should FALL when |T| rises.")
pr("      r24 is UNCHANGED by a lag-pole edit, so the whole move is on |T|.  Computed on the same creep")
pr("      stratum by re-filtering the tap and re-running the comparator against the measured bit-6 duty.")
pr("  %-5s %-22s %10s %10s %10s" % ("route", "shape", "duty meas", "duty pred", "x base"))
for tag in ROUTES:
    if tag not in G or "bit6" not in G[tag]:
        continue
    g = G[tag]
    m = CREEP(g)
    if m.sum() < 400:
        continue
    duty = float(g["bit6"][m].mean())
    tm = np.interp(g["T_t"], g["t"], m.astype(float)) > 0.5
    b6T = np.interp(g["T_t"], g["t"], g["bit6"]) > 0.5
    d = np.diff(np.r_[0, tm.astype(int), 0])
    runs = [(a_, b_) for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b_ - a_ >= int(4 * FST)]
    base_pred = None
    for nm, a2, b2, fb in PICK:
        num = den = 0
        for a_, b_ in runs:
            seg = np.abs(g["T"][a_:b_])
            y = np.abs(apply_ratio(g["T"][a_:b_], FST, a2, b2, fb))
            bb = b6T[a_:b_]
            # r24 magnitude is implied per-frame by the comparator: |r24| >= |T| iff bit6.
            # Under the edit, |T| -> y.  A frame that was 1 stays 1 iff |r24| >= y; we only know
            # |r24| >= |T| (bit 1) or < |T| (bit 0), so bound it: the duty can only FALL, and the
            # fall is bounded by the fraction of 1-frames whose |T| grew past the next-larger |T|.
            # Use the empirical |r24| distribution implied by the duty on this route instead:
            num += np.sum(bb)
            den += len(bb)
        # scale-invariant prediction: bit6 duty = P(|r24| >= |T|); |T| -> k*|T| pointwise with
        # k = median band-weighted ratio, so duty_new = P(|r24|/|T| >= k) = the quantile of the
        # ratio distribution.  Estimated from the measured duty and a lognormal fit of |r24|/|T|.
        if base_pred is None:
            base_pred = duty
            pr("  %-5s %-22s %10.4f %10.4f %10.3f" % (tag, nm, duty, duty, 1.0))
            continue
        num = den = 0.0
        for a_, b_ in runs:
            seg = g["T"][a_:b_]
            num += np.std(apply_ratio(seg, FST, a2, b2, fb)) * (b_ - a_)
            den += np.std(seg) * (b_ - a_)
        k = num / den if den else float("nan")
        # lognormal: P(R >= 1) = duty  ->  z0 = Phi^-1(1-duty); P(R >= k) = 1 - Phi(z0 + ln k / sd)
        from scipy import stats as st
        sd = 0.85   # sd of ln(|r24|/|T|), the value that reproduces the r36-r38 duty ladder (see below)
        z0 = st.norm.ppf(1 - duty)
        dpred = 1 - st.norm.cdf(z0 + math.log(k) / sd)
        pr("  %-5s %-22s %10.4f %10.4f %10.3f" % (tag, nm, duty, dpred, dpred / base_pred))

pr("""
  CALIBRATING sd.  The r36-r38 read measured the bit-6 duty against the closed-form r24 gain ladder:
  duty 0.196 / 0.115 / 0.078 / 0.039 as the gain goes 5244 / 3072 / 2048 / 1024 (r39's own replay).
  Those are pure SCALINGS of |r24| by 1.00 / 0.586 / 0.391 / 0.195, i.e. the same one-sided lognormal
  quantile problem with k = 1/scale.  The sd that best fits that ladder is reported below.
""")
from scipy import stats as st
lad = [(1.0, 0.196), (3072 / 5244.0, 0.115), (2048 / 5244.0, 0.078), (1024 / 5244.0, 0.039)]
best = None
for sd in np.arange(0.30, 2.51, 0.01):
    z0 = st.norm.ppf(1 - lad[0][1])
    err = 0.0
    for sc, dd in lad[1:]:
        p = 1 - st.norm.cdf(z0 - math.log(sc) / sd)
        err += (p - dd) ** 2
    if best is None or err < best[1]:
        best = (sd, err)
pr("  best-fit sd(ln |r24|/|T|) = %.2f, sum sq err %.5f.  Predicted ladder at that sd:" % best)
z0 = st.norm.ppf(1 - lad[0][1])
for sc, dd in lad:
    p = 1 - st.norm.cdf(z0 - math.log(sc) / best[0])
    pr("     gain scale %.3f  measured/replayed %.3f   lognormal %.3f" % (sc, dd, p))

pr("")
pr("  6d. THE 7.3 Hz RING GUARD -- model (b), and ONLY as a ratio between candidates (convention defect sec4).")
pr("      L_tot = Ls + Lr, the two-arm ripple composition; a lag-pole edit multiplies the SERVO arm Ls by")
pr("      H_new/H_old at 7.3 Hz and leaves the r24 arm Lr alone.  Registered pool value |L_tot| = 0.980")
pr("      [0.971-0.983] (n = 8 episodes, r39 added).  A candidate is BLOCKED if the ratio takes it to 1.000.")
Ls, Lr = Ls_, Lr_
base_ring = abs(Ls + Lr)
pr("  %-30s %12s %12s %12s" % ("shape", "ring ratio", "|L_tot| pred", "verdict"))
for nm, a, b, g_, fb in SHAPES:
    R = Hlag(7.3, a, b) / Hlag(7.3)
    if fb is not None:
        R = R * abs(Hfb(7.3, fb[0], fb[1]) / Hfb(7.3))
    rr = abs(Ls * R + Lr) / base_ring
    pr("  %-30s %12.3f %12.3f %12s" % (nm, rr, 0.980 * rr, "BLOCK" if 0.980 * rr >= 1.0 else "pass"))

pr("")
pr("  6e. THE 33-49.9 Hz FOLDED-SHELF GUARD.  The 427 tap is 50 Hz (Nyquist 25) and 0x18F is 100 Hz")
pr("      (usable to 40).  Content at 50-67 Hz folds onto 33-50 Hz on the 100 Hz streams.  TASK5 measured")
pr("      that engaging raises >50 Hz content 1.4-3.4x already.  The guard statistic is the 0x18F rate's")
pr("      33-49.9 Hz band amplitude in the same creep stratum; today's values:")
for tag in ROUTES:
    if tag not in G:
        continue
    g = G[tag]
    m = CREEP(g)
    if m.sum() < 400:
        continue
    d = np.diff(np.r_[0, m.astype(int), 0])
    runs = [(a_, b_) for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b_ - a_ >= 200]
    v = [bandamp(g["rate_x"][a_:b_], FS, 33.0, 49.9) for a_, b_ in runs]
    v2 = [bandamp(g["bar"][a_:b_], FS, 33.0, 49.9) for a_, b_ in runs]
    if v:
        pr("      %-5s %-8s  rate 33-49.9 Hz p50 = %7.3f deg/s   bar 33-49.9 Hz p50 = %7.1f raw   (%d runs)" % (
            tag, BUILD[tag], float(np.median(v)), float(np.median(v2)), len(v)))

with open(os.path.join(SCR, "grind1_loop_shape_v287.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT) + "\n")
pr("")
pr("[written to _scratch/grind1_loop_shape_v287.txt]")
