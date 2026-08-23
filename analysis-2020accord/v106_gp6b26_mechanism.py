#!/usr/bin/env python
"""
V106 / gp-0x6b26 mechanism, ceiling and reshape -- integer mirror of the decompiled arithmetic.

Every arithmetic line is annotated with the instruction address it mirrors.
V850E2 is little-endian; `sar` == Python `>>` (both floor); `mul rA,rB,r0` keeps only the
LOW 32 bits (r0 discards the high word) so int32 wrap is mirrored explicitly.

Programs:  stock  code.bin
           v106   _v106_V105BASE-GP6B26.X3.0.D7A5C-D7A6C_plain_image.bin

Chain traced (all addresses verified by GhidraMCP disassembly, 2026-08-22):
  FUN_00041464 @0x41464   gp-0x4f50 (motor rate) -> EMA1 -> backward difference -> x32 -> EMA-A
                          -> >>9 -> gp-0x6c2c            (= angular ACCELERATION)
  FUN_00036c12 @0x36c12   gp-0x6c2c -> validity gate -> speed LERP (0xCBE74[mode]) -> *0x111>>18
                          -> clamp +-cal(0xC407E)=511 -> gp-0x6b26
  FUN_0003aa2c @0x3aa2c   gp-0x6b26 -> +-1024 validity window -> UNWEIGHTED +1 into the
                          aggregator -> clamp +-0x2800 -> gp-0x6b94
"""
import cmath
import math
import struct

# ---------------------------------------------------------------------------
# 0. Calibrations, byte-read little-endian from the images
# ---------------------------------------------------------------------------
K1 = 37     # cal 0xC643C, ld.hu 0x743c[tp] @0x415DA   EMA1 alpha = 37/128
K2A = 22    # cal 0xC40DC, ld.hu 0x50dc[tp] @0x41626   EMA-A alpha = 22/64
CLAMP = 511  # cal 0xC407E, ld.h 0x507e[tp]  @0x36C34
FS = 1000.0  # FUN_0002214a (sole caller of FUN_00036c12) and FUN_00041464 both run at 1 kHz

# 0xCBE74 + mode*4 -> record base.  Record: n@+0, X[3]@+2, Y[3]@+8   (all int16 LE)
X_ROW = (0, 1280, 5760)                 # gp-0x6a5e counts, 64 ct/km/h  =>  0, 20, 90 km/h
Y_STOCK = (-9830, -5734, -1966)         # every mode record, stock
Y_V106 = (-29490, -17202, -5898)        # modes 26/27 only  (= x3.0 stock)

CT_PER_DEG_S = 4.7121   # gp-0x4f50 / gp-0x6abe scale, inherited (BELIEF-grade elsewhere in kit)


# ---------------------------------------------------------------------------
# 1. FUN_00041464 -- the gp-0x6c2c producer, exact integer recurrence
# ---------------------------------------------------------------------------
def s32(v):
    """Mirror the 32-bit truncation of `mul rA,rB,r0` (high word discarded)."""
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def s16(v):
    """Mirror `st.h` truncation."""
    v &= 0xFFFF
    return v - (1 << 16) if v & 0x8000 else v


class C2CProducer:
    """gp-0x6c2c, byte-exact.  State: s1 (gp-0x359c), sA (gp-0x35a0)."""

    def __init__(self):
        self.s1 = 0x7FFFFFFF   # gp-0x359c sentinel, tested @0x415D6
        self.sA = 0            # gp-0x35a0

    def step(self, rate):
        # 0x415BE addi 0x32c8,r15,r11 / 0x415C2 addi -0x6591,r11,r0 / 0x415CE bc
        valid = -13000 <= rate <= 13000
        if not valid:
            self.s1, self.sA = 0, 0          # 0x415F2 mov 0x0,r24 ; 0x41652 st.w r0
            return 0x7FFF                    # 0x41ABE movea 0x7fff -> st.h @0x41AC2
        target = rate << 10                  # 0x415D4 shl 0xa,r28
        if self.s1 == 0x7FFFFFFF:            # 0x415D8 be  -> first tick
            s1_new = target                  # 0x415EE mov r28,r24
            s1_old = s1_new                  # 0x415FE mov r24,r7  (difference forced to 0)
        else:
            step = s32(s32((target - self.s1) * K1)) >> 7   # 0x415DE sub / 0x415E0 mul / 0x415E6 sar 7
            s1_new = self.s1 + step                          # 0x415E8 add r28,r24
            s1_old = self.s1 if self.s1 <= 0xCB2000 else s1_new  # 0x415FA cmp / 0x415FC ble / 0x415FE
        d = s1_new - s1_old                  # 0x41602 sub r7,r9   <- THE BACKWARD DIFFERENCE
        if d > 0x7D000:                      # 0x4160A cmp 512000 / 0x41610 bgt
            d32 = 0xFA0000                   # 0x4160C movhi 0xfa  (= 512000*32 exactly)
        else:
            d32 = d << 5                     # 0x41612 shl 0x5,r9
            if d32 <= -0xFA0000:             # 0x41618 cmp / 0x4161A cmovle
                d32 = -0xFA0000
        self.sA += s32(s32((d32 - self.sA) * K2A)) >> 6   # 0x41630 sub / 0x41632 mul / 0x4163A sar 6 / 0x41642 add
        self.s1 = s1_new                     # 0x41B74 st.w r28,-0x359c[gp]
        return s16(self.sA >> 9)             # 0x4184A sar 0x9 ; 0x4184E st.h -0x6c2c[gp]


def H_c2c(f, fs=FS):
    """Closed-form z-domain twin of C2CProducer, for cross-checking the integer sim.

    H(z) = 1024 * [a1/(1-(1-a1)z^-1)] * (1-z^-1) * 32 * [a2/(1-(1-a2)z^-1)] / 512
    """
    a1, a2 = K1 / 128.0, K2A / 64.0
    z1 = cmath.exp(-2j * math.pi * f / fs)
    h1 = a1 / (1 - (1 - a1) * z1)
    h2 = a2 / (1 - (1 - a2) * z1)
    return 1024 * h1 * (1 - z1) * 32 * h2 / 512      # net static factor 64


# ---------------------------------------------------------------------------
# 2. FUN_00036c12 -- speed LERP, gain, clamp
# ---------------------------------------------------------------------------
def lerp_Y(speed_ct, X=X_ROW, Y=Y_STOCK):
    """Mirror of 0x36C60..0x36CB0.  `speed_ct` = gp-0x6a5e (64 ct/km/h)."""
    if speed_ct <= X[0]:                    # 0x36C6A cmp / 0x36C6C bgt
        return Y[0]                         # 0x36C6E ld.h 0x0[r14]
    if speed_ct >= X[2]:                    # 0x36C76 cmp / 0x36C78 bge
        return Y[2]                         # 0x36C84 ld.h 0x4[r14]
    i = 1 if speed_ct >= X[1] else 0        # 0x36C7E cmp / 0x36C80 bge  (walk loop 0x36C8A)
    num = (Y[i + 1] - Y[i]) * (speed_ct - X[i])          # 0x36CA0 sub / 0x36CA6 mul
    den = X[i + 1] - X[i]                                # 0x36CAA sub
    q = int(num / den) if num * den < 0 else num // den  # 0x36CAC divq  (truncates toward zero)
    return Y[i] + q                                      # 0x36CB0 add r7,r12


def gp6b26(c2c, Y_gain, clamp=CLAMP):
    """Mirror of 0x36C1A..0x36CE2.  Returns (value, overflowed)."""
    # 0x36C26 addi 0x7d00 / 0x36C2A cmp 0xfa01 / 0x36C2C cmovnc  -> +-32000 validity gate
    g = c2c if (c2c + 0x7D00) & 0xFFFFFFFF < 0xFA01 else 0
    m = s32(g * Y_gain) >> 6                # 0x36CBE mulh r12,r13 / 0x36CC4 sar 0x6
    raw = s32(m * 0x111)                    # 0x36CC6 mul r13,r6,r0   <- LOW 32 BITS ONLY
    ovf = (m * 0x111) != raw                # int32 wrap actually occurred
    out = raw >> 18                         # 0x36CCA sar 0x12
    if out > clamp:                         # 0x36CCC cmp / 0x36CCE ble
        out = clamp                         # 0x36CD0
    elif out < -clamp:                       # 0x36CD8 cmp / 0x36CDA bge
        out = -clamp                        # 0x36CDC..0x36CE2
    return out, ovf                          # stored @0x36CF0 st.h -0x6b26[gp] (+ shadow 0x36CF4)


def aggregator_term(x):
    """Mirror of 0x3AC98..0x3ACB8 then the `add` chain 0x3ACD2/0x3ACD4."""
    keep = ((x + 0x400) & 0xFFFFFFFF) < 0x801     # +-1024 validity window
    return x if keep else 0                        # coefficient EXACTLY +1


K_OF_Y = 273.0 / 2 ** 24    # net |gp-0x6b26| / |gp-0x6c2c| = |Y| * 0x111 / 2**(6+18)


def sat_df(A, L):
    """Describing function of a symmetric saturation, normalised to unity in the linear region."""
    if A <= L:
        return 1.0
    r = L / A
    return (2 / math.pi) * (math.asin(r) + r * math.sqrt(1 - r * r))


# ---------------------------------------------------------------------------
# 3. Verification: integer sim vs closed form, and the aggregator sign
# ---------------------------------------------------------------------------
def sim_response(f, amp_ct, fs=FS, cycles=60):
    """Drive the exact integer recurrence with a sinusoid; return (gain, phase_deg)."""
    p = C2CProducer()
    n = int(cycles * fs / f)
    out, drive_c, drive_s = [], 0.0, 0.0
    for k in range(n):
        y = p.step(int(round(amp_ct * math.sin(2 * math.pi * f * k / fs))))
        if k >= n // 2:
            out.append(y)
    m = len(out)
    for k, y in enumerate(out):
        t = 2 * math.pi * f * (k + n - m) / fs
        drive_c += y * math.cos(t)
        drive_s += y * math.sin(t)
    ph = math.degrees(math.atan2(drive_c, drive_s))
    mag = 2 * math.hypot(drive_c, drive_s) / m / amp_ct
    return mag, ph


def main():
    print("=" * 78)
    print("D2  gp-0x6c2c CASCADE  |H| and PHASE  (rate -> acceleration proxy)")
    print("=" * 78)
    print(" f(Hz)   |H|_closed   ph_closed   |H|_int    ph_int    dissip.   inertial")
    for f in (5, 8, 15, 20, 21.73, 22, 25, 30, 40):
        h = H_c2c(f)
        gi, pi = sim_response(f, 800)
        # gp-0x6b26 = -k*gp-0x6c2c, so its phase vs rate is (phase(H) + 180).
        # projection onto the 180deg (damping) axis = cos(phase(H))
        # projection onto the 270deg (ADDED-inertia) axis = sin(phase(H))
        ph = math.degrees(cmath.phase(h))
        print("%6.2f   %8.3f   %+8.2f   %8.3f  %+8.2f   %+7.3f   %+7.3f"
              % (f, abs(h), ph, gi, pi, math.cos(math.radians(ph)), math.sin(math.radians(ph))))

    print()
    print("  phase(H) > 0 everywhere below ~65 Hz  =>  cos>0 (DAMPING) and sin>0 (ADDED INERTIA).")
    print("  gp-0x6b26 = -k*gp-0x6c2c enters the aggregator at +1, so its torque phasor sits at")
    print("  phase(H)+180 deg relative to motor rate: between 180 (pure damping) and 270 (pure")
    print("  ADDED inertia).  It can never land between 90 and 180 = the only sector that would")
    print("  RAISE a 2nd-order resonance.")

    print()
    print("=" * 78)
    print("D1  SIGN, three ways")
    print("=" * 78)
    for nm, Y in (("stock", Y_STOCK), ("V106 x3.0", Y_V106)):
        print("  %-10s Y row %s  -> ALL NEGATIVE at every speed; k=|Y|*273/2**24" % (nm, Y))
    for v in (-2000, -500, 500, 2000):
        o, _ = gp6b26(v, lerp_Y(0, Y=Y_V106))
        print("    gp-0x6c2c=%+6d  ->  gp-0x6b26=%+5d   (opposite sign: OPPOSES acceleration)" % (v, o))
    print("    aggregator: gated value enters via `add r10,r15` @0x3ACD2, coefficient +1, no weight")

    print()
    print("=" * 78)
    print("D3(a)/D4  SPEED SCHEDULE, CLAMP KNEE, int16 CEILING")
    print("=" * 78)
    print("  X row = %s counts = %s km/h  (gp-0x6a5e, 64 ct/km/h)" % (X_ROW, [x / 64 for x in X_ROW]))
    print()
    print("  mult   Y[0]      Y[1]      Y[2]     int16?   k@0kmh  k@8kmh  k@90kmh  "
          "knee@0kmh  knee@90kmh")
    for m in (1.0, 1.5, 2.0, 3.0, 3.334, 4.0, 5.0, 6.0, 8.0):
        Y = tuple(int(round(y * m)) for y in Y_STOCK)
        ok = all(-32768 <= y <= 32767 for y in Y)
        k0 = abs(lerp_Y(0, Y=Y)) * K_OF_Y
        k8 = abs(lerp_Y(8 * 64, Y=Y)) * K_OF_Y
        k90 = abs(lerp_Y(90 * 64, Y=Y)) * K_OF_Y
        print("  %5.3f  %7d  %8d  %8d   %-6s  %6.4f  %6.4f  %7.4f  %8.0f  %10.0f"
              % (m, Y[0], Y[1], Y[2], "OK" if ok else "OVERFLOW",
                 k0, k8, k90, CLAMP / k0, CLAMP / k90))
    print()
    print("  int16 ceiling per row (stock-relative):  Y[0] x%.3f   Y[1] x%.3f   Y[2] x%.3f"
          % (32767 / 9830, 32767 / 5734, 32767 / 1966))
    print("  => UNIFORM scaling is hard-capped at x3.334 by Y[0].  V106 (x3.0) is at 90% of it.")

    print()
    print("=" * 78)
    print("D3(a) CLAMP DUTY -- against the measured V104 |gp-0x6c2c| distribution")
    print("=" * 78)
    #  reconstructed |gp-0x6c2c| percentiles, V104 engaged <16 km/h (ra4 corpus, FFT method)
    pct = [(50, 119), (90, 1064), (95, 1296), (99, 1704), (99.9, 2053), (100, 5141)]
    print("  V104 engaged <16km/h percentiles: %s" % pct)
    print("  mult   knee@0kmh   exceedance (log-interp on the percentile grid)   published")
    published = {1.5: 0.088, 2.0: 1.563, 3.0: 9.969}
    for m in (1.5, 2.0, 3.0, 3.334, 4.0, 5.0, 6.0, 8.0):
        knee = CLAMP / (9830 * m * K_OF_Y)
        # log-linear interpolation of the exceedance curve
        xs = [v for _, v in pct]
        ys = [100 - p for p, _ in pct]
        ex = None
        for i in range(len(xs) - 1):
            if xs[i] <= knee <= xs[i + 1]:
                t = (math.log(knee) - math.log(xs[i])) / (math.log(xs[i + 1]) - math.log(xs[i]))
                ex = ys[i] + t * (ys[i + 1] - ys[i])
                break
        if ex is None:
            ex = ys[0] if knee < xs[0] else ys[-1]
        print("  %5.3f  %8.0f    %6.2f %%%s%s"
              % (m, knee, ex, " " * 26,
                 ("   published %.3f%%" % published[m]) if m in published else ""))

    print()
    print("=" * 78)
    print("D3(b)  int32 OVERFLOW on the *0x111 product  (0x36CC6 mul, high word discarded)")
    print("=" * 78)
    for m in (1.5, 2.0, 3.0, 3.334, 5.0):
        Y = int(round(-9830 * m))
        thr = None
        for c in range(1, 32001):
            _, ov = gp6b26(c, Y)
            if ov:
                thr = c
                break
        print("  x%-6.3f  Y[0]=%-7d  first overflowing |gp-0x6c2c| = %s   (producer ceiling 32000, "
              "corpus max 5141)" % (m, Y, thr if thr else ">32000"))

    print()
    print("=" * 78)
    print("D3(c)  RULE-11 / 0xC407E ORDERING")
    print("=" * 78)
    print("  0x36CCC..0x36CE2  clamp to +-cal(0xC407E)=511")
    print("  0x36CF0          st.h r6,-0x6b26[gp]      <- the ONLY writer, image-wide")
    print("  0x36CF4          st.h r6,-0x4cd0[gp]      <- shadow half, same clamped value")
    print("  FUN_00036d74     |gp-0x6b26|*0.0009765625 > f32(0xC4004)=0.5  =>  trip at 512 raw")
    print("  => clamp PRECEDES both the store and the monitor. 511 < 512 by exactly one count.")
    print("     Structurally untrippable at ANY Y multiplier, provided 0xC407E stays 511.")
    print("  Aggregator +-1024 validity window (0x3ACB0) is likewise unreachable: 511 < 1024.")
    print("  !! Raising 0xC407E above 1024 would ACQUIRE a full-magnitude dropout the lane")
    print("     does not have today, on top of re-arming the 512 trip.  Do not touch it.")

    print()
    print("=" * 78)
    print("D3(a)  RELAY INDEX -- the V80 failure mode.  N = saturation describing function.")
    print("=" * 78)
    print("  index = N(A_p50)/N(A_p99) over the measured in-burst |gp-0x6c2c| range 119..1704.")
    print("  V80's damper (the worst grinding ever recorded) scored 3.27; V75 scored 1.45.")
    print("  mult     A_p50    A_p99   N(p50)  N(p99)   relay index")
    for m in (1.0, 1.5, 2.0, 3.0, 3.334, 4.0, 6.0, 8.0):
        k = 9830 * m * K_OF_Y
        a50, a99 = 119 * k, 1704 * k
        n50, n99 = sat_df(a50, CLAMP), sat_df(a99, CLAMP)
        print("  %5.3f  %7.1f  %7.1f   %6.3f  %6.3f   %8.2f%s"
              % (m, a50, a99, n50, n99, n50 / n99,
                 "   <- V75-class" if n50 / n99 < 1.5 else
                 ("   <- V80-CLASS RELAY" if n50 / n99 > 3.0 else "   <- transitional")))

    print()
    print("=" * 78)
    print("D3(d)/MECHANISM  IMPEDANCE DECOMPOSITION AND THE AUTHORITY BOUND")
    print("=" * 78)
    print("  Torque phasor of gp-0x6b26 vs motor rate = k*|H| at (phase(H)+180) deg.")
    print("  damping        c(f)  = k*|H(f)|*cos(phase)        [counts per count-of-rate]")
    print("  ADDED inertia  dJ(f) = k*|H(f)|*sin(phase)/omega  [counts per count-of-accel]")
    print()
    print("   f(Hz)     c  (x1.5)    c  (x3.0)    dJ (x1.5)    dJ (x3.0)")
    for f in (5, 8, 15, 20, 21.73, 25, 30, 40):
        h = H_c2c(f)
        w = 2 * math.pi * f
        ph = cmath.phase(h)
        for lbl, mm in (("", 1.5), ("", 3.0)):
            pass
        c15 = 9830 * 1.5 * K_OF_Y * abs(h) * math.cos(ph)
        c30 = 9830 * 3.0 * K_OF_Y * abs(h) * math.cos(ph)
        j15 = 9830 * 1.5 * K_OF_Y * abs(h) * math.sin(ph) / w
        j30 = 9830 * 3.0 * K_OF_Y * abs(h) * math.sin(ph) / w
        print("  %6.2f    %9.4f    %9.4f    %9.5f    %9.5f" % (f, c15, c30, j15, j30))
    print()
    print("  dJ is POSITIVE at every frequency => ADDED apparent inertia => omega_n DOWN.")
    print("  dJ FALLS with frequency (0.0301 -> 0.0219 -> 0.0104 at x3.0, 5->21.7->40 Hz) while c RISES 32x.")
    print()
    print("  AUTHORITY BOUND on any mechanical frequency shift:")
    print("    the term is hard-clamped at 511 counts of a +-10240 aggregate  = 4.99%%.")
    print("    Even if the ENTIRE aggregate command were the inertial reaction of the mode,")
    print("    dJ/J <= 0.0499  =>  |df/f| <= 0.0250  =>  |df| <= %.2f Hz on a 21.73 Hz mode."
          % (0.5 * 0.0499 * 21.73))
    print("    A 'notable' audible pitch rise is larger than that, in EITHER direction.")
    print()
    print("  AMPLITUDE-MEDIATED alternative (accord-f0-crossover-is-the-endpoint):")
    print("    f0 moves -1.93 Hz per e-fold of COMMAND AMPLITUDE at fixed gain (measured,")
    print("    within-route, speed-matched, disjoint CIs).  So an amplitude REDUCTION of")
    print("    factor R predicts +1.93*ln(R) Hz:")
    for R in (1.5, 2.0, 3.0, 5.0, 8.0):
        print("      amplitude /%-4.1f  ->  %+5.2f Hz  (%+5.2f%% of 21.73 Hz)"
              % (R, 1.93 * math.log(R), 100 * 1.93 * math.log(R) / 21.73))

    print()
    print("=" * 78)
    print("BLAST RADIUS  gp-0x6b26 -- 5 sites, Ghidra and a raw LE byte scan AGREE EXACTLY")
    print("=" * 78)
    print("  0x36CE4  ld.h  FUN_00036c12   shadow-lockstep compare vs gp-0x4cd0")
    print("  0x36CF0  st.h  FUN_00036c12   THE SOLE WRITER, image-wide, post-clamp")
    print("  0x36D78  ld.h  FUN_00036d74   RULE-11 monitor -> DTC 0x1d (trip at 512)")
    print("  0x3815C  ld.h  FUN_00038148   PATH 2  -> gp-0x6b70 -> gp-0x6ad6 (weight 0xC63A6=1024)")
    print("  0x3AC98  ld.h  FUN_0003aa2c   PATH 1  -> aggregator, UNWEIGHTED +1 -> gp-0x6b94")
    print("  (Ghidra also returns 0x6B25A/0x6B25E: branch-target TEXT collisions, adjudicated out.)")
    print()
    print("  !! TWO CONSUMER PATHS, not one.  The +-511 clamp is UPSTREAM of both, so both")
    print("     scale identically with Y and the ceiling analysis is unaffected -- but the")
    print("     4.99%% authority figure below covers PATH 1 ONLY.  Path 2's referral factor to")
    print("     gp-0x6ad6 is x1.601 @21 Hz (0xC63A6=1024 x 0xC6468=2639 x16, stage-2 >>4 cancels")
    print("     the x16, through the 0xC63AC=102/1024 EMA) => ~10%% of gp-0x6ad6's own 8192")
    print("     clamp -- and then a RUNTIME-SCHEDULED PID gain that is NOT statically boundable.")

    print()
    print("=" * 78)
    print("D5  RAMP OPPOSITION -- does this term cause the steering-rate limit?")
    print("=" * 78)
    print("  H(f=0) = 0 EXACTLY: a SUSTAINED constant rate produces zero acceleration and zero")
    print("  term.  So the term cannot bound the maximum sustained rate at any multiplier.")
    print("  What it does oppose is a constant-ACCELERATION ramp.  Steady state of the exact")
    print("  recurrence under rate[n]=rate[n-1]+delta:  gp-0x6c2c -> 64*delta.")
    print()
    print("   accel      gp-0x6c2c   |gp-0x6b26| @0km/h    %% of aggregate +-10240 clamp")
    print("   deg/s^2               V105 x1.5   V106 x3.0    V105    V106   delta")
    for A in (250, 500, 1000, 2000, 3532, 5000, 7064, 10000):
        p15, p30 = C2CProducer(), C2CProducer()
        r = 0.0
        c15 = c30 = 0
        for n in range(4000):
            r += CT_PER_DEG_S * A / FS
            c15 = p15.step(int(round(r)))
            c30 = p30.step(int(round(r)))
            if abs(r) > 12000:
                break
        v15, _ = gp6b26(c15, lerp_Y(0, Y=tuple(int(y * 1.5) for y in Y_STOCK)))
        v30, _ = gp6b26(c30, lerp_Y(0, Y=Y_V106))
        print("   %6d      %6d      %5d       %5d      %5.2f%%  %5.2f%%  %+5.2f%%"
              % (A, c30, abs(v15), abs(v30), 100 * abs(v15) / 10240,
                 100 * abs(v30) / 10240, 100 * (abs(v30) - abs(v15)) / 10240))
    print()
    print("  Fully saturated the term is 511/10240 = 4.99%% of aggregate authority.")
    print("  The V106-minus-V105 DELTA never exceeds 2.5%% of it.")

    print()
    print("=" * 78)
    print("D4  RESHAPE vs UNIFORM SCALE -- authority at the symptomatic speeds")
    print("=" * 78)
    speeds = [(5 * 1.609, "creep ~5 mph"), (20, "20 km/h"), (48, "30 mph"),
              (90, "90 km/h"), (105, "highway ~65 mph")]
    cands = {
        "stock                 ": Y_STOCK,
        "V105  x1.5 uniform    ": tuple(int(y * 1.5) for y in Y_STOCK),
        "V106  x3.0 uniform    ": Y_V106,
        "MAX uniform x3.334    ": (-32767, -19122, -6556),
        "RESHAPE A  flat -29490": (-29490, -29490, -29490),
        "RESHAPE B  flat -32767": (-32767, -32767, -32767),
        "RESHAPE C  hold creep ": (-29490, -29490, -20000),
    }
    hdr = "  %-22s" % "candidate"
    for _, nm in speeds:
        hdr += "%14s" % nm
    print(hdr + "     int16")
    for nm, Y in cands.items():
        row = "  %-22s" % nm
        for v, _ in speeds:
            row += "%14d" % lerp_Y(int(round(v * 64)), Y=Y)
        ok = all(-32768 <= y <= 32767 for y in Y)
        print(row + "     %s" % ("OK" if ok else "OVERFLOW"))
    print()
    print("  ratio vs V106 (how much MORE opposition each candidate delivers):")
    base = {v: abs(lerp_Y(int(round(v * 64)), Y=Y_V106)) for v, _ in speeds}
    for nm, Y in cands.items():
        row = "  %-22s" % nm
        for v, _ in speeds:
            row += "%13.2fx" % (abs(lerp_Y(int(round(v * 64)), Y=Y)) / base[v])
        print(row)
    print()
    print("  Creep clamp-knee is what costs; highway clamp-knee is nowhere near being reached.")
    print("  RESHAPE A holds Y[0] EXACTLY at V106 => creep clamp duty is UNCHANGED (~10%%),")
    print("  while highway authority rises 5.00x, 30 mph 2.33x and 20 km/h 1.71x.")


if __name__ == "__main__":
    main()
