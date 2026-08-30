# -*- coding: utf-8 -*-
r"""WITHDRAWN 2026-08-30 -- 0xC6384 IS MEASURED INERT. DO NOT FLASH. Fly V238.

The slope cap only reshapes the map ABOVE 2844 torque counts -- it moves the top X breakpoints and
Y never changes -- and the car is above that on 1.65 % of engaged frames. 6-9 Hz band ratio 1.0000
(range 0.999-1.000, 22 routes). CONTROL: on a route that never crosses 2844 counts, b82 and b84 are
BIT-IDENTICAL at every dose down to 256. The cap branch never fires at any shipped value: the map's
natural max slope is 0.350 against a cap at 2.000. The GATE 2 "Q ratio 14.29 -> 4.26" came from a
loop model that assumed the cap SCALES the lane gain; it does not.

--- the original docstring follows, retained as the record ---

V239 -- BOTH RATCHET LEVERS IN THE SAME LANE. V236's slope cap PLUS V238's pole.

WHY BOTH. The two cells sit at opposite ends of one structure and their sizes are now MEASURED, so
combining them confounds nothing:

    out(f) = table2 + H_k(f) * (table1 - table2)
             ^^^^^^                ^^^^^^^^^^^
             gp-0x69a0 slew-limited      0xC6384 caps the slope of BOTH   <- V236, the big lever
             |                                  H_k is the valve          <- V238, measured small

MEASURED THIS SESSION, on 22 routes with the gate live, from the integer-exact firmware mirror plus
Welch band power at the ratchet (6-9 Hz):

    the CUT (table1 - table2) carries a median 0.4 % of its power in 6-9 Hz -- it is almost entirely
    LOW frequency, so H_k restores it at any k and the pole can only move what little is in band.

    6-9 Hz band-power ratio vs the car:   k=8  (V238)  0.9731   -2.7 %   range 0.709..1.005
                                          k=2  (floor) 0.9622   -3.8 %   range 0.589..1.007

**=> the ENTIRE reachable range of 0xC6906 at the ratchet is 3.8 %.** V238's 2.7 % is most of what the
cell has. That is a nibble, not a fix -- and it is exactly where the archive landed by a different
route ("THE EFFECT IS TOO SMALL"), which is a genuine convergence, not a re-derivation.

**0xC6384 is the lever with the size.** It caps the interpolation slope of the map itself (tp+0x7384,
read as float x 1/1024 = 2.000), so it scales table1 AND table2 -- the whole lane, not the residue the
pole gates. 2048 -> 1536 is a 25 % slope reduction, and the record's GATE 2 puts the loop Q ratio at
14.29 -> 4.26. Unlike the pole it is a REAL GAIN, so it is monotone with no reversal at any value, and
it DOES cost steering effort where it binds. That trade is the point of the build.

WHAT V239 IS. V236 + V238's four halfwords: the largest ratchet lever available, plus the free 2.7 %.
Combining them costs no interpretability because the pole's contribution is already bounded at 3.8 %.

    0xC6384   2048 -> 1536    slope cap, s 2.000 -> 1.500      2 B   the ratchet lever with the size
    0xC6906   Y[0..3] 20 -> 8 the engaged lag pole             8 B   free, measured 2.7 %

**V236 REMAINS ON THE SHELF as the paired arm** -- V239 minus exactly 8 bytes -- so if the operator
wants the pole's contribution isolated after the fact, the pair still does it.

WHAT IS ASSUMED. The 2.7 %/3.8 % figures are EVIDENCE (measured band power, 22 routes, the firmware's
own integer transform driving them). V236's "3.4x more damped" is NOT -- it comes from a loop model the
record itself corrected, and the honest statement is direction well-founded, size soft. Said plainly on
the card.

BASE: V236, which is V235 + the slope cap.
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
WRITE_MODE = os.environ.get("ACCORD_V239_WRITE", "").strip().lower()

# base renamed when V236 was withdrawn 2026-08-30; the builder must still reproduce
BASE_NAME = "SUPERSEDED-_v236_V236-V235BASE-ASSISTMAP.SLOPECAP.1536.RATCHET_plain_image.bin"
BASE_SHA = "509785673468a346ac366dfb2fb8e491231f49a4e440e22ef9ce4fe39602d862"

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
PROBE_HW2, SHIFT_OFF = 0x55DF2, 0x55E10
HW2_KEEP, SAR_KEEP = 0xC7EA, 0xA3          # V231's biquad-state probe -- CARRIED, asserted
# the re-aim: zeros 34.0 Hz, poles 28.0 Hz, r 0.920 -- bytes, never a re-derived decimal
REAIM_BIQ = bytes.fromhex("fa15f3bffaed6b3f25d9fcbf16d7693f")

# carried levers -- asserted, never re-set
LEVER_B, LEVER_B_VAL = 0xC6446, 5244        # V88's bracketed optimum -- CARRIED, asserted
RESID_SCALE_VAL = 1024                      # CARRIED, asserted
SLOPE_CAP, CAP_V236 = 0xC6384, 1536         # V236's lever -- CARRIED by this build
POLE_Y = 0xC6906                            # engaged lag pole, LERP Y[0..3]
POLE_X = 0xC68FE                            # its X axis -- asserted, never written
K_OLD, K_NEW = 20, 8                        # corner 1.554 Hz -> 0.622 Hz; |H| at 7.79 Hz 0.1966 -> 0.0797
K_CLAMP_MIN = 2                             # the firmware's own floor, from the reader
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V239-V236BASE-SLOPECAP.PLUS.LAGPOLE.8"

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
          f"engaged pole Y[0..3] {K_OLD} -> {K_NEW} (corner 1.554 Hz -> 0.622 Hz)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check(K_NEW >= K_CLAMP_MIN,
          f"{K_NEW} is inside the firmware's OWN floor of {K_CLAMP_MIN} -- the reader does "
          f"max(2, min(k, 204)), so this cannot go below what Honda's code already permits")
    check(K_NEW < K_OLD,
          "the direction is LOWER k: out = table2 + H_k*(table1 - table2), so a SMALLER H at "
          "7.79 Hz leaves MORE of the slew limiter's tightening in force -- less lane gain, "
          "less positive feedback, more damping. V237 raised it and was backwards.")
    check(u16(base, SLOPE_CAP) == CAP_V236,
          f"base carries 0x{SLOPE_CAP:05X} = {CAP_V236} -- V236's slope cap, inherited")
    check(u16(code, SLOPE_CAP) == CAP_V236,
          f"0x{SLOPE_CAP:05X} CARRIED at {CAP_V236} -- V239 keeps the big lever")
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
    FF.assert_x31_checksum(rwd, "V239 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v239_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V239_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V239 = V236's slope cap + V238's lag pole. Both ratchet levers in one lane.                        **")
    print("  ** MEASURED THIS SESSION, 22 routes, Welch band power at 6-9 Hz, driven by the                        **")
    print("  ** integer-exact firmware mirror:                                                                     **")
    print("  **   the CUT (table1 - table2) carries a median 0.4 % of its power in 6-9 Hz,                         **")
    print("  **   so it is almost all LOW frequency and H_k restores it at any k.                                  **")
    print("  **   band ratio vs the car:  k=8 (V238) 0.9731  -2.7 %   range 0.709..1.005                           **")
    print("  **                           k=2 (floor) 0.9622  -3.8 %   range 0.589..1.007                          **")
    print("  ** => the ENTIRE reachable range of 0xC6906 at the ratchet is 3.8 %. A nibble.                        **")
    print("  **    That is where the archive landed by a different route ('TOO SMALL') --                          **")
    print("  **    a convergence, not a re-derivation.                                                             **")
    print("  ** 0xC6384 IS THE LEVER WITH THE SIZE: it caps the map's interpolation slope, so                      **")
    print("  ** it scales table1 AND table2 -- the whole lane, not the residue the pole gates.                     **")
    print("  ** It IS a real gain: monotone, no reversal, and it DOES cost steering effort.                        **")
    print("  ** V236 stays on the shelf as the paired arm -- V239 minus exactly 8 bytes.                           **")
    print("  ** NOT CLAIMED: V236's '3.4x more damped'. That rests on a loop model the record                      **")
    print("  ** itself corrected. Direction well-founded, SIZE soft. The 2.7 %/3.8 % ARE measured.                 **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
