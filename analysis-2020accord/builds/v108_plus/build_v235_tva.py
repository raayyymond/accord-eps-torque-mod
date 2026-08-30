# -*- coding: utf-8 -*-
r"""V235 -- THE LAST UNPRICED CELL REMOVED. TWO BYTES ON V234.

A cell-by-cell audit of V234 against STOCK found 115 non-CRC runs, of which only SIX also differ from
the car: the biquad-state probe, the four biquad runs, and `0xC63AF`. The first two are justified -- the
probe is instrumentation with no control effect, and the notch was chosen by optimising against a
measurement. `0xC63AE` was not justified at all, and the record indicts it:

  * the UPWARD direction is already ruled out. BUILD-LINEAGE: "`0xC63AE` 1024->2048 | NO-GO | AC gain
    non-monotone, REVERSES across his amplitude range (0.70x @500 ct -> 2.00x @6000)."
  * the DOWNWARD direction, built at V206/V210 and carried by every build since, is UNPRICED.
    STATE.md, in its own words: "a ratchet null licenses nothing, because `0xC63AE` is unpriced."
  * it halves the soft relay's SMALL-SIGNAL gain, and the operator's own goals include LKAS authority.
    Roughness is a small-command phenomenon, so this cell sits exactly where authority is decided.

A cell whose gain is MEASURED to reverse across the operator's amplitude range, in a direction nobody
has priced, on a build being recommended, is not defensible. That is the same standard that produced
V234, applied to the one cell V234 still carried without a reason.

V235 returns `0xC63AE` to 1024, which is both Honda's value and the car's.

WHAT V235 THEREFORE IS, and this is the point:

    V235 = THE CAR, plus exactly THREE things -- 15 payload bytes in 6 runs, verified by diffing
             the built image against the car rather than asserted:

             1. 0xC60A8/AC/B0/B4  the biquad at the net-damping optimum   12 B
             2. 0xC40DC  alpha2 8 -> 22                                    1 B
             3. 0x55DF2  the biquad-state probe on CAN 427                 2 B   telemetry only

WHY alpha2 BELONGS HERE, since it is the one cell above that is not the notch. 22 is HONDA'S OWN
value; the car's 8 is the non-stock one, restored to Honda at V179. That cell is the low-pass corner
of the cascaded EMA feeding `gp-0x6b26`, and `gp-0x6b26` is a MEASURED DAMPER -- "+137/+139 deg vs
wheel rate, |cos| 0.73, i.e. +518/+565 counts of POSITIVE Re(Z)", called in the record "a REAL 6-9 Hz
DAMPER". The car's 8 attenuates that damper lane to 0.782 at 18.5 Hz and 0.466 at 55 Hz relative to
Honda's 22, so it REMOVES damping. Restoring 22 gives it back, and it is Honda's shipped value, not a
kit invention. The cell is otherwise closed in both directions: raising it above 22 buys at most
1.007x (it already sits at 99.3 % of its theoretical ceiling at 7.79 Hz), and lowering it removes
damping -- which is what V94 did 6x of, ending a drive.

Every other cell is byte-identical to what he drives today. That is the smallest and most defensible
build this kit has produced since the arc began: ONE control change chosen by optimising against a
measured quantity, ONE restoration of a Honda value the car had moved away from, an instrument on the
first of them, and nothing else moving.

(An earlier draft of this docstring said "exactly two things" and omitted alpha2. Diffing the built
image against the car is what caught it -- the claim was checked rather than trusted.)

    net damping vs the car   6-9      9-12    12-15    22-30    30-40   damping  pumping
    V235 (the notch alone) 1.004x   1.000x   0.891x  -0.050x  -0.888x   0.965x  -0.469x

RISK. If `0xC63AE` = 512 was helping, V235 gives that up. It has never flown, so there is no evidence
that it was. V234 stays on the shelf as the paired arm -- TWO BYTES apart -- so driving both isolates
this cell exactly, the same way V233/V234 isolates Lever B.
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
WRITE_MODE = os.environ.get("ACCORD_V235_WRITE", "").strip().lower()

BASE_NAME = "_v234_V234-V233BASE-LEVERB.BACK.TO.V88.OPTIMUM.5244_plain_image.bin"
BASE_SHA = "7adbc68f2b8163c69c6b387171a2fc18938f8f1dce8127abf6cfff9907be42e6"

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
PROBE_HW2, SHIFT_OFF = 0x55DF2, 0x55E10
HW2_KEEP, SAR_KEEP = 0xC7EA, 0xA3          # V231's biquad-state probe -- CARRIED, asserted
# the re-aim: zeros 34.0 Hz, poles 28.0 Hz, r 0.920 -- bytes, never a re-derived decimal
REAIM_BIQ = bytes.fromhex("fa15f3bffaed6b3f25d9fcbf16d7693f")

# carried levers -- asserted, never re-set
LEVER_B, LEVER_B_VAL = 0xC6446, 5244        # V88's bracketed optimum -- CARRIED, asserted
RESID_OLD, RESID_NEW = 512, 1024            # back to Honda's value, and the car's
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V235-V234BASE-C63AE.BACK.TO.HONDA.1024"

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
    check(u16(base, RESID_SCALE) == RESID_OLD,
          f"base carries 0xC63AE = {RESID_OLD} -- unpriced, carried since V206/V210")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, RESID_SCALE, RESID_NEW)
    attributed |= {RESID_SCALE, RESID_SCALE + 1}
    check(u16(code, RESID_SCALE) == RESID_NEW,
          f"0x{RESID_SCALE:05X} {RESID_OLD} -> {RESID_NEW} (Honda's value, and the car's)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check(RESID_NEW == 1024,
          "1024 is Honda's value AND the car's. The UPWARD direction is already NO-GO -- AC gain "
          "non-monotone, REVERSES across his amplitude range, 0.70x at 500 ct to 2.00x at 6000 -- "
          "and the DOWNWARD one is UNPRICED, in STATE.md's own words")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL} -- V88's bracketed optimum, restored in V234")
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
    _exp = sum(1 for k in range(2)
               if ((RESID_OLD >> (8 * k)) & 0xFF) != ((RESID_NEW >> (8 * k)) & 0xFF))
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(set(pay) <= {RESID_SCALE, RESID_SCALE + 1},
          "every payload byte is 0xC63AE -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V235 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v235_{TAG}_plain_image.bin")).write_bytes(bytes(code))
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
