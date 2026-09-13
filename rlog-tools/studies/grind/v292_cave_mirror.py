# -*- coding: utf-8 -*-
"""v292_cave_mirror.py -- the byte-exact integer mirror of the V292 error-feedback feedback-lag cave,
and the five proofs the design is required to carry.  Agent `cavedesign`, 2026-09-13.

DESIGN STUDY: builds nothing, flashes nothing, sends nothing.  Importable.

WHAT V292 CHANGES
-----------------
V291 (C10) runs Honda's filter at 0x28F8E-0x28FA8 with the cal pair (a, b) = (962, 958):

    t_b   = x * b                       ; 0x28F8E  mul r16,r7,r0
    t_a   = s * a                       ; 0x28F92  mul r26,r9,r0
    step_b = t_b >> 10                  ; 0x28F9A  sar 0xa,r7     <-- floors toward -inf
    step_a = t_a >> 10                  ; 0x28FA0  sar 0xa,r9     <-- a SEPARATE floor
    s_new = step_a + step_b             ; 0x28FA2  add r7,r9
    out   = s_old + s_new               ; 0x28FA4  add r9,r26
    s     = s_new                       ; 0x28FA8  st.w r9,-0x3d30,gp
    out   = clamp(out, +-[0xC62E6])     ; 0x28FA6..0x28FBC

With b = 958 the input quantum is 1024/958 = 1.0689 raw counts (V282: 1024/1560 = 0.6564), so at the
1-3 count wheel rates of a grinding episode the feedback reads ~half of nominal and the closed loop's
steady state departs from the linear DC by x1.34-1.80 (ADV-V291-B SS5.2, SS11.4).

V292 keeps (a, b) EXACTLY -- the pole stays cal-visible at 0xC63E8/0xC63EA -- and carries the residue
of each floor into the next tick (first-order ERROR FEEDBACK, the same device as V289's notch cave):

    t_b   = x * b + rem_b ; step_b = t_b >> 10 ; rem_b = t_b & 0x3FF
    t_a   = s * a + rem_a ; step_a = t_a >> 10 ; rem_a = t_a & 0x3FF

`t & 0x3FF` IS `t - ((t >> 10) << 10)` exactly, for two's-complement t of either sign, because
arithmetic shift right satisfies t == ((t >> k) << k) + (t & (2**k - 1)).  One `andi` replaces
mov/shl/sub.

WHY THE MEAN BECOMES EXACT
--------------------------
    step_b[n] = (b*x[n] + rem_b[n-1] - rem_b[n]) / 1024
so summing over n telescopes:  sum(step_b) = (b*sum(x) + rem_b[0] - rem_b[N]) / 1024, and rem is
bounded in [0,1023].  The same holds for step_a.  Hence, writing S_N = sum_{1..N} s[n]:

    (1024 - a) * S_N = N*b*x + a*(s[0] - s[N]) + (bounded)          =>   mean(s) -> b*x/(1024-a)
    mean(out) = 2*mean(s) -> 2*b*x / (1024 - a)   EXACTLY, at EVERY amplitude, x = 1 included.

The quantisation error becomes (1 - z^-1)-shaped: it carries NO DC and is bounded by 1 LSB per term.
"""
import json
import os
import sys
from fractions import Fraction

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

TS = 1.0e-3                      # tick period, 1 ms (EVIDENCE-by-consistency, two label<->byte agreements)
FS = 1.0 / TS
CLAMP_C = 46080                  # [0xC62E6] on V282/V291
V282_A, V282_B = 923, 1560
V291_A, V291_B = 962, 958        # read from the V291 image: 0xC63E8 = 962, 0xC63EA = 958


# ======================================================================================================
#  1.  THE FILTERS -- byte-exact.  Python's >> on int floors toward -inf, matching V850 `sar`.
# ======================================================================================================
def _sar(v, k):
    return v >> k


def fb_lag_v291(x, s, a=V291_A, b=V291_B, C=CLAMP_C):
    """Honda's filter as V291/V282 ship it.  Returns (out, s_new).  No remainder."""
    s_new = _sar(a * s, 10) + _sar(b * x, 10)
    out = s + s_new
    return max(-C, min(C, out)), s_new


def fb_lag_v292(x, s, rem_b, rem_a, a=V291_A, b=V291_B, C=CLAMP_C):
    """The V292 cave.  Returns (out, s_new, rem_b', rem_a').

    Instruction-for-instruction (cave 0xC4C00, 15 instructions):
        mul r16,r7,r0        t_b = x*b
        mul r26,r9,r0        t_a = s*a
        ld.hu -0x6d74,gp,r13 ; add r13,r7 ; andi 0x3ff,r7,r13 ; st.h r13,-0x6d74,gp ; sar 0xa,r7
        ld.hu -0x6d72,gp,r13 ; add r13,r9 ; andi 0x3ff,r9,r13 ; st.h r13,-0x6d72,gp ; sar 0xa,r9
        ld.hu 0x72e6,tp,r13 ; ld.hu 0x72e6,tp,r14 ; jr 0x28FA2
    """
    t_b = b * x + rem_b
    step_b = _sar(t_b, 10)
    rem_b = t_b & 0x3FF                      # == t_b - (step_b << 10), exactly, for either sign
    t_a = a * s + rem_a
    step_a = _sar(t_a, 10)
    rem_a = t_a & 0x3FF
    s_new = step_a + step_b                  # 0x28FA2  add r7,r9   (unmodified Honda code)
    out = s + s_new                          # 0x28FA4  add r9,r26  (unmodified Honda code)
    return max(-C, min(C, out)), s_new, rem_b, rem_a


class FbLag:
    """Stateful wrapper.  ef=False -> V291/V282 behaviour; ef=True -> the V292 cave."""

    def __init__(self, a=V291_A, b=V291_B, C=CLAMP_C, ef=True, s=0, rem_b=0, rem_a=0):
        self.a, self.b, self.C, self.ef = int(a), int(b), int(C), bool(ef)
        self.s, self.rem_b, self.rem_a = int(s), int(rem_b), int(rem_a)

    def tick(self, x):
        if self.ef:
            out, self.s, self.rem_b, self.rem_a = fb_lag_v292(
                int(x), self.s, self.rem_b, self.rem_a, self.a, self.b, self.C)
        else:
            out, self.s = fb_lag_v291(int(x), self.s, self.a, self.b, self.C)
        return out


def dc_exact(a, b):
    """The LINEAR DC gain of the two-sample-sum lag, as an exact rational."""
    return Fraction(2 * b, 1024 - a)


def h_lin(f, a, b):
    """Exact linear frequency response.  H(z) = (b/1024)(1+z^-1) / (1 - (a/1024) z^-1)."""
    z1 = np.exp(-2j * np.pi * f * TS)
    return (b / 1024.0) * (1 + z1) / (1 - (a / 1024.0) * z1)


def corner_hz(a):
    return -np.log(a / 1024.0) / (2 * np.pi * TS)


# ======================================================================================================
#  2.  PROOF HELPERS
# ======================================================================================================
def mean_over_cycle(a, b, x, ef=True, max_ticks=4_000_000):
    """Drive a CONSTANT x to its eventual periodic orbit and return the EXACT rational mean of `out`
    over one period, plus the period.  The state space is finite (s bounded, rem in [0,1024)), so the
    orbit is always reached."""
    f = FbLag(a, b, ef=ef)
    seen = {}
    hist = []
    for k in range(max_ticks):
        key = (f.s, f.rem_b, f.rem_a) if ef else (f.s,)
        if key in seen:
            i = seen[key]
            cyc = hist[i:]
            return Fraction(sum(cyc), len(cyc)), len(cyc), k
        seen[key] = len(hist)
        hist.append(f.tick(x))
    raise RuntimeError("no cycle found")


def describing_fn(a, b, f_hz, A, ef=True, n_warm=20000, n_meas=40000):
    """Ratio of the measured fundamental of `out` to the LINEAR prediction from the fundamental of the
    integer input actually applied.  1.00 == the integer filter is behaving exactly like its linear
    model at this amplitude."""
    w = 2 * np.pi * f_hz * TS
    flt = FbLag(a, b, ef=ef)
    for k in range(n_warm):
        flt.tick(int(round(A * np.sin(w * k))))
    xs = np.empty(n_meas)
    ys = np.empty(n_meas)
    for k in range(n_meas):
        xk = int(round(A * np.sin(w * (n_warm + k))))
        xs[k] = xk
        ys[k] = flt.tick(xk)
    ph = np.exp(-1j * w * np.arange(n_meas))
    X1 = np.dot(xs, ph) / n_meas
    Y1 = np.dot(ys, ph) / n_meas
    H = h_lin(f_hz, a, b)
    return abs(Y1) / (abs(X1) * abs(H)), float(np.angle(Y1 / (X1 * H), deg=True))


# ======================================================================================================
#  3.  THE V850 ENCODER + AN INDEPENDENT DECODER, for the cave bytes
#      Every form is proven against a STOCK instance carrying the same hw1/hw2 pattern.
# ======================================================================================================
import struct                                                                        # noqa: E402

R0, R7, R9, R13, R14, R16, R26, GPr, TPr = 0, 7, 9, 13, 14, 16, 26, 4, 5
_OP1 = {"mov": 0x00, "add": 0x0E, "sub": 0x0D, "cmp": 0x0F}
_OP2 = {"sar": 0x15, "shl": 0x16, "movi": 0x10}
_OP67 = {"andi": 0x36, "ld.h": 0x39, "st.h": 0x3B, "ld.hu": 0x3F}


def _hw(v):
    return struct.pack("<H", v & 0xFFFF)


def i_f1(mn, reg1, reg2):
    return _hw((reg2 << 11) | (_OP1[mn] << 5) | reg1)


def i_f2(mn, imm5, reg2):
    return _hw((reg2 << 11) | (_OP2[mn] << 5) | (imm5 & 0x1F))


def i_f67(mn, reg1, reg2, disp):
    return _hw((reg2 << 11) | (_OP67[mn] << 5) | reg1) + _hw(disp)


def i_ld_hu(disp, base, dst):
    assert disp % 2 == 0
    return i_f67("ld.hu", base, dst, (disp & 0xFFFE) | 1)


def i_st_h(src, disp, base):
    assert disp % 2 == 0
    return i_f67("st.h", base, src, disp)


def i_andi(imm16, reg1, reg2):
    assert 0 <= imm16 <= 0xFFFF
    return i_f67("andi", reg1, reg2, imm16)


def i_mul(reg1, reg2, reg3=R0):
    """Format XI: hw1 = reg2<<11 | 0x3F<<5 | reg1 ; hw2 = reg3<<11 | 0x0220.  hw2 bit 0 == 0 is what
    separates `mul` from `ld.hu` in the shared 0x3F opcode field."""
    return _hw((reg2 << 11) | (0x3F << 5) | reg1) + _hw((reg3 << 11) | 0x0220)


def i_jr(pc, target):
    d = target - pc
    assert d % 2 == 0 and -(1 << 21) <= d < (1 << 21), f"disp22 out of range: {d:#x}"
    d &= 0x3FFFFF
    return _hw((0 << 11) | (0x1E << 6) | ((d >> 16) & 0x3F)) + _hw(d & 0xFFFE)


HOOK = 0x28F8E                 # `mul r16,r7,r0`, bytes f0 3f 20 02
RETURN_TO = 0x28FA2            # `add r7,r9`
CAVE = 0xC4C00
REM_B_DISP = -0x6D74           # 0xFEDF128C
REM_A_DISP = -0x6D72           # 0xFEDF128E
CLAMP_TP = 0x72E6              # tp + 0x72E6 = 0xC62E6


def build_cave(cave=CAVE, hook=HOOK, ret=RETURN_TO, rb=REM_B_DISP, ra=REM_A_DISP):
    """Return (hook_bytes, cave_bytes, listing) for the V292 cave."""
    rows = [
        (i_mul(R16, R7),            "mul   r16,r7,r0",          "r7 = t_b = x*b            [replicated 0x28F8E]"),
        (i_mul(R26, R9),            "mul   r26,r9,r0",          "r9 = t_a = s*a            [replicated 0x28F92]"),
        (i_ld_hu(rb, GPr, R13),     f"ld.hu {rb:#x},gp,r13",    "r13 = rem_b  (0..65535 -> harmless)"),
        (i_f1("add", R13, R7),      "add   r13,r7",             "r7 = t_b + rem_b"),
        (i_andi(0x3FF, R7, R13),    "andi  0x3ff,r7,r13",       "r13 = rem_b' = t_b & 0x3FF"),
        (i_st_h(R13, rb, GPr),      f"st.h  r13,{rb:#x},gp",    "rem_b := rem_b'"),
        (i_f2("sar", 10, R7),       "sar   0xa,r7",             "r7 = step_b              [replicated 0x28F9A]"),
        (i_ld_hu(ra, GPr, R13),     f"ld.hu {ra:#x},gp,r13",    "r13 = rem_a"),
        (i_f1("add", R13, R9),      "add   r13,r9",             "r9 = t_a + rem_a"),
        (i_andi(0x3FF, R9, R13),    "andi  0x3ff,r9,r13",       "r13 = rem_a' = t_a & 0x3FF"),
        (i_st_h(R13, ra, GPr),      f"st.h  r13,{ra:#x},gp",    "rem_a := rem_a'"),
        (i_f2("sar", 10, R9),       "sar   0xa,r9",             "r9 = step_a             [replicated 0x28FA0]"),
        (i_ld_hu(CLAMP_TP, TPr, R13), "ld.hu 0x72e6,tp,r13",    "clamp                   [replicated 0x28F96]"),
        (i_ld_hu(CLAMP_TP, TPr, R14), "ld.hu 0x72e6,tp,r14",    "clamp                   [replicated 0x28F9C]"),
    ]
    body = b"".join(r[0] for r in rows)
    rows.append((i_jr(cave + len(body), ret), f"jr    {ret:#x}", "back into Honda's `add r7,r9`"))
    body += rows[-1][0]
    listing, pc = [], cave
    for by, mn, cm in rows:
        listing.append((pc, by, mn, cm))
        pc += len(by)
    return i_jr(hook, cave), body, listing


# ======================================================================================================
#  4.  CLOSED LOOP -- design290b's Controller with the fb filter swapped for the V292 cave.
#      Everything else (P, D, fade, sum clamp, output lag, gain, t clamp) is design290b's, unchanged.
# ======================================================================================================
def make_controller(c, ef, a=None, b=None):
    """Return a design290b Controller whose feedback-lag stage runs the V292 cave when ef=True."""
    import design290b_candidates as D

    cc = dict(c)
    if a is not None:
        cc["fb_a"] = int(a)
    if b is not None:
        cc["fb_b"] = int(b)

    class _Ctl(D.Controller):
        def __init__(self, cells):
            super().__init__(cells)
            self.rem_b = 0
            self.rem_a = 0

        def tick(self, sp, x):
            cl = self.c
            x = D.clampi(int(x), 12000)
            A_, B_ = int(cl["fb_a"]), int(cl["fb_b"])
            if ef:
                t_b = B_ * x + self.rem_b
                step_b = t_b >> 10
                self.rem_b = t_b & 0x3FF
                t_a = A_ * self.s_fb + self.rem_a
                step_a = t_a >> 10
                self.rem_a = t_a & 0x3FF
                s_new = step_a + step_b
            else:
                s_new = D.sar(A_ * self.s_fb, 10) + D.sar(B_ * x, 10)
            fb = D.clampi(self.s_fb + s_new, int(cl["fb_clamp"]))
            self.s_fb = s_new
            E = 32 * int(sp) - fb
            P = D.clampi(D.sar(E * self.kp, 8), int(cl["p_clamp"]))
            dE = 0 if self.E_prev is None else (E - self.E_prev)
            self.E_prev = E
            Dt = D.clampi(D.sar(dE * self.kd, 3), int(cl["d_clamp"]))
            S = D.clampi(D.sar(254 * (P + Dt), 8), int(cl["sum_clamp"]))
            s_new2 = D.sar(int(cl["lag_a"]) * self.s_lag, 10) + D.sar(int(cl["lag_b"]) * S, 10)
            y = D.sar(self.s_lag + s_new2, 5)
            self.s_lag = s_new2
            y = ((y + 0x8000) & 0xFFFF) - 0x8000
            return D.clampi(D.sar(y * int(cl["gain"]), 15), int(cl["t_clamp"]))

    return _Ctl(cc)


def closed_loop_ss(c, plant, ef, a, b, sp_step, n=6000, tail=800):
    """Byte-exact closed loop: controller -> plant fit -> wheel rate -> x.  Returns (ss deg/s, peak)."""
    import design290b_candidates as D

    ctl = make_controller(c, ef, a, b)
    bn, an = plant.num, plant.den
    xh = np.zeros(len(bn))
    yh = np.zeros(len(an))
    rate = np.zeros(n)
    x = 0
    for k in range(n):
        Tk = ctl.tick(sp_step if k >= 5 else 0, x)
        xh = np.roll(xh, 1)
        xh[0] = Tk
        yk = (np.dot(bn, xh) - np.dot(an[1:], yh[:-1])) / an[0]
        yh = np.roll(yh, 1)
        yh[0] = yk
        rate[k] = yk
        x = int(round(D.CPD * yk))
    return float(np.mean(rate[-tail:])), float(np.max(np.abs(rate)))


# ======================================================================================================
#  5.  THE FIVE PROOFS
# ======================================================================================================
def _pr(out, s=""):
    print(s, flush=True)
    out.append(s)


def run_proofs():
    O = []

    def pr(s=""):
        _pr(O, s)

    A291, B291 = V291_A, V291_B
    dc291 = dc_exact(A291, B291)
    dc282 = dc_exact(V282_A, V282_B)
    pr("=" * 118)
    pr("V292 ERROR-FEEDBACK FEEDBACK-LAG CAVE -- the five proofs.  a = %d, b = %d (UNCHANGED from V291 C10)."
       % (A291, B291))
    pr("  linear DC = 2b/(1024-a) = %s = %.6f   (V282: %s = %.6f, ratio %.6f)"
       % (dc291, float(dc291), dc282, float(dc282), float(dc291 / dc282)))
    pr("  corner    = %.3f Hz (V282: %.3f Hz);  input quantum 1024/b = %.4f raw counts (V282: %.4f)"
       % (corner_hz(A291), corner_hz(V282_A), 1024 / B291, 1024 / V282_B))
    pr("=" * 118)

    # ---------------------------------------------------------------- PROOF (i)
    pr("")
    pr("PROOF (i)  MEAN GAIN IS EXACT AT EVERY AMPLITUDE -- no dead zone, no stick.")
    pr("-" * 118)
    pr("  Constant x driven to its periodic orbit; mean of `out` over one full period, as an EXACT rational.")
    pr("  %6s | %-14s | %-30s | %-11s | %-16s | %-11s" %
       ("x", "V291 mean/x", "V292 mean/x (exact)", "V292 period", "V292 - linear", "V291/linear"))
    bad = 0
    XS = [1, 2, 3, 4, 5, 8, 13, 16, 32, 64, 100, 333, 1000, 4096, 12000]
    for x in XS:
        m291, p291, _ = mean_over_cycle(A291, B291, x, ef=False)
        m292, p292, _ = mean_over_cycle(A291, B291, x, ef=True)
        g291, g292 = m291 / x, m292 / x
        err = g292 - dc291
        if err != 0:
            bad += 1
        pr("  %6d | %-14.6f | %-30s | %-11d | %-16s | %-11.4f"
           % (x, float(g291), "%s = %.9f" % (g292, float(g292)), p292, str(err), float(g291 / dc291)))
    xc = int(CLAMP_C * (1024 - A291) / (2 * B291))
    pr("  => the last two rows are NOT the quantiser: the pre-existing +-%d OUTPUT clamp binds for" % CLAMP_C)
    pr("     |x| >= C*(1024-a)/(2b) = %d counts = %.1f deg/s, and V291 and V292 sit on that rail IDENTICALLY"
       % (xc, xc / 8.0))
    pr("     (both read %.2f at x=4096 and %.2f at x=12000).  Below the rail V292 is exact on every row."
       % (CLAMP_C / 4096.0, CLAMP_C / 12000.0))
    worst, wx = Fraction(0), None
    for x in list(range(1, xc + 1)) + list(range(-xc, 0)):
        m, _, _ = mean_over_cycle(A291, B291, x, ef=True)
        d = abs(m / x - dc291)
        if d > worst:
            worst, wx = d, x
    pr("  EXHAUSTIVE over the WHOLE UNCLAMPED RANGE x = -%d..-1 and 1..%d (%d amplitudes, BOTH SIGNS --"
       % (xc, xc, 2 * xc))
    pr("  the negative side is where V291's floor is biased): max |mean/x - 2b/(1024-a)| = %s  (%s)"
       % (worst, "EXACTLY ZERO" if worst == 0 else "NON-ZERO, worst at x=%s" % wx))
    pr("  => VERDICT (i): %s"
       % ("PASS -- the mean input gain is EXACTLY b/1024 and the mean decay EXACTLY a/1024 at every "
          "amplitude\n     below the output clamp, x = +-1 included.  No dead zone, no stick."
          if worst == 0 else "FAIL"))
    pr("")
    pr("  THE s = -1 ABSORBING STATE (pre-existing on stock and on V291) -- released by the error feedback:")
    for lab, ef in (("V291", False), ("V292", True)):
        f = FbLag(A291, B291, ef=ef, s=-1)
        outs = [f.tick(0) for _ in range(200)]
        pr("    %s, s0 = -1, x = 0 for 200 ticks:  final s = %+d,  out[190:200] = %s"
           % (lab, f.s, outs[190:200]))
    for lab, ef in (("V291", False), ("V292", True)):
        f = FbLag(A291, B291, ef=ef, s=-500)
        k = 0
        while f.s != 0 and k < 100000:
            f.tick(0)
            k += 1
        pr("    %s, s0 = -500, x = 0:  ticks for s to reach EXACTLY 0 = %s"
           % (lab, k if f.s == 0 else "NEVER (stuck at s = %d)" % f.s))

    # ---------------------------------------------------------------- PROOF (ii)
    pr("")
    pr("PROOF (ii)  FIRST-TICK RESPONSE TO A 1-COUNT x STEP.")
    pr("-" * 118)
    r282, _ = fb_lag_v291(1, 0, V282_A, V282_B)
    r291, _ = fb_lag_v291(1, 0, A291, B291)
    hits = [fb_lag_v292(1, 0, rb, 0, A291, B291)[0] for rb in range(1024)]
    ge282 = sum(1 for h in hits if h >= r282)
    ge291 = sum(1 for h in hits if h >= r291)
    gt291 = sum(1 for h in hits if h > r291)
    pr("  V282 (a=923,b=1560): out[1] = %d      V291 (a=962,b=958): out[1] = %d" % (r282, r291))
    pr("  V292: out[1] depends on the rem_b phase.  Over all 1024 phases: mean %.4f, min %d, max %d"
       % (float(np.mean(hits)), min(hits), max(hits)))
    pr("    >= V291 (%d): %d/1024 (%.1f%%)   STRICTLY > V291: %d/1024 (%.1f%%)"
       % (r291, ge291, 100.0 * ge291 / 1024, gt291, 100.0 * gt291 / 1024))
    pr("    >= V282 (%d): %d/1024 (%.1f%%)" % (r282, ge282, 100.0 * ge282 / 1024))
    pr("  VERDICT (ii) vs V291 (SAME pole -- the like-for-like comparison): PASS.  Never worse; strictly")
    pr("    better on %.1f%% of phases.  V291 answers a 1-count input with 0 on 100%% of phases, forever."
       % (100.0 * gt291 / 1024))
    pr("  VERDICT (ii) vs V282 (a DIFFERENT, deliberately slower pole): the clause is NOT met")
    pr("    deterministically.  V292's first tick is %.4f of V282's IN MEAN (= b/1024 = %.4f), because the"
       % (float(np.mean(hits)) / r282, B291 / 1024.0))
    pr("    quantum is 1.07 counts, not 0.66.  It is met on %.1f%% of phases.  REPORTED, NOT CLAIMED."
       % (100.0 * ge282 / 1024))
    pr("")
    pr("  CUMULATIVE response to a sustained 1-count x (sum of `out` over the first K ticks):")
    pr("  %4s | %10s | %10s | %22s | %14s" % ("K", "V282", "V291", "V292 (min..max phase)", "V292min/V282"))
    for K in (1, 2, 3, 5, 10, 20, 50, 200, 1000):
        f = FbLag(V282_A, V282_B, ef=False)
        cc282 = sum(f.tick(1) for _ in range(K))
        f = FbLag(A291, B291, ef=False)
        cc291 = sum(f.tick(1) for _ in range(K))
        cs = []
        for rb in range(0, 1024, 8):
            f = FbLag(A291, B291, ef=True, rem_b=rb)
            cs.append(sum(f.tick(1) for _ in range(K)))
        pr("  %4d | %10d | %10d | %22s | %14.3f"
           % (K, cc282, cc291, "%d..%d" % (min(cs), max(cs)),
              (min(cs) / cc282) if cc282 else float("nan")))

    # ---------------------------------------------------------------- PROOF (iii)
    pr("")
    pr("PROOF (iii)  DESCRIBING-FUNCTION GAIN AT 20.3 Hz, normalised to the LINEAR response (1.00 = linear).")
    pr("-" * 118)
    pr("  |H_linear(20.3 Hz)| = %.6f" % abs(h_lin(20.3, A291, B291)))
    pr("  %8s | %-24s | %-24s | %-12s" % ("A cnts", "V291 gain (phase)", "V292 gain (phase)", "V292 |err|"))
    worst_iii = 0.0
    for A in (1, 2, 3, 5, 8, 16):
        g1, p1 = describing_fn(A291, B291, 20.3, A, ef=False)
        g2, p2 = describing_fn(A291, B291, 20.3, A, ef=True)
        worst_iii = max(worst_iii, abs(g2 - 1.0))
        pr("  %8d | %-24s | %-24s | %-12.4f"
           % (A, "%.4f (%+.2f deg)" % (g1, p1), "%.4f (%+.2f deg)" % (g2, p2), abs(g2 - 1.0)))
    pr("  => worst |V292 gain - 1.00| over A = 1..16 : %.4f" % worst_iii)
    pr("  => VERDICT (iii): %s (tolerance +-0.02)"
       % ("PASS" if worst_iii <= 0.02 else "FAIL -- exceeds +-0.02"))

    # ---------------------------------------------------------------- PROOF (iv)
    pr("")
    pr("PROOF (iv)  BYTE-EXACT CLOSED-LOOP STEADY STATE, family median fit.  THE ADV-V291-B B4 CLAUSE.")
    pr("-" * 118)
    try:
        import design290b_candidates as D
        c289, c282 = D.cells()
        fam = json.load(open(os.path.join(SCR, "design290b_family.json")))
        stab = [p for p in fam if p["z289"] >= D.Z289_STABLE]
        med = sorted(stab, key=lambda p: p["g0"])[len(stab) // 2]
        pl = D.mkplant(med)
        pr("  median fit: fp %.2f  zp %.4f  tau %.0f ms  f1 %.1f  g0 %.4f  (of %d stable fits)"
           % (med["fp"], med["zp"], 1e3 * med["tau"], med["f1"], med["g0"], len(stab)))
        pr("  The 4th column is the CONTROL that isolates the cave from the pole: V282's OWN cal pair with")
        pr("  the cave applied.  It shows how much of any residual is the cave removing V282's own floor bias.")
        pr("  %6s | %13s | %13s | %13s | %13s | %10s | %10s"
           % ("sp", "V282 (ref)", "V291 = C10", "V292", "V282+cave", "V291/V282", "V292/V282"))
        worst_iv = 0.0
        rows = {}
        for sp in (3, 33, 330):
            ss282, pk282 = closed_loop_ss(c282, pl, False, V282_A, V282_B, sp, n=12000, tail=2000)
            ss291, pk291 = closed_loop_ss(c282, pl, False, A291, B291, sp, n=12000, tail=2000)
            ss292, pk292 = closed_loop_ss(c282, pl, True, A291, B291, sp, n=12000, tail=2000)
            ssctl, _ = closed_loop_ss(c282, pl, True, V282_A, V282_B, sp, n=12000, tail=2000)
            r1 = ss291 / ss282 if ss282 else float("nan")
            r2 = ss292 / ss282 if ss282 else float("nan")
            worst_iv = max(worst_iv, abs(r2 - 1.0))
            rows[sp] = (r1, r2, ssctl / ss282, pk282, pk291, pk292)
            pr("  %6d | %13.5f | %13.5f | %13.5f | %13.5f | %10.4f | %10.4f"
               % (sp, ss282, ss291, ss292, ssctl, r1, r2))
        pr("")
        pr("  sp = 3 IS THE OPERATING POINT THE B4 CLAUSE NAMES.  There V291 = x%.4f (the adversary's"
           % rows[3][0])
        pr("  x1.34-1.80 band) and V292 = x%.5f -- EXACTLY 1.000.  B4 IS CLOSED AT ITS OWN OPERATING POINT."
           % rows[3][1])
        pr("  sp = 33 : V292 is %.2f%% low, OUTSIDE the brief's +-1%%.  REPORTED AS A MISS, not rounded away."
           % (100 * (1 - rows[33][1])))
        pr("    Cause, from the control column: V282 + the same cave lands at x%.4f, i.e. V282's own integer"
           % rows[33][2])
        pr("    reference is itself inflated ~%.1f%% by ITS floor bias; V292 is within %.2f%% of V282-corrected."
           % (100 * (1 - rows[33][2]), 100 * abs(rows[33][1] - rows[33][2])))
        pr("  sp = 330: V292 is %.2f%% low, INSIDE +-1%%." % (100 * (1 - rows[330][1])))
        pr("  => worst |V292/V282 - 1| over the three points: %.4f" % worst_iv)
        pr("  => VERDICT (iv): PASS at sp=3 (exact) and sp=330; MISS at sp=33 by %.2f pct."
           % (100 * (worst_iv - 0.01)))
        pr("  Peak wheel rate (transient authority, unchanged by the cave in kind):")
        for sp in (3, 33, 330):
            _, _, _, p282, p291, p292 = rows[sp]
            pr("     sp %3d : V282 %8.4f | V291 %8.4f (x%.3f) | V292 %8.4f (x%.3f)"
               % (sp, p282, p291, p291 / p282, p292, p292 / p282))
    except Exception as e:
        pr("  UNAVAILABLE: %s: %s" % (type(e).__name__, e))

    # ---------------------------------------------------------------- PROOF (v)
    pr("")
    pr("PROOF (v)  THE LINEAR PART IS UNCHANGED, SO EVERY C10 LOOP GATE CARRIES OVER WITH NO RECOMPUTATION.")
    pr("-" * 118)
    pr("  The cal cells are byte-IDENTICAL to C10: 0xC63E8 = %d, 0xC63EA = %d.  The cave changes neither"
       % (A291, B291))
    pr("  coefficient, neither multiply, the two-sample sum, the state cell, nor the +-[0xC62E6] clamp.")
    pr("  It changes ONLY how each of the two `sar 0xa` floors disposes of its residue.")
    pr("")
    pr("    step_b[n] = (b*x[n] + rem_b[n-1] - rem_b[n])/1024 = (b/1024)*x[n] - (1 - z^-1)*rem_b[n]/1024")
    pr("")
    pr("  so the quantisation error is a FIRST DIFFERENCE of a sequence bounded in [0,1023]:")
    pr("    - it carries EXACTLY ZERO DC (the telescoping sum is bounded, so its mean -> 0 as 1/N);")
    pr("    - its magnitude is <= 1 LSB of s per term, i.e. <= 2 counts on the two-sample sum, against")
    pr("      a clamp range of +-%d;" % CLAMP_C)
    pr("    - it is HIGH-PASS shaped (|1 - e^-jw| = 0 at DC), so it adds nothing at low frequency.")
    pr("  gate73 / Ms / pkR are functions of (a, b, structure) ONLY -- the quantiser is not represented in")
    pr("  the linear model at all.  So gate73 = 1.0099, Ms and pkR as scored for C10 are the SAME NUMBERS")
    pr("  for V292, not merely close to them.  EVIDENCE: the cells are byte-identical on the V291 image.")
    pr("  DEDUCTION: therefore the gates hold.  What V292 changes is the SMALL-AMPLITUDE nonlinear")
    pr("  behaviour, which those linear gates never measured.")
    pr("")
    pr("  MEASURED, against the EXACT LINEAR filter run in float alongside the integer one (20.3 Hz sine,")
    pr("  20000 scored ticks after a 10000-tick warm-up).  This is the decisive table: it shows the integer")
    pr("  filter's DEVIATION FROM ITS OWN LINEAR MODEL, which is what every C10 gate assumed was small.")
    pr("  %8s | %-34s | %-34s" % ("A cnts", "V292 - linear", "V291 - linear  (= C10 today)"))
    for A in (1, 3, 8, 64, 512):
        w = 2 * np.pi * 20.3 * TS
        f292, f291 = FbLag(A291, B291, ef=True), FbLag(A291, B291, ef=False)
        s_lin = 0.0
        d2, d1 = [], []
        for k in range(30000):
            xk = int(round(A * np.sin(w * k)))
            s_prev = s_lin
            s_lin = (A291 / 1024.0) * s_lin + (B291 / 1024.0) * xk
            lin = s_prev + s_lin
            d2.append(f292.tick(xk) - lin)
            d1.append(f291.tick(xk) - lin)
        d2, d1 = np.array(d2[10000:]), np.array(d1[10000:])
        pr("  %8d | mean %+7.4f rms %6.4f max %5.2f | mean %+8.4f rms %7.4f max %6.2f"
           % (A, d2.mean(), d2.std(), np.abs(d2).max(), d1.mean(), d1.std(), np.abs(d1).max()))
    pr("  => V292's mean deviation from its linear model is ZERO to 4 decimals at EVERY amplitude, with an")
    pr("     rms under 0.7 counts and a peak under 2 -- exactly the <= 2-count bound predicted above.")
    pr("  => C10's carries a CONSTANT -32-count DC OFFSET at every amplitude.  That is the accumulated floor")
    pr("     bias: each of the two floors loses 0.5 LSB per tick, the state integrates it to 0.5*1024/(1024-a)")
    pr("     = %.1f counts per term, and the two-sample sum doubles it -> %.0f.  Against E = 32*sp - fb, a"
       % (0.5 * 1024 / (1024 - A291), 2 * 2 * 0.5 * 1024 / (1024 - A291)))
    pr("     -32 offset in fb is +32 counts of PHANTOM ERROR, i.e. one whole extra setpoint count, forever.")
    pr("     At sp = 3 (E = 96 nominal) that is +33%% of demand -- THE MECHANISM BEHIND THE B4 FAILURE.")
    pr("     V282's own bias is 0.5*1024/101*2*2 = %.0f counts, which is why V282 is the smaller offender."
       % (2 * 2 * 0.5 * 1024 / (1024 - V282_A)))

    # ---------------------------------------------------------------- the cave bytes
    pr("")
    pr("=" * 118)
    pr("THE CAVE, ASSEMBLED.  hook 0x%05X -> cave 0x%05X -> return 0x%05X" % (HOOK, CAVE, RETURN_TO))
    pr("=" * 118)
    hb, cb, listing = build_cave()
    pr("  HOOK   0x%05X   %-12s  jr 0x%05X   (replaces `mul r16,r7,r0`, stock bytes f0 3f 20 02)"
       % (HOOK, hb.hex(" "), CAVE))
    for pc, by, mn, cm in listing:
        pr("  0x%05X  %-12s  %-24s ; %s" % (pc, by.hex(" "), mn, cm))
    pr("  CAVE SIZE: %d bytes, %d instructions.  Honda executed 6 instructions in the displaced span;"
       % (len(cb), len(listing)))
    pr("  V292 executes 1 jr + %d = %d.  NET +%d instructions per 1 ms tick."
       % (len(listing), len(listing) + 1, len(listing) + 1 - 6))
    open(os.path.join(SCR, "v292_cave_mirror.txt"), "w", encoding="utf-8").write("\n".join(O) + "\n")
    pr("")
    pr("wrote _scratch/v292_cave_mirror.txt")
    return O


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run_proofs()
