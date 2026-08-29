#!/usr/bin/env python3
r"""
V193 -- HONDA'S OSCILLATION DETECTOR CANNOT SEE AN 8 Hz RATCHET.  Base = V192.  ONE byte.

THE FREQUENCY WINDOW -- the finding this build exists for
---------------------------------------------------------
FUN_000428d4 is a reversal counter on gp-0x6c2c (the acceleration EMA):

    T    = cal(0xC620A) = 12800        amplitude threshold
    HYST = cal(0xC64DD) = 50           DWELL LIMIT, in task ticks

    state +latched:  if (dwell >= HYST)  -> neutral        // TIMES OUT
                     else if (x < -T)    -> -latched, count++
                     else dwell++

A reversal only COUNTS if the opposite peak arrives within HYST ticks.  FUN_000428d4,
FUN_00041464 and FUN_000352b4 all share the single caller FUN_0002214a, so they run in the same
task -- the 1 kHz control task (independently corroborated: the biquad response was verified at
fs = 1000 Hz against three stock points).  So HYST = 50 ticks = 50 ms, and:

    countable  <=>  half-period < 50 ms  <=>  ** f > 10 Hz **

    ratchet  7.34 - 8.59 Hz   half-period 58 - 68 ms   ** OUTSIDE the window **
    grind   15   - 25   Hz    half-period 20 - 33 ms      inside

=> ** Honda's detector CANNOT COUNT AN 8 Hz OSCILLATION.  The dwell times out before the opposite
   peak arrives, so gp-0x671a never leaves 0 for the ratchet, and V191 + V192 -- both of which act
   only on the counter >= 5 branch -- are INERT FOR THE RATCHET. **  They may still act on the
   grind, which is inside the window, if its amplitude reaches T.

!! This also corrects a recorded assumption.  The lineage treats T (0xC620A) as the detector knob
   ("lowering T changes five things at once").  ** T is the wrong knob for the ratchet: no amount of
   lowering an AMPLITUDE threshold makes an 8 Hz oscillation countable when the DWELL is what
   expires. **  HYST is the binding constraint.

WHAT V193 DOES
--------------
0xC64DD  50 -> 100.  The dwell limit becomes 100 ms, so the window opens to f > 5 Hz and covers the
whole 5-12 Hz ratchet band with margin:

    HYST  50 ->  f > 10.0 Hz     (ratchet excluded)
    HYST 100 ->  f >  5.0 Hz     (ratchet fully inside)

With the ratchet finally visible to the detector, V191's and V192's damping responses -- which are
gated on exactly that counter -- can act on it.

!! THE HONEST RISK, AND IT IS DIFFERENT IN KIND FROM V191/V192
   V191 and V192 are conditional on a state that (per the finding above) never occurs during the
   ratchet, so they cannot affect normal driving at all.  ** V193 makes that state REACHABLE, so for
   the first time in this chain the detector-conditional damping can engage while driving. **  A
   spurious detection would tighten the slew limit for a hold period and could read as brief
   heaviness.  The counter still requires |gp-0x6c2c| > 12800 on BOTH sides, which is a large
   acceleration excursion, so this is bounded rather than free-running -- but it is a real change to
   normal driving and is pre-registered as such.
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
WRITE_MODE = os.environ.get("ACCORD_V193_WRITE", "").strip().lower()
BASE_NAME = "_v192_V192-V191BASE-OSC-SLEW-CURVE-TIGHTENED_plain_image.bin"
BASE_SHA = "c36b6ca12e27633f6a52a9a0d8c32feab71e08606fb253d4ef96cf3a17d5cdc1"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
ACCEL_FLAG = 0xC64AE
OSC_FALLBACK = 0xC640A
NORM_X, NORM_Y = 0xC6936, 0xC693E
HYST = 0xC64DD
NEW_HYST = 100
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
    print("  V193 -- REMOVE THE FactorC m27 RELAY WE CREATED   (base V188)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V192 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE DETECTOR'S FREQUENCY WINDOW")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    T = struct.unpack_from("<h", base, 0xC620A)[0]
    H = base[HYST]
    print(f"      T    0xC620A = {T}   (amplitude threshold on gp-0x6c2c)")
    print(f"      HYST 0xC64DD = {H}   (dwell limit, in 1 kHz task ticks)")
    check(H == stock[HYST], f"HYST is still Honda's value ({H}) on the base")
    fmin = 1000.0 / (2.0 * H)
    print(f"      => countable only when half-period < {H} ms, i.e. f > {fmin:.2f} Hz")
    print("         ratchet 7.34-8.59 Hz  (half-period 58-68 ms)  -> OUTSIDE")
    print("         grind  15-25 Hz       (half-period 20-33 ms)  -> inside")
    check(fmin > 8.59,
          f"at HYST={H} the window starts at {fmin:.2f} Hz, ABOVE the ratchet's top (8.59 Hz)"
          " -- the detector provably cannot count it")

    print("\n  [3] THE EDIT -- one byte")
    attributed = set()
    code[HYST] = NEW_HYST
    attributed.add(HYST)
    fnew = 1000.0 / (2.0 * code[HYST])
    print(f"      0x{HYST:05X}  {H} -> {code[HYST]}")
    print(f"      => window opens from f > {fmin:.2f} Hz to f > {fnew:.2f} Hz")
    check(fnew < 7.34,
          f"the window now starts at {fnew:.2f} Hz, BELOW the ratchet's bottom (7.34 Hz)"
          " -- the whole 5-12 Hz band is inside")
    check(code[HYST] <= 255, "HYST is a byte cal (ld.bu) and fits")

    print("\n  [4] T IS DELIBERATELY NOT TOUCHED")
    check(struct.unpack_from("<h", code, 0xC620A)[0] == T,
          f"0xC620A T unchanged at {T} -- lowering an AMPLITUDE threshold cannot make an 8 Hz"
          " oscillation countable when the DWELL is what expires")

    print("\n  [5] WHAT THIS UNLOCKS -- V191 AND V192 BECOME REACHABLE")
    check(s16(code, 0xC640A) == 0, "0xC640A oscillation fallback ZEROED (V191) -- now reachable")
    ocurve = [struct.unpack_from("<H", code, OSC_Y + 2 * i)[0] for i in range(4)]
    check(ocurve == [215, 184, 184, 184],
          f"0xC691A oscillating slew curve {ocurve} (V192) -- now reachable")

    print("\n  [6] EVERY OTHER V192 LEVER IS UNTOUCHED")
    check(code[0xC64AE] == 0, "0xC64AE the 2nd accel term still DISABLED (V190)")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V192")
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
    check(len(pay) <= 2, f"{len(pay)} payload bytes (<= 2: one byte)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V193 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V193-V192BASE-DETECTOR-DWELL-WIDENED"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v193_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V193_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V192 + the detector dwell widened 50->100: the 8 Hz ratchet is now VISIBLE. **")
    print("  ** This one CAN reach normal driving -- it makes the detector state reachable. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
