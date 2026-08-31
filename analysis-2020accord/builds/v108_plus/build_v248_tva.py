# -*- coding: utf-8 -*-
r"""V248 -- V247 PLUS THE DAMPER'S FLAT GAIN DOUBLED. THE MARGIN RUNG, ENGAGED ONLY.

WHY A SECOND RUNG EXISTS.  V247 opens the damper's rate dead zone and delivers ~50.6 counts at the
ratchet's measured operating point, against a requirement of ~56 counts computed from Re(Z) = -65.
That is 90 % -- close, but the requirement is itself an ESTIMATE, and if it is really 70 or 80 then
V247 lands short.  This rung buys margin from the same lane, and the arithmetic for it is exact.

    0xD774C   FactorB (engaged, mode 26)   Y = [1024, 1024, 1024, 1024] -> [2048, 2048, 2048, 2048]

FactorB is a FLAT Q10 gain sitting at unity across its whole axis.  It is a pure multiplier: doubling
it doubles the damper magnitude everywhere, with NO SHAPE TO CORRUPT -- there is no dead zone, no knee
and no slope in it to get wrong.

    V247            50.6 counts    90 % of requirement
    V248 (this)    101.3 counts   181 % of requirement      headroom to the 512 ceiling: 5x

WHY DOUBLING IT IS SAFE AT THE TOP END, which is the part that matters.  The damper output is clamped
to the ceiling, whose floor is 512 in ordinary driving (the kickback index gp-0x6ac2 is 0 unless the
wheel is being back-driven).  At HIGH rate the product ALREADY clamps at stock:

    stock, high rate:  1024 * (908/1024) * (927/1024) = 822  -> clamped to 512
    V248,  high rate:  that x2 = 1644                        -> clamped to 512, IDENTICAL

So doubling FactorB changes NOTHING at high rate -- it only lifts the low/mid-rate region, which is
exactly where the ratchet lives and exactly where the damper was too small.  The lever's shape matches
the target by construction rather than by tuning.

ENGAGED ONLY.  Every mode owns its own record, so the MANUAL FactorB (mode 24) is asserted untouched
and manual steering feel is byte-identical.  Added damping is affordable here precisely because the
driver never feels it.

🛑 FLY V247 FIRST.  This is the MARGIN rung, not the first attempt.  V247 vs V241 is one
variable; V248 vs V247 is one variable.  Flying V248 before V247 wastes the discrimination -- if the
ratchet improves you will not know whether the dead zone or the gain did it, and if the wheel feels
heavy or LKAS lazy you will not know which half to walk back.

THE COST, and it is twice V247's.  ~101 counts against the 3072 forward clamp is ~3.3 % of LKAS
authority, spent only while engaged.  If LKAS feels reluctant or slow to hold a lane, this rung is the
first thing to revert -- FactorB back to 1024 returns you to V247 exactly.

BASE: V247.  Eight bytes.
"""
import hashlib
import os
import struct
import sys
import math
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
WRITE_MODE = os.environ.get("ACCORD_V248_WRITE", "").strip().lower()

BASE_NAME = "_v247_V247-V241BASE-FACTORE.DEADZONE.OPEN.ENGAGED_plain_image.bin"
BASE_SHA = "7a59497a592ea6e342a985583c77f18ae753941c90c28ef22bf2145f5028c288"

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
PROBE_HW2, SHIFT_OFF = 0x55DF2, 0x55E10
HW2_KEEP, SAR_KEEP = 0xC7EA, 0xA3          # V231's biquad-state probe -- CARRIED, asserted
# the re-aim: zeros 34.0 Hz, poles 28.0 Hz, r 0.920 -- bytes, never a re-derived decimal
REAIM_BIQ = bytes.fromhex("fa15f3bffaed6b3f25d9fcbf16d7693f")

# carried levers -- asserted, never re-set
LEVER_B, LEVER_B_VAL = 0xC6446, 5244        # V88's bracketed optimum -- CARRIED, asserted
RESID_SCALE_VAL = 1024                      # CARRIED, asserted
SLOPE_CAP, CAP_STOCK = 0xC6384, 2048        # V236's lever -- NOT touched here, asserted
BQ = 0xC60A8                                # a1, a2, b1, c4 -- four float32, direct form II
FB26 = 0xD774C                              # FactorB record, ENGAGED mode 26 -- resolved at runtime
FB_OLD, FB_NEW = 1024, 2048                 # flat Q10 gain at unity -> x2, no shape to corrupt
FE26 = 0xD780C                              # FactorE record, ENGAGED mode 26 (manual 24 @0xD6820)
FE_X0, FE_Y1 = FE26 + 2, FE26 + 2 + 8 + 2   # layout [npt][X x4][Y x4]
X0_OLD, X0_NEW = 60, 12                     # open the rate dead zone
Y1_OLD, Y1_NEW = 140, 539                   # := Y[2], real slope on the first segment
FE24 = 0xD6820                              # MANUAL record -- asserted UNTOUCHED
OP_POINT = 99                               # gp-0x6ac0 in-burst, measured on-car [94,113]
FS_HZ = 1000.0                              # the control task rate
POLE_Y, K_STOCK = 0xC6906, 20               # the lag pole -- asserted STOCK, V241 does not touch it
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V248-V247BASE-FACTORB.X2.ENGAGED"

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
    _b = struct.unpack_from("<ffff", base, BQ)
    check(abs(_b[3]) > 0, "base carries a live biquad c4")
    _fx = [struct.unpack_from("<h", base, FE26 + 2 + 2 * _i)[0] for _i in range(4)]
    _fy = [struct.unpack_from("<h", base, FE26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_fx == [12, 400, 2500, 4000] and _fy == [0, 539, 539, 927],
          f"base already carries V247's opened dead zone X={_fx} Y={_fy} -- this rung stacks "
          f"on it rather than replacing it")
    _fb = [struct.unpack_from("<h", base, FB26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_fb == [FB_OLD] * 4,
          f"base FactorB(engaged) Y={_fb} -- FLAT at unity, a pure multiplier with no shape")
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    for _i in range(4):
        struct.pack_into("<h", code, FB26 + 10 + 2 * _i, FB_NEW)
        attributed |= {FB26 + 10 + 2 * _i, FB26 + 11 + 2 * _i}
    def _lerp(v, X, Y):
        if v <= X[0]:
            return float(Y[0])
        for _i in range(len(X) - 1):
            if v < X[_i + 1]:
                return Y[_i] + (Y[_i + 1] - Y[_i]) * (v - X[_i]) / (X[_i + 1] - X[_i])
        return float(Y[-1])
    _nb = [struct.unpack_from("<h", code, FB26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_nb == [FB_NEW] * 4,
          f"FactorB(engaged) {FB_OLD} -> {FB_NEW} at all four points -- still FLAT, so it stays "
          f"a pure multiplier and adds no shape")
    _fe = _lerp(OP_POINT, [12, 400, 2500, 4000], [0, 539, 539, 927])
    _v247 = 1024.0 * (429 / 1024) * (_fe / 1024)
    _v248 = _v247 * (FB_NEW / FB_OLD)
    check(_v248 > 56.0,
          f"at the operating point the damper goes {_v247:.1f} -> {_v248:.1f} counts, "
          f"past the ~56 needed to cancel Re(Z) = -65 ({100 * _v248 / 56:.0f}% of requirement)")
    check(_v248 < 512,
          f"{_v248:.1f} stays UNDER the 512 ceiling floor, so nothing new clamps at the "
          f"operating point")
    check(1024.0 * (908 / 1024) * (927 / 1024) * (FB_NEW / FB_OLD) > 512,
          "at HIGH rate the product still clamps at 512 exactly as it did at stock -- doubling "
          "FactorB changes nothing at the top end, only the low/mid-rate region")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    # GATE 2 -- V72 turned this lane into a RELAY and a relay at a lightly-damped resonance is
    # a limit-cycle GENERATOR. These three assertions are what make this the opposite of that.
    _ny = [struct.unpack_from("<h", code, FE26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_ny == [0, 539, 539, 927],
          f"V247's FactorE curve is CARRIED unchanged {_ny} -- FactorB is the only variable")
    check(_ny[0] == 0,
          "Y[0] is still ZERO -- the damper goes to zero at zero rate, so this is NOT a relay")
    check(bytes(code[FE24:FE24 + 20]) == bytes(base[FE24:FE24 + 20]),
          "the MANUAL FactorE record (mode 24) is BYTE-IDENTICAL -- manual steering feel is "
          "untouched, which is what makes added damping affordable here")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the notch is CARRIED byte-for-byte -- V241's grinding treatment is untouched")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL} -- this build is NOT V246, it is a different lane")
    check(u16(code, LKAS_CLAMP) == 0,
          "0xC616C = 0 -- the map is fed by the driver torque sensor alone; LKAS cannot reach it")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")

    print("\n  [4] FactorE IS THE ONE THING V247 CHANGES; ELSE V241 BYTE FOR BYTE")
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == bytes(base[BIQ:BIQ + BIQ_LEN]),
          "the biquad block is CARRIED byte-for-byte -- V247 changes FactorE and nothing else")
    check(u16(code, PROBE_HW2) == HW2_KEEP, "biquad-state probe CARRIED")
    check(code[SHIFT_OFF] == SAR_KEEP, "probe shift CARRIED")
    check(code[ALPHA2] == ALPHA2_VAL, f"0x{ALPHA2:05X} alpha2 = {ALPHA2_VAL}")
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
    check(len(pay) <= 8, f"{len(pay)} payload byte(s), at most the four FactorB halfwords")
    check(set(pay) <= {FB26 + 10 + _j for _j in range(8)},
          "every payload byte is inside the ENGAGED FactorB record -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V248 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v248_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V248_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V248 = V247 + THE DAMPER'S FLAT GAIN DOUBLED. THE MARGIN RUNG, ENGAGED ONLY.                       **")
    print("  **   0xD774C   FactorB(engaged) Y = [1024]x4 -> [2048]x4                                              **")
    print("  ** WHY: V247 delivers ~50.6 counts against a ~56 requirement -- 90%, and the                          **")
    print("  ** requirement is itself an ESTIMATE. This buys margin from the same lane.                            **")
    print("  **   V247          50.6 counts    90% of requirement                                                  **")
    print("  **   V248 (this)  101.3 counts   181% of requirement    5x under the ceiling                          **")
    print("  ** WHY IT IS THE RIGHT SHAPE: FactorB is a FLAT Q10 gain at unity -- a pure                           **")
    print("  ** multiplier with NO dead zone, knee or slope to get wrong. And at HIGH rate the                     **")
    print("  ** product ALREADY clamps at 512 (stock 822 -> 512), so doubling changes nothing                      **")
    print("  ** at the top end and only lifts the low/mid-rate region, which is exactly where                      **")
    print("  ** the ratchet lives.                                                                                 **")
    print("  ** ENGAGED ONLY: manual FactorB (mode 24) asserted untouched.                                         **")
    print("  ** FLY V247 FIRST. This is the MARGIN rung. V247 vs V241 is one variable and                          **")
    print("  ** V248 vs V247 is one variable -- flying this first wastes the discrimination.                       **")
    print("  ** COST: ~101 counts is ~3.3% of the 3072 forward clamp, engaged only. If LKAS                        **")
    print("  ** feels reluctant, FactorB back to 1024 returns you to V247 exactly.                                 **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
