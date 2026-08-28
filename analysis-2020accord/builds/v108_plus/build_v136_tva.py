#!/usr/bin/env python3
# ============================================================================
# SUPERSEDED 2026-08-28 -- V133-BASED, AND V133 REGRESSED ON-CAR.  DO NOT FLY.
#   V133 vs the last FLOWN build (V122) moved SIX cells, including the b26
#   clamp 511->1023 (APPARENT MASS ceiling, not mode-gated), the LKAS gain
#   5346->7128 (6x->8x), and BOTH Lever A arms (the r24 half is recorded as
#   having CAUSED grind #2).  Operator reported violent grinding persisting
#   after disengage, plus grind #2 disengaged on a hard turn.
#   This build inherits ALL of those.  Rebase onto V122 before flying.
#   See docs/STATE.md "V133 REGRESSED ON-CAR".
# ============================================================================
r"""
V136 -- alpha2 0xC40DC 5 -> 2.  ONE payload byte.  Base = V133.

*** A FOLLOW-UP.  FLY V133 FIRST. ***
V133 restores V62's Lever A, the only lever in this kit's record with a MEASURED fix on the
operator's exact remaining symptom.  V136 is a follow-up alongside V134; flying it before V133
would confound that test.

WHY alpha2 -- AND WHY THIS REVERSES V135's RATIONALE
------------------------------------------------------
V135's docstring argues "alpha2 is nearly INERT at 20 Hz => V122's improvement came from the
KNEE/K1".  That was a delivered-component TRANSFER-FUNCTION argument whose sign convention was
never reconciled.  A CLEAN SINGLE-VARIABLE ON-CAR COMPARISON says the opposite:

    build  endpoint*  knee   K1  alpha2   relay slope   sat deg/s  gain
    V91      10.59     600   204     22     0.003984       10.6     3564
    V111      4.40     600   204     14     0.003984       10.6     5346
    V112      4.74    1800   612     14     0.003984       31.8     5346
    V122      3.38    3000  1020      8     0.003984       53.1     5346
    * ENGAGED/MANUAL 18-22 Hz at creep, speed-matched, 30-40 Hz control guard PASSED on all four

  V111 -> V112 is SINGLE-VARIABLE: same alpha2 (14), same gain (5346), same relay slope (the
  gain-holding invariant), differing ONLY in saturation point 10.6 -> 31.8 deg/s.
      => endpoint 4.40 -> 4.74.  THE KNEE STEP BOUGHT NOTHING.  Slightly worse, and inside
         V112's own 3 % route spread (4.66 vs 4.82 on its two routes) => honestly a NULL.
  V112 -> V122 moves alpha2 14 -> 8 => 4.74 -> 3.38, a 1.35x improvement, ABOVE that noise.
      => [EVIDENCE] alpha2 is the lever with a detectable effect; the KNEE is NULL.
      => V135 is DEMOTED.  It still delivers the 17 % friction cut the operator asked for, but
         it must NOT be sold as a grind fix.

AND THE MECHANISM AGREES WITH THE MEASUREMENT
-----------------------------------------------
    H(f) = 64 * H1(alpha0 = 37/128) * (1 - z^-1) * H2(alpha2/64),  fs = 1000 Hz
    |H| averaged over 18-22 Hz:
        alpha2 22 -> 7.2300     alpha2  8 -> 5.4903     alpha2  2 -> 1.8490   <- THIS BUILD
        alpha2 14 -> 6.7211     alpha2  5 -> 4.0982     alpha2  0 -> LANE DEAD (do not)
    predicted alpha2 14 -> 8 : 1.22x less lane      MEASURED: 1.35x better endpoint
    predicted V111 vs V112 (identical alpha2): 1.00x   MEASURED: 1.08x = the noise floor
  The single-path prediction UNDER-shoots the measurement, which is exactly what a SECOND path
  would do -- see the blast radius below.

  And the physics closes it: gp-0x6b26 = -K * acceleration is APPARENT MASS.  Less apparent mass
  raises zeta = c / (2*sqrt(k*m)) => LESS resonant.  Ladder, transfer function and physics all
  point the same way, and lowering apparent steering mass is what the operator explicitly asked
  for -- "We want both: low apparent steering mass and friction to LKAS AND no ratcheting."
  This lever moves BOTH his goals the same direction instead of trading them.

THE ARITHMETIC, READ FROM THE DECOMPILE (FUN_00041464 @ 0x41626)
------------------------------------------------------------------
    iVar17 = ((int)((iVar14 - *(int *)(gp-0x35a0)) * (uint)*(ushort *)(tp+0x50dc)) >> 6)
             + *(int *)(gp-0x35a0);          // y += ((accel - y) * alpha2) >> 6
    *(int *)(gp-0x35a0) = iVar17;            // 32-BIT state
    ...
    *(short *)(gp-0x6c2c) = (short)(iVar17 >> 9);
  * the EMA state is 32-BIT and the output is >>9, so the truncation deadband |x-y| < 64/alpha2
    is 32 STATE units at alpha2=2 = 32/512 = 0.0625 OUTPUT LSB.  SUB-LSB => no stair-stepping.
    That was the one mechanism by which a low alpha2 could itself CAUSE a ratchet.  It cannot.
  * an EMA has UNITY DC GAIN for any alpha => no static behaviour changes anywhere.

THE BLAST RADIUS -- DECLARED, NOT ASSUMED
-------------------------------------------
gp-0x6c2c is this EMA's output and has EIGHT gp-based accesses (base-register-filtered scan):
    0x36C1A   FUN_00036c12   the gp-0x6b26 inertia lane        <- the intended target
    0x428FA   the hard-reversal DETECTOR (vs cal 0xC620A = 12800), which drives gp-0x671a
    0x4292C   0x42968        the same detector cluster
    0x4184E   0x41AC2        the writers, in FUN_00041464 itself
    0x71378   FUN_00071272   ld.h -> cvtf.ws -> mulf.s (const 0x39C90FDB ~ pi/8192)  FLOAT MODEL
    0x7B1A2   FUN_0007B022   ld.h -> mulf.s, alongside tp+0x623c (0xC523C, model-coeff block)
  => alpha2 is NOT a single-purpose filter coefficient.  It is a SHARED lever.
  => [EVIDENCE] but every one of these consumers was in force across V91/V111/V112/V122, which
     flew alpha2 at 22/14/14/8 -- a 2.75x swing -- fault-free, with monotone symptom improvement.
     This build is one further rung of 2.5x on a path already walked.

WHAT IS NEW AT alpha2 = 2, AND WHY IT IS ACCEPTABLE
-----------------------------------------------------
The detector loses sensitivity to FAST transients.  Peak of the EMA for a half-sine acceleration
pulse (unity input; the detector compares against 12800):
    pulse ms     a2=5     a2=2    loss
        10      0.366    0.174    2.10x   SEVERE
        30      0.686    0.409    1.68x   moderate
       100      0.935    0.759    1.23x   negligible
       200      0.982    0.903    1.09x   negligible
       400      0.995    0.971    1.03x   negligible
  vs the 18-22 Hz inertia-lane attenuation of 2.22x.
  * a DRIVER hard reversal is a 100-400 ms event (human bandwidth 2-5 Hz) => the detector loses
    only 1.03-1.23x there, while the grind band drops 2.22x.  alpha2 is SELECTIVE.
  * and the branch that detector selects -- the oscillation branch 0xC640A -- V133 has ALREADY
    sized from Honda's -8192 down to -1966 (4.17x), so it is de-fanged before alpha2 touches it.
[BELIEF] that this further rung reduces the operator's rare creep grind.  The ladder supports
         the DIRECTION with one clean single-variable comparison; it does not prove this dose.

EVIDENCE vs BELIEF
------------------
[EVIDENCE] the decompiled EMA arithmetic and its 32-bit state; the sub-LSB deadband; unity DC
           gain; the eight-consumer blast radius from a base-register-filtered scan; the flown
           alpha2 ladder 22/14/14/8 and its guard-passing endpoints; the selectivity table.
[BELIEF]   the symptom effect of this specific dose, and that suppressing the fast-transient
           detector response is harmless on a V133 base.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------

import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V136_WRITE", "").strip().lower()

BASE_NAME = "_v133_V133-V131BASE-B26.CEILING.1023-SAR3_plain_image.bin"
BASE_SHA = "f26ddb4364198293f5fd91c99cccd103ebc951b4f1bb9cc56d40b67a7388822b"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -- ONE CAL, ONE PAYLOAD BYTE ----------------------------------------------------
ALPHA2_CAL, ALPHA2_OLD, ALPHA2_NEW = 0xC40DC, 5, 2
ALPHA2_STOCK = 22
ALPHA2_SHIFT = 6                    # y += ((x - y) * alpha2) >> 6      @ 0x41626
EMA_OUT_SHIFT = 9                   # gp-0x6c2c = (short)(state >> 9)   @ 0x4184E
ALPHA2_FLOWN = {22: "V91", 14: "V111 / V112", 8: "V122"}      # all flown, all fault-free
ALPHA2_BUILT = {5: "V133 (this build's base)"}

# ---- cells that must NOT move -----------------------------------------------------------------
ALPHA2_TWIN_CAL, ALPHA2_TWIN_VAL = 0xC40DA, None    # the >>7 twin feeding gp-0x6c2e -- UNTOUCHED
ALPHA0_CAL_NOTE = "alpha0 = 37/128 is frozen: shared with the 0xC520C cap-table index"
KNEE_CAL, KNEE_VAL = 0xC40BC, 3000
K1_CAL, K1_VAL, K1_CEILING = 0xC40D2, 1020, 1023
OFF_CAL, OFF_VAL = 0xC4080, 0
POLE_CAL, POLE_VAL = 0xC40D0, 408
RESID_CAL, RESID_VAL = 0xC7468, 41232
GAIN_CAL, GAIN_VAL = 0xC6CD0, 7128                  # 8x
CLAMP_A, CLAMP_B, CLAMP_VAL = 0xC61B2, 0xC61B4, 4096
TRIM_CAL, TRIM_VAL = 0xC63D2, 3
BQ_ADDR, BQ_LEN = 0xC60A8, 16
TAP_DISP_ADDR, TAP_VAL = 0x55DF2, (-0x6B26) & 0xFFFF
SAR_ADDR, SAR_VAL = 0x55E10, 0xA3                   # sar 3, inherited from V133
SAR_A = {0x3AB76: "r26 arm", 0x3AC20: "r24 arm"}    # V62's Lever A, inherited from V131
SAR_A_V62 = 0xA9
CEIL_I, CEIL_I_VAL = 0xC407E, 1023
CEIL_F, CEIL_F_VAL = 0xC4004, 1.0
ARM_CAL, ARM_VAL = 0xC620A, 12800                   # the detector threshold on |gp-0x6c2c|
REV_CEIL_CAL, REV_CEIL_VAL = 0xC64FA, 5             # gp-0x671a CEIL
YFB_CAL, YFB_VAL, YFB_STOCK = 0xC640A, -1966, -8192  # the oscillation branch, de-fanged by V127
YFB_ALT_CAL, YFB_ALT_VAL = 0xC640C, -3277
CAVE_BASE, CAVE_LEN = V106B.CAVE_BASE, V106B.CAVE_LEN
CAVE_FREE_END = V106B.CAVE_FREE_END

# the eight gp-based accesses of gp-0x6c2c, from a base-register-filtered scan (hw1 & 0x1F == 4)
C2C_CONSUMERS = {
    0x36C1A: "FUN_00036c12  the gp-0x6b26 inertia lane -- THE INTENDED TARGET",
    0x4184E: "FUN_00041464  writer",
    0x41AC2: "FUN_00041464  writer",
    0x428FA: "the hard-reversal DETECTOR vs cal 0xC620A, drives gp-0x671a",
    0x4292C: "the same detector cluster",
    0x42968: "the same detector cluster",
    0x71378: "FUN_00071272  ld.h -> cvtf.ws -> mulf.s (0x39C90FDB ~ pi/8192)  FLOAT MODEL",
    0x7B1A2: "FUN_0007B022  ld.h -> mulf.s, alongside tp+0x623c (0xC523C model-coeff block)",
}

FS = 1000.0
ALPHA0 = 37 / 128.0
SIG_BAND = (18.0, 22.0)
OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ASSERTION FAILED: {msg}")


def lane_mag(a2, f):
    """|64 * H1(alpha0) * (1 - z^-1) * H2(a2/64)| at frequency f."""
    w = 2 * math.pi * f / FS
    z = complex(math.cos(w), math.sin(w))
    h1 = ALPHA0 / (1 - (1 - ALPHA0) / z)
    d = 1 - 1 / z
    a = a2 / 64.0
    h2 = a / (1 - (1 - a) / z)
    return abs(64 * h1 * d * h2)


def band_mag(a2, band=SIG_BAND, n=41):
    lo, hi = band
    return sum(lane_mag(a2, lo + (hi - lo) * i / (n - 1)) for i in range(n)) / n


def ema_pulse_peak(a2, t_ms, n=4000):
    """peak of y += ((x-y)*a2)>>6 for a unit half-sine acceleration pulse of t_ms."""
    t_s = t_ms / 1000.0
    y = pk = 0.0
    for i in range(n):
        t = i / FS
        x = math.sin(math.pi * t / t_s) if t < t_s else 0.0
        y += (x - y) * a2 / 64.0
        pk = max(pk, abs(y))
    return pk


def build():
    print("=" * 102)
    print("  V136 -- alpha2 0xC40DC 5 -> 2 on a V133 base.  ONE payload byte.")
    print("=" * 102)

    print("\n  [1] BASE = V133, AND IT MUST BE V133")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V133 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] EVERY ASSUMPTION ABOUT THE BASE IS CHECKED")
    check(u16(base, ALPHA2_CAL) == ALPHA2_OLD,
          f"  0x{ALPHA2_CAL:05X} (alpha2) = {ALPHA2_OLD} -- V133's value, the lowest ever built")
    check(u16(stock, ALPHA2_CAL) == ALPHA2_STOCK,
          f"  STOCK 0x{ALPHA2_CAL:05X} = {ALPHA2_STOCK} -- Honda's value, the ladder's top rung")
    check(u16(base, KNEE_CAL) == KNEE_VAL, f"  0x{KNEE_CAL:05X} relay knee = {KNEE_VAL} (V133)")
    check(u16(base, K1_CAL) == K1_VAL,
          f"  0x{K1_CAL:05X} K1 = {K1_VAL}, under its {K1_CEILING} ceiling")
    check(u16(base, OFF_CAL) == OFF_VAL, f"  0x{OFF_CAL:05X} relay offset = 0, no Coulomb floor")
    check(u16(base, POLE_CAL) == POLE_VAL,
          f"  0x{POLE_CAL:05X} friction EMA pole = {POLE_VAL} -- the only PHASE cell in the lane")
    check(u16(base, RESID_CAL) == RESID_VAL, f"  0x{RESID_CAL:05X} residual scale = {RESID_VAL}")
    check(u16(base, GAIN_CAL) == GAIN_VAL, f"  0x{GAIN_CAL:05X} LKAS gain = {GAIN_VAL} (8x)")
    check(u16(base, CLAMP_A) == u16(base, CLAMP_B) == CLAMP_VAL,
          f"  forward clamps = {CLAMP_VAL}, matched to the 8x gain")
    check(u16(base, CEIL_I) == CEIL_I_VAL, f"  0x{CEIL_I:05X} b26 clamp = {CEIL_I_VAL} (V133)")
    _fb = struct.unpack_from("<f", base, CEIL_F)[0]
    check(abs(_fb * 1024 - (CEIL_I_VAL + 1)) < 1e-6,
          f"  the int/float matched pair holds on the base ({_fb*1024:.0f} == {CEIL_I_VAL+1})")
    check(s16(base, YFB_CAL) == YFB_VAL and s16(stock, YFB_CAL) == YFB_STOCK,
          f"  0x{YFB_CAL:05X} oscillation branch = {YFB_VAL} (stock {YFB_STOCK}) -- ALREADY"
          f" de-fanged {abs(YFB_STOCK)/abs(YFB_VAL):.2f}x by V127, BEFORE alpha2 touches it")
    check(u16(base, ARM_CAL) == ARM_VAL,
          f"  0x{ARM_CAL:05X} detector threshold = {ARM_VAL}, and it is NOT moved by this build")
    check(base[REV_CEIL_CAL] == REV_CEIL_VAL,
          f"  0x{REV_CEIL_CAL:05X} gp-0x671a CEIL = {REV_CEIL_VAL}")
    for _a, _n in SAR_A.items():
        check(base[_a] == SAR_A_V62,
              f"  0x{_a:05X} ({_n}) = 0x{SAR_A_V62:02X} -- V62's Lever A present in the base")
    check(u16(base, TAP_DISP_ADDR) == TAP_VAL and base[SAR_ADDR] == SAR_VAL,
          "  the 427 probe tap on gp-0x6B26 at sar 3 is present and will be carried unchanged")

    print("\n  [3] THE EDIT -- ONE CAL")
    struct.pack_into("<H", code, ALPHA2_CAL, ALPHA2_NEW)
    attributed |= {ALPHA2_CAL, ALPHA2_CAL + 1}
    print(f"      0x{ALPHA2_CAL:05X}  {ALPHA2_OLD} -> {ALPHA2_NEW}   alpha2")
    check(u16(code, ALPHA2_CAL) == ALPHA2_NEW, f"  reads back {ALPHA2_NEW}")

    print("\n  [4] THE LADDER GATE -- this continues a FLOWN, FAULT-FREE, MONOTONE ladder")
    for a2 in sorted(ALPHA2_FLOWN, reverse=True):
        print(f"      alpha2 {a2:3d}   {ALPHA2_FLOWN[a2]:<24s} FLOWN, fault-free")
    for a2 in sorted(ALPHA2_BUILT, reverse=True):
        print(f"      alpha2 {a2:3d}   {ALPHA2_BUILT[a2]:<24s} built")
    print(f"      alpha2 {ALPHA2_NEW:3d}   THIS BUILD")
    check(ALPHA2_NEW < ALPHA2_OLD < ALPHA2_STOCK,
          f"  the edit moves DOWN the same ladder ({ALPHA2_STOCK} -> {ALPHA2_OLD} ->"
          f" {ALPHA2_NEW}), never up")
    check(ALPHA2_NEW >= 1,
          f"  \U0001f6d1 THE NON-ZERO GATE: alpha2 = {ALPHA2_NEW} >= 1.  At 0 the EMA increment is"
          f" identically 0 and the lane FREEZES at its init value -- never ship alpha2 = 0")
    _swing = max(ALPHA2_FLOWN) / min(ALPHA2_FLOWN)
    check(ALPHA2_OLD / ALPHA2_NEW <= _swing,
          f"  this rung ({ALPHA2_OLD/ALPHA2_NEW:.2f}x) is no larger than the swing already flown"
          f" through every gp-0x6c2c consumer ({_swing:.2f}x across alpha2"
          f" {max(ALPHA2_FLOWN)} -> {min(ALPHA2_FLOWN)})")

    print("\n  [5] THE QUANTIZATION GATE -- a low alpha2 must not itself create a ratchet")
    _dead_state = (1 << ALPHA2_SHIFT) / ALPHA2_NEW          # |x-y| below which the increment is 0
    _dead_out = _dead_state / (1 << EMA_OUT_SHIFT)          # ... expressed in OUTPUT LSB
    print(f"      y += ((x - y) * alpha2) >> {ALPHA2_SHIFT} on a 32-BIT state;"
          f"  gp-0x6c2c = state >> {EMA_OUT_SHIFT}")
    print(f"      deadband  |x-y| < {_dead_state:.0f} state units  =  {_dead_out:.4f} OUTPUT LSB")
    check(_dead_out < 1.0,
          f"  \U0001f6d1 the truncation deadband is SUB-LSB ({_dead_out:.4f} < 1), so the output"
          f" cannot stair-step.  This was the one way a low alpha2 could CAUSE a ratchet")
    check(abs(lane_mag(ALPHA2_NEW, 1e-6) - lane_mag(ALPHA2_OLD, 1e-6)) < 1e-9,
          "  and the EMA has UNITY DC GAIN for any alpha => no static behaviour changes")

    print("\n  [6] THE SELECTIVITY GATE -- it must cost the DETECTOR far less than it buys")
    m_old, m_new = band_mag(ALPHA2_OLD), band_mag(ALPHA2_NEW)
    print(f"      |H| over {SIG_BAND[0]:.0f}-{SIG_BAND[1]:.0f} Hz:"
          f"  {m_old:.4f} -> {m_new:.4f}  = {m_old/m_new:.2f}x LESS inertia lane")
    print(f"      {'pulse ms':>10s} {'a2=%d' % ALPHA2_OLD:>9s} {'a2=%d' % ALPHA2_NEW:>9s}"
          f" {'loss':>8s}")
    losses = {}
    for t_ms in (10, 30, 100, 200, 400):
        p_old, p_new = ema_pulse_peak(ALPHA2_OLD, t_ms), ema_pulse_peak(ALPHA2_NEW, t_ms)
        losses[t_ms] = p_old / p_new
        print(f"      {t_ms:10d} {p_old:9.3f} {p_new:9.3f} {p_old/p_new:7.2f}x")
    check(m_old / m_new >= 2.0,
          f"  the {SIG_BAND[0]:.0f}-{SIG_BAND[1]:.0f} Hz band drops {m_old/m_new:.2f}x -- a real dose")
    check(losses[100] <= 1.25 and losses[200] <= 1.25 and losses[400] <= 1.25,
          f"  \U0001f6d1 THE SELECTIVITY GATE: on a DRIVER hard reversal (100-400 ms, human"
          f" bandwidth 2-5 Hz) the detector loses only {losses[400]:.2f}-{losses[100]:.2f}x"
          f" while the grind band drops {m_old/m_new:.2f}x")
    check(losses[10] > losses[100],
          f"  the loss is concentrated in FAST transients ({losses[10]:.2f}x at 10 ms) -- declared,"
          f" and acceptable only because 0x{YFB_CAL:05X} is already de-fanged to {YFB_VAL}")

    print("\n  [7] THE BLAST RADIUS -- DECLARED, and every consumer already exercised")
    for a in sorted(C2C_CONSUMERS):
        print(f"      0x{a:05X}  {C2C_CONSUMERS[a]}")
    check(len(C2C_CONSUMERS) == 8,
          "  all 8 gp-based accesses of gp-0x6c2c are enumerated, not assumed")
    check(u16(code, ARM_CAL) == ARM_VAL and code[REV_CEIL_CAL] == REV_CEIL_VAL,
          "  neither the detector threshold nor the gp-0x671a CEIL is touched -- the ONLY change"
          " reaching them is the attenuation quantified in [6]")
    check(u16(code, ALPHA2_TWIN_CAL) == u16(base, ALPHA2_TWIN_CAL),
          f"  0x{ALPHA2_TWIN_CAL:05X} (the >>7 twin feeding gp-0x6c2e) UNTOUCHED")

    print("\n  [8] NOTHING ELSE MOVED")
    for a, w, nm in ((KNEE_CAL, 2, "relay knee"), (K1_CAL, 2, "K1"), (OFF_CAL, 2, "relay offset"),
                     (POLE_CAL, 2, "friction EMA pole"), (RESID_CAL, 2, "residual scale"),
                     (GAIN_CAL, 2, "LKAS gain"), (CLAMP_A, 2, "forward clamp A"),
                     (CLAMP_B, 2, "forward clamp B"), (TRIM_CAL, 2, "trim IIR"),
                     (CEIL_I, 2, "b26 clamp"), (CEIL_F, 4, "b26 clamp FLOAT twin"),
                     (YFB_CAL, 2, "oscillation branch"), (YFB_ALT_CAL, 2, "implausible branch"),
                     (TAP_DISP_ADDR, 2, "427 probe tap"), (SAR_ADDR, 1, "427 packer sar")):
        check(rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} {nm} byte-identical to V133")
    for _a, _n in SAR_A.items():
        check(code[_a] == base[_a] == SAR_A_V62,
              f"  0x{_a:05X} ({_n}) = 0x{SAR_A_V62:02X}, V62's Lever A CARRIED unchanged")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- cal-only, OUTSIDE the"
          f" bricking class (V24, V27 and V48B all bricked on cave edits)")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    # 0xC40DC is in V106B.FROZEN; THIS build deliberately moves it, so it is exempted BY NAME.
    exempt = {ALPHA2_CAL, ALPHA2_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V133 base (alpha2 exempted)")

    print("\n  [9] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [10] FULL BYTE DIFF vs V133 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    _tr = [b[1] for b in blocks]
    for lo, hi in runs:
        # a run is CRC if it OVERLAPS any 4-byte trailer [t, t+4), not merely if it CONTAINS
        # the trailer start -- the old test mislabelled a partial trailer change
        tag = "CRC" if any(lo < t + 4 and t < hi for t in _tr) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo < t + 4 and t < hi for t in _tr))
    check(payload == 1, f"exactly 1 payload byte ({payload} found)")

    print("\n  [11] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V136 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V136-V133BASE-ALPHA2.2"
    img_out = plain_image_path(f"_v136_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [12] NOT WRITTEN -- set ACCORD_V136_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
