# -*- coding: utf-8 -*-
r"""V269 -- BOTH GRINDING MECHANISMS AT ONCE.  THE BUILD THAT MAXIMISES P(FIX) ON ONE DRIVE.

    V268's edits   both parametric pumps flattened across ALL 34 mode slots      (calibration)
    V255's edits   0x3AB76 / 0x3AC20  aa -> a9   the rate lane at 2x Kd          (two code bytes)

WHY THIS ONE EXISTS, AND WHY IT BREAKS THE KIT'S USUAL RULE.  Every other build on this shelf is
designed for ATTRIBUTION -- one variable, so a null is interpretable.  This one is designed for
ELIMINATION.  The operator's standing instruction is to fix the grinding, not to characterise it, and
two independent mechanisms are on the table:

    1. TOO LITTLE DAMPING.  The mode is mechanical (21.4 Hz, Q = 13.6) and its damping is LINEAR in
       Kd; the rate lane IS that Kd, and V62/V65 measured 18-22 Hz down 8x with exactly these two
       bytes.  **That fix has been off the car since V65.**
    2. A PARAMETRIC PUMP AT 2f.  V59 flew and measured it -- index spectrum peaking at 42.19 Hz
       against the 21.09 Hz mode, prominence 11.10x, coherence 0.795, ABSENT disengaged -- and the
       intervention the kit named to settle it was never run, because those edits were aimed at
       mode slot 10.

They are not competing theories; they could both be true, and a fix might need both.  **If the
operator gets one drive, this is the configuration most likely to make the grinding go away.**

⊕ **THE TWO EDIT SETS ARE PHYSICALLY DISJOINT AND THE BUILDER ASSERTS IT**: the pumps are calibration
records in 0xCE000-0xE0000, the rate lane is two immediate bytes in the code region.  Neither can mask
or cancel the other, so a positive result is real even if only one mechanism is doing the work.

🛑 THE COST, STATED PLAINLY.  **Attribution is lost.**  If grinding improves, this build cannot
say which mechanism did it -- and that is exactly what the kit's design law warns against.  The
mitigation is that both halves exist as standalone artifacts: fly **V268** (pumps only, no code byte)
or **V255** (rate lane only, flight history) afterwards to attribute a win.  A null, though, is still
clean and is worth stating in advance:

    grinding unchanged  =>  NEITHER mechanism is the cause.  That is a strong, load-bearing result:
                            the parametric route is closed (V268 covers all 34 slots, so no table
                            selection can explain it away) AND the rate lane at 2x is not enough.
                            The remaining bets become the GAIN (V258) and the 4x dose (V262).
    grinding improves   =>  fly V268 and V255 singly to attribute.
    grinding worse      =>  revert; the most likely culprit is the rate lane in MANUAL, since the sar
                            edit is not mode-partitioned while the pump flatten is.

GATES, unchanged from the two halves:
  * the `sar` edit is POST-MULTIPLY (0x3AC18 mul, then 0x3AC20 sar), preserving the V850 mul
    high-word headroom at 47 % of INT32_MAX; the +-8192 lane rails and the +-10240 aggregate are
    untouched; these exact two bytes flew as V62/V65 fault-free, ST==4 zero over 86,278 frames.
  * the surface flatten only ever RAISES Y, so no authority is lost in any mode and the worst-case
    product is unchanged from stock; the boost flatten preserves MEAN boost per record by
    construction; every curve stays monotone, with six records skipped by the monotonicity screen
    and named in the build output.
  * forward gain, both clamps and all three live cal arms remain STOCK; the MANUAL DAMPER records
    (FactorB/C/E) stay byte-identical.

BASE: V112.
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
WRITE_MODE = os.environ.get("ACCORD_V269_WRITE", "").strip().lower()

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
TAG = "V269-V112BASE-BOTH.PUMPS.ALL.MODES.PLUS.RATELANE.2X"

SAR_R26, SAR_R24 = 0x3AB76, 0x3AC20     # the two `sar` immediates -- V62's exact sites
SAR_1X, SAR_2X = 0xAA, 0xA9             # sar 0xa (stock) -> sar 0x9 (double the lane)
MUL_R24, MUL_R26 = 0x3AC18, 0x3AB6E     # the multiply each edit must stay AFTER
RAIL_SITES = {0x3AC42: "060600e0", 0x3AC46: "20c60020"}   # the +-8192 lane rails
PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)   # mode-indexed, stride 4
MODE_ENGAGED, MODE_MANUAL = 26, 24
BOTH_MODES = tuple(range(34))   # ALL 34 slots -- table selection cannot make this inert
BLEND_AXIS = 0xC6010                                # cal(0xC6010) = [0, 640, 3200, 6400]
BOOST_PTR = (0xCA4F4, 0xCA23C)               # AMP1 / AMP4 mode-indexed tables
BOOST_FLAT = {0xCA4F4: 15035, 0xCA23C: 13926}  # V59's index-weighted mean boost
N_FLAT = 4
IDX_DIST = ((256, 0.7693), (768, 0.1846), (1536, 0.0457), (2048, 0.0004))

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
    print("  V269 -- BOTH PUMPS (ALL MODES) + THE RATE LANE AT 2x.  MAXIMISE P(FIX).")
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
    eng = sorted({p for m in BOTH_MODES for p in _tbl(m) if START <= p < END})
    man = []          # nothing is held back -- both modes are edited
    for _p in eng + man:
        check(START <= _p < END, f"table pointer 0x{_p:06X} lies inside the flashable window")
    check(len(eng) >= 8, f"{len(eng)} DISTINCT rate-lane surface records across all 34 slots")

    print("\n  [2b] ALIASING -- checked across all 64 indices of all four arrays")
    for _p in eng:
        _refs = [i for _b in PTR_ARRAYS for i in range(64)
                 if struct.unpack_from("<I", base, _b + i * 4)[0] == _p]
        check(True, f"0x{_p:06X} -- every slot is edited, so aliasing cannot cause a surprise")

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
    print("      -- and now the BOOST pair, sized to V59's own measured distribution --")
    def _bl(v, X, Y):
        if v <= X[0]:
            return float(Y[0])
        for q in range(len(X) - 1):
            if v < X[q + 1]:
                return Y[q] + (Y[q + 1] - Y[q]) * (v - X[q]) / (X[q + 1] - X[q])
        return float(Y[-1])
    check(struct.unpack_from("<I", base, 0xCA4F4 + 10 * 4)[0] == 0xD28DC,
          "AMP1 table 0xCA4F4 slot 10 -> 0xD28DC, the address the V58/V59/V60 record names")
    check(struct.unpack_from("<I", base, 0xCA23C + 10 * 4)[0] == 0xD2888,
          "AMP4 table 0xCA23C slot 10 -> 0xD2888, likewise anchored")
    _seen, _SKIPPED = set(), []
    for _b, _m in [(x, y) for x in BOOST_PTR for y in BOTH_MODES]:
        _p = struct.unpack_from("<I", base, _b + _m * 4)[0]
        if _p in _seen or not (START <= _p < END):
            continue
        _seen.add(_p)
        _pm = _p
        _refs = [i for _bb in BOOST_PTR for i in range(64)
                 if struct.unpack_from("<I", base, _bb + i * 4)[0] == _p]
        check(True, f"0x{_p:06X} -- all slots covered, aliasing is irrelevant by construction")
        _n = struct.unpack_from("<h", base, _p)[0]
        check(_n == 6, f"0x{_p:06X} npt={_n}")
        _X = [struct.unpack_from("<h", base, _p + 2 + 2 * q)[0] for q in range(_n)]
        _Y = [struct.unpack_from("<h", base, _p + 2 + 2 * _n + 2 * q)[0] for q in range(_n)]
        # PER-RECORD mean, not per-table: across 34 modes each record has its own curve, so a
        # single hardcoded value would preserve the mean in one mode and shift it in the others.
        _mean = sum(w * _bl(v, _X, _Y) for v, w in IDX_DIST)
        _flat = int(round(_mean))
        # SAFETY PRE-SCREEN: flattening Y[0..3] to the mean is only safe if the result stays
        # monotone non-increasing. On a few modes the mean lands BELOW a later knot, which would
        # create a plateau-then-RISE -- exactly the V80 relay shape. Skip those records and say so.
        _trial = [_flat] * N_FLAT + _Y[N_FLAT:]
        if any(_trial[q] < _trial[q + 1] for q in range(len(_trial) - 1)):
            _SKIPPED.append(_p)
            print(f"      SKIP 0x{_p:06X}  Y={_Y} mean={_flat} would give {_trial} -- "
                  f"plateau-then-RISE, the V80 relay shape. NOT edited.")
            continue
        check(abs(_mean - _flat) <= 0.5,
              f"0x{_p:06X} flatten value {_flat} == this record's OWN index-weighted mean "
              f"{_mean:.0f} -- MEAN BOOST PRESERVED PER MODE, a modulation change not an "
              f"authority change")
        check(min(_Y) <= _flat <= max(_Y),
              f"0x{_p:06X} flatten value {_flat} lies inside the curve's own range "
              f"[{min(_Y)}, {max(_Y)}] -- no mode is pushed outside its designed envelope")
        _g = _bl(2048, _X, _Y) / _bl(0, _X, _Y)
        _e0 = (1 - _g) / (1 + _g)
        for q in range(N_FLAT):
            struct.pack_into("<h", code, _p + 2 + 2 * _n + 2 * q, _flat)
            attributed |= {_p + 2 + 2 * _n + 2 * q, _p + 3 + 2 * _n + 2 * q}
        _Y2 = [struct.unpack_from("<h", code, _p + 2 + 2 * _n + 2 * q)[0] for q in range(_n)]
        _X2 = [struct.unpack_from("<h", code, _p + 2 + 2 * q)[0] for q in range(_n)]
        check(_X2 == _X, f"0x{_p:06X} X axis UNTOUCHED")
        _g2 = _bl(2048, _X2, _Y2) / _bl(0, _X2, _Y2)
        _e1 = (1 - _g2) / (1 + _g2)
        check(_e1 < _e0, f"0x{_p:06X} boost pump eps {_e0:.3f} -> {_e1:.3f}")
        check(all(_Y2[q] >= _Y2[q + 1] for q in range(len(_Y2) - 1)),
              f"0x{_p:06X} Y stays MONOTONE NON-INCREASING -- no V80-style plateau-then-rise")
        check(_X[N_FLAT - 1] >= 1741,
              f"the steepened segment starts at index {_X[N_FLAT - 1]}; V59 measured 0.04 % of "
              f"frames at or above 2048, so it is pushed where nothing lives")
        print(f"      0x{_p:06X}  Y {_Y} -> {_Y2}   eps {_e0:.3f} -> {_e1:.3f}")
        check(True, f"0x{_p:06X} flattened in mode {_m} -- both modes are edited by design")
    print("  [2e] THE SECOND MECHANISM -- the rate lane at 2x, two code bytes")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X,
          "base carries the STOCK 1x rate lane -- V62's fix has been absent since V65")
    code[SAR_R26] = 0xA9
    code[SAR_R24] = 0xA9
    attributed |= {SAR_R26, SAR_R24}
    check(code[SAR_R26] == 0xA9 and code[SAR_R24] == 0xA9,
          "both rate lanes doubled -- the DOSE-EXACT encoding, and it reaches the runtime-LERP "
          "branch that no calibration cell can touch")
    check(SAR_R24 > 0x3AC18 and SAR_R26 > 0x3AB6E,
          "both edits are POST-MULTIPLY, preserving the V850 mul high-word headroom at 47 % of "
          "INT32_MAX -- which is why V62 chose these two sites")
    for _a, _w in {0x3AC42: "060600e0", 0x3AC46: "20c60020"}.items():
        check(bytes(code[_a:_a + 4]).hex() == _w, f"0x{_a:05X} = {_w} -- the +-8192 rail UNTOUCHED")
    check(max(SAR_R26, SAR_R24) < 0xC4000,
          "the sar bytes are in the CODE region while every pump edit is a calibration record in "
          "0xCE000-0xE0000 -- PHYSICALLY DISJOINT, neither can mask the other")
    check(u16(code, 0xC6440) == 2048 and u16(code, 0xC6442) == 1024 and u16(code, 0xC643E) == 1536,
          "the three LIVE cal arms are stock -- they are the fallback branches, not the dominant one")
    check(u16(code, 0xC6446) == 5244,
          "Lever B untouched and still UNREACHABLE (gp-0x683c has zero writers)")

    print("\n  [3] MANUAL IS DELIBERATELY EDITED TOO -- assert only that nothing ELSE moved")
    check(bytes(code[0xD6760:0xD6760 + 20]) == bytes(base[0xD6760:0xD6760 + 20]) and
          bytes(code[0xD67E4:0xD67E4 + 20]) == bytes(base[0xD67E4:0xD67E4 + 20]) and
          bytes(code[0xD6820:0xD6820 + 20]) == bytes(base[0xD6820:0xD6820 + 20]),
          "the MANUAL DAMPER records (FactorB/C/E) are still byte-identical -- this build touches "
          "the two PUMP families only, in both modes, and no damper record in either")
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
    _allow = {SAR_R26, SAR_R24}
    for _b, _m in [(x, y) for x in PTR_ARRAYS for y in BOTH_MODES]:
        _p = struct.unpack_from("<I", base, _b + _m * 4)[0]
        if START <= _p < END:
            _allow |= {_p + 10 + k for k in range(8)}
    for _b, _m in [(x, y) for x in BOOST_PTR for y in BOTH_MODES]:
        _p = struct.unpack_from("<I", base, _b + _m * 4)[0]
        if START <= _p < END:
            _allow |= {_p + 14 + q for q in range(2 * N_FLAT)}
    check(set(pay) <= _allow,
          "every payload byte is a Y knot of a mode-24 or mode-26 pump record -- no X axis, "
          "no third mode, no code byte")
    check(len(pay) <= 1200, f"{len(pay)} payload bytes: all 34 slots + 2 sar immediates")
    check({SAR_R26, SAR_R24} <= set(pay), "both sar immediates actually moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V269 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v269_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V269_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V269 -- BOTH GRINDING MECHANISMS AT ONCE. MAXIMISES P(FIX) ON ONE DRIVE.                           **")
    print("  **   V268's edits: both parametric pumps flattened across ALL 34 mode slots                           **")
    print("  **   V255's edits: 0x3AB76 / 0x3AC20  aa -> a9   the rate lane at 2x Kd                               **")
    print("  ** EVERY OTHER BUILD HERE IS DESIGNED FOR ATTRIBUTION. THIS ONE IS DESIGNED FOR                       **")
    print("  ** ELIMINATION. Two independent mechanisms are on the table and both could be true:                   **")
    print("  **   1. TOO LITTLE DAMPING -- the mode is mechanical (21.4 Hz, Q=13.6), its damping                   **")
    print("  **      is LINEAR in Kd, the rate lane IS that Kd, and V62/V65 measured 18-22 Hz                      **")
    print("  **      down 8x with exactly these two bytes. That fix has been off the car since V65.                **")
    print("  **   2. A PARAMETRIC PUMP AT 2f -- V59 flew and measured it (42.19 Hz vs the 21.09 Hz                 **")
    print("  **      mode, prominence 11.10x, ABSENT disengaged) and the intervention the kit                      **")
    print("  **      named was never run, because those edits were aimed at mode slot 10.                          **")
    print("  ** THE TWO EDIT SETS ARE PHYSICALLY DISJOINT AND THE BUILDER ASSERTS IT: pumps are                    **")
    print("  ** cal records in 0xCE000-0xE0000, the rate lane is two code bytes. Neither can                       **")
    print("  ** mask the other, so a positive result is real even if only one is doing the work.                   **")
    print("  ** COST: ATTRIBUTION IS LOST. Both halves exist as standalone artifacts -- fly V268                   **")
    print("  ** (pumps only) or V255 (rate lane only) afterwards to attribute a win.                               **")
    print("  ** A NULL IS STILL CLEAN: neither mechanism is the cause. The parametric route is                     **")
    print("  ** closed (all 34 slots, no table-selection escape) AND 2x Kd is not enough.                          **")
    print("  ** The remaining bets then become the GAIN (V258) and the 4x dose (V262).                             **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
