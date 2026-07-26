"""build_v38_tva.py - V38 = V37 + 4x-stock LKAS gain, matched 5120/5.0 soft-EME walls,
and the arb SETPOINT LIMIT raised 15360 -> 16384 (recovers the clipped top ~6% of the LKAS setpoint).

V38 changes the live LKAS gain 1782->3564 and both source clamps 1024->2048. The maximum modeled
merged command is 2048 LKAS + 2560 COMP = 4608, so both the direction corridor and ungated boost
floor move in int/float lockstep from 4096/4.0 to 5120/5.0. This leaves 512 counts of soft-wall margin.
The fixed +/-0x2800 and +/-0x2000 code clamps do not bind; the nominal 4762 runtime governor leaves
154 counts, though its dynamic speed/load schedule may reduce the runtime ceiling. All V37 gentle-EME
and DTC-0x49 guards are retained unchanged. Built from STOCK code.bin; cal-only; study artifact.

V38 ADDITION (operator-directed 2026-07-18) -- ARB SETPOINT LIMIT 15360 -> 16384
=========================================================================================================
The +/-clamp applied to the LKAS setpoint (gp-0x69ae) inside m_steer_torque_arbitration, immediately
BEFORE the Q15 LKAS gain (0xC646C), is sourced from a 9-point LERP whose Y row is FLAT 15360 in every
shipped record -- a degenerate curve, i.e. a constant clamp. openpilot CAR.HONDA_ACCORD uses
torqueBP=[[0,4096]] -> setpoint max = 4096*-4 = 16384, so the top 6.25% of the command range is clipped.
Raising the flat row 15360 -> 16384 removes exactly that clip: +6.71% top-end at every build tier
(V38: 1670 -> 1782 against the 2048 source clamp), observable only above 3840/4096 of commanded torque.

MECHANISM (call site 0x28fc8-0x2903a; verified by raw byte read, not re-decompiled this session):
    ld.bu -0x674e,gp,r12   ; mode selector BYTE
    mov   0xcb844,r8       ; pointer array  -> record; +0x14 = the Y row
    ...9-point LERP...     ; both out-of-range early exits also return Y[0]/Y[8]
    ld.h  -0x69ae,gp,r13   ; the LKAS setpoint
    cmp/bgt/subr/cmovle    ; SYMMETRIC +/- clamp
Record format = 40 bytes: [u16 count=9][9x u16 X][9x u16 Y][u16 pad]. The X row (3200..8320) is
identical in every record and is LEFT STOCK (guarded) -- only the flat Y row moves.

BLAST RADIUS (whole-image LE32 scan, this session):
  - pointer array 0xCB844 is referenced by EXACTLY ONE code site: 0x28FCE. No other subsystem shares it.
  - bank bases 0xE4180 / 0xE5180 appear ONLY inside that pointer array (0xCB844 / 0xCB85C). No aliases.
  - the axis is gp-0x6a5e (AVG voter = DRIVER column torque), so this is a driver-pushback taper surface
    that Honda shipped flattened; raising the flat row cannot feed the gentle-EME channel (that channel
    is gp-0x4f60 Sensor-B driver torque, causally independent of the LKAS command).
  - no IEEE-754 float 15360.0 exists image-wide (both endiannesses) -> NO float twin, so unlike the
    corridor/boost walls this edit has no lockstep mirror to keep in step. Hard-EME lockstep monitor
    FUN_00043e44 reads the INTEGER gp-0x6acc and casts it, so a rise lifts both sides together.

SCOPE -- ALL SELECTOR-REACHABLE RECORDS (operator-directed 2026-07-18):
Across all 16 variant slots (table 0xCD000, stride 0x24, selector byte at +0x1A) gp-0x674e takes only
{0,1,3,4,6,7,8,9}. Our A160 resolves via slot 2 (key 'TVAA1') -> selector 1 -> record 0xE41A8. Rather
than rely on that slot resolution (its HW-ID provenance is not fully pinned down), ALL EIGHT reachable
records are patched, so the change takes effect regardless of how the slot resolves. All eight rows are
byte-identical flat 15360 in stock and only one is ever read at runtime, so the extra records are inert.

NEW CRC BLOCKS -- FIRST BUILD IN THIS KIT TO TOUCH THEM:
The records live in bootloader CRC blocks [0xE4000,0xE4FFC) (blk#23) and [0xE5000,0xE5FFC) (blk#22),
which no prior build touched. Both are added to TOUCHED_BLOCKS. The linked-list page fields the walk
uses to chain blocks (at block_start-8/-6) sit INSIDE the preceding block's CRC range and are not
modified, so the 49-block chain topology is preserved; only the two trailer words change.

V37 HISTORY RETAINED BELOW

WHAT V36 CHANGES (operator-directed 2026-07-14)
=========================================================================================================
Root cause localized this session (rlog telemetry + Ghidra, self-verified): the gentle EME
(STEER_STATUS=no_torque_alert_2, felt as a sharp slight wheel-straightening mid-turn) is produced by a
DEBOUNCE STATE MACHINE, NOT by the engage-SM decider torque-MAX gate (0xC6312, which fires as benign
~10 Hz background and was shown NOT to correlate with the cut -> V33's 320->65535 was chasing the wrong
gate; V36 leaves 0xC6312 at stock 320).

The debounce FSM lives in TWO functions that BOTH read the SAME calibration thresholds and BOTH drive the
STEER_STATUS byte gp-0x6807:
    FUN_0002a30e            (0x2a30e, the status producer; rise 0x2a420.., hold 0x2a49a..)
    m_steer_torque_arbitration (0x29xxx inline twin; rise 0x2923e.., hold 0x292b8..)
A signed counter gp-0x6757 starts at -cal(0xC64E2)=-5 and only advances while a qualifying condition holds;
STEER_STATUS=4 fires only after 5 consecutive qualifying cycles. The qualifying condition (byte-verified in
Ghidra, both functions, rise + hold branches) is:

    gp-0x682f > cal[0xC64B4/B5]           (TORQUE channel:  gp-0x682f = min(|arb signal|>>5, 255))
      OR  param_1 > cal[0xC61C0]          (RATE channel:    param_1 = angular-rate magnitude, thr 1600)
      OR (param_2 && ((gp-0x682f>cal[0xC64B7] && param_1>cal[0xC61C2])         [secondary AND terms]
                   ||  (gp-0x682f>cal[0xC64B6] && param_1>cal[0xC61C4])))

Every load is ld.bu/ld.hu (UNSIGNED) and every compare is `cmp; bh` (UNSIGNED "branch if higher"), i.e. the
test is `cal < signal`. Raising each cal to its unsigned datatype max makes `cal < signal` PERMANENTLY FALSE:
  - byte cals -> 0xFF (255): gp-0x682f is a byte clamped to 255, so `255 < gp-0x682f` can never be true.
  - u16 cals  -> 0xFFFF (65535): param_1 is a clamped angular-rate magnitude (<= 65535), so `65535 < param_1`
    can never be true.
=> the debounce counter can never advance -> STEER_STATUS=4 can never be produced by either function.
This disables the TORQUE and the ANGLE-RATE trigger conditions COMPLETELY, exactly as directed.

BLAST RADIUS (verified: whole-image operand scan for each tp-displacement)
=========================================================================================================
0xC64B4/B5/B6/B7 (74b4/b5/b6/b7) and 0xC61C0/C2/C4 (71c0/c2/c4) are read ONLY by FUN_0002a30e and
m_steer_torque_arbitration -- the two copies of this one FSM. No other function reads them (all other search
hits were branch-target substring false-positives; the `mov 0xc71c4,ep` @0x2bb36 is a different ADDRESS,
0xC71C4, not the cal 0xC61C4). Both copies use the cals for the identical debounce purpose, so raising them
disables the condition in BOTH -- consistent with "disable the debounce state machine."

LEFT STOCK (deliberate)
=========================================================================================================
- 0xC6312 (=320): the engage-SM decider torque-MAX gate. Stock/V31. NOT the trigger (this session's finding).

V37 ADDITION -- DISABLE THE DTC-0x49 FAULT COUNTER (0xC64B8 112 -> 0xFF)  [operator-directed 2026-07-14]
=========================================================================================================
V36 (debounce SM off) UNMASKED a regression driven off the SAME function. Both the STEER_STATUS=4 counter
gp-0x6757 AND a separate DTC fail-counter gp-0x6758 run in m_steer_torque_arbitration on the same tick.
EVERY branch that sets/holds STEER_STATUS=4 also executes an in-code interlock `gp-0x6758 = 0`, and that was
the ONLY thing keeping gp-0x6758 (gated by 0xC64B8=112 on the same torque channel gp-0x682f, saturating at
cal(0xC64E0)+cal(0xC64E1)=50+50=100 cycles) from saturating. V36 made STEER_STATUS=4 unreachable -> the
interlock write never runs -> under sustained torque>112 the DTC counter free-runs to 100 (~1s at ~100 Hz)
and fires STEER_STATUS=7 + FUN_00016de6(0x49,1,1,1) = DTC 0x49. That set a burst of dashboard warning lights
and dropped LKAS (openpilot treats STEER_STATUS=7 as a permanent fault) while base power steering survived.
V37 raises 0xC64B8 112 -> 0xFF: gp-0x682f (byte, <=255) can never exceed 0xFF, so counter B never increments
-> it can never saturate -> DTC 0x49 can never fire. STEER_STATUS=4 stays disabled (V36 cals), so nothing
re-arms the interlock -- gp-0x6758 simply sits at 0.

0xC64B8 BLAST RADIUS (whole-image scan, all 185116 instrs; the ONE live side effect operator-ACCEPTED):
  6 direct byte reads (all ld.bu); NO absolute-pointer load of 0xC64B8; NO wide (ld.hu/ld.w) load spans the
  byte (every neighbour 0xC64B4/B5/B6/B7 read is single-byte ld.bu):
    0x2920a, 0x2921c  m_steer_torque_arbitration (LIVE) = DTC counter-B gate   -> INTENDED (counter disabled)
    0x29a78           m_steer_torque_arbitration (LIVE) = torque-arb branch
                      (torque>112 ? high-torque cutoff : full arb-curve interp) -> LIVE SIDE EFFECT, ACCEPTED
    0x2a3ec, 0x2a3fe  FUN_0002a30e  (DEAD: 0 callers/xrefs/ptrs)                 -> inert
    0x2a97a           FUN_0002a93a  (DEAD: 0 callers/xrefs/ptrs)                 -> inert
  ACCEPTED CONSEQUENCE: for torque in (112,255] the live arb no longer takes its high-torque cutoff branch at
  0x29a78 -- it runs the full arb-curve interpolation instead (a drivability change in the loaded-curve
  regime). TRADE-OFF: this also disables genuine DTC-0x49 fault detection (same trade accepted for the fix).
  NOTE: FUN_0002a30e / FUN_0002a93a are DEAD out-of-line copies; the LIVE logic is inlined in
  m_steer_torque_arbitration (called by w_steer_control_task@0x2214a). Corrects the "FUN_0002a30e = status
  producer" labeling in earlier docs -- that standalone copy never executes.

CAVEAT -- honest status (operator has this in the handoff)
=========================================================================================================
STEER_STATUS=4 was shown to be a REPORT; the exact instruction that ZEROES the LKAS motor term during the
felt cut was NOT located this session (the previously-assumed anchor gp-0x6809 is dead code -- 0 writers).
V36 provably kills the STEER_STATUS=4 debounce SM (and its arbitration twin). IF the felt assist-drop is
driven by this same gp-0x682f/param_1 condition (very likely -- same signals, same arbitration function),
V36 eliminates the gentle EME. IF the felt drop persists with NO STEER_STATUS=4, that is itself the decisive
result: the assist-drop is a separate path. V36 is thus a clean discriminating experiment, not a guaranteed
fix. STUDY ARTIFACT -- no flash until the operator names file + bus (kit iron rule).

ALL V31 EDITS RETAINED UNCHANGED: GAIN 1782, clamps 1024, ramp 0x1B, corridor x4 int+float, boost floor
4096 int+float, PN. ZERO code edits (cal-only).
"""
import os, sys, gzip, struct, zlib

if not __debug__:
    raise RuntimeError("V38 builder requires assertions; do not run with python -O")

from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for p in (HERE, FLASHING):
    if p not in sys.path:
        sys.path.insert(0, p)

from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31, OPS
from verify_bootloader_crc import walk

CODE_BIN     = STOCK_FW_DUMP / "code.bin"
TEMPLATE_T2F = CALIB_FILES / "39990-T2F-A210.rwd.gz"
OUT_DIR      = RWD_DIR
BIN_OUT      = plain_image_path("_v38_plain_image.bin")
V37_BIN      = plain_image_path("_v37_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"
V38_TAG       = "LKAS-4x-V37guards-softwall5120-float5-setpoint16384"
V38_OUT       = os.path.join(OUT_DIR, f"39990-TVA,A160-V38-{V38_TAG}-0x{START:X}-0x{END:X}.rwd")

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 5120
CORRIDOR_FLT = 5.0
BOOST_INT    = 5120
BOOST_FLT    = 5.0
LKAS_GAIN    = 3564
LKAS_CLAMP   = 2048
MAX_COMP     = 2560
MAX_MERGED   = LKAS_CLAMP + MAX_COMP
RUNTIME_GOVERNOR_NOMINAL = 4762
assert CORRIDOR_INT == BOOST_INT == 5120
assert CORRIDOR_FLT == BOOST_FLT == 5.0
assert CORRIDOR_INT > MAX_MERGED
assert RUNTIME_GOVERNOR_NOMINAL > MAX_MERGED

# ===================== V36: gentle-EME DEBOUNCE-SM conditions -> unsigned MAX (fully disabled) ============
# TORQUE channel (gp-0x682f), byte cals, unsigned compare -> max 0xFF. gp-0x682f is clamped to 255, so
# `0xFF < gp-0x682f` is never true. RISE uses 0xC64B4; HOLD uses 0xC64B5; secondary AND-terms use B7/B6.
DEBOUNCE_TORQUE_CALS = [  # (addr, cur, new, note) -- byte
    (0xC64B4, 112, 0xFF, "DEBOUNCE torque RISE tp+0x74b4  gp-0x682f> cut  112->255 (V36 MAX u8 = OFF)"),
    (0xC64B5,  96, 0xFF, "DEBOUNCE torque HOLD tp+0x74b5  gp-0x682f> cut   96->255 (V36 MAX u8 = OFF)"),
    (0xC64B7,  64, 0xFF, "DEBOUNCE torque 2ndAND tp+0x74b7 gp-0x682f> cut  64->255 (V36 MAX u8 = OFF)"),
    (0xC64B6,  54, 0xFF, "DEBOUNCE torque 2ndAND tp+0x74b6 gp-0x682f> cut  54->255 (V36 MAX u8 = OFF)"),
]
# RATE channel (param_1 angular-rate magnitude), u16 cals, unsigned compare -> max 0xFFFF. param_1 is a
# clamped rate (<= 65535), so `0xFFFF < param_1` is never true. RISE+HOLD share 0xC61C0; secondary C2/C4.
DEBOUNCE_RATE_CALS = [  # (addr, cur, new, note) -- u16
    (0xC61C0, 1600, 0xFFFF, "DEBOUNCE rate PRIMARY tp+0x71c0  param_1> cut 1600->65535 (V36 MAX u16 = OFF)"),
    (0xC61C2,  896, 0xFFFF, "DEBOUNCE rate 2ndAND  tp+0x71c2  param_1> cut  896->65535 (V36 MAX u16 = OFF)"),
    (0xC61C4, 1280, 0xFFFF, "DEBOUNCE rate 2ndAND  tp+0x71c4  param_1> cut 1280->65535 (V36 MAX u16 = OFF)"),
]
# ===================== V37: DTC-0x49 fault counter gate -> unsigned MAX (fully disabled) ==================
# Counter B (gp-0x6758) increment gate. gp-0x682f (byte, <=255) so `0xFF < gp-0x682f` is never true ->
# counter B never advances -> can never reach its 100-cycle saturation -> STEER_STATUS=7 + DTC 0x49 (via
# FUN_00016de6) can never fire. SHARED with the live torque-arb branch @0x29a78 (side effect ACCEPTED).
DTC_COUNTER_CAL = [  # (addr, cur, new, note) -- byte
    (0xC64B8, 112, 0xFF, "V37 DTC-0x49 counterB gate tp+0x74b8  gp-0x682f> cut 112->255 (fault counter OFF)"),
]

# ===================== V38 LKAS REACH (V37 values doubled; stock-based patch expectations) =====================
CAL_PATCHES = [
    (0xC646C, 891, LKAS_GAIN,  "GAIN     tp+0x746c  live arb Q15 output gain  891->3564 (x4 stock)"),
    (0xC61B4, 512, LKAS_CLAMP, "CLAMP    tp+0x71b4  live arb output clamp     512->2048 (x4 stock)"),
    (0xC61B2, 512, LKAS_CLAMP, "CLAMP    tp+0x71b2  live limit&pack clamp     512->2048 (x4 stock)"),
]
# ⚠ 2026-07-18 LABEL CORRECTION: "RAMPSTEP / EME ramp" is NOT supported. A whole-image scan found
# 0xC64DE's 18 read sites are ALL in the 0x29xxx/0x2axxx/0x2bxxx arbitration / STEER_STATUS / ENABLE
# region (mostly ld.bu) -- NONE in the command/governor path. The real per-cycle command slew limiter
# is in m_motor_torque_governor on gp-0x6ace, step = (cal x Q15)>>15 with cal 0xC6206=512 / 0xC6208=205.
# This edit has ridden along since V18 on flashed, road-validated builds, so it is retained unchanged --
# but do NOT reason about it as a command ramp step. See memory/reference_accord_watchdog_fault_sm_fun43e44.md
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "tp+0x74de  arbitration/STEER_STATUS-region byte  17->27 (V18 legacy; label disputed)"),
]

# ===================== V38: ARB SETPOINT LIMIT 15360 -> 16384 (recover clipped top ~6%) ===================
SETPOINT_PTR_ARRAY = 0xCB844          # the ONLY consumer is code site 0x28FCE
SETPOINT_RECORD_STRIDE = 0x28         # 40-byte record
SETPOINT_Y_OFF = 0x14                 # [u16 n][9x u16 X][9x u16 Y][u16 pad]
SETPOINT_N = 9
SETPOINT_X_STOCK = (3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320)
SETPOINT_STOCK = 15360
SETPOINT_NEW = 16384                  # openpilot ACCORD torqueBP=[[0,4096]] -> 4096*-4 = 16384
SETPOINT_LIVE_SELECTOR = 1            # A160 = variant slot 2 (key 'TVAA1') -> gp-0x674e = 1
# Every value gp-0x674e can take across all 16 variant slots (table 0xCD000+0x24*slot, byte +0x1A).
SETPOINT_REACHABLE_SELECTORS = (0, 1, 3, 4, 6, 7, 8, 9)
# Explicit expected record bases, asserted against the pointer array read from the stock image.
SETPOINT_RECORDS_EXPECT = {
    0: 0xE4180, 1: 0xE41A8, 3: 0xE41F8, 4: 0xE4220,
    6: 0xE5180, 7: 0xE51A8, 8: 0xE51D0, 9: 0xE51F8,
}
assert SETPOINT_LIVE_SELECTOR in SETPOINT_REACHABLE_SELECTORS
assert set(SETPOINT_RECORDS_EXPECT) == set(SETPOINT_REACHABLE_SELECTORS)
assert SETPOINT_NEW > SETPOINT_STOCK and SETPOINT_NEW <= 0xFFFF


def setpoint_records(code):
    """Resolve + verify the reachable setpoint records from the stock pointer array."""
    recs = []
    for sel in SETPOINT_REACHABLE_SELECTORS:
        base = struct.unpack_from("<I", code, SETPOINT_PTR_ARRAY + 4 * sel)[0]
        expect = SETPOINT_RECORDS_EXPECT[sel]
        if base != expect:
            raise AssertionError(f"setpoint ptr[{sel}]: expected 0x{expect:X} got 0x{base:X}")
        n = struct.unpack_from("<H", code, base)[0]
        if n != SETPOINT_N:
            raise AssertionError(f"setpoint rec 0x{base:X}: expected count {SETPOINT_N} got {n}")
        recs.append((sel, base))
    return recs


def setpoint_y_addrs(code):
    return [(sel, base + SETPOINT_Y_OFF + 2 * i)
            for sel, base in setpoint_records(code) for i in range(SETPOINT_N)]


def guard_setpoint_axis(code, note):
    """The X (driver-torque axis) row and the record count must stay byte-identical to stock."""
    for sel, base in setpoint_records(code):
        x = struct.unpack_from("<9H", code, base + 2)
        if x != SETPOINT_X_STOCK:
            raise AssertionError(f"GUARD setpoint X row rec 0x{base:X} (sel {sel}) altered: {x} ({note})")
        pad = struct.unpack_from("<H", code, base + SETPOINT_Y_OFF + 2 * SETPOINT_N)[0]
        if pad != 0:
            raise AssertionError(f"GUARD setpoint pad rec 0x{base:X} (sel {sel}) = {pad} ({note})")


def patch_setpoint_limit(code):
    for sel, base in setpoint_records(code):
        y = struct.unpack_from("<9H", code, base + SETPOINT_Y_OFF)
        if y != (SETPOINT_STOCK,) * SETPOINT_N:
            raise AssertionError(f"setpoint rec 0x{base:X}: expected flat {SETPOINT_STOCK}, got {y}")
        for i in range(SETPOINT_N):
            struct.pack_into("<H", code, base + SETPOINT_Y_OFF + 2 * i, SETPOINT_NEW)
        live = "  <-- LIVE (A160)" if sel == SETPOINT_LIVE_SELECTOR else ""
        print(f"  0x{base + SETPOINT_Y_OFF:05X}: sel {sel} Y[0..8] {SETPOINT_STOCK} -> {SETPOINT_NEW} "
              f"(flat, 9 halfwords){live}")
CORRIDOR_PATCHES = [
    (0xC674E,  1024,  CORRIDOR_INT, "INT dir1 Y[0] tp+0x774e  UPPER soft wall +1024->+5120"),
    (0xC6750,  1024,  CORRIDOR_INT, "INT dir1 Y[1] tp+0x7750  UPPER soft wall +1024->+5120"),
    (0xC675A, -1024, -CORRIDOR_INT, "INT dir2 Y[0] tp+0x775a  LOWER soft wall -1024->-5120"),
    (0xC675C, -1024, -CORRIDOR_INT, "INT dir2 Y[1] tp+0x775c  LOWER soft wall -1024->-5120"),
]
CORRIDOR_GUARD = [
    (0xC6748,     2, "INT TABLE1 N (count)"),
    (0xC674A, -8192, "INT TABLE1 X[0] velocity bkpt"),
    (0xC674C, -1024, "INT TABLE1 X[1] velocity bkpt"),
    (0xC6754,     2, "INT TABLE2 N (count)"),
    (0xC6756,  1024, "INT TABLE2 X[0] velocity bkpt"),
    (0xC6758,  8192, "INT TABLE2 X[1] velocity bkpt"),
]
FLOAT_CORRIDOR_PATCHES = [
    (0xC6598,  1.0,  CORRIDOR_FLT, "FLOAT dir1 Y[0] tp+0x7598  lockstep mirror +1.0->+5.0"),
    (0xC659C,  1.0,  CORRIDOR_FLT, "FLOAT dir1 Y[1] tp+0x759c  lockstep mirror +1.0->+5.0"),
    (0xC65AC, -1.0, -CORRIDOR_FLT, "FLOAT dir2 Y[0] tp+0x75ac  lockstep mirror -1.0->-5.0"),
    (0xC65B0, -1.0, -CORRIDOR_FLT, "FLOAT dir2 Y[1] tp+0x75b0  lockstep mirror -1.0->-5.0"),
]
FLOAT_CORRIDOR_GUARD_I = [
    (0xC658C, 2, "FLOAT dir1 N (count, int32)"),
    (0xC65A0, 2, "FLOAT dir2 N (count, int32)"),
]
FLOAT_CORRIDOR_GUARD_F = [
    (0xC6590, -8.0, "FLOAT dir1 X[0]"),
    (0xC6594, -1.0, "FLOAT dir1 X[1]"),
    (0xC65A4,  1.0, "FLOAT dir2 X[0]"),
    (0xC65A8,  8.0, "FLOAT dir2 X[1]"),
]
INT_BOOST_FLOOR_PATCHES = [
    (0xC6768,    0, BOOST_INT, "INT boost Y[0] tp+0x7768  flat soft wall 0->5120"),
    (0xC676A, 1536, BOOST_INT, "INT boost Y[1] tp+0x776a  flat soft wall 1536->5120"),
    (0xC676C, 2048, BOOST_INT, "INT boost Y[2] tp+0x776c  flat soft wall 2048->5120"),
]
FLOAT_BOOST_FLOOR_PATCHES = [
    (0xC65C4, 0.0, BOOST_FLT, "FLOAT boost Y[0] tp+0x75c4  lockstep mirror 0.0->5.0"),
    (0xC65C8, 1.5, BOOST_FLT, "FLOAT boost Y[1] tp+0x75c8  lockstep mirror 1.5->5.0"),
    (0xC65CC, 2.0, BOOST_FLT, "FLOAT boost Y[2] tp+0x75cc  lockstep mirror 2.0->5.0"),
]
INT_BOOST_GUARD = [
    (0xC6760,    3, "INT boost N (count)"),
    (0xC6762,  700, "INT boost X[0] tp+0x7762"),
    (0xC6764,  800, "INT boost X[1] tp+0x7764"),
    (0xC6766, 1100, "INT boost X[2] tp+0x7766"),
]
FLOAT_BOOST_GUARD_I = [
    (0xC65B4, 3, "FLOAT boost N (count, int32)"),
]
FLOAT_BOOST_GUARD_F = [
    (0xC65B8,  700.0, "FLOAT boost X[0]"),
    (0xC65BC,  800.0, "FLOAT boost X[1]"),
    (0xC65C0, 1100.0, "FLOAT boost X[2]"),
]
FLOAT_LERPB_STOCK_GUARD = [
    (0xC6664, 1.0, "ENVELOPE LERP_B Y[0] tp+0x7664 -- MUST stay stock 1.0"),
    (0xC6668, 1.0, "ENVELOPE LERP_B Y[1]"),
    (0xC666C, 1.0, "ENVELOPE LERP_B Y[2]"),
    (0xC6670, 1.0, "ENVELOPE LERP_B Y[3]"),
    (0xC6674, 1.0, "ENVELOPE LERP_B Y[4]"),
    (0xC6678, 1.0, "ENVELOPE LERP_B Y[5]"),
    (0xC667C, 1.0, "ENVELOPE LERP_B Y[6]"),
]
FLOAT_SPEEDGAIN_GUARD_F = [
    (0xC65F0,   2.0, "SPEED-gain float Y[0] -- stock"),
    (0xC65F8,   0.5, "SPEED-gain float Y[2] -- stock"),
]
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# ----- pre/post GUARD: 0xC64B8 is now PATCHED by V37 (was V36's left-stock guard); pre-stock 112 is
# verified by patch_bytes(DTC_COUNTER_CAL) itself (cur==112). List left empty so the post-patch guard
# does not expect stock 112. -----
DEBOUNCE_STOCK_GUARD_U8 = []
GENTLE_EME_DECIDER_STOCK_GUARD_U16 = [
    (0xC6312, 320, "engage-SM decider torque-MAX gate 0xC6312 -- LEFT STOCK 320 (V31 base; NOT the trigger)"),
]

# --- NO-CODE-EDIT guard: V36 is cal-only; these stock code sites MUST remain byte-identical ---
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x561C2, b"\x44\x07\xf0\xea", "0x660 packer byte0 zero-store -- stock (V36 is NOT a telemetry build)"),
    # engage-SM decider stays stock (cal-only edit): the disengage-decider instructions are untouched.
    (0x40dd0, b"\xe5\x87\x13\x73", "engage-SM param2 ld.hu 0x7312[tp],r16 -- stock (reads 0xC6312 kept 320)"),
    (0x40db8, b"\xe5\x3f\x13\x73", "engage-SM param1 ld.hu 0x7312[tp],r7  -- stock"),
    (0x40df4, b"\xe5\x3f\x13\x73", "engage-SM param3 ld.hu 0x7312[tp],r7  -- stock"),
    # debounce-SM cal READ sites stay stock (proves cal-only: only the cal DATA changes, not the code)
    (0x2a420, b"\x85\x6f\xb5\x74", "FUN_0002a30e rise ld.bu 0x74b4[tp],r13 -- stock (reads cal we edit)"),
    (0x2a42c, b"\xe5\x4f\xc1\x71", "FUN_0002a30e rise ld.hu 0x71c0[tp],r9  -- stock"),
    (0x2a49a, b"\xa5\x57\xb5\x74", "FUN_0002a30e hold ld.bu 0x74b5[tp],r10 -- stock"),
    (0x2a4a6, b"\xe5\x47\xc1\x71", "FUN_0002a30e hold ld.hu 0x71c0[tp],r8  -- stock"),
    (0x2923e, b"\x85\x5f\xb5\x74", "arb rise ld.bu 0x74b4[tp],r11 -- stock"),
    (0x2924a, b"\xe5\x47\xc1\x71", "arb rise ld.hu 0x71c0[tp],r8  -- stock"),
    (0x292b8, b"\xa5\x4f\xb5\x74", "arb hold ld.bu 0x74b5[tp],r9  -- stock"),
    (0x292c4, b"\xe5\x3f\xc1\x71", "arb hold ld.hu 0x71c0[tp],r7  -- stock"),
]
CAVE_GUARD = (0xC4E00, 0x18)


def patch_cal_u(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#06x} got {got:#06x} ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_corridor(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} got {got} ({note})")
        struct.pack_into("<h", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_float(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} got {got} ({note})")
        struct.pack_into("<f", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6.1f} -> {new:6.1f}   {note}")


def patch_bytes(code, table):
    for addr, cur, new, note in table:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}   {note}")


def guard_u16(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_u8(code, table):
    for addr, expect, note in table:
        if code[addr] != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {code[addr]} ({note})")


def guard_s16(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_int32(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<i", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_float(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_no_code_edit(code, table):
    for addr, expect_bytes, note in table:
        got = bytes(code[addr:addr + len(expect_bytes)])
        if got != expect_bytes:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect_bytes.hex()} got {got.hex()} ({note})")


def make_tva_headers(template_info):
    new = []
    for tag, vals in template_info["headers"]:
        if tag == b"/":
            new.append((tag, [b"39990-TVA-A110", b"39990-TVA,A160"]))
        elif tag == b"!":
            new.append((tag, [vals[0], vals[0]]))
        elif tag == b"%":
            new.append((tag, [CAN_SIG_BYTE]))
        else:
            new.append((tag, list(vals)))
    return new


def full_image(plain_window):
    img = bytearray(b"\xff" * 0x100000)
    img[START:END] = plain_window
    return bytes(img)


def recompute_crc(code, start, crc_off):
    old = struct.unpack_from("<I", code, crc_off)[0]
    new = zlib.crc32(code[start:crc_off]) & 0xFFFFFFFF
    struct.pack_into("<I", code, crc_off, new)
    print(f"  CRC [0x{start:X},0x{crc_off:X}) @0x{crc_off:X}: 0x{old:08X} -> 0x{new:08X}")


TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),   # covers debounce cals (0xC61C0.., 0xC64B4..), 0xC64B8, AND all V31 cals
    (0xE4000, 0xE4FFC),   # V38 setpoint-limit records sel 0/1/3/4 (blk#23) -- NEW, first build to touch
    (0xE5000, 0xE5FFC),   # V38 setpoint-limit records sel 6/7/8/9 (blk#22) -- NEW, first build to touch
    (0x13000, 0xC4FFC),   # covers the PN bytes
]
# Chain integrity: walk() finds each next block via u16 page fields at block_start-8/-6, which live in
# the PRECEDING block's range -- never inside a block we patch. Assert we only move trailer words.
SETPOINT_CRC_BLOCKS = [(0xE4000, 0xE4FFC), (0xE5000, 0xE5FFC)]

# V37 is CAL-ONLY: the two SM copies' CODE must stay byte-identical to stock (only cal DATA changes).
# 0xC64B8 lives in the cal block (0xC6xxx), NOT in these code ranges -> these MUST diff to ZERO.
FSM_CODE_RANGES = [
    (0x29000, 0x29400, "m_steer_torque_arbitration LIVE SM + arb branch"),
    (0x2A30E, 0x2A508, "FUN_0002a30e dead copy"),
]
# Full application code must remain stock. Calibrations begin at tp=0xBF000.
CAL_ONLY_CODE_RANGE = (0x15000, 0xBF000)
V38_VS_V37_FIELDS = [
    (0xC646C, 2), (0xC61B4, 2), (0xC61B2, 2),
    (0xC674E, 2), (0xC6750, 2), (0xC675A, 2), (0xC675C, 2),
    (0xC6598, 4), (0xC659C, 4), (0xC65AC, 4), (0xC65B0, 4),
    (0xC6768, 2), (0xC676A, 2), (0xC676C, 2),
    (0xC65C4, 4), (0xC65C8, 4), (0xC65CC, 4),
    # V38 setpoint limit: 8 reachable records x 9 halfwords, appended at runtime by setpoint_y_addrs().
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V37 guards + 4x-stock LKAS gain/clamps + matched 5120/5.0 soft-EME walls"
          f" + setpoint limit {SETPOINT_STOCK}->{SETPOINT_NEW}")
    out = os.path.join(OUT_DIR, f"39990-TVA,A160-{label}-{tag}-0x{START:X}-0x{END:X}.rwd")
    for stale in (out, BIN_OUT):
        if os.path.exists(stale):
            os.remove(stale)
    code = bytearray(code_stock)

    # pre-patch guards
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    guard_u8(code, DEBOUNCE_STOCK_GUARD_U8)
    guard_u16(code, GENTLE_EME_DECIDER_STOCK_GUARD_U16)
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
    guard_setpoint_axis(code, "pre-patch")
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave must be 0xFF before patch"
    # Snapshot the setpoint CRC blocks so we can prove ONLY the Y rows + trailers move.
    setpoint_blocks_before = {a: bytes(code[a:c + 4]) for a, c in SETPOINT_CRC_BLOCKS}
    setpoint_y = setpoint_y_addrs(code)

    # patches -- V36 debounce-SM disable
    patch_bytes(code, DEBOUNCE_TORQUE_CALS)    # gp-0x682f byte thresholds -> 0xFF
    patch_cal_u(code, DEBOUNCE_RATE_CALS)      # param_1 u16 thresholds -> 0xFFFF
    patch_bytes(code, DTC_COUNTER_CAL)         # V37: DTC-0x49 counter-B gate 0xC64B8 -> 0xFF
    # V31 base (unchanged)
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_corridor(code, INT_BOOST_FLOOR_PATCHES)
    patch_float(code, FLOAT_BOOST_FLOOR_PATCHES)
    patch_setpoint_limit(code)                 # V38: arb setpoint limit 15360 -> 16384 (all 8 reachable)
    patch_bytes(code, PN_PATCHES)

    # post-patch guards (untouched arms still stock; left-stock cals still stock)
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    guard_u8(code, DEBOUNCE_STOCK_GUARD_U8)                 # (empty in V37: 0xC64B8 now patched)
    guard_u16(code, GENTLE_EME_DECIDER_STOCK_GUARD_U16)     # 0xC6312 STILL stock 320
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
    guard_setpoint_axis(code, "post-patch")                 # X rows + pads still stock
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave tail must remain 0xFF"

    # V38 setpoint blocks: ONLY the 72 Y halfwords may differ (trailers are rewritten after this).
    setpoint_y_bytes = {p for _, a in setpoint_y for p in (a, a + 1)}
    assert len(setpoint_y_bytes) == 8 * SETPOINT_N * 2 == 144, "expected 144 setpoint Y bytes"
    for a, c in SETPOINT_CRC_BLOCKS:
        before = setpoint_blocks_before[a]
        moved = {a + i for i in range(len(before)) if code[a + i] != before[i]}
        assert moved <= setpoint_y_bytes, f"stray edit in setpoint block 0x{a:X}: {sorted(moved - setpoint_y_bytes)}"
        assert moved, f"setpoint block 0x{a:X} unchanged"
        # linked-list page fields for the NEXT block live at a-8/a-6, outside this block: unmodified.
        assert bytes(code[a - 8:a - 4]) == bytes(code_stock[a - 8:a - 4]), f"chain page fields @0x{a-8:X} moved"

    # V38 cal-only proof: all application code and the focused SM ranges remain byte-identical to stock.
    for a, b, note in FSM_CODE_RANGES:
        assert bytes(code[a:b]) == bytes(code_stock[a:b]), f"FSM CODE EDIT 0x{a:X}-0x{b:X} ({note})"
    a, b = CAL_ONLY_CODE_RANGE
    assert bytes(code[a:b]) == bytes(code_stock[a:b]), f"APPLICATION CODE EDIT 0x{a:X}-0x{b:X}"

    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    # Exact lineage proof against the already-built V37 plain image.
    v37 = open(V37_BIN, "rb").read()
    assert len(v37) == len(code) == 0x100000, "V37/plain image size mismatch"
    assert struct.unpack_from("<H", v37, 0xC646C)[0] == 1782
    assert struct.unpack_from("<H", v37, 0xC61B4)[0] == 1024
    assert struct.unpack_from("<H", v37, 0xC61B2)[0] == 1024
    assert all(v37[x] == 0xFF for x in (0xC64B4, 0xC64B5, 0xC64B6, 0xC64B7, 0xC64B8))
    assert all(struct.unpack_from("<H", v37, x)[0] == 0xFFFF for x in (0xC61C0, 0xC61C2, 0xC61C4))
    assert all(struct.unpack_from("<H", v37, a)[0] == SETPOINT_STOCK for _, a in setpoint_y), \
        "V37 must still carry the stock flat 15360 setpoint rows"
    allowed = {p for addr, size in V38_VS_V37_FIELDS for p in range(addr, addr + size)}
    allowed.update(p for _, a in setpoint_y for p in (a, a + 1))     # 72 setpoint Y halfwords
    allowed.update(range(0xC6FFC, 0xC7000))
    for _, crc_off in SETPOINT_CRC_BLOCKS:                           # 2 new block trailers
        allowed.update(range(crc_off, crc_off + 4))
    v37_diffs = {i for i in range(START, END) if code[i] != v37[i]}
    assert v37_diffs <= allowed, f"unexpected V38-vs-V37 bytes: {sorted(v37_diffs - allowed)}"
    for addr, size in V38_VS_V37_FIELDS:
        assert bytes(code[addr:addr + size]) != bytes(v37[addr:addr + size]), f"V38 field unchanged @0x{addr:X}"
    n_fields = len(V38_VS_V37_FIELDS) + len(setpoint_y)
    print(f"  V38-vs-V37 exact lineage: {len(v37_diffs)} changed byte(s), "
          f"all within {n_fields} fields + 3 block CRCs")

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    print(f"  ECU-decode==patched: {matches}   CRC blocks failing: {fails}")

    # readback asserts (decode the emitted .rwd from scratch)
    for addr, _, new, _ in DEBOUNCE_TORQUE_CALS:
        assert ecu_plain[addr - START] == new, f"debounce torque cal @0x{addr:X} lost (want {new:#x})"
    for addr, _, new, _ in DEBOUNCE_RATE_CALS:
        assert struct.unpack_from("<H", ecu_plain, addr - START)[0] == new, f"debounce rate cal @0x{addr:X} lost"
    # left-stock invariants must survive
    assert ecu_plain[0xC64B8 - START] == 0xFF, "0xC64B8 must be 0xFF (V37 DTC-0x49 counter-B disabled)"
    assert struct.unpack_from("<H", ecu_plain, 0xC6312 - START)[0] == 320, "0xC6312 must stay stock 320 (V31 base)"
    # V31 base survives
    assert struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0] == LKAS_GAIN, "GAIN lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B4 - START)[0] == LKAS_CLAMP, "CLAMP b4 lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B2 - START)[0] == LKAS_CLAMP, "CLAMP b2 lost"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lost"
    for addr, _, new, _ in CORRIDOR_PATCHES:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == new, f"int corridor @0x{addr:X}"
    for addr, _, new, _ in FLOAT_CORRIDOR_PATCHES:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == new, f"float corridor @0x{addr:X}"
    for addr, _, new, _ in INT_BOOST_FLOOR_PATCHES:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == new, f"int boost floor @0x{addr:X}"
    for addr, _, new, _ in FLOAT_BOOST_FLOOR_PATCHES:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == new, f"float boost floor @0x{addr:X}"
    for addr, expect, note in CORRIDOR_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int corridor GUARD @0x{addr:X} ({note})"
    for addr, expect, note in INT_BOOST_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int boost GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_BOOST_GUARD_I:
        assert struct.unpack_from("<i", ecu_plain, addr - START)[0] == expect, f"float boost N GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_BOOST_GUARD_F:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"float boost X GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_LERPB_STOCK_GUARD:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"LERP_B stock GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_SPEEDGAIN_GUARD_F:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"speed-gain stock GUARD @0x{addr:X} ({note})"
    for addr, expect_bytes, note in NO_CODE_EDIT_SITES:
        got = bytes(ecu_plain[addr - START:addr - START + len(expect_bytes)])
        assert got == expect_bytes, f"unexpected code edit @0x{addr:X} ({note})"
    # V38 setpoint limit survives the encode/decode round trip, on every reachable record
    for sel, base in SETPOINT_RECORDS_EXPECT.items():
        assert struct.unpack_from("<I", ecu_plain, SETPOINT_PTR_ARRAY - START + 4 * sel)[0] == base, \
            f"setpoint ptr[{sel}] moved"
        y = struct.unpack_from("<9H", ecu_plain, base + SETPOINT_Y_OFF - START)
        assert y == (SETPOINT_NEW,) * SETPOINT_N, f"setpoint Y row rec 0x{base:X} (sel {sel}) = {y}"
        x = struct.unpack_from("<9H", ecu_plain, base + 2 - START)
        assert x == SETPOINT_X_STOCK, f"setpoint X axis rec 0x{base:X} (sel {sel}) altered"
        assert struct.unpack_from("<H", ecu_plain, base - START)[0] == SETPOINT_N, f"setpoint count rec 0x{base:X}"
    assert struct.unpack_from("<9H", ecu_plain, SETPOINT_RECORDS_EXPECT[SETPOINT_LIVE_SELECTOR]
                              + SETPOINT_Y_OFF - START) == (SETPOINT_NEW,) * SETPOINT_N, \
        "LIVE (A160, selector 1) setpoint record not raised"
    assert bytes(ecu_plain[0xC4E00 - START:0xC4E18 - START]) == b"\xff" * 0x18, "cave region must be 0xFF (no caves)"
    pn_old = b"39990-TVA-A160"; pn_new = b"39990-TVA,A160"
    assert ecu_plain.count(pn_old) == 0 and ecu_plain.count(pn_new) == 2, "PN lost"

    diffs = [i for i in range(START, END) if code[i] != code_stock[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    print(f"  byte-diff vs stock: {len(diffs)} bytes in {len(runs)} run(s):")
    for a, b in runs:
        print(f"     0x{a:05X}-0x{b:05X} ({b - a + 1}B)")

    if not matches or fails:
        print(f"  *** {label} self-check FAILED -- not writing ***\n")
        return None

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out, "wb") as f:
        f.write(rwd)
    with open(BIN_OUT, "wb") as f:
        f.write(full_image(ecu_plain))
    print(f"  WROTE {os.path.relpath(out, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)} (1MB plain image for Ghidra verify)\n")
    return out


def main():
    # Invalidate prior outputs before any fallible input/preflight work. This includes V38 .rwd files
    # emitted under an EARLIER tag -- leaving a stale, differently-named V38 artifact in rwd/ is a
    # flash-safety hazard (the operator names a file by hand at flash time).
    import glob
    stale_tagged = [p for p in glob.glob(os.path.join(OUT_DIR, "39990-TVA,A160-V38-*.rwd"))
                    if os.path.abspath(p) != os.path.abspath(V38_OUT)]
    for stale in stale_tagged + [V38_OUT, BIN_OUT]:
        if os.path.exists(stale):
            os.remove(stale)
            print(f"  removed stale artifact {os.path.relpath(stale, REPO)}")
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  (built from stock)")
    print("V38 = V37 guards + live LKAS gain 3564 + both source clamps 2048")
    print("      + matched corridor/boost soft-EME walls 5120 integer / 5.0 float")
    print(f"      + arb setpoint limit {SETPOINT_STOCK}->{SETPOINT_NEW} on all "
          f"{len(SETPOINT_REACHABLE_SELECTORS)} selector-reachable records (+6.71% top-end)")
    print(f"      modeled merged max {MAX_MERGED}; wall margin {CORRIDOR_INT - MAX_MERGED}; nominal governor margin {RUNTIME_GOVERNOR_NOMINAL - MAX_MERGED}")
    print("      (0xC6312 decider LEFT STOCK 320; cal-only, NO code edits)\n")
    out = build("V38", code, headers, tag=V38_TAG)
    assert out == V38_OUT, f"unexpected output path: {out}"
    if out is None:
        raise RuntimeError("V38 self-check failed; no artifact emitted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
