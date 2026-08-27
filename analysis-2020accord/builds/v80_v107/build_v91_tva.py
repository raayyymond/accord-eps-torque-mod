#!/usr/bin/env python3
r"""builds/v80_v107/build_v91_tva.py -- V91 = the FLOWN V90 + 12 CALIBRATION BYTES. No cave change, no code change.

    base   _v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin
           sha256 28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db

    0xD7A5C  mode 26 friction/damping-comp LERP Y row  (-9830,-5734,-1966) -> (-14745,-8601,-2949)
    0xD7A6C  mode 27 friction/damping-comp LERP Y row  (-9830,-5734,-1966) -> (-14745,-8601,-2949)

TWELVE BYTES. Two int16 triples. Nothing else moves: the V90 cave at 0xC4B34, the CAN 427 repoint at
0x55DF2, V89's K1 at 0xC40D2, Lever B, the ratchet fix -- all carried byte-identical.

===================================================================================================
🛑🛑 HONEST LABELLING -- READ THIS BEFORE THE PHYSICS
===================================================================================================
> **V91 is the SAME LEVER at the SAME x1.5 DOSE that flew on V74 and V75. Both of those flights
> HARD-FAULTED with a latched total loss of power steering. The single difference is `0xC407E`: every
> artefact that ever carried this dose also carried 850; V91 carries Honda's 511, one count below the
> DTC-0x1d monitor's 512 trip, so the monitor is structurally untrippable at any multiplier.
> ZERO flights have ever separated the dose from the 850 interlock -- the separation is STRUCTURAL,
> never empirical. V81 (route 67, fault-free) is a control for the INTERLOCK ONLY: it is byte-stock on
> the friction row in all 34 modes, so it says nothing about the dose.
> Writing only modes 26/27 is a DELIBERATE NARROWING from V74/V75's 14 records, not a reproduction.**

Verified from the images, not from the build scripts (this script re-verifies it at run time):
    _v74_engagedcols_x0_12_addonly_plain_image.bin   friction Y != stock on modes
    _v75_CY0.566-EX1.200_magprobe_plain_image.bin      [2,3,5,10,11,14,15,17,23,26,27,29,32,33]
                                                       = 14 records, both -> (-14745,-8601,-2949)
                                                       both with 0xC407E = 850
    (builds/v50_v79/build_v74_tva.py's own header comment says "13 modes". The IMAGE says 14. The image wins.)
V91 writes {26, 27} -- a strict 2-of-14 subset, and the only two that are ENGAGED on this car.

===================================================================================================
WHAT CLASS OF BUILD THIS IS -- against the whole arc since V38
===================================================================================================
V38-V52 authority/filters/poles/caves - V53-V61 telemetry + lane mutes - V62-V73 the rate lane
(r24/r26) - V74-V83a the base-assist damper - V84-V86B damper reverts and phase - V87 subtractive
measurement - V88 Lever B restored - V89 the first build to touch the PLANT MODEL (K1 friction) -
V90 pure instrument.

**V91 is a RE-RUN of V74/V75's LEVER D', narrowed to the two engaged modes and carried on Honda's
511 interlock instead of 850.** It is NOT a new lever. What is different this time, and why a
different outcome is plausible:
    1. 0xC407E = 511 (Honda's own value), not 850. V74/V75's hard fault is attributed to 850 raising
       the clamp ABOVE the DTC-0x1d monitor's 512 trip (see the 0xC407E memory). At 511 the clamp
       output can never reach 512, so that monitor is structurally untrippable at ANY multiplier.
       🛑 This is a STRUCTURAL argument. No flight has ever separated the dose from the interlock.
    2. 14 records -> 2. Modes 24/25 (manual) stay byte-stock, so a manual-vs-engaged contrast exists
       in the same drive. V74/V75 moved both arms and could not separate them.
    3. It rides V90's four-rung instrument: gp-0x6b26 is the lane this lever scales, and CAN 427
       now CARRIES gp-0x6b26 directly. V74/V75 flew blind on this signal; V91 measures its own dose.
    4. This is the first friction-family build since V89 that moves a CALIBRATION rather than the
       plant model. K1 (0xC40D2 = 204) is carried unchanged, so V89's lever is NOT re-litigated.

===================================================================================================
THE LANE -- where 0xCBE74 sits
===================================================================================================
    gp-0x4f50 (resolver / motor rate)
        |
        v  FUN_00041464   3-stage cascade
    gp-0x6c2c   (motor-rate derivative)
        |
        v  FUN_00036c12   applies the 0xCBE74 PER-MODE LERP over voted vehicle speed
    gp-0x6b26   clamped to +/- 0xC407E = +/- 511          <-- V90's CAN 427 and cave bit b7 read HERE
        |
        +--> Path 1  0x3AC98 in FUN_0003AA2C   the AGGREGATOR: direct, UNWEIGHTED, plain `add`,
        |                                      NO negation
        +--> Path 2  0x3815C in FUN_00038148   the OBSERVER, weight 0xC63A6 = 1024

The Y row is NEGATIVE, so gp-0x6b26 carries the OPPOSITE sign to gp-0x6c2c => the term is genuinely
DISSIPATIVE (it opposes motor rate). A uniform x1.5 on all three Y knots is a REAL SCALAR MULTIPLY:
it adds ZERO phase at any frequency, changes no sign anywhere, and does not move a breakpoint --
the X axis is untouched. It scales the damping coefficient and nothing else.

===================================================================================================
x1.5 IS FORCED BY THREE INDEPENDENT BOUNDS, NOT CHOSEN
===================================================================================================
(1) THE CLIP ENVELOPE. Route 77 measured |gp-0x6b26| ENGAGED MAX = 319.1 counts at the stock Y row
    against the +/-511 rail, which permits <= 1.6014.

    multiplier   predicted |gp-0x6b26| max   vs the 511 rail
       1.0                 319.1              37.6 % headroom
       1.5                 478.7               6.3 % headroom     <-- V91. clip-free.
       1.6                 510.6               0.1 % headroom     on the edge
       2.0                 638.2              CLIPS

    🛑 A CLIPPED lane is `sign(gp-0x6c2c) x 511` -- a Coulomb RELAY, which is exactly the V80
      mechanism ("worst grinding ever").

(2) INT32 WRAPAROUND in FUN_00036c12's `x 0x111` multiply, which is UNCLAMPED and PRECEDES the
    0xC407E comparison -- so the clamp cannot save it; it wraps arbitrarily and corrupts one tick of
    gp-0x6b26. Impossible only for M <= 1.6005, proven against gp-0x6c2c's own hard +/-32,000 bound
    rather than against any measured distribution -- so it holds in emergency manoeuvres, kerb
    strikes and fault-adjacent transients that route 77 never sampled. See ASSERTION 12 below.

(3) IT IS THE SAME DOSE THAT FLEW ON V74/V75, so V91 changes exactly ONE thing versus those two
    builds: the interlock.

⚠ THE ~1.60 AGREEMENT BETWEEN (1) AND (2) IS NOT A SHARED MECHANISM AND NOT AN OBSERVED DESIGN
  INTENT. The clamp binds at |gp-0x6c2c| ~ 3,200; the overflow binds at ~34,000 -- an ORDER OF
  MAGNITUDE apart. They are two independent constraints that happen to coincide near 1.60. No
  claim of design intent is made or established.
⚠ int16 STORAGE headroom is a DIFFERENT and much LOOSER, NON-BINDING bound: k_max = 32768/9830 =
  3.3335, binding on Y[0] against int16 MIN. It is NOT the dose ceiling and must never be quoted
  as one.

===================================================================================================
ASSERTION 12 -- THE INT32 OVERFLOW BOUND. Verified here in Ghidra, NOT inherited.
===================================================================================================
`decompile_function 0x36c12` then `disassemble_function 0x36c12` (GhidraMCP, code.bin), with every
constant re-read LE from the BUILT IMAGE by Python as the second method:

    00036c1a  ld.h  -0x6c2c[gp],r9        x, the motor-rate derivative
    00036c22  ori   0xfa01,r0,r11         64001                            bytes 805e01fa
    00036c26  addi  0x7d00,r9,r14         x + 32000                        bytes 0976007d
    00036c2a  cmp   r11,r14
    00036c2c  cmovnc 0x0,r9,r13            r13 = (x+32000 >=u 64001) ? 0 : x
                                          => |x| > 32000 ZEROES the term  => |x_gated| <= 32000
    ...
    00036cbe  mulh  r12,r13               r13 = sVar7 * x_gated   16x16->32, EXACT, no overflow
    00036cc0  movea 0x111,r0,r6           273                              bytes 20361101
    00036cc4  sar   0x6,r13               >> 6                             bytes a66a
    00036cc6  mul   r13,r6,r0             🛑 r0 = HIGH HALF, DISCARDED     bytes ed372002
                                          => 32x32 -> LOW 32 ONLY => 2's-complement WRAPAROUND
    00036cca  sar   0x12,r6               >> 18                            bytes b232
    00036ccc  cmp   r16,r6                r16 = ld.h 0x507e[tp] = 0xC407E = 511 -- the clamp, and
                                          it runs AFTER the wraparound has already happened

★ REFINEMENT ON THE BRIEFED BOUND, and it makes the argument STRONGER, not weaker. The +/-32,000
  limit is NOT (only) a producer-side clamp in FUN_00041464 that this function must trust. It is a
  `cmovnc` GATE at 0x36C2C inside FUN_00036c12 ITSELF, two instructions before the multiply, in the
  same expression -- it ZEROES the term outside the window rather than saturating. The window
  derives from the gate's own constants: x + 0x7D00 <u 0xFA01 => x in [-32000, +32000]. So the
  bound needs NO assumption about the producer at all. (0xFA0000 >> 9 = 32000 agrees numerically.)

★ THE FALLBACK PATHS ARE COVERED, and this check could have gone the other way. sVar7 is NOT always
  the LERP output: `ld.h 0x740a[tp]` (= 0xC640A = -8192) and `ld.h 0x740c[tp]` (= 0xC640C = -3277)
  feed it when the mode gate or the 0x74FD compare fails. 🛑 tp = 0xBF000 so tp+0x740A is 0xC640A,
  NOT 0xC740A -- the off-by-0x1000 trap, 6th recurrence avoided. Both are smaller in magnitude than
  our dosed |Y[0]| = 14745, so the DOSED row is the binding worst case. If either had exceeded
  14745 the bound would be set by a cell V91 does not touch.

    worst_product = 32000 * 14745 // 64 * 273 = 2,012,692,500  <=  2,147,483,647 = INT32_MAX
    headroom = 1.0670x
  (The `//64` floor is conservative for both signs: |P|max = 471,840,000 is exactly divisible by 64,
   so the arithmetic `sar 0x6` gives the same magnitude for a negative product.)

===================================================================================================
TWO STANDING FACTS ABOUT THIS LANE
===================================================================================================
* H(0) = 0 IS PROVEN, THREE INDEPENDENT WAYS -- symbolically from the (1 - z^-1) zero; numerically
  |H|/f constant at 0.402 over 0.1-2 Hz; and IN THE FIXED-POINT INTEGER ARITHMETIC ITSELF, where a
  constant input makes the differencer's operands identical integers so gp-0x6c2c goes to EXACTLY 0
  bit-for-bit. ⇒ THIS LANE CONTRIBUTES NOTHING AT ANY SUSTAINED STEERING RATE, AT ANY MULTIPLIER.
  The operator's own hard constraint is satisfied STRUCTURALLY, not by argument.
* MODE 27 IS NEVER REACHED ON THIS CAR -- gp-0x67e2 stayed at 1 across all 104,061 frames of V73
  telemetry. Dosing 27 is FREE INSURANCE against a mode transition nobody has proven impossible; it
  costs 6 bytes. ⚠ It is NOT a second lever and does NOT double the lever's reach. Mode 26 is the
  one that acts.

===================================================================================================
🛑 THE TRAPS THIS SCRIPT IS BUILT AGAINST
===================================================================================================
* AN ADDRESS IS NOT A MODE. 0xD6A5C is mode 23; 0xD6A64 is mode 24. Every record address here is
  DEREFERENCED from 0xCBE74 + mode*4 and printed with its mode beside it. Nothing is hard-coded.
* Y IS AT RECORD BASE + 8. Writing at base+2 lands in the X breakpoint array, which the LERP compares
  UNSIGNED -- the result is a silent flat Y[0] at all speeds that LOOKS like a working calibration.
  The script asserts the write span is DISJOINT from the X span.
* MODE 25's RECORD (0xD7A44) SITS EXACTLY 0x10 BELOW MODE 26's (0xD7A54). A -0x10 slip lands on a
  DISENGAGED column and looks entirely plausible. Modes 24 AND 25 are asserted byte-identical.
* THE POINTER ARRAY HAS EXACTLY 34 SLOTS, modes 0..33 -- a GIVEN BOUND, named below, never a walk.
  0xCBE74 + 34*4 = 0xCBEFC is the FIRST SLOT PAST the array and it holds 0x000DAA44, a perfectly
  valid-looking pointer to a perfectly valid-looking n=3 record. An exhaustion walk therefore runs
  straight on into the gain_B tables (gain_B[0] is at 0xCBF5C) -- a previous agent's walk reached
  "mode 289" and reported phantom differences at "modes 68/126", which are gain_B array 0/1 mode 10.
  A guessed bound is not a bound. There is a separate guard that 0xCBEFC is not written.
* walk_all_blocks() == 0 IS NECESSARY, NOT SUFFICIENT -- a corrupt build can pass its own verifier
  because the recompute hides the corruption. The zero-unattributed full byte diff is the independent
  check and both must pass.

===================================================================================================
CRC
===================================================================================================
Both writes are in [0xD7000, 0xD7FFC) so exactly ONE trailer, 0xD7FFC, should move -- but the
trailer set is DERIVED IN CODE from the touched addresses via V53.owning_block (which reads the
image's own self-describing 50-block map) and the derivation is ASSERTED to return that set. Never
hard-coded. The per-0x1000 rule generalises ONLY above 0xC4000; block 50 is the single MAIN block
spanning [0x013000, 0x0C4FFC) and V91 does not touch it at all.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V91_WRITE", "").strip().lower()

BASE_BIN = str(plain_image_path(
    "_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin"))
BASE_SHA = "28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))

# ---------------------------------------------------------------------------------------------
# THE LEVER
# ---------------------------------------------------------------------------------------------
FRICTION_PTR_ARRAY = 0xCBE74
FRICTION_N_MODES = 34                  # 🛑 modes 0..33. A GIVEN BOUND, not a walk. 0xCBE74+34*4
                                       #    = 0xCBEFC is the first slot PAST the array.
FRICTION_ARRAY_END = FRICTION_PTR_ARRAY + FRICTION_N_MODES * 4      # 0xCBEFC
REC_N_OFF, REC_X_OFF, REC_Y_OFF, REC_PAD_OFF, REC_LEN = 0x00, 0x02, 0x08, 0x0E, 0x10

# TVCA4: 24/25 MANUAL, 26/27 ENGAGED.
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
TARGET_MODES = ENGAGED_MODES

FRICTION_NPT = 3
FRICTION_X = (0, 1280, 5760)           # counts of voted vehicle speed; 64 counts/km/h = [0,20,90]
FRICTION_Y_STOCK = (-9830, -5734, -1966)
SCALE_NUM, SCALE_DEN = 3, 2            # x1.5 -- EXACT in integers on all three knots
FRICTION_Y_NEW = tuple(y * SCALE_NUM // SCALE_DEN for y in FRICTION_Y_STOCK)

SPEED_COUNTS_PER_KMH = 64
CLAMP_ADDR, CLAMP_VALUE = 0xC407E, 511         # 🛑 Honda's own. The whole fault argument rests here.
DTC_1D_TRIP = 512
ROUTE77_ENGAGED_MAX = 319.1                    # measured |gp-0x6b26| at the STOCK Y row

# ---- ASSERTION 12: int32 wraparound in FUN_00036c12. Every constant is re-read from the IMAGE.
INT32_MAX = 2 ** 31 - 1
TP = 0xBF000                                   # 🛑 tp+0x740A = 0xC640A, NOT 0xC740A
GATE_ORI_IMM_ADDR, GATE_ORI_IMM = 0x36C24, 0xFA01     # `ori 0xfa01,r0,r11`   @0x36C22
GATE_ADDI_IMM_ADDR, GATE_ADDI_IMM = 0x36C28, 0x7D00   # `addi 0x7d00,r9,r14`  @0x36C26
MUL_IMM_ADDR, MUL_IMM = 0x36CC2, 0x111                # `movea 0x111,r0,r6`   @0x36CC0
PRE_SAR_ADDR, PRE_SAR = 0x36CC4, bytes.fromhex("a66a")     # `sar 0x6,r13`
MUL_ADDR, MUL_BYTES = 0x36CC6, bytes.fromhex("ed372002")   # `mul r13,r6,r0` -- r0 = HIGH, DISCARDED
POST_SAR_ADDR, POST_SAR = 0x36CCA, bytes.fromhex("b232")   # `sar 0x12,r6`
SVAR7_FALLBACKS = {TP + 0x740A: -8192, TP + 0x740C: -3277}  # the two non-LERP sources of sVar7

# The V74/V75 record, re-verified from those IMAGES at run time when they are on disk.
V74_V75_MODES = (2, 3, 5, 10, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
V74_V75_IMAGES = ("_v74_engagedcols_x0_12_addonly_plain_image.bin",
                  "_v75_CY0.566-EX1.200_magprobe_plain_image.bin")

# ---------------------------------------------------------------------------------------------
# EVERYTHING THAT MUST NOT MOVE. Asserted on the base AND re-asserted on the built image.
# ---------------------------------------------------------------------------------------------
FROZEN = {
    0xC407E: (2, 511, "🛑 HARD-FAULT INTERLOCK CLAMP -- Honda's 511, one under its own 512 trip"),
    0xC40D2: (2, 204, "K1 modelled Coulomb friction -- V89's lever, CARRIED unchanged"),
    0xC4080: (2, 0, "K0 pure-Coulomb arm -- the recorded NEVER-RAISE relay hazard, stays 0"),
    0xC40BC: (2, 600, "friction relay gate -- 600. 6000 measured 2.3x WORSE; DO NOT restore it"),
    0xC40D0: (2, 408, "friction EMA alpha (16.7 Hz)"),
    0xC40D4: (2, 573, "command-branch EMA -- V86's FALSIFIED lever"),
    0xC40D8: (2, 3686, "friction-family constant"),
    0xC646E: (2, 1428, "INERTIA/damping gain -- unmeasured sizing figure"),
    0xC63A0: (2, 1024, "INERT, no mechanism"),
    0xC63A2: (2, 1024, "loop-gain family"),
    0xC63A4: (2, 1024, "loop-gain family"),
    0xC63A6: (2, 1024, "observer weight on gp-0x6b26 (Path 2) -- FROZEN, so the dose is the ONLY"
                       " thing that moves in the observer"),
    0xC63A8: (2, 1024, "loop-gain family"),
    0xC63AA: (2, 1024, "loop-gain family"),
    0xC63AC: (2, 102, "loop-gain family"),
    0xC63AE: (2, 1024, "loop-gain family"),
    0xC6200: (2, 8192, "loop-gain family"),
    0xC6446: (2, 5244, "Lever B arm -- V88's 5244"),
    0xC6468: (2, 2639, "model output gain -- SHARED, 5 readers"),
    0xC646C: (2, 891, "shared sensor scale -- Honda 891"),
    0xC6CD0: (2, 3564, "private forward LKAS gain = 4.000x, NEVER lower"),
    0xC62EA: (2, 0, "steer-to-zero"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0x3AA96: (1, 0xFB, "Lever B gate -- V88's"),
    0x454FE: (1, 0xB5, "V42's ratchet fix -- restored at V80, carried V87/V88/V89/V90"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
}

# The V90 instrument, carried byte-for-byte. Hex captured from the flown V90 image.
CAVE_BASE, CAVE_END = 0xC4B34, 0xC4B80         # 76 bytes: 74-byte payload + 2 virgin 0xFF
V90_CAVE = bytes.fromhex(
    "003a2437da946032ae05483a24370a946032ae058031a9326032a305443a24371e956032"
    "a305423a243700946032ae05413ac43a483a8437edeac636070007314437ecea2436e8ea7f00ffff")
HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")
R427_ADDR, R427_DISP = 0x55DF2, 0x6B26         # `ld.h -0x6b26[gp],r6` -- V90's 427 repoint

VARIANT_TOKEN = "V90BASE-CBE74.M26.M27.X1.5"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v91_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V91-{TAG}-0x{START:X}-0x{END:X}.rwd")

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    """Every assertion prints a BOOLEAN. A check that produces no output is not a check that passed."""
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"🛑 ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def rec_addr(buf, mode):
    """🛑 DEREFERENCE. An address is not a mode. Never hard-code a record address."""
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_fields(buf, mode):
    p = rec_addr(buf, mode)
    return (p,
            u16(buf, p + REC_N_OFF),
            struct.unpack_from("<3h", buf, p + REC_X_OFF),
            struct.unpack_from("<3h", buf, p + REC_Y_OFF),
            u16(buf, p + REC_PAD_OFF))


def lerp_y(y_row, speed_counts):
    """Piecewise-linear interpolation over the SPEED axis, integer, knots read LE from the image.

    x  = voted vehicle speed in counts (64 counts per km/h)
    X  = FRICTION_X, the breakpoints -- V91 does NOT touch them
    Y  = the row being interpolated
    Below X[0] and above X[n-1] the surface saturates at the end knot.

    ⚠ SCOPE. This is an ILLUSTRATION of the surface SHAPE, not a byte-exact mirror of
      FUN_00036c12: the rounding mode of the firmware's own interior interpolation is NOT
      re-derived here. The load-bearing claim -- that the dose is exactly x1.5 -- rests on the
      THREE KNOTS, which are read from the built image and are exact. Interior points here differ
      from an exact x1.5 by at most 1 count, purely from this function's own floor division.
    """
    x = FRICTION_X
    if speed_counts <= x[0]:
        return y_row[0]
    if speed_counts >= x[FRICTION_NPT - 1]:
        return y_row[FRICTION_NPT - 1]
    for i in range(FRICTION_NPT - 1):
        if x[i] <= speed_counts < x[i + 1]:
            return y_row[i] + (y_row[i + 1] - y_row[i]) * (speed_counts - x[i]) // (x[i + 1] - x[i])
    raise AssertionError("speed fell outside every LERP segment")


def assert_frozen(buf, label):
    bad = [(a, u16(buf, a) if w == 2 else buf[a], want, why)
           for a, (w, want, why) in sorted(FROZEN.items())
           if (u16(buf, a) if w == 2 else buf[a]) != want]
    for a, got, want, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {want} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


def build():
    # ==========================================================================================
    # 1. THE BASE
    # ==========================================================================================
    base = bytearray(Path(BASE_BIN).read_bytes())
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    print("=" * 102)
    print("  V91 -- the FLOWN V90 + 12 CALIBRATION BYTES.")
    print("         0xCBE74 friction/damping-comp LERP Y row x1.5 on modes 26 and 27 (ENGAGED) ONLY.")
    print("         🛑 SAME LEVER, SAME DOSE as V74/V75 -- both of which HARD-FAULTED at 0xC407E=850.")
    print(f"\n    base   {os.path.basename(BASE_BIN)}")
    print(f"    sha256 {base_sha}")
    print("=" * 102)

    print("\n  [1] BASE IMAGE")
    check(len(base) == 0x100000, f"base length = {len(base)} = 0x{len(base):X} bytes (1 MiB)")
    check(base_sha == BASE_SHA, f"base sha256 == the flown V90's {BASE_SHA}")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain verifies 50/50")

    # ==========================================================================================
    # 2. POINTER IDENTITY -- DEREFERENCED, never hard-coded
    # ==========================================================================================
    print("\n  [2] POINTER IDENTITY -- every record address DEREFERENCED from 0xCBE74 + mode*4")
    EXPECT_PTR = {24: 0xD6A64, 25: 0xD7A44, 26: 0xD7A54, 27: 0xD7A64}
    for mode, want in EXPECT_PTR.items():
        got = rec_addr(base, mode)
        check(got == want, f"mode {mode}: slot 0x{FRICTION_PTR_ARRAY + mode * 4:05X} -> "
                           f"0x{got:05X} (expected 0x{want:05X})")
    check(rec_addr(base, 23) == 0xD6A54,
          "mode 23 -> 0xD6A54 -- confirming 0xD6A5C is mode 23's Y, NOT mode 24's")
    check(FRICTION_ARRAY_END == 0xCBEFC,
          f"array bound: 0xCBE74 + {FRICTION_N_MODES}*4 = 0x{FRICTION_ARRAY_END:05X} "
          f"= the FIRST SLOT PAST the {FRICTION_N_MODES}-slot array (modes 0..{FRICTION_N_MODES - 1})")
    past = struct.unpack_from("<I", base, FRICTION_ARRAY_END)[0]
    check(past == 0xDAA44,
          f"0x{FRICTION_ARRAY_END:05X} holds 0x{past:05X} -- a VALID-LOOKING pointer. This is exactly "
          f"why an exhaustion walk over-runs into gain_B; the bound is GIVEN, never discovered")

    # ==========================================================================================
    # 3. PRE-EDIT STATE
    # ==========================================================================================
    print("\n  [3] PRE-EDIT -- n, X and Y read from the BASE for all four TVCA4 modes")
    for mode in MANUAL_MODES + ENGAGED_MODES:
        p, n, x, y, pad = rec_fields(base, mode)
        arm = "MANUAL " if mode in MANUAL_MODES else "ENGAGED"
        check(n == FRICTION_NPT and x == FRICTION_X and y == FRICTION_Y_STOCK,
              f"mode {mode} ({arm}) rec 0x{p:05X}: n={n} X@0x{p + REC_X_OFF:05X}={x} "
              f"Y@0x{p + REC_Y_OFF:05X}={y} pad@0x{p + REC_PAD_OFF:05X}=0x{pad:04X}")
    check(rec_addr(base, 26) - rec_addr(base, 25) == 0x10,
          f"mode 25's record 0x{rec_addr(base, 25):05X} sits EXACTLY 0x10 below mode 26's "
          f"0x{rec_addr(base, 26):05X} -- a -0x10 slip would land on a DISENGAGED column")

    print("\n      the DOSE arithmetic")
    want = tuple(y * SCALE_NUM // SCALE_DEN for y in FRICTION_Y_STOCK)
    check(SCALE_NUM / SCALE_DEN == 1.5, f"multiplier = {SCALE_NUM}/{SCALE_DEN} = "
                                        f"{SCALE_NUM / SCALE_DEN} -- ASSERTED to be exactly 1.5")
    check(all(y * SCALE_NUM % SCALE_DEN == 0 for y in FRICTION_Y_STOCK),
          f"x1.5 is EXACT in integers on all three knots: {FRICTION_Y_STOCK} -> {want} "
          f"(no rounding, so the multiplier is not silently something else)")
    check(want == FRICTION_Y_NEW, f"declared Y row {FRICTION_Y_NEW} == the derived x1.5 row")
    check(all(-32768 <= y <= 32767 for y in FRICTION_Y_NEW),
          f"every new knot fits int16 (Y[0] = {FRICTION_Y_NEW[0]}, int16 MIN is -32768)")
    pred = ROUTE77_ENGAGED_MAX * SCALE_NUM / SCALE_DEN
    check(pred < CLAMP_VALUE,
          f"NO-CLIP: route-77 engaged max |gp-0x6b26| = {ROUTE77_ENGAGED_MAX} ct at stock; "
          f"x1.5 -> {pred:.1f} ct vs the {CLAMP_VALUE} rail "
          f"({100 * (1 - pred / CLAMP_VALUE):.1f} % headroom)")
    check(ROUTE77_ENGAGED_MAX * 2.0 > CLAMP_VALUE,
          f"and the ceiling is REAL, not decorative: x2.0 -> {ROUTE77_ENGAGED_MAX * 2:.1f} ct "
          f"CLIPS => sign(gp-0x6c2c) x {CLAMP_VALUE} = a Coulomb RELAY = the V80 mechanism")
    k_int16 = 32768 / abs(FRICTION_Y_STOCK[0])
    print(f"    ---- int16 headroom would allow k_max = 32768/{abs(FRICTION_Y_STOCK[0])} = "
          f"{k_int16:.3f}. ⚠ That is a LOOSER, DIFFERENT bound and is NOT the dose ceiling.")

    # ==========================================================================================
    # 4. THE INTERLOCK -- the entire fault argument
    # ==========================================================================================
    print("\n  [4] 🛑 THE HARD-FAULT INTERLOCK -- refuse to build if this is not Honda's 511")
    got = u16(base, CLAMP_ADDR)
    check(got == CLAMP_VALUE,
          f"base 0x{CLAMP_ADDR:05X} = {got} == {CLAMP_VALUE}, which is {DTC_1D_TRIP - CLAMP_VALUE} "
          f"count below the DTC-0x1d monitor's {DTC_1D_TRIP} trip => the monitor is STRUCTURALLY "
          f"untrippable by this lane at ANY multiplier")
    print(f"    ---- 🛑 V74 and V75 both carried 0x{CLAMP_ADDR:05X} = 850 and both HARD-FAULTED. "
          f"No flight has\n         ever separated the DOSE from the 850 interlock. The separation "
          f"is STRUCTURAL, not empirical.")

    print("\n  [5] CARRIED-FORWARD CELLS on the BASE")
    assert_frozen(base, "base")
    check(rd(base, CAVE_BASE, CAVE_END - CAVE_BASE) == V90_CAVE,
          f"V90 cave 0x{CAVE_BASE:05X}-0x{CAVE_END - 1:05X} ({CAVE_END - CAVE_BASE} B) byte-exact")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"cave hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} unchanged")
    check(rd(base, R427_ADDR, 2) == struct.pack("<h", -R427_DISP),
          f"CAN 427 repoint 0x{R427_ADDR:05X} = {rd(base, R427_ADDR, 2).hex()} "
          f"= ld.h -0x{R427_DISP:04X}[gp],r6")

    # ==========================================================================================
    # 5. SNAPSHOT ALL 34 RECORDS, then EDIT
    # ==========================================================================================
    before = {m: (rec_addr(base, m), rd(base, rec_addr(base, m), REC_LEN))
              for m in range(FRICTION_N_MODES)}
    code = bytearray(base)
    attributed, by_addr = set(), {}

    print("\n  [6] THE EDIT -- 12 bytes, two int16 triples")
    new_bytes = struct.pack("<3h", *FRICTION_Y_NEW)
    check(len(new_bytes) == 6, f"each Y row is {len(new_bytes)} bytes = 3 x int16 LE "
                               f"({new_bytes.hex()})")
    for mode in TARGET_MODES:
        p = rec_addr(code, mode)
        w0, w1 = p + REC_Y_OFF, p + REC_Y_OFF + 6 - 1
        x0, x1 = p + REC_X_OFF, p + REC_X_OFF + 6 - 1
        check(w1 < x0 or w0 > x1,
              f"mode {mode}: write span [0x{w0:05X},0x{w1:05X}] is DISJOINT from the X span "
              f"[0x{x0:05X},0x{x1:05X}] -- the LERP compares X UNSIGNED, so an X overwrite would "
              f"give a SILENT flat Y[0] at all speeds")
        old = rd(code, w0, 6)
        check(old == struct.pack("<3h", *FRICTION_Y_STOCK),
              f"mode {mode}: 0x{w0:05X} reads {old.hex()} = {FRICTION_Y_STOCK} before the write")
        code[w0:w0 + 6] = new_bytes
        for k in range(6):
            attributed.add(w0 + k)
            by_addr[w0 + k] = f"LEVER mode {mode} friction LERP Y[{k // 2}] x1.5"
        print(f"    0x{w0:05X}   6 B   mode {mode} Y {FRICTION_Y_STOCK} -> {FRICTION_Y_NEW}")
    check(len(attributed) == 12, f"TOTAL LEVER BYTES = {len(attributed)} (expected 12)")

    # ==========================================================================================
    # 6. POST-EDIT
    # ==========================================================================================
    print("\n  [7] POST-EDIT -- read back from the BUILT image")
    for mode in TARGET_MODES:
        p, n, x, y, pad = rec_fields(code, mode)
        check(y == FRICTION_Y_NEW, f"mode {mode} rec 0x{p:05X}: Y@0x{p + REC_Y_OFF:05X} = {y}")
        check(x == FRICTION_X, f"mode {mode}: X@0x{p + REC_X_OFF:05X} = {x} UNCHANGED "
                               f"(no breakpoint moved => no phase, no new dead zone)")
        check(n == FRICTION_NPT, f"mode {mode}: n@0x{p:05X} = {n} UNCHANGED")
        check(pad == u16(base, p + REC_PAD_OFF),
              f"mode {mode}: pad@0x{p + REC_PAD_OFF:05X} = 0x{pad:04X} UNCHANGED")

    print("\n  [8] 🛑 EVERY OTHER MODE BYTE-IDENTICAL -- modes 0..33, the GIVEN 34-slot bound")
    moved = [m for m in range(FRICTION_N_MODES)
             if rd(code, before[m][0], REC_LEN) != before[m][1]]
    check(moved == list(TARGET_MODES),
          f"exactly modes {moved} moved out of {FRICTION_N_MODES} "
          f"(0..{FRICTION_N_MODES - 1}); every other 16-byte record is byte-identical")
    for mode in MANUAL_MODES:
        p, n, x, y, pad = rec_fields(code, mode)
        check(rd(code, p, REC_LEN) == before[mode][1] and y == FRICTION_Y_STOCK,
              f"🛑 MANUAL mode {mode} rec 0x{p:05X} BYTE-IDENTICAL, Y = {y} = STOCK "
              f"(the -0x10 slip did NOT happen)")
    check(rd(code, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4)
          == rd(base, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4),
          f"the pointer array itself [0x{FRICTION_PTR_ARRAY:05X},0x{FRICTION_ARRAY_END:05X}) "
          f"is byte-identical -- no pointer was rewritten")
    check(not [a for a in attributed if FRICTION_ARRAY_END <= a < FRICTION_ARRAY_END + 4],
          f"GUARD: 0x{FRICTION_ARRAY_END:05X} (the first slot PAST the array) is NOT written")
    check(rd(code, 0xCBEFC, 0xCBF60 - 0xCBEFC) == rd(base, 0xCBEFC, 0xCBF60 - 0xCBEFC),
          "GUARD: [0xCBEFC,0xCBF60) -- the slots past the array and gain_B[0] at 0xCBF5C -- "
          "byte-identical (the 'mode 68/126' phantom-diff region)")

    print("\n  [9] CARRIED-FORWARD CELLS on the BUILT image")
    assert_frozen(code, "built image")
    check(u16(code, CLAMP_ADDR) == CLAMP_VALUE,
          f"🛑 0x{CLAMP_ADDR:05X} = {u16(code, CLAMP_ADDR)} == {CLAMP_VALUE} on the OUTPUT too")
    check(rd(code, CAVE_BASE, CAVE_END - CAVE_BASE) == V90_CAVE,
          f"V90 cave 0x{CAVE_BASE:05X}-0x{CAVE_END - 1:05X} byte-identical to V90")
    check(rd(code, R427_ADDR, 2) == struct.pack("<h", -R427_DISP),
          f"CAN 427 repoint 0x{R427_ADDR:05X} byte-identical to V90")
    check(rd(code, HOOK_ADDR, 4) == HOOK_BYTES, f"cave hook 0x{HOOK_ADDR:05X} byte-identical")

    # ==========================================================================================
    # ASSERTION 12 -- int32 wraparound in FUN_00036c12's `x 0x111` multiply.
    # It is UNCLAMPED and PRECEDES the 0xC407E comparison, so the clamp cannot save it: it wraps
    # arbitrarily rather than saturating, corrupting one tick of gp-0x6b26. Proven impossible
    # against gp-0x6c2c's OWN hard gate -- never against a measured distribution, so it holds in
    # emergency manoeuvres and fault-adjacent transients that route 77 never sampled.
    # Run on the BUILT image, so it constrains the DOSED cell rather than the base.
    # ==========================================================================================
    print("\n  [9b] 🛑 ASSERTION 12 -- INT32 OVERFLOW in FUN_00036c12, PRE-CLAMP")
    print("       every constant re-read LE from the BUILT IMAGE (2nd method vs the Ghidra decode)")
    for a, want, what in ((GATE_ORI_IMM_ADDR, GATE_ORI_IMM, "ori 0xfa01,r0,r11   @0x36C22"),
                          (GATE_ADDI_IMM_ADDR, GATE_ADDI_IMM, "addi 0x7d00,r9,r14  @0x36C26"),
                          (MUL_IMM_ADDR, MUL_IMM, "movea 0x111,r0,r6   @0x36CC0")):
        got = u16(code, a)
        check(got == want, f"0x{a:05X} imm16 = 0x{got:04X} == 0x{want:04X}   {what}")
    for a, want, what in ((PRE_SAR_ADDR, PRE_SAR, "sar 0x6,r13   -- the >>6 before the multiply"),
                          (MUL_ADDR, MUL_BYTES,
                           "mul r13,r6,r0 -- r0 is the HIGH HALF and it is DISCARDED => the "
                           "product WRAPS, it does not saturate"),
                          (POST_SAR_ADDR, POST_SAR, "sar 0x12,r6   -- the >>18 after")):
        got = rd(code, a, len(want))
        check(got == want, f"0x{a:05X} = {got.hex()} == {want.hex()}   {what}")

    # The +/-32000 bound comes from the GATE'S OWN CONSTANTS, in this very function, two
    # instructions before the multiply. cmovnc at 0x36C2C ZEROES the term outside the window.
    producer_ceiling = GATE_ORI_IMM - GATE_ADDI_IMM - 1        # x + 0x7D00 <u 0xFA01
    check(producer_ceiling == GATE_ADDI_IMM == 32000,
          f"the cmovnc GATE at 0x36C2C passes x only for x + 0x{GATE_ADDI_IMM:04X} <u "
          f"0x{GATE_ORI_IMM:04X}, i.e. |gp-0x6c2c| <= {producer_ceiling} -- DERIVED from the gate's "
          f"own two constants, inside THIS function, needing NO assumption about the producer")
    check(producer_ceiling == (0xFA0000 >> 9),
          f"and it agrees numerically with the briefed producer clamp 0xFA0000>>9 = {0xFA0000 >> 9}")

    # sVar7 is NOT always the LERP output. Cover both fallbacks -- this could have gone the other way.
    for a, want in SVAR7_FALLBACKS.items():
        got = struct.unpack_from("<h", code, a)[0]
        check(got == want, f"sVar7 fallback 0x{a:05X} (tp+0x{a - TP:04X}) = {got} "
                           f"🛑 tp = 0x{TP:05X}, so this is 0x{a:05X} and NOT 0x{a + 0x1000:05X}")
    y_max_dosed = max(abs(y) for y in rec_fields(code, 26)[3])
    y_max_all = max([y_max_dosed] + [abs(v) for v in SVAR7_FALLBACKS.values()])
    check(y_max_all == y_max_dosed == abs(FRICTION_Y_NEW[0]),
          f"the BINDING |sVar7| is our DOSED Y[0] = {y_max_dosed}, larger than both fallbacks "
          f"{sorted(abs(v) for v in SVAR7_FALLBACKS.values())} => the worst case is V91's own cell")

    worst_product = producer_ceiling * y_max_all // 64 * MUL_IMM
    check(worst_product <= INT32_MAX,
          f"INT32 OVERFLOW IMPOSSIBLE: worst_product = {producer_ceiling} * {y_max_all} // 64 * "
          f"{MUL_IMM} = {worst_product:,} <= {INT32_MAX:,} = INT32_MAX")
    check(INT32_MAX / worst_product > 1.0,
          f"int32 headroom {INT32_MAX / worst_product:.4f}x at the producer ceiling "
          f"(anything below 1.0 aborts)")
    check(producer_ceiling * y_max_all % 64 == 0,
          f"|P|max = {producer_ceiling * y_max_all:,} is exactly divisible by 64, so the arithmetic "
          f"`sar 0x6` gives the same magnitude for a NEGATIVE product -- the floor is not a leak")
    m_overflow = INT32_MAX * 64 / (MUL_IMM * abs(FRICTION_Y_STOCK[0]) * producer_ceiling)
    m_clip = CLAMP_VALUE / ROUTE77_ENGAGED_MAX
    check(SCALE_NUM / SCALE_DEN <= m_overflow,
          f"the OVERFLOW bound is M <= {m_overflow:.4f}; V91 is at {SCALE_NUM / SCALE_DEN}")
    check(SCALE_NUM / SCALE_DEN <= m_clip,
          f"the CLIP bound is M <= {m_clip:.4f}; V91 is at {SCALE_NUM / SCALE_DEN}")
    print(f"    ---- ⚠ the two bounds agree at ~1.60 by COINCIDENCE, NOT by a shared mechanism: the")
    print(f"         clamp binds at |gp-0x6c2c| ~ 3,200, the overflow at ~34,000 -- an ORDER OF")
    print(f"         MAGNITUDE apart. No design intent is claimed. int16 k_max = "
          f"{32768 / abs(FRICTION_Y_STOCK[0]):.4f} is looser still and NON-BINDING.")
    for M in (1.0, 1.5, 1.6, 2.0, 3.0):
        t = INT32_MAX / MUL_IMM * 64 / (abs(FRICTION_Y_STOCK[0]) * M)
        flag = "SAFE" if t > producer_ceiling else "🛑 REACHABLE"
        star = "  <-- V91" if M == SCALE_NUM / SCALE_DEN else ""
        print(f"         M={M:<4} wraps at |gp-0x6c2c| = {t:10,.0f}  = {t / producer_ceiling:.4f}x "
              f"the {producer_ceiling} gate   {flag}{star}")


    # ==========================================================================================
    # 7. CRC -- DERIVED IN CODE
    # ==========================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  [10] CRC -- {len(blocks)} block(s) move, trailer set DERIVED from the image's own "
          f"block map")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit landed on the trailer at 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        owners = [a for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old_crc:08X} -> "
              f"0x{new_crc:08X}   owns {len(owners)} of {len(touched)} touched byte(s)")
    derived = {blk[1] for blk in blocks}
    check(derived == {0xD7FFC},
          f"DERIVED trailer set {sorted(hex(t) for t in derived)} == {{0xd7ffc}} -- both writes "
          f"lie inside [0xD7000,0xD7FFC). Derived, then asserted; never hard-coded")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50 "
                                             "(NECESSARY, NOT SUFFICIENT -- see [11])")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "the CRC-SKIPPED block [0xC5000,0xC5FFC) is byte-identical to the base (V40's brick)")
    check(not [a for a in attributed if a < START or a >= END],
          f"every edit lies inside [0x{START:X},0x{END:X})")
    check(bytes(code[:START]) == bytes(base[:START]),
          f"nothing below 0x{START:X} changed (the bootloader region)")

    # ==========================================================================================
    # 8. ZERO-UNATTRIBUTED FULL BYTE DIFF -- the INDEPENDENT check
    # ==========================================================================================
    runs, i = [], START
    while i < END:
        if code[i] != base[i]:
            j = i
            while j < END and code[j] != base[j]:
                j += 1
            runs.append((i, j - 1))
            i = j
        else:
            i += 1
    attribute = lambda d: by_addr.get(d, "CRC trailer 0xD7FFC" if d in crc_only else None)  # noqa: E731
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    total = sum(b - a + 1 for a, b in runs)
    print("\n" + "=" * 102)
    print("  [11] 🛑 FULL BYTE DIFF: BUILT V91 vs the FLOWN V90 -- over [0x13000, 0x100000)")
    print(f"       {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"       0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    check(not stray, f"ZERO unattributed bytes vs V90 "
                     f"(stray = {[hex(x) for x in stray[:16]]})")
    check(total == 12 + 4, f"exactly 12 lever bytes + 4 CRC trailer bytes = {total}")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    check(hashlib.sha256(bytes(rt)).hexdigest() == base_sha,
          "restoring the attributed set reproduces the flown V90 BIT-FOR-BIT")

    # ==========================================================================================
    # 9. THE DELIVERED SURFACE, and the V74/V75 comparison, read from the IMAGES
    # ==========================================================================================
    print("\n  [12] THE DELIVERED SURFACE -- LERP mirrored in integer Python, knots read from the "
          "BUILT image")
    y26 = rec_fields(code, 26)[3]
    y24 = rec_fields(code, 24)[3]
    print("       speed          Y  MANUAL (24/25)     Y ENGAGED (26/27)     ratio    |gp-0x6b26| "
          "at the route-77 envelope")
    for kmh in (0, 5, 10, 20, 40, 60, 90, 120):
        sc = kmh * SPEED_COUNTS_PER_KMH
        a, b = lerp_y(y24, sc), lerp_y(y26, sc)
        env = ROUTE77_ENGAGED_MAX * b / a if a else 0.0
        print(f"       {kmh:3d} km/h ({sc:5d} ct)   {a:8d}          {b:8d}       "
              f"{b / a:5.3f}    {env:6.1f} of {CLAMP_VALUE}")
    check(all(a * SCALE_NUM == b * SCALE_DEN for a, b in zip(y24, y26)),
          f"AT THE KNOTS -- the load-bearing claim -- the engaged row is EXACTLY 1.5x the manual "
          f"row: {y24} x 3/2 == {y26}, no rounding anywhere")
    worst = max(abs(lerp_y(y26, k * SPEED_COUNTS_PER_KMH) * SCALE_DEN
                    - lerp_y(y24, k * SPEED_COUNTS_PER_KMH) * SCALE_NUM)
                for k in range(0, 200))
    check(worst <= SCALE_DEN,
          f"BETWEEN the knots the ratio holds to {worst / SCALE_DEN:.1f} count over 0..199 km/h "
          f"-- and that residue is this MIRROR's own floor division, not the lever "
          f"=> a pure scalar multiply: no phase, no sign change, no breakpoint moved")
    check(all(lerp_y(y26, k * SPEED_COUNTS_PER_KMH) < 0 for k in range(0, 200)),
          "the engaged surface is NEGATIVE at every speed 0..199 km/h => gp-0x6b26 keeps the "
          "OPPOSITE sign to gp-0x6c2c: the term stays DISSIPATIVE, x1.5 cannot flip it")
    check(max(abs(lerp_y(y26, k * SPEED_COUNTS_PER_KMH)) for k in range(0, 200))
          == abs(FRICTION_Y_NEW[0]),
          f"the engaged surface peaks at |{FRICTION_Y_NEW[0]}| (at rest) and decays with speed "
          f"-- the shape is Honda's, only the scale moved")

    print("\n  [13] 🛑 V74 / V75 -- the SAME LEVER at the SAME DOSE, read from THEIR images")
    for name in V74_V75_IMAGES:
        p = plain_image_path(name)
        if not p.exists():
            print(f"    ---- {name}: not on disk, skipped")
            continue
        img = p.read_bytes()
        diff = [m for m in range(FRICTION_N_MODES)
                if struct.unpack_from("<3h", img, rec_addr(img, m) + REC_Y_OFF) != FRICTION_Y_STOCK]
        rows = {struct.unpack_from("<3h", img, rec_addr(img, m) + REC_Y_OFF) for m in diff}
        check(tuple(diff) == V74_V75_MODES and rows == {FRICTION_Y_NEW},
              f"{name[:46]}: {len(diff)} records at {FRICTION_Y_NEW}, modes {diff}")
        check(u16(img, CLAMP_ADDR) == 850,
              f"{name[:46]}: 0x{CLAMP_ADDR:05X} = {u16(img, CLAMP_ADDR)} -- the 850 interlock "
              f"that V91 does NOT carry")
    check(set(TARGET_MODES) < set(V74_V75_MODES),
          f"V91's {set(TARGET_MODES)} is a STRICT 2-of-{len(V74_V75_MODES)} SUBSET of V74/V75's "
          f"records => a DELIBERATE NARROWING, not a reproduction")

    stock_p = Path(STOCK_BIN)
    if stock_p.exists():
        stock = stock_p.read_bytes()
        same = [m for m in range(FRICTION_N_MODES)
                if rd(stock, rec_addr(stock, m), REC_LEN) == before[m][1]]
        check(len(same) == FRICTION_N_MODES,
              f"the V90 base is BYTE-STOCK on all {FRICTION_N_MODES} friction records "
              f"=> V91's 12 bytes are the FIRST movement of this lever since V75")

    # ==========================================================================================
    # 10. .rwd
    # ==========================================================================================
    print("\n  [14] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V91 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "the decoded .rwd payload is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V91_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"🛑 a DIFFERENT {OUT} already exists -- ONE .rwd per build number.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")

            print("\n  [15] 🛑 FROM-DISK -- the SHIPPED .rwd re-read, re-hashed, decoded, re-asserted")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha,
                  f"shipped .rwd re-read from disk, sha256 {rwd_sha}")
            FF.assert_x31_checksum(shipped, "V91 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "the SHIPPED .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain 50/50")
            assert_frozen(sd, "shipped .rwd from disk")
            for mode in TARGET_MODES:
                check(rec_fields(sd, mode)[3] == FRICTION_Y_NEW,
                      f"shipped .rwd: mode {mode} Y = {FRICTION_Y_NEW}")
                check(rec_fields(sd, mode)[2] == FRICTION_X,
                      f"shipped .rwd: mode {mode} X = {FRICTION_X} UNCHANGED")
            for mode in MANUAL_MODES:
                check(rec_fields(sd, mode)[3] == FRICTION_Y_STOCK,
                      f"shipped .rwd: MANUAL mode {mode} Y = {FRICTION_Y_STOCK} = STOCK")
            check(u16(sd, CLAMP_ADDR) == CLAMP_VALUE,
                  f"shipped .rwd: 0x{CLAMP_ADDR:05X} = {CLAMP_VALUE}")
            check(rd(sd, CAVE_BASE, CAVE_END - CAVE_BASE) == V90_CAVE,
                  "shipped .rwd: the V90 cave is byte-identical")
            check(rd(sd, R427_ADDR, 2) == struct.pack("<h", -R427_DISP),
                  "shipped .rwd: the CAN 427 repoint is byte-identical")
            on_disk = Path(BIN_OUT).read_bytes()
            check(hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code),
                  f"the plain image re-read from disk hashes to {img_sha}")

    print("\n" + "=" * 102)
    print(f"  V91 [{VARIANT_TOKEN}]     {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print("  🛑 12 bytes. Modes 26/27 (ENGAGED) friction/damping LERP Y row x1.5. Modes 24/25")
    print("     (MANUAL) BYTE-STOCK. 0xC407E = 511. V89's K1 = 204 and the V90 instrument carried.")
    print("  🛑 SAME LEVER, SAME DOSE as the hard-faulted V74/V75. The ONLY difference is the")
    print("     interlock, and that separation is STRUCTURAL -- no flight has ever tested it.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
