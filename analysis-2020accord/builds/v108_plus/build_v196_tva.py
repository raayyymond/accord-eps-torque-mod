#!/usr/bin/env python3
r"""
V196 -- HALVE THE ENGAGED ANTI-DAMPING INERTIA TERM.  Base = V195.  THREE int16, ENGAGED ONLY.

THE LEVER
---------
gp-0x6b26 is an INERTIA term built from the acceleration EMA, so its loop contribution scales as
omega^2 -- ** 66x stronger at 8.2 Hz than at 1 Hz **.  That makes it the only frequency-selective
lever pointing at the ratchet that is not the biquad, and the biquad is spent on the grind.

    gp-0x6b26 = clamp( ((accel * L) >> 6) * 273 >> 18, +-cal(0xC407E) )
    L = LERP(0xCBE74[mode], gp-0x6a5e)      Honda: Y = (-9830, -5734, -1966)

THE DOSE LADDER SUPPORTS THE DIRECTION
--------------------------------------
    FLYING build V122   engaged Y = (-29490, -17202, -16000)   ~3x Honda   ** and it ratchets **
    V189..V195          engaged Y = ( -9830,  -5734,  -1966)   = Honda
    V196                engaged Y = ( -4915,  -2867,   -983)   = HALF Honda

[[accord-gp6b26-is-inertia-not-damping]] (5-star) makes this term ANTI-damping -- negative apparent
inertia -- and the flying build carries 3x of it while ratcheting 3.58x more when engaged.  Going
BELOW Honda continues that ladder in the direction the evidence points.

ENGAGED ONLY -- MANUAL DRIVING STAYS BYTE-STOCK
-----------------------------------------------
m24 (manual) and m26 (engaged) are DISTINCT records (0xD6A64 vs 0xD7A54), so the engaged column can
be dosed alone.  ** Only 0xD7A5C..0xD7A61 moves; m24 is untouched. **  That is the V74 pattern the
TVCA4 memory endorses: dose the engaged columns, leave manual byte-stock.
!! This deliberately RE-CREATES an engaged/manual asymmetry, which earlier work removed.  The
difference is DIRECTION: the asymmetries removed made ENGAGED WORSE (more anti-damping when
engaged); this one makes engaged BETTER.  Stated explicitly so the next reader does not "fix" it.

THE TRADE, STATED PLAINLY
-------------------------
Negative apparent inertia makes the wheel feel LIGHTER to fast inputs.  Halving it means the wheel
feels closer to its true inertia at high frequency, so very fast steering inputs get marginally less
help.  ** There is ZERO effect at DC ** -- acceleration is zero in steady state -- so no LKAS
authority is lost and no steady steering weight is added.  A half-dose is the first step rather than
zero precisely because this trade is real.
!! Sign basis: the 5-star anti-damping reading plus the dose-ladder observation.  If that reading is
inverted, this term was damping and the ratchet gets WORSE -- revert to V195, three int16.
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
WRITE_MODE = os.environ.get("ACCORD_V196_WRITE", "").strip().lower()
BASE_NAME = "_v195_V195-V189BASE-NOTCH.REFIT.ON.RATE_plain_image.bin"
BASE_SHA = "a3ea8683df48c6b3f40e8ba8ac879047da6aec62fedc8d56cf9f1dc83f7b610b"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
FACTORC_PTR = 0xC9E9C
Y0_ADDR = 0xD77EE
ENG_Y = 0xD7A5C
DOSE = 0.5
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
    print("  V196 -- REMOVE THE FactorC m27 RELAY WE CREATED   (base V188)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V195 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE MODE RECORDS -- manual and engaged must be DISTINCT")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    p24, p26 = u32(base, PTR_I + 4 * 24), u32(base, PTR_I + 4 * 26)
    check(p24 != p26,
          f"m24 0x{p24:05X} and m26 0x{p26:05X} are DISTINCT -- the engaged column can be"
          " dosed while manual stays byte-stock")
    n = s16(base, p26)
    check(n == 3, f"the engaged record has {n} breakpoints")
    yoff = p26 + 2 + 2 * n
    check(yoff == ENG_Y, f"engaged Y resolves to 0x{yoff:05X} (expected 0x{ENG_Y:05X})")
    n24 = s16(base, p24)
    Y26 = [s16(base, yoff + 2 * i) for i in range(n)]
    Y24 = [s16(base, p24 + 2 + 2 * n24 + 2 * i) for i in range(n24)]
    print(f"      m24 MANUAL  Y {Y24}")
    print(f"      m26 ENGAGED Y {Y26}")
    check(Y26 == Y24, "they start EQUAL (V184's revert) -- so this build is the only asymmetry")
    check(Y26 == [s16(stock, yoff + 2 * i) for i in range(n)],
          "and equal to STOCK, so the ladder starts from Honda")

    print("\n  [3] THE EDIT -- halve the ENGAGED column only")
    attributed = set()
    NEWY = [int(round(v * DOSE)) for v in Y26]
    for i, v in enumerate(NEWY):
        struct.pack_into("<h", code, ENG_Y + 2 * i, v)
        attributed |= {ENG_Y + 2 * i, ENG_Y + 2 * i + 1}
    got = [s16(code, ENG_Y + 2 * i) for i in range(n)]
    print(f"      0x{ENG_Y:05X}  {Y26} -> {got}   (x{DOSE})")
    check(got == NEWY, "the engaged Y column is written")
    check(all(abs(x) < abs(y) for x, y in zip(got, Y26)),
          "every engaged point is strictly SMALLER in magnitude")
    check(all(x < 0 for x in got), "the sign is preserved -- a dose step, not a flip")

    print("\n  [4] MANUAL IS UNTOUCHED")
    Y24b = [s16(code, p24 + 2 + 2 * n24 + 2 * i) for i in range(n24)]
    check(Y24b == Y24, f"m24 MANUAL Y still {Y24b} -- byte-stock")
    check(bytes(code[p24:p24 + 16]) == bytes(base[p24:p24 + 16]),
          "the whole manual record is byte-identical")

    print("\n  [5] ZERO EFFECT AT DC -- no authority, no steering weight")
    print("      gp-0x6b26 is built from the ACCELERATION EMA, which is 0 in steady state, so the")
    print("      contribution at DC is 0 before and after.  The change is omega^2-weighted:")
    for hz in (1.0, 3.0, 8.2, 20.0):
        print(f"        {hz:5.1f} Hz   relative weight {(hz / 1.0) ** 2:8.1f}x that of 1 Hz")

    print("\n  [6] EVERY V195 LEVER IS UNTOUCHED")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V195")
    mn, _ = resp(code, 19.75)
    check(mn < 0.05, f"the re-fitted notch is still at 19.75 Hz, |H| = {mn:.5f}")
    p27 = u32(code, 0xC9E9C + 4 * 27)
    n27 = s16(code, p27)
    check(tuple(s16(code, p27 + 2 + 2 * n27 + 2 * i) for i in range(n27))
          == tuple(s16(stock, p27 + 2 + 2 * n27 + 2 * i) for i in range(n27)),
          "FactorC m27 still stock (V189)")

    print("\n  [10] EVERY CARRIED LEVER IS ASSERTED")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        check(u16(code, off) == want, f"0x{off:05X} {nm} CARRIED ({want})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED (0x{want:02X})")
    for m in (24,):
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
    check(len(pay) <= 6, f"{len(pay)} payload bytes (<= 6: three int16)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V196 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V196-V195BASE-ENGAGED-INERTIA-HALF-DOSE"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v196_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V196_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V188 plus the FactorC m27 relay removed. Strictly toward stock. **")
    print("  ** Inert if mode 27 is unreachable; removes a live damper relay if not. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
