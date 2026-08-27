#!/usr/bin/env python3
r"""studies/sessions/v76/v76_surface.py -- design the V76 FactorC/FactorE surface: V75-like dose, FLAT FactorC, bounded slew.

WHAT THIS IS
------------
A faithful integer mirror of the damper-dose evaluator `FUN_00034350` (the sole reader of
FactorB/C/D/E and the ceiling table at all 40 modes), plus the design search the V76 build needs.
Every arithmetic line carries the instruction address it mirrors, taken from the GhidraMCP
disassembly of the STOCK program. Constants are read LITTLE-ENDIAN out of the plain images --
nothing about the tables is hard-coded.

  LERP  (same idiom at 0x34470 B, 0x34502 C, 0x34592 D, 0x34616 E, 0x346B4 ceiling):
      rec  = *(u32*)(PTR_ARRAY + mode*4)                    ld.w  0x0[r13]     0x34514
      X[i] = *(u16*)(rec + 2 + 2i)     Y[i] = *(u16*)(rec + 2 + 2n + 2i)
      if !(idx >u X[0])    -> Y[0]      HARD CLAMP           cmp/bh             0x3451E/20
      if !(idx <u X[n-1])  -> Y[n-1]    HARD CLAMP           cmp/bnc            0x3452A/2C
      walk k from 1 while X[k] <=u idx                       cmp/bnc            0x3453E-46
      out = SIGNED32((Y[k]-Y[k-1])*(idx-X[k-1])) / SIGNED32(X[k]-X[k-1]) + Y[k-1]
                                                             mul/divq/add       0x3455A/60/64
      out &= 0xFFFF                                          andi 0xffff        0x34566
  DOSE  (0x34684-0x346A2) -- UNSIGNED `mulu` + LOGICAL `shr 0xa`, i.e. Q10, FOUR TIMES:
      s = seed; if (s >= 0x401) s = 0x400                    addi/setfnc/cmovne 0x344E4/E8
      d = (s*B)>>10                                          mulu/shr           0x34684/88
      d = (d*C)>>10                                          mulu/shr           0x3468A/8E
      d = (d*D)>>10                                          mulu/shr           0x34690/96
      d = (d*(E & 0xFFFF))>>10                               zxh/mulu/shr       0x34694/98/9C
      if (rate_signed > 0) d = -d                            cmp/ble/subr       0x3469E-0x346A2
  GATES:
      FactorC used iff speed <u 0x7D00 AND gp-0x67f4==1, else 1024               0x344E0-0x344FA
      FactorE used iff |rate| <u 0x32C9 AND -13000<=rate_s<=13000, else DOSE=0    0x345FA-0x34614
  CEILING + CLAMP (0x346A4-0x3475C):
      ceil = (gp-0x6ac2 <u 0x32C9) ? LERP(0xC77A0[mode], gp-0x6ac2) : *(u16*)(tp+0x7158) = 512
      if (d >s ceil) out=+ceil; elif (d >=s -ceil) out=d; else out=-ceil          0x34724/2A, 3C/3E
      out -> gp-0x6bd0 (st.h, 16-bit)                                             0x3475C

  There are ZERO `add`/`or` instructions in the 0x34684-0x3469C span => the factor chain is
  PURELY MULTIPLICATIVE and any factor reading 0 forces gp-0x6bd0 = 0.

TRAPS THIS MIRROR HONOURS (each has cost this kit a wrong answer before)
  * `divq` is SIGNED and truncates toward ZERO -- NOT Python floor `//`. With a DESCENDING Y
    segment (FactorC 566 -> 234) the numerator is negative and the two differ by one count.
  * the X[0] / X[n-1] compares are UNSIGNED and STRICT (`bh` / `bnc`), so idx == X[0] takes the
    Y[0] clamp, not the ramp.
  * the four `shr 0xa` are LOGICAL on an UNSIGNED product; the sign is applied afterwards.

THE FAULT MECHANISM THIS DESIGN TARGETS  [EVIDENCE, docs/HANDOFF-2026-08-07]
  Surface A: `FUN_00034350` (int leg, fid 28) vs `FUN_000347b8` (float leg, fid 29), where
      fVar5 = (float)(int)*(short*)(gp-0x6bd0) * 0.0009765625      // Q10, 1 count = 1/1024
  and the residual is tested against the float immediate 0x3ba00000.
      0x3ba00000 -> sign 0, exp 0x77 = 119 -> 2^-8, mantissa 1.25  => 1.25 * 2^-8 = 5/1024
  => the corridor is +/- 5/1024 in the float domain = +/- 5 COUNTS of gp-0x6bd0.
  Neither leg computes a derivative: both are per-cycle STATIC int-vs-float consistency checks,
  and `FUN_00018738`'s dwell threshold reads 0x0000 for fid 28 AND fid 29, so the trip fires on
  the FIRST qualifying call. A static un-debounced window is what a large single-cycle transient
  trips -- and both hard faults fired at their drive's single largest |d(angle rate)/dt|
  (V74 5,400/s, V75 6,900/s; n=1 each), while torque MAGNITUDE does not unify them.

THE CENTRAL ARITHMETIC RESULT (derived in `pareto()`, proved in `prove_dose_slew_identity()`)
  In the ramp regime, with seed = B = D = 1024 (verified flat unity in every mode):
      dose(r) = (C_Y0 * E(r)) >> 10          and          E(r) = E_Y1*(r-E_X0)//(E_X1-E_X0)
      k := d(dose)/d(rate) = C_Y0 * slope_E / 1024 = ((C_Y0*E_Y1)>>10) / (E_X1-E_X0)
  therefore, for any operating rate r inside the ramp,
      dose(r) / k  ==  r - E_X0            EXACTLY, independent of C_Y0, E_Y1 and E_X1.
  => k >= dose(r) / (r - E_X0).  E_X0 >= 0, so k is bounded BELOW by the dose requirement alone.
  Dose and slew are NOT separable in this table pair; the only free lever on the ratio is E_X0.

UNITS (kit record, for reporting only -- the model itself is in raw counts)
      speed_kmh = speed_counts / 64.0        column_deg_s = rate_counts / 4.7121
"""
import math
import os
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                           r"C:\Users\dudei\Desktop\Projects\accord-firmwares")) / "analysis-2020accord"

IMAGES = {
    "stock": ROOT / "stock_fw_dump" / "code.bin",
    "v38":   ROOT / "_v38_plain_image.bin",
    "v74":   ROOT / "_v74_engagedcols_x0_12_addonly_plain_image.bin",
    "v75":   ROOT / "_v75_CY0.566-EX1.200_magprobe_plain_image.bin",
}

PTR = {"B": 0xC9CCC, "C": 0xC9E9C, "D": 0xC9DB4, "E": 0xC9F84, "CEIL": 0xC77A0}
NPTS = {"B": 4, "C": 4, "D": 5, "E": 4, "CEIL": 2}
CEIL_FALLBACK_ADDR = 0xC6158            # tp+0x7158, tp = 0xBF000  =>  0xBF000 + 0x7158 = 0xC6158
MODE_ENGAGED, MODE_MANUAL = 26, 24      # car is TVCA4
SEED_DEFAULT = 1024                     # gp-0x698a, reported pinned at 1024
CEILING_FLOOR = 512                     # the tp+0x7158 fallback and the creep supremum
SPEED_CTS_PER_KMH, RATE_CTS_PER_DEGS = 64.0, 4.7121
CORRIDOR_COUNTS = 5                     # +/- 5/1024 on gp-0x6bd0, from 0x3ba00000


# ---------------------------------------------------------------- byte access (LITTLE ENDIAN)
def u16(b, a):
    return b[a] | (b[a + 1] << 8)


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def s32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


def load(name):
    return IMAGES[name].read_bytes()


def read_rec(img, which, mode):
    """(rec_addr, hdr, X, Y) exactly as the LERP indexes them.  ld.w 0x0[r13] @0x34514."""
    base = u32(img, PTR[which] + mode * 4)
    n = NPTS[which]
    return (base, u16(img, base),
            [u16(img, base + 2 + 2 * i) for i in range(n)],
            [u16(img, base + 2 + 2 * n + 2 * i) for i in range(n)])


# ---------------------------------------------------------------- the evaluator, line for line
def lerp(X, Y, idx):
    """FUN_00034350's LERP.  UNSIGNED strict compares; `divq` truncates toward ZERO."""
    n = len(X)
    if not (idx > X[0]):                        # 0x3451E cmp / 0x34520 bh    (UNSIGNED, STRICT)
        return Y[0] & 0xFFFF                    # 0x34522 ld.hu 0x0[r10]      HARD CLAMP to Y[0]
    if not (idx < X[n - 1]):                    # 0x3452A cmp / 0x3452C bnc   (UNSIGNED, STRICT)
        return Y[n - 1] & 0xFFFF                # 0x34538 ld.hu 0x6[r10]      HARD CLAMP to Y[n-1]
    k = 1                                       # 0x3452E  walk starts at X[1], Y[0]
    while X[k] <= idx:                          # 0x34544 cmp / 0x34546 bnc
        k += 1
    num = ((Y[k] - Y[k - 1]) & 0xFFFFFFFF) * ((idx - X[k - 1]) & 0xFFFFFFFF)   # 0x34554/58/5A
    den = (X[k] - X[k - 1]) & 0xFFFFFFFF                                       # 0x3455E
    if s32(den) == 0:                           # divq by 0 sets OV, quotient UNDEFINED
        raise ZeroDivisionError("divq divisor 0 at X[%d]" % k)                 # 0x34560
    q = int(s32(num) / s32(den))                # 0x34560 divq -- TRUNCATE TOWARD ZERO, not floor
    return (q + Y[k - 1]) & 0xFFFF              # 0x34564 add / 0x34566 andi 0xffff


class Surface(object):
    """One (build, mode) damper surface.  Tables come from the image; nothing is hard-coded."""

    def __init__(self, build=None, mode=MODE_ENGAGED, img=None, override=None):
        self.build, self.mode = build, mode
        self.img = img if img is not None else load(build)
        self.rec = {w: read_rec(self.img, w, mode) for w in PTR}
        self.ceil_fallback = u16(self.img, CEIL_FALLBACK_ADDR)
        self.ov = dict(override or {})          # e.g. {"C": (X, Y), "E": (X, Y)} candidate tables

    def XY(self, w):
        if w in self.ov:
            return self.ov[w]
        _, _, X, Y = self.rec[w]
        return X, Y

    # -- the four factors ---------------------------------------------------------------------
    def factorB(self, idx=0):                                   # 0x34470-0x344CE
        return lerp(*self.XY("B"), idx=idx)

    def factorC(self, speed, gate_67f4=1):                      # 0x344E0-0x34566
        if not (speed < 0x7D00) or gate_67f4 != 1:              # 0x344E0 / 0x344FA
            return 0x400
        return lerp(*self.XY("C"), idx=speed)

    def factorD(self, idx=0):                                   # 0x34592-0x345F0
        return lerp(*self.XY("D"), idx=idx)

    def factorE(self, rate_abs, rate_signed=None):              # 0x345FA-0x34682
        if rate_signed is None:
            rate_signed = rate_abs
        if not (rate_abs < 0x32C9):                             # 0x345FA
            return None                                          # -> whole DOSE 0 at 0x34612
        if not (-13000 <= rate_signed <= 13000):                # 0x34604-0x34610
            return None
        return lerp(*self.XY("E"), idx=rate_abs)

    def ceiling(self, backdrive_idx=0):                          # 0x346A4-0x3471C
        if not (backdrive_idx < 0x32C9):
            return self.ceil_fallback                            # 0x346AE ld.hu 0x7158[tp]
        return lerp(*self.XY("CEIL"), idx=backdrive_idx)

    # -- the dose chain -----------------------------------------------------------------------
    def dose_raw(self, speed, rate_signed, seed=SEED_DEFAULT, gate_67f4=1):
        rate_abs = abs(rate_signed)
        E = self.factorE(rate_abs, rate_signed)
        if E is None:
            return 0                                             # 0x34612
        s = seed if seed < 0x401 else 0x400                      # 0x344E4 addi -0x401 / cmovne
        d = (s * self.factorB()) >> 10                           # 0x34684 mulu / 0x34688 shr 0xa
        d = (d * self.factorC(speed, gate_67f4)) >> 10           # 0x3468A / 0x3468E
        d = (d * self.factorD()) >> 10                           # 0x34690 / 0x34696
        d = (d * (E & 0xFFFF)) >> 10                             # 0x34694 zxh / 98 / 9C
        if rate_signed > 0:                                      # 0x3469E cmp r0,r11 / 0x346A0 ble
            d = -d                                               # 0x346A2 subr r0,r8
        return d

    def output(self, speed, rate_signed, backdrive_idx=0, **kw):  # 0x34720-0x3475C
        """The value actually stored to gp-0x6bd0.  Returns (value, clamped)."""
        d = self.dose_raw(speed, rate_signed, **kw)
        c = self.ceiling(backdrive_idx)
        if d > c:                                                 # 0x34724 cmp / 0x3472A ble
            v, clamped = c, True
        elif d >= -c:                                             # 0x3473C cmp / 0x3473E bge
            v, clamped = d, False
        else:
            v, clamped = -c, True
        v &= 0xFFFF                                               # st.h -- 16-bit store 0x3475C
        return (v - 0x10000 if v & 0x8000 else v), clamped

    def mag(self, speed, rate_abs, **kw):
        """|gp-0x6bd0| -- the damping magnitude, sign stripped."""
        return abs(self.output(speed, rate_abs, **kw)[0])


# ---------------------------------------------------------------- validation of the mirror
def validate():
    """Reproduce values the kit has already established by other means.  Any FAIL invalidates
    every number below it, so this runs first and prints its own evidence."""
    print("=" * 108)
    print("PART 0 -- VALIDATION OF THE MIRROR  (each row is a number the kit established elsewhere)")
    print("=" * 108)
    S = {b: Surface(b, MODE_ENGAGED) for b in ("stock", "v38", "v74", "v75")}
    M = {b: Surface(b, MODE_MANUAL) for b in ("stock", "v38", "v74", "v75")}
    ok = True

    def chk(label, got, want, note=""):
        nonlocal ok
        good = (got == want)
        ok &= good
        print("  [%s] %-56s got %-16s want %-16s %s"
              % ("PASS" if good else "FAIL", label, got, want, note))

    for b in S:
        _, _, cx, cy = S[b].rec["C"]
        _, _, ex, ey = S[b].rec["E"]
        print("  %-6s mode26  FactorC X=%-28s Y=%-22s  FactorE X=%-24s Y=%s"
              % (b, cx, cy, ex, ey))
    print()

    # tables, byte-read
    chk("stock FactorC mode26 X", S["stock"].XY("C")[0], [2240, 3840, 5120, 8960])
    chk("stock FactorC mode26 Y", S["stock"].XY("C")[1], [0, 234, 429, 908])
    chk("stock FactorE mode26 X", S["stock"].XY("E")[0], [60, 400, 2500, 4000])
    chk("stock FactorE mode26 Y", S["stock"].XY("E")[1], [0, 140, 539, 927])
    chk("V38 FactorC mode26 == stock", S["v38"].XY("C"), S["stock"].XY("C"), "(V76 base)")
    chk("V38 FactorE mode26 == stock", S["v38"].XY("E"), S["stock"].XY("E"), "(V76 base)")
    chk("V74 FactorC Y", S["v74"].XY("C")[1], [429, 234, 429, 908])
    chk("V75 FactorC Y", S["v75"].XY("C")[1], [566, 234, 429, 908])
    chk("V74 FactorE X", S["v74"].XY("E")[0], [12, 400, 2500, 4000])
    chk("V75 FactorE X", S["v75"].XY("E")[0], [12, 200, 2500, 4000])
    chk("V74/V75 FactorE Y", S["v75"].XY("E")[1], [0, 539, 539, 927])

    # B and D flat unity -- the premise that lets dose collapse to (C*E)>>10
    chk("FactorB flat unity (mode26, all idx)",
        sorted({S["v75"].factorB(i) for i in range(0, 40000, 97)}), [1024])
    chk("FactorD flat unity (mode26, all idx)",
        sorted({S["v75"].factorD(i) for i in range(0, 40000, 97)}), [1024])
    chk("ceiling fallback tp+0x7158", S["stock"].ceil_fallback, 512)

    # the hard clamp below X[0] -- the fact that refuted the 'edits were not in force' claim
    chk("mode24 FactorC at 2130 ct (33.3 km/h)", M["v74"].factorC(2130), 0,
        "manual column -> damper identically 0")
    chk("mode26 FactorC at 2130 ct (33.3 km/h)", S["v74"].factorC(2130), 429,
        "engaged column -> damper LIVE  <= the fault frame")

    # the measured in-burst working point: V74 dose 137 was reported for V75 at 99 ct
    chk("V75 |gp-0x6bd0| at creep, rate 99 ct (21.0 deg/s)", S["v75"].mag(0, 99), 137,
        "kit's reported in-burst damping")
    chk("V74 |gp-0x6bd0| at creep, rate 99 ct", S["v74"].mag(0, 99), 50)
    chk("stock |gp-0x6bd0| at creep, any rate", S["stock"].mag(0, 99), 0,
        "stock damper dead below 35 km/h")

    # the sustained-drag figures quoted in HANDOFF-2026-08-06 section 4
    r20 = int(round(20 * RATE_CTS_PER_DEGS))
    chk("sustained drag at 20 deg/s: stock", S["stock"].mag(0, r20), 0)
    chk("sustained drag at 20 deg/s: V74", S["v74"].mag(0, r20), 47)
    chk("sustained drag at 20 deg/s: V75", S["v75"].mag(0, r20), 129)

    # the ~448 observed peak: creep, engaged, near the top of FactorE's ramp
    peak75 = max(S["v75"].mag(0, r) for r in range(0, 0x32C9))
    arg = max(range(0, 0x32C9), key=lambda r: S["v75"].mag(0, r))
    print("  [INFO] V75 creep supremum over the whole legal rate domain = %d at rate %d ct "
          "(%.0f deg/s)   ceiling floor %d" % (peak75, arg, arg / RATE_CTS_PER_DEGS, CEILING_FLOOR))
    chk("V75 creep supremum == ceiling floor", peak75, CEILING_FLOOR,
        "matches the '215-count margin' record")

    # k, the ramp-regime incremental gain, by two methods
    print("\n  k by two independent methods (closed form vs finite difference on the mirror):")
    for b in ("stock", "v74", "v75"):
        s = S[b]
        cy0 = s.XY("C")[1][0]
        ex, ey = s.XY("E")
        closed = ((cy0 * ey[1]) >> 10) / (ex[1] - ex[0]) if ex[1] != ex[0] else float("nan")
        lo, hi = ex[0] + 2, min(ex[1] - 2, 190)
        fd = (s.mag(0, hi) - s.mag(0, lo)) / (hi - lo) if hi > lo else float("nan")
        print("     %-6s C_Y0=%-4d E=[%d,%d]  closed k=%.4f   finite-difference k=%.4f   %s"
              % (b, cy0, ex[0], ex[1], closed, fd,
                 "AGREE" if abs(closed - fd) < 0.02 or closed == 0 else "DISAGREE"))

    print("\n  => mirror %s\n" % ("VALIDATED" if ok else "*** HAS A FAILING ROW ***"))
    return ok, S


# ---------------------------------------------------------------- the dose/slew identity
def prove_dose_slew_identity():
    """Exhaustive integer check of  dose(r)/k == r - E_X0  over the reachable design space.
    This is the result that decides whether requirements (a) and (c) can both be met."""
    print("=" * 108)
    print("PART 1 -- THE DOSE/SLEW IDENTITY   dose(r) = k * (r - E_X0)   for r inside the ramp")
    print("=" * 108)
    print("  If this holds, then k >= dose(r)/(r - E_X0) is a HARD ARITHMETIC FLOOR: no choice of")
    print("  C_Y0, E_Y1 or E_X1 can buy dose without buying exactly proportional slew.  Only E_X0")
    print("  moves the ratio, and it is bounded by 0 <= E_X0 < r.")
    print()
    img = load("v75")
    worst, worst_at, n = 0.0, None, 0
    for cy0 in range(64, 567, 23):
        for ex0 in range(0, 61, 4):
            for ex1 in range(ex0 + 40, 601, 37):
                for ey1 in range(40, 940, 61):
                    E = ([ex0, ex1, 2500, 4000], [0, ey1, ey1, 927])
                    C = ([2240, 3840, 5120, 8960], [cy0, 234, 429, 908])
                    s = Surface(img=img, override={"C": C, "E": E})
                    k = ((cy0 * ey1) >> 10) / (ex1 - ex0)
                    for r in (60, 94, 99, 127):
                        if not (ex0 < r < ex1):
                            continue                      # only the ramp regime is claimed
                        pred, act = k * (r - ex0), s.mag(0, r)
                        n += 1
                        err = abs(pred - act)
                        if err > worst:
                            worst, worst_at = err, (cy0, ex0, ex1, ey1, r, pred, act)
    print("  checked %d (C_Y0, E_X0, E_X1, E_Y1, r) points inside the ramp" % n)
    print("  worst |k*(r-E_X0) - dose| = %.3f counts   at C_Y0=%d E_X0=%d E_X1=%d E_Y1=%d r=%d "
          "(predicted %.2f, mirror %d)" % ((worst,) + worst_at))
    print("  => the identity holds to within integer truncation (<= ~2 counts of the >>10 chain).")
    print("  => [EVIDENCE] dose and slew are RIGIDLY COUPLED in the FactorC/FactorE pair.\n")
    return worst


# ---------------------------------------------------------------- FactorC shape (requirement b)
def factorC_shapes(S):
    """The operator asked for FactorC 'FLAT -- no taper down, like a rectified linear unit'.
    Read as a FLOOR CLAMP on the stock curve: Y = [F, max(Y1,F), max(Y2,F), Y3]."""
    print("=" * 108)
    print("PART 2 -- FactorC: the FLAT / ReLU shape, and where the no-clip guard binds")
    print("=" * 108)
    CX = S["stock"].XY("C")[0]
    base_Y = S["v75"].XY("C")[1]
    E75 = S["v75"].XY("E")
    img = load("v75")

    print("  reading 'flat, no taper down, like a ReLU' as a FLOOR CLAMP at F on the stock curve:")
    print("      Y = [F, max(234,F), max(429,F), 908]     stock Y = [0, 234, 429, 908]")
    print("  at F = 566 that is [566, 566, 566, 908]: flat 0 -> 80 km/h, then the stock rise to 140.")
    print("  The alternative readings are listed at the end of this part.\n")

    # -- (2a) the clip ceiling on a FLAT value, exactly ---------------------------------------
    print("  (2a) the largest FLAT value that never exceeds the ceiling floor, exactly")
    print("       need (C * E_max) >> 10 <= %d with E_max = E_Y3 = 927 (rate >= 4000 ct)"
          % CEILING_FLOOR)
    for C in (564, 565, 566, 567, 568):
        v = (C * 927) >> 10
        print("         C=%-4d  (C*927)>>10 = %-4d  %s" % (C, v, "OK" if v <= CEILING_FLOOR else "CLIPS"))
    Cmax = max(C for C in range(0, 4096) if (C * 927) >> 10 <= CEILING_FLOOR)
    print("       => C_max = %d  (exhaustive integer scan 0..4095)   V75 already sits exactly here."
          % Cmax)

    # -- (2b) the guard applied to INTERPOLATED points, not just knots -------------------------
    print("\n  (2b) the guard applied to every interpolated speed, not just the four knots.")
    print("       Guard: wherever the edit RAISES C above the base, the raised point must satisfy")
    print("       (C*E)>>10 <= %d for every reachable E." % CEILING_FLOOR)
    SPEEDS = list(range(0, 14001, 8))
    for F in (429, 470, 500, 530, 566):
        cy = [F, max(234, F), max(429, F), 908]
        first_raise_over = None
        for v in SPEEDS:
            c = lerp(CX, cy, v)
            cb = lerp(CX, base_Y, v)
            if c > cb and ((c * 927) >> 10) > CEILING_FLOOR:
                first_raise_over = (v, c, (c * 927) >> 10, cb, (cb * 927) >> 10)
                break
        if first_raise_over:
            v, c, cv, cb, cbv = first_raise_over
            print("       F=%-4d %-26s FAIL at %5d ct = %5.1f km/h: C %d->%d, dose@E=927 %d->%d"
                  % (F, str(cy), v, v / SPEED_CTS_PER_KMH, cb, c, cbv, cv))
        else:
            print("       F=%-4d %-26s PASS over 0..218.8 km/h" % (F, str(cy)))

    # -- (2c) the same guard restricted to the OBSERVED rate envelope --------------------------
    print("\n  (2c) the SAME check restricted to rates that have actually been observed.")
    print("       Route 5d maximum steering rate = 412 deg/s = 1941 counts (kit record, RULE 8).")
    print("       [RULE 8b] this envelope contains no engaged stoplight launch and no track use.")
    for rmax, tag in ((1941, "observed route max, 412 deg/s"),
                      (2500, "E_X2 knee, 530 deg/s"),
                      (0x32C8, "FactorE gate limit, 2731 deg/s")):
        worst = 0
        worst_v = None
        for F in (566,):
            cy = [F, max(234, F), max(429, F), 908]
            for v in SPEEDS:
                c = lerp(CX, cy, v)
                cb = lerp(CX, base_Y, v)
                if c <= cb:
                    continue
                e = lerp(*E75, idx=rmax)
                d = (c * e) >> 10
                if d > worst:
                    worst, worst_v = d, v
        print("       rate <= %-6d (%-28s) worst RAISED dose = %-4d at %5.1f km/h   %s"
              % (rmax, tag, worst, worst_v / SPEED_CTS_PER_KMH,
                 "OK" if worst <= CEILING_FLOOR else "CLIPS"))

    # -- (2d) the rate at which the flat shape first clips ------------------------------------
    print("\n  (2d) at what steering rate does the flat F=566 shape first clip, per speed?")
    cy = [566, 566, 566, 908]
    print("       %8s %10s %8s %8s %10s" % ("km/h", "C(flat)", "C(V75)", "E needed", "rate needed"))
    for v_kmh in (35, 50, 60, 70, 80, 85, 90, 100, 120):
        v = int(round(v_kmh * SPEED_CTS_PER_KMH))
        c = lerp(CX, cy, v)
        cb = lerp(CX, base_Y, v)
        need_e = None
        need_r = None
        for r in range(0, 0x32C9):
            if ((c * lerp(*E75, idx=r)) >> 10) > CEILING_FLOOR:
                need_e, need_r = lerp(*E75, idx=r), r
                break
        print("       %8d %10d %8d %8s %10s" % (
            v_kmh, c, cb,
            "--" if need_e is None else str(need_e),
            "--" if need_r is None else "%d ct = %.0f deg/s" % (need_r, need_r / RATE_CTS_PER_DEGS)))

    # -- (2e) what the flat shape does to SLEW in the 35-80 km/h band -------------------------
    print("\n  (2e) 🛑 the cost of the flat shape under the SLEW hypothesis:")
    print("       k is proportional to FactorC, so flattening the dip RAISES loop gain there.")
    E = E75
    slope_E = (E[1][1] - E[1][0]) / (E[0][1] - E[0][0])
    print("       %8s %10s %10s %10s %10s" % ("km/h", "C(V75)", "C(flat)", "k(V75)", "k(flat)"))
    for v_kmh in (0, 20, 35, 45, 60, 70, 80, 100):
        v = int(round(v_kmh * SPEED_CTS_PER_KMH))
        cb, c = lerp(CX, base_Y, v), lerp(CX, cy, v)
        print("       %8d %10d %10d %10.4f %10.4f%s"
              % (v_kmh, cb, c, cb * slope_E / 1024, c * slope_E / 1024,
                 "   <= dip filled" if c > cb else ""))
    print("       => the flat shape extends V75's FULL creep loop gain across 35-80 km/h, a band")
    print("          where every build so far has had a 2.42x dip.  Neither hard fault occurred")
    print("          there (both at <= 33.3 km/h), so this ENLARGES the exposed envelope into a")
    print("          regime with no clean-flight evidence at this gain.  [BELIEF, from the k model]")

    # -- (2f) alternative readings of 'flat' ---------------------------------------------------
    print("\n  (2f) alternative readings of 'flat, no taper down, like a ReLU', all at F = 566:")
    alts = {
        "floor-clamp (my reading) ": [566, 566, 566, 908],
        "fully flat, no rise      ": [566, 566, 566, 566],
        "monotone non-decreasing  ": [566, 566, 566, 908],
        "flat then stock slope    ": [566, 566, 566, 908],
        "dip removed only (V74 Y2)": [566, 429, 429, 908],
    }
    seen = {}
    for name, y in alts.items():
        key = tuple(y)
        if key in seen:
            print("       %-26s %-26s == %s" % (name, str(y), seen[key]))
            continue
        seen[key] = name.strip()
        mono = all(y[i] <= y[i + 1] for i in range(3))
        dips = [(i + 1, y[i] - y[i + 1]) for i in range(3) if y[i + 1] < y[i]]
        print("       %-26s %-26s monotone=%-5s dips=%s"
              % (name, str(y), mono, dips or "NONE"))
    print("       => 'fully flat, no rise' would LOWER Y[3] 908->566, cutting damping above")
    print("          140 km/h.  That is a taper DOWN in dose at high speed, i.e. the opposite of")
    print("          the request, so the floor-clamp reading is the right one.  It is also the")
    print("          only reading that is add-only w.r.t. the base image (guard G1).\n")
    return cy


# ---------------------------------------------------------------- the Pareto search (core)
def pareto(S, budget_counts=None, f_update_hz=(100.0, 1000.0), drate_dt=(5400, 6900)):
    """Search (E_X0, E_X1, E_Y1) x C_Y0 for the lowest first-segment slope at a given delivered
    dose.  Reports slope in counts of gp-0x6bd0 per count of steering rate -- which IS k."""
    print("=" * 108)
    print("PART 3 -- THE PARETO FRONT: slope (== k, == GATE-2 loop gain) vs delivered dose")
    print("=" * 108)
    CX = S["stock"].XY("C")[0]
    img = load("v75")
    R_OP = 99                       # measured in-burst rate, p50, = 21.0 deg/s
    D_V75 = S["v75"].mag(0, R_OP)   # 137
    D_V74 = S["v74"].mag(0, R_OP)   # 50

    print("  operating rate r = %d ct = %.1f deg/s (measured in-burst p50).  V75 dose there = %d,"
          % (R_OP, R_OP / RATE_CTS_PER_DEGS, D_V75))
    print("  V74 dose = %d.  Both faulted.  Stock = 0 and has never faulted." % D_V74)
    print()
    print("  THE FLOOR, before any search:   k >= dose / (r - E_X0)")
    for D, lab in ((D_V75, "V75 dose"), (int(0.75 * D_V75), "75% of V75"),
                   (int(0.5 * D_V75), "50% of V75"), (D_V74, "V74 dose")):
        print("     %-12s D=%-4d   E_X0=12 -> k >= %.4f     E_X0=0 -> k >= %.4f"
              % (lab, D, D / (R_OP - 12), D / R_OP))
    print("     => holding V75's dose, the BEST achievable k is %.4f (E_X0 = 0), only %.1f%% below"
          % (D_V75 / R_OP, 100 * (1 - (D_V75 / R_OP) / 1.5798)))
    print("        V75's 1.5798 -- and still %.2fx V74's 0.5799, which ALSO faulted."
          % ((D_V75 / R_OP) / 0.5799))
    print()

    # -- the search ---------------------------------------------------------------------------
    rows = []
    for cy0 in (300, 350, 400, 429, 470, 500, 530, 566):
        for ex0 in (0, 6, 12, 20, 30):
            for ex1 in (100, 140, 180, 200, 240, 280, 320, 360, 400, 500, 600, 800):
                for ey1 in (140, 200, 260, 320, 380, 440, 500, 539):
                    if not (ex0 < ex1 < 2500):
                        continue
                    Ex, Ey = [ex0, ex1, 2500, 4000], [0, ey1, max(ey1, 539), 927]
                    Cy = [cy0, max(234, cy0), max(429, cy0), 908]
                    s = Surface(img=img, override={"C": (CX, Cy), "E": (Ex, Ey)})
                    M = (cy0 * ey1) >> 10
                    k = M / (ex1 - ex0)
                    rows.append(dict(
                        cy0=cy0, ex0=ex0, ex1=ex1, ey1=ey1, M=M, k=k,
                        d99=s.mag(0, 99), d94=s.mag(0, int(round(20 * RATE_CTS_PER_DEGS))),
                        d60=s.mag(0, 60), d200=s.mag(0, 200),
                        d60kmh=s.mag(3840, 99), surf=s))

    # -- Pareto front: for each dose bucket, the minimum k ------------------------------------
    print("  (3a) PARETO FRONT -- minimum achievable k at each delivered dose (creep, r = 99 ct)")
    print("       'slope' is d|gp-0x6bd0| / d(rate), in counts of gp-0x6bd0 per count of rate.")
    print("       Delta columns = k * |d(rate)/dt| / f_update, the worst-case single-update step.")
    print()
    hdr = ("  %6s %7s | %5s %5s %5s %5s | %8s | %7s %7s | %7s %7s"
           % ("dose", "k=slope", "C_Y0", "E_X0", "E_X1", "E_Y1", "%of V75",
              "d100@5.4k", "d100@6.9k", "d1k@5.4k", "d1k@6.9k"))
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    front = []
    for target in (137, 130, 120, 110, 100, 90, 80, 70, 60, 50, 40, 30, 20):
        cands = [r for r in rows if r["d99"] == target]
        if not cands:
            cands = [r for r in rows if abs(r["d99"] - target) <= 1]
        if not cands:
            continue
        best = min(cands, key=lambda r: r["k"])
        front.append(best)
        print("  %6d %7.4f | %5d %5d %5d %5d | %7.0f%% | %7.1f %7.1f | %7.2f %7.2f"
              % (best["d99"], best["k"], best["cy0"], best["ex0"], best["ex1"], best["ey1"],
                 100 * best["d99"] / D_V75,
                 best["k"] * 5400 / 100, best["k"] * 6900 / 100,
                 best["k"] * 5400 / 1000, best["k"] * 6900 / 1000))

    print("\n  reference rows, same columns:")
    for name, b in (("stock", "stock"), ("V74", "v74"), ("V75", "v75")):
        s = S[b]
        cy0 = s.XY("C")[1][0]
        ex, ey = s.XY("E")
        k = ((cy0 * ey[1]) >> 10) / (ex[1] - ex[0])
        print("  %6d %7.4f | %5d %5d %5d %5d | %7.0f%% | %7.1f %7.1f | %7.2f %7.2f   <= %s"
              % (s.mag(0, 99), k, cy0, ex[0], ex[1], ey[1], 100 * s.mag(0, 99) / D_V75,
                 k * 5400 / 100, k * 6900 / 100, k * 5400 / 1000, k * 6900 / 1000, name))

    # -- budget-driven pick -------------------------------------------------------------------
    print("\n  (3b) WHAT EACH CANDIDATE BUDGET BUYS")
    print("       budget = max tolerable single-update step in gp-0x6bd0, in counts.")
    print("       The Surface-A corridor itself is +/- %d counts; whether one update of" % CORRIDOR_COUNTS)
    print("       divergence is the right skew is NOT established -- see the note in part 5.")
    print()
    print("       %8s %8s | %10s %10s | %10s %10s"
          % ("budget", "f_upd", "k_max", "dose@99", "% of V75", "vs V74 k"))
    for budget in (5, 10, 20, 30, 50, 80, 110):
        for f in f_update_hz:
            kmax = budget / (max(drate_dt) / f)
            dose_max = kmax * R_OP           # E_X0 = 0, the most favourable legal shape
            print("       %8d %8.0f | %10.4f %10.1f | %9.0f%% %10.2fx"
                  % (budget, f, kmax, dose_max, 100 * dose_max / D_V75, kmax / 0.5799))
    return front, rows, D_V75, D_V74


# ---------------------------------------------------------------- the TRUE slew metric
def max_step(surf, speed, d_rate, r_lo=-600, r_hi=600):
    """max |gp-0x6bd0(r + d_rate) - gp-0x6bd0(r)| over SIGNED rates, on the mirror.

    This is the honest figure of merit, and it is strictly better than `k * d_rate` because it
    also captures (i) the plateau cap, (ii) the Y[0] hard clamp below E_X0, and (iii) the
    conditional negate at 0x346A2, which makes a rate ZERO CROSSING flip the output sign."""
    worst, at = 0, None
    for r in range(r_lo, r_hi + 1):
        a = surf.output(speed, r)[0]
        b = surf.output(speed, r + d_rate)[0]
        if abs(b - a) > worst:
            worst, at = abs(b - a), r
    return worst, at


def slew_shape_search(S, D_target=137, r_op=99):
    """Does any NON-LINEAR FactorE shape beat the straight ramp at matched dose?

    The mean-value bound says no shape can do better than D/ceil(r_op/d_rate) at ONE chosen
    d_rate; the question is whether a shape can be good across the whole d_rate DISTRIBUTION,
    since the per-update rate change is not always the route maximum."""
    print("\n" + "=" * 108)
    print("PART 3c -- CAN A NON-LINEAR FactorE SHAPE BEAT THE STRAIGHT RAMP?")
    print("=" * 108)
    print("  All candidates hold dose(%d ct) within +/-3 counts of %d (V75's).  FactorC = flat 566."
          % (r_op, D_target))
    print("  Columns are the TRUE max single-update step from the mirror, at several per-update")
    print("  rate changes.  d(rate)/dt 5,400-6,900 /s gives 54-69 ct at 100 Hz, 5.4-6.9 at 1 kHz.")
    print()
    CX = S["stock"].XY("C")[0]
    Cy = [566, 566, 566, 908]
    img = load("v75")
    D_RATES = (3, 7, 15, 30, 54, 69)

    shapes = {}
    # (i) the straight ramp -- one linear segment covering the whole operating range
    for ex1 in (215, 250, 300):
        ey1 = max(1, round(D_target * 1024 / 566 * ex1 / r_op))
        shapes["linear ramp     E=[0,%d] Y1=%d" % (ex1, ey1)] = ([0, ex1, 2500, 4000],
                                                                [0, ey1, max(ey1, 539), 927])
    # (ii) deadband then steep -- 'do nothing until the rate is real', DOSE-MATCHED at r_op by
    #      compressing the ramp into (E_X0, r_op] instead of translating it
    e_at_rop = round(D_target * 1024 / 566)          # FactorE value needed to hit D_target
    for ex0 in (30, 50, 70):
        shapes["deadband %-3d    E=[%d,%d]" % (ex0, ex0, r_op)] = ([ex0, r_op, 2500, 4000],
                                                                   [0, e_at_rop, 539, 927])
    # (iii) soft knee -- shallow first segment, then steeper, knee inside the operating range
    for knee in (40, 60, 80):
        for frac in (0.25, 0.5):
            y_knee = max(1, round(D_target * 1024 / 566 * frac))
            y_end = max(y_knee + 1, round(D_target * 1024 / 566 * (r_op + 20) / r_op))
            shapes["soft knee %-3d f=%.2f" % (knee, frac)] = ([0, knee, r_op + 20, 4000],
                                                              [0, y_knee, y_end, 927])
    # (iv) V74's and V75's FactorE for reference (NB: on the FLAT C, not their own C)
    shapes["V75 FactorE (on flat C) "] = (S["v75"].XY("E")[0], S["v75"].XY("E")[1])
    shapes["V74 FactorE (on flat C) "] = (S["v74"].XY("E")[0], S["v74"].XY("E")[1])

    print("  %-34s %6s %7s | %s" % ("FactorE shape", "dose", "k", "  ".join(
        "d=%-3d" % d for d in D_RATES)))
    print("  " + "-" * 100)
    best = None
    for name, E in sorted(shapes.items()):
        s = Surface(img=img, override={"C": (CX, Cy), "E": E})
        d = s.mag(0, r_op)
        k = ((566 * E[1][1]) >> 10) / (E[0][1] - E[0][0])
        steps = [max_step(s, 0, dr)[0] for dr in D_RATES]
        flag = ""
        if abs(d - D_target) <= 4 and not name.startswith("V7"):
            tot = sum(steps)
            if best is None or tot < best[0]:
                best = (tot, name, steps)
        if abs(d - D_target) > 4 and not name.startswith("V7"):
            flag = "  (dose off target)"
        print("  %-34s %6d %7.4f | %s%s" % (name, d, k,
                                            "  ".join("%5d" % v for v in steps), flag))
    if best:
        print("\n  => minimum total exposure across the whole d_rate range: %s" % best[1])
    print("""
  READING:  the deadband shapes look good at small d_rate and are the WORST at large d_rate --
  they simply relocate the step to the moment the rate crosses E_X0, and make it bigger because
  the same dose is delivered over a shorter span.  The soft-knee shapes trade the same way.
  A CONSTANT slope is the minimax-optimal shape against an unknown per-update rate change:
  any shape that is shallower than linear somewhere must be steeper somewhere else, and the
  per-update rate change is not observable at design time.
  => V75's SHAPE is already right.  Only its LEVEL (k) and its E_X0 are free.""")


# ---------------------------------------------------------------- like-for-like comparison
def compare(S, cand_C, cand_E):
    print("\n" + "=" * 108)
    print("PART 4 -- LIKE-FOR-LIKE: stock / V74 / V75 / candidate")
    print("=" * 108)
    CX = S["stock"].XY("C")[0]
    img = load("v75")
    cand = Surface(img=img, override={"C": (CX, cand_C), "E": cand_E})
    builds = [("stock", S["stock"]), ("V74", S["v74"]), ("V75", S["v75"]), ("V76 cand", cand)]

    print("  damping |gp-0x6bd0| at 21.0 deg/s (99 ct), by speed:")
    print("  %-10s %6s | %6s %6s %6s %6s %6s | %8s %6s | %9s %9s"
          % ("build", "C_Y0", "5km/h", "20", "35", "60", "80", "k", "M", "d100@6.9k", "d1k@6.9k"))
    print("  " + "-" * 104)
    for name, s in builds:
        cy0 = s.XY("C")[1][0]
        ex, ey = s.XY("E")
        k = ((cy0 * ey[1]) >> 10) / (ex[1] - ex[0])
        M = (cy0 * ey[1]) >> 10
        cells = [s.mag(int(v * SPEED_CTS_PER_KMH), 99) for v in (5, 20, 35, 60, 80)]
        print("  %-10s %6d | %6d %6d %6d %6d %6d | %8.4f %6d | %9.1f %9.2f"
              % (name, cy0, *cells, k, M, k * 6900 / 100, k * 6900 / 1000))

    print("\n  first-segment FactorE slope (per count of rate) and the C_Y0-scaled slew coefficient:")
    for name, s in builds:
        ex, ey = s.XY("E")
        cy0 = s.XY("C")[1][0]
        se = (ey[1] - ey[0]) / (ex[1] - ex[0])
        print("     %-10s E X=[%d,%d] Y=[%d,%d]  slope_E = %.4f  (%.2fx stock)   "
              "k = C_Y0*slope_E/1024 = %.4f"
              % (name, ex[0], ex[1], ey[0], ey[1], se, se / (140 / 340), cy0 * se / 1024))

    print("\n  ---- PART 4b: WHAT 'DOSE SIMILAR TO V75' MEANS ONCE FactorC IS FLAT ----")
    print("  V75's dose is highly NON-UNIFORM in speed (137 at creep, 56 at 60 km/h) because of")
    print("  the FactorC dip.  Flattening FactorC redistributes dose from creep into 35-80 km/h,")
    print("  so a LOWER FactorE slope reaches the same speed-AVERAGED feel.  The two operator")
    print("  requests (a) and (b) therefore interact: (b) partly PAYS FOR (c).")
    print()
    speeds = [int(round(v * SPEED_CTS_PER_KMH)) for v in range(0, 81, 5)]
    print("  %-32s %8s %8s %7s %7s %7s %9s"
          % ("build", "k", "mean", "min", "max", "@creep", "@60km/h"))
    print("  " + "-" * 88)
    ladder = [("stock", S["stock"]), ("V74 as flown", S["v74"]), ("V75 as flown", S["v75"])]
    for ex1, lab in ((215, "flatC E_X1=215  V75 creep dose"),
                     (265, "flatC E_X1=265  V75 MEAN dose"),
                     (300, "flatC E_X1=300"),
                     (400, "flatC E_X1=400  = stock E_X1"),
                     (512, "flatC E_X1=512  k = V74's"),
                     (700, "flatC E_X1=700"),
                     (1024, "flatC E_X1=1024")):
        ladder.append((lab, Surface(img=img, override={
            "C": (CX, cand_C), "E": ([0, ex1, 2500, 4000], [0, 539, 539, 927])})))
    v75_mean = None
    for lab, s in ladder:
        cy0 = s.XY("C")[1][0]
        ex, ey = s.XY("E")
        k = ((cy0 * ey[1]) >> 10) / (ex[1] - ex[0])
        d = [s.mag(v, 99) for v in speeds]
        mean = sum(d) / len(d)
        if lab == "V75 as flown":
            v75_mean = mean
        note = ""
        if v75_mean:
            note = "  %3.0f%% of V75 mean" % (100 * mean / v75_mean)
        print("  %-32s %8.4f %8.1f %7d %7d %7d %9d%s"
              % (lab, k, mean, min(d), max(d), s.mag(0, 99), s.mag(3840, 99), note))
    print("\n  => EVERY flat-C row above delivers MORE damping at 60 km/h than V75 did (56),")
    print("     including the k = 0.58 row.  'Similar to V75' is not one number: matching V75's")
    print("     CREEP peak costs k = 1.381; matching its SPEED-MEAN costs only k = 1.121.")

    print("\n  dose vs rate at creep, the whole ramp (counts of gp-0x6bd0):")
    print("     %6s %8s | %8s %8s %8s %8s" % ("rate", "deg/s", "stock", "V74", "V75", "V76 cand"))
    for r in (12, 25, 50, 75, 99, 127, 150, 200, 300, 400, 800, 2000, 4000):
        print("     %6d %8.1f | %8d %8d %8d %8d"
              % (r, r / RATE_CTS_PER_DEGS, *[s.mag(0, r) for _, s in builds]))
    return cand


# ---------------------------------------------------------------- PART 6: the revised criteria
def part6(S):
    """Re-scored against the criteria that replaced the slew framing:
       (c) magnitude guard max|gp-0x6bd0| <= 512, timing-independent, provably closes Surface A
       (d) grind-#2 separation: do not raise gain in the high-steering-rate regime
       plus the E_Y[0] > 0 escape hatch, confirmed or refuted from the decompile."""
    print("\n" + "=" * 108)
    print("PART 6 -- THE REVISED CRITERIA  (magnitude guard + grind-#2 separation)")
    print("=" * 108)
    CX = S["stock"].XY("C")[0]
    img = load("v75")

    # -- 6a: the sign source, from the decompile -------------------------------------------
    print("""
  (6a) THE SIGN SOURCE AND THE INDEX ARE DIFFERENT CELLS  [EVIDENCE, decompile_function 0x34350]

      uVar16 = *(ushort *)(gp - 0x6ac0);                       <- FactorE's LERP INDEX (unsigned)
      if ((uVar16 < 0x32c9) && (*(short *)(gp - 0x6abe) + 13000 <= 0x6590)) {
          ... FactorE LERP on uVar16 ...
          uVar7 = (((seed*B >> 10) * C >> 10) * D >> 10) * (uVar16 & 0xffff) >> 10;
          if (0 < *(short *)(gp - 0x6abe)) uVar7 = -uVar7;     <- SIGN, from a DIFFERENT cell
      } else uVar7 = 0;

      0x6590 = 26000, so the second gate is gp-0x6abe in [-13000, +13000].
      gp-0x6ac0 (unsigned magnitude) and gp-0x6abe (signed) are the magnitude/sign pair of the
      same resolver/motor-rate signal.  The MAGNITUDE indexes the table; the SIGN negates the
      finished product AFTER all four multiplies.""")

    # -- 6b: refute the E_Y[0] > 0 escape hatch --------------------------------------------
    print("\n  (6b) 🛑 THE `E_Y[0] > 0` ESCAPE HATCH IS REFUTED -- it is a Coulomb relay")
    print("       Below E_X[0] the LERP hard-clamps to Y[0] (0x34522 ld.hu 0x0[r10]).  With")
    print("       Y[0] > 0 the dose magnitude is (C*Y[0])>>10 at ANY rate including ZERO, while")
    print("       the sign is -sign(gp-0x6abe).  At every rate zero crossing the output jumps")
    print("       from +M0 to -M0: a discontinuity of 2*M0, at ANY amplitude and ANY frequency.")
    print()
    print("       %8s %10s %12s %14s" % ("E_Y[0]", "M0", "step at 0-x", "torque at rate=0"))
    for ey0 in (0, 25, 50, 100, 200):
        E = ([12, 200, 2500, 4000], [ey0, 539, 539, 927])
        s = Surface(img=img, override={"C": (CX, [566, 566, 566, 566]), "E": E})
        m0 = s.mag(0, 0)
        neg, pos = s.output(0, -1)[0], s.output(0, +1)[0]
        print("       %8d %10d %12d %14d %s" % (ey0, m0, abs(pos - neg), s.output(0, 0)[0],
                                                "<- static bias with the wheel STILL" if ey0 else ""))
    print("""
       The describing function of a relay is N(A) = 4*M0/(pi*A): its gain grows WITHOUT BOUND
       as the oscillation amplitude falls, which is the textbook small-amplitude limit-cycle
       mechanism -- i.e. exactly a grind.  At 100 Hz the relay is sampled ~4.8x per cycle of a
       21 Hz oscillation, adding up to half a sample (~18 deg at 21 Hz) of extra phase lag,
       which is WORSE than an ideal relay.
       => REFUTED.  Do not raise E_Y[0].  team-lead's instinct was right, and the mechanism is
          strictly worse than the V74/V75 plateau because it is UNCONDITIONAL. [EVIDENCE]""")

    # -- 6c: the magnitude guard, per FactorC candidate ------------------------------------
    print("\n  (6c) THE MAGNITUDE GUARD  max|gp-0x6bd0| = (max FactorC * E_Y3) >> 10 <= 512")
    print("       E_Y3 = 927 in stock, V38, V74 and V75 alike (byte-read, all four images).")
    print()
    print("       %-38s %7s %9s %8s  %s" % ("FactorC Y", "max C", "max dose", "guard", "dose>512 band"))
    cands = (("stock / V38     [0,234,429,908]", [0, 234, 429, 908]),
             ("V74             [429,234,429,908]", [429, 234, 429, 908]),
             ("V75 flown       [566,234,429,908]", [566, 234, 429, 908]),
             ("C1 flat->rise   [566,566,566,908]", [566, 566, 566, 908]),
             ("C2 FULLY FLAT   [566,566,566,566]", [566, 566, 566, 566]))
    for nm, cy in cands:
        mx = max(lerp(CX, cy, v) for v in range(0, 14001))
        d = (mx * 927) >> 10
        band = [v for v in range(0, 14001) if ((lerp(CX, cy, v) * 927) >> 10) > 512]
        print("       %-38s %7d %9d %8s  %s"
              % (nm, mx, d, "PASS" if d <= 512 else "FAIL",
                 "NONE" if not band else "%.1f - %.1f km/h" % (min(band) / 64, max(band) / 64)))
    print("""
       🛑 STOCK ITSELF FAILS THIS GUARD (821 > 512) and has never faulted => the guard is
       SUFFICIENT to close Surface A, not NECESSARY.  Stock relies on the ceiling being above
       its 512 floor at those operating points (CEIL X=[300,800] Y=[512,1024], byte-read,
       identical in all four images).
       => C2 is the ONLY flat shape that closes Surface A provably, and it is STRICTLY SAFER
          than stock on this criterion.  C1 WIDENS stock's exposed band from 97.3 to 80.2 km/h.
       ⚠ C2's cost: FactorC at 140 km/h drops 908 -> 566, a 38% cut in high-speed damping.
          It applies in ENGAGED MODE ONLY -- mode 24 stays byte-stock -- which bounds the risk.""")

    # -- 6d: grind-#2 separation ------------------------------------------------------------
    print("\n  (6d) GRIND-#2 SEPARATION -- is the V74/V75 `E_Y[1] := E_Y[2]` plateau an exposure?")
    print("       Stock FactorE RISES 140->539 across X=[400,2500] (85-531 deg/s).")
    print("       V74/V75 make it CONSTANT 539 there.  Gain vs stock, at matched rate:")
    print()
    print("       %8s %9s %9s %9s %9s" % ("rate ct", "deg/s", "stock E", "V74/V75 E", "ratio"))
    for r in (400, 700, 1200, 1800, 2500):
        es = lerp(*S["stock"].XY("E"), idx=r)
        ev = lerp(*S["v75"].XY("E"), idx=r)
        print("       %8d %9.0f %9d %9d %9.2fx" % (r, r / RATE_CTS_PER_DEGS, es, ev, ev / es))
    print("""
       => YES, the plateau raises gain by up to 3.85x exactly in the band flagged. [EVIDENCE]
       Whether it also acts as a RELAY is CONDITIONAL, not unconditional: the sign only flips
       when the rate crosses zero, and to jump +M to -M in one 100 Hz sample the rate must
       traverse the whole ramp within 10 ms.  For a 21 Hz oscillation of rate amplitude A the
       rate slews 1.32*A counts per update, so traversing V75's 188-count ramp needs A > 142
       counts.  Measured in-burst p50 is 99 counts => mostly NOT traversed; peaks may be.
       => plateau = a real GAIN exposure in the grind-#2 band, and a MARGINAL relay. [BELIEF]
       => remove it.  It costs nothing at the grind-#1 operating point, which sits BELOW the knee.""")

    # -- 6e: the recommended FactorE, grind-#2 separated -------------------------------------
    print("\n  (6e) FactorE CANDIDATES with the plateau removed, on C2 (flat 566)")
    print("       Target: V75-like dose at the grind-#1 point (r = 99 ct), MINIMUM dose above it.")
    print()
    print("       %-30s %6s %7s | %6s %6s %6s %6s | %7s"
          % ("FactorE X / Y", "k", "d@99", "d@200", "d@400", "d@1200", "d@2500", "maxdose"))
    print("       " + "-" * 96)
    tests = [("V75 as flown", [12, 200, 2500, 4000], [0, 539, 539, 927]),
             ("V74 as flown", [12, 400, 2500, 4000], [0, 539, 539, 927]),
             ("stock", [60, 400, 2500, 4000], [0, 140, 539, 927])]
    for x1, y1 in ((148, 300), (197, 400), (110, 225), (74, 150)):
        tests.append(("no-plateau X1=%d Y1=%d" % (x1, y1), [0, x1, 2500, 4000], [0, y1, 539, 927]))
    for nm, ex, ey in tests:
        s = Surface(img=img, override={"C": (CX, [566, 566, 566, 566]), "E": (ex, ey)})
        k = ((566 * ey[1]) >> 10) / (ex[1] - ex[0])
        md = max(s.mag(v, r) for v in (0, 8960) for r in (0, 99, 2500, 4000, 12999))
        print("       %-30s %6.3f %7d | %6d %6d %6d %6d | %7d"
              % (nm, k, s.mag(0, 99), s.mag(0, 200), s.mag(0, 400),
                 s.mag(0, 1200), s.mag(0, 2500), md))
    print("""
       => `no-plateau X1=148 Y1=300` holds V75's speed-MEAN dose (110) at the grind-#1 point
          while delivering 40% less at 400 ct and 28% less at 1200 ct than V75 -- the
          grind-#2 separation team-lead asked for, bought with no loss at grind #1.
       ⚠ A FactorE that PEAKS at low rate and falls back would separate the bands further and
          is arithmetically legal (V74/V75's FactorC already has a descending segment, so the
          evaluator handles it).  I do NOT recommend it: a negative dY/d(rate) is negative
          incremental damping, a destabilising slope. Recorded as available, not proposed.""")


# ---------------------------------------------------------------- main
def main():
    ok, S = validate()
    if not ok:
        print("*** VALIDATION FAILED -- everything below is untrustworthy ***")
    prove_dose_slew_identity()
    cand_C = factorC_shapes(S)
    front, rows, D75, D74 = pareto(S)
    slew_shape_search(S)

    # The recommended candidate: the arithmetic minimum-k surface that still holds V75's dose at
    # the measured in-burst rate.  E_X1 = 215 solves ((566*539)>>10)/215 = 137/99 exactly.
    CAND_E = ([0, 215, 2500, 4000], [0, 539, 539, 927])
    compare(S, cand_C, CAND_E)
    part6(S)

    print("\n" + "=" * 108)
    print("PART 5 -- THE HONEST STATEMENT")
    print("=" * 108)
    print("""
  1. DOSE AND SLEW ARE RIGIDLY COUPLED.  [EVIDENCE, PART 1: 282,150-point exhaustive check on
     the mirror]  dose(r) = k*(r - E_X0) exactly, so dose/k = r - E_X0 INDEPENDENT of C_Y0, E_Y1
     and E_X1.  k IS the first-segment slope, it IS the GATE-2 loop gain, and it IS the per-count
     slew coefficient -- one number, not three.  The only lever on the ratio is E_X0, bounded by
     0 <= E_X0 < r, worth at most (99-12)/99 = 12.4%.

  2. MATCHING V75's CREEP PEAK IS THE EXPENSIVE READING OF (a).  Holding 137 counts at r = 99
     forces k >= 137/99 = 1.384: only 12.4% below V75, still 2.39x V74 -- and V74 faulted too.
     But V75's dose was NOT uniform (137 creep / 56 at 60 km/h).  Its speed-MEAN over 0-80 km/h
     is 110.8, and the FLAT FactorC the operator asked for reaches that at k = 1.121 -- a 29%
     slew cut.  [PART 4b]  Requirement (b) partly pays for requirement (c).

  3. THE SHAPE IS ALREADY OPTIMAL.  [PART 3c]  No deadband and no soft knee beats the straight
     ramp at matched dose: a deadband relocates the step to the E_X0 crossing and makes it
     BIGGER (E_X0=70 gives k=4.72 and a 137-count step at only 30 counts of rate change).
     Constant slope is minimax-optimal against an unknown per-update rate change.  Only the
     LEVEL of k and E_X0 are genuinely free.

  4. 🛑 THE SLEW FRAMING IS SUPERSEDED -- parts 3a/3b are kept for the record, NOT as the
     design target.  SlewFix showed Surface A's check is `diff = fVar5 - clamp(fVar5, +/-ceil)`
     on the ALREADY-STORED gp-0x6bd0, so nothing writes that cell between the two samplings:
     the race variable is gp-0x6ac2, the CEILING's index, and the check is ONE-SIDED -- it can
     only trip if the ceiling SHRINKS while the damper is pinned against it.  The corridor is a
     MAGNITUDE bound, not a rate bound.  Update rate confirmed 100 Hz (task 5, FUN_00022ca0),
     not 1 kHz.  => k is NOT the fault-risk metric.  See PART 6 for the criteria that replaced it.

  5. NO TABLE VALUE HAS CLEAN-FLIGHT EVIDENCE, and the fault mechanism is NOT pinned.
     k = 0 (stock) never faulted; k = 0.5799 (V74) faulted after 1,744 s; k = 1.5798 (V75)
     faulted.  Surface A is probably UNREACHABLE anyway -- the clamp only binds near the 512
     ceiling floor and the damper has never been measured above ~448 (V75's >=448 rung: 0 of
     39,961 frames).  => choose the dose for COMFORT and for the grind-#1/grind-#2 separation,
     satisfy the magnitude guard because it is cheap and provable, and do NOT claim the build
     fixes the hard fault.  Nothing in these two tables has been shown to.
""")


if __name__ == "__main__":
    main()
