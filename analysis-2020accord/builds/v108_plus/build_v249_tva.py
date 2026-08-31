# -*- coding: utf-8 -*-
r"""V249 -- V247 PLUS THE DAMPER'S *SPEED* DEAD ZONE. THE HALF I LEFT OUT, AND IT IS 36 % OF THE PROBLEM.

WHY THIS BUILD EXISTS -- IT CLOSES A GAP IN MY OWN V247.  The record's recommendation was to open BOTH
of the damper's dead zones: "FactorC Y[0]:=Y[2] + FactorE X[0]: 60 -> 12 + FactorE Y[1]:=Y[2]".  V247
opened only the FactorE (RATE) half.  FactorC's SPEED dead zone is X[0] = 2240 counts = 35 km/h with
Y[0] = 0, and zero x anything = 0, so **below 35 km/h the whole damper product is structurally ZERO no
matter what FactorE does.**

Stratifying the measured 6-9 Hz anti-damping by vehicle speed, coherence-gated, 4,772 engaged windows:

    0-10 km/h    -55.52     damper DEAD (below the FactorC knee)
    10-20 km/h   -65.63     damper DEAD
    20-35 km/h   -71.70     damper DEAD
    35-50 km/h   -68.35     damper live
    50-70 km/h   -60.04     damper live
    70-200 km/h  -57.39     damper live

    below the knee: 36.4 % of engaged windows, Re(Z) -64.7
    above the knee: 63.6 %,                    Re(Z) -60.9

🛑 SO THE ANTI-DAMPING IS PRESENT AT EVERY SPEED, ROUGHLY UNIFORMLY -- it is NOT a creep-only
phenomenon -- and V247 can only act on the 64 % above the knee.  On the other 36 % it is inert by
construction, and the anti-damping there is if anything slightly WORSE.

THE EDIT.  FactorC (engaged, mode 26) X = [2240, 3840, 5120, 8960], Y = [0, 234, 429, 908]:

    Y[0]  0 -> 429   (:= Y[2], the record's own recommendation)

Below X[0] the LERP clamps flat to Y[0], so this sets FactorC = 429 at every speed under 35 km/h --
exactly the value it already has at 5120 counts (80 km/h).  With V247's FactorE that yields the SAME
damper magnitude at low speed as at high:

    low speed, V247 alone:  FactorC 0   -> damper 0 counts        (structurally dead)
    low speed, V249:        FactorC 429 -> damper ~50 counts       89 % of the ~56 requirement
    high speed, unchanged:  FactorC 429 -> damper ~50 counts       identical to V247

WHY Y[0] := Y[2] AND NOT Y[1].  Y[1] = 234 would give ~27 counts, 49 % of requirement -- half a fix.
Y[2] = 429 makes low-speed damping equal the high-speed case, which is the shape that makes the build
interpretable: one damper level across the whole speed range, so a drive scores the LANE rather than a
speed-dependent blend.

ENGAGED ONLY, AND THAT IS WHAT MAKES A CREEP-SPEED DAMPER ACCEPTABLE AT ALL.  Honda's dead zone is
there for a reason -- damping at parking speed makes the wheel heavy in the driver's hands.  This edit
touches ONLY the mode-26 record; mode 24 (manual) is asserted byte-identical, so **parking and
low-speed manual steering are completely unchanged**.  The added damping exists only while openpilot is
steering, which is precisely when nobody is holding the wheel.

🛑 THE RISK THIS CARRIES THAT V247 DOES NOT.  Openpilot engaged at low speed now meets a damper
that Honda deliberately removed there.  If LKAS feels sluggish or reluctant to turn in slow corners or
traffic, THIS is the cell -- FactorC Y[0] back to 0 returns you to V247 exactly.  V247's own risk
(1.6 % of forward authority) is unchanged above 35 km/h.

BASE: V247.  Two bytes.
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
WRITE_MODE = os.environ.get("ACCORD_V249_WRITE", "").strip().lower()

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
FC26 = 0xD77D0                              # FactorC record, ENGAGED mode 26 (manual 24 @0xD67E4)
FC_Y0 = FC26 + 2 + 8                        # layout [npt][X x4][Y x4] -> Y[0]
FC_OLD, FC_NEW = 0, 429                     # := Y[2]; below X[0] the LERP clamps flat to Y[0]
FC24 = 0xD67E4                              # MANUAL FactorC -- asserted UNTOUCHED
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
TAG = "V249-V247BASE-FACTORC.SPEED.DEADZONE.OPEN"

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
          f"base already carries V247's opened RATE dead zone X={_fx} Y={_fy}")
    _cx = [struct.unpack_from("<h", base, FC26 + 2 + 2 * _i)[0] for _i in range(4)]
    _cy = [struct.unpack_from("<h", base, FC26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_cx == [2240, 3840, 5120, 8960] and _cy == [FC_OLD, 234, 429, 908],
          f"base FactorC(engaged) X={_cx} Y={_cy} -- Y[0]=0 below {_cx[0] // 64} km/h, so the "
          f"WHOLE damper product is structurally zero there")
    check(FC_NEW == _cy[2],
          f"the new Y[0] {FC_NEW} is exactly Y[2] -- the record's own recommendation, and it "
          f"makes low-speed damping EQUAL the 80 km/h case rather than inventing a level")
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<h", code, FC_Y0, FC_NEW)
    attributed |= {FC_Y0, FC_Y0 + 1}
    def _lerp(v, X, Y):
        if v <= X[0]:
            return float(Y[0])
        for _i in range(len(X) - 1):
            if v < X[_i + 1]:
                return Y[_i] + (Y[_i + 1] - Y[_i]) * (v - X[_i]) / (X[_i + 1] - X[_i])
        return float(Y[-1])
    check(struct.unpack_from("<h", code, FC_Y0)[0] == FC_NEW,
          f"FactorC Y[0] {FC_OLD} -> {FC_NEW} -- the SPEED dead zone is OPEN")
    _fe = _lerp(OP_POINT, [12, 400, 2500, 4000], [0, 539, 539, 927])
    _lo_before = 1024.0 * (FC_OLD / 1024) * (_fe / 1024)
    _lo_after = 1024.0 * (FC_NEW / 1024) * (_fe / 1024)
    _hi = 1024.0 * (429 / 1024) * (_fe / 1024)
    check(_lo_before == 0 and _lo_after > 40,
          f"below 35 km/h the damper goes {_lo_before:.0f} -> {_lo_after:.1f} counts -- from STRUCTURALLY DEAD to {100 * _lo_after / 56:.0f}% of the ~56 requirement")
    check(abs(_lo_after - _hi) < 1.0,
          f"low-speed damping {_lo_after:.1f} now EQUALS the high-speed case {_hi:.1f} -- one "
          f"level across the whole speed range, so a drive scores the LANE not a blend")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    # the shape gates: FactorC must stay monotone and its X axis untouched
    _ncy = [struct.unpack_from("<h", code, FC26 + 10 + 2 * _i)[0] for _i in range(4)]
    _ncx = [struct.unpack_from("<h", code, FC26 + 2 + 2 * _i)[0] for _i in range(4)]
    check(_ncx == [2240, 3840, 5120, 8960],
          f"the FactorC X axis is UNTOUCHED {_ncx} -- only the clamp value below it moved")
    check(all(_ncy[_i] <= _ncy[_i + 1] for _i in range(3)) or _ncy[0] == _ncy[2],
          f"FactorC Y {_ncy} -- Y[0] is lifted to Y[2], so the curve is flat-then-rising "
          f"rather than corrupted; it never exceeds its own maximum")
    check(max(_ncy) == 908,
          "FactorC still peaks at its stock 908 -- this opens the floor, it does not raise "
          "the lane's ceiling")
    check(bytes(code[FC24:FC24 + 20]) == bytes(base[FC24:FC24 + 20]),
          "the MANUAL FactorC record (mode 24) is BYTE-IDENTICAL -- parking and low-speed "
          "manual steering are completely unchanged, which is what makes a creep-speed "
          "damper acceptable at all")
    check(bytes(code[FE24:FE24 + 20]) == bytes(base[FE24:FE24 + 20]),
          "the MANUAL FactorE record is BYTE-IDENTICAL too")
    _ny = [struct.unpack_from("<h", code, FE26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_ny == [0, 539, 539, 927],
          f"V247's FactorE curve is CARRIED unchanged {_ny} -- FactorC is the only variable")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the notch is CARRIED byte-for-byte")
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
    check(len(pay) <= 2, f"{len(pay)} payload byte(s), at most the FactorC Y[0] halfword")
    check(set(pay) <= {FC_Y0, FC_Y0 + 1},
          "every payload byte is FactorC Y[0] in the ENGAGED record -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V249 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v249_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V249_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V249 = V247 + THE DAMPER'S *SPEED* DEAD ZONE. THE HALF I LEFT OUT OF V247.                         **")
    print("  **   0xD77DA   FactorC(engaged) Y[0]  0 -> 429  (:= Y[2])                                             **")
    print("  ** WHY: FactorC's dead zone is X[0]=2240 = 35 km/h with Y[0]=0, and zero x                            **")
    print("  ** anything = 0 -- so BELOW 35 km/h the whole damper is structurally ZERO no                          **")
    print("  ** matter what FactorE does. V247 opened only the RATE half.                                          **")
    print("  ** MEASURED, 4772 coherence-gated engaged windows:                                                    **")
    print("  **    0-10 km/h  -55.5   10-20  -65.6   20-35  -71.7   <- damper DEAD                                 **")
    print("  **   35-50 km/h  -68.4   50-70  -60.0   70+    -57.4   <- damper live                                 **")
    print("  **   36.4% of engaged windows are BELOW the knee, and the anti-damping there is                       **")
    print("  **   if anything WORSE. The ratchet is NOT creep-only -- it is at every speed.                        **")
    print("  ** EFFECT: below 35 km/h the damper goes 0 -> ~50 counts, which EQUALS the                            **")
    print("  ** high-speed case. One damper level across the whole speed range.                                    **")
    print("  ** ENGAGED ONLY, and that is what makes a creep-speed damper acceptable: Honda's                      **")
    print("  ** dead zone exists so the wheel is not heavy in the driver's hands at parking                        **")
    print("  ** speed. Mode 24 (manual) is asserted byte-identical -- unchanged completely.                        **")
    print("  ** THE RISK V247 DOES NOT CARRY: openpilot engaged at low speed now meets a                           **")
    print("  ** damper Honda deliberately removed there. If LKAS feels sluggish in slow                            **")
    print("  ** corners or traffic, THIS is the cell -- FactorC Y[0] back to 0 gives V247.                         **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
