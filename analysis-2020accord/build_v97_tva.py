#!/usr/bin/env python3
r"""=================================================================================================
V97 -- ONE CELL. `0xC63AC` 102 -> 150.  The Path-2 IIR pole in `FUN_00038148`.
=================================================================================================

BASE: V96 (**the build on the car**, routes 7e/7f, both fault-free).  V97 = V96 + 2 bytes.
The V96 cave, its 427 probe, V92's calibration and every frozen lever are carried UNCHANGED.

-------------------------------------------------------------------------------------------------
WHAT THE CELL IS
-------------------------------------------------------------------------------------------------
    gp-0x374c += ((target - gp-0x374c) * A) >> 10          A = cal(0xC63AC)      @0x38202
                                                            `ld.hu 0x73ac,tp,r13`

A one-pole IIR on the Stage-1 accumulator that feeds `iVar6`, hence `gp-0x6b70`, hence the PID
reference.  🛑 **DC gain is 1.000000 for ANY A** -- it is a POLE, not a GAIN.  It cannot change how
hard the car pulls, only WHEN.  That is the whole reason it escapes the sign problem that
disqualified all six lane weights.

    A = 102 (stock, all 99 images)   fc = 15.9 Hz   -18.7 / -23.6 / -26.7 deg at 6 / 7.79 / 9 Hz
    A = 150 (V97)                    fc = 23.3 Hz    -8.5 / -11.0 / -12.6 deg  =>  +7.82 deg at 7.79

-------------------------------------------------------------------------------------------------
WHY UP, AND HOW THE DIRECTION WAS SETTLED (it was NOT settled by arithmetic alone)
-------------------------------------------------------------------------------------------------
Measured on routes 7e/7f, V96 on the car, TWO independent instruments that agree to <7 deg:

  1. `Q = -d(gp-0x6b70)/d(T)` from the 427 magnitude + sign against `0x18F` STEER_TORQUE_SENSOR,
     hands-off engaged returns, episode-bootstrapped   (`rlog-tools/v97_measure_Q.py`):
         |Q| = 1.233 (both routes)   arg Q = -133.7 / -131.5 deg   coherence 0.974 / 0.978
         |Q| + cos(arg Q) = +0.542 [+0.477, +0.598] and +0.570 [+0.462, +0.619]
     🛑 The criterion is "inversion iff |Q| < 1 AND cos(arg Q) < -|Q|".  **|Q| = 1.233 > 1, so
     inversion is ARITHMETICALLY EXCLUDED at any phase** -- the +-28 deg CAN-join uncertainty,
     which was the dominant error term, is moot.  THE LEAD ARRIVES AS LEAD.

  2. The V96 cave's own sign bits, Welch on the full engaged set:
         arg(V) - arg(rate)  = -97.3 / -101.8 deg   (V = sign of gp-0x6b70,  byte4 b7)
         arg(B') - arg(rate) = +78.6 / +78.0 deg    (B' = sign of gp-0x374c>>4, byte4 b6)
         arg(V) - arg(B')    = -178.1 deg on BOTH routes
     => `iVar6`'s 6-9 Hz phase is set by the B branch, i.e. by the lane sum THROUGH `gp-0x374c`
     => `0xC63AC` rotates essentially all of Q.  ⊕ The orchestrator reproduced the SEPARATION
     independently at +179.8 / +178.6 deg (coherence 0.215 / 0.107 against shuffled 0.0066 /
     0.0041), and arg(V) vs rate at -113.0 / -115.1 deg -- same quadrant.

  arg(V) sits just BELOW -90 deg, where cos < 0 = ANTI-DAMPING (the corpus `Re(Z) < 0`, now seen
  on a firmware-internal signal).  Adding lead rotates it TOWARD -90 and past it, i.e. TOWARD the
  damping axis.  Dissipative projection |V|.cos(theta), k = |f'B'|/|V| bracketed 0.5 .. 2.0:
         7e baseline -0.1270  ->  A=130: -0.0845 / -0.0419 / +0.0432    ALL BETTER
         7f baseline -0.2042  ->  A=130: -0.1619 / -0.1196 / -0.0350    ALL BETTER
         A=150 better still; 7e crosses into genuinely DISSIPATIVE at k >= 1.

🛑🛑 THE DIRECTION WAS INVERTED ONCE, BY A `scipy.signal.csd` CONVENTION ERROR, AND CAUGHT.
`csd(x, y)` returns `arg(Y) - arg(X)`.  An agent labelled every cross-spectrum backwards and
recommended LOWERING this cell -- which would have made the car worse.  The tell was that its
phases disagreed with instrument (1) by a REPLICATED ~90 deg.  A bug signature, not physics.
⇒ **This build exists because two independent measurements were run and allowed to disagree.**
Recorded so the next session knows the direction is measured, not modelled.

-------------------------------------------------------------------------------------------------
🛑 THE COST -- STATED UP FRONT, AND IT LANDS ON A SYMPTOM THE OPERATOR CALLS FIXED
-------------------------------------------------------------------------------------------------
Raising the pole widens the passband.  Path-2 throughput at 21 Hz:
        A=102 1.000x   A=130 1.152x   A=150 1.234x   A=170 1.300x   A=205 1.383x
**V62 bought the grinding fix by taking 18-22 Hz down 8-42x, and V88's Lever B (15-22 Hz command
0.549 [0.407, 0.844]) is on the car now.**  Path 1 is unweighted and unaffected by A, which dilutes
the figure to **+2% .. +13% on the TOTAL command at A=150** -- worst case 1.13 x 0.549 = 0.620,
still inside V88's measured CI.  ⚠ That dilution is a MODEL, not a measurement.
🛑 The exchange rate is FLAT at 0.33 deg per 1% of extra 21 Hz across the whole sweep -- there is no
sweet spot, so a smaller step buys proportionally less.  **A=150 was the operator's own choice,
made with this trade stated.**  RULE 9: grind #1 and grind #2 have never been separated.

-------------------------------------------------------------------------------------------------
BLAST RADIUS -- the smallest of any candidate examined this session
-------------------------------------------------------------------------------------------------
**1 reader, 0 writers**, established FIVE ways, three of them independent of each other:
  * Ghidra operand search -> exactly 1 hit, `ld.hu 0x73ac,tp,r13` @0x38202  (183,570 scanned)
  * raw LE scan, BOTH parities (covers `hw2 = disp|1` and the 0x3C/0x3D `ld.bu` parity trap):
    6 raw hits, every one adjudicated, only 0x38202 is a real tp-based access
  * the 6-byte extended gp/tp form: 0 hits
  * absolute synthesis via movea/addi/movhi with immediate 0x63ac: 0 sites image-wide
  * `ep`-relative short-format aliasing re-test (the NEW trap found this session): 98
    `movea imm,tp,ep` sites image-wide, **0** within the 254-byte `sld` reach of 0xC63AC, and a
    gp-based `ep` cannot reach the cal block at all (movea is +-32768 from 0xFEDF8000)
GATE 1 (RAM ownership): VACUOUS -- a flash cal cell, no cave, no RAM claimed.
GATE 2 (closed-loop stability): magnitude AND phase priced above; the 21 Hz cost is the residual
risk and it is stated, not hidden.  ⚠ Describing-function analysis across the PID's anti-windup and
`FUN_00036682`'s hysteresis was NOT done -- every phase figure here is linear-small-signal.

-------------------------------------------------------------------------------------------------
WHAT THIS BUILD IS NOT
-------------------------------------------------------------------------------------------------
* NOT a return-SPEED fix.  The "2.13x faster" figure that first sold this cell was the ACCUMULATOR
  settling, not the wheel; it was withdrawn.  Three mechanisms for the slow return died this
  session (`0xC520C` ceiling: 0.00% of return samples reach its first knot · `0xC6194` slew
  limiter: real, calibrated, but its input partition `0xC4118` is all-1 so 100% bypasses it ·
  AUTH/`0xC67C8`: beta(log AUTH) = -0.013 [-0.344, +0.319], CI excludes the predicted +1, and
  `gp-0x6b4c` is a second LKAS route that never sees AUTH).  **Clause 2 has NO mechanism. This
  build does not address it and must not be scored as if it did.**
* NOT a probe change.  V96's cave is carried byte-for-byte.  Its regressor is 34x over-range
  (M pinned at 0 on 99.9% of frames) so S1/S2 stay VOID -- V97 does not fix that either.

-------------------------------------------------------------------------------------------------
CLASS, AGAINST THE WHOLE ARC SINCE V38
-------------------------------------------------------------------------------------------------
V38-V52 authority/filters/poles/caves · V53-V61 telemetry + lane mutes · V62-V73 the rate lane ·
V74-V83a the base-assist damper · V84-V86B damper reverts + phase · V87 subtractive · V88 Lever B ·
V89 plant model · V90 instrument · V91/V92 `0xCBE74` x1.5 · V93/V94 `0xCBE74` CUT (ABORTED) ·
V96 instrument + revert.
**V97 is the first build in the arc to move a LOOP POLE.**  Every prior lever was a gain, a weight,
a table shape, a gate or a probe.  `0xC63AC` is virgin across all 99 images -- genuinely new, not a
re-run in a different direction.
=================================================================================================
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the block map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V97_WRITE", "").strip().lower()

TP = 0xBF000                       # 🛑 tp+0x73ac = 0xC63AC, NOT 0xC73AC (off-by-0x1000, 5 times)

BASE_NAME = ("_v96_V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6_plain_image.bin")
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "876cf2be5800f0f8e315f8b1d63dd103ec11ee7293577808ecff5f19a849cda3"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))

CELL = 0xC63AC                     # the ONE cell
CELL_FROM, CELL_TO = 102, 150
CELL_TP_OFF = 0x73AC               # asserted against TP + off == CELL, computed not eyeballed

VARIANT_TOKEN = "V96BASE-C63AC.102to150"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v97_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V97-{TAG}-0x{START:X}-0x{END:X}.rwd")

# EVERYTHING THAT MUST NOT MOVE -- asserted on the base, the built image AND the shipped .rwd.
# 🛑 Values are the V96 base's, read from the image where marked None.
FROZEN = {
    0xC6446: (2, 5244, "🛑 Lever B ARM -- silently reverted at a rebase THREE times"),
    0x3AA96: (1, 0xFB, "🛑 Lever B GATE -- both halves or neither"),
    0xC6CD0: (2, 3564, "🛑 the 4x forward LKAS gain -- NEVER lower"),
    0xC40BC: (2, 600,  "🛑 Coulomb relay gate -- 6000 measured 2.3x WORSE. Do not restore"),
    0xC40D2: (2, 204,  "V89's K1, measured FLAT, left on deliberately"),
    0xC40D4: (2, 573,  "observer torque IIR -- V86 took it to 286 and was FALSIFIED"),
    0xC40D6: (2, 246,  "🛑 accel/inertia IIR -- VIRGIN 92/92. Same branch V86 nulled. NOT touched"),
    0xC40D8: (2, 3686, "gp-0x4f60 IIR -- a NO-OP (-0.6 deg). Kill any proposal to move it"),
    0xC4080: (2, 0,    "🛑 K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC63AE: (2, 1024, "🛑 Stage-2 input scale -- never 0 (LERP index would go constant = relay)"),
    0xC6200: (2, 8192, "🛑 gp-0x6b70's clamp -- never below Y[0]"),
    0xC6468: (2, 2639, "model output gain -- SHARED, 5 readers"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0 -- lane measured ~0; frozen since V83a"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN. NOT this build"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN. Deflated: lane carries ~1.1 of 342 counts"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN. A cliff edge, not a lever"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e -- lane PROVABLY == 0; editing it is a guaranteed null"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS lane. Instrument, not mechanism"),
    0xC63D2: (2, 6,    "🛑 FUN_00036682 pole, fc 0.93 Hz -- ALREADY the tilt. Raising it DESTROYS it"),
    0xC644A: (2, 1024, "PID D-path IIR -- pass-through. V43->32, V49->64, both null"),
    0xC6AE6: (2, 2048, "PID Kd -- VIRGIN. Pure phase; do NOT lower (it is the only lead)"),
    0xC6B12: (2, 98,   "PID Ki -- VIRGIN but INERT: anti-windup already railed at 6-10 km/h"),
    0xC6B26: (2, 256,  "PID Kp -- VIRGIN. Blunt"),
    0xC62EA: (2, 0,    "steer-to-zero, V53, on the car"),
    0x454FE: (1, 0xB5, "V42 byte -- MEASURED INERT. Carried because free. Claim nothing for it"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
    0xC6194: (2, 3,    "the REAL LKAS slew limiter -- dead because 0xC4118 is all-1. Do not arm"),
    0xE547C: (2, None, "🛑 AUTHORITY CURVE -- virgin on all 99 images. NOT touched"),
    0xE5404: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xE52FC: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xE5284: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xC520C: (2, None, "🛑 governor rate ceiling -- V40 BRICKED on a neighbour. NOT touched"),
}

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    """Every assertion prints a BOOLEAN. A check that produces no output is not a check."""
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"🛑 ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def rdw(b, a, w):
    return u16(b, a) if w == 2 else b[a]


def runs_of(a, b):
    """Contiguous differing byte runs between two images."""
    out, i, n = [], 0, len(a)
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def main():
    print("=" * 102)
    print("  V97 -- 0xC63AC 102 -> 150.  ONE CELL.  Base = V96, the build ON THE CAR.")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(BASE_BIN).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base is V96, sha256 {BASE_SHA[:16]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain verifies 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())

    print("\n  [2] THE ADDRESS -- computed, never eyeballed (off-by-0x1000 has recurred 5x)")
    check(TP + CELL_TP_OFF == CELL,
          f"tp(0x{TP:X}) + 0x{CELL_TP_OFF:X} == 0x{CELL:X}  (NOT 0x{TP + 0x1000 + CELL_TP_OFF:X})")
    check(u16(base, CELL) == CELL_FROM, f"base 0x{CELL:X} reads {CELL_FROM}")
    check(u16(stock, CELL) == CELL_FROM, f"STOCK 0x{CELL:X} also reads {CELL_FROM} -- VIRGIN")

    print("\n  [3] READER SITE -- the one instruction that consumes it")
    # 🛑 THE `hw2 = (disp | 1)` PARITY TRAP, hit while writing this file and recorded here.
    # A first draft asserted `ad 37 ac 73`, reasoning that a disp of 0x73ac appears literally in
    # hw2.  It does NOT: for this form the encoder sets bit 0, so hw2 reads 0x73AD.  The check
    # failed, which is the check doing its job -- an eyeballed encoding is a guess, and this kit
    # has a standing rule that assembly CONFIRMS a claim, it does not FORM one.
    site = 0x38202
    check(bytes(base[site:site + 4]) == bytes.fromhex("e56fad73"),
          f"@0x{site:X} is the sole reader, bytes e5 6f ad 73  (hw2 = 0x73AD = 0x73AC | 1)")
    check(u16(base, site + 2) == (CELL_TP_OFF | 1),
          f"hw2 0x{u16(base, site + 2):04X} == (0x{CELL_TP_OFF:X} | 1) -- the parity trap, asserted")
    check(bytes(base[site:site + 4]) == bytes(stock[site:site + 4]),
          "the reader instruction is byte-identical to stock -- no code edit in this build")
    check(bytes(base[0x381FE:0x38202]) == bytes.fromhex("2437b5c8"),
          "@0x381FE is `ld.w -0x374c[gp],r6` -- the accumulator this pole filters, anchor confirmed")

    print("\n  [4] EDIT")
    code = bytearray(base)
    struct.pack_into("<H", code, CELL, CELL_TO)
    check(u16(code, CELL) == CELL_TO, f"built 0x{CELL:X} reads {CELL_TO}")
    dc = 1024.0 / CELL_TO
    print(f"      fc: 15.9 Hz -> 23.3 Hz | +7.82 deg at 7.79 Hz | 21 Hz Path-2 x1.234 "
          f"| dead zone {1024 // CELL_FROM} -> {1024 // CELL_TO} counts")
    check(dc > 0, "dead-zone note printed")

    print("\n  [5] THE DIFF IS EXACTLY ONE BYTE, IN ONE RUN")
    # 102 = 0x0066, 150 = 0x0096 -- the HIGH byte is 0x00 in both, so only the low byte moves.
    # V97 is a ONE-BYTE build.  Asserted as such rather than loosening a wrong 2-byte expectation.
    rs = runs_of(base, code)
    exp_len = 2 if (CELL_FROM >> 8) != (CELL_TO >> 8) else 1
    check(len(rs) == 1, f"exactly ONE differing run (got {len(rs)})")
    check(rs[0] == (CELL, exp_len),
          f"the run is (0x{CELL:X}, {exp_len} byte) -- got {[(hex(a), n) for a, n in rs]}")
    check(sum(r[1] for r in rs) == exp_len,
          f"{exp_len} byte total, zero unattributed  "
          f"(high byte 0x{CELL_FROM >> 8:02X} unchanged, low 0x{CELL_FROM & 0xFF:02X}"
          f" -> 0x{CELL_TO & 0xFF:02X})")
    check(u16(code, CELL) == CELL_TO and u16(base, CELL) == CELL_FROM,
          "and the HALFWORD still reads 102 -> 150 -- the one byte carries the whole edit")

    print("\n  [6] NOTHING ELSE MOVED -- frozen cells, base vs built")
    for a, (w, want, why) in sorted(FROZEN.items()):
        bv, cv = rdw(base, a, w), rdw(code, a, w)
        check(bv == cv, f"0x{a:X} unchanged ({bv}) -- {why[:64]}")
        if want is not None:
            check(bv == want, f"0x{a:X} == {want} on the base as expected")

    print("\n  [7] THE CAL BLOCKS AND THE CAVE ARE UNTOUCHED")
    for lo, hi, nm in ((0xC6000, 0xC7000, "cal block A"), (0xD6000, 0xD8000, "mode records"),
                       (0xC4000, 0xC4200, "FUN_0003b8f6 cals"), (0xE5000, 0xE5600, "auth curves")):
        d = [i for i in range(lo, hi) if base[i] != code[i]]
        expect = list(range(CELL, CELL + exp_len)) if lo <= CELL < hi else []
        check(d == expect, f"{nm} [0x{lo:X},0x{hi:X}) differs only at the target "
                           f"({len(d)} byte(s), expected {len(expect)})")

    print("\n  [8] CRC -- the owning block DERIVED from the image's own 50-block map, then asserted")
    touched = list(range(CELL, CELL + exp_len))
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    check(len(blocks) == 1, f"the edit lands in exactly ONE block (got {len(blocks)})")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit landed on the trailer at 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}")
    derived = {blk[1] for blk in blocks}
    check(derived == {0xC6FFC},
          f"DERIVED trailer set {sorted(hex(t) for t in derived)} == {{0xc6ffc}} -- 0x{CELL:X} lies "
          f"in the calibration block [0x0C6000,0x0C6FFC). Derived, then asserted; never hard-coded")
    check(0x055FFC not in {blk[1] + k for blk in blocks for k in range(4)},
          "🛑 0x055FFC is LIVE CODE, not a trailer -- writing there would be hidden by the recompute")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "the risky 0xC5000 model-coeff block is byte-identical to the base")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")

    print("\n  [8b] AND THE DIFF IS NOW EXACTLY THE EDIT PLUS ITS OWN CRC TRAILER")
    rs2 = runs_of(base, code)
    check(len(rs2) == 2, f"two runs: the edit and the trailer (got {len(rs2)})")
    check(rs2[0] == (CELL, exp_len), f"run 1 is the edit at 0x{CELL:X}")
    check(rs2[1][0] == 0xC6FFC and rs2[1][1] <= 4,
          f"run 2 is the CRC trailer at 0x{rs2[1][0]:X} ({rs2[1][1]} bytes) -- nothing else moved")

    print("\n  [9] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V97 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd payload is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50")
    check(u16(dec, CELL) == CELL_TO, f"the .rwd payload carries 0x{CELL:X} == {CELL_TO}")
    for a, (w, want, why) in sorted(FROZEN.items()):
        check(rdw(dec, a, w) == rdw(base, a, w), f"0x{a:X} frozen in the .rwd payload too")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   ({len(rwd)} bytes)")
    print(f"  {_checks[1]}/{_checks[0]} assertions PASSED")
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V97_WRITE=rwd to cut.")
        return
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None and existing != bytes(code):
        raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
    Path(BIN_OUT).write_bytes(bytes(code))
    print(f"  wrote {BIN_OUT}")
    if WRITE_MODE == "rwd":
        if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
            raise SystemExit(f"🛑 a DIFFERENT {OUT} exists -- ONE .rwd per build number.")
        Path(OUT).write_bytes(rwd)
        print(f"  wrote {OUT}")
        print("\n  [10] 🛑 FROM-DISK -- the SHIPPED .rwd re-read, re-hashed, decoded, re-asserted")
        shipped = Path(OUT).read_bytes()
        check(hashlib.sha256(shipped).hexdigest() == rwd_sha, f"shipped .rwd sha256 {rwd_sha[:16]}…")
        FF.assert_x31_checksum(shipped, "V97 shipped")
        sd = bytearray(base)
        sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
        check(bytes(sd) == bytes(code), "the SHIPPED .rwd decodes to the built image")
        check(u16(sd, CELL) == CELL_TO, f"the SHIPPED .rwd carries 0x{CELL:X} == {CELL_TO}")
        check(walk_all_blocks(bytes(sd)) == 0, "shipped-.rwd CRC chain 50/50")
        print(f"\n  {_checks[1]}/{_checks[0]} assertions PASSED")


if __name__ == "__main__":
    main()
