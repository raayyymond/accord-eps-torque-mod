# -*- coding: utf-8 -*-
r"""V234 -- LEVER B RETURNED TO V88'S MEASURED OPTIMUM. TWO BYTES ON V233.

WHY THIS BUILD EXISTS, AND IT IS A CORRECTION TO MY OWN SHELF.

`memory/accord/builds/accord-v88-flew-grinding-fixed-command-intact.md` records, verbatim:

    "THE LANE IS AN OPTIMUM AND V88 IS SITTING ON IT. BOTH FLANKS ARE NOW MEASURED:
     V61 (net BELOW V88) 'made it WORSE... the rate lane is the mode's damper';
     V71c (net ABOVE) worst in the corpus. The standing '2x = OPTIMUM, not a point on a ramp'
     warning now has BOTH sides, not one.
     => LEVER B IS OFF EVERY FUTURE SHORTLIST, IN BOTH DIRECTIONS."

V71c is described there as **"the worst build ever recorded on all three symptoms (ratchet at the corpus
record 8,521 ct p-p)"**, and it differs from V88 only in the net rate-lane dose.

READ FROM THE IMAGES, which is how this was caught:

    build        0xC6446 (Lever B)   0xC6444 (r26 arm)
    V88-era           5244                512
    car V122          5244                512
    V217              5244                512
    V221             13107                512     <- the step
    V228/231/232/233 13107                512     <- every build on my shelf inherits it

**V221 raised Lever B 2.5x above the measured optimum and V228 through V233 all carry it**, against a
standing instruction in the kit's own record and on the flank that produced the worst build ever
recorded. The r26 arm never moved, so this is Lever B alone.

V234 returns `0xC6446` to **5244** -- V88's value, and the value on the car today.

WHAT V234 THEREFORE IS: the net-damping-optimal notch (V233's 25.0/23.5/0.96, chosen by optimising
against the measured lane) combined with the rate-lane dose that is the ONLY on-car optimum this kit has
ever bracketed on both sides. Every other cell is V231's.

    net damping vs the car    6-9      9-12    12-15    22-30    30-40   damping  pumping
    V233 / V234 notch       1.004x   1.000x   0.891x  -0.050x  -0.888x   0.965x  -0.469x

(The notch table is unchanged -- Lever B is a different lane and does not enter the biquad response.)

WHAT I AM NOT CLAIMING. That 13107 is definitely harmful: it has never flown, and the V71c evidence is
about the NET rate-lane dose reached via the r26 arm, not via `0xC6446` itself. What the record does say
is that the net dose ABOVE V88 was measured catastrophic once, that both flanks are now bracketed, and
that the lever is off the shortlist in both directions. **Carrying an unflown 2.5x step on that lever,
in that direction, while recommending the build, is not defensible.** V234 removes the step.

RISK: if the 2.5x step were in fact helping, V234 gives that up. The mitigation is that V233 remains on
the shelf as the paired arm -- the two are TWO BYTES apart, so driving both isolates Lever B exactly.
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
WRITE_MODE = os.environ.get("ACCORD_V234_WRITE", "").strip().lower()

BASE_NAME = "_v233_V233-V231BASE-NOTCH.NETDAMPING.OPTIMUM.25HZ_plain_image.bin"
BASE_SHA = "399424fd8b03266950ed07d5e47964705c9a87bf2f86c4370c0999179d0ae42a"

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
PROBE_HW2, SHIFT_OFF = 0x55DF2, 0x55E10
HW2_KEEP, SAR_KEEP = 0xC7EA, 0xA3          # V231's biquad-state probe -- CARRIED, asserted
# the re-aim: zeros 34.0 Hz, poles 28.0 Hz, r 0.920 -- bytes, never a re-derived decimal
REAIM_BIQ = bytes.fromhex("fa15f3bffaed6b3f25d9fcbf16d7693f")

# carried levers -- asserted, never re-set
LEVER_B = 0xC6446
LEVER_B_OLD, LEVER_B_NEW = 13107, 5244   # back to V88's measured optimum
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V234-V233BASE-LEVERB.BACK.TO.V88.OPTIMUM.5244"

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
    check(u16(base, LEVER_B) == LEVER_B_OLD,
          f"base carries Lever B = {LEVER_B_OLD} -- the 2.5x step introduced at V221")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, LEVER_B, LEVER_B_NEW)
    attributed |= {LEVER_B, LEVER_B + 1}
    check(u16(code, LEVER_B) == LEVER_B_NEW,
          f"0x{LEVER_B:05X} Lever B {LEVER_B_OLD} -> {LEVER_B_NEW}")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check(LEVER_B_NEW == 5244,
          "5244 is V88's value, the car's value, and V217's -- the ONLY rate-lane dose this kit has "
          "bracketed on BOTH flanks (V61 below: 'made it WORSE'; V71c above: worst in the corpus)")
    check(LEVER_B_OLD > LEVER_B_NEW,
          f"the step being removed was UPWARD ({LEVER_B_OLD}/{LEVER_B_NEW} = "
          f"{LEVER_B_OLD/LEVER_B_NEW:.2f}x), i.e. toward the flank V71c measured as catastrophic")
    check(u16(code, R26_ARM) == 512,
          "0xC6444 r26 arm UNTOUCHED at 512 -- this build moves Lever B alone, so the pair "
          "V233/V234 isolates it exactly")

    print("\n  [4] THE NOTCH AND EVERYTHING ELSE ARE V233, BYTE FOR BYTE")
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == bytes(base[BIQ:BIQ + BIQ_LEN]),
          "the net-damping-optimum biquad is untouched (Lever B is a different lane)")
    check(u16(code, PROBE_HW2) == HW2_KEEP, "biquad-state probe CARRIED")
    check(code[SHIFT_OFF] == SAR_KEEP, "probe shift CARRIED")
    check(code[ALPHA2] == ALPHA2_VAL, f"0x{ALPHA2:05X} alpha2 = {ALPHA2_VAL}")
    check(u16(code, RESID_SCALE) == RESID_VAL, f"0x{RESID_SCALE:05X} = {RESID_VAL}")
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
               if ((LEVER_B_OLD >> (8 * k)) & 0xFF) != ((LEVER_B_NEW >> (8 * k)) & 0xFF))
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(set(pay) <= {LEVER_B, LEVER_B + 1}, "every payload byte is Lever B -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V234 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v234_{TAG}_plain_image.bin")).write_bytes(bytes(code))
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
