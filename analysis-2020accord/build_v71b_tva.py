#!/usr/bin/env python3
"""build_v71b_tva.py -- V71B = V71A's SIBLING: dose r26 ALONE, SPEED-SHAPED, stock at highway.

    V71B  ==  V70  +  0x454FE  +  gain_A rec0/rec1 Y[0..3] DOUBLED  +  gain_B surface -> STOCK
              and BOTH `sar` sites LEFT STOCK.

WHY IT EXISTS -- the highway trade V71A cannot avoid
------------------------------------------------------
V71A doses both lanes through two `sar` immediates. A shift is speed-INDEPENDENT, so V71A is a FLAT
2.000000x at every speed -- including highway, where V70 was EXACTLY 1.000000x and the operator
reported it clean, and where a flat 2.00x is the configuration on record as having caused grind #2.
V71B buys that back: `gain_A` is a **4-record x 4-point surface on the SAME speed cross-axis as
`gain_B`**, so doubling rec0 and rec1 gives 2.000000x at and below 10 km/h tapering to EXACTLY
1.000000x at and above 50 km/h -- V69/V70's proven structural guarantee, applied to the lane that
matters.

★ AND IT IS SINGLE-VARIABLE ON r26. The corpus contains a clean r24 dose series -- stock -> V70 ->
V69 is r24 x1 -> x2 -> x4 with r26 held at x1 -- and grind #1 reads **879 -> 729 -> 746**, all three
CIs mutually overlapping ⇒ r24 is close to INERT for grind #1 across a 4:1 range. Both builds that
DID fix grind #1 changed r26 (V62 x2, V67/V68 /6.00). V71B moves r26 and NOTHING else.

🛑 A CORRECTION TO THIS BUILD'S OWN RATIONALE -- `gain_A` HAS BEEN EDITED BEFORE, AND IT FAILED
------------------------------------------------------------------------------------------------
An earlier framing of V71B called `gain_A` untouched. **It is not. V42 ZEROED IT** -- byte-verified
across the images by this builder's own gate:

    stock / V38 / V59 / V62 / V70   rec0 [3072,3072,2434,2048]  rec1 [3072,3072,2488,1536]
                                    rec2 [2664,2664,2243,1436]  rec3 [2560,2560,2145,1331]
                                    0xC6444 = 512    0xC643E = 1536
    V42                             rec0/rec1/rec2/rec3 ALL [0,0,0,0]
                                    0xC6444 = 0      0xC643E = 0

V42 zeroed **all four records and both override arms** ⇒ r26 identically 0 in every state -- and it
was **FALSIFIED on-car ("no effect")**. ⚠ Weak evidence about grind #1 *specifically*: V42 predates
the `e_18-22` harness and was aimed at the vibration, not the grind. But it is a real prior.

⇒ **THE CLAIM, STATED CORRECTLY: V71B is the first UPWARD test of `gain_A`, not the first test.**
That is exactly the distinction the V61 -> V62 correction turned on: V39, V42 and V61 all pushed the
rate lane DOWN and were null-or-worse; V62 pushed it UP and it worked. "Tested downward" is not
"tested". That precedent is what makes this upward test worth running.

⚠ AND THE TENSION, RECORDED RATHER THAN SMOOTHED. No single-lane story fits all five points:
    r26 -> 0 alone           did NOTHING          (V42, falsified)
    r24 up alone             does NOTHING         (V70 729 / V69 746 vs stock 879)
    BOTH up together         the only measured fix (V62, 168)
V71B tests **half of V62's change**. It is therefore the cleaner EXPERIMENT -- single-variable, no
highway cost, the first upward `gain_A` test -- and **not** the higher-probability fix. The
orchestrator's recommendation has moved to **V71A** on exactly this basis. Read V71B that way.

THE STRUCTURE -- CONFIRMED FROM THE DECOMPILATION, not from the bytes upward
----------------------------------------------------------------------------
`FUN_0003ad74` has two halves. Both walk the SAME 4-entry speed cross-axis at `tp+0x7010` =
**0xC6010** = [0, 640, 3200, 6400] counts = [0, 10, 50, 100] km/h, and both LERP a 4-record set into
a RAM X/Y pair:

  HALF 1 -> gp-0x6e40 (X) / gp-0x6e38 (Y)   gain_B, r24's default arm.  🛑 MODE-INDEXED:
      `iVar10 = (byte)(gp+0x63fd) * 4` then four ROM pointer arrays 0xCBF5C / 0xCC044 / 0xCC12C /
      `tp+0xd214` (= 0xCC214). That is why V62 refused to edit r24's gain by calibration.
  HALF 2 -> gp-0x6e30 (X) / gp-0x6e28 (Y)   gain_A, r26's default arm.  ★ **NOT MODE-INDEXED**:
      the four record pointers are HARDCODED IMMEDIATES in the decompilation --
          aiStack_14[1] = tp + 0x7a68;   aiStack_14[2] = tp + 0x7a7c;
          aiStack_14[3] = tp + 0x7a90;   psStack_4     = tp + 0x7aa4;
      i.e. 0xC6A68 / 0xC6A7C / 0xC6A90 / 0xC6AA4, emitted as four `movea 0x7a__,tp,rN` at
      0x3AECC / 0x3AED4 / 0x3AED8 / 0x3AEE0. A raw byte scan finds NO other tp-relative pointer
      formation for any of the four (the single extra hit, 0x40894, is not on an instruction
      boundary -- 0x40892 is a 4-byte `ld.bu`). ⇒ **exactly ONE consumer, and no mode to get wrong.**
  Record layout, read straight off the decompiled indices: count @+0x00, X[j] @+0x02 (`psVar11[j+1]`),
  Y[j] @+0x0A (`psVar11[j+5]`), stride 0x14.
  Selection: index <= cross[0] -> rec0 copied; index >= cross[3] -> rec3 copied; otherwise LERP
  between the bracketing pair. ⇒ **at >= 3200 counts only rec2/rec3 are read**, which is the whole
  structural guarantee, and it is asserted by sweep below rather than argued.
  The cross-axis INPUT is shared too: `gp-0x6a5e` when `gp-0x67f4 == 1`, else cal `tp+0x7314`.

THE r26 LANE, instruction for instruction (0x3AB3A-0x3AB76, stock)
-------------------------------------------------------------------
    0x3AB3A  ld.hu -0x69a4[gp],r6     ; UNSIGNED halfword ⇒ structurally 0..65535
    0x3AB4A  ld.hu -0x3672[gp],r10    ; the previous sample
    0x3AB4E  st.h  r6,-0x3672[gp]     ; store current as previous
    0x3AB52  add   r10,r6             ; cur + prev
    0x3AB54  shr   0x1,r6             ; avg = (cur + prev) >> 1     <- the "avg" of the record
    0x3AB5E  ld.hu 0x7444[tp],r8      ; arm 0xC6444 = 512   (gate gp-0x683c: 0 writers ⇒ DEAD)
    0x3AB68  ld.hu 0x743e[tp],r8      ; arm 0xC643E = 1536  (state < CEIL)
             else  r8 = the gain_A LERP                      <- **V71B's EDIT**
    0x3AB6C  mul   r1,r6,r0           ; dtorque * avg
    0x3AB70  sar   0xa,r6             ; stage1 = >> 10        🛑 LEFT STOCK
    0x3AB72  mul   r8,r6,r0           ; stage1 * gain_A       <- the multiply V62 protected
    0x3AB76  sar   0xa,r6             ; pre    = >> 10        🛑 LEFT STOCK (V71A makes this 0x9)
    then polarity, then clamp +/-0x2000.
`r1` is the shared dtorque, clamped to **+/-0x1400 = +/-5120** at 0x3AAB2 / 0x3AABC -- byte-verified
here, not quoted.

🛑🛑 THE ONE NUMBER THAT DECIDES BETWEEN V71A AND V71B
--------------------------------------------------------
V71A and V71B deliver the **SAME r26 magnitude** at creep -- `sar 0x9` after the multiply and a
doubled `gain_A` before it produce the identical `pre`. So their **+/-8192 clamp behaviour is
IDENTICAL**: both rail at `|dtorque| = 8192 * 2^20 / (avg * 6144) = 1,398,101 / avg`, crossing the
repo-recorded max |dtorque| of 839 at **avg ~= 1666**. If `avg` is a Q10 scale around unity (1024)
the rail is **1365**, exactly V71A's r24 rail. **avg ~= 1666 is only 1.63x unity, so the crossing IS
plausible in normal driving** -- but a clamp crossing is a SATURATION, not a wrap: it costs the lead
term describing-function gain, it cannot produce garbage, and V71A crosses at the same point.

**The difference is INT32 HEADROOM AT `mul` 0x3AB72, and it is where V71B is worse:**
    structural worst case  =  ((5120 * 65535) >> 10) * gain_A  =  327,675 * gain_A
        gain_A = 3072 (stock, V71A)  ->  1.007e9  =  **46.9% of INT32_MAX**
        gain_A = 6144 (V71B)         ->  2.013e9  =  **93.75% of INT32_MAX**
V850 `mul` discards the high word into r0, so an overflow is a SILENT truncation with a possible
sign flip. **No overflow is reachable** -- `ld.hu` bounds `avg` at 65535 and 93.75% < 100% -- but the
headroom halves, and **V62's own build note rejected editing `0x3AB70` at exactly this 94% / 6%
margin, by exactly this method, on exactly this multiply.** V71A's `sar` leaves both multiply
operands at stock magnitude; that is precisely why V62 chose it.
⇒ **[EVIDENCE] identical clamp behaviour; [EVIDENCE] V71B has half the INT32 headroom.**
⇒ **[BELIEF] V71A is the arithmetically safer of the two; V71B is the better-targeted one.** The
   trade is real and it is the operator's to make.

★ THE PROBE WATCHES THE LANE THIS BUILD DOSES
-----------------------------------------------
bit4/bit3 read **`gp-0x6adc` -- r26's OWN post-clip mirror** (`st.h r26,-0x6adc,gp` @0x3AD4E, **0
readers / 1 writer** image-wide, and flight-proven: V70's probe already read this cell). V71A doses
both lanes and watches r24's mirror; V71B doses r26 alone and watches r26's. **A build must
instrument the lane it moves** -- pointing V71B's positive control at r24 would have dosed one lane
and measured the other, which is precisely the failure that ran for four builds.
bit6 (`gp-0x671d`) and bit5 (`gp-0x67fa == 4`) are lane-independent and unchanged.

⚠ TWO CONSEQUENCES, STATED UP FRONT
1. **THE TWO CAVES DIFFER IN EXACTLY ONE BYTE** -- cave+0x1A, `0x26` -> `0x24` -- and **that byte is
   not visible on the wire.** V71A and V71B are still NOT distinguishable from the CAN payload; the
   **.rwd FILENAME is the only pre-drive discriminator**. Their plain images are separate files and
   neither builder will overwrite the other's. `decode_v71_probe.py` now **REFUSES to run without
   `--v71a` or `--v71b`** rather than guess which bit map to apply.
2. **A CROSS-BUILD COMPARISON OF bit4 OR bit3 IS NOT LIKE-FOR-LIKE.** They measure different lanes on
   different scales: r26 carries an extra `avg(gp-0x69a4)` factor that r24 does not. Compare each
   build's bit4 against ITS OWN prediction, never against the sibling's reading.

Usage:  python build_v71b_tva.py
"""
import hashlib
import os
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v69_tva as V69                # noqa: E402
import build_v71a_tva as A                 # noqa: E402  -- the cave, the gates, the ratchet edit
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = A.START, A.END
CAVE_BASE, CAVE_EXTENT = A.CAVE_BASE, A.CAVE_EXTENT

# ---- EDIT 2: the gain_A surface -- rec0 and rec1, ALL FOUR Y points ----------------------------
# 🛑 ALL FOUR, not Y[0..1]. V69/V70 doubled only the first two points of gain_B's records, which
# left the dose falling away along the RATE axis exactly where grind #2 lives (rateKey >= 1126).
# There is no reason to repeat that here: the speed shaping comes from WHICH RECORDS are edited,
# not from which points within them.
RATE_A_RECORDS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)
RATE_A_X_STOCK = ((0, 400, 1600, 3000), (0, 250, 1200, 3000),
                  (0, 400, 1250, 3000), (0, 400, 1250, 3000))
RATE_A_Y_STOCK = ((3072, 3072, 2434, 2048), (3072, 3072, 2488, 1536),
                  (2664, 2664, 2243, 1436), (2560, 2560, 2145, 1331))
EDITED_RECS = (0xC6A68, 0xC6A7C)          # 0 and 10 km/h
UNTOUCHED_A_RECS = (0xC6A90, 0xC6AA4)     # 50 and 100 km/h -- the structural highway 1.000x
Y_OFFSET, X_OFFSET, REC_STRIDE = 0x0A, 0x02, 0x14
SCALE = 2

CROSS_X_ADDR = V69.CROSS_X_ADDR            # 0xC6010 -- SHARED with gain_B, confirmed in the decompile
HIGHWAY_COUNTS = 3200                      # the cross-axis breakpoint above which only rec2/rec3 read
RECORD_PTR_SITES = (0x3AECC, 0x3AED4, 0x3AED8, 0x3AEE0)   # the four `movea 0x7a__,tp,rN`

# ---- the r26 lane's arithmetic, byte-anchored --------------------------------------------------
DTORQUE_CLAMP = 0x1400                     # +/-5120, from `movea +/-0x1400,r0,r1` @0x3AAB2/0x3AABC
CLAMP_SITES = ((0x3AAB2, bytes.fromhex("200e0014")), (0x3AABC, bytes.fromhex("200e00ec")))
AVG_MAX = 0xFFFF                           # `ld.hu -0x69a4[gp],r6` @0x3AB3A ⇒ unsigned halfword
LANE_CLIP = 0x2000                         # the r26 output clamp
SAR1, SAR2 = 10, 10                        # 🛑 BOTH LEFT STOCK on V71B
R26_ARMS = ((0xC6444, 512, "gate gp-0x683c -- DEAD, 0 writers image-wide"),
            (0xC643E, 1536, "state < CEIL"))
RECORDED_DTORQUE_MAX = 839

CAL_BLOCK = (0xC6000, 0xC6FFC)

# 🛑 THE PROBE WATCHES THE LANE THIS BUILD DOSES. V71A doses both lanes and watches r24's mirror;
# V71B doses r26 ALONE, so it watches r26's. One cave byte apart (cave+0x1A, 0x26 -> 0x24).
MIRROR = A.R26_MIRROR_DISP                 # 0x6ADC -- st.h r26 @0x3AD4E, 0 readers / 1 writer

TAG = ("LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-gainA-rec0rec1-x2-SPEEDSHAPED-"
       "sarSTOCK-probe2-671d-67fa4-6adcABS128-sign-can330byte4")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V71B-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v71b_plain_image.bin"))
SRC_BIN = plain_image_path("_v70_plain_image.bin")
STOCK_BIN = stock_fw_path("code.bin")
V71A_BIN = plain_image_path("_v71a_plain_image.bin")
DECODER = os.path.join(HERE, "..", "rlog-tools", "decode_v71_probe.py")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def rec_a(buf, addr):
    """gain_A record -> (X[4], Y[4]). SIGNED: FUN_0003ad74 reads them through `short *`."""
    return (list(struct.unpack_from("<4h", buf, addr + X_OFFSET)),
            list(struct.unpack_from("<4h", buf, addr + Y_OFFSET)))


def gain_a_q10(buf, speed_counts, axis_counts):
    """The gain_A surface, mirroring FUN_0003ad74's SECOND half + the LERP at 0x3AAD0-0x3AB2A.

    Structurally identical to V69.gain_q10 (gain_B) -- same cross-axis, same record layout, same
    truncating `divq` -- with the record set swapped for the four HARDCODED gain_A pointers.
    """
    recs = [rec_a(buf, a) for a in RATE_A_RECORDS]
    cross = list(struct.unpack_from("<4h", buf, CROSS_X_ADDR))
    k = max(cross[0], min(speed_counts, cross[-1]))
    xs = [V69._lerp(k, cross, [recs[i][0][j] for i in range(4)]) for j in range(4)]
    ys = [V69._lerp(k, cross, [recs[i][1][j] for i in range(4)]) for j in range(4)]
    idx = axis_counts if 0 <= axis_counts < 13001 else 0
    return V69._lerp(idx, xs, ys)


def r26_rail(avg, gain_a, sar1=SAR1, sar2=SAR2):
    """|dtorque| at which r26's output reaches its +/-0x2000 clip, as a function of `avg`."""
    if avg <= 0 or gain_a <= 0:
        return float("inf")
    return LANE_CLIP * (1 << (sar1 + sar2)) / (avg * gain_a)


def int32_worst(gain_a, sar1=SAR1):
    """The worst-case product at `mul r8,r6,r0` @0x3AB72, using the STRUCTURAL bounds only."""
    stage1 = (DTORQUE_CLAMP * AVG_MAX) >> sar1
    return stage1 * gain_a


def assert_gain_a(buf, label, doubled):
    """Every gain_A record, by exact value. X rows, counts and terminators never move."""
    for i, base in enumerate(RATE_A_RECORDS):
        want_y = [y * SCALE for y in RATE_A_Y_STOCK[i]] if (doubled and base in EDITED_RECS) \
            else list(RATE_A_Y_STOCK[i])
        got_x, got_y = rec_a(buf, base)
        assert got_x == list(RATE_A_X_STOCK[i]), \
            f"{label}: gain_A 0x{base:05X} X row is {got_x}, expected {list(RATE_A_X_STOCK[i])}"
        assert got_y == want_y, f"{label}: gain_A 0x{base:05X} Y row is {got_y}, expected {want_y}"
        assert u16(buf, base) == 4, f"{label}: gain_A 0x{base:05X} count moved"
        assert u16(buf, base + 0x12) == 0, f"{label}: gain_A 0x{base:05X} terminator moved"
        for y in got_y:
            assert 0 < y < 0x8000, \
                f"{label}: gain_A 0x{base:05X} Y = {y} is not a positive SIGNED halfword -- " \
                "FUN_0003ad74 reads these through `short *` and the lane would INVERT"


def assert_decoder_matches(cave_bytes):
    """The shared decoder must match this cave too, and must name BOTH siblings."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX_B\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m and m.group(1) == cave_bytes.hex(), "V71B: the decoder's CAVE_HEX_B is STALE"
    assert "V71B" in txt, \
        "V71B: the decoder does not mention V71B -- it carries a byte-identical cave and the reader " \
        "MUST be told the wire cannot tell the two apart"
    assert os.path.basename(OUT) in txt, "V71B: the decoder does not carry V71B's .rwd basename"
    assert re.search(r'"v71b": dict\(cave=CAVE_HEX_B, lane="r26", cell=0x6ADC', txt),         "V71B: the decoder's v71b entry does not watch gp-0x6adc -- it would misread every frame"
    assert re.search(r'"v71a": dict\(cave=CAVE_HEX_A, lane="r24", cell=0x6ADA', txt),         "V71B: the decoder's v71a entry drifted"
    assert "NOT LIKE-FOR-LIKE" in txt.upper(),         "V71B: the decoder does not warn that a cross-build bit4/bit3 comparison is not like-for-like"
    return True


def build():
    print(__doc__)
    src = Path(SRC_BIN)
    v70 = bytearray(src.read_bytes())
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V70): {src}\n  SHA256 {hashlib.sha256(bytes(v70)).hexdigest()}")

    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    assert Path(BIN_OUT).name != Path(A.BIN_OUT).name, \
        "V71B would overwrite V71A's plain image -- the recorded same-number hazard"

    # ---- gate the SOURCE ------------------------------------------------------------------------
    assert len(v70) == len(stock) == 0x100000
    A.assert_ratchet_edit(v70, "V70 source", expect_edited=False)
    A.assert_sar_sites(v70, "V70 source", expect_doubled=False)
    A.assert_no_external_entry(v70)
    assert_gain_a(v70, "V70 source", doubled=False)
    assert_gain_a(stock, "stock", doubled=False)
    for addr, raw in CLAMP_SITES:
        assert bytes(stock[addr:addr + 4]) == raw and bytes(v70[addr:addr + 4]) == raw, \
            f"the dtorque clamp @0x{addr:05X} is not {raw.hex()} -- the saturation model is anchored " \
            "on it and would be quoting a number the image no longer carries"
    for lo, hi, what in A.STOCK_IDENTICAL_SPANS:
        assert not [i for i in range(lo, hi) if v70[i] != stock[i]], \
            f"[0x{lo:05X},0x{hi:05X}) ({what}) differs from stock"
    assert list(struct.unpack_from("<4h", stock, CROSS_X_ADDR)) == [0, 640, 3200, 6400], \
        "the shared speed cross-axis at 0xC6010 is not [0,640,3200,6400]"
    print(f"  ⭐ cross-axis 0xC6010 = {list(struct.unpack_from('<4h', stock, CROSS_X_ADDR))} counts "
          "= [0, 10, 50, 100] km/h -- SHARED by gain_A and gain_B (confirmed in the decompile)")
    print(f"  ⭐ dtorque clamp +/-{DTORQUE_CLAMP} byte-verified at "
          f"{', '.join(f'0x{a:05X}' for a, _ in CLAMP_SITES)}")

    code = bytearray(v70)

    # ---- EDIT 1 -- the ratchet fix (identical to V71A) -------------------------------------------
    print("\n  EDIT 1 -- THE RATCHET FIX, identical to V71A:")
    struct.pack_into("<H", code, A.RATCHET_ADDR, A.RATCHET_NEW_HW)
    A.assert_ratchet_edit(code, "V71B", expect_edited=True)
    A.assert_no_external_entry(code)
    n_state = A.assert_governor_monitor_safety(code, "V71B")
    print(f"    0x{A.RATCHET_ADDR:05X}  0x{A.RATCHET_STOCK_HW:04X} -> 0x{A.RATCHET_NEW_HW:04X}   "
          f"bne 0x455C4 -> br 0x455C4; FUN_0004595a safety re-derived ({n_state} state read)")

    # ---- EDIT 2 -- gain_A rec0/rec1, ALL FOUR Y points, doubled ---------------------------------
    print("\n  EDIT 2 -- gain_A rec0/rec1, ALL FOUR Y points DOUBLED (r26's default arm):")
    for i, base in enumerate(RATE_A_RECORDS):
        if base not in EDITED_RECS:
            continue
        old = list(RATE_A_Y_STOCK[i])
        new = [y * SCALE for y in old]
        struct.pack_into("<4h", code, base + Y_OFFSET, *new)
        print(f"    0x{base + Y_OFFSET:05X}  {old} -> {new}   record 0x{base:05X} "
              f"({'0' if base == RATE_A_RECORDS[0] else '10'} km/h)")
    assert_gain_a(code, "V71B", doubled=True)
    for base in UNTOUCHED_A_RECS:
        assert bytes(code[base:base + REC_STRIDE]) == bytes(stock[base:base + REC_STRIDE]), \
            f"gain_A 0x{base:05X} (50/100 km/h) is not byte-identical to STOCK"
    print(f"    ✅ gain_A rec2/rec3 (0x{UNTOUCHED_A_RECS[0]:05X}/0x{UNTOUCHED_A_RECS[1]:05X}) "
          "byte-identical to STOCK ⇒ the highway 1.000000x is STRUCTURAL")

    # ---- EDIT 3 -- V70's gain_B surface reverted to stock ---------------------------------------
    print("\n  EDIT 3 -- V70's gain_B surface dose REVERTED to stock (r24 goes fully stock):")
    for addr, old, new, name in A.SURFACE:
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {old:5d} -> {new:5d}   {name}")
    for base, ys in A.REC_Y_STOCK.items():
        assert bytes(code[base:base + REC_STRIDE]) == bytes(stock[base:base + REC_STRIDE]), \
            f"mode-10 gain_B record 0x{base:05X} is not byte-identical to STOCK"
    A.assert_sar_sites(code, "V71B", expect_doubled=False)
    print("    ✅ all four mode-10 gain_B records byte-identical to STOCK, and BOTH `sar` sites left")
    print(f"       STOCK (0x{A.R26_SAR:05X} and 0x{A.R24_SAR:05X} = 0x32AA / 0x42AA) ⇒ r24 is FULLY")
    print("       STOCK on V71B. This build moves r26 and NOTHING else.")
    for addr, want, what in R26_ARMS:
        assert u16(code, addr) == want, f"r26 arm 0x{addr:05X} moved ({what})"
    print(f"    ✅ r26's two override arms untouched: "
          + ", ".join(f"0x{a:05X} = {v}" for a, v, _ in R26_ARMS))

    # ---- EDIT 4 -- the probe, byte-identical to V71A's ------------------------------------------
    print("\n  EDIT 4 -- THE PROBE, RETARGETED TO r26 (68 of 68 bytes, ZERO spare):")
    cave_bytes, cave_listing = A.build_cave(MIRROR)
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    nr, nw = A.assert_probe_census(bytes(code), cave_span, MIRROR)
    print(f"    ✅ GATE 1 re-measured from raw bytes: gp-0x67fa {nr}r/{nw}w, read-only by the cave; "
          "the sole store is the CAN-330 payload byte")
    print(f"    ✅ bit4/bit3 watch gp-0x{MIRROR:04X} = r26's OWN post-clip mirror (st.h @0x3AD4E,")
    print("       0 readers / 1 writer image-wide, and FLIGHT-PROVEN: V70's probe already read it).")
    print("       V71B doses r26, so V71B instruments r26. A build must watch the lane it moves.")
    print("    🛑 THE TWO CAVES DIFFER IN EXACTLY ONE BYTE (cave+0x1A: 0x26 -> 0x24), which is NOT")
    print("       visible on the wire. The .rwd FILENAME is still the only pre-drive discriminator,")
    print("       and a cross-build comparison of bit4/bit3 is NOT like-for-like: different lanes,")
    print("       different scales (r26 carries the extra avg(gp-0x69a4) factor).")
    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/decode_v71_probe.py matches this cave and names BOTH siblings")

    # ---- THE DOSE, PROVEN BY SWEEP ---------------------------------------------------------------
    print("\n  THE DOSE -- gain_A, over the full speed x rate grid:")
    grid = [(v, r) for v in range(0, 6401, 32) for r in range(0, 3001, 25)]
    mults = [gain_a_q10(code, v, r) / gain_a_q10(stock, v, r) for v, r in grid]
    mx, mn = max(mults), min(mults)
    print("      km/h  " + "".join(f"{k:>8}" for k in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 93)))
    row = [gain_a_q10(code, int(k * 64.0625), 100) / gain_a_q10(stock, int(k * 64.0625), 100)
           for k in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 93)]
    print("      mult  " + "".join(f"{x:8.3f}" for x in row))
    print(f"    ✅ over {len(grid)} operating points: MAX {mx:.9f}x, MIN {mn:.9f}x")
    # 🛑 CLAIM WHAT IS TRUE. The brief asked for "MAX = 2.000000 and MIN = 1.000000". MIN holds
    # EXACTLY. MAX does NOT, by 0.029%, and the reason is arithmetic, not a shaping error: the
    # RATE-axis LERP truncates (`divq` toward zero) in BOTH the doubled and the stock evaluation, so
    # the ratio of two truncated interpolants is not exactly 2 between the record's own X knots.
    # V69/V70 never saw this because they doubled only Y[0] and Y[1], which are EQUAL, so their
    # edited segment was FLAT and truncation-free. Doubling all four points is the right call --
    # grind #2 lives at rateKey >= 1126, where a Y[0..1]-only edit has already decayed -- and this
    # is its stated cost. A gate that asserted "exactly 2.000000" here could not fail honestly.
    assert mn == 1.0, f"the surface dips to {mn}x -- NO point may fall below stock"
    assert mx <= SCALE * 1.001, f"the surface peaks at {mx}x, more than 0.1% above {SCALE}x"
    n_over = sum(1 for x in mults if x > SCALE)
    print(f"    ✅ MIN is EXACTLY 1.000000000 -- not one of {len(grid)} points falls below stock")
    print(f"    ⚠ MAX is {mx:.9f}, not exactly 2: {n_over} points exceed 2x by at most "
          f"{(mx / SCALE - 1) * 100:.4f}% (`divq` truncation in the RATE-axis LERP, see the comment)")
    bad = [(v, r) for v, r in grid if v >= HIGHWAY_COUNTS
           and gain_a_q10(code, v, r) != gain_a_q10(stock, v, r)]
    assert not bad, f"a >= 50 km/h operating point moved: {bad[:4]}"
    n_hw = sum(1 for v, r in grid if v >= HIGHWAY_COUNTS)
    print(f"    ✅ all {n_hw} points at >= {HIGHWAY_COUNTS} counts (>= 50 km/h) are BYTE-IDENTICAL to")
    print("       stock ⇒ EXACTLY 1.000000x at highway, EVERY rate. ⇐ THE OPERATOR'S COMPLAINT.")
    # ---- where it IS exact: the FLAT low-rate segment, at both edited records' own breakpoints ---
    flat = min(RATE_A_X_STOCK[0][1], RATE_A_X_STOCK[1][1])          # 250 counts -- both Y[0]==Y[1]
    for counts in (0, 640):
        for r in range(0, flat + 1, 5):
            assert gain_a_q10(code, counts, r) == SCALE * gain_a_q10(stock, counts, r), \
                f"{counts} counts / rateKey {r} is not EXACTLY {SCALE}x on the flat segment"
    print(f"    ✅ EXACTLY {SCALE}.000000x -- integer-exact, not within a tolerance -- at BOTH edited")
    print(f"       breakpoints (0 and 640 counts) for every rateKey <= {flat}, where Y[0] == Y[1] and")
    print("       the rate LERP is flat. That is grind #1's own operating region.")
    # r24's own surface must be untouched -- machine-checked on the gain_B model too.
    assert not [1 for v, r in grid if V69.gain_q10(code, v, r) != V69.gain_q10(stock, v, r)], \
        "a gain_B operating point moved -- r24 must be FULLY stock on V71B"
    print("    ✅ the gain_B (r24) surface is EXACTLY stock at every one of those points")

    # ---- SATURATION -- the number that decides between the siblings ------------------------------
    peak_a = max(gain_a_q10(code, v, r) for v, r in grid)
    # ---- 📋 SIZING bit4's THRESHOLD AGAINST r26's OWN REACHABLE OUTPUT --------------------------
    # 🛑 THIS IS THE V69 FAILURE MODE. V69's bit4 tested a lane at >= 4096 whose entire reachable
    # range topped out at 164-341 -- 12-25x above anything it could ever produce. Sizing T against
    # r24's numbers would repeat it, because r26 carries an EXTRA `avg(gp-0x69a4)` factor that r24
    # does not: r26 = (dtorque * avg >> 10) * gain_A >> 10 vs r24 = (dtorque * gain_B) >> 10.
    T = A.THRESHOLD                            # 128, inherited from V71A's rung SHAPE (sar 0x7)
    print(f"\n  📋 bit4 SIZING -- against r26's OWN output, not r24's. T = {T}, two-sided.")
    print(f"     |r26| >= {T}  <=>  |dtorque| * avg >= {T} * 2^{SAR1 + SAR2} / gain_A")
    print(f"    {'avg':>7} {'x unity':>8}  {'|dtorque| to trip @gain_A ' + str(peak_a):>34}")
    need = {}
    for avg in (16, 32, 64, 128, 256, 512, 1024, 2048, 4096):
        need[avg] = T * (1 << (SAR1 + SAR2)) / (avg * peak_a)
        flag = "  🛑 VACUOUS (> the recorded max 839)" if need[avg] > RECORDED_DTORQUE_MAX else ""
        print(f"    {avg:>7} {avg / 1024:>7.3f}x  {need[avg]:>34.1f}{flag}")
    avg_vacuous = T * (1 << (SAR1 + SAR2)) / (RECORDED_DTORQUE_MAX * peak_a)
    print(f"    ⇒ the rung goes VACUOUS only below avg = {avg_vacuous:.1f} "
          f"({avg_vacuous / 1024:.4f}x unity) -- i.e. it stays live over a ~2500:1 range of `avg`.")
    assert avg_vacuous < 64, \
        f"bit4 needs avg >= {avg_vacuous:.0f} to be non-vacuous -- size T lower (the V69 lesson)"
    print(f"    ⇒ at unity avg (1024) it trips at |dtorque| = {need[1024]:.1f}, against a recorded")
    print(f"      max of {RECORDED_DTORQUE_MAX} and V69's flight max of 633.9. Very sensitive.")
    print("    ⚠ THE OTHER TAIL, stated: if `avg` is large the rung may read a HIGH duty rather than")
    print("      a mid-band one. That is still informative -- combined with bit3 it says the lane is")
    print("      live and large, which is what a positive control is for -- but do not read a 100%")
    print("      duty as 'the dose worked'; read it as 'the lane reaches +/-128 nearly always'.")
    print(f"    ★ bit3 (the SIGN of gp-0x{MIRROR:04X}) IS INDEPENDENTLY GUARANTEED NON-VACUOUS: V70's")
    print("      probe read this exact cell and measured 1,644 / 18,010 frames STRICTLY NEGATIVE")
    print("      (9.13%). A pinned-zero cell cannot do that ⇒ r26 is live and signed-varying on-car.")
    print("      That is the one rung on this build whose informativeness is already measured.")

    print("\n  🛑 SATURATION -- r26's rail as a FUNCTION OF avg(gp-0x69a4), which is UNMEASURED.")
    print(f"     r26 = clamp(polarity * ((dtorque * avg) >> {SAR1}) * gain_A >> {SAR2}, +/-{LANE_CLIP})")
    print(f"     rail |dtorque| = {LANE_CLIP} * 2^{SAR1 + SAR2} / (avg * gain_A)")
    print(f"    {'avg':>7}  {'x unity(1024)':>13}  {'rail @gain_A 3072':>18}  {'rail @gain_A 6144':>18}")
    for avg in (256, 512, 1024, 1536, 2048, 4096, 8192, 16384, AVG_MAX):
        print(f"    {avg:>7}  {avg / 1024:>12.2f}x  {r26_rail(avg, 3072):>18.0f}  "
              f"{r26_rail(avg, peak_a):>18.0f}")
    cross_new = LANE_CLIP * (1 << (SAR1 + SAR2)) / (peak_a * RECORDED_DTORQUE_MAX)
    cross_old = LANE_CLIP * (1 << (SAR1 + SAR2)) / (3072 * RECORDED_DTORQUE_MAX)
    print(f"    ⇒ at the repo-recorded max |dtorque| = {RECORDED_DTORQUE_MAX}, the rail is crossed at")
    print(f"      avg = {cross_new:.0f} with the doubled gain_A ({cross_new / 1024:.2f}x unity), and at")
    print(f"      avg = {cross_old:.0f} with stock ({cross_old / 1024:.2f}x unity).")
    print(f"    ⚠ {cross_new / 1024:.2f}x unity IS PLAUSIBLE in normal driving. SAY SO. But note this")
    print("      crossing is IDENTICAL for V71A -- `sar 0x9` after the multiply and a doubled gain_A")
    print("      before it produce the SAME magnitude -- and a clamp crossing is a SATURATION, not a")
    print("      wrap: it costs describing-function gain, it cannot produce garbage.")
    print("\n  🛑 WHERE V71B IS GENUINELY WORSE THAN V71A -- INT32 headroom at `mul` 0x3AB72:")
    print(f"     structural worst case = ((({DTORQUE_CLAMP} * {AVG_MAX}) >> {SAR1}) * gain_A)")
    for g, who in ((3072, "stock / V71A (the doubling is in the SHIFT)"), (peak_a, "V71B (in the MUL)")):
        p = int32_worst(g)
        print(f"       gain_A {g:>5}  {p:>13,}  = {p / 2**31 * 100:5.2f}% of INT32_MAX   {who}")
    assert int32_worst(peak_a) < 2 ** 31, \
        "the worst-case product at 0x3AB72 OVERFLOWS int32 -- V850 `mul` truncates SILENTLY"
    print("    ✅ NO overflow is reachable: `ld.hu` bounds avg at 65535 and the product stays below")
    print(f"       INT32_MAX ({int32_worst(peak_a) / 2**31 * 100:.2f}%).")
    print("    ⚠ BUT the headroom HALVES, into the band V62's own note rejected: V62 refused to edit")
    print("      0x3AB70 because it 'pushes a mul operand to 94% of INT32_MAX' -- the same method, the")
    print("      same multiply, the same number. V71A's `sar` leaves both operands at stock magnitude.")

    # ---- CRC -------------------------------------------------------------------------------------
    touched = [CAVE_BASE, A.RATCHET_ADDR, EDITED_RECS[0], EDITED_RECS[1],
               A.SURFACE[0][0], A.SURFACE[-1][0]]
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    assert [b[1] for b in blocks] == [0xC4FFC, 0xC6FFC, 0xD2FFC], \
        f"expected the MAIN, CAL and 0xD2000 trailers, got {[hex(b[1]) for b in blocks]}"
    assert V53.owning_block(code, EDITED_RECS[0]) == CAL_BLOCK, "gain_A is not in the CAL block"
    print(f"\n  CRC -- EXACTLY {len(blocks)} blocks move (asserted, not observed):")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    assert walk_all_blocks(bytes(code)) == 0, "CRC chain FAILED"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")

    # ---- the attributed diff ----------------------------------------------------------------------
    cave_range = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))
    surf_bytes = {a + k for a, _, _, _ in A.SURFACE for k in (0, 1)}
    gaina_bytes = {b + Y_OFFSET + k for b in EDITED_RECS for k in range(8)}
    d70 = [i for i in range(START, END) if code[i] != v70[i]]
    f70 = [d for d in d70 if d not in crc_only]
    stray = [d for d in f70 if d not in cave_range | surf_bytes | gaina_bytes | {A.RATCHET_ADDR}]
    assert not stray, f"UNATTRIBUTED functional bytes vs V70: {[hex(x) for x in stray]}"
    print(f"\n  EXACT DIFF vs V70: {len(d70)} bytes = {len(f70)} functional + {len(d70) - len(f70)} CRC")
    for d in sorted(f70):
        where = ("EDIT 4 cave" if d in cave_range else
                 "EDIT 3 gain_B surface (x2 -> STOCK)" if d in surf_bytes else
                 "EDIT 2 gain_A rec0/rec1 Y (x2)" if d in gaina_bytes else
                 "EDIT 1 ratchet 0x454FE")
        print(f"    0x{d:05X}  {v70[d]:02X} -> {code[d]:02X}   {where}")

    if os.path.exists(V71A_BIN):
        a_img = Path(V71A_BIN).read_bytes()
        da = [i for i in range(START, END) if code[i] != a_img[i]]
        fa = [i for i in da if i not in crc_only]
        in_cave = [i for i in fa if i in cave_range]
        n_sar = len([i for i in fa if i in (A.R26_SAR, A.R24_SAR)])
        n_gaina = len([i for i in fa if i in gaina_bytes])
        print(f"\n  DIFF vs V71A (the sibling): {len(da)} bytes = {n_sar} `sar` + {n_gaina} gain_A + "
              f"{len(in_cave)} cave + {len(da) - len(fa)} CRC")
        # 🛑 EXACTLY ONE CAVE BYTE, and it must be the mirror displacement. That single byte is the
        # difference between a build that watches the lane it doses and one that does not.
        assert in_cave == [CAVE_BASE + 0x1A], \
            f"the caves differ at {[hex(x) for x in in_cave]}, expected EXACTLY " \
            f"[0x{CAVE_BASE + 0x1A:05X}] -- the mirror displacement byte"
        assert code[CAVE_BASE + 0x1A] == 0x24 and a_img[CAVE_BASE + 0x1A] == 0x26, \
            "the mirror byte is not 0x24 (gp-0x6adc) on V71B / 0x26 (gp-0x6ada) on V71A"
        print(f"    ✅ the caves differ in EXACTLY ONE byte, 0x{CAVE_BASE + 0x1A:05X}: "
              "0x26 (gp-0x6ada, r24) on V71A -> 0x24 (gp-0x6adc, r26) on V71B.")
        print("       🛑 That byte is NOT visible on the wire. The .rwd FILENAME remains the only")
        print("          pre-drive discriminator, and bit4/bit3 are NOT comparable across the two.")

    d_stock = [i for i in range(START, END) if code[i] != stock[i]]
    print(f"  EXACT DIFF vs STOCK: {len(d_stock)} bytes -- run `python diff_build_vs_stock.py v71b`")

    # ---- write + readback --------------------------------------------------------------------------
    if existing is not None and existing != bytes(code):
        raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {img_sha}")

    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V71B output")
    back = parse_x31(rwd)
    dec = bytearray(v70)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"
    A.assert_ratchet_edit(dec, "V71B readback", expect_edited=True)
    A.assert_sar_sites(dec, "V71B readback", expect_doubled=False)
    A.assert_governor_monitor_safety(dec, "V71B readback")
    assert_gain_a(dec, "V71B readback", doubled=True)
    A.assert_probe_census(bytes(dec), cave_span, MIRROR)
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    for base in UNTOUCHED_A_RECS:
        assert bytes(dec[base:base + REC_STRIDE]) == bytes(stock[base:base + REC_STRIDE])
    for base in A.REC_Y_STOCK:
        assert bytes(dec[base:base + REC_STRIDE]) == bytes(stock[base:base + REC_STRIDE])
    assert not [(v, r) for v, r in grid if v >= HIGHWAY_COUNTS
                and gain_a_q10(dec, v, r) != gain_a_q10(stock, v, r)], \
        "readback moved a >= 50 km/h operating point"
    V57.assert_decoupled(_with_stock_ratchet(dec), "V71B readback (0x454FE restored for the guard)")
    V55.assert_variant_tables(dec)
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    print("\n  READBACK -- payload, the ratchet byte, both stock `sar` sites, every gain_A record,")
    print("     every gain_B record == STOCK, the whole cave, the probe census, the >= 50 km/h")
    print("     structural-stock sweep and the full CRC chain: ALL re-verified.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print("  V71B BUILT. r26 dosed ALONE and SPEED-SHAPED: 2.000000x at <= 10 km/h, EXACTLY")
    print("  1.000000x at >= 50 km/h. r24 fully stock. Same 68-byte probe as V71A.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _with_stock_ratchet(buf):
    """V57's inherited guard asserts 0x454FE is the STOCK `bne`, which V71B deliberately changes.
    Run it in FULL on a copy with that ONE byte restored, and assert the exception set is exactly it.
    """
    copy = bytearray(buf)
    struct.pack_into("<H", copy, A.RATCHET_ADDR, A.RATCHET_STOCK_HW)
    diff = [i for i in range(START, END) if copy[i] != buf[i]]
    assert diff == [A.RATCHET_ADDR], \
        f"the guard relaxation covers {[hex(x) for x in diff]}, expected [0x{A.RATCHET_ADDR:05X}]"
    return copy


if __name__ == "__main__":
    build()
