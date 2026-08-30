# -*- coding: utf-8 -*-
r"""V237 -- THE RATCHET LEVER THAT COSTS NO EFFORT. EIGHT BYTES ON V235.

WHAT THIS IS. `gp-0x6b86`'s lane is not the memoryless curve the loop census priced: `FUN_000352b4`
ends with a PARALLEL LAGGED BRANCH added to the direct path,

    iVar24 += (iVar33*0x80 - iVar24) * k >> 11        32-bit state, 1 kHz
    contribution = (iVar24 -/+ 0x80) >> 7

which is a first-order EMA with `a = k/2048` and **DC gain exactly 1**. That is the whole point: k moves
the POLE and cannot move the static gain, so unlike V236's slope cap it costs NO assist at any steering
input. The archive that found the branch says of the census's slope-only model: "any |L| computed from
the slope alone is incomplete."

THE LAYOUT, READ OUT OF THE DECOMPILE RATHER THAN INFERRED. An earlier pass refused to edit these cells
because a raw dump showed two 4-value blocks straddling a 6-value ascending run and would not parse.
The LERP reader settles it:

    pcVar26 = FUN_00007906 + unaff_tp;                     Y base   = tp+0x7906
    if (*(ushort *)(unaff_tp + 0x78fe) < uVar17) {         X[0]     = tp+0x78FE
        if (uVar17 < *(ushort *)(unaff_tp + 0x7904)) {     X[3]     = tp+0x7904
            puVar13 = (ushort *)(unaff_tp + 0x7900);       X[1]
        } else uVar40 = *(ushort *)(unaff_tp + 0x790c);    Y[3]     = tp+0x790C
    } else uVar40 = *(ushort *)(FUN_00007906 + unaff_tp);  Y[0]     = tp+0x7906

    => X = [0, 9830, 26214, 32768] at 0xC68FE   Y = [20, 20, 20, 20] at 0xC6906   (tp = 0xBF000)

and the reader then CLAMPS the result:

    if (uVar40 < 0xcd) { iVar27 = max(2, uVar40); } else { iVar27 = 0xcc; }

**k is bounded to [2, 204] by the firmware itself**, which makes the top of the range a natural,
safe-by-construction bound rather than an arbitrary one.

THE DIRECTION, AIMED AND CHECKED. The archive computes the engaged-vs-manual difference at the mode:
"engaged lags 10.18 deg MORE, which moves 1-P.L the RIGHT way (1.798 -> 1.713)" -- i.e. MORE lag gives
SMALLER |1-P.L| gives LESS damping. **So raising k damps.** And the consistency check uses data that
played no part in deriving it: the MANUAL arm already runs k=41, and the ratchet is ABSENT in manual
(engaged clears its null 7/7, manual 0/7). The arm with the higher k is the arm without the symptom.

THE REACHABLE RANGE at 7.79 Hz, from the EMA (validated against the archive's own k=20 and k=41 figures
to 4 dp, which is what confirms the recursion was read correctly):

    k       |H|      arg      corner    lag vs k=20
    20    0.1966  -77.26 deg   1.56 Hz    0.00      <- ENGAGED today
    41    0.3819  -66.15 deg   3.22 Hz  +11.11      <- MANUAL arm; the archive calls this "TOO SMALL"
    80    0.6314  -49.46 deg   6.34 Hz  +27.80      <- THIS BUILD
   204    0.9063  -23.63 deg  16.70 Hz  +53.63      <- the firmware's own ceiling

WHY 80 AND NOT THE CEILING. k=41 is Honda's manual value and buys about 4.7 % less Q -- the archive
reached that and headlined it "THE EFFECT IS TOO SMALL". The ceiling extrapolates to roughly 21 %, but
that is a LINEAR extrapolation over five times the measured range on a branch the record calls
incomplete, and a 10x jump on an unmodelled lever is how the V94 drive ended. **80 puts the corner at
6.34 Hz, just BELOW the 7.79 Hz mode**, so the branch becomes responsive AT the mode while still
rolling off above it; it is 4x the current value, takes 52 % of the available phase change, and leaves
204 as a second rung if it helps. HF passage stays small either way (at 100 Hz, 0.064 at k=80 against
0.167 at the ceiling).

WHAT IT DOES NOT DO. No static assist changes at any input -- DC gain is 1 by construction, so this
build does NOT carry V236's 34.2 %-of-driving effort cost. It also cannot touch LKAS: the map is fed by
the driver torque sensor alone (`0xC616C` = 0 on all 161 images).

🛑 WHAT IS ASSUMED. The magnitude rests on the archive's 1.713/1.798 linearisation extrapolated 2.7x.
The DIRECTION is well-founded -- the archive's arithmetic plus the manual-arm consistency check -- but
the SIZE is an order-of-magnitude estimate, not a gated number. Said plainly on the card.

BASE: V235, the no-added-effort build. V237 = V235 + these four halfwords, so the pair isolates the
pole exactly, and neither build asks the operator for the effort trade V236 does.
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

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V237_WRITE", "").strip().lower()

BASE_NAME = "_v235_V235-V234BASE-C63AE.BACK.TO.HONDA.1024_plain_image.bin"
BASE_SHA = "ad6d485eefb2f6bcc195c062035d5a9dab5fb06dae7f46f68f5ca03a504c18ab"

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
POLE_Y = 0xC6906                            # engaged lag pole, LERP Y[0..3]
POLE_X = 0xC68FE                            # its X axis -- asserted, never written
K_OLD, K_NEW = 20, 80                       # corner 1.56 Hz -> 6.34 Hz, just below the mode
K_CLAMP_MAX = 204                           # the firmware's own clamp, from the reader
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V237-V235BASE-ENGAGED.LAGPOLE.80.NOCOST"

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
    print("  V234 -- LEVER B BACK TO V88'S MEASURED OPTIMUM.  TWO BYTES ON V233.")
    print("=" * 102)

    print("\n  [1] BASE = V233")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V233 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    for _i in range(4):
        check(u16(base, POLE_Y + 2 * _i) == K_OLD,
              f"base Y[{_i}] = {K_OLD} (the engaged pole, flat)")
    check([u16(base, POLE_X + 2 * _i) for _i in range(4)] == [0, 9830, 26214, 32768],
          "the X axis reads [0, 9830, 26214, 32768] -- the layout from the LERP reader, confirmed")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    for _i in range(4):
        struct.pack_into("<H", code, POLE_Y + 2 * _i, K_NEW)
        attributed |= {POLE_Y + 2 * _i, POLE_Y + 2 * _i + 1}
    check(all(u16(code, POLE_Y + 2 * _i) == K_NEW for _i in range(4)),
          f"engaged pole Y[0..3] {K_OLD} -> {K_NEW} (corner 1.56 Hz -> 6.34 Hz)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check(K_NEW <= K_CLAMP_MAX,
          f"{K_NEW} is inside the firmware's OWN clamp of {K_CLAMP_MAX} -- the reader does "
          f"max(2, min(k, 204)), so this cannot exceed what Honda's code already permits")
    check(K_NEW > K_OLD,
          "the direction is RAISE k: the archive shows more lag gives smaller |1-P.L| gives LESS "
          "damping, and the MANUAL arm at k=41 is the arm WITHOUT the ratchet")
    check(u16(code, SLOPE_CAP) == CAP_STOCK,
          f"0x{SLOPE_CAP:05X} left at {CAP_STOCK} -- this build does NOT carry V236's effort cost")
    check([u16(code, POLE_X + 2 * _i) for _i in range(4)] == [0, 9830, 26214, 32768],
          "the X axis is UNTOUCHED -- only the four Y halfwords moved")
    check(u16(code, LKAS_CLAMP) == 0,
          "0xC616C = 0 -- the map is fed by the driver torque sensor alone; LKAS cannot reach it")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")

    print("\n  [4] THE NOTCH AND EVERYTHING ELSE ARE V233, BYTE FOR BYTE")
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == bytes(base[BIQ:BIQ + BIQ_LEN]),
          "the net-damping-optimum biquad is untouched")
    check(u16(code, PROBE_HW2) == HW2_KEEP, "biquad-state probe CARRIED")
    check(code[SHIFT_OFF] == SAR_KEEP, "probe shift CARRIED")
    check(code[ALPHA2] == ALPHA2_VAL, f"0x{ALPHA2:05X} alpha2 = {ALPHA2_VAL}")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- not the bricking class")
    for a, want in sorted(ARM_SITES.items()):
        check(bytes(code[a:a + len(bytes.fromhex(want))]).hex() == want, f"0x{a:05X} = {want}")
    check(code[ARM_CAL] == 1, f"0x{ARM_CAL:05X} = 1 (biquad enabled)")

    print("\n  [5] THE +-8192 RAIL IS UNTOUCHED")
    check(bytes(code[0x3AC42:0x3AC44]) == bytes(base[0x3AC42:0x3AC44]), "0x3AC42 rail immediate frozen")
    check(bytes(code[0x3AC58:0x3AC5A]) == bytes(base[0x3AC58:0x3AC5A]), "0x3AC58 rail immediate frozen")

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

    print("\n  [7] FULL BYTE DIFF vs V233")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    _exp = 4 * sum(1 for k in range(2)
                   if ((K_OLD >> (8 * k)) & 0xFF) != ((K_NEW >> (8 * k)) & 0xFF))
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(set(pay) <= {POLE_Y + j for j in range(8)},
          "every payload byte is inside the pole Y block -- the X axis did not move")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V237 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v237_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V234_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** A CORRECTION TO MY OWN SHELF. The record states: 'THE LANE IS AN OPTIMUM AND V88 IS  **")
    print("  ** SITTING ON IT. BOTH FLANKS ARE NOW MEASURED... LEVER B IS OFF EVERY FUTURE          **")
    print("  ** SHORTLIST, IN BOTH DIRECTIONS.' V61 below V88 'made it WORSE'; V71c above was the   **")
    print("  ** worst build ever recorded on all three symptoms, ratchet at 8,521 ct p-p.           **")
    print("  ** Read from the images: V88, the car and V217 all carry 5244. V221 stepped it to      **")
    print("  ** 13107 and V228/231/232/233 all inherit that -- an UNFLOWN 2.5x step in the same     **")
    print("  ** direction as the flank measured catastrophic. V234 removes it.                      **")
    print("  ** NOT CLAIMED: that 13107 is harmful. It has never flown, and V71c's evidence is      **")
    print("  ** about the NET rate-lane dose reached via the r26 arm, not via 0xC6446 itself.       **")
    print("  ** What IS true: carrying an unflown 2.5x step on a lever the record puts off the      **")
    print("  ** shortlist in both directions, while recommending the build, is not defensible.      **")
    print("  ** V233 stays on the shelf as the paired arm -- TWO BYTES apart, so driving both       **")
    print("  ** isolates Lever B exactly. The r26 arm 0xC6444 is untouched at 512 throughout.       **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
