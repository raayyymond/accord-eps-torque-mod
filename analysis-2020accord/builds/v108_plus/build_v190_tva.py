#!/usr/bin/env python3
r"""
V190 -- DISABLE THE SECOND ACCELERATION FEEDBACK.  Base = V189.  ONE byte.

WHAT WAS FOUND, AND WHY IT IS NEW
---------------------------------
Tracing the second acceleration EMA (gp-0x6c2e, coefficient 0xC40DA) found a whole feedback path the
kit has never touched:

    FUN_00041464   gp-0x6c2e = EMA(rate derivative) >> 9          the 2nd accel channel
    FUN_00036f30   L    = LERP(0xC68EA/0xC68F2, speed)
                   gp-0x6bc2 = clamp( ((L*a)>>6) * sign(gp-0x6752) * gp-0x69be >> 6, +-gp-0x6bc0 )
    FUN_00037fe6   gp-0x6ad6 = clamp( (SUM + gp-0x6bc2*cal(0xC64AE) + ...) * LERP >> 10, +-25600 )
                   ^ gp-0x6ad6 is the TORQUE-TRACKING REFERENCE

** cal 0xC64AE is an ENABLE FLAG (0 or 1), not a gain **, like all seven weights at 0xC64AD..0xC64B3
-- every one of them reads 1 in stock, V122 and V189.  Its two neighbours 0xC64AB/0xC64AC are the
same kind of flag and Honda ships THOSE at 0, which is what confirms 0 is a supported state.

WHY THIS IS THE RIGHT SHAPE FOR THE RATCHET
-------------------------------------------
    * it is ACCELERATION-derived, so its loop contribution scales as omega^2
      -> 66x stronger at 8.2 Hz than at 1 Hz.  Frequency-selective in the direction we want.
    * its speed weighting is STRONGEST EXACTLY WHERE THE RATCHET LIVES:
          X = [0, 4, 32, 96] km/h        Y = [64, 64, 32, 32]
          1 km/h -> 64      24 km/h -> 41      40+ km/h -> 32
      i.e. 2x stronger at creep than at highway.  The ratchet is a creep symptom.
    * it has ZERO effect at DC -- acceleration is zero in steady state -- so it costs NO LKAS
      authority and no steering weight.  That is exactly the operator's constraint: no added
      apparent mass or friction as the price of fixing the ratchet.
    * ** it has never been touched in the whole post-V38 arc. **

THE SIGN -- STATED AS BELIEF, NOT EVIDENCE
------------------------------------------
gp-0x6752 is -1 (verified 3 ways), so gp-0x6bc2 ~ -k*a.  Following the recorded polarity chain
(gp-0x6ad6 down => error up => MORE assist), positive acceleration produces more assist, which is
POSITIVE feedback on acceleration = negative apparent inertia = DESTABILISING.  Removing it should
therefore damp the ratchet.
!! That chain has five links and rests on the recorded polarity claim.  ** EVIDENCE: the term
exists, is acceleration-derived, is 2x weighted at creep, and its enable flag reads 1.  BELIEF: that
its sign is destabilising. **  If the sign is the other way the term was providing damping and the
ratchet will get WORSE -- a one-byte, cal-only revert to V189 undoes it.  That is the failure mode
to watch for, and it is pre-registered on the drive card.

WHAT V190 DOES
--------------
0xC64AE 1 -> 0.  One byte.  Everything in V189 is carried and asserted, including the grind notch.
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
WRITE_MODE = os.environ.get("ACCORD_V190_WRITE", "").strip().lower()
BASE_NAME = "_v189_V189-V188BASE-FACTORC.M27.RELAY.REMOVED_plain_image.bin"
BASE_SHA = "71a7032a485ec8253cd46c2532adcf0331382b5b8c374fb204b9fc9d07e9240b"

A8_OFF, AC_OFF, B0_OFF, B4_OFF = 0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4
ACCEL_FLAG = 0xC64AE
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
    print("  V190 -- REMOVE THE FactorC m27 RELAY WE CREATED   (base V188)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V189 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE TERM, READ FROM THE IMAGES")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    print("      the seven Path-2 enable flags 0xC64AD..0xC64B3 (FUN_00037fe6 -> gp-0x6ad6):")
    for off in range(0xC64AD, 0xC64B4):
        print(f"        0x{off:05X}  stock {stock[off]}   base {base[off]}"
              f"{'   <== gp-0x6bc2, THE ACCEL TERM' if off == ACCEL_FLAG else ''}")
    for off in range(0xC64AD, 0xC64B4):
        check(stock[off] in (0, 1) and base[off] in (0, 1),
              f"0x{off:05X} is an ENABLE FLAG (0/1), stock={stock[off]} base={base[off]}")
    check(stock[ACCEL_FLAG] == 1 and base[ACCEL_FLAG] == 1,
          f"0x{ACCEL_FLAG:05X} reads 1 (enabled) in stock AND on the base")
    check(stock[0xC64AB] == 0 and stock[0xC64AC] == 0,
          "Honda ships the sibling flags 0xC64AB/AC at 0 -- 0 is a supported state")

    print("\n  [3] THE SPEED WEIGHTING -- strongest exactly at creep")
    X = [struct.unpack_from("<H", stock, 0xC68EA + 2 * i)[0] for i in range(4)]
    Y = [struct.unpack_from("<H", stock, 0xC68F2 + 2 * i)[0] for i in range(4)]
    print(f"      X = {X}  (~{[round(x / 64.0, 1) for x in X]} km/h)")
    print(f"      Y = {Y}")
    check(Y[0] >= 2 * Y[-1],
          f"creep weight {Y[0]} is >= 2x the highway weight {Y[-1]} -- the term peaks at creep")

    print("\n  [4] THE EDIT -- one byte")
    attributed = set()
    before = code[ACCEL_FLAG]
    code[ACCEL_FLAG] = 0
    attributed.add(ACCEL_FLAG)
    print(f"      0x{ACCEL_FLAG:05X}  {before} -> {code[ACCEL_FLAG]}")
    check(code[ACCEL_FLAG] == 0, "the gp-0x6bc2 acceleration term is DISABLED")
    for off in range(0xC64AD, 0xC64B4):
        if off != ACCEL_FLAG:
            check(code[off] == base[off], f"0x{off:05X} other Path-2 flag UNCHANGED ({code[off]})")

    print("\n  [5] NO DC EFFECT -- this cannot cost LKAS authority")
    print("      the term is acceleration-derived; acceleration is 0 in steady state, so the")
    print("      contribution to gp-0x6ad6 at DC is 0 both before and after.  No authority change.")

    print("\n  [6] THE GRIND NOTCH AND EVERY V189 LEVER ARE UNTOUCHED")
    for off in BIQUAD:
        check(u32(code, off) == u32(base, off), f"0x{off:05X} biquad cell identical to V189")
    m194, _ = resp(code, 19.40)
    check(m194 < 0.05, f"notch still at 19.40 Hz, |H| = {m194:.5f}")
    p27 = u32(code, 0xC9E9C + 4 * 27)
    n27 = s16(code, p27)
    Y27 = tuple(s16(code, p27 + 2 + 2 * n27 + 2 * i) for i in range(n27))
    check(Y27 == tuple(s16(stock, p27 + 2 + 2 * n27 + 2 * i) for i in range(n27)),
          f"FactorC m27 still stock {Y27} (V189's revert carried)")

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
    FF.assert_x31_checksum(rwd, "V190 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V190-V189BASE-ACCEL-REFERENCE-TERM-OFF"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v190_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [14] NOT WRITTEN -- set ACCORD_V190_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V189 + the 2nd acceleration feedback DISABLED (0xC64AE 1->0). **")
    print("  ** omega^2-scaled, 2x weighted at creep, ZERO effect at DC. Sign is BELIEF. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
