#!/usr/bin/env python3
r"""
V198 -- PROBE THE BIGGEST 8 Hz EXCITER.  Base = V196.  3 bytes, telemetry only.

WHY THIS TARGET AND NOT V197's
------------------------------
The aggregator exciter map is now complete -- 6 LIVE, 4 dead, 0 unidentified -- and it corrected an
earlier count of mine.  Two terms the decompiler had named iVar21/iVar16 are stored by the
aggregator's own tail:

    *(short *)(gp - 0x6adc) = iVar21;      *(short *)(gp - 0x6ada) = iVar16;

** they are the r26 and r24 RATE LANES **, LIVE, with 8192 clamps.  Ranking the live exciters by the
authority a clamp permits, and by whether they carry energy at 8 Hz:

    gp-0x6b86  12288  biquad output   -- carries the LKAS command, a 1-5 Hz low-pass
    gp-0x6b4c  10240  11-slot sum     -- low frequency
    gp-0x6ada   8192  r24 RATE LANE   -- omega^1, LIVE at 8 Hz          <-- THIS PROBE
    gp-0x6adc   8192  r26 RATE LANE   -- omega^1, LIVE at 8 Hz
    gp-0x6bbe   2048  viscous         -- omega^1                        <-- what V197 probed
    gp-0x6b26   1024  inertia (511)   -- omega^2                        <-- what V196 halves

=> the rate lanes carry ** 4x the viscous term's clamp and 8x the inertia term's **, and they are the
   biggest competitors to the term V196 halves.  Measuring the largest candidate first is worth more
   than measuring the second-largest.  ** V198 supersedes V197. **

The record also designates this exact cell as a telemetry target:  "both inline lanes are mirrored
to RAM and nothing reads them -- gp-0x6ada (r24) / gp-0x6adc (r26), post-clamp => free
zero-blast-radius telemetry."  Reading it costs nothing and disturbs nothing.

WHAT V198 DOES
--------------
Repoints the CAN 427 probe from gp-0x6ac0 onto gp-0x6ada.  Every V196 control cell is carried
unchanged; this adds an instrument only.

    0x55DF2  hw2 of `ld.h disp, gp, r6`   0x9540 (-0x6AC0)  ->  0x9526 (-0x6ADA)
    0x55E10  the pack shift               sar 4 (0xA4)      ->  sar 5 (0xA5)

THE SHIFT IS SIZED TO THE SOURCE, AS ALWAYS
-------------------------------------------
gp-0x6ada is SIGNED and the aggregator clamps it to +-8192, so sar 5 fits it in the 10-bit field
with the sign intact and 2x headroom before aliasing:

    positive x (0..8192)    -> raw    0 ..  256
    negative x (-8192..-1)  -> raw  768 .. 1023
    decode:  x = (raw < 512 ? raw : raw - 1024) * 32
    resolution 32 counts, unambiguous for |x| <= 16352

(V194 used sar 6 for gp-0x6c2c, which spans the full int16; V197 used sar 3 for a +-2048 source.
The shift is a property of the SOURCE.  Using the wrong one either wraps the sign or throws away
resolution.)

WHAT IT ANSWERS IN ONE DRIVE
----------------------------
    r24's 8 Hz content >> the inertia term's  -> V196 aims at a MINOR exciter.  The rate lanes are
                                                where a bigger lever belongs -- and unlike every
                                                other candidate they have a MEASURED on-car
                                                dose-response history (V62's sar x2: "18-22 Hz down
                                                8-42x"; V88's Lever B: "grinding FIXED on-car").
    comparable or smaller                     -> V196 is aimed correctly and the omega^2 weighting
                                                is carrying the work despite the small clamp.
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
WRITE_MODE = os.environ.get("ACCORD_V198_WRITE", "").strip().lower()
BASE_NAME = "_v196_V196-V195BASE-ENGAGED-INERTIA-HALF-DOSE_plain_image.bin"
BASE_SHA = "f904e43a1f4ccb94e81204dbecd93982049a024b95e48bd1c2c43852a7edec8e"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
ACCEL_FLAG = 0xC64AE
OSC_FALLBACK = 0xC640A
NORM_X, NORM_Y = 0xC6936, 0xC693E
HYST = 0xC64DD
NEW_HYST = 100
PROBE_HW2, PROBE_SHIFT = 0x55DF2, 0x55E10
NEW_DISP, NEW_SAR = (-0x6ADA) & 0xFFFF, 5
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
               0x55DF2: ("427 probe source gp-0x6ada, the r24 lane (V198)", 0x9526)}
CARRIED_B = {0xC40DC: ("accel alpha -> Honda (V179)", 22),
             0x55E10: ("packer sar 5 (V198)", 0xA5)}
PTR_I = 0xCBE74
HONDA_Y = (-9830, -5734, -1966)
HALF_Y = (-4915, -2867, -983)

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
    print("  V198 -- REMOVE THE FactorC m27 RELAY WE CREATED   (base V188)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V196 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE PROBE AS IT STANDS (V183 base)")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    old_disp = struct.unpack_from("<H", base, PROBE_HW2)[0]
    print(f"      0x{PROBE_HW2:05X} hw2 = 0x{old_disp:04X}  -> gp{old_disp - 0x10000:+d}"
          f" (= gp-0x{0x10000 - old_disp:04X})")
    print(f"      0x{PROBE_SHIFT:05X} shift byte = 0x{base[PROBE_SHIFT]:02X}"
          f"  -> sar {base[PROBE_SHIFT] & 0x1F}")
    check(old_disp == 0x9540, "the base carries V183's gp-0x6ac0 probe (0x9540)")
    check(base[PROBE_SHIFT] & 0x1F == 4, "the base carries sar 4")

    print("\n  [3] THE EDIT -- repoint onto the r24 RATE LANE, and re-size the shift")
    attributed = set()
    struct.pack_into("<H", code, PROBE_HW2, NEW_DISP)
    attributed |= {PROBE_HW2, PROBE_HW2 + 1}
    code[PROBE_SHIFT] = (base[PROBE_SHIFT] & ~0x1F) | NEW_SAR
    attributed.add(PROBE_SHIFT)
    d = struct.unpack_from("<H", code, PROBE_HW2)[0]
    print(f"      0x{PROBE_HW2:05X}  0x{old_disp:04X} -> 0x{d:04X}   (gp-0x{0x10000 - d:04X})")
    print(f"      0x{PROBE_SHIFT:05X}  sar {base[PROBE_SHIFT] & 0x1F} -> sar"
          f" {code[PROBE_SHIFT] & 0x1F}")
    check(0x10000 - d == 0x6ADA, f"the probe now reads gp-0x6ADA, the r24 rate lane (hw2 0x{d:04X})")
    check((0x10000 - d) % 2 == 0, "the displacement is EVEN, as ld.h requires")
    check(code[PROBE_SHIFT] & 0x1F == NEW_SAR, f"the pack shift is sar {NEW_SAR}")

    print("\n  [4] THE 10-BIT FIELD CARRIES THE SIGN CLEANLY AT sar 5")
    def pack(x):
        return ((x & 0xFFFF) >> NEW_SAR) & 0x3FF

    def unpack(r):
        return (r if r < 512 else r - 1024) * (1 << NEW_SAR)
    for x in (0, 32, 2048, 8192, -32, -2048, -8192):
        r = pack(x)
        print(f"        x = {x:+7d}  -> raw {r:4d} -> decoded {unpack(r):+7d}")
    for x in (0, 32, 2048, 8192, -32, -2048, -8192):
        check(abs(unpack(pack(x)) - x) <= (1 << NEW_SAR),
              f"x={x:+7d} round-trips to {unpack(pack(x)):+7d} within one LSB ({1 << NEW_SAR})")
    CL = 8192
    check(pack(CL) < 512 and pack(-CL) >= 512,
          f"the +-{CL} writer clamp maps to raw {pack(CL)} / {pack(-CL)} -- sign intact, no aliasing")

    print("\n  [5] V196 LEVERS CARRIED, AND WHAT IS DELIBERATELY ABSENT")
    check(code[0xC64DD] == 50, "0xC64DD dwell is Honda 50 -- V193s widening NOT carried")
    check(s16(code, 0xC640A) == -8192, "0xC640A oscillation fallback is Honda -8192")
    check(code[0xC64AE] == 1, "0xC64AE the 2nd accel term is Honda-enabled (V190 not carried)")
    p26 = u32(code, 0xCBE74 + 4 * 26)
    n26 = s16(code, p26)
    Y26 = [s16(code, p26 + 2 + 2 * n26 + 2 * i) for i in range(n26)]
    check(Y26 == [-4915, -2867, -983], f"engaged inertia Y = {Y26} -- V196s half dose CARRIED")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V196")
    m194, _ = resp(code, 19.40)
    check(m194 < 0.05, f"notch still at 19.40 Hz, |H| = {m194:.5f}")

    print("\n  [10] EVERY CARRIED LEVER IS ASSERTED")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        check(u16(code, off) == want, f"0x{off:05X} {nm} CARRIED ({want})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED (0x{want:02X})")
    for m, want, lbl in ((26, HALF_Y, "V196s HALF dose"), (27, HONDA_Y, "Honda")):
        p = u32(code, PTR_I + 4 * m)
        n = s16(code, p)
        Y = tuple(s16(code, p + 2 + 2 * n + 2 * i) for i in range(3))
        check(Y == want, f"inertia m{m} Y = {Y} -- {lbl}, CARRIED")
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
    check(len(pay) <= 4, f"{len(pay)} payload bytes (<= 4: hw2 + shift)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V198 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V198-V196BASE-PROBE-THE-R24-RATE-LANE"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v198_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V198_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V196 + the 427 probe on gp-0x6ada, the r24 lane: the BIGGEST 8 Hz exciter. **")
    print("  ** Decode: x = (raw<512 ? raw : raw-1024) * 32.  Clamp +-8192 = raw 256/768. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
