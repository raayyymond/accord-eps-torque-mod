#!/usr/bin/env python3
r"""
V210 -- HALVE THE SOFT RELAY'S SMALL-SIGNAL GAIN.  Base = V202.  ONE u16 cal.

WHAT THE LEVER IS
-----------------
FUN_00038148 ends with

    0x38242   uVar7 = (|resid| * cal(0xC63AE)) >> 10          cal = 1024 = unity
              sVar8 = LERP(uVar7)                              X gp-0x64b6.., Y gp-0x641c..
              gp-0x6b70 = sgn(resid) * sVar8,  clamped +-cal(0xC6200) = 8192

Computing that LERP from the image -- it is the POWER-ASSIST CURVE, via the staging arrays
assist_map_mirror.py already mirrors integer-exactly (validated 200/200 vs V72's flown probe) --
shows it is NOT a hard relay but a SOFT one:

    speed    gain near 0    mid-range     ratio
      640       2.67x         0.256x      10.4x
     1280       3.04x         0.284x      10.7x
     2560       3.77x         0.352x      10.7x
     5120       3.43x         0.516x       6.7x

High small-signal gain around a zero crossing is the shape that sustains a small-amplitude limit
cycle, and it matches the record's own "command-proportional Coulomb relay" blamed for the ratchet.
0xC63AE scales the LERP's INPUT, so near the origin -- where the curve is near-linear -- it scales
that gain DIRECTLY.  Halving it halves 2.67x -> 1.34x, 3.77x -> 1.89x.

** BUT THAT IS THE SMALL-SIGNAL LIMIT ONLY, AND THE DOSE IS WEAKER AT LARGER AMPLITUDES. **
Scaling the INPUT of a CONCAVE curve moves the operating point onto a STEEPER part, so the two
effects fight.  The correct instrument is the describing function, N_g(A) = k * N_f(k*A), NOT
k * N_f(A).  Measured on the real curve (verify/gate2_v210_describing_function.py):

    amplitude A      25     200     800    3200    6400   12800
    N ratio        0.486   0.472   0.619   0.794   0.771   0.658     <- NOT a flat 0.500

So the dose buys between 1.26x and 2.1x of loop-gain reduction depending on amplitude, not a uniform
2x.  It still reduces gain EVERYWHERE, which is the GATE 2 pass -- but do not quote "half".

** It scales THIS STAGE ONLY. **  The base power-assist map is fed by Xsrc/Ysrc, a different
transform of the same source, so the map is untouched.  That matters: the curve's shape is otherwise
welded to the ROM assist records and could not be moved without moving steering feel, which is very
likely why the ratchet has resisted sixty builds.

GATE 1: 0xC63AE has EXACTLY ONE site image-wide (0x38242, the reader above) and ZERO writers, by the
kit's own tp_cal_readers.py.  Byte-stock on every build.  Cal-only, 2 bytes, no cave -- not the
bricking class.

THE SIGN, AND THE PRICE -- STATED, NOT HIDDEN
---------------------------------------------
The record's nine-link Ghidra polarity trace covers this exact path, and its step 4 IS this stage:

    4  gp-0x6b70 = clamp(sgn(res)*LERP(|res|), +-8192), f' >= 0  =>  d/d(MODEL) >= 0 everywhere
    5  FUN_00037fe6: gp-0x6ad6 += gp-0x6b70 * w                  =>  target felt effort
    9  delivered = gp-0x6752 * gp-0x6b94                         =>  torque in the driver's direction

with the measured cross-check d(gp-0x6b94)/d(gp-0x6b70) = +0.2529 / +0.2565.  So the sign is known
WITHOUT a drive:

    lowering 0xC63AE shrinks |gp-0x6b70| toward zero.  V87 measured gp-0x6b70 NEGATIVE 67.19 % of
    engaged time, and shrinking a negative value raises it => LESS assist on ~2/3 of frames,
    MORE on the other ~1/3.  ** Net: predominantly LESS assist, a slightly heavier wheel. **

** That is a real cost against a stated goal, so it is priced here rather than buried. **  The trade
is: the soft relay's small-signal gain halves (the ratchet mechanism) and the wheel gets somewhat
heavier (an authority cost).  The operator has been explicit that he wants low apparent friction AND
no ratcheting; this buys one with some of the other, so ** it is deliberately NOT the recommended
build ** -- V205 is, because V205 measures gp-0x6b70's actual range and sign so this dose can be
sized rather than guessed.  V210 exists so that if V205 says the range is large, the fix is already
cut.

WHY HALF AND NOT LESS
---------------------
The gain ratio between small and mid signal is 6.7-10.7x, so halving is a modest step inside a large
range -- enough to be felt if the mechanism is real, small enough that the assist cost stays bounded.
A quarter dose is the obvious follow-up if half reads in the right direction.

WHAT IS CARRIED
---------------
Everything in V208, bit for bit: the 20.50 Hz notch with poles at 15.50 Hz, the engaged inertia
half-dose, the K1 and accel-alpha reverts, w[3] halved, 0xC407E frozen at 511, the 164-byte cave
byte-identical, and the 427 probe still on gp-0x6ac0.  ** V210 is a lever, not an instrument. **
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
WRITE_MODE = os.environ.get("ACCORD_V210_WRITE", "").strip().lower()
BASE_NAME = "_v208_V208-V202BASE-NOTCH.20.50.REFIT.ON.EPISODES_plain_image.bin"
BASE_SHA = "e27b4fcc2dafd872feb25e5625544dbe4f9067a742cec1670d8d3dde176b1f7a"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
ACCEL_FLAG = 0xC64AE
OSC_FALLBACK = 0xC640A
NORM_X, NORM_Y = 0xC6936, 0xC693E
HYST = 0xC64DD
NEW_HYST = 100
PROBE_HW2, PROBE_SHIFT = 0x55DF2, 0x55E10
RESID_SCALE = 0xC63AE          # the soft relay's own input scale, 1 reader / 0 writers
NEW_SCALE = 512                # HALF Honda unity 1024
KITROOT = str(Path(__file__).resolve().parents[2].parent)
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
F0 = 20.50         # notch centre, Hz -- V199 design: zeros 20.50, poles 15.50, r 0.9575
RP = 0.9300        # pole radius     -- WIDE: 19 Hz is far from openpilot, so we can afford it

FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
CARRIED_U16 = {0xC40D2: ("K1 -> Honda (V177)", 102),
               0xC63A6: ("w[3] halved (V181)", 512),
               0x55DF2: ("427 probe source gp-0x6ac0 (V202, UNCHANGED)", 0x9540)}
CARRIED_B = {0xC40DC: ("accel alpha -> Honda (V179)", 22),
             0x55E10: ("packer sar 4 (V202, UNCHANGED)", 0xA4)}
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
    """DEAD IN THIS BUILDER -- never called; this build does not edit the biquad.
    It is also the OLD poles-AT-zeros form (a8 uses the ZERO angle), which BUILD-LINEAGE.md
    names as a trap. Do NOT revive it here: the current geometry is V208s poles-BELOW-zeros.
    """
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
    print("  V200 -- REMOVE THE FactorC m27 RELAY WE CREATED   (base V188)")
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
    check(u16(base, PROBE_HW2) == 0x9540, "the base probe reads gp-0x6ac0")

    print("\n  [3] THE EDIT -- one u16 cal, the soft relay's own input scale")
    attributed = set()
    before = u16(code, RESID_SCALE)
    check(before == 1024, f"0x{RESID_SCALE:05X} starts at Honda unity ({before})")
    struct.pack_into("<H", code, RESID_SCALE, NEW_SCALE)
    attributed |= {RESID_SCALE, RESID_SCALE + 1}
    print(f"      0x{RESID_SCALE:05X}  {before} -> {u16(code, RESID_SCALE)}"
          f"   ({NEW_SCALE / 1024.0:.3f}x)")
    check(u16(code, RESID_SCALE) == NEW_SCALE, f"the residual scale is now {NEW_SCALE}")

    print("\n  [4] WHAT THE DOSE DOES TO THE SOFT RELAY, from the image")
    # gp-0x6b70 = sgn(resid) * LERP((|resid| * cal) >> 10).  Scaling the INPUT scales the
    # small-signal gain directly, because the curve is near-linear close to the origin.
    import sys as _sys
    _sys.path.insert(0, os.path.join(KITROOT, "analysis-2020accord", "studies", "models"))
    import assist_map_mirror as _M                                            # noqa: E402
    for sp in (640, 1280, 2560, 5120):
        A_, B_ = _M.stage_382d8(26, sp)
        _M.stage_389ec(A_, B_, sp, 150)
        Xi, Yi = _M._LAST_STAGING["Xi"], _M._LAST_STAGING["Yi"]
        g0 = Yi[1] / Xi[1]
        print(f"        speed {sp:5d}   small-signal gain {g0:.2f}x"
              f" -> {g0 * NEW_SCALE / 1024.0:.2f}x")
    check(NEW_SCALE < 1024, "the dose LOWERS the gain (raising it would make the relay worse)")

    print("\n  [5] V196 LEVERS CARRIED, AND WHAT IS DELIBERATELY ABSENT")
    check(code[0xC64DD] == 50, "0xC64DD dwell is Honda 50 -- V193s widening NOT carried")
    check(s16(code, 0xC640A) == -8192, "0xC640A oscillation fallback is Honda -8192")
    check(code[0xC64AE] == 1, "0xC64AE the 2nd accel term is Honda-enabled (V190 not carried)")
    p26 = u32(code, 0xCBE74 + 4 * 26)
    n26 = s16(code, p26)
    Y26 = [s16(code, p26 + 2 + 2 * n26 + 2 * i) for i in range(n26)]
    check(Y26 == [-4915, -2867, -983], f"engaged inertia Y = {Y26} -- V196s half dose CARRIED")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V202")
    check(u16(code, PROBE_HW2) == u16(base, PROBE_HW2)
          and code[PROBE_SHIFT] == base[PROBE_SHIFT],
          "the 427 probe is UNTOUCHED -- V210 is a lever, not an instrument")
    m194, _ = resp(code, F0)
    check(m194 < 0.05, f"notch still at {F0:.2f} Hz, |H| = {m194:.5f}")

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
    # DERIVE the count, never assume it: 1024 = 0x0400 -> 512 = 0x0200 moves only the HIGH byte,
    # so this is ONE byte, not two.  Same trap as the V181 assertion bug and V198's 0x9540->0x9526.
    _exp = sum(1 for _k in range(2)
               if ((1024 >> (8 * _k)) & 0xFF) != ((NEW_SCALE >> (8 * _k)) & 0xFF))
    check(len(pay) == _exp,
          f"{len(pay)} payload byte(s), derived expectation {_exp} for 1024 -> {NEW_SCALE}")

    print("\n  [13] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V200 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V210-V208BASE-C63AE.1024.TO.512"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v210_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V210_WRITE=rwd to emit the files")

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
