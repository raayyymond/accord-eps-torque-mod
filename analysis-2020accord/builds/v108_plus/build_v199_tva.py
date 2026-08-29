#!/usr/bin/env python3
r"""
V199 -- THE SAME NOTCH, BUILT SO IT CANNOT ADD LOOP GAIN.  Base = V196.  4 float32 cells.

WHY V196 MUST NOT FLY
---------------------
V199/V196 place the biquad POLES AT THE SAME ANGLE AS THE ZEROS.  That is the textbook narrow notch,
and BUILD-LINEAGE.md names it as a trap in the V105 section, in these words:

    "THE HIDDEN ONE: fixing DC with poles at the notch angle (the textbook narrow notch) forces
     max|H| to 1.098-1.608 ... Fix: Honda own poles-BELOW-zeros layout (stock is poles 42.3 /
     zeros 55.2).  Check max|H| over 0-500 Hz against stock 1.0000 before shipping any biquad edit."

V196 was never checked against that bar, because V199 own GATE 2 assertion was written as
`mx <= 2.0`.  Measured from the built image, V196 scores:

    max|H| over 0-500 Hz = 1.7177        the bar is 1.0000        ** FAILS **

It amplifies above ~30 Hz: 1.88x Honda at 35 Hz, 4.57x at 45 Hz, 1.72x at Nyquist.  That is exactly
what V103 GATE 2 exists to forbid -- the sentence that licensed arming this section at all was
"|H| <= 1.000032 everywhere 0.1-500 Hz => the filter can only REMOVE loop gain, never add it".
A filter that adds gain in a loop whose instability we are chasing is not a fix, it is a new risk.

WHY THE BAR IS ABSOLUTE 1.0 AND NOT "vs Honda"
----------------------------------------------
0xC649B 0->1 alone is INERT: the record states the real arm is gp-0x671a >= 5, "never observed true
across 255,292 engaged frames on three builds (V64/V67/V68)".  ** Honda ships this biquad DORMANT. **
The car ran H = 1 at every frequency for its entire life until V103 armed it engaged-only.  So the
55.226 Hz null is not a protection Honda relies on at this operating point, and the honest reference
for "does this filter make anything worse than the car has ever been" is H = 1, i.e. max|H| <= 1.0.
Under that reference V199 is never worse than stock at ANY frequency, and V196 is worse above 30 Hz.

WHAT V199 CHANGES
-----------------
Same zeros -- 19.75 Hz, the cs_rate refit, kept exactly.  The poles move BELOW the zeros, Honda own
layout, and the radius rises:

                        zeros Hz   poles Hz   radius   max|H|    d phase @5Hz   18-21 Hz atten
    V196                  19.75      19.75     0.9000   1.7177      -7.80 deg        16.8x
    V199                  19.75      17.45     0.9675   1.000000    -2.95 deg        10.1x

=> the peak attenuation is lower, and that is the price.  What it buys: the filter can no longer add
   loop gain anywhere, and it gives back 4.85 degrees of LKAS-band phase -- the same currency peak
   command oscillation is paid in, and the reason V184 8 Hz notch was abandoned at -40.5 degrees.

A sweep of 1485 (pole frequency, radius) pairs found 521 that pass max|H| <= 1.0.  Inside that set the
tradeoff is hard and monotone: the corner that is free at 54-74.5 Hz costs -46 deg at 5 Hz, and the
corner that is free in phase gives only 6.9x.  V199 is the deepest notch with added phase <= 3 deg.

WHAT IS CARRIED
---------------
Everything in V196, unchanged: the engaged inertia half-dose at 0xD7A5C, the K1 and accel-alpha
reverts, w[3] halved, the FactorC m27 relay removed, 0xC407E frozen at 511, and the 164-byte cave
byte-identical.  Only the four biquad cells move.  Manual driving is untouched either way -- the
section is engagement-gated by V103 three-site patch on gp-0x6806.
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
WRITE_MODE = os.environ.get("ACCORD_V199_WRITE", "").strip().lower()
BASE_NAME = "_v196_V196-V195BASE-ENGAGED-INERTIA-HALF-DOSE_plain_image.bin"
BASE_SHA = "f904e43a1f4ccb94e81204dbecd93982049a024b95e48bd1c2c43852a7edec8e"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
BIQUAD = (A8_OFF, AC_OFF, B0_OFF, B4_OFF)

# --- THE SPEC IS THE FORMULA, NEVER A TYPED DECIMAL --------------------------------------------
# A 6-dp decimal does not round-trip a float32; three agents once produced three byte strings for
# one coefficient, none mis-encoded -- they had encoded three DIFFERENT NUMBERS.  So the two design
# parameters are exact, everything else is derived, and every assertion below is checked against the
# ENCODED float32 read back out of the image -- not against these Python doubles.
SEC_FS = 1000.0
F0 = 19.75         # notch centre, Hz -- refit on cs_rate, where the grind LIVES
FP = 17.45         # POLE centre, Hz -- BELOW the zeros: the layout Honda uses
RP = 0.9675        # pole radius     -- deepest notch with added phase <= 3 deg

FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
CARRIED_U16 = {0xC40D2: ("K1 -> Honda (V177)", 102),
               0xC63A6: ("w[3] halved (V181)", 512),
               0x55DF2: ("427 probe source gp-0x6ac0 (V183)", 0x9540)}
CARRIED_B = {0xC40DC: ("accel alpha -> Honda (V179)", 22),
             0x55E10: ("packer sar 4 (V183)", 0xA4)}
PTR_I = 0xCBE74
HONDA_Y = (-9830, -5734, -1966)
HALF_HONDA_Y = (-4915, -2867, -983)   # V196 engaged half-dose at 0xD7A5C

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
    a8 = -2.0 * RP * math.cos(2.0 * math.pi * FP / SEC_FS)   # POLE angle, not the zero angle
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
    print("  V199 -- THE SAME NOTCH, BUILT SO IT CANNOT ADD LOOP GAIN   (base V196)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V196 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] DESIGN PARAMETERS -> COEFFICIENTS (formula, not typed decimals)")
    a8, ac, b0, b4 = design()
    print(f"      F0 = {F0:.2f} Hz   RP = {RP:.4f}   fs = {SEC_FS:.0f} Hz")
    print(f"      B0 = -2*cos(2*pi*F0/fs)   = {b0:+.10g}")
    print(f"      A8 = -2*RP*cos(2*pi*F0/fs)= {a8:+.10g}")
    print(f"      AC = RP*RP                = {ac:+.10g}")
    print(f"      B4 = (1+A8+AC)/(2+B0)     = {b4:+.10g}")

    print("\n  [3] THE EDIT -- four float32 cells")
    attributed = set()
    for off, val, nm in ((A8_OFF, a8, "A8"), (AC_OFF, ac, "AC"),
                         (B0_OFF, b0, "B0"), (B4_OFF, b4, "B4")):
        before = f32(code, off)
        struct.pack_into("<f", code, off, val)
        attributed |= set(range(off, off + 4))
        print(f"      0x{off:05X} {nm}  {before:+.9g} -> {f32(code, off):+.9g}")

    print("\n  [4] ASSERT AGAINST THE ENCODED float32, NOT THE PYTHON DOUBLES")
    for off, val, nm in ((A8_OFF, a8, "A8"), (AC_OFF, ac, "AC"),
                         (B0_OFF, b0, "B0"), (B4_OFF, b4, "B4")):
        enc = f32(code, off)
        rel = abs(enc - val) / max(abs(val), 1e-30)
        check(rel < 1e-6, f"{nm} encodes to {enc:+.9g}, rel err {rel:.2e} < 1e-6")

    print("\n  [5] DC GAIN -- the assist level the driver feels MUST NOT MOVE")
    mag0, _ = resp(code, 0.0)
    check(abs(mag0 - 1.0) < 2e-3, f"|H(DC)| = {mag0:.6f} (unity within 0.2%)")

    print("\n  [6] GATE 2 MAGNITUDE -- max |H| over 0-500 Hz")
    grid = [x * 0.25 for x in range(1, 240)] + [60.0 + 2.0 * k for k in range(221)]
    mx = max(resp(code, x)[0] for x in grid)
    at = max(grid, key=lambda x: resp(code, x)[0])
    # THE BAR IS STOCK 1.0000, NOT 2.0.  V199 wrote 2.0 and that is how V196 shipped at
    # 1.7177.  BUILD-LINEAGE.md V105: "Check max|H| over 0-500 Hz against stock 1.0000
    # before shipping any biquad edit."  V103 GATE 2: the filter "can only REMOVE loop
    # gain, never add it".  Both are the same bar, and this is it.
    check(mx <= 1.0000001, f"max |H| = {mx:.6f} at {at:.2f} Hz (<= 1.0, the lineage bar)")
    mb_max = max(resp(base, x)[0] for x in grid)
    check(mb_max > 1.5, f"CONTROL: base V196 scores {mb_max:.4f} and FAILS this same bar")

    print("\n  [7] GATE 2 PHASE -- openpilot's band, vs what the car flies today")
    for fr in (0.5, 1.0, 2.0, 3.0):
        _, pn = resp(code, fr)
        _, pb = resp(base, fr)
        d = pn - pb
        check(abs(d) <= 10.0, f"{fr:4.1f} Hz added lag {d:+6.2f} deg (budget 10.0)")

    print("\n  [8] THE NOTCH IS WHERE IT WAS DESIGNED, AND DEEP")
    mags = [(x, resp(code, x)[0]) for x in [16.0 + 0.02 * k for k in range(451)]]
    fmin, vmin = min(mags, key=lambda t: t[1])
    check(abs(fmin - F0) < 0.10, f"deepest point at {fmin:.2f} Hz (designed {F0:.2f})")
    check(vmin < 0.05, f"notch depth |H| = {vmin:.5f} at the centre")
    print("      response across the grind band:")
    for x in (8.8, 12.0, 15.0, 17.0, 19.75, 21.0, 22.2, 23.0, 25.0, 30.0):
        m, p = resp(code, x)
        mb, _ = resp(base, x)
        print(f"        {x:5.2f} Hz  |H| {m:7.4f}  ({20 * math.log10(max(m / mb, 1e-12)):+6.1f} dB"
              f" vs V196)   phase {p:+7.1f} deg")

    print("\n  [9] WHAT WE GIVE UP -- Honda's 55.226 Hz null, DISCLOSED NOT HIDDEN")
    m55n, _ = resp(code, 55.226)
    m55b, _ = resp(base, 55.226)
    print(f"      55.226 Hz  |H| {m55b:.6f} -> {m55n:.6f}   "
          f"({20 * math.log10(max(m55n / max(m55b, 1e-12), 1e-12)):+.1f} dB)")
    print("      alias test, 295 routes: median 0.99, max 2.69, zero routes > 3;")
    print("      controls 41/43/46.5/48 Hz reach 3.6-6.5  => no road-excited 55 Hz mode.")
    print("      NOT excluded: a command-excited loop mode the notch currently suppresses.")

    print("\n  [10] EVERY CARRIED LEVER IS ASSERTED")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        check(u16(code, off) == want, f"0x{off:05X} {nm} CARRIED ({want})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED (0x{want:02X})")
    p = u32(code, PTR_I + 4 * 27)
    n = s16(code, p)
    Y27 = tuple(s16(code, p + 2 + 2 * n + 2 * i) for i in range(3))
    check(Y27 == HONDA_Y, f"inertia m27 Y = {Y27} -- Honda, the dose revert CARRIED")
    Y26 = tuple(s16(code, 0xD7A5C + 2 * i) for i in range(3))
    check(Y26 == HALF_HONDA_Y, f"inertia m26 ENGAGED Y = {Y26} -- V196 half-dose CARRIED")
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

    print("\n  [12] FULL BYTE DIFF vs V196")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) <= 16, f"{len(pay)} payload bytes (<= 16: four float32 cells)")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V199 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V199-V196BASE-NOTCH.POLES.BELOW.ZEROS"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v199_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V199_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** max|H| 1.000000 <= 1.0: this filter can only REMOVE loop gain, never add it. **")
    print("  ** V196 scores 1.7177 and FAILS that bar.  V199 gives back 4.85 deg of LKAS phase. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
