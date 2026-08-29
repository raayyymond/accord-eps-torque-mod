#!/usr/bin/env python3
r"""
V189 -- REMOVE AN ENGAGED-ONLY RELAY THIS KIT CREATED BY ACCIDENT.  Base = V188.  ONE int16.

WHAT WAS FOUND
--------------
Auditing every FactorC mode record against stock, exactly ONE deviates:

    record 0xD77E4, reached by mode 27
        stock  Y = (  0, 233, 426, 875)      monotonic -- Honda's viscous surface
        V188   Y = (426, 233, 426, 875)      steps UP at zero, then DROPS

** THE FLYING BUILD V122 MATCHES STOCK. **  So this is a regression introduced somewhere in the
V177..V183 chain and inherited by V185/V186/V187/V188 -- including every build recommended so far.
V184's "engaged == manual in every data table" fixed m26 and MISSED m27.

WHY IT MATTERS
--------------
FactorC is a factor of the base-assist damper, ch0 = (FactorC x FactorE) >> 10.  The recorded fact
is that ** FactorC Y[0] == 0 in ALL 13 stock records **: the damper is DEAD at low index by design,
which is what makes Honda's surface viscous rather than switched.  A non-zero Y[0] gives the damper
a FLOOR that engages abruptly at the first breakpoint -- ** a RELAY ** -- and a relay in exactly
this component is what V80 shipped, which produced the worst grinding in the whole arc
([[accord-v80-damper-relay-and-grind1-inert]], "Honda's surface is viscous; ours is a relay").

Here it is worse than a plain relay: Y[0]=426 is GREATER than Y[1]=233, so the curve steps up and
then falls.  That is not a calibration anyone chose; it is a defect.

WHAT V189 DOES
--------------
Writes Y[0] at 0xD77EE back to Honda's 0, read from the stock image rather than typed.  One int16.
Everything else in V188 is carried and asserted, including the grind notch.

REACHABILITY -- STATED HONESTLY
-------------------------------
The record is ambiguous about whether the car ever runs mode 27: one memory says the car is TVCA4
using ** modes 24/26 **, another describes ** m26/27 as engaged **.  So:
    if m27 IS reachable engaged -> this removes a live engaged-only relay in the damper, a prime
                                   suspect for ratcheting/stuttering
    if m27 is NOT reachable     -> the edit is INERT and costs nothing
Either way the edit is strictly toward stock, so there is no configuration in which it is worse.
** BELIEF: m27 reachability. EVIDENCE: the byte deviation and that V122 matches stock. **
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
WRITE_MODE = os.environ.get("ACCORD_V189_WRITE", "").strip().lower()
BASE_NAME = "_v188_V188-V185BASE-NOTCH.ON.THE.GRIND_plain_image.bin"
BASE_SHA = "81c0845fdf22c3af8a164c56240acfd3be2467705997f2f299b29fe560be3279"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
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
    print("  V189 -- REMOVE THE FactorC m27 RELAY WE CREATED   (base V188)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V188 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE DEVIATION, READ FROM THE IMAGES")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    ptr = u32(base, FACTORC_PTR + 4 * 27)
    n = s16(base, ptr)
    check(ptr == u32(stock, FACTORC_PTR + 4 * 27),
          f"mode-27 FactorC pointer 0x{ptr:05X} identical to stock (no repoint)")
    check(n == 4, f"record has {n} breakpoints")
    yoff = ptr + 2 + 2 * n
    check(yoff == Y0_ADDR, f"Y[0] resolves to 0x{yoff:05X} (expected 0x{Y0_ADDR:05X})")
    Ys = tuple(s16(stock, yoff + 2 * i) for i in range(n))
    Yb = tuple(s16(base, yoff + 2 * i) for i in range(n))
    print(f"      stock Y = {Ys}   monotonic, Honda's viscous surface")
    print(f"      V188  Y = {Yb}   steps UP at zero then DROPS")
    check(Ys[0] == 0, "stock Y[0] == 0 -- the damper is DEAD at low index by design")
    check(Yb[0] != 0, f"V188 Y[0] == {Yb[0]} -- the relay this build removes")
    check(Ys[1:] == Yb[1:], "only Y[0] differs; the rest of the record is already stock")

    print("\n  [3] THE EDIT -- one int16, Honda's value copied from the stock image")
    attributed = set()
    struct.pack_into("<h", code, Y0_ADDR, s16(stock, Y0_ADDR))
    attributed |= {Y0_ADDR, Y0_ADDR + 1}
    Yn = tuple(s16(code, yoff + 2 * i) for i in range(n))
    print(f"      0x{Y0_ADDR:05X}  {Yb[0]} -> {Yn[0]}")
    print(f"      V189  Y = {Yn}")
    check(Yn == Ys, "mode-27 FactorC record is now BYTE-IDENTICAL to stock")
    check(all(Yn[i] <= Yn[i + 1] for i in range(n - 1)),
          "the curve is MONOTONIC again -- no relay, no reversal")

    print("\n  [4] EVERY FactorC RECORD NOW MATCHES STOCK")
    bad = []
    for mm in range(40):
        ps = u32(stock, FACTORC_PTR + 4 * mm)
        if not (0xC0000 <= ps < 0xE0000):
            continue
        k = s16(stock, ps)
        if not (0 < k < 32):
            continue
        if any(s16(stock, ps + 2 + 2 * k + 2 * i) != s16(code, ps + 2 + 2 * k + 2 * i)
               for i in range(k)):
            bad.append(mm)
    check(not bad, f"no FactorC record deviates from stock (checked 0..39, deviations: {bad})")

    print("\n  [5] ENGAGED vs MANUAL IN EVERY DAMPER TABLE, m26 AND m27")

    def rd(bb, tptr, mm):
        q = u32(bb, tptr + 4 * mm)
        k = s16(bb, q)
        if not (0 < k < 64):
            return None
        return (tuple(s16(bb, q + 2 + 2 * i) for i in range(k)),
                tuple(s16(bb, q + 2 + 2 * k + 2 * i) for i in range(k)))

    for nm, tptr in (("L1", 0xC9CCC), ("L3", 0xC9DB4), ("FactorC", 0xC9E9C),
                     ("FactorE", 0xC9F84), ("L5clamp", 0xC77A0), ("inertia", 0xCBE74)):
        r24, r26, r27 = rd(code, tptr, 24), rd(code, tptr, 26), rd(code, tptr, 27)
        s27 = rd(stock, tptr, 27)
        ok26 = (r26 == r24)
        ok27 = (r27 == r24) or (r27 == s27)
        check(ok26 and ok27,
              f"{nm}: m26 {'==m24' if ok26 else 'DIFFERS'}, "
              f"m27 {'==m24' if r27 == r24 else 'IS STOCK' if r27 == s27 else 'DIFFERS'}")

    print("\n  [6] THE GRIND NOTCH FROM V188 IS UNTOUCHED")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V188")
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
    check(len(pay) <= 4, f"{len(pay)} payload bytes (<= 4: one int16)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V189 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V189-V188BASE-FACTORC.M27.RELAY.REMOVED"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v189_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V189_WRITE=rwd to emit the files")

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
