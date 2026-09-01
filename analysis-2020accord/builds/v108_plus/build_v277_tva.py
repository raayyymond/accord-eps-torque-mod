# -*- coding: utf-8 -*-
r"""V277 -- THE DRIVER-OVERRIDE CLIFF, SOFTENED.  AND A TAP THAT CARRIES BOTH.  BASE: V268.

TWO OPERATOR DECISIONS, 2026-09-01, both taken after the original x2.5 design was FALSIFIED:
  (1) "Soften the cliff instead" -- keep the threshold near stock, replace the dropout with a
      gradual roll-off, targeting the LET-GO FEEL rather than the threshold.
  (2) Bit-pack the CAN-427 field so it carries the variant selector AND a live demand channel.

=== WHAT WAS FALSIFIED, AND WHY IT MATTERS MORE THAN THE EDIT ==================================
This build began as "move the override taper's X knots out by 2.5x".  An adversarial agent
falsified its premise and the operator changed the design.  The premise was that taper slots
10-27 were live.  THEY ARE DEAD:
  * FUN_00057f8e -- the variant matcher -- is `i = 0; do {...} while (i < 0x10);`.  Only records
    0..15 of the 0x24-stride table at 0xCD000 are ever searched.  Records 16+ are 0xFF filler.
  * FUN_00042692 writes byte +0x1A of the matched record to gp-0x674E (st.b at 0x4272A, the ONE
    writer image-wide), and gp-0x674E is a DIRECT UNSCALED word index into every per-variant bank
    (ld.bu at 0x29AA0, shl 0x2 at 0x29AAA).
  * Byte +0x1A over the 16 searchable records is {0,0,1,1,0,0,1,1,3,4,6,7,6,8,8,9}.  MAX 9.
  => REACHABLE SLOTS ARE {0,1,3,4,6,7,8,9}.  Slots 2, 5 and 10-27 are dead calibration.
  => This also RESOLVES the kit's long-open question in accord-variant-selector-chain-0xcd000
     ("record 2 (slots 10/11) vs record 11 (24/25/26/27) UNRESOLVED"): NEITHER.  Any earlier build
     that dosed only slots 10-27 dosed dead cells.  Worth a lineage check.

=== WHAT THE LIVE CURVE ACTUALLY IS -- A CLIFF, NOT A TAPER ====================================
Three distinct shapes are reachable, and only ONE of them is a cliff:
  A  X(70,72,78,80)  Y(254,234,12,0)   banks 0xCBA04 + 0xCBA74   16 recs   <- 99% -> 0% in 320 raw
  B  X(32,38,80,112) Y(255,255,255,0)  bank  0xCB8B4              8 recs   <- already a linear fade
  C  X(32,42,80,112) Y(255,255,255,0)  bank  0xCB924              8 recs   <- already a linear fade
Bank selection: sign agreement between LKAS command and driver torque picks the pair (0x29A8E),
then gp-0x6803 == 2 picks within it (0x29A80).  So shape A is the mode==2 pair -- INCLUDING the
OPPOSING-torque case, which is the actual driver-override case.
Shape A drops authority from 254 to 0 across raw driver torque 2240..2560.  That is a 320-count
DROPOUT, and it lands exactly where the operator drives: his median override torque is 2289 raw
(index 71), one index step inside the cliff.  (!) PROVENANCE: 2289 is r75's WIRE figure 2235
unit-converted (x1.024), not re-derived from the census.  The census's own override-conditioned
median is the POOLED 2819 raw = index 88 -- EIGHT steps past the cliff's far end, in total dropout.
The conservative number is quoted here; the pooled one is what the table below uses.  This is the firmware behind the long-standing report
that the assist does not fade under load -- it LETS GO.

=== THE EDIT -- 16 RECORDS.  X[0] AND Y[0] UNCHANGED. ==========================================
  X (70, 72, 78, 80)  ->  (70,  84,  98, 112)      kick-in raw 2240  UNCHANGED
  Y (254, 234, 12, 0) ->  (254, 170, 85,   0)      zero moves raw 2560 -> 3584
Segment widths become a uniform 14/14/14 and the drops 84/85/85: a near-straight fade, not a knee.
Only the 8 reachable slots of the two mode==2 banks are touched.  Banks 0xCB8B4/0xCB924 are ALREADY
linear fades and are left BYTE-STOCK; so is every unreachable slot.  All asserted, per record.

WHY ZERO LANDS AT 112 AND NOT SOMEWHERE ELSE: 112 is exactly where banks B and C already reach
zero.  After this edit all four banks share ONE full-override threshold (raw 3584) instead of the
mode==2 pair cutting out 1024 counts early.  The number is Honda's own, not ours.

DELIVERED CURVE, read from the BUILT IMAGE (record 0xE43F0, opposing / mode==2, LIVE):
      raw torque | idx | V276 | V277 |
            2240 |  70 | 100% | 100% |  kick-in -- the two curves AGREE here
            2289 |  71 |  96% |  97% |  operator's median override push
            2560 |  80 |   0% |  76% |  stock FULL override -- THE DROPOUT IS GONE
            2819 |  88 |   0% |  57% |  pooled median override (34-route census)
            3082 |  96 |   0% |  38% |  override p75
            3306 | 103 |   0% |  21% |  override p90
            3584 | 112 |   0% |   0% |  V277 full override
Full override is STILL FULLY AVAILABLE -- at a torque reached in 1.6% of override time, versus
~75% for stock's 2560.  Asserted: V277 authority >= V276 at every index 0..255 (this build only
RELAXES), and the new curve is MONOTONE NON-INCREASING (more push never buys more assist).

=== [B] TELEMETRY -- 34 BYTES REWRITTEN IN PLACE, CARRYING BOTH SIGNALS ========================
  wire = 0x10 | (gp-0x674E & 0x0F) | ((gp-0x674B >> 3) << 5)      [0x1AB byte1 + byte0 bits 1:0]
     bits 3:0  VARIANT SELECTOR  (max 9, so 4 bits is lossless -- verified from the table)
     bit  4    LIVENESS BEACON   (so a dead channel reads 0 and a live one never can)
     bits 9:5  POST-TAPER DEMAND INDEX / 8  (0..240 in 30 steps; 3.3% quantisation, stated as a cost)
  DECODE: wire = ((b0 & 3) << 8) | b1 ; sel = wire & 0xF ; live = (wire>>4)&1 ; demand = (wire>>5)*8
The window 0x55DF0..0x55E12 is rewritten IN PLACE, same length, and `jarl FUN_00049a90` at 0x55E12
is untouched -- no branch is re-encoded.  The room comes from five instructions that are dead when
the source is an unsigned byte: `jarl abs`, `mov r10,r6`, `ori 0xffff`, `jarl min`, `andi 0xffff`.
Every written instruction is DECODED field-by-field from the built bytes, and every opcode is
cross-checked against a real instance elsewhere in this image.  That check earned its keep twice:
an encoder derived the `or` opcode as 0x04 when it is 0x08, and this file's own first draft had
`andi`/`ori` as 0x06/0x04 when they are 0x36/0x34.  Both would have shipped wrong instructions.

WHY BOTH CHANNELS: the selector is STATIC -- written once at init, never changing while driving --
so on its own it CANNOT OBSERVE ANY LEVER IN THIS BUILD.  The demand index is the taper's OUTPUT and
the assist map's INPUT, live at loop rate.  Plotted against driver torque it IS the taper curve,
measured on the car.  Shipping only the selector would have violated the standing rule that every
build carries the instrument for its own edit.
(!) The selector names the SLOT, not the part number.  V277's wire carries the RAW NIBBLE in bits
    3:0, so selector 1 <- records 2/3/6/7, selector 6 <- records 10/12, selector 8 <- records 13/14.
    An earlier draft quoted 5/30/40 here; those were V276's |sel| x 5 numbers and are MEANINGLESS on
    this build's wire.  And a part number ABSENT from the table falls back to record 0,
    indistinguishable from a genuinely selector-0 car.

=== RISK, PLAINLY =============================================================================
 1. THIS BUILD ONLY RELAXES DRIVER OVERRIDE.  Between raw 2560 and 3584 the lane now keeps 76% down
    to 0% of authority where it previously kept NONE.  Pushing the wheel in that band will meet
    real resistance that was not there before.  The threshold at which resistance BEGINS is
    unchanged (2240), and full override is still reachable (3584) -- but the middle is different.
 2. HONDA'S OTHER OVERRIDE LAYER IS ALREADY DEAD, and not by this build.  A driver-fighting-the-
    assist plausibility ladder exists in FUN_00028ea6, keyed on gp-0x682f (the taper's own X axis)
    with a sign-comparison direction discriminator, and it sets DTC 0x49 via FUN_00016de6.  Its
    thresholds 0xC64B4/B5/B6/B7/B8 are all 255 (stock 112/96/54/64/112) and 0xC61C0/C2/C4 all
    65535 (stock 1600/896/1280), against a byte index clamped to 240.  IT CANNOT FIRE.  V112 did
    that, not V277, and V277 does not touch gp-0x682f -- but it means the taper is the ONLY
    driver-override mechanism left in this ECU, so softening it is not one protection among several.
 3. THE PLAUSIBILITY-FAIL PATH DISABLES OVERRIDE.  0x290B8 writes the taper index to ZERO on an
    implausible torque reading (outside +-25600 at 0x28F30), and index 0 is FULL AUTHORITY.  Stock,
    unchanged, and it matters more now.
 4. openpilot's own steeringPressed disengage still applies.  It is OUTSIDE this ECU and is not
    something this image guarantees.

=== WHAT ELSE IS IN THIS BUILD (carried from V276, byte-identical) =============================
  assist map 0xC9A88 x6 (the LKAS RATE REFERENCE, 28 records) and feedback clamp 0xC62E6
  7680 -> 46080, preserving Honda's setpoint:feedback ratio 1.395.
  0xC62E6 is safe as an unsigned value: exactly THREE tp-form readers image-wide (0x28F96/0x28F9C/
  0x28FB8), ALL `ld.hu` zero-extending, so 46080 is never read as the -19456 it would be as s16.
  Re-derived per build run, not inherited.

  THE DELIVERED CEILING IS 3072, NOT 2505.  An earlier draft of this file said the forward-gain
  path is bounded by (15360 * 5346) >> 15 = 2505 via a P clamp at 0xC61BC.  THAT CHAIN IS WRONG:
  0xC61BC = 15360 sits on a different leg, applied after `sar 0x8`, not upstream of the forward
  gain.  The binding clamp on the 0xC6CD0 path is `ld.hu tp+0x71b4` = 0xC61B4 = 3072.
  The 6x claim survives in a STRONGER form: gain 891 -> 5346 is 6.000000 and clamp 512 -> 3072 is
  6.000000, so the knee is UNCHANGED at 18830 -- a uniform 6.000x dilation of the whole curve, not
  a ceiling that moved.  ⚠ Honest limit: this is the ceiling of the 0xC6CD0 forward-gain path
  terminating at gp-0x6b38.  That gp-0x6b38 is the FINAL motor torque is NOT proven; do not write
  "max LKAS torque = 3072" without closing that step.
  V277 changes no cal and no instruction on that path, so it cannot move the ceiling either way.

=== INSTRUMENT -- how ONE short drive reads this build =========================================
  * 427 (0x1AB) byte1 + byte0[1:0]: selector AND live demand, as above.
  * Driver torque, free on 0x18F/399 bytes 0-1.  DECODER: raw = wire * 128/125 = wire * 1.024, and
    opendbc's factor is -1.  The EPS builds that frame as -(raw * 125 >> 7) (FUN_00055C42 ->
    FUN_000218BE).  A prior kit figure never applied this and was wrong by 2.34%.
  * Achieved column rate, free on 399 bytes 2-3 at 100 Hz (magnitude-clamped +-12000).
  * THE READOUT: 427-demand plotted against 0x18F-torque IS the taper curve.  Stock shows a step to
    zero at raw 2560; V277 must show a straight ramp from 2240 to 3584.  That is a large, obvious
    difference visible from a handful of override brushes.
  * THE SENTENCE A NULL LICENSES: "the demand channel never went above raw 2240, so the taper was
    never exercised."  Override is 8.26% of engaged time in normal driving, so a few deliberate
    pushes against the lane supply it -- but they must be DONE, not assumed.
  * extract_r73.py:555 hard-codes a 427 threshold of 160 -- a V277 decoder MUST NOT reuse that path.

=== CLASS OF BUILD, against the whole arc since V38 ============================================
GENUINELY NEW, twice over.  The arc has moved authority (V38-52), lane gains (V62-73), damping
(V74-84), phase (the notch era) and forward gain (V101-112).  V276 was the first to move the rate
REFERENCE.  V277 is the first to touch the DRIVER-OVERRIDE curve at all -- these four banks are
virgin across every FLOWN build (diffing the taper records against stock over all 274 plain images in
accord-firmwares finds them non-stock in exactly TWO: V273's, withdrawn unflashed, and V277's own); V273/V274/V275 proposed flattening them and all three were
withdrawn unflashed.  It is also the first build to bit-pack two signals onto one CAN field.
It is NOT the x2.5 knee-shift this build started as: that design was falsified and abandoned, and
the shape here is a different intervention on the same curve.
"""

import hashlib
import os
import struct
import sys
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

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                               # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                                   # noqa: E402

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V277_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
TAG = "V277-V276BASE-OVERRIDE.CLIFF.SOFTENED.TAP.PACKED"
# The x2.5 knee-shift design was FALSIFIED and withdrawn.  The TAG names the SHIPPED
# design, not the one this file started as: a flashable .rwd carrying the name of a
# discarded design is what gets flashed by mistake six weeks later.

K = 6                                       # the rate-axis scale factor

# ---- [A] telemetry ---------------------------------------------------------------------------
# The tap is re-pointed from V276's variant selector to gp-0x674B, the POST-TAPER LKAS demand
# index (st.b r22 at 0x29D14).  One field instruments BOTH levers: it is the taper's OUTPUT and
# the assist map's INPUT.  The selector is not lost -- BOTH live-variant candidates (10/11 and
# 24-27) carry the SAME taper record, so the selector cannot change this build's meaning.
PACK_LO, PACK_HI = 0x55DF0, 0x55E12                  # the 34 bytes rewritten, in place
PACK_V268 = bytes.fromhex("24374495bfff663c0a30803effffbfff7a3cca36ffff"
                          "e53740022046ff03003aa332")
PACK_NEW = bytes.fromhex("8437b398"    # ld.bu -0x674e[gp],r6   selector -> r6   (even disp, op 3C)
                         "a43fb598"    # ld.bu -0x674b[gp],r7   demand   -> r7   (odd  disp, op 3D)
                         "c6360f00"    # andi 0x0f,r6,r6        selector &= 0x0F (max 9, lossless)
                         "86361000"    # ori  0x10,r6,r6        LIVENESS BEACON -> bit 4
                         "833a"        # shr  0x3,r7            demand >>= 3     (0..30)
                         "c53a"        # shl  0x5,r7            demand <<= 5
                         "0731"        # or   r7,r6             combine
                         "2046ff03"    # movea 0x3ff,r0,r8      clamp HI = 1023  (moved, unchanged)
                         "003a"        # mov  0x0,r7            clamp LO = 0     (moved, unchanged)
                         "000000000000")   # nop nop nop -- the slack the dead abs/min/andi freed
MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)
TAPER_N = 4
TAPER_SHAPES = {(70, 72, 78, 80): (254, 234, 12, 0),      # A -- CBA04/CBA74, THE CLIFF (edited)
                (32, 38, 80, 112): (255, 255, 255, 0),   # B -- CB8B4, already a linear fade
                (32, 42, 80, 112): (255, 255, 255, 0),   # C -- CB924, already a linear fade
                (32, 48, 64, 112): (255, 205, 154, 0),   # slots 10-27 -- UNREACHABLE, stock
                (32, 38, 64, 102): (255, 255, 255, 0),   # slots 2/5   -- UNREACHABLE, stock
                (32, 38, 54, 96): (255, 255, 223, 0)}    # slots 2/5   -- UNREACHABLE, stock
KP_PTR, KD_PTR = 0xCB994, 0xCB7D4
CAVE, HOOK = (0xC4B34, 0xC4BD8), 0x55C0E
SAR_R26, SAR_R24, SAR_1X = 0x3AB76, 0x3AC20, 0xAA
MODE2_BANKS = (0xCBA04, 0xCBA74)                     # the pair carrying the CLIFF shape
SOFT_BANKS = (0xCB8B4, 0xCB924)                      # already linear fades -- LEFT BYTE-STOCK
A_OLD_X, A_OLD_Y = (70, 72, 78, 80), (254, 234, 12, 0)
A_NEW_X, A_NEW_Y = (70, 84, 98, 112), (254, 170, 85, 0)
VARIANT_TBL, VARIANT_STRIDE, VARIANT_N = 0xCD000, 0x24, 16   # FUN_00057f8e loops while i < 0x10
SEL_OFF, NEIGHBOUR_OFF = 0x1A, 0x19                          # gp-0x674E and gp-0x674D
X_CEIL = 255
TORQUE_PER_X = 32
IDX_SITE = 0x29A7C
SAT_SITE = 0x29060
SAR_TQ_SITE = 0x2904A
DEAD_OVERRIDE_B = {0xC64B4: 255, 0xC64B5: 255, 0xC64B6: 255, 0xC64B7: 255, 0xC64B8: 255}
DEAD_OVERRIDE_H = {0xC61C0: 65535, 0xC61C2: 65535, 0xC61C4: 65535}
GRAB_RATE_REC = 0xC6974

# ---- [C] feedback clamp ----------------------------------------------------------------------
FB_CELL, FB_STOCK, FB_NEW = 0xC62E6, 7680, 7680 * K
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)      # all three must be ld.hu (low byte 0xE5)

# ---- frozen torque path, all asserted --------------------------------------------------------
FROZEN = {
    0xC61B4: 3072,                     # OUTPUT clamp -- the TRUE ceiling of the 0xC6CD0 path.
                                       # 6.000x stock 512.  An earlier draft quoted 2505 from a
                                       # chain that is NOT what the bytes do; corrected.
    0xC6CD0: 5346,                     # forward gain -- 6.000x Honda's 891.  Because BOTH gain and
                                       # clamp are exactly 6x, the knee is UNCHANGED at 18830:
                                       # a uniform 6.000x dilation, not a moved ceiling.
    0xC61B6: 10240,  0xC61BA: 10240,   # D clamp / I anti-windup -- FROZEN
    0xC61BC: 15360,  0xC61BE: 15360,   # P clamp / sum clamp -- FROZEN (a DIFFERENT leg, applied
                                       # after `sar 0x8`, NOT upstream of the forward gain)
    0xC63E6: 0,                        # Ki -- stays OFF
    0xC63E8: 923,    0xC63EA: 1560,    # feedback lag pole / input gain
    0xC63EC: 992,    0xC63EE: 507,     # 5 Hz output LPF
    0xC62E4: 4,                        # error deadband
    0xC6B26: 256,    0xC6B12: 98,      # the driver-side PID -- untouched
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
}
GAIN_CELL, GAIN_V268 = 0xC6CD0, 5346
OUT_CELL, OUT_V268 = 0xC61B4, 3072
GAIN_SITE = 0x2A1EE
KP_N, KD_N = 5, 4
JARL_CLAMP = 0x55E12                                # `jarl FUN_00049a90` -- MUST stay untouched
SEL_WRITER = 0x4272A                                # st.b r8,-0x674e,gp   (the ONE writer)
DEMAND_WRITER = 0x29D14                             # st.b r22,-0x674b,gp  (post-taper demand)
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1         # demand clamped +-240

CAVE, HOOK = (0xC4B34, 0xC4BD8), 0x55C0E
SAR_R26, SAR_R24, SAR_1X = 0x3AB76, 0x3AC20, 0xAA
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1
KP_PTR, KD_PTR = 0xCB994, 0xCB7D4
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)      # must all be ld.hu (low byte 0xe5)

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


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p, n):
    return ([u16(b, p + 2 + 2 * i) for i in range(n)],
            [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)])


def build():
    print("=" * 102)
    print("  V277 -- V276 + THE OVERRIDE CLIFF SOFTENED, AND A TAP THAT CARRIES BOTH.  BASE V268.")
    print("=" * 102)

    print("\n  [1] BASE = V268")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}")
    check(u16(base, FB_CELL) == FB_STOCK, f"base feedback clamp == {FB_STOCK}")
    check(bytes(base[0x2A1F0:0x2A1F2]) == bytes.fromhex("d07c"),
          "0x2A1F0 = d0 7c (stock 6c 74) -- V112's REDIRECT of the gain load from tp+0x746c "
          "(0xC646C) to tp+0x7cd0 (0xC6CD0).  The 6x is a REDIRECT PLUS a newly programmed cell, "
          "not one cell changing value: STOCK 0xC6CD0 IS 0xFFFF, erased flash.")
    check(u16(base, 0xC646C) == 891,
          "and 0xC646C still holds Honda's 891, untouched by the redirect -- so 5346/891 = 6.000000 "
          "compares what the gain load READS before and after, which is the honest comparison")
    check(u16(base, GAIN_CELL) == GAIN_V268, f"base forward gain == {GAIN_V268} (= 6 x Honda's 891)")
    check(u16(base, OUT_CELL) == OUT_V268, f"base output clamp == {OUT_V268} -- the TORQUE CAP")
    check(bytes(base[PACK_LO:PACK_HI]) == PACK_V268,
          "base 427 packer window is the expected 34 bytes")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49 (the flash-time model)")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X, "rate lane stock 1x (V62 NOT restored)")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240, "index clamp +-240 unchanged")

    print("\n  [1b] THE SIGN-EXTENSION DEFECT -- V276 raises NEITHER cell that carries it")
    # CORRECTED TWICE. BOTH 0xC61B4 AND 0xC61BE have EIGHT tp-form readers in TWO stages, not
    # four, and each stage carries one sign-extended read. The second
    # stage at 0x2A910..0x2A92E lives in a region Ghidra never made a function, so every
    # Ghidra-only xref census is BLIND to it; it was found by raw byte scan. Each stage carries
    # one sign-extended read. V276 freezes the cell, so this documents rather than gates -- but
    # V275's "exactly ONE sign-extended read" was a FALSE [PASS] -- and the first fix repeated
    # the same undercount on 0xC61BE (second stage 0x2B024..0x2B03C) until an audit caught it.
    # LESSON: a Ghidra-only xref census is blind to code outside a recognised function; every
    # census here is a raw little-endian byte scan over the WHOLE image.
    SIGN_SITES = {0xC61BE: ((0x2A13E, 0xE5), (0x2A146, 0x25), (0x2A14C, 0xE5), (0x2A156, 0xE5),
                            (0x2B024, 0xE5), (0x2B02C, 0x25), (0x2B032, 0xE5), (0x2B03C, 0xE5)),
                  0xC61B4: ((0x2A1F8, 0xE5), (0x2A20C, 0x25), (0x2A212, 0xE5), (0x2A21C, 0xE5),
                            (0x2A910, 0xE5), (0x2A91E, 0x25), (0x2A924, 0xE5), (0x2A92E, 0xE5))}
    for cal_, sites in SIGN_SITES.items():
        n_sign = 0
        for a, want in sites:
            kind = "ld.hu ZERO-ext" if base[a] == 0xE5 else "ld.h  SIGN-ext" if base[a] == 0x25 else "??"
            check(base[a] == want, f"0x{cal_:05X} read @0x{a:05X} {base[a]:02X} = {kind}")
            n_sign += base[a] == 0x25
        check(n_sign == 2,
              f"0x{cal_:05X}: {len(sites)} tp-form reads in TWO stages, {n_sign} sign-extended "
              f"-> hard cap 32767")
    print("      -> 0xC61BE stays 15360 (a 6x would be 92160: over u16 AND over the sign cap).")
    check(base[GAIN_SITE] == 0x25, f"0x{GAIN_SITE:05X} is ld.h (sign-ext) -- gain capped at 32767")
    print("      -> V276 raises NEITHER 0xC61B4 NOR 0xC6CD0.  The 6x is on the RATE axis only.")

    print("\n  [1c] the feedback clamp's OWN reads must all be ld.hu, or 6x would break it")
    for a in FB_SITES:
        check(base[a] == 0xE5, f"0x{a:05X} {base[a]:02X} = ld.hu (zero-extend) -- safe above 32768")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] [A] TELEMETRY -- CAN 427 (0x1AB) CARRIES *BOTH* SELECTOR AND LIVE DEMAND")

    # ---- the variant table, read from the image; everything downstream depends on it ----------
    sel = [base[VARIANT_TBL + VARIANT_STRIDE * i + SEL_OFF] for i in range(VARIANT_N)]
    nbr = [base[VARIANT_TBL + VARIANT_STRIDE * i + NEIGHBOUR_OFF] for i in range(VARIANT_N)]
    LIVE = sorted(set(sel))
    check(sel == [0, 0, 1, 1, 0, 0, 1, 1, 3, 4, 6, 7, 6, 8, 8, 9],
          f"variant selector byte over the {VARIANT_N} searchable records: {sel}")
    check(max(sel) <= 9,
          f"MAX SELECTOR = {max(sel)}.  FUN_00057f8e loops `while (i < 0x10)`, so records 16+ are "
          f"UNREACHABLE by construction; the selector is a DIRECT unscaled word index into each "
          f"bank (ld.bu 0x29AA0 + shl 0x2 0x29AAA).  => TAPER SLOTS 10-27 ARE DEAD.")
    check(LIVE == [0, 1, 3, 4, 6, 7, 8, 9],
          f"REACHABLE SLOTS = {LIVE} -- slots 2 and 5 are never produced either")
    check(all(x == 0 for x in nbr),
          f"gp-0x674D (the byte the tap's neighbour would supply) is ZERO in all {VARIANT_N} "
          f"searchable records -- so a 16-bit read of the selector cannot be contaminated.  "
          f"Asserted rather than assumed: this was previously 'safe by luck'.")
    check(max(sel) <= 15, "and the selector fits FOUR BITS, so `andi 0x0f` below is LOSSLESS")

    # ---- the two source cells are real -------------------------------------------------------
    check(bytes(base[SEL_WRITER:SEL_WRITER + 4]) == bytes.fromhex("4447b298"),
          f"0x{SEL_WRITER:05X} `st.b r8,-0x674e,gp` -- the selector's ONE writer, disp 0x98B2")
    check(bytes(base[DEMAND_WRITER:DEMAND_WRITER + 4]) == bytes.fromhex("44b7b598"),
          f"0x{DEMAND_WRITER:05X} `st.b r22,-0x674b,gp` -- the POST-TAPER demand index, written by "
          f"the live LKAS rate PID immediately after the taper multiply")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240,
          "demand is clamped +-240 by 0xC64F0/0xC64F1, so it needs 8 bits before quantisation")

    # ---- the rewrite ------------------------------------------------------------------------
    check(bytes(base[PACK_LO:PACK_HI]) == PACK_V268, "base packer window is the expected 34 bytes")
    check(len(PACK_NEW) == len(PACK_V268) == PACK_HI - PACK_LO,
          f"the replacement is EXACTLY {PACK_HI-PACK_LO} bytes -- IN PLACE, no length change, no "
          f"alignment change, no branch target moved")
    code[PACK_LO:PACK_HI] = PACK_NEW
    attributed |= set(range(PACK_LO, PACK_HI))
    check(bytes(code[PACK_LO:PACK_HI]) == PACK_NEW, "packer window rewritten")
    check(bytes(code[JARL_CLAMP:JARL_CLAMP + 4]) == bytes(base[JARL_CLAMP:JARL_CLAMP + 4])
          == bytes.fromhex("bfff7e3c"),
          f"`jarl FUN_00049a90` at 0x{JARL_CLAMP:05X} is UNTOUCHED and keeps its displacement.  It "
          f"is OUTSIDE the rewritten window [0x{PACK_LO:05X},0x{PACK_HI:05X}), not inside it.")

    # THE REWRITE DELETES TWO `jarl` CALLS, and no assertion previously said so:
    #   0x55DF4  jarl 0x00049A5A  = abs(r6)          -- DELETED
    #   0x55DFE  jarl 0x00049A78  = unsigned min     -- DELETED
    # Both are PURE LEAF routines: register-only, no memory access, no onward call, `jmp lp`.
    # They are safe to delete because two zero-extended BYTE loads plus explicit masking already
    # bound the value -- abs() and min(.,0xFFFF) are no-ops on a u8.  Asserted below.
    # These WERE documentation wearing a [PASS] until an audit proved it by injection: the old pair
    # asserted only "these two bytes are not both zero" (true of nearly every address) and a
    # comparison between two literals (cannot fail for any image).  Replaced with a real decode of
    # the Format-V `jarl disp22` TARGETS in the base, which binds the claim to the bytes.
    def jarl_target(addr, img=None):
        img = base if img is None else img
        hw1, hw2 = u16(img, addr), u16(img, addr + 2)
        if (hw1 >> 6) & 0x1F != 0b11110:
            return None
        disp = (((hw1 & 0x3F) << 16) | hw2) & ~1
        if disp & (1 << 21):
            disp -= 1 << 22
        return addr + disp

    check(jarl_target(JARL_CLAMP) == 0x49A90,
          f"POSITIVE CONTROL for the jarl decoder: 0x{JARL_CLAMP:05X} resolves to 0x49A90, the clamp "
          f"helper this build KEEPS.  The decoder is validated before any null is drawn from it.")
    for site, tgt, lbl in ((0x55DF4, 0x49A5A, "abs"), (0x55DFE, 0x49A78, "unsigned min")):
        check(jarl_target(site) == tgt,
              f"0x{site:05X} in the BASE is `jarl 0x{tgt:05X}` ({lbl}) -- DECODED from the bytes. "
              f"V277 deletes this call.")
        check(not (PACK_LO <= tgt < PACK_HI),
              f"and 0x{tgt:05X} lies OUTSIDE the rewritten window -- the CALL goes, the callee stays")
    # NO jarl SURVIVES IN THE WINDOW -- and this is ENTAILED, not separately scanned.  A byte scan
    # is the wrong instrument here: the jarl opcode field collides with ld.bu, so a naive mask
    # reports the two loads as calls.  What actually settles it is that the ten field-by-field
    # decodes above pin EVERY instruction in the window by opcode, registers and immediate, and
    # none of the ten is a jarl.  The 12 boundaries tile the 34 bytes exactly (asserted above), so
    # there is no room for an eleventh instruction to hide.
    BOUNDS = (0, 4, 8, 12, 16, 18, 20, 22, 26, 28, 30, 32)
    check(BOUNDS[-1] + 2 == len(PACK_NEW) and len(BOUNDS) == 12,
          "the 12 decoded instruction boundaries tile the 34-byte window exactly -- no room for an "
          "undecoded instruction, so 'no jarl in the window' follows from the decodes above")
    check(sum(2 if o in (16, 18, 20, 26, 28, 30, 32) else 4 for o in BOUNDS) == len(PACK_NEW),
          "and the per-instruction lengths sum to exactly 34 bytes")

    # ---- decode every written instruction back, from the BUILT bytes -------------------------
    _hw = lambda o: struct.unpack_from("<H", code, PACK_LO + o)[0]
    for off, want_op, want_r1, want_r2, want_disp, lbl in (
            (0, 0x3C, 4, 6, 0x98B2, "ld.bu -0x674e[gp],r6  (selector, EVEN disp -> op 0x3C)"),
            (4, 0x3D, 4, 7, 0x98B5, "ld.bu -0x674b[gp],r7  (demand,   ODD  disp -> op 0x3D)")):
        hw1, hw2 = _hw(off), _hw(off + 2)
        check((hw1 >> 5) & 0x3F == want_op and (hw1 & 0x1F) == want_r1 and (hw1 >> 11) == want_r2
              and (hw2 | 1) == (want_disp | 1),
              f"+{off}: {lbl} -- opcode/reg1/reg2/disp all DECODED from the written bytes")
    for off, want_op, want_imm, want_r1, want_r2, lbl in (
            (8, 0x36, 0x0F, 6, 6, "andi 0x0f,r6,r6"), (12, 0x34, 0x10, 6, 6, "ori 0x10,r6,r6")):
        hw1, hw2 = _hw(off), _hw(off + 2)
        # reg1 is the SOURCE.  An audit proved that without this clause three mutations pass every
        # assertion and ship DIFFERENT images -- `andi 0x0f,r7,r6` masks the DEMAND instead of the
        # selector, `ori 0x10,r7,r6` overwrites the selector with the demand, and `andi 0x0f,r0,r6`
        # makes the selector field CONSTANT ZERO.  That last one is the dangerous one: a dead
        # selector field is indistinguishable on the wire from a genuinely selector-0 car, and the
        # beacon would still read 1, so the liveness test would call the channel healthy.
        check((hw1 >> 5) & 0x3F == want_op and (hw1 & 0x1F) == want_r1
              and (hw1 >> 11) == want_r2 and hw2 == want_imm,
              f"+{off}: {lbl} -- opcode, SOURCE reg1, dest reg2 and imm16 all decoded")
    for off, want_op, want_imm, want_r2, lbl in (
            (16, 0x14, 3, 7, "shr 0x3,r7"), (18, 0x16, 5, 7, "shl 0x5,r7")):
        hw1 = _hw(off)
        check((hw1 >> 5) & 0x3F == want_op and (hw1 & 0x1F) == want_imm and (hw1 >> 11) == want_r2,
              f"+{off}: {lbl}")
    check((_hw(20) >> 5) & 0x3F == 0x08 and (_hw(20) & 0x1F) == 7 and (_hw(20) >> 11) == 6,
          "+20: or r7,r6 -- opcode 0x08 (an uncontrolled encoder derived 0x04 here and was WRONG)")
    check(_hw(22) == 0x4620 and _hw(24) == 0x03FF, "+22: movea 0x3ff,r0,r8 -- clamp HI, unchanged")
    check(_hw(26) == 0x3A00, "+26: mov 0x0,r7 -- clamp LO 0; the beacon makes a floor unnecessary")
    check(all(code[PACK_LO + 28 + k] == 0 for k in range(6)),
          "+28: three NOPs fill the slack freed by the dead abs/min/andi -- no stray instruction")

    # ---- the encodings are COPIED from real instances in this image, not invented -------------
    for ref, want, lbl in ((0x28FC8, 0x3784, "ld.bu EVEN-disp ->r6"),
                           (0x55DD8, 0x37A4, "ld.bu ODD-disp  ->r6"),
                           (0x55E02, 0x36CA, "andi ->r6"), (0x55DFA, 0x3E80, "ori ->r7"),
                           (0x55DA6, 0x3107, "or r7,r6")):
        check(((u16(base, ref) >> 5) & 0x3F) == ((want >> 5) & 0x3F),
              f"opcode field of {lbl} matches a REAL instance at 0x{ref:05X} -- copied, not invented")

    # ---- the wire formula, simulated over the whole reachable domain -------------------------
    wire = lambda s, d: min(1023, max(0, 0x10 | (s & 0x0F) | ((d >> 3) << 5)))
    check(wire(max(sel), 240) == 985 and wire(15, 240) == 991 <= 1023,
          f"worst case: this car's max selector {max(sel)} + demand 240 -> wire {wire(max(sel),240)}; "
          f"even a hypothetical selector 15 gives {wire(15,240)} <= 1023, so the clamp NEVER acts "
          f"and nothing spills past bit 9 into byte0[1:0]")
    for s in LIVE:
        for d in range(0, 241):
            w = wire(s, d)
            check_sel, check_live, check_dem = w & 0x0F, (w >> 4) & 1, (w >> 5) * 8
            if (s, d) == (LIVE[-1], 240):
                check(check_sel == s and check_live == 1 and abs(check_dem - d) < 8,
                      f"round-trip over ALL {len(LIVE)}x241 (selector,demand) pairs: selector EXACT, "
                      f"beacon always 1, demand within one 8-count quantum")
            if not (check_sel == s and check_live == 1 and 0 <= d - check_dem < 8):
                raise SystemExit(f"pack round-trip FAILED at sel={s} demand={d}")
    print(f"      wire = 0x10 | (sel & 0x0F) | ((demand >> 3) << 5)   [0x1AB byte1 + byte0 bits1:0]")
    print(f"        bits 3:0 selector (max {max(sel)}, lossless)   bit 4 LIVENESS BEACON")
    print(f"        bits 9:5 demand/8 (0..240 in 30 steps of 8 = 3.3% quantisation)")
    check(bytes(base[0x29CFA:0x29CFC]) == bytes(base[0x2904E:0x29050]) == bytes.fromhex("8039"),
          "0x29CFA `subr r0,r7` (hw 0x3980 -- the SAME encoding as 0x2904E, which the index "
          "chain independently documents as subr r0,r7) takes the ABSOLUTE VALUE before the "
          "byte store at 0x29D14: no "
          "negative value can alias through st.b/ld.bu, and THE TAP IS A MAGNITUDE -- it cannot "
          "tell left from right.")
    check(bytes(base[0x29D12:0x29D14]) == bytes.fromhex("9600"),
          "0x29D12 `zxb r22` zero-extends before the store -- exact for 0..240")
    # STRONGER BOUND, adopted from the adversarial pass: derive the ceiling from the LOAD WIDTH
    # rather than from the 0xC64F0 clamp, so the field-safety proof does not depend on a cal.
    check((0x10 | max(sel) | ((255 >> 3) << 5)) == 1017 < 1024
          and (0x10 | 0x0F | ((255 >> 3) << 5)) == 1023 < 1024,
          "even if the demand cell held the FULL u8 range 0..255 -- ignoring the +-240 clamp "
          "entirely -- the packed value maxes at 1017 with this car's selector 9, and 1023 "
          "even with a hypothetical selector 15.  The field cannot spill past bit 9 "
          "for ANY byte value, so this proof survives a future change to 0xC64F0/F1.")
    check((0x10 | max(sel) | ((240 >> 3) << 5)) == 985,
          "and under the actual clamp of 240 it maxes at 985")
    check(240 >> 3 == 30 < 32,
          "demand>>3 in 0..30 fills bits 5-9 COMPLETELY -- ZERO spare bits.  Raising the "
          "0xC64F0/F1 clamp above 248 would overflow this pack SILENTLY.")
    print(f"      DECODE: wire = ((b0 & 3) << 8) | b1 ; sel = wire & 0xF ; live = (wire>>4)&1 ;")
    print(f"              demand = (wire >> 5) * 8      -- and `live` MUST read 1.")
    print(f"      WHY BOTH: the selector alone is STATIC -- written once at init, never changing")
    print(f"      while driving -- so it could not observe ANY of this build's levers.  The demand")
    print(f"      index is the taper's OUTPUT and the assist map's INPUT, and it is live at loop")
    print(f"      rate.  Paired with driver torque (0x18F b0:b1) it IS the taper curve, measured.")
    print(f"      (!) The selector names the SLOT, not the part number.  V277 sends the RAW nibble:")
    print(f"        selector 1 <- records 2/3/6/7, 6 <- records 10/12, 8 <- records 13/14.  (V276's")
    print(f"        wire was |sel|*5; those 5/30/40 numbers do NOT apply to this build.)  And a part")
    print(f"        number ABSENT from the table falls back to record 0, indistinguishable from a")
    print(f"        genuinely selector-0 car.")
    print(f"      DECODER: raw driver torque = wire * 128/125 = wire * 1.024 (0x18F is scaled 125/128).")
    print(f"      extract_r73.py:555 hard-codes a 427 threshold of 160 -- do NOT reuse that path.")

    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "cave byte-identical")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "hook byte-identical")

    print(f"\n  [3] [B] ASSIST MAP -- scaled {K}x, SHAPE PRESERVED, all {N_SLOTS} records")
    ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(all(START <= p < END for p in ptrs), f"all {len(ptrs)} map pointers in range")
    shapes = {}
    for p in ptrs:
        n = s16(base, p)
        check(n == MAP_N, f"map 0x{p:05X} npt == {MAP_N}")
        X, Y = rec(base, p, n)
        check(tuple(X) == MAP_X, f"map 0x{p:05X} X == stock (X is NOT touched)")
        ceil = K * Y[-1]                                   # 6x THIS record's own ceiling
        newY = tuple(K * y for y in Y)                     # HONDA'S SHAPE, scaled -- NOT linearised
        check(max(newY) <= 32767, f"map 0x{p:05X} scaled ceiling {max(newY)} fits int16")
        for i, y in enumerate(newY):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, y)
            attributed |= {o, o + 1}
        gY = rec(code, p, n)[1]
        check(tuple(gY) == newY, f"map 0x{p:05X} Y -> {K}x, ceiling {ceil}")
        check(all(gY[i] == K * Y[i] for i in range(n)),
              f"map 0x{p:05X} EXACTLY {K}x stock at every knot -- Honda's SHAPE is preserved, so "
              f"torque-vs-index is preserved when Kp is divided by {K}")
        _r = [gY[i] / Y[i] for i in range(n) if Y[i]]
        check(max(_r) == min(_r) == K, f"map 0x{p:05X} every knot scales by exactly {K}, no rounding")
        check(all(gY[i + 1] >= gY[i] for i in range(n - 1)), f"map 0x{p:05X} still monotone")
        shapes.setdefault((tuple(Y), newY), []).append(p)
    for (oldY, newY), ps in shapes.items():
        print(f"      {len(ps):2d} records  ceiling {oldY[-1]:4d} -> {newY[-1]:5d}   (Honda's shape, x{K})")
    check(all(tuple(rec(code, p, MAP_N)[0]) == MAP_X for p in ptrs), "every map X untouched")

    print("\n  [3b] [B] OVERRIDE TAPER -- THE CLIFF SOFTENED.  KICK-IN UNCHANGED.")

    check(bytes(code[IDX_SITE:IDX_SITE + 4]) == bytes.fromhex("a40fd197"),
          f"0x{IDX_SITE:05X} ld.bu -0x682f,gp,r1 (disp 0x97D1 = -0x682F) -- ZERO-EXTENDED BYTE")
    check(bytes(code[0x29068:0x2906C]) == bytes.fromhex("4447d197"),
          "0x29068 st.b r8,-0x682f,gp -- same cell, BYTE width")
    check(bytes(code[SAT_SITE:SAT_SITE + 4]) == bytes.fromhex("2086ff00"),
          f"0x{SAT_SITE:05X} movea 0xff,r0,r16 -- the explicit 255 saturate")
    check(bytes(code[SAR_TQ_SITE:SAR_TQ_SITE + 2]) == bytes.fromhex("a53a"),
          f"0x{SAR_TQ_SITE:05X} sar 0x5,r7 -- 1 X count == {TORQUE_PER_X} raw torque counts")
    check(X_CEIL == base[SAT_SITE + 2] == 255, "X_CEIL DERIVED from the image, not a free constant")
    check(bytes(code[0x290B8:0x290BC]) == bytes.fromhex("4407d197"),
          "0x290B8 `st.b r0,-0x682f,gp` -- the PLAUSIBILITY-FAIL path writes index ZERO = FULL "
          "AUTHORITY.  An implausible torque reading DISABLES the override rather than engaging "
          "it.  Stock, unchanged, and on the risk page because the taper is the last layer left.")
    for c_, v_ in sorted(DEAD_OVERRIDE_B.items()):
        check(code[c_] == v_, f"0x{c_:05X} == {v_} -- unsigned vs a <=255 index: DEAD")
    for c_, v_ in sorted(DEAD_OVERRIDE_H.items()):
        check(u16(code, c_) == v_, f"0x{c_:05X} == {v_} -- vs an operand clamped +-12800: DEAD")
    gr_n = s16(code, GRAB_RATE_REC)
    check((gr_n, [u16(code, GRAB_RATE_REC + 2 + 2 * gr_n + 2 * i) for i in range(gr_n)])
          == (4, [255, 255, 255, 255]),
          f"grab-rate 0x{GRAB_RATE_REC:05X} Y is FLAT 255 -- so the taper product is <= 255*255 = "
          f"65025 < 65536 and the `andi 0xffff` at 0x29CB8 is provably a NO-OP")

    # ---- enumerate, and edit ONLY the reachable cliff records --------------------------------
    edited, stock_kept, shapes = 0, 0, {}
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            p = u32(base, arr + 4 * s)
            check(START <= p < END, f"taper ptr 0x{arr:05X}[{s}] in range")
            n = s16(base, p)
            check(n == TAPER_N, f"taper 0x{p:05X} n == {TAPER_N}")
            X = tuple(u16(base, p + 2 + 2 * i) for i in range(n))
            Y = tuple(u16(base, p + 2 + 2 * n + 2 * i) for i in range(n))
            check(X in TAPER_SHAPES and TAPER_SHAPES[X] == Y,
                  f"taper 0x{p:05X} X={X} Y={Y} is a KNOWN stock shape")
            live = s in LIVE
            if live and arr in MODE2_BANKS:
                check((X, Y) == (A_OLD_X, A_OLD_Y),
                      f"0x{p:05X} slot {s}: every REACHABLE slot of a mode==2 bank carries the "
                      f"CLIFF shape {A_OLD_X}/{A_OLD_Y}")
                for i in range(n):
                    struct.pack_into("<H", code, p + 2 + 2 * i, A_NEW_X[i])
                    struct.pack_into("<H", code, p + 2 + 2 * n + 2 * i, A_NEW_Y[i])
                    attributed |= {p + 2 + 2 * i, p + 3 + 2 * i,
                                   p + 2 + 2 * n + 2 * i, p + 3 + 2 * n + 2 * i}
                gX = tuple(u16(code, p + 2 + 2 * i) for i in range(n))
                gY = tuple(u16(code, p + 2 + 2 * n + 2 * i) for i in range(n))
                check((gX, gY) == (A_NEW_X, A_NEW_Y), f"0x{p:05X} -> X{list(gX)} Y{list(gY)}")
                edited += 1
                shapes.setdefault((X, Y, gX, gY), []).append(p)
            else:
                check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]),
                      f"0x{p:05X} slot {s} bank 0x{arr:05X} BYTE-STOCK "
                      f"({'unreachable slot' if not live else 'already a linear fade'})")
                stock_kept += 1
    check(edited == 2 * len(LIVE) == 16,
          f"EXACTLY {edited} records edited -- the {len(LIVE)} reachable slots x the 2 mode==2 "
          f"banks.  Every other record of all four banks is byte-stock.")
    check(stock_kept == 4 * N_SLOTS - edited, f"{stock_kept} records left byte-stock")

    # ---- the new shape's own properties ------------------------------------------------------
    check(A_NEW_X[0] == A_OLD_X[0],
          f"KICK-IN UNCHANGED at X={A_NEW_X[0]} = raw {A_NEW_X[0]*TORQUE_PER_X} -- the operator "
          f"asked to soften the CLIFF, not to move the THRESHOLD")
    check(A_NEW_Y[0] == A_OLD_Y[0], f"and peak authority is unchanged at {A_NEW_Y[0]}")
    check(all(A_NEW_X[i] < A_NEW_X[i + 1] for i in range(3)), f"X strictly increasing {A_NEW_X}")
    check(all(A_NEW_Y[i] > A_NEW_Y[i + 1] for i in range(3)), f"Y strictly DECREASING {A_NEW_Y}")
    check(max(A_NEW_X) <= 255, "every knot reachable by the saturating byte index")
    _w = [A_NEW_X[i + 1] - A_NEW_X[i] for i in range(3)]
    _d = [A_NEW_Y[i] - A_NEW_Y[i + 1] for i in range(3)]
    check(_w == [14, 14, 14] and _d == [84, 85, 85],
          f"segment widths {_w} and drops {_d} are UNIFORM -- a near-straight fade, not a knee")
    check(A_NEW_X[-1] == 112,
          "zero lands at X=112 = raw 3584, EXACTLY where banks CB8B4/CB924 already reach zero, so "
          "all four banks now share ONE full-override threshold")
    check(max(A_NEW_Y) * 255 <= 65535, "Y*255 still fits the andi 0xffff -- no Y knot was raised")

    # ---- the delivered curve, from the BUILT image ------------------------------------------
    def taper_lerp(X, Y, x):
        if x <= X[0]:
            return Y[0]
        if x >= X[-1]:
            return Y[-1]
        for i in range(len(X) - 1):
            if X[i] <= x <= X[i + 1]:
                num, den = (Y[i + 1] - Y[i]) * (x - X[i]), X[i + 1] - X[i]
                # V850 `divq` truncates toward ZERO; Python `//` floors.  They differ on the
                # negative numerators a falling taper produces.
                return Y[i] + (int(num / den) if num % den else num // den)
        raise AssertionError

    LIVEREC = u32(base, MODE2_BANKS[0] + 4 * LIVE[0])
    lx0 = tuple(u16(base, LIVEREC + 2 + 2 * i) for i in range(4))
    ly0 = tuple(u16(base, LIVEREC + 2 + 8 + 2 * i) for i in range(4))
    lx1 = tuple(u16(code, LIVEREC + 2 + 2 * i) for i in range(4))
    ly1 = tuple(u16(code, LIVEREC + 2 + 8 + 2 * i) for i in range(4))
    print(f"\n      AUTHORITY vs DRIVER TORQUE -- record 0x{LIVEREC:05X}, opposing/mode==2, LIVE")
    print("         raw torque | idx |  V276 Y  |  V277 Y  |")
    for raw, tagm in ((2240, "kick-in, BOTH"), (2289, "r75 median push"),
                      (2560, "stock FULL override"), (2819, "pooled median override"),
                      (3082, "override p75"), (3306, "override p90"),
                      (3584, "V277 full override"), (4664, "override p99.9")):
        i = min(X_CEIL, raw >> 5)
        y0, y1 = taper_lerp(lx0, ly0, i), taper_lerp(lx1, ly1, i)
        print(f"        {raw:10d} | {i:3d} | {y0:5d} {100*y0//254:3d}% | {y1:5d} {100*y1//254:3d}% | {tagm}")
    check(taper_lerp(lx1, ly1, 70) == taper_lerp(lx0, ly0, 70) == 254,
          "at the kick-in itself the two curves AGREE -- the threshold really did not move")
    check(taper_lerp(lx0, ly0, 80) == 0 and taper_lerp(lx1, ly1, 80) == 194,
          "at raw 2560 stock is at ZERO authority and V277 is at 194/254 = 76% -- THE DROPOUT IS "
          "GONE and this is the single biggest change on the car")
    check(taper_lerp(lx1, ly1, 112) == 0,
          "FULL OVERRIDE IS STILL FULLY AVAILABLE, at raw 3584 -- reached in 1.6% of override "
          "time by the 34-route census, versus ~75% for stock's 2560")
    check(all(taper_lerp(lx1, ly1, i) >= taper_lerp(lx0, ly0, i) for i in range(256)),
          "V277 authority >= V276 at EVERY index 0..255 -- this build only RELAXES, never tightens")
    check(all(taper_lerp(lx1, ly1, i) >= taper_lerp(lx1, ly1, i + 1) for i in range(255)),
          "and the new curve is MONOTONE NON-INCREASING in driver torque -- more push is never "
          "rewarded with more assist")
    for (X, Y, gX, gY), ps in shapes.items():
        print(f"      {len(ps)} records  X {list(X)} -> {list(gX)}   Y {list(Y)} -> {list(gY)}")

    print(f"\n  [4] [C] FEEDBACK CLAMP 0xC62E6  {FB_STOCK} -> {FB_NEW}")
    struct.pack_into("<H", code, FB_CELL, FB_NEW)
    attributed |= {FB_CELL, FB_CELL + 1}
    check(u16(code, FB_CELL) == FB_NEW, f"feedback clamp == {FB_NEW}")
    check(FB_NEW < 65536, "fits u16")

    print("\n  [5] THE ARITHMETIC -- ALL 28 RECORDS x 241 INDICES, FROM THE BUILT IMAGE")
    print("      MODEL: FEEDBACK = 0 (the stall / step-response point).  Stated explicitly")
    print("      because an fb=0 model is what made V274's and V275's torque claims tautologies.")
    print("      It is the RIGHT model for a BOUND -- fb=0 maximises the forward error, so")
    print("      'peak bounded' and 'never less than V268' hold at EVERY fb -- but it is NOT")
    print("      a description of the car in motion.  What the loop does once the wheel moves")
    print("      is in the docstring's RISK paragraph, not in these assertions.")

    def lerp(X, Y, x):
        if x <= X[0]:
            return Y[0]
        if x >= X[-1]:
            return Y[-1]
        for i in range(len(X) - 1):
            if X[i] <= x <= X[i + 1]:
                return Y[i] + (Y[i + 1] - Y[i]) * (x - X[i]) // (X[i + 1] - X[i])
        raise AssertionError

    PC = u16(code, 0xC61BC)
    OC = u16(code, OUT_CELL)
    G = u16(code, GAIN_CELL)

    def surface(img, slot):
        mp = u32(base, MAP_PTR + 4 * slot)
        kp = u32(base, KP_PTR + 4 * slot)
        mX, mY = rec(img, mp, MAP_N)
        pX, pY = rec(img, kp, KP_N)
        out = []
        for idx in range(241):
            sp = lerp(mX, mY, idx)
            P = max(-PC, min(PC, (32 * sp * lerp(pX, pY, idx)) >> 8))
            out.append((sp, P, max(-OC, min(OC, (P * G) >> 15))))
        return out

    peaks, ratios, npts, peakmap = set(), [], 0, {}
    rslot, ridx, tq_new, sp_err = [], [], {}, [0]
    for s in range(N_SLOTS):
        a_, b_ = surface(base, s), surface(code, s)
        check(b_[240][0] == K * a_[240][0],
              f"slot {s}: setpoint ceiling {a_[240][0]} -> {b_[240][0]} = exactly {K}x")
        check(a_[240][2] <= b_[240][2] <= 2505,
              f"slot {s}: peak torque {a_[240][2]} -> {b_[240][2]}, capped by the FROZEN clamps at "
              f"2505 -- this is the fb=0 BOUND of the assist-map leg, NOT the delivered "
              f"ceiling.  The 0xC6CD0 forward-gain path's true clamp is 0xC61B4 = 3072 (6.000x "
              f"stock 512); 0xC61BC = 15360 sits on a different leg, after `sar 0x8`.")
        check(b_[240][2] / a_[240][2] <= 1.03,
              f"slot {s}: peak torque rises only {100*(b_[240][2]/a_[240][2]-1):.1f}% "
              f"(P reaches its clamp where V268 stopped at 97.4% of it)")
        peaks.add(a_[240][2]); peakmap[s] = a_[240][2]
        mp_ = u32(base, MAP_PTR + 4 * s)
        mXs, mYs = rec(base, mp_, MAP_N)
        for i in range(1, 241):
            tq_new[(s, i)] = b_[i][2]
            true6 = 6 * (lerp(mXs, [1000 * y for y in mYs], i) / 1000.0)
            sp_err.append(abs(b_[i][0] - true6))
            if a_[i][2] > 0:
                ratios.append(b_[i][2] / a_[i][2]); rslot.append(s); ridx.append(i)
                npts += 1
    check(min(ratios) >= 0.999, f"NO (slot,index) delivers LESS than V268 (min {min(ratios):.3f}x)")
    # Some low-index points exceed 6x. That is V268 QUANTISATION BEING REMOVED, not V276
    # overshooting: V268 floors a sub-unit setpoint to a coarse integer, V276 resolves it. Assert
    # the honest invariant -- V276 tracks 6x the UNQUANTISED setpoint -- instead of a false <=6x.
    over = [(r, s, i) for (r, s, i) in zip(ratios, rslot, ridx) if r > K + 0.01]
    check(all(i <= 40 for _, _, i in over),
          f"every >{K}x point is at demand index <= 40 ({len(over)} of {npts}) -- the micro regime "
          f"where V268's integer LERP floors the setpoint")
    worst_abs = max((tq_new[(s, i)] for _, s, i in over), default=0)
    check(worst_abs <= 2505, f"largest torque at any >{K}x point is {worst_abs}, still under the "
                             f"frozen fb=0 bound of 2505 -- no new authority, only finer resolution")
    check(max(sp_err) <= 1.0, f"V276 setpoint tracks {K}x the UNQUANTISED map everywhere "
                            f"(max deviation {max(sp_err)} counts = integer rounding)")
    from collections import Counter
    print(f"      V268 per-record peak torque: "
          f"{dict(sorted(Counter(peakmap.values()).items()))} (value -> #slots)")
    print(f"      V276 raises every slot to the same fb=0 bound 2505; the DELIVERED ceiling "
          f"of this path is 0xC61B4 = 3072, exactly 6.000x stock 512, knee unmoved.")
    print(f"      torque ratio V276/V268 across {npts} (slot,index) points: "
          f"min {min(ratios):.2f}x  max {max(ratios):.2f}x")

    s0, s1 = surface(base, 1), surface(code, 1)
    print("\n        idx |  V268: sp     P  torque |  V276: sp     P  torque")
    for idx in (12, 24, 48, 96, 160, 240):
        print(f"      {idx:5d} | {s0[idx][0]:8d} {s0[idx][1]:6d} {s0[idx][2]:6d}  |"
              f" {s1[idx][0]:8d} {s1[idx][1]:6d} {s1[idx][2]:6d}")

    r0 = FB_STOCK / (32 * s0[240][0])
    r1 = FB_NEW / (32 * s1[240][0])
    print(f"\n      feedback clamp {FB_STOCK} -> {FB_NEW};  setpoint:feedback ratio "
          f"{r0:.3f} -> {r1:.3f}")
    check(FB_NEW == FB_STOCK * K and u16(code, FB_CELL) == FB_STOCK * K,
          f"feedback clamp is EXACTLY {FB_STOCK} * {K} = {FB_STOCK*K}, asserted as an exact integer "
          f"-- the ratio check below has ~+-30 counts of slack and cannot gate this alone")
    check(abs(r1 - r0) < 0.001, "Honda's setpoint:feedback ratio preserved EXACTLY (both scaled 6x)")

    print("\n  [6] TORQUE PATH RE-ASSERTED ON THE BUILT IMAGE")
    for a, v in FROZEN.items():
        check(u16(code, a) == v, f"0x{a:05X} still {v}")
    check(code[SAR_R26] == SAR_1X and code[SAR_R24] == SAR_1X, "rate lane still stock 1x")
    check(code[IDX_CLAMP_P] == 240 and code[IDX_CLAMP_N] == 240, "index clamp still +-240")
    for nm, ptr, npt in (("Kp", KP_PTR, KP_N), ("Kd", KD_PTR, KD_N)):
        for s in range(N_SLOTS):
            p = u32(base, ptr + 4 * s)
            n = s16(base, p)
            check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]),
                  f"{nm} slot {s} BYTE-IDENTICAL -- Kp/Kd are NOT retuned in this build")
    check(u16(code, GAIN_CELL) == GAIN_V268, f"0xC6CD0 still {GAIN_V268}")
    check(u16(code, OUT_CELL) == OUT_V268, f"0xC61B4 still {OUT_V268}")

    print("\n  [7] CRC TRAILERS")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    for b0, b1 in blocks:
        check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit on trailer 0x{b1:06X}")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")

    print("\n  [8] FULL BYTE DIFF vs V268")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(not [x for x in diff if x not in attributed], f"all {len(diff)} differing bytes attributed")
    pay = [x for x in diff if (x & 0xFFF) < 0xFFC]
    allow = set(range(PACK_LO, PACK_HI)) | {FB_CELL, FB_CELL + 1}
    for p in ptrs:
        allow |= {p + 2 + 2 * MAP_N + k for k in range(2 * MAP_N)}
    for arr_ in MODE2_BANKS:
        for s_ in LIVE:
            p_ = u32(base, arr_ + 4 * s_)
            allow |= {p_ + 2 + k for k in range(4 * TAPER_N)}
    check(set(pay) <= allow, "every payload byte is a MAP Y knot, a TAPER X knot, the feedback "
                             "clamp, or inside the 34-byte packer window -- no map X, no UNREACHABLE taper "
                             "no cave, no gain, no output clamp, no unintended cell")
    cb = sorted(x for x in pay if x < 0xC0000)
    check(set(cb) <= set(range(PACK_LO, PACK_HI)),
          f"every moved code byte is inside the 34-byte packer window "
          f"[0x{PACK_LO:05X},0x{PACK_HI:05X}) -- {len(cb)} bytes, no code moves anywhere else")
    check(all(0x55D80 <= x <= 0x55F2D for x in cb),
          "every moved code byte lies inside the packer body 0x55D80-0x55F2D -- nothing near the "
          "control path, no cave, no hook")
    check(bytes(code[0x28EA6:0x2A30D]) == bytes(base[0x28EA6:0x2A30D]),
          "FUN_00028ea6 itself is byte-identical -- every edit is a CALIBRATION, not code")
    print(f"      {len(pay)} payload bytes, {len(cb)} code, {len(blocks)} CRC trailers")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V277 output")
    # [!] FAIL-CLOSED.  This was `... if hasattr(FF,"V38_PLAIN") else True`, which an audit proved
    # would pass 2194/2194 while PRINTING "cipher table validated NON-circularly" if FF were ever
    # refactored and the attribute renamed.  The kit's ONLY non-circular cipher test must not fail
    # open, so the guard is asserted separately and the check now defaults to FALSE.
    _CIPHER_GUARD = hasattr(FF, "V38_PLAIN")
    check(_CIPHER_GUARD, "FF.V38_PLAIN EXISTS -- the non-circular cipher test is actually ARMED "
                         "(the encode/decode round-trip is an identity for ANY bijective table "
                         "and proves nothing; only decoding the known V38 .rwd tests the table)")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49 (predicts flash NRC 0x72)")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest()
          if _CIPHER_GUARD else False,
          "cipher table validated NON-circularly against the known V38 plain image")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v277_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V277_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
