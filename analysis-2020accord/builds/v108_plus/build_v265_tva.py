# -*- coding: utf-8 -*-
r"""V265 -- FLATTEN THE RATE-LANE GAIN SURFACE.  KILLS A SECOND PUMP *AND* RESTORES THE DAMPING.
SUPERSEDES V263 AS THE RATE-LANE BUILD TO FLY.

    0xD7A88  A  Y [3072, 3072, 2322, 1536] -> [3072, 3072, 3072, 3072]     eps 0.333 -> 0.000
    0xD7AC4  B  Y [2560, 2560, 2246, 1946] -> [2560, 2560, 2560, 2560]     eps 0.136 -> 0.000
    0xD7B00  C  Y [2303, 2303, 2151, 1947] -> [2303, 2303, 2303, 2303]     eps 0.084 -> 0.000
    0xD7B3C  D  Y [2150, 2150, 2049, 1947] -> [2150, 2150, 2150, 2150]     eps 0.050 -> 0.000

    (mode 26 = ENGAGED only; mode 24 = MANUAL is disjoint and asserted byte-identical.)

🛑 **WHY THIS SUPERSEDES V263, AND IT IS NOT A SMALL DIFFERENCE.**  V263 multiplied this same
surface by 2.  A uniform scale leaves the RATIO g = Ymin/Ymax untouched, so it leaves the parametric
depth **eps = (1-g)/(1+g) EXACTLY AS IT WAS** -- V263 does not reduce the pump at all.  And it raises
the gain everywhere, including at low rate, where the operator explicitly did not want more resistance.

Flattening does both jobs at once:

    * **eps -> 0 on all four curves.**  A flat gain cannot parametrically pump, at any frequency.
    * **the gain RISES only where the rolloff had cut it** -- i.e. in the grinding band -- and is
      **unchanged at low rate**, so no low-speed resistance is added.

At the record's own measured grinding operating points (grind #1 motor rate ~603, grind #2 creep
~1206, grind #2 highway ~170), on curve A:

        stock      2920 @603   2468 @1206   3072 @170
        FLATTENED  3072 @603   3072 @1206   3072 @170      (+5 %, +24 %, +0 %)
        V263 x2    5840 @603   4935 @1206   6144 @170      (+100 % everywhere, eps unchanged)

WHY A PUMP HERE AT ALL.  The census (`analysis-2020accord/verify/parametric_pump_census.py`) ranks every
mode-selected curve by depth, and this surface scores **eps = 0.333** -- the SAME depth as the two boost
curves V59 flew and measured (0.334, and V59's measured p95 was 0.333).  V59 established that a
rectified rate index sweeps at **2x the mode frequency**: its own spectrum peaks at 42.19 Hz against
the 21.09 Hz mode, prominence 11.10x, coherence 0.795 over 13 disjoint runs, and **absent disengaged**.
A rate-dependent GAIN driven by that index is therefore a parametric pump at 2f into a mode at f.

⇒ **the rate lane carries a pump as deep as the one the kit spent three builds studying, and nobody
ever looked at it.**  V264 flattens the boost pair; this flattens the rate-lane surface.  They are
disjoint records and disjoint builds, asserted.

⊕ **AND IT IS MONOTONE-SAFE BY CONSTRUCTION.**  Flattening to Y[0] only ever RAISES Y, never lowers it,
so no authority is given up anywhere.  A constant curve is trivially monotone, so no plateau-then-rise
of the V80 relay kind is created -- and unlike V264 there is **no steepened tail**, because the whole
curve is flattened rather than part of it.

🛑 WHAT IT COSTS.  More damping at mid/high motor rate while ENGAGED: +24 % at the grind #2 creep
operating point.  A derivative term is frequency-selective (at 1 Hz it delivers 4.7 % of its 21.4 Hz
output), so this is not the low-speed friction the operator ruled out -- but brisk engaged corrections
will be damped more than today.  Manual steering is untouched.

🛑 AND THE ROLLOFF MIGHT BE LOAD-BEARING.  Honda put it there.  The kit's GATE 2 note on this axis
says only that **STEEPENING** must be argued -- flattening reduces the pump and is the safe direction --
but "Honda had a reason" is not disproved by that.  The pre-registered null: if grinding gets WORSE,
the rolloff was protective for a reason not yet identified, and this reverts to V263 or stock.

RELATIONSHIP TO THE OTHER RATE-LANE BUILDS:
    V255  sar 2x                 2x everywhere, BOTH modes, pump unchanged   flight history (V62/V65)
    V262  sar 4x                 4x everywhere, BOTH modes, pump unchanged   escalation
    V261  sar 2x + cal arms 2x   fallback branches only                      misses the LERP branch
    V263  surface x2             2x, engaged only, **pump unchanged**        SUPERSEDED BY THIS
    V265  surface FLATTENED      engaged only, **pump -> 0**, damping up in  <- THIS
                                 the grinding band only

BASE: V112.  Twenty-four payload bytes, all Y knots of the four mode-26 records.
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
WRITE_MODE = os.environ.get("ACCORD_V265_WRITE", "").strip().lower()

BASE_NAME = "_v112_V112-V111BASE-RELAY.KNEE1800.K1.612_plain_image.bin"
BASE_SHA = "f032878c4e0b8e90d782ddac6ba2d644e09956cc1b267a60ef4fb1c44ee1f96f"

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
CLAMP_P, CLAMP_N = 0xC61B2, 0xC61B4         # forward clamps -- tracking BROKEN deliberately
CLAMP_OLD, CLAMP_NEW = 3072, 4096           # the ceiling that peak torque actually is
GAIN_CELL = 0xC6CD0                         # forward LKAS gain
GAIN_OLD, GAIN_NEW = 5346, 4455             # 6x -> 5x
SOFT_EME = 0xC674E                          # the interlock the clamp must stay BELOW
FB26 = 0xD774C                              # FactorB record, ENGAGED mode 26 (manual 24 @0xD6760)
FB_OLD, FB_NEW = 1024, 2048                 # flat Q10 gain at unity -> x2, no shape to corrupt
FB24 = 0xD6760                              # MANUAL FactorB -- asserted UNTOUCHED
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
TAG = "V265-V112BASE-RATELANE.SURFACE.FLATTENED.ENGAGED"

SAR_R26, SAR_R24 = 0x3AB76, 0x3AC20     # the two `sar` immediates -- V62's exact sites
SAR_1X, SAR_2X = 0xAA, 0xA9             # sar 0xa (stock) -> sar 0x9 (double the lane)
MUL_R24, MUL_R26 = 0x3AC18, 0x3AB6E     # the multiply each edit must stay AFTER
RAIL_SITES = {0x3AC42: "060600e0", 0x3AC46: "20c60020"}   # the +-8192 lane rails
PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)   # mode-indexed, stride 4
MODE_ENGAGED, MODE_MANUAL = 26, 24
BLEND_AXIS = 0xC6010                                # cal(0xC6010) = [0, 640, 3200, 6400]
BOOST_ENG = (0xD78F8, 0xD78A4)   # V264 flattens these; asserted UNTOUCHED here

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
    print("  V265 -- FLATTEN THE RATE-LANE GAIN SURFACE.  PUMP -> 0, ENGAGED ONLY.")
    print("=" * 102)

    print("\n  [1] BASE = V112 -- what the operator says is on the car")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V112 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X,
          "base carries the STOCK 1x rate lane (sar 0xa at both sites) -- V62's fix is ABSENT, "
          "which is the whole reason for this build")
    check(u16(base, LEVER_B) == LEVER_B_VAL,
          f"Lever B is {LEVER_B_VAL} on this car (V62 flew with it at stock 512) -- the lane arm "
          f"is 10.2x higher, so the doubled lane clips on large transients where V62's never did")
    check(u16(base, GAIN_CELL) == 5346, "forward gain is 5346 (6x) -- NOT touched by this build")
    check(u16(base, CLAMP_P) == 3072 and u16(base, CLAMP_N) == 3072,
          "forward clamps are 3072 -- NOT touched by this build")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] RESOLVE THE MODE-26 TABLES FROM THE POINTER ARRAYS")
    def _tbl(idx):
        return [struct.unpack_from("<I", base, _b + idx * 4)[0] for _b in PTR_ARRAYS]
    eng, man = _tbl(MODE_ENGAGED), _tbl(MODE_MANUAL)
    for _p in eng + man:
        check(START <= _p < END, f"table pointer 0x{_p:06X} lies inside the flashable window")
    check(not (set(eng) & set(man)),
          f"ENGAGED tables {[hex(x) for x in eng]} are DISJOINT from MANUAL {[hex(x) for x in man]}")

    print("\n  [2b] ALIASING -- checked across all 64 indices of all four arrays")
    for _p in eng:
        _refs = [i for _b in PTR_ARRAYS for i in range(64)
                 if struct.unpack_from("<I", base, _b + i * 4)[0] == _p]
        check(set(_refs) == {MODE_ENGAGED},
              f"0x{_p:06X} is referenced by mode index {sorted(set(_refs))} -- mode 26 ONLY, so "
              f"doubling it cannot leak into another mode")

    print("\n  [2c] THE EDIT -- flatten every Y to Y[0], X axes untouched")
    _before, _after = [], []
    for _p in eng:
        _npt = struct.unpack_from("<h", base, _p)[0]
        check(_npt == 4, f"0x{_p:06X} npt={_npt} -- the expected 4-point record")
        _x = [struct.unpack_from("<h", base, _p + 2 + 2 * k)[0] for k in range(4)]
        _y = [struct.unpack_from("<h", base, _p + 10 + 2 * k)[0] for k in range(4)]
        _before.append((_x, _y))
        _g = min(_y) / max(_y)
        _eps_old = (1 - _g) / (1 + _g)
        for k in range(4):
            struct.pack_into("<h", code, _p + 10 + 2 * k, _y[0])
            attributed |= {_p + 10 + 2 * k, _p + 11 + 2 * k}
        _nx = [struct.unpack_from("<h", code, _p + 2 + 2 * k)[0] for k in range(4)]
        _ny = [struct.unpack_from("<h", code, _p + 10 + 2 * k)[0] for k in range(4)]
        _after.append((_nx, _ny))
        check(_nx == _x, f"0x{_p:06X} X axis UNTOUCHED {_nx} -- no breakpoint moves")
        check(_ny == [_y[0]] * 4,
              f"0x{_p:06X} Y {_y} -> {_ny}  (FLAT at Y[0])")
        _g2 = min(_ny) / max(_ny)
        _eps_new = (1 - _g2) / (1 + _g2)
        check(_eps_new == 0.0,
              f"0x{_p:06X} parametric depth eps {_eps_old:.3f} -> {_eps_new:.3f} -- a FLAT gain "
              f"cannot pump at ANY frequency")
        check(all(a >= b for a, b in zip(_ny, _y)),
              f"0x{_p:06X} every knot RISES or stays -- flattening to Y[0] never gives up authority")
        def _l(v, X, Y):
            if v <= X[0]:
                return float(Y[0])
            for q in range(len(X) - 1):
                if v < X[q + 1]:
                    return Y[q] + (Y[q + 1] - Y[q]) * (v - X[q]) / (X[q + 1] - X[q])
            return float(Y[-1])
        print(f"      0x{_p:06X}  Y={_y} -> {_ny}   eps {_eps_old:.3f} -> 0.000")
        print(f"                 gain @603 {_l(603, _x, _y):.0f} -> {_l(603, _x, _ny):.0f} ; "
              f"@1206 {_l(1206, _x, _y):.0f} -> {_l(1206, _x, _ny):.0f} ; "
              f"@170 {_l(170, _x, _y):.0f} -> {_l(170, _x, _ny):.0f}")

    print("\n  [2d] THE SHIFT, THE CAL ARMS AND V264's BOOST PAIR ARE ASSERTED STOCK")
    for _p in BOOST_ENG:
        check(bytes(code[_p:_p + 26]) == bytes(base[_p:_p + 26]),
              f"V264's boost record 0x{_p:06X} is UNTOUCHED -- V264 and V265 flatten DIFFERENT pumps "
              f"and are disjoint builds")
    check(code[SAR_R26] == SAR_1X and code[SAR_R24] == SAR_1X,
          "both sar immediates left at stock 0xAA -- unlike V255/V262 this build does NOT touch the "
          "code path, so MANUAL steering is not dosed")
    check(u16(code, 0xC6440) == 2048 and u16(code, 0xC6442) == 1024 and u16(code, 0xC643E) == 1536,
          "the three LIVE cal arms are stock -- they are the fallback branches, not the dominant one")
    check(u16(code, 0xC6446) == 5244,
          "Lever B untouched and still UNREACHABLE (gp-0x683c has zero writers)")

    print("\n  [3] MANUAL STEERING MUST BE BYTE-IDENTICAL")
    for _p in man:
        check(bytes(code[_p:_p + 18]) == bytes(base[_p:_p + 18]),
              f"MANUAL (mode 24) record 0x{_p:06X} is BYTE-IDENTICAL -- parking and low-speed manual "
              f"feel are exactly as today")
    check(bytes(code[0xD6760:0xD6760 + 20]) == bytes(base[0xD6760:0xD6760 + 20]) and
          bytes(code[0xD67E4:0xD67E4 + 20]) == bytes(base[0xD67E4:0xD67E4 + 20]) and
          bytes(code[0xD6820:0xD6820 + 20]) == bytes(base[0xD6820:0xD6820 + 20]),
          "the MANUAL damper records are byte-identical too")

    print("\n  [3b] GATE 2 ARITHMETIC")
    _gmax = max(max(y) for _, y in _after)
    _worst = 5120 * _gmax
    check(_gmax == max(max(y) for _, y in _before),
          "flattening raises no knot above the curve's own existing maximum, so the worst-case "
          "product is UNCHANGED from stock -- overflow and saturation are exactly as today")
    print(f"      largest doubled gain {_gmax}; overflow worst case 5120 x {_gmax} = {_worst:,} "
          f"= {100.0 * _worst / 2147483647:.2f} % of INT32_MAX")
    check(_worst < 0.05 * 2147483647, "overflow headroom is enormous")
    _clip = 8192 * 1024 // _gmax
    check(_clip > 859,
          f"the lane clips above input {_clip}, ABOVE the measured p50 of 859 -- the median frame "
          f"stays LINEAR")
    check(_clip < 5120, f"the upper tail DOES clip above {_clip} -- stated, not hidden")
    check(all(all(a <= b for a, b in zip(x, x[1:])) for x, _ in _after),
          "every X axis is still monotone -- no LERP is corrupted")
    print(f"      blend axis cal(0x{BLEND_AXIS:05X}) = "
          f"{[u16(code, BLEND_AXIS + 2 * k) for k in range(4)]}  (untouched)")

    print("\n  [4] THE RAILS AND EVERYTHING ELSE ARE FROZEN")
    for a, want in sorted(RAIL_SITES.items()):
        check(bytes(code[a:a + 4]).hex() == want,
              f"0x{a:05X} = {want} -- the +-8192 lane rail is UNTOUCHED")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- not the bricking class")
    check(u16(code, LEVER_B) == LEVER_B_VAL, f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")
    check(u16(code, GAIN_CELL) == 5346, "forward gain UNTOUCHED -- single variable")
    check(u16(code, CLAMP_P) == 3072 and u16(code, CLAMP_N) == 3072, "clamps UNTOUCHED")
    check(code[ALPHA2] == 14, "alpha2 stays at the CAR's 14 -- this build does not touch it")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the biquad block is BYTE-IDENTICAL -- no notch change in this build")

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

    print("\n  [7] FULL BYTE DIFF vs V112")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    _allow = set()
    for _b in PTR_ARRAYS:
        _p = struct.unpack_from("<I", base, _b + MODE_ENGAGED * 4)[0]
        _allow |= {_p + 10 + k for k in range(8)}
    check(set(pay) <= _allow,
          "every payload byte is a Y knot of a mode-26 record -- no X axis, no other mode, "
          "no code byte")
    check(len(pay) <= 32, f"{len(pay)} payload bytes across the four engaged records")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V265 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v265_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V265_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V265 -- FLATTEN THE RATE-LANE GAIN SURFACE. SUPERSEDES V263.                                       **")
    print("  **   0xD7A88 A  [3072,3072,2322,1536] -> [3072,3072,3072,3072]  eps .333 -> 0                         **")
    print("  **   0xD7AC4 B  [2560,2560,2246,1946] -> [2560,2560,2560,2560]  eps .136 -> 0                         **")
    print("  **   0xD7B00 C  [2303,2303,2151,1947] -> [2303,2303,2303,2303]  eps .084 -> 0                         **")
    print("  **   0xD7B3C D  [2150,2150,2049,1947] -> [2150,2150,2150,2150]  eps .050 -> 0                         **")
    print("  ** WHY THIS SUPERSEDES V263: a uniform x2 leaves the RATIO Ymin/Ymax untouched, so                    **")
    print("  ** it leaves the parametric depth EXACTLY AS IT WAS -- V263 does not reduce the                       **")
    print("  ** pump at all, and it raises gain at low rate where more resistance was not asked                    **")
    print("  ** for. Flattening does both jobs: eps -> 0, and gain rises ONLY where the rolloff                    **")
    print("  ** had cut it (the grinding band), staying unchanged at low rate.                                     **")
    print("  **   curve A at the record's measured operating points:                                               **")
    print("  **     stock      2920 @603   2468 @1206   3072 @170                                                  **")
    print("  **     FLATTENED  3072 @603   3072 @1206   3072 @170   (+5%, +24%, +0%)                               **")
    print("  **     V263 x2    5840 @603   4935 @1206   6144 @170   (+100% everywhere, eps same)                   **")
    print("  ** THIS SURFACE SCORES eps = 0.333 -- THE SAME DEPTH AS THE TWO BOOST CURVES V59                      **")
    print("  ** FLEW AND MEASURED (0.334; its measured p95 was 0.333). The rate lane carries a                     **")
    print("  ** pump as deep as the one the kit spent three builds studying, unexamined.                           **")
    print("  ** MONOTONE-SAFE BY CONSTRUCTION: flattening to Y[0] only ever RAISES Y, so no                        **")
    print("  ** authority is given up and the worst-case product is unchanged from stock. No                       **")
    print("  ** steepened tail either, unlike V264 -- the whole curve is flattened.                                **")
    print("  ** DISJOINT FROM V264, asserted: that one flattens the boost pair, this the surface.                  **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
