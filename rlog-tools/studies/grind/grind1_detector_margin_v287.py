# -*- coding: utf-8 -*-
"""studies/grind/grind1_detector_margin_v287.py -- Honda's oscillation-reversal detector (FUN_000428d4) as a
RANKING CRITERION for the output-lag-pole ladder, and the sizing of the proposed cave rung.  Subagent `shape`, 2026-09-06.

ANALYSIS ONLY.  Builds nothing, sends nothing, flashes nothing.

The detector [EVIDENCE, tracer 2026-09-06, docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md]:
  input   gp-0x6c2c = a doubly-filtered derivative of motor ROTOR ANGLE (NOT on the torque path).
          Its own input filter is cal(0xC40DC), a one-pole  y += (x-y)*a/64  at 1 kHz.
          V282 flies a = 14 (corner 39.4 Hz); STOCK is 22 (corner 67.1 Hz).  V282 already narrowed it.
  trigger alternate crossings of +-cal(0xC620A) = 12800 (= 40 % of gp-0x6c2c's own full scale 32000),
          counter RESET if cal(0xC64DD) = 50 ticks (50 ms) elapse between crossings
          => it can only ever count content FASTER THAN 10 Hz.
  action  after 15 / 20 / 25 reversals (cal knots at 0xC694C/E/0xC6950) a LERP at 0xC694A cuts assist by
          up to 40 %; the factor reaches governor slot 2 (FUN_00045608 -> FUN_0004503c), is MIN-folded into
          the Q15 motor-demand scale and is SLEW-LIMITED.  Net x0.600 on motor demand.  Speed-gated
          gp-0x6a5e <= 960.  It is LIVE and engaged-relevant.

WHY IT RANKS THE LADDER.  The detector input is on the MOTION side, so its amplitude moves with the
closed-loop sensitivity, not with the lane gain.  The output-lag pole CUTS 18-22 Hz motion and RAISES
26-33 Hz motion; the detector's 50 ms reset means BOTH bands count.  So the pole's effect on the
detector is not obvious a priori and has to be computed on the measured waveform.

Run: python grind1_detector_margin_v287.py   (writes _scratch/grind1_detector_margin_v287.txt beside it)
"""
import os
import sys
import math
import cmath
import struct

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

LAG_A, LAG_B = u16(B, 0xC63EC), u16(B, 0xC63EE)
FB_A, FB_B = u16(B, 0xC63E8), u16(B, 0xC63EA)
DET_A = B[0xC40DC]          # detector input filter coefficient, /64
DET_TH = u16(B, 0xC620A)    # 12800
DET_RESET = B[0xC64DD]      # 50 ticks
DET_KNOTS = (B[0xC694C], B[0xC694E], B[0xC6950])
FS, FST, T = 100.0, 50.0, 1e-3

z = lambda f: cmath.exp(2j * math.pi * f * T)
Hlag = lambda f, a2=None, b2=None: ((LAG_B if b2 is None else b2) / 32768.0) * (1 + 1 / z(f)) / (
    1 - ((LAG_A if a2 is None else a2) / 1024.0) / z(f))
Hfb = lambda f, a=None, b=None: ((FB_B if b is None else b) / 1024.0) * (1 + 1 / z(f)) / (
    1 - ((FB_A if a is None else a) / 1024.0) / z(f))
dg = lambda c: math.degrees(cmath.phase(c))
polef = lambda a: -math.log(a / 1024.0) * 1000.0 / (2 * math.pi)

KP, KD = 248.0, 128.0
Cc = lambda f, kp=KP, kd=KD: kp / 256.0 + (kd / 8.0) * (1 - 1 / z(f))
PH_G20 = 157.0 - dg(Cc(20, 295, 0)) - dg(Hlag(20)) - dg(Hfb(20)) - 360.0
SLOPE = -(73.0 - 28.0) / 12.0
KMAG = 0.37 / abs(Cc(20, 295, 0) * Hlag(20) * Hfb(20))


def Lc(f, a2, b2):
    ph = dg(Cc(f)) + dg(Hlag(f, a2, b2)) + dg(Hfb(f)) + PH_G20 + SLOPE * (f - 20)
    return KMAG * abs(Cc(f) * Hlag(f, a2, b2) * Hfb(f)) * cmath.exp(1j * math.radians(ph))


def Srat(f, a2, b2):
    if f <= 0.5:
        return 1.0
    return abs(1.0 / (1.0 + Lc(f, a2, b2))) / abs(1.0 / (1.0 + Lc(f, LAG_A, LAG_B)))


DOSES = [("as-built V282", LAG_A, LAG_B),
         ("lag 6.0 Hz 986/602", 986, 602), ("lag 6.5 Hz 983/650", 983, 650),
         ("lag 7.2 Hz 979/713", 979, 713), ("lag 8.0 Hz 974/792", 974, 792),
         ("lag 10 Hz 962/982", 962, 982), ("lag 12 Hz 950/1172", 950, 1172),
         ("lag 15 Hz 932/1458", 932, 1458)]

pr("=" * 150)
pr("HONDA'S OSCILLATION-REVERSAL DETECTOR AS A RANKING CRITERION FOR THE OUTPUT-LAG POLE")
pr("=" * 150)
pr("  cals read from the V282 image (stock in brackets):")
pr("    0xC40DC detector input filter coeff  = %d /64  (stock %d)  -> corner %.1f Hz (stock %.1f Hz)" % (
    DET_A, BS[0xC40DC], -math.log(1 - DET_A / 64.0) * 1000 / (2 * math.pi),
    -math.log(1 - BS[0xC40DC] / 64.0) * 1000 / (2 * math.pi)))
pr("    0xC620A reversal threshold           = %d  (stock %d)  = %.0f %% of gp-0x6c2c full scale 32000" % (
    DET_TH, u16(BS, 0xC620A), 100.0 * DET_TH / 32000.0))
pr("    0xC64DD reset ticks                  = %d ms  -> counts only content faster than %.0f Hz" % (
    DET_RESET, 1000.0 / (2.0 * DET_RESET)))
pr("    0xC694C/E/0xC6950 reversal knots      = %d / %d / %d" % DET_KNOTS)
pr("  ⚠ 0xC40DC IS NOT STOCK ON V282 (14 vs 22).  V282 has already narrowed the detector's own input")
pr("    filter from 67.1 Hz to 39.4 Hz, which reduces what the detector sees above ~30 Hz.  It is the")
pr("    kit's 'second HF lever' (memory accord-alpha2-is-the-second-hf-lever).  [EVIDENCE, byte-read]")


def det_filter_response(f, a=None):
    a = DET_A if a is None else a
    p = 1.0 - a / 64.0
    zz = z(f)
    return (1 - p) / (1 - p / zz)


pr("")
pr("  DETECTOR INPUT FILTER, magnitude by frequency [EVIDENCE, arithmetic]:")
FG = [5, 7.3, 10, 15, 20, 25, 28, 30, 33, 40, 50]
pr("    %-16s" % "f Hz" + "".join("%7.4g" % f for f in FG))
pr("    %-16s" % ("V282 a=%d" % DET_A) + "".join("%7.3f" % abs(det_filter_response(f)) for f in FG))
pr("    %-16s" % ("stock a=%d" % BS[0xC40DC]) + "".join("%7.3f" % abs(det_filter_response(f, BS[0xC40DC])) for f in FG))
pr("  ⇒ the input filter is only %.1f dB down at 30 Hz.  IT DOES NOT PROTECT AGAINST A 26-33 Hz RISE." % (
    20 * math.log10(abs(det_filter_response(30)))))

# ------------------------------------------------------------------ the detector, mirrored
def reversal_max_count(x, fs, th, reset_s):
    """Largest run of ALTERNATE +-th crossings with < reset_s between consecutive counted crossings."""
    x = np.asarray(x, float)
    above = x > th
    below = x < -th
    ev_t, ev_s = [], []
    last = 0
    for i in range(len(x)):
        s = 1 if above[i] else (-1 if below[i] else 0)
        if s != 0 and s != last:
            ev_t.append(i / fs)
            ev_s.append(s)
            last = s
    if not ev_t:
        return 0
    best = cur = 1
    for k in range(1, len(ev_t)):
        if ev_t[k] - ev_t[k - 1] < reset_s:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def fire_threshold(x, fs, need, reset_s):
    """Largest threshold at which the detector would reach `need` reversals.  Bisection."""
    hi = float(np.max(np.abs(x)))
    if hi <= 0 or reversal_max_count(x, fs, 0.0, reset_s) < need:
        return 0.0
    lo = 0.0
    for _ in range(40):
        m = (lo + hi) / 2.0
        if reversal_max_count(x, fs, m, reset_s) >= need:
            lo = m
        else:
            hi = m
    return lo


def apply_ratio_1k(x100, a2, b2):
    """Upsample 100 Hz -> 1 kHz, apply the closed-loop sensitivity ratio, then the detector input filter."""
    x = C20.up1k(np.asarray(x100, float))
    n = len(x)
    m = x.mean()
    X = np.fft.rfft(x - m)
    f = np.fft.rfftfreq(n, 1.0 / 1000.0)
    R = np.array([Srat(ff, a2, b2) * abs(det_filter_response(ff)) if ff > 0 else 1.0 for ff in f])
    return np.fft.irfft(X * R, n)


# ------------------------------------------------------------------ load
ROUTES = ["r39", "r3a", "r3c", "r35"]
BUILD = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r35": "V281r3"}
G = {}
for tag in ROUTES:
    try:
        C20.BUILD[tag] = BUILD[tag]
    except Exception:
        pass
    try:
        G[tag] = C20.load(tag)
    except Exception as e:
        pr("  !! %s: %s" % (tag, e))

CREEP = lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)
# the two r39 userBookmark episodes (V282-READ-r39 sec0.1: episode PRECEDES the mark by 6-17 s)
EPISODES = {"r39": [(672.0, 692.0), (910.0, 930.0)]}


def segments(tag):
    g = G[tag]
    out = []
    m = CREEP(g)
    d = np.diff(np.r_[0, m.astype(int), 0])
    for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        if b_ - a_ >= 200:
            out.append(("creep", a_, b_))
    for t0, t1 in EPISODES.get(tag, []):
        a_ = int(np.searchsorted(g["tr"] if "tr" in g else g["t"] - g["t"][0], t0))
        b_ = int(np.searchsorted(g["tr"] if "tr" in g else g["t"] - g["t"][0], t1))
        if b_ - a_ >= 200:
            out.append(("bookmark", a_, b_))
    return out


for tag in G:
    G[tag]["tr"] = G[tag]["t"] - G[tag]["t"][0]

pr("")
pr("=" * 150)
pr("A. THE DETECTOR MARGIN, per dose -- computed on the MEASURED 0x18F wheel rate as a proxy for rotor rate")
pr("=" * 150)
pr("""
  🛑 PROXY, STATED AS BELIEF.  gp-0x6c2c is a derivative of motor ROTOR angle; I have the COLUMN/wheel
  rate on 0x18F.  Between them sit the worm gear (a scale, harmless to a ratio) and the torsional
  compliance of the column, which at 20-33 Hz lets the rotor move MORE than the wheel.  So a rotor-rate
  spectrum has, if anything, MORE relative high-frequency content than my proxy -- which makes every
  26-33 Hz number below an UNDER-estimate of the true detector exposure.  The direction of that error is
  the conservative one for a RISK statistic, and I am relying on that rather than on the proxy's accuracy.
  Absolute counts are not computable: no firmware factor links rotor rate to anything on the wire, so the
  scale K (counts per deg/s) is unknown.  EVERYTHING BELOW IS A RATIO, which is scale-free.
""")
pr("""
  THE STATISTIC.  Th_fire (the largest threshold still giving 15 reversals) turned out to be DEGENERATE:
  in most windows the base value is 0, because 15 alternate reversals inside the 50 ms reset window means
  375 ms of SUSTAINED >10 Hz oscillation, which today's creep motion mostly does not produce -- so the
  ratio divides by zero and reports absurd numbers.  That degeneracy is itself the physical finding: the
  detector needs PERSISTENCE, not amplitude.  I therefore fix the threshold at a fraction q of each
  window's OWN baseline peak (the true 12800 sits at an unknown fraction, so q is swept) and report the
  MAXIMUM REVERSAL RUN before and after.  Firing needs a run of 15.
""")
QS = (0.10, 0.15, 0.20, 0.30, 0.50, 0.70)
pr("  %-5s %-9s %6s | %-22s %10s | %s" % (
    "route", "window", "s", "dose", "peak |d| x",
    "".join("%18s" % ("maxrun q=%.1f" % q) for q in QS)))
MARG = {}
for tag in ROUTES:
    if tag not in G:
        continue
    g = G[tag]
    for lbl, a_, b_ in segments(tag):
        seg = g["rate_x"][a_:b_]
        base_pk, base_run = None, None
        for nm, a2, b2 in DOSES:
            d = apply_ratio_1k(seg, a2, b2)
            pk = float(np.max(np.abs(d)))
            if base_pk is None:
                base_pk = pk
            runs = [reversal_max_count(d, 1000.0, q * base_pk, DET_RESET / 1000.0) for q in QS]
            if base_run is None:
                base_run = runs
            MARG.setdefault(nm, []).append((pk / base_pk, runs, base_run))
            pr("  %-5s %-9s %6.1f | %-22s %10.3f | %s" % (
                tag, lbl, (b_ - a_) / FS, nm, pk / base_pk,
                "".join("%10d%8s" % (r, "(%+d)" % (r - br)) for r, br in zip(runs, base_run))))
        pr("")

pr("  POOLED ACROSS EVERY WINDOW:")
pr("  %-22s %12s | %s | %s" % ("dose", "peak |d| x",
                               "".join("%14s" % ("mean run q=%.1f" % q) for q in QS),
                               "windows reaching 15"))
for nm, a2, b2 in DOSES:
    v = MARG.get(nm, [])
    if not v:
        continue
    pk = float(np.mean([a for a, _, _ in v]))
    means = [float(np.mean([r[k] for _, r, _ in v])) for k in range(len(QS))]
    fired = [sum(1 for _, r, _ in v if r[k] >= DET_KNOTS[0]) for k in range(len(QS))]
    pr("  %-22s %12.3f | %s | %s of %d" % (
        nm, pk, "".join("%14.1f" % m for m in means),
        "/".join(str(f) for f in fired), len(v)))
pr("""
  READING.  'peak |d|' barely moves at any dose (0.98-1.00) because the detector input's peak is carried
  by LOW-frequency motion the edit does not touch.  What the edit changes is the PERSISTENCE of >10 Hz
  reversals -- exactly the thing the detector counts.  A dose that raises the mean maximum run, or that
  takes any window from below 15 to at or above 15, is spending detector margin.  The counts are on a
  wheel-rate PROXY and are ratios, not absolute predictions of firing.
""")

pr("")
pr("=" * 150)
pr("B. THE PROPOSED CAVE RUNG:  bit = ( |gp-0x6c2c| >= |gp-0x6c2e| )")
pr("=" * 150)
pr("""
  gp-0x6c2c is the FAST EMA (39.4 Hz) and gp-0x6c2e the SLOW EMA (3.8 Hz) of the same rotor-rate signal,
  so the rung is a scale-free HF-content detector on the MOTION, evaluated at full precision inside the
  cave at 1 kHz -- it is NOT alias-limited the way 0x18F is.  That is exactly the band my build's
  dominant risk lives in, and it is the doctrine's own 'compare, do not measure' form.
""")
slow = lambda f: (1 - math.exp(-2 * math.pi * 3.8 / 1000.0)) / abs(1 - math.exp(-2 * math.pi * 3.8 / 1000.0) / z(f)) \
    if False else abs((1 - 0.976397) / (1 - 0.976397 / z(f)))
pr("  ratio |fast/slow| by frequency [arithmetic; the tracer's 4.8 at 20 Hz is the check]:")
pr("    %-10s" % "f Hz" + "".join("%8.4g" % f for f in FG))
pr("    %-10s" % "|fast/slow|" + "".join("%8.2f" % (abs(det_filter_response(f)) / slow(f)) for f in FG))


def rung_duty(x100, a2, b2):
    x = C20.up1k(np.asarray(x100, float))
    n = len(x)
    m = x.mean()
    X = np.fft.rfft(x - m)
    f = np.fft.rfftfreq(n, 1.0 / 1000.0)
    Rf = np.array([Srat(ff, a2, b2) * abs(det_filter_response(ff)) if ff > 0 else 1.0 for ff in f])
    Rs = np.array([Srat(ff, a2, b2) * slow(ff) if ff > 0 else 1.0 for ff in f])
    fa = np.fft.irfft(X * Rf, n)
    sl = np.fft.irfft(X * Rs, n)
    return float(np.mean(np.abs(fa) >= np.abs(sl)))


pr("")
pr("  PREDICTED RUNG DUTY (fraction of 100 Hz frames with |fast| >= |slow|), per window and dose:")
pr("  %-5s %-9s | %-22s %10s %10s" % ("route", "window", "dose", "duty", "x base"))
DUTY = {}
for tag in ROUTES:
    if tag not in G:
        continue
    g = G[tag]
    for lbl, a_, b_ in segments(tag):
        seg = g["rate_x"][a_:b_]
        base = None
        for nm, a2, b2 in DOSES:
            d = rung_duty(seg, a2, b2)
            if base is None:
                base = d
            DUTY.setdefault(nm, []).append((d, base))
            pr("  %-5s %-9s | %-22s %10.4f %10.3f" % (tag, lbl, nm, d, d / base if base else float("nan")))
        pr("")
pr("  POOLED:")
pr("  %-22s %12s %12s" % ("dose", "mean duty", "x base"))
for nm, a2, b2 in DOSES:
    v = DUTY.get(nm, [])
    if not v:
        continue
    pr("  %-22s %12.4f %12.3f" % (nm, np.mean([d for d, _ in v]), np.mean([d / b for d, b in v if b])))

pr("")
pr("=" * 150)
pr("C. THE EXACT CAVE EDIT, read from the V282 image")
pr("=" * 150)
pr("""
  The V105 cave at 0xC4B34 carries FIVE rungs.  Read from the image, the two-operand COMPARATOR rungs are
  bit 6 and bit 5 (0x2E bytes each, operand A then operand B twelve bytes later); bits 7, 4 and 3 are
  SINGLE-OPERAND sign rungs of ~10-12 bytes each:

    0xC4B34  ld.h  -0x6ADA, gp, r6   hw1 3724   bit 6 operand A   (= r24)
    0xC4B40  ld.h  -0x6B38, gp, r6   hw1 3724   bit 6 operand B   (= T)
    0xC4B62  ld.h  -0x6ADA, gp, r6   hw1 3724   bit 5 operand A   (= r24)
    0xC4B6E  ld.h  -0x6B94, gp, r6   hw1 3724   bit 5 operand B   (= aggregator)
    0xC4B92  ld.h  -0x6B4C, gp, r6   hw1 3724   bit 7  sign(11-slot assist sum)      SINGLE OPERAND
    0xC4B9C  ld.h  -0x6ADA, gp, r6   hw1 3724   bit 4  sign(r24)                     SINGLE OPERAND
    0xC4BA8  ld.w  -0x3680, gp, r6   hw1 3724   bit 3  sign(gp-0x3680)                SINGLE OPERAND
             (hw2 C981 -- displacement bit 0 is the ld.h/ld.w opcode select, so this is a WORD load of
              -0x3680, which is why the record calls it gp-0x3680 and not gp-0x367f.  The
              'hw2 = disp|1' trap, confirmed here.)

  🛑 SO IT IS TWO HALFWORDS, NOT FOUR, AND IT COSTS BIT 5 -- NOT A LEGACY BIT.  A legacy bit (3 or 7) is
  a SINGLE-OPERAND rung; converting one to a comparator needs ~+0x22 bytes of new instructions, a length
  change and a relocation.  That is NOT the V282 class of edit and I do not propose it.  The only
  in-place, no-length-change route is to REPOINT an existing comparator rung.
""")
pr("  PROPOSED, repointing bit 5 (the less load-bearing comparator):")
pr("    %-12s %-14s %-26s %-26s" % ("offset", "now (hw2)", "from", "to"))
pr("    %-12s %-14s %-26s %-26s" % ("0xC4B64-65", "%04X" % u16(B, 0xC4B64), "gp-0x6ADA (r24)", "gp-0x6C2C -> hw2 %04X" % ((-0x6C2C) & 0xFFFF)))
pr("    %-12s %-14s %-26s %-26s" % ("0xC4B70-71", "%04X" % u16(B, 0xC4B70), "gp-0x6B94 (aggregator)", "gp-0x6C2E -> hw2 %04X" % ((-0x6C2E) & 0xFFFF)))
pr("    hw1 stays 3724 at both sites; both new displacements are EVEN (bit 0 = 0), so both stay `ld.h`.")
pr("    Byte-level: 0xC4B64 `26 95` -> `d4 93` ; 0xC4B70 `6c 94` -> `d2 93`.  4 bytes, read-only,")
pr("    no length change, no relocation.  Recompute the page CRC at 0xC4FFC and re-hash the cave.")
pr("")
pr("  WHAT IS GIVEN UP: bit 5 = |r24| >= |aggregator|, duty 0.1341 / 0.1525 / 0.1678 on r39 / r3a / r3c.")
pr("  Its question -- how big r24 is against the whole aggregator -- is answered to the precision that")
pr("  matters (s = 0.41-0.52, replicated on four routes and two builds), and the proposed build does NOT")
pr("  touch r24, the r24 gain, or the aggregator composition.  Bit 6 (|r24| >= |T|) is KEPT, so the r24")
pr("  ladder still reads on this drive and the negative control against r34/r35 still holds.")

with open(os.path.join(SCR, "grind1_detector_margin_v287.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT) + "\n")
pr("")
pr("[written to _scratch/grind1_detector_margin_v287.txt]")
