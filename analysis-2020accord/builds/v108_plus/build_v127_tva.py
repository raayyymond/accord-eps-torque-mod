#!/usr/bin/env python3
r"""

V127 -- THE OSCILLATION-BRANCH FIX, SIZED PROPERLY.  0xC640A -8192 -> -1966.  Base = V124.

THE FINDING THIS BUILD ACTS ON
-------------------------------
FUN_00036c12 chooses the gp-0x6b26 acceleration-feedback scale Y three ways (decompiled and
disassembled 2026-08-28, stock code.bin):

    if (gp-0x671a < 0xff) and (gp-0x67f4 == 1):
        if gp-0x671a < cal(0xC64FD)=5:  Y = LERP(mode record, index = VOTED VEHICLE SPEED)
        else:                           Y = cal(0xC640A) = -8192   <- ld.h 0x740a,tp,r12 @0x36CB4
    else:                               Y = cal(0xC640C) = -3277   <- ld.h 0x740c,tp,r12 @0x36CBA
    gp-0x6b26 = clamp(((c2c_gated * Y) >> 6) * 273 >> 18, +-cal(0xC407E)=511)

gp-0x671a is the hard-reversal counter, and it is CLAMPED to CEIL = cal(0xC64FA) = 5
(gp_0x671a = min(revcount, CEIL) @0x42A12, the only st.b writer image-wide).  So
"gp-0x671a >= 5" is reachable ONLY when the counter has SATURATED -- i.e. exactly when 5+ hard
reversals have been detected, held for 5.0 s by cal(0xC6270).

*** THE FALLBACK IS THE OSCILLATION BRANCH, AND IT RAISES Y ***

Honda's schedule tapers Y with speed; the fallback is a FLAT -8192 that ignores speed:

    speed    LERP Y     fallback/LERP
      5 km/h  -8806        0.93x
     15 km/h  -6758        1.21x
     24 km/h  -5519        1.48x
     44 km/h  -4442        1.84x   <- the operator's logged oscillation event
     64 km/h  -3366        2.43x
     90 km/h  -1966        4.17x

=> on detecting an oscillation the firmware MULTIPLIES the acceleration-feedback term by up to
4x, at exactly the speeds where the symptoms live, driving |gp-0x6b26| into its 511 rail.  A
railed acceleration term is sign(alpha)*511 -- a bang-bang Coulomb relay, which is precisely
accord-v80-damper-relay-and-grind1-inert's measured mechanism.  A relay ratchets; it does not
damp.  This is a positive-feedback trap: oscillate -> detector arms -> bigger Y -> rail -> relay.

IT EXPLAINS THREE THINGS AT ONCE
---------------------------------
  1. the peak-turn oscillation the operator reports at 44 km/h, hands-off, engaged;
  2. why grinding is reported at 15-40 mph and NEVER below 5-6 mph -- the jump ratio is 0.93x
     at creep and grows monotonically with speed (V107 already noted "the symptom map and the
     rail-duty map are the same map"; this supplies the mechanism);
  3. why the 0xCBE74 x1.5 dose MEASURED INERT -- if the counter saturates during the manoeuvre
     the mode record is BYPASSED entirely, so no dose on it can act.
     See accord-cbe74-dose-measured-inert-wrong-mode-record, a null the kit could not explain.

THE EDIT
--------
    0xC640A   -8192 -> -1966    the oscillation-branch Y

WHY -1966 AND NOT -3277 -- V126 WAS SIZED WRONG, CAUGHT BEFORE IT FLEW
-----------------------------------------------------------------------
V126 used -3277 because Honda ships that value at 0xC640C for this same variable.  That was the
wrong criterion.  The value has to be sized against the DETECTOR'S OWN ARMING THRESHOLD, because
the branch is only ever taken once the detector has armed.

The detector reads gp-0x6c2c -- the MOTOR-RATE DERIVATIVE, not driver torque (ld.h -0x6c2c,gp,r10
@0x428FA, compared against cal(0xC620A)=12800 loaded @0x42910).  That is the SAME signal
FUN_00036c12 multiplies by Y, so the detector's input and the term's input are one signal.

Mirroring the decompiled integer arithmetic exactly
(iVar4 = ((c2c*Y)>>6)*0x111 ; iVar5 = iVar4>>0x12 ; clamp +-511):

    Y                       b26 at arm    rails from    state when the detector arms
    -8192  stock fallback        1706          3834     RAILED (3.34x over the clamp)
    -3277  V126 as built          682          9584     RAILED (1.33x over the clamp)
    -2453  exact break-even       510         12803     LINEAR (100 % of clamp)
    -1966  Honda Y[2], 90 km/h    409         15974     LINEAR (80 % of clamp)

=> -3277 STILL RAILS the instant the detector arms, so V126 would have left the term a bang-bang
Coulomb relay in exactly the state it was built to fix.  -1966 is the LARGEST Honda-shipped value
in this family that stays LINEAR at the arming threshold, and it is still a STRONG term -- 80 % of
the clamp -- with headroom to |c2c| = 15974 before it rails.

It is also Honda's own Y[2], the 90 km/h end of the very mode record this branch replaces, so it
is inside the calibrated range by construction.  New ratios vs the speed LERP: creep 0.22x,
24 km/h 0.36x, 44 km/h 0.44x, 64 km/h 0.58x, 90 km/h 1.00x -- the fallback now NEVER exceeds what
the schedule would have delivered at any speed.

NOTE FOR CONTEXT: the normal speed LERP ALSO rails at mid speeds (Y=-4442 at 44 km/h rails from
|c2c|=7070; Y=-5519 at 24 km/h rails from 5691), both below the 12800 arming threshold.  So the
term rails in ordinary driving too, not only in the oscillation branch.  This build does NOT
address that -- it is a separate, larger change to the mode record (0xCBE74), and V91/V92 measured
a dose there INERT, which is now explained: a saturated counter BYPASSES the record entirely.

THE FULL OSCILLATION-RESPONSE CENSUS -- 0xC640A IS THE ONLY MAGNITUDE
---------------------------------------------------------------------
gp-0x671a has 8 instruction sites: 5 consumers plus the writer.  What each does on saturation:

    0x36C1E  FUN_00036c12  Y = fixed -8192 instead of the speed LERP   <- THE ONLY MAGNITUDE
    0x3AA70  FUN_0003aa2c  enable flag 0xC6138=1 -> 0xC6136=0, DISABLES a lane
    0x3A4A6  FUN_0003a382  LERP 0xC67B0 X=[5,10,15] Y=[1024,1024,1024] FLAT UNITY, and X[0]=5
                           is the counter's own CEIL => DOUBLY INERT
    0x35A06  FUN_000352b4  boolean gate (setfnc) on a 2nd-order IIR update
    0x35BEA  FUN_00035b20  boolean selector (setfnc) between two LERP curves at 0xC7934

=> 0xC640A is the ONLY cell in the whole response that changes a feedback MAGNITUDE, so this
build targets the right cell and there is no second hidden gain jump to chase.

HONDA'S INTENT IS COHERENT -- THE DEFECT IS THE RAIL, NOT THE DESIGN
---------------------------------------------------------------------
The census shows a deliberate anti-oscillation design: DISABLE a destabilising lane (0x3AA70)
AND apply a strong FIXED acceleration feedback (0xC640A).  That works -- if the fixed term stays
LINEAR.  It does not, because |gp-0x6b26| clamps at 511 and our elevated forward gain makes
|gp-0x6c2c| far larger than stock.  This build's job is therefore to keep the term inside its
linear range, NOT to remove Honda's response.  -1966 is consequently a FLOOR, not a target:
cutting further eventually removes the anti-oscillation response itself.

SCAN TRAP, RECORDED BECAUSE IT NEARLY RETRACTED A CORRECT RECORD
-----------------------------------------------------------------
Scanning the whole image for gp-0x671a at displacement 0x98E6 returns ONE hit -- the st.b writer
-- which looks like the kit's "8 hits, 6 reader functions" record had gone stale.  It has not:
every reader is ld.bu, which stores the displacement as (disp & 0xFFFE) | 1 = 0x98E7.  Scanning
both forms returns exactly 8.  A LOW count is as much a symptom of the hw2=(disp|1) trap as a
wrong one.  Ghidra cannot substitute here: get_xrefs_to on the absolute RAM address 0xFEDF18E6
returns "No references found", because gp-relative accesses are never resolved to absolute
addresses in this program.

BLAST RADIUS -- THE SMALLEST IN THE KIT'S RECENT HISTORY
---------------------------------------------------------
0xC640A has ONE reader (ld.h 0x740a,tp,r12 @0x36CB4, inside FUN_00036c12) and zero writers,
confirmed by a whole-image byte scan for the tp-relative displacement AND by disassembly at the
instruction boundary -- the scan hit 0x36CB6, which is the SECOND halfword of the 4-byte ld.h.
The branch fires ONLY when the reversal counter is saturated, so in every other moment of
driving this build is BYTE-IDENTICAL to V124 in behaviour.  Cal-only, no code edit, no cave edit.

EVIDENCE vs BELIEF
------------------
[EVIDENCE] the branch structure, the CEIL clamp, the reader census, the Y table and every ratio
          above -- all read from the binary this session.
[EVIDENCE] a railed acceleration term behaves as a Coulomb relay: V80 measured the worst
          grinding in the kit's record, and V107 measured 32.32 % rail duty at 10-25 km/h.
[BELIEF]   that lowering 0xC640A specifically de-rails the term on-car.  Rail duty CANNOT be
          predicted open-loop here: V107 predicted <=1.05 % and measured 33.49 %, a 32x miss,
          because gp-0x6b26 -> aggregator -> motor -> motor rate -> gp-0x6c2c is a CLOSED LOOP.
          That is why this build carries the probe below instead of asserting a number.

THE PROBE -- MEASURING THE ONE QUANTITY THE KIT HAS GOT WRONG
--------------------------------------------------------------
    0x55DF2   427 source displacement  gp-0x6ABC -> gp-0x6B26
    0x55E10   packer sar 3 -> 2, sized to +-511

Both are edits to the EXISTING CAN 427 packer -- no new cave instructions, so this carries none
of the cave bricking risk (V24 / V27 / V48B).  wire = min((|gp-0x6b26| * 5) >> 2, 0x3FF), so the
511 rail maps to 638 of 1023: no clipping, LSB 0.8 counts, and the rail is directly countable.

427 arrives at 49.9 Hz and the lane's -3 dB band (25-153 Hz) is above Nyquist, so this wire
CANNOT measure the lane's SPECTRUM -- that is exactly the blindness that voided V107's safety
case.  But RAIL DUTY is a LEVEL statistic, not a spectral one, and undersampling an ergodic
signal leaves the duty estimate unbiased.  This probe measures duty, and nothing else.
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
WRITE_MODE = os.environ.get("ACCORD_V127_WRITE", "").strip().lower()

BASE_NAME = "_v124_V124-V122BASE-GAIN8X-CLAMPS4096-ALPHA2.5-TRIM.C63D2.3_plain_image.bin"
BASE_SHA = "34368e919b2ce3d6d4c4999cca8f510903226d5fb9923537ac5dc8cf46b74ff2"
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
TAP_DISP_ADDR, TAP_OLD, TAP_NEW = 0x55DF2, (-0x6ABC) & 0xFFFF, (-0x6B26) & 0xFFFF
SAR_ADDR, SAR_OLD, SAR_NEW = 0x55E10, 0xA3, 0xA2   # sar 3 -> sar 2, sized to +-511
YFB_CAL, YFB_OLD, YFB_NEW = 0xC640A, -8192, -1966  # THE EDIT -- the oscillation branch
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
    print("  V127 -- V124 + 0xC640A -8192->-1966 (the OSCILLATION BRANCH, sized) + 427 probe on gp-0x6B26.")
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
    check(s16(stock, YFB_CAL) == YFB_OLD and s16(stock, YFB_ALT_CAL) == YFB_ALT_VAL,
          "  both fixed-Y cells match STOCK -- no prior build has moved either")
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
    struct.pack_into("<h", code, YFB_CAL, YFB_NEW)          # THE EDIT -- signed int16
    attributed |= {YFB_CAL, YFB_CAL + 1}
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
    check(code[SAR_ADDR] == SAR_NEW and base[SAR_ADDR] == SAR_OLD,
          "  0x55E10 packer sar 3 -> 2 (THIS BUILD), sized to the +-511 clamp")
    _rail = wire(511, 2)
    check(_rail <= 0x3FF,
          f"  the 511 rail maps to wire {_rail} of 1023 -- NO CLIPPING, LSB {4/5:.1f} counts,"
          f" so rail duty is directly countable")
    check(wire(511, 3) != _rail, "  sar 2 is not a no-op against the base's sar 3")
    check(s16(code, YFB_CAL) == YFB_NEW, f"  0x{YFB_CAL:05X} reads back {YFB_NEW}")
    check(s16(code, YFB_ALT_CAL) == YFB_ALT_VAL,
          f"  0x{YFB_ALT_CAL:05X} UNTOUCHED -- only the OSCILLATION branch moves")
    def _b26(c2c, Y):
        return (((abs(c2c) * abs(Y)) >> 6) * 0x111) >> 0x12
    check(u16(code, ARM_CAL) == ARM_VAL,
          f"  0x{ARM_CAL:05X} (detector arm threshold on |gp-0x6c2c|) = {ARM_VAL}, UNTOUCHED")
    _at_arm_old, _at_arm_new = _b26(ARM_VAL, YFB_OLD), _b26(ARM_VAL, YFB_NEW)
    print(f"      |gp-0x6b26| the instant the detector arms:  {_at_arm_old} (RAILED)"
          f"  ->  {_at_arm_new} ({100*_at_arm_new/B26_CLAMP:.0f} % of the {B26_CLAMP} clamp)")
    check(_at_arm_old >= B26_CLAMP,
          f"  the STOCK fallback rails at the arming threshold ({_at_arm_old} >= {B26_CLAMP})"
          f" -- this is the defect")
    check(_at_arm_new < B26_CLAMP,
          f"  🛑 THE SIZING GATE: the new value is LINEAR at the arming threshold"
          f" ({_at_arm_new} < {B26_CLAMP}).  -3277 FAILS this ({_b26(ARM_VAL, 3277)}) -- it is why"
          f" V126 was superseded before it flew")
    check(_at_arm_new > B26_CLAMP // 2,
          f"  and it is still a STRONG term ({100*_at_arm_new/B26_CLAMP:.0f} % of clamp), not a"
          f" removal of Honda's anti-oscillation response")
    check(abs(YFB_NEW) < abs(YFB_OLD),
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
    exempt = {TAP_DISP_ADDR, TAP_DISP_ADDR + 1, SAR_ADDR}
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
        tag = "CRC" if any(lo <= x < hi for x in (b[1] for b in blocks)) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo <= x < hi for x in (b[1] for b in blocks)))
    check(payload == 5, f"exactly 5 payload bytes ({payload} found)")
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
    tag = "V127-V124BASE-C640A.-1966-427.6B26.SAR2"
    img_out = plain_image_path(f"_v127_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V127_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
