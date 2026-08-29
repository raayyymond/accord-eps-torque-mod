#!/usr/bin/env python3
r"""
V192 -- MAKE HONDA'S OWN OSCILLATION RESPONSE WORK AT LOW INDEX.  Base = V191.  Four halfwords.

THE GAP
-------
FUN_00035b20 switches the slew limit gp-0x69a0 between two curves on the hard-reversal counter:

    NORMAL      (counter < 5)   X = [ 320, 1600, 3200,  4480]   Y = [358, 358, 461, 512]
    OSCILLATING (counter >= 5)  X = [ 640, 3200, 6400, 12800]   Y = [358, 307, 307, 307]
                                                                     ^^^ IDENTICAL

** At the LOW index the two curves are the same (358), so Honda's oscillation response provides NO
tightening there at all. **  It only bites once the index climbs -- and the breakpoints on the
oscillating curve are stretched 2x, which pushes the tightening even further out.

WHAT V192 DOES
--------------
Applies Honda's OWN tightening ratio once more.  Honda already chose 512 -> 307 at the high end,
a factor of 0.60, as its response to detected oscillation.  V192 scales the whole oscillating curve
by that same 0.60:

    Y = [358, 307, 307, 307]  ->  [215, 184, 184, 184]

so the slew limit is tightened across the entire index range, including the low end where the
detector currently does nothing.

WHY THIS IS A SAFER LEVER THAN A SIGN BET
-----------------------------------------
    * ** PROVABLY INERT IN NORMAL DRIVING **: this curve is read ONLY on the counter >= 5 branch.
      Below saturation the NORMAL curve is used and is untouched.  No steering-feel change, no LKAS
      authority change, by construction.
    * ** IT PUSHES THE DIRECTION HONDA ALREADY CHOSE. **  Honda tightens the slew limit when it
      detects oscillation; V192 tightens it more.  This is not a polarity gamble like V190/V191 --
      the sign is established by Honda's own two curves.
    * gp-0x69a0 is a RATE limit on the boost-table walk in FUN_000352b4
      (delta = ((step * limit * 4) >> 12)), so lowering it slows how fast the assist may change
      DURING a detected oscillation -- which is what damping an oscillation means.
    * four halfwords, cal-only, no cave.

WHAT TO WATCH FOR
-----------------
A slew limit that is too tight during an event could feel like a brief HESITATION rather than a
ratchet.  That is a different symptom, not a worse one, and it is pre-registered on the card.
"""
import hashlib
import math
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
WRITE_MODE = os.environ.get("ACCORD_V192_WRITE", "").strip().lower()
BASE_NAME = "_v191_V191-V190BASE-OSCILLATION-FALLBACK-ZEROED_plain_image.bin"
BASE_SHA = "82ce1db4e73099377c61a78c1b5033b5ca3ba3368062761e8836c709b0c29f4b"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
ACCEL_FLAG = 0xC64AE
OSC_FALLBACK = 0xC640A
NORM_X, NORM_Y = 0xC6936, 0xC693E
OSC_X, OSC_Y = 0xC6912, 0xC691A
FACTORC_PTR = 0xC9E9C
Y0_ADDR = 0xD77EE
BIQUAD = (A8_OFF, AC_OFF, B0_OFF, B4_OFF)

# --- THE SPEC IS THE FORMULA, NEVER A TYPED DECIMAL --------------------------------------------
# A 6-dp decimal does not round-trip a float32; three agents once produced three byte strings for
# one coefficient, none mis-encoded -- they had encoded three DIFFERENT NUMBERS.  So the two design
# parameters are exact, everything else is derived, and every assertion below is checked against the
# ENCODED float32 read back out of the image -- not against these Python doubles.
SEC_FS = 1000.0
F0 = 19.40         # notch centre, Hz -- ON THE GRIND, minimax over 67 routes
RP = 0.9300        # pole radius     -- WIDE: 19 Hz is far from openpilot, so we can afford it

FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
CARRIED_U16 = {0xC40D2: ("K1 -> Honda (V177)", 102),
               0xC63A6: ("w[3] halved (V181)", 512),
               0x55DF2: ("427 probe source gp-0x6ac0 (V183)", 0x9540)}
CARRIED_B = {0xC40DC: ("accel alpha -> Honda (V179)", 22),
             0x55E10: ("packer sar 4 (V183)", 0xA4)}
PTR_I = 0xCBE74
HONDA_Y = (-9830, -5734, -1966)

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


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def design():
    """The four coefficients, from the two design parameters.  Doubles here; the image gets f32."""
    th = 2.0 * math.pi * F0 / SEC_FS
    b0 = -2.0 * math.cos(th)
    a8 = -2.0 * RP * math.cos(th)
    ac = RP * RP
    b4 = (1.0 + a8 + ac) / (2.0 + b0)
    return a8, ac, b0, b4


def resp(img, fr):
    """|H| and phase AT A FREQUENCY, computed from the ENCODED float32 in the image."""
    import cmath
    z = cmath.exp(2j * math.pi * fr / SEC_FS)
    h = (f32(img, B4_OFF) * (z * z + f32(img, B0_OFF) * z + 1.0)
         / (z * z + f32(img, A8_OFF) * z + f32(img, AC_OFF)))
    return abs(h), math.degrees(cmath.phase(h))


def build():
    print("=" * 102)
    print("  V192 -- REMOVE THE FactorC m27 RELAY WE CREATED   (base V188)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V191 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE TWO SLEW CURVES, READ FROM THE IMAGES")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()

    def rd(b, off, n=4):
        return [struct.unpack_from("<H", b, off + 2 * i)[0] for i in range(n)]

    XN, YN = rd(base, NORM_X), rd(base, NORM_Y)
    XO, YO = rd(base, OSC_X), rd(base, OSC_Y)
    print(f"      NORMAL      X {XN}   Y {YN}")
    print(f"      OSCILLATING X {XO}   Y {YO}")
    check(YN[0] == YO[0],
          f"the two curves are IDENTICAL at the low index ({YN[0]}) -- Honda's oscillation"
          " response gives NO tightening there")
    ratio = YO[-1] / YN[-1]
    print(f"      Honda's own high-end tightening ratio: {YN[-1]} -> {YO[-1]} = {ratio:.3f}")
    check(0.0 < ratio < 1.0, f"Honda TIGHTENS on detection (ratio {ratio:.3f} < 1) -- the"
                             " direction of this edit is set by Honda, not by us")

    print("\n  [3] THE EDIT -- scale the OSCILLATING curve by Honda's own ratio")
    attributed = set()
    NEWY = [max(1, int(round(v * ratio))) for v in YO]
    for i, v in enumerate(NEWY):
        struct.pack_into("<H", code, OSC_Y + 2 * i, v)
        attributed |= {OSC_Y + 2 * i, OSC_Y + 2 * i + 1}
    print(f"      0x{OSC_Y:05X}  {YO} -> {rd(code, OSC_Y)}")
    check(rd(code, OSC_Y) == NEWY, "the oscillating Y curve is written")
    check(all(a < b for a, b in zip(rd(code, OSC_Y), YO)),
          "every point is STRICTLY TIGHTER than before")
    check(rd(code, OSC_Y)[0] < rd(code, NORM_Y)[0],
          f"the low index is now TIGHTER than normal ({rd(code, OSC_Y)[0]} <"
          f" {rd(code, NORM_Y)[0]}) -- the gap is closed")

    print("\n  [4] THE NORMAL CURVE IS UNTOUCHED -- provably inert on a calm road")
    check(rd(code, NORM_X) == XN and rd(code, NORM_Y) == YN,
          f"NORMAL curve byte-identical (X {XN}, Y {YN})")
    check(rd(code, OSC_X) == XO, f"oscillating X breakpoints unchanged {XO}")
    print("      the oscillating curve is read ONLY on the gp-0x671a >= 5 branch of FUN_00035b20,")
    print("      so below saturation this edit cannot be reached at all.")

    print("\n  [5] EVERY V191 LEVER IS UNTOUCHED")
    check(s16(code, 0xC640A) == 0, "0xC640A oscillation fallback still ZEROED (V191)")
    check(code[0xC64AE] == 0, "0xC64AE the 2nd accel term still DISABLED (V190)")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V191")
    m194, _ = resp(code, 19.40)
    check(m194 < 0.05, f"notch still at 19.40 Hz, |H| = {m194:.5f}")

    print("\n  [10] EVERY CARRIED LEVER IS ASSERTED")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        check(u16(code, off) == want, f"0x{off:05X} {nm} CARRIED ({want})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED (0x{want:02X})")
    for m in (26, 27):
        p = u32(code, PTR_I + 4 * m)
        n = s16(code, p)
        Y = tuple(s16(code, p + 2 + 2 * n + 2 * i) for i in range(3))
        check(Y == HONDA_Y, f"inertia m{m} Y = {Y} -- the dose revert CARRIED")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- no cave change, not the bricking class")

    print("\n  [11] CRC RECOMPUTATION")
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

    print("\n  [12] FULL BYTE DIFF vs V185")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) <= 8, f"{len(pay)} payload bytes (<= 8: four halfwords)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V192 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V192-V191BASE-OSC-SLEW-CURVE-TIGHTENED"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v192_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V192_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V191 + the OSCILLATING slew curve tightened by Hondas own 0.60 ratio. **")
    print("  ** Provably inert in normal driving. Direction set by Hondas own two curves. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
