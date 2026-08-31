# -*- coding: utf-8 -*-
r"""V261 -- V255 + ALL THREE LIVE ARMS, DOSE-SYMMETRIC ACROSS BOTH LANES.  SUPERSEDES V260.

    0x3AB76 / 0x3AC20   aa -> a9        rate lane 2x Kd   (V62's encoding, doses EVERY branch)
    0xC643E             1536 -> 3072    LANE 1 live arm
    0xC6440             2048 -> 4096    LANE 2 live arm A (the [0,5] ramp saturated)
    0xC6442             1024 -> 2048    LANE 2 live arm B (gp-0x671d != 0)

🛑 WHY THIS SUPERSEDES V260.  V260 doubled only `0xC6440` and `0xC6442`, which both belong to
**lane 2** (their loads sit at 0x3AC12 and 0x3ABFE, after lane 1's `sar` at 0x3AB76).  Lane 1's live arm
is a different cell, **`0xC643E` = 1536, loaded at 0x3AB68** -- and V260 left it at stock.  So V260 put
the two lanes at DIFFERENT doses.

That is not a cosmetic complaint.  The record's own reason for preferring the `sar` encoding over any
cal is that it is **DOSE-EXACT: it scales both lanes identically, so it is 2.000x on the total for
every value of the adaptive arm `a`**.  V260 broke precisely the property the encoding was chosen for,
and r26 is LIVE (V70's bit4: 1,644/18,010 frames strictly negative), so the imbalance is real rather
than notional.  **V260 is marked SUPERSEDED-DO-NOT-FLASH.**

THE ARM MAP, read from the image and confirmed against the decompile of FUN_0003aa2c:

    cal        value   loaded at   lane     status
    0xC643E     1536    0x3AB68    lane 1   LIVE
    0xC6444      512    0x3AB5E    lane 1   DEAD  (gp-0x683c branch)
    0xC6442     1024    0x3ABFE    lane 2   LIVE  (gp-0x671d != 0)
    0xC6440     2048    0x3AC12    lane 2   LIVE  (the [0,5] ramp saturated at 5)
    0xC6446     5244    0x3AC08    lane 2   DEAD  (gp-0x683c branch) = LEVER B

**LEVER B AND ITS LANE-1 TWIN ARE BOTH UNREACHABLE.**  Both are selected by `gp-0x683c != 0`, and that
byte has **zero writers** -- confirmed two ways: `FUN_00052e32` writes every neighbour (`-0x683b`,
`-0x683d`, `-0x683e`, `-0x6832`..`-0x6835`) and never `-0x683c`; and a corrected byte-form scan shows
all 14 apparent sites are aliases of `-0x683b` (for byte forms the displacement's bit 0 lives in
**hw1 bit 5**, so the opcode is bits **6-10**; decoding it as 5-10 conflates odd and even
displacements).  ⇒ **every Lever B measurement in this kit is of a dead cell**, V88's "bracketed
optimum" of 5244 included.  Both dead cells are left untouched here and asserted -- editing an
unreachable cell would be theatre.

⚠ **THE SELECTOR THRESHOLD IS A BYTE**: `cal_byte(0xC64FA)` = **5**, not the 517 a halfword read gives.
It is compared against a bounded [0,5] persistence ramp.

WHAT THIS ADDS OVER V255, AND WHY V255 STILL FLIES FIRST.  The `sar` sits AFTER the multiply, so it
doubles whichever arm is live -- including the **runtime LERP on motor rate**, which is the dominant
path and which **no calibration cell can reach** (its table is RAM at `gp-0x6e40`/`gp-0x6e38` with no
`st.h` writer anywhere in the image, so it is initialised once from flash outside gp-relative
addressing).  This build adds a second doubling only in the branches a cal CAN reach.  V255 is the
clean single-variable test; this is the escalation for *"helped but not enough"*.

🛑 THE DOSE IS UNVALIDATED, AND SAYING SO IS THE POINT.  With Lever B dead and the `sar` reverted
after V65, **this lane has not been dosed in ~200 builds and has no measured optimum at all.**  Doubling
stock is the smallest step that is clearly a step.  The lane output is hard-clamped at +-8192
(`0x3AC42 addi -0x2000` / `movea 0x2000`) and the aggregate at +-10240, so no dose can exceed what the
hardware already permits.

GATES.  GATE 1 vacuous (no cave; two immediate bytes and three cal halfwords).  GATE 2: Kd is a DAMPING
term -- phase lead, no pole moved into the right half plane; rails untouched and asserted.  The `sar`
bytes flew as V62/V65, fault-free, ST==4 zero over 86,278 frames.

BASE: V112.  Eight bytes.
"""
import hashlib
import os
import struct
import sys
import math
import zlib
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V261_WRITE", "").strip().lower()

BASE_NAME = "_v112_V112-V111BASE-RELAY.KNEE1800.K1.612_plain_image.bin"
BASE_SHA = "f032878c4e0b8e90d782ddac6ba2d644e09956cc1b267a60ef4fb1c44ee1f96f"

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
PROBE_HW2, SHIFT_OFF = 0x55DF2, 0x55E10
HW2_KEEP, SAR_KEEP = 0xC7EA, 0xA3          # V231's biquad-state probe -- CARRIED, asserted
# the re-aim: zeros 34.0 Hz, poles 28.0 Hz, r 0.920 -- bytes, never a re-derived decimal
REAIM_BIQ = bytes.fromhex("fa15f3bffaed6b3f25d9fcbf16d7693f")

# carried levers -- asserted, never re-set
LEVER_B, LEVER_B_VAL = 0xC6446, 5244        # V88's bracketed optimum -- CARRIED, asserted
RESID_SCALE_VAL = 1024                      # CARRIED, asserted
SLOPE_CAP, CAP_STOCK = 0xC6384, 2048        # V236's lever -- NOT touched here, asserted
BQ = 0xC60A8                                # a1, a2, b1, c4 -- four float32, direct form II
CLAMP_P, CLAMP_N = 0xC61B2, 0xC61B4         # forward clamps -- tracking BROKEN deliberately
CLAMP_OLD, CLAMP_NEW = 3072, 4096           # the ceiling that peak torque actually is
GAIN_CELL = 0xC6CD0                         # forward LKAS gain
GAIN_OLD, GAIN_NEW = 5346, 4455             # 6x -> 5x
SOFT_EME = 0xC674E                          # the interlock the clamp must stay BELOW
FB26 = 0xD774C                              # FactorB record, ENGAGED mode 26 (manual 24 @0xD6760)
FB_OLD, FB_NEW = 1024, 2048                 # flat Q10 gain at unity -> x2, no shape to corrupt
FB24 = 0xD6760                              # MANUAL FactorB -- asserted UNTOUCHED
FC26 = 0xD77D0                              # FactorC record, ENGAGED mode 26 (manual 24 @0xD67E4)
FC_Y0 = FC26 + 2 + 8                        # layout [npt][X x4][Y x4] -> Y[0]
FC_OLD, FC_NEW = 0, 429                     # := Y[2]; below X[0] the LERP clamps flat to Y[0]
FC24 = 0xD67E4                              # MANUAL FactorC -- asserted UNTOUCHED
FE26 = 0xD780C                              # FactorE record, ENGAGED mode 26 (manual 24 @0xD6820)
FE_X0, FE_Y1 = FE26 + 2, FE26 + 2 + 8 + 2   # layout [npt][X x4][Y x4]
X0_OLD, X0_NEW = 60, 12                     # open the rate dead zone
Y1_OLD, Y1_NEW = 140, 539                   # := Y[2], real slope on the first segment
FE24 = 0xD6820                              # MANUAL record -- asserted UNTOUCHED
OP_POINT = 99                               # gp-0x6ac0 in-burst, measured on-car [94,113]
FS_HZ = 1000.0                              # the control task rate
POLE_Y, K_STOCK = 0xC6906, 20               # the lag pole -- asserted STOCK, V241 does not touch it
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V261-V112BASE-RATELANE.2X.ALL3LIVEARMS.2X"

SAR_R26, SAR_R24 = 0x3AB76, 0x3AC20     # the two `sar` immediates -- V62's exact sites
SAR_1X, SAR_2X = 0xAA, 0xA9             # sar 0xa (stock) -> sar 0x9 (double the lane)
MUL_R24, MUL_R26 = 0x3AC18, 0x3AB6E     # the multiply each edit must stay AFTER
RAIL_SITES = {0x3AC42: "060600e0", 0x3AC46: "20c60020"}   # the +-8192 lane rails
ARM_A, ARM_A_OLD, ARM_A_NEW = 0xC6440, 2048, 4096   # LIVE: ramp saturated
ARM_B, ARM_B_OLD, ARM_B_NEW = 0xC6442, 1024, 2048   # LIVE: gp-0x671d != 0
ARM_L1, ARM_L1_OLD, ARM_L1_NEW = 0xC643E, 1536, 3072  # LANE 1's live arm -- V260 MISSED THIS
ARM_DEAD, ARM_DEAD_VAL = 0xC6446, 5244              # Lever B -- UNREACHABLE, asserted untouched
ARM_DEAD_L1, ARM_DEAD_L1_VAL = 0xC6444, 512         # lane 1's dead twin -- same gp-0x683c branch
SEL_THRESH = 0xC64FA                                # read as a BYTE (= 5), not a halfword

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def build():
    print("=" * 102)
    print("  V261 -- V255 + ALL THREE LIVE ARMS, DOSE-SYMMETRIC.  SUPERSEDES V260.")
    print("=" * 102)

    print("\n  [1] BASE = V112 -- what the operator says is on the car")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V112 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X,
          "base carries the STOCK 1x rate lane (sar 0xa at both sites) -- V62's fix is ABSENT, "
          "which is the whole reason for this build")
    check(u16(base, LEVER_B) == LEVER_B_VAL,
          f"Lever B is {LEVER_B_VAL} on this car (V62 flew with it at stock 512) -- the lane arm "
          f"is 10.2x higher, so the doubled lane clips on large transients where V62's never did")
    check(u16(base, GAIN_CELL) == 5346, "forward gain is 5346 (6x) -- NOT touched by this build")
    check(u16(base, CLAMP_P) == 3072 and u16(base, CLAMP_N) == 3072,
          "forward clamps are 3072 -- NOT touched by this build")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes, sar 0xa -> sar 0x9")
    code[SAR_R26] = SAR_2X
    code[SAR_R24] = SAR_2X
    attributed |= {SAR_R26, SAR_R24}
    check(code[SAR_R26] == SAR_2X and code[SAR_R24] == SAR_2X,
          "both rate lanes doubled -- the DOSE-EXACT encoding: it scales r24 AND r26 identically, "
          "so it is 2.000x on the total for every value of the adaptive arm a")
    check(SAR_R24 > MUL_R24 and SAR_R26 > MUL_R26,
          f"both edits are POST-MULTIPLY (0x{SAR_R24:05X} > 0x{MUL_R24:05X}, "
          f"0x{SAR_R26:05X} > 0x{MUL_R26:05X}) -- preserves the V850 mul high-word headroom at "
          f"47% of INT32_MAX rather than pushing it to 94%")

    print("\n  [2b] THE LIVE ARMS -- four bytes")
    check(u16(base, ARM_A) == ARM_A_OLD and u16(base, ARM_B) == ARM_B_OLD and
          u16(base, ARM_L1) == ARM_L1_OLD,
          f"base live arms are all stock: lane1 0x{ARM_L1:05X}={ARM_L1_OLD}, "
          f"lane2 0x{ARM_A:05X}={ARM_A_OLD} / 0x{ARM_B:05X}={ARM_B_OLD} -- none has EVER been moved")
    struct.pack_into("<H", code, ARM_A, ARM_A_NEW)
    struct.pack_into("<H", code, ARM_B, ARM_B_NEW)
    struct.pack_into("<H", code, ARM_L1, ARM_L1_NEW)
    attributed |= {ARM_A, ARM_A + 1, ARM_B, ARM_B + 1, ARM_L1, ARM_L1 + 1}
    check(u16(code, ARM_A) == ARM_A_NEW and u16(code, ARM_B) == ARM_B_NEW and
          u16(code, ARM_L1) == ARM_L1_NEW,
          f"all three live arms doubled: lane1 {ARM_L1_OLD}->{ARM_L1_NEW}, "
          f"lane2 {ARM_A_OLD}->{ARM_A_NEW} and {ARM_B_OLD}->{ARM_B_NEW}")
    check(ARM_L1_NEW == 2 * ARM_L1_OLD and ARM_A_NEW == 2 * ARM_A_OLD and
          ARM_B_NEW == 2 * ARM_B_OLD,
          "the dose is EXACTLY 2x on every live arm in BOTH lanes -- which is the dose-symmetry "
          "V62's sar encoding was chosen for, and the thing V260 broke")
    check(u16(code, ARM_DEAD) == ARM_DEAD_VAL and u16(code, ARM_DEAD_L1) == ARM_DEAD_L1_VAL,
          f"BOTH dead arms left untouched -- Lever B 0x{ARM_DEAD:05X}={ARM_DEAD_VAL} and its lane-1 "
          f"twin 0x{ARM_DEAD_L1:05X}={ARM_DEAD_L1_VAL}. Both sit behind the gp-0x683c branch, which "
          f"has zero writers, so editing either would be theatre")
    check(base[SEL_THRESH] == 5,
          f"the arm selector threshold is a BYTE = {base[SEL_THRESH]} (a halfword read gives "
          f"{u16(base, SEL_THRESH)}, which is the wrong width)")

    print("\n  [3] SATURATION, COMPUTED NOT ASSERTED")
    for _k, _who in ((ARM_B_OLD, "arm B stock"), (ARM_A_OLD, "arm A stock"),
                     (ARM_B_NEW, "arm B doubled"), (ARM_A_NEW, "arm A doubled")):
        print(f"      {_who:<14} k={_k:>5}:  1x clips above {8192 * 1024 // _k:>6}   "
              f"2x clips above {8192 * 512 // _k:>6}")
    check(8192 * 512 // ARM_B_OLD > 859,
          "at the STOCK live arms the doubled lane does NOT clip at the measured p50 input of 859")
    _clip_a = 8192 * 512 // ARM_A_NEW
    check(859 < _clip_a < 5120,
          f"with arm A doubled the clip point is {_clip_a}: ABOVE the measured p50 input of 859 so "
          f"the median frame is still linear, but BELOW the 5120 ceiling so the upper tail clips -- "
          f"stated, not hidden")

    print("\n  [4] THE RAILS AND EVERYTHING ELSE ARE FROZEN")
    for a, want in sorted(RAIL_SITES.items()):
        check(bytes(code[a:a + 4]).hex() == want,
              f"0x{a:05X} = {want} -- the +-8192 lane rail is UNTOUCHED")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- not the bricking class")
    check(u16(code, LEVER_B) == LEVER_B_VAL, f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")
    check(u16(code, GAIN_CELL) == 5346, "forward gain UNTOUCHED -- single variable")
    check(u16(code, CLAMP_P) == 3072 and u16(code, CLAMP_N) == 3072, "clamps UNTOUCHED")
    check(code[ALPHA2] == 14, "alpha2 stays at the CAR's 14 -- this build does not touch it")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the biquad block is BYTE-IDENTICAL -- no notch change in this build")

    print("\n  [6] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = u32(code, blk[1])
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block byte-identical to base")

    print("\n  [7] FULL BYTE DIFF vs V112")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(set(pay) <= {SAR_R26, SAR_R24, ARM_A, ARM_A + 1, ARM_B, ARM_B + 1,
                       ARM_L1, ARM_L1 + 1},
          "every payload byte is a sar immediate or a LIVE arm -- nothing else moved")
    check({SAR_R26, SAR_R24} <= set(pay), "both sar immediates actually moved")
    check(len(pay) >= 4, f"{len(pay)} payload bytes -- 2 sar + the live-arm high bytes")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V261 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v261_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V261_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V261 -- V255 + ALL THREE LIVE ARMS, DOSE-SYMMETRIC. SUPERSEDES V260.                               **")
    print("  **   0x3AB76 / 0x3AC20   aa -> a9       rate lane 2x (doses EVERY branch)                             **")
    print("  **   0xC643E             1536 -> 3072   LANE 1 live arm  <- V260 MISSED THIS                          **")
    print("  **   0xC6440             2048 -> 4096   lane 2 live arm A                                             **")
    print("  **   0xC6442             1024 -> 2048   lane 2 live arm B                                             **")
    print("  ** WHY V260 IS SUPERSEDED: its two cells are both LANE 2. Lane 1's live arm is                        **")
    print("  ** 0xC643E, loaded at 0x3AB68, and V260 left it stock -- putting the two lanes at                     **")
    print("  ** different doses. That breaks exactly the DOSE-EXACTNESS the sar encoding was                       **")
    print("  ** chosen for ('2.000x on the total for every value of a'), and r26 is LIVE.                          **")
    print("  ** BOTH DEAD ARMS LEFT ALONE: 0xC6446 (Lever B, 5244) and 0xC6444 (512) sit behind                    **")
    print("  ** the gp-0x683c branch, and that byte has ZERO WRITERS -- confirmed two ways.                        **")
    print("  ** => every Lever B measurement in this kit is of a dead cell.                                        **")
    print("  ** THE SAR IS STILL PRIMARY: it sits after the multiply, so it doubles whichever                      **")
    print("  ** arm is live, including the runtime LERP on motor rate -- the dominant path,                        **")
    print("  ** which no calibration cell can reach (its table is RAM with no st.h writer).                        **")
    print("  ** UNVALIDATED DOSE, AND THAT IS THE POINT: Lever B was dead and the sar was                          **")
    print("  ** reverted after V65, so this lane has no measured optimum at all.                                   **")
    print("  ** FLY V255 FIRST. This is the escalation for 'helped but not enough'.                                **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
