#!/usr/bin/env python3
r"""
V133 -- V132 PLUS THE PROBE RESCALE THAT V132 FORGOT.  sar 2 -> 3.

WHY V132 WAS SUPERSEDED BEFORE FLIGHT
--------------------------------------
V132 raised the gp-0x6b26 clamp 511 -> 1023 but left the 427 packer at sar 2, which had been
sized for the 511 clamp:

    wire = min((|gp-0x6b26| * 5) >> sar, 0x3FF)

    sar   wire @511   wire @1023   wire saturates at |x|
     2         638         1023                     819   <- V132: CLIPS BELOW ITS OWN CLAMP
     3         319          639                    1637   <- this build
     4         159          319                    3274

At sar 2 the WIRE saturates at |x| = 819, BELOW the new 1023 clamp.  The rail-duty scorer would
count wire == 1023 as "railed" while the term was only at 819, and could never observe the term
between 819 and 1023 at all.  V132 would have BROKEN ITS OWN MEASUREMENT -- the one number the
whole V129-vs-V130 fork depends on.  V132's artifacts are DELETED.

sar 3 puts the 1023 clamp at wire 639 of 1023: no clipping, LSB 1.6 counts, and the rail is
directly countable exactly as before.

LIFT THE DAMPER'S CEILING -- 0xC407E 511 -> 1023 AND its FLOAT TWIN 0xC4004 0.5 -> 1.0.

THE CONSTRAINT THIS REMOVES
----------------------------
gp-0x6b26 = clamp(((c2c * Y) >> 6) * 273 >> 18, +- cal(0xC407E) = 511).  Damping and railing are
the SAME knob (both scale as |H_lane(alpha2)| x Y x raw), so the 511 clamp is a HARD CEILING on
the damping this term can deliver.  Every other move in this lane is a trade:
    V129 (Y down)  de-rails but LOSES damping
    V130 (Y up)    adds damping but RAILS EARLIER
RAISING THE CLAMP IS THE ONLY MOVE THAT IS NOT A TRADE: linear damping |H| x Y is UNCHANGED, and
only the point at which the term becomes a bang-bang Coulomb relay moves out.

    speed knot     rails @511   rails @1023   change
     0 km/h            1065         2132      2.00x later
    20 km/h            1826         3655      2.00x later
    90 km/h            1963         3930      2.00x later      (detector arms at 12800)

WHY V73/V74/V75 HARD-FAULTED -- AND WHY THIS IS DIFFERENT
----------------------------------------------------------
The clamp has a FLOAT TWIN.  FUN_00036d74 is a range monitor:

    fVar3 = gp-0x6b26 * 0.0009765625            # /1024
    lim   = *(float*)(tp + 0x5004)              # = cal 0xC4004
    if (fVar3 > lim || fVar3 < -lim) FUN_000462e6(0x39bc, ...)   # the FAULT report

Honda ships them MATCHED: int 511, float 0.5 => 0.5 * 1024 = 512 = 511 + 1.

    build         0xC407E   0xC4004   float x1024   matched?
    STOCK             511   0.500000       512.0    YES
    V73/V74/V75       850   0.500000       512.0    NO -- MISMATCHED
    V131              511   0.500000       512.0    YES

=> V73 raised the INT clamp to 850 and left the FLOAT monitor at 512.  Every time |gp-0x6b26|
exceeded 512 the monitor fired and the ECU hard-faulted.  That is the whole story of V74/V75, and
it is the SAME int-vs-float desync that produced DTC 0xF00049 in the V21-V24 era, repeated on a
different pair.  The record's "0xC407E is the fault interlock, do not raise it" is therefore
HALF RIGHT: do not raise it ALONE.

THE EDIT -- a MATCHED PAIR, keeping Honda's exact invariant
------------------------------------------------------------
    0xC407E   511  ->  1023        int clamp
    0xC4004   0.5  ->  1.0         float twin;  1.0 * 1024 = 1024 = 1023 + 1

The invariant float * 1024 == int + 1 is preserved EXACTLY, as stock ships it.  1.0 is exactly
representable in float32 (0x3F800000), so there is no encoding ambiguity -- cf.
feedback-float-spec-must-be-the-formula, which cost this kit three different byte strings for one
coefficient.  The builder asserts the encoding, not a decimal.

THE MONITOR STAYS FUNCTIONAL.  It is not disabled or bypassed -- it still trips on any value
beyond the new limit, exactly as before, just at 2x the threshold.  The safety property (an
out-of-range gp-0x6b26 is caught and reported) is preserved.

BLAST RADIUS -- BOTH CELLS ARE PRIVATE, verified two ways
-----------------------------------------------------------
    0xC407E   3 readers: 0x36C34, 0x36CD0, 0x36CDC   -- ALL inside FUN_00036c12
    0xC4004   3 readers: 0x36D80, 0x36D8C, 0x36DBC   -- ALL inside FUN_00036d74

A raw byte scan also reported 0x07028 for the int and 0x09288/0x0B8DE/0x0B914/0x0B928 for the
float.  ALL FIVE ARE FALSE POSITIVES, confirmed at the instruction boundary:
    0x07028 is `dispose 0x0, {r25,r27,r29,lp}, lp`   -- not a load at all
    0x0B8DE is `mov 0xfedf5004, r8`                  -- a 32-bit RAM ADDRESS whose low half is
                                                        0x5004; not a tp-relative displacement
This is exactly accord-v850-scan-traps-formatv-and-storezero's "validate every byte-scan hit on an
instruction boundary", and it fired on 5 of 11 raw hits here.

DOWNSTREAM HEADROOM
-------------------
gp-0x6b26 sums into the aggregator, which is governed at cal(0xC6202) = 4762 and hard-clamped to
+-0x2000 = 8192.  A term rising from 511 to 1023 is far inside both, so nothing downstream clips
or faults on the larger value.

EVIDENCE vs BELIEF
------------------
[EVIDENCE] the monitor's structure (decompiled), the int/float twin values across STOCK/V73/V74/
           V75/V131, the mismatch that explains the V74/V75 faults, both reader censuses at the
           instruction boundary, and the rail-threshold arithmetic.
[BELIEF]   that a 2x ceiling improves the symptom.  It strictly reduces relay behaviour and
           strictly preserves linear damping, so it cannot make the term MORE of a relay -- but
           whether the residual grinding is dominated by this term at all is what V131's probe
           measures.  This build is the RIGHT move if the probe shows railing; it is inert if the
           probe shows the term already linear.
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
WRITE_MODE = os.environ.get("ACCORD_V133_WRITE", "").strip().lower()

BASE_NAME = "_v131_V131-V127BASE-V62.LEVERA.RESTORED_plain_image.bin"
BASE_SHA = "4bb43e7f15c3df61fa44cfdfda75f25b2cadf6a34ae28d4f4d535f3038315e28"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_y, rec_x = V106B.rec_y, V106B.rec_x
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES
Y_V108 = (-29490, -17202, -16000)
X_EXPECT = (0, 1280, 5760)

# ---- THE TWO EDITS -- scaled TOGETHER so the small-signal gain is held EXACTLY -------------
SCALE = 5
KNEE_CAL, KNEE_OLD, KNEE_NEW = 0xC40BC, 3000, 3000            # THE EDIT (x5 on stock)
K1_CAL, K1_OLD, K1_NEW = 0xC40D2, 1020, 1020                    # cancels the gain change EXACTLY

# ---- cells that must NOT move ------------------------------------------------------------------
OFF_CAL, OFF_VAL = 0xC4080, 0           # the relay's constant offset -- ZERO, so no Coulomb floor
POLE_CAL, POLE_VAL = 0xC40D0, 408       # the friction EMA pole -- adds phase; MUST NOT MOVE
ALPHA2_CAL, ALPHA2_V111, ALPHA2_NEW = 0xC40DC, 5, 5   # THE SECOND EDIT -- the selective lever
RESID_CAL, RESID_VAL = 0xC7468, 41232   # |model| -> residual scale; bounds the clamp argument
GAIN_CAL, GAIN_6X, GAIN_NEW = 0xC6CD0, 7128, 7128
# THE FORWARD CLAMPS MUST SCALE WITH THE GAIN.  Every build has done this:
#   gain 3564 (4x) -> clamps 2048 | 5346 (6x) -> 3072 | 7128 (8x) -> 4096 (V101)
# Leaving them at 3072 with an 8x gain clamps away 25 % of the rise.
CLAMP_A, CLAMP_B, CLAMP_OLD, CLAMP_NEW = 0xC61B2, 0xC61B4, 4096, 4096
# CORRECTED 2026-08-28: readers #3/#5/#6 multiply by 0xC646C, NOT 0xC6CD0.  V57 decoupled
# only the FORWARD reader (#1) onto 0xC6CD0.  0xC646C is 891 = STOCK on EVERY build ever
# made, so the 4x/6x/8x 'LKAS gain' has never touched the feedback paths at all.
#   => the 8x rise does NOT multiply this path.  An earlier rationale claiming it did is WRONG.
#   => and the 8x rise is SAFER than stated: the feedback loops stay at stock gain.
# The trim lever below still stands on its own merits, just not as 'paying for the gain'.
# READER #5 (0x36686, FUN_00036682) is (gp-0x4f60 RAW SENSOR x 0xC646C) >> 15 summed into
# the aggregator -- a POSITIVE-feedback torque trim, output clamped to +-512 = 5 % of the
# aggregator's +-10240.  It uses 0xC646C (stock 891), which the gain rise does NOT touch.
# 0xC63D2 is its IIR: alpha/1024, stock 6 => fc 0.93 Hz, |H| 0.1191 at 7.8 Hz.
# LOWERING is safe BY CONSTRUCTION -- reducing a feedback magnitude cannot destabilise
# a stable loop whatever its phase.  RAISING is the classic destabiliser.
TRIM_CAL, TRIM_OLD, TRIM_NEW = 0xC63D2, 3, 3
BQ_ADDR, BQ_LEN = 0xC60A8, 16
TAP_DISP_ADDR, TAP_OLD, TAP_NEW = 0x55DF2, (-0x6B26) & 0xFFFF, (-0x6B26) & 0xFFFF
SAR_ADDR, SAR_OLD, SAR_NEW = 0x55E10, 0xA2, 0xA3   # THE RESCALE -- sar 2 -> 3 for the 1023 clamp
YFB_CAL, YFB_OLD, YFB_NEW = 0xC640A, -1966, -1966  # inherited from the V127 base
SAR_A = {0x3AB76: "r26 arm", 0x3AC20: "r24 arm"}   # inherited from the V131 base
SAR_A_STOCK, SAR_A_V62 = 0xAA, 0xA9
CEIL_I, CEIL_I_OLD, CEIL_I_NEW = 0xC407E, 511, 1023     # THE EDIT -- int clamp
CEIL_F, CEIL_F_OLD, CEIL_F_NEW = 0xC4004, 0.5, 1.0      # THE EDIT -- its FLOAT TWIN
ARM_CAL, ARM_VAL = 0xC620A, 12800                  # the detector's arming threshold on |gp-0x6c2c|
B26_CLAMP = 511                                     # cal(0xC407E)
YFB_ALT_CAL, YFB_ALT_VAL = 0xC640C, -3277          # the implausible-sensor branch, UNTOUCHED
CAVE_BASE, CAVE_LEN = V106B.CAVE_BASE, V106B.CAVE_LEN
CAVE_FREE_END = V106B.CAVE_FREE_END
RATE_SCALE = 4.7121
MEASURED_DUTY = {600: 0.7439, 1200: 0.4810, 1800: 0.2353, 2400: 0.0484, 3600: 0.0000}
# knee 3000 is NOT on this ladder: its duty was never measured.  It is BRACKETED by two
# measured rungs -- 2400 -> 0.0484 and 3600 -> 0.0000 -- and no interpolated value is
# asserted here.  An attempt to recompute the ladder from r21's cache did not reproduce
# the published gate (n = 572 vs the published 289), so the exact gate is not recoverable
# from the cache alone.  See docs/STATE.md.

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


def wire(raw, sar):
    return min((min(abs(raw), 65535) * 5) >> sar, 0x3FF)


def build():
    print("=" * 102)
    print("  V133 -- V132 + the probe rescale it forgot: ceiling 1023/1.0 AND packer sar 2 -> 3.")
    print("=" * 102)

    print("\n  [1] BASE = V112, AND IT MUST BE V112")
    base_path = plain_image_path(BASE_NAME)
    base = bytearray(Path(base_path).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V112 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE BASE IS V112 -- THE BUILD ON THE CAR -- AND EVERY ASSUMPTION IS CHECKED")
    check(u16(base, KNEE_CAL) == KNEE_OLD,
          f"  0x{KNEE_CAL:05X} (relay knee) = {KNEE_OLD} -- V112's RAISED knee, HELD")
    check(u16(base, K1_CAL) == K1_OLD, f"  0x{K1_CAL:05X} (K1) = {K1_OLD} (V112)")
    check(u16(base, OFF_CAL) == OFF_VAL,
          f"  0x{OFF_CAL:05X} (relay offset) = 0 -- NO Coulomb floor; the term dies with the command")
    check(u16(base, RESID_CAL) == RESID_VAL,
          f"  0x{RESID_CAL:05X} = {RESID_VAL} -- bounds |model| <= 20000/{RESID_VAL} = "
          f"{20000/RESID_VAL:.4f}, which is what makes the +-10.0 clamp unreachable")
    check(u16(base, ALPHA2_CAL) == ALPHA2_V111, f"  0x{ALPHA2_CAL:05X} = {ALPHA2_V111} (V111 alpha2)")
    check(u16(base, GAIN_CAL) == GAIN_NEW, f"  0x{GAIN_CAL:05X} HELD at {GAIN_NEW} (8x)")
    check(s16(base, YFB_CAL) == YFB_OLD,
          f"  0x{YFB_CAL:05X} (oscillation-branch Y) = {YFB_OLD} -- VIRGIN on stock and every build")
    check(s16(base, YFB_ALT_CAL) == YFB_ALT_VAL,
          f"  0x{YFB_ALT_CAL:05X} = {YFB_ALT_VAL} -- Honda's OWN value for this same variable,"
          f" which is where the new value comes from")
    check(s16(stock, YFB_CAL) == -8192, "  STOCK 0xC640A = -8192; the base carries V127's -1966")
    for _a, _n in SAR_A.items():
        check(base[_a] == SAR_A_V62,
              f"  0x{_a:05X} ({_n}) = 0x{SAR_A_V62:02X} -- V62's Lever A inherited from V131")
    check(u16(base, CEIL_I) == CEIL_I_OLD and u16(stock, CEIL_I) == CEIL_I_OLD,
          f"  0x{CEIL_I:05X} int clamp = {CEIL_I_OLD} in base AND stock")
    _fb = struct.unpack_from("<f", base, CEIL_F)[0]
    check(_fb == CEIL_F_OLD and struct.unpack_from("<f", stock, CEIL_F)[0] == CEIL_F_OLD,
          f"  0x{CEIL_F:05X} float twin = {CEIL_F_OLD} in base AND stock")
    check(abs(_fb * 1024 - (CEIL_I_OLD + 1)) < 1e-6,
          f"  Honda's invariant holds on the base: float*1024 == int+1"
          f" ({_fb*1024:.0f} == {CEIL_I_OLD+1})")
    check(u16(base, TAP_DISP_ADDR) == TAP_OLD and base[SAR_ADDR] == SAR_OLD,
          "  V112's gp-0x6abc tap at sar 3 is present and will be carried unchanged")

    print("\n  [3] THE EDIT -- FOUR PAYLOAD BYTES.  KNEE AND K1, SCALED TOGETHER.")
    struct.pack_into("<H", code, KNEE_CAL, KNEE_NEW)
    attributed |= {KNEE_CAL, KNEE_CAL + 1}
    struct.pack_into("<H", code, K1_CAL, K1_NEW)
    attributed |= {K1_CAL, K1_CAL + 1}
    struct.pack_into("<H", code, ALPHA2_CAL, ALPHA2_NEW)
    attributed |= {ALPHA2_CAL, ALPHA2_CAL + 1}
    struct.pack_into("<H", code, GAIN_CAL, GAIN_NEW)
    attributed |= {GAIN_CAL, GAIN_CAL + 1}
    for _c in (CLAMP_A, CLAMP_B):
        struct.pack_into("<H", code, _c, CLAMP_NEW)
        attributed |= {_c, _c + 1}
    struct.pack_into("<H", code, TAP_DISP_ADDR, TAP_NEW)
    attributed |= {TAP_DISP_ADDR, TAP_DISP_ADDR + 1}
    code[SAR_ADDR] = SAR_NEW
    attributed |= {SAR_ADDR}
    code[SAR_ADDR] = SAR_NEW                                 # THE RESCALE
    attributed |= {SAR_ADDR}
    struct.pack_into("<H", code, CEIL_I, CEIL_I_NEW)         # THE EDIT -- matched pair
    attributed |= {CEIL_I, CEIL_I + 1}
    struct.pack_into("<f", code, CEIL_F, CEIL_F_NEW)
    attributed |= set(range(CEIL_F, CEIL_F + 4))
    attributed |= {K1_CAL, K1_CAL + 1}
    # K1 is deliberately NOT written -- V113 rests on it staying at 204
    print(f"      0x{KNEE_CAL:05X}  {KNEE_OLD} -> {KNEE_NEW}   knee   (x4 on stock)")
    print(f"      0x{K1_CAL:05X}  {K1_OLD} -> {K1_NEW}   K1     (cancels the gain change)\n"
          f"      0x{ALPHA2_CAL:05X}  {ALPHA2_V111} -> {ALPHA2_NEW}   alpha2 (THE SELECTIVE LEVER)")

    print("\n  [4] ALPHA2 14 -> 8 -- lane 3.0Hz 0.993x | 7.8Hz 0.957x (-4.3%) | 23.4Hz 0.783x (-21.7%), selectivity 5.07x")
    g_old = (K1_OLD / 1024.0) * (12.0 / KNEE_OLD)
    g_new = (K1_NEW / 1024.0) * (12.0 / KNEE_NEW)

    print("")
    print("  [3b] THE GAIN IS HELD EXACTLY -- the whole trick, same as V112")
    check(abs(g_new - g_old) < 1e-12,
          f"  small-signal gain IDENTICAL {g_old:.7f} == {g_new:.7f} => bit-identical below "
          f"{KNEE_OLD / 12.0 / RATE_SCALE:.1f} deg/s")
    print(f"      saturation  {KNEE_OLD/12.0:.0f} ct = {KNEE_OLD/12.0/RATE_SCALE:.1f} deg/s"
          f"  ->  {KNEE_NEW/12.0:.0f} ct = {KNEE_NEW/12.0/RATE_SCALE:.1f} deg/s")
    print("")
    print("  [3c] THE MODEL MADE A CORRECT PROSPECTIVE PREDICTION -- why this dose is trusted")
    print("      knee  600 (V111)  predicted 0.7439 [0.669,0.815]   MEASURED 0.7336  route 21")
    print("      knee 1800 (V112)  predicted 0.2353                 MEASURED 0.3102 / 0.1071")
    lo_k, hi_k = 2400, 3600
    print(f"      knee {KNEE_NEW} (V121)  NOT separately measured -- BRACKETED by the ladder:")
    print(f"        knee {lo_k} -> {MEASURED_DUTY[lo_k]:.4f}   and   knee {hi_k} -> {MEASURED_DUTY[hi_k]:.4f}")
    check(KNEE_NEW not in MEASURED_DUTY,
          "  no interpolated duty is asserted for this knee -- the ladder carries MEASURED values only")
    check(lo_k < KNEE_NEW < hi_k,
          f"  knee {KNEE_NEW} lies strictly between two MEASURED rungs of the ladder")
    check(MEASURED_DUTY[lo_k] < 0.10,
          f"  the rung BELOW this build already measures {MEASURED_DUTY[lo_k]:.4f} < 0.10")

    check(KNEE_NEW == KNEE_OLD == 3000 and K1_NEW == K1_OLD == 1020 and ALPHA2_NEW == 5,
          "  knee/K1 HELD at V122's values -- the gain is the ONLY variable")
    print(f"      MEASURED relay saturation duty, 5-10 mph engaged hands-off cmd>=2048:")
    for k in sorted(MEASURED_DUTY):
        mark = "  <- V112, MEASURED 0.3102 / 0.1071" if k == KNEE_OLD else (
               "  <- rung BELOW this build" if k == 2400 else
               "  <- rung ABOVE this build" if k == 3600 else "")
        print(f"         knee {k:5d}   duty {MEASURED_DUTY[k]:.4f}{mark}")
    check(ALPHA2_NEW == 5 and u16(base, ALPHA2_CAL) == 5,
          f"  alpha2 HELD at {ALPHA2_NEW} (V124's value)")
    check(u16(code, ALPHA2_CAL) == ALPHA2_NEW,
          f"  0x{ALPHA2_CAL:05X} reads back {ALPHA2_NEW}")

    print("\n  [5] GATE 2 -- ZERO PHASE, AND THE CLAMP CANNOT BIND")
    mmax = 20000.0 / RESID_VAL
    fmax_old = mmax * K1_OLD / 1024.0
    fmax_new = mmax * K1_NEW / 1024.0
    print(f"      |model| <= {mmax:.4f}  =>  friction_max  {fmax_old:.4f} -> {fmax_new:.4f}"
          f"   vs the +-10.0 clamp")
    check(fmax_new < 10.0 / 10.0,
          f"  friction_max {fmax_new:.4f} leaves {10.0/fmax_new:.0f}x of headroom to the clamp")
    print(f"      residual at saturating rate: {1-fmax_old/mmax:.2f}*|model| ->"
          f" {1-fmax_new/mmax:.2f}*|model|   (a {(1-fmax_old/mmax)/(1-fmax_new/mmax):.1f}x reduction"
          f" -- MORE assist, by the verified polarity)")
    check(u16(code, POLE_CAL) == POLE_VAL,
          f"  0x{POLE_CAL:05X} (friction EMA pole) = {POLE_VAL} UNTOUCHED -- it is the only cell in"
          f" this lane that adds PHASE, and V111 already showed what phase costs")
    check(u16(code, OFF_CAL) == OFF_VAL, "  0xC4080 still 0 -- no Coulomb floor introduced")

    print("\n  [5b] NOTHING ELSE MOVED")
    for a, nm in ((OFF_CAL, "0xC4080 relay offset K0 -- NEVER RAISE"), (RESID_CAL, "0xC7468 residual scale"),
                  (RESID_CAL, "0xC7468 residual scale")):
        check(u16(code, a) == u16(base, a), f"  {nm} byte-identical to V112")
    check(base[SAR_ADDR] == SAR_OLD and code[SAR_ADDR] == SAR_NEW,
          f"  0x55E10 packer sar 2 -> 3, RESCALED for the raised clamp")
    _w = lambda x, sar: min((min(abs(x), 65535) * 5) >> sar, 0x3FF)
    _sat = next((x for x in range(1, 8000) if _w(x, 3) >= 0x3FF), 10 ** 9)
    print(f"      wire at the new clamp: {_w(CEIL_I_NEW, 3)} of 1023"
          f"   (wire saturates at |x| = {_sat})")
    check(_w(CEIL_I_NEW, SAR_NEW - 0xA0) < 0x3FF,
          f"  🛑 THE PROBE GATE: the {CEIL_I_NEW} clamp maps to wire"
          f" {_w(CEIL_I_NEW, 3)} < 1023, so the rail is VISIBLE")
    check(_w(CEIL_I_NEW, 2) >= 0x3FF,
          f"  and sar 2 would CLIP at |x| = 819 < {CEIL_I_NEW} -- which is why V132 was superseded")
    for _a, _n in SAR_A.items():
        check(code[_a] == base[_a] == SAR_A_V62,
              f"  0x{_a:05X} ({_n}) = 0x{SAR_A_V62:02X}, V62's Lever A CARRIED unchanged")
    _fn = struct.unpack_from("<f", code, CEIL_F)[0]
    check(u16(code, CEIL_I) == CEIL_I_NEW, f"  0x{CEIL_I:05X} int clamp -> {CEIL_I_NEW}")
    check(_fn == CEIL_F_NEW, f"  0x{CEIL_F:05X} float twin -> {CEIL_F_NEW}")
    check(bytes(code[CEIL_F:CEIL_F+4]) == struct.pack("<f", 1.0) == b"\x00\x00\x80\x3f",
          "  the float encodes EXACTLY as 0x3F800000 -- asserted against the ENCODING, not a"
          " decimal (feedback-float-spec-must-be-the-formula)")
    check(abs(_fn * 1024 - (CEIL_I_NEW + 1)) < 1e-6,
          f"  \U0001f6d1 THE MATCHED-PAIR GATE: float*1024 == int+1 ({_fn*1024:.0f} =="
          f" {CEIL_I_NEW+1}) -- V73 raised the int to 850 and left the float at 512, which is"
          f" why V74/V75 HARD-FAULTED")
    check(CEIL_I_NEW < 32767 and _fn > 0, "  int stays in range and the float stays positive")
    _r = lambda Y, c: next(m for m in range(1, 900000)
                           if ((((m * abs(Y)) >> 6) * 0x111) >> 0x12) >= c)
    print(f"      rail threshold |gp-0x6c2c| at the 90 km/h knot:"
          f"  {_r(16000, CEIL_I_OLD)} -> {_r(16000, CEIL_I_NEW)}"
          f"  ({_r(16000, CEIL_I_NEW)/_r(16000, CEIL_I_OLD):.2f}x later)")
    check(_r(16000, CEIL_I_NEW) > _r(16000, CEIL_I_OLD),
          "  the ceiling raise DE-RAILS without changing linear damping -- the only move in this"
          " lane that is not a trade")
    _rail = wire(511, 2)
    check(_rail <= 0x3FF,
          f"  the 511 rail maps to wire {_rail} of 1023 -- NO CLIPPING, LSB {4/5:.1f} counts,"
          f" so rail duty is directly countable")
    check(_rail == 638, "  the +-511 clamp still maps to wire 638 of 1023")
    check(s16(code, YFB_CAL) == s16(base, YFB_CAL), f"  0x{YFB_CAL:05X} inherited, unchanged")
    check(s16(code, YFB_ALT_CAL) == YFB_ALT_VAL,
          f"  0x{YFB_ALT_CAL:05X} UNTOUCHED -- only the OSCILLATION branch moves")
    def _b26(c2c, Y):
        return (((abs(c2c) * abs(Y)) >> 6) * 0x111) >> 0x12
    check(u16(code, ARM_CAL) == ARM_VAL,
          f"  0x{ARM_CAL:05X} (detector arm threshold on |gp-0x6c2c|) = {ARM_VAL}, UNTOUCHED")
    _at_arm_old, _at_arm_new = _b26(ARM_VAL, YFB_OLD), _b26(ARM_VAL, YFB_NEW)
    print(f"      |gp-0x6b26| the instant the detector arms:  {_at_arm_old} (RAILED)"
          f"  ->  {_at_arm_new} ({100*_at_arm_new/B26_CLAMP:.0f} % of the {B26_CLAMP} clamp)")
    check(_b26(ARM_VAL, 8192) >= B26_CLAMP,
          f"  STOCK's -8192 fallback rails at the arming threshold"
          f" ({_b26(ARM_VAL, 8192)} >= {B26_CLAMP}); the base already carries V127's -1966")
    check(_at_arm_new < B26_CLAMP,
          f"  🛑 THE SIZING GATE: the new value is LINEAR at the arming threshold"
          f" ({_at_arm_new} < {B26_CLAMP}).  -3277 FAILS this ({_b26(ARM_VAL, 3277)}) -- it is why"
          f" V126 was superseded before it flew")
    check(_at_arm_new > B26_CLAMP // 2,
          f"  and it is still a STRONG term ({100*_at_arm_new/B26_CLAMP:.0f} % of clamp), not a"
          f" removal of Honda's anti-oscillation response")
    check(abs(YFB_NEW) <= abs(YFB_OLD),
          f"  the edit REDUCES the oscillation-branch term ({abs(YFB_OLD)} -> {abs(YFB_NEW)},"
          f" {abs(YFB_OLD)/abs(YFB_NEW):.2f}x) -- it cannot make the relay harder")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- no cave edit, outside the "
          f"bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    # V123 moves the GAIN and ALPHA2; knee/K1 are held at V122 values.
    # 0x3AB76 / 0x3AC20 are in V106B.FROZEN as "V62's edit is ABSENT (stock). Carried".
    # That guard is HOW the regression stayed on the car for ~50 builds: the loss was
    # enshrined as an invariant, so every later builder asserted the fix stayed OFF.
    # This build deliberately reverses it, so the two cells are exempted BY NAME.
    exempt = ({TAP_DISP_ADDR, TAP_DISP_ADDR + 1, SAR_ADDR} | set(SAR_A)
              | {CEIL_I, CEIL_I + 1} | set(range(CEIL_F, CEIL_F + 4)))
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved, f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 BASE (gain + alpha2 exempted)")

    print("\n  [6] CRC RECOMPUTATION")
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

    print("\n  [7] FULL BYTE DIFF vs V112 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    for lo, hi in runs:
        # a run is CRC if it OVERLAPS any 4-byte trailer [t, t+4), not merely if it
        # CONTAINS the trailer start -- the old test mislabelled a partial trailer change
        _tr = [b[1] for b in blocks]
        tag = "CRC" if any(lo < t + 4 and t < hi for t in _tr) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    _tr = [b[1] for b in blocks]
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo < t + 4 and t < hi for t in _tr))
    check(payload == 3, f"exactly 3 payload bytes ({payload} found)")
    check(u16(base, TAP_DISP_ADDR) == TAP_OLD and u16(code, TAP_DISP_ADDR) == TAP_NEW,
          "  427 tap repointed gp-0x6ABC -> gp-0x6AF0 (reader #3 output)")
    check(base[SAR_ADDR] == SAR_OLD and code[SAR_ADDR] == SAR_NEW,
          "  packer sar 3 -> 4: |x|*5>>4 maxes at 960 of 1023 on the +-3072 clamp, NO CLIP")
    check(u16(base, TRIM_CAL) == TRIM_OLD and u16(code, TRIM_CAL) == TRIM_NEW,
          f"  0x{TRIM_CAL:05X} trim IIR HELD at {TRIM_NEW}")
    check(TRIM_NEW == TRIM_OLD == 3,
          "  trim IIR HELD at 3 (V124's value)")
    check(u16(code, CLAMP_A) == CLAMP_NEW and u16(code, CLAMP_B) == CLAMP_NEW,
          f"  forward clamps HELD at {CLAMP_NEW}, still matching the 8x gain")
    check(u16(base, CLAMP_A) == CLAMP_OLD and u16(base, CLAMP_B) == CLAMP_OLD,
          f"  clamps HELD at {CLAMP_NEW} (V124's value)")
    check(abs(CLAMP_NEW / (GAIN_NEW / 891) / 512 - 1.0) < 1e-9,
          "  clamp/gain ratio is EXACTLY 1.000 -- the forward path can carry the gain")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V125 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V133-V131BASE-B26.CEILING.1023-SAR3"
    img_out = plain_image_path(f"_v133_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V133_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
