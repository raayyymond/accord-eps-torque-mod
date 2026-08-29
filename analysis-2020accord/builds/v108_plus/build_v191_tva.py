#!/usr/bin/env python3
r"""
V191 -- STOP FEEDING THE OSCILLATION ONCE THE FIRMWARE HAS DETECTED IT.  Base = V190.  ONE halfword.

THE MECHANISM
-------------
gp-0x671a is Honda's own HARD-REVERSAL COUNTER -- a built-in oscillation detector, clamped at
CEIL = 5 (cal 0xC64FA).  FUN_00036c12 branches on it:

    if (gp-0x671a < 0xFF && gp-0x67f4 == 1) {
        if (gp-0x671a < cal(0xC64FD)=5)  L = LERP(0xCBE74[mode], gp-0x6a5e);   // normal
        else                             L = cal(0xC640A) = -8192;             // OSCILLATING
    } else                               L = cal(0xC640C) = -3277;
    gp-0x6b26 = clamp( ((accel * L) >> 6) * 273 >> 18, +-cal(0xC407E) )

So the ANTI-DAMPING acceleration gain is switched by an oscillation detector, and the value it
switches TO is a fixed -8192.  Against the LERP's own range:

    LERP Y  = [-9830, -5734, -1966]   (Honda; X = [0, 1280, 5760] on gp-0x6a5e)
    fallback  -8192                   ** 4.2x STRONGER than the LERP's weak end **

=> once sustained oscillation is DETECTED, the firmware can make the anti-damping term dramatically
   STRONGER than it was.  That is positive feedback on the thing it just detected, and it is a
   plausible reason the ratchet SUSTAINS instead of decaying.

WHY THIS LEVER IS UNUSUALLY WELL-SHAPED
---------------------------------------
    * ** it is CONDITIONAL ON THE DETECTOR **.  With the counter below 5 -- i.e. all normal driving
      -- this cal is not read at all, so the edit is provably inert outside an oscillation event.
      No steering-feel change, no LKAS authority change, nothing to notice on a calm road.
    * it acts EXACTLY during the symptom, which is the one time we want the term gone.
    * one halfword, cal-only, no cave.
    * ** never touched in the whole post-V38 arc. **

WHAT V191 DOES
--------------
0xC640A  -8192 -> 0.  When Honda's own detector says the wheel is oscillating, the anti-damping
acceleration term is removed instead of boosted.  Everything in V190 is carried and asserted.

THE SIGN, STATED HONESTLY
-------------------------
This shares V190's sign basis: gp-0x6b26 is anti-damping per the kit's 5-star result
[[accord-gp6b26-is-inertia-not-damping]], supported by the flying build carrying 3x its dose while
ratcheting 3.58x more engaged.  ** If that reading is inverted, this term was DAMPING and zeroing it
during an oscillation would make the ratchet worse. **  Same pre-registered revert applies.
!! Note this build does NOT depend on gp-0x6a5e's value during the ratchet: zeroing the fallback
removes the term outright, so the edit is unambiguous whether or not -8192 was a "boost" at the
operating point.
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
WRITE_MODE = os.environ.get("ACCORD_V191_WRITE", "").strip().lower()
BASE_NAME = "_v190_V190-V189BASE-ACCEL-REFERENCE-TERM-OFF_plain_image.bin"
BASE_SHA = "ab75a383fad5c65ad03645daffa8d3a93d15916040b438d3a01275e82196744f"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
ACCEL_FLAG = 0xC64AE
OSC_FALLBACK = 0xC640A
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
    print("  V191 -- REMOVE THE FactorC m27 RELAY WE CREATED   (base V188)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V190 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE DETECTOR AND ITS FALLBACK, READ FROM THE IMAGES")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    print(f"      0xC64FA CEIL (counter clamp)          = {stock[0xC64FA]}")
    print(f"      0xC64FD LERP-vs-fallback threshold    = {stock[0xC64FD]}")
    print(f"      0xC640A fallback L when OSCILLATING   = {s16(base, OSC_FALLBACK)}")
    print(f"      0xC640C fallback L when outer gate off= {s16(base, 0xC640C)}")
    check(stock[0xC64FA] == stock[0xC64FD],
          f"the counter CEIL ({stock[0xC64FA]}) equals the branch threshold ({stock[0xC64FD]})"
          " -- the fallback is reached exactly at saturation")
    p = u32(base, 0xCBE74 + 4 * 26)
    n = s16(base, p)
    Y = [s16(base, p + 2 + 2 * n + 2 * i) for i in range(n)]
    print(f"      LERP Y (mode 26) = {Y}")
    check(abs(s16(base, OSC_FALLBACK)) > abs(Y[-1]),
          f"the fallback |{s16(base, OSC_FALLBACK)}| EXCEEDS the LERP weak end |{Y[-1]}|"
          f" by {abs(s16(base, OSC_FALLBACK)) / abs(Y[-1]):.1f}x -- detecting oscillation can"
          " STRENGTHEN the anti-damping term")

    print("\n  [3] THE EDIT -- one halfword")
    attributed = set()
    before = s16(code, OSC_FALLBACK)
    struct.pack_into("<h", code, OSC_FALLBACK, 0)
    attributed |= {OSC_FALLBACK, OSC_FALLBACK + 1}
    print(f"      0x{OSC_FALLBACK:05X}  {before} -> {s16(code, OSC_FALLBACK)}")
    check(s16(code, OSC_FALLBACK) == 0,
          "when the detector saturates, the anti-damping term is now REMOVED, not boosted")
    check(s16(code, 0xC640C) == s16(base, 0xC640C),
          f"the OTHER fallback 0xC640C is UNCHANGED ({s16(code, 0xC640C)})")

    print("\n  [4] PROVABLY INERT OUTSIDE AN OSCILLATION EVENT")
    print("      cal 0xC640A is read ONLY on the gp-0x671a >= 5 branch of FUN_00036c12.")
    print("      gp-0x671a is the hard-reversal counter, clamped at CEIL=5, so below saturation")
    print("      this cell is never loaded => no steering-feel or LKAS-authority change on a")
    print("      calm road, by construction rather than by measurement.")
    check(stock[0xC64FD] == 5, "threshold is 5, so the branch needs a SATURATED counter")

    print("\n  [5] THE LERP PATH IS STILL HONDA'S, AND STILL LIVE")
    check(tuple(Y) == tuple(s16(stock, p + 2 + 2 * n + 2 * i) for i in range(n)),
          f"mode-26 LERP Y = {Y} = stock (V184's revert carried, and it IS reached when"
          " the counter is below 5 -- i.e. in all normal driving)")

    print("\n  [6] EVERY V190 LEVER IS UNTOUCHED")
    check(code[0xC64AE] == 0, "0xC64AE the 2nd accel term still DISABLED (V190)")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V190")
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
    check(len(pay) <= 2, f"{len(pay)} payload bytes (<= 2: one halfword)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V191 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V191-V190BASE-OSCILLATION-FALLBACK-ZEROED"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v191_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V191_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V190 + the OSCILLATION-DETECTED anti-damping fallback ZEROED. **")
    print("  ** Provably inert until Hondas own detector saturates. Sign shares V190s basis. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
