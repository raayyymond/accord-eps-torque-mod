# -*- coding: utf-8 -*-
r"""V264 -- KILL THE PARAMETRIC PUMP.  THE INTERVENTION THIS KIT NAMED IN 2026-07 AND NEVER RAN.

    0xD78F8  AMP1  Y [16384, 14658, 11676, 9362, 8245, 8188] -> [15035, 15035, 15035, 15035, 8245, 8188]
    0xD78A4  AMP4  Y [16384, 14393, 10269, 8997, 8177, 8177] -> [13926, 13926, 13926, 13926, 8177, 8177]

    (mode 26 = ENGAGED only.  Mode 24 = MANUAL is a disjoint pair and is asserted byte-identical.)

🛑 **THIS IS A DIAGNOSTIC AS MUCH AS A FIX, AND THE KIT WROTE THE SPEC FOR IT ITSELF.**  V59 flew
2026-07-30 (route 2c) with a thermometer probe on `gp-0x6ba6` -- 50,963 frames, 100 % live, 100 %
monotonic, fault sentinel 0.000 % -- and MEASURED a parametric gain pump:

    the index's own spectrum peaks at 42.19 Hz = 2 x the 21.09 Hz mode, prominence 11.10x,
    coherence 0.795 vs the torsion bar (K=30, 13 DISJOINT runs, never spliced).
    The 18-26 Hz band shows only 1.23x -- the full-wave-rectification signature.
    Disengaged: bit5 NEVER toggles. 0/4 runs, 61.2 s, K=90, prominence 0.00x. **PUMP ABSENT.**

⇒ a parametric gain pump at **2f into a mode at f** -- the textbook parametric-resonance condition,
and the mode at f is the 21.4 Hz grinding mode.  The kit then wrote, verbatim:

    "🛑 CAUSALITY IS NOT SETTLED AND CANNOT BE FROM THIS DATA.  The index is |x| of a bar-derived
     signal, so 'pump tracks mode' is partly guaranteed by rectification: a mode dying for its own
     reasons quiets the bar, pins the index, and produces identical numbers.
     **Only an INTERVENTION (flatten the swept range, re-fly) separates drive from echo.**"

**That intervention was never built.**  V58/V59/V60 studied the curves at `0xD28DC`/`0xD2888`, which
are **mode slot 10** -- and this car runs modes 24/26, so those edits could not have reached it anyway
(the same table-selection trap that made V72/V73 inert).  This build is that intervention, on the
car's own mode.

THE MODE-26 CURVES, resolved through the pointer tables this session:

    AMP1 table base 0xCA4F4 (slot 10 -> 0xD28DC, byte-verified against the record)  idx 26 -> 0xD78F8
    AMP4 table base 0xCA23C (slot 10 -> 0xD2888, byte-verified against the record)  idx 26 -> 0xD78A4

Both stock curves have **epsilon = (1-g)/(1+g) = 0.334** over their full sweep, which matches V59's
measured p95 depth of **0.333** -- independent confirmation that these are the curves it measured.

HOW THE DOSE WAS SIZED -- from V59's OWN measured index distribution, not a guess:

    engaged + creep + sustained hands-off, n=5016:
        76.93 % <512  |  18.46 % 512-1k  |  4.57 % 1k-2k  |  0.04 % >=2048

    index-weighted mean boost:  AMP1 = 15035   AMP4 = 13926

Flattening Y[0..3] to that mean **preserves the mean boost by construction** -- so this is not an
authority change dressed up as a pump fix.  It removes the MODULATION and leaves the LEVEL.

    epsilon over [0, 2048]:   AMP1  0.222 -> 0.000      AMP4  0.301 -> 0.050

🛑 THE COST, STATED AS THE RECORD DEMANDS.  The kit's GATE 2 rule on this axis is: *"any edit that
STEEPENS it must state the new slope and argue the pump margin."*  This edit **does** steepen one
segment -- the one beyond the flattened region:

    AMP1  X[3]->X[4]:  -1.001 -> -6.084 per count
    AMP4  X[3]->X[4]:  -0.616 -> -4.319 per count

**Both of those segments begin at index 2529 and 1741 respectively, and V59 measured 0.04 % of frames
at or above 2048.**  The steepening is pushed into a region that essentially nothing occupies, while
the modulation is removed from the 99.96 % that does.  Net epsilon falls in both curves.  That is the
pump-margin argument the rule asks for.

WHAT EACH OUTCOME LICENSES -- pre-registered, because a null here is load-bearing:
  * grinding drops                  => the pump was DRIVING the mode, not echoing it.  Fifteen months
                                       of "nothing moves grinding" resolves, and the follow-up is to
                                       flatten harder / check the mode-24 twin.
  * grinding unchanged              => the pump was an ECHO.  V59's 11.10x prominence is then fully
                                       explained by rectification, the parametric route is CLOSED by
                                       experiment, and the rate lane (V255/V263) is the remaining bet.
  * grinding worse                  => the level, not the modulation, was doing the work; the mean-
                                       preserving assumption is wrong.  Revert.

⊕ GATE 1 vacuous -- calibration only, no cave.  GATE 2: mean boost preserved, monotonicity preserved,
both X axes untouched, no breakpoint moved.  **Mode 24 (MANUAL) is a disjoint pair at 0xD6914/0xD68C0
and is asserted byte-identical**, which resolves the record's own *"GATE 2 is NOT clean -- both sit on
the base-assist path and change manual feel"* caveat: that was written for a mode-10 edit, which is
not mode-partitioned.  This one is.

⊕ ALIASING CHECKED across all 64 indices of both pointer tables.

BASE: V112.  Sixteen payload bytes, all inside the two mode-26 boost records.
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
WRITE_MODE = os.environ.get("ACCORD_V264_WRITE", "").strip().lower()

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
TAG = "V264-V112BASE-PUMP.FLATTENED.ENGAGED"

SAR_R26, SAR_R24 = 0x3AB76, 0x3AC20     # the two `sar` immediates -- V62's exact sites
SAR_1X, SAR_2X = 0xAA, 0xA9             # sar 0xa (stock) -> sar 0x9 (double the lane)
MUL_R24, MUL_R26 = 0x3AC18, 0x3AB6E     # the multiply each edit must stay AFTER
RAIL_SITES = {0x3AC42: "060600e0", 0x3AC46: "20c60020"}   # the +-8192 lane rails
PTR_ARRAYS = (0xCA4F4, 0xCA23C)      # AMP1 / AMP4 boost tables, mode-indexed, stride 4
FLAT_TO = {0xCA4F4: 15035, 0xCA23C: 13926}   # V59's index-weighted mean boost per curve
N_FLAT = 4                            # flatten Y[0..3]; the sweep is 0..2048 at p99.96
# V59's measured index distribution, engaged + creep + sustained hands-off, n=5016
IDX_DIST = ((256, 0.7693), (768, 0.1846), (1536, 0.0457), (2048, 0.0004))
MODE_ENGAGED, MODE_MANUAL = 26, 24
BLEND_AXIS = 0xC6010                                # cal(0xC6010) = [0, 640, 3200, 6400]
GAIN_MULT = 2                                       # pure scalar on Y; X axes untouched

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
    print("  V264 -- KILL THE PARAMETRIC PUMP.  THE INTERVENTION NAMED IN 2026-07.")
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

    print("\n  [2] RESOLVE THE MODE-26 BOOST CURVES, AND ANCHOR THE TABLES AGAINST THE RECORD")
    def _slot(b, idx):
        return struct.unpack_from("<I", base, b + idx * 4)[0]
    check(_slot(0xCA4F4, 10) == 0xD28DC,
          "AMP1 table base 0xCA4F4 slot 10 resolves to 0xD28DC -- the address the V58/V59/V60 record "
          "names, so the table base is anchored against the record and not guessed")
    check(_slot(0xCA23C, 10) == 0xD2888,
          "AMP4 table base 0xCA23C slot 10 resolves to 0xD2888 -- likewise anchored")
    eng = [_slot(b, MODE_ENGAGED) for b in PTR_ARRAYS]
    man = [_slot(b, MODE_MANUAL) for b in PTR_ARRAYS]
    for _p in eng + man:
        check(START <= _p < END, f"0x{_p:06X} lies inside the flashable window")
    check(not (set(eng) & set(man)),
          f"ENGAGED {[hex(x) for x in eng]} DISJOINT from MANUAL {[hex(x) for x in man]}")

    print("\n  [2b] ALIASING -- all 64 indices of both tables")
    for _p in eng:
        _refs = [i for _b in PTR_ARRAYS for i in range(64) if _slot(_b, i) == _p]
        check(set(_refs) == {MODE_ENGAGED},
              f"0x{_p:06X} referenced by mode index {sorted(set(_refs))} -- mode 26 ONLY")

    def _rec(buf, p):
        n = struct.unpack_from("<h", buf, p)[0]
        X = [struct.unpack_from("<h", buf, p + 2 + 2 * k)[0] for k in range(n)]
        Y = [struct.unpack_from("<h", buf, p + 2 + 2 * n + 2 * k)[0] for k in range(n)]
        return n, X, Y

    def _lerp(v, X, Y):
        if v <= X[0]:
            return float(Y[0])
        for k in range(len(X) - 1):
            if v < X[k + 1]:
                return Y[k] + (Y[k + 1] - Y[k]) * (v - X[k]) / (X[k + 1] - X[k])
        return float(Y[-1])

    print("\n  [2c] THE EDIT -- flatten the SWEPT RANGE at V59's index-weighted mean boost")
    for _b, _p in zip(PTR_ARRAYS, eng):
        _n, _X, _Y = _rec(base, _p)
        check(_n == 6, f"0x{_p:06X} npt={_n} -- the expected 6-point boost record")
        _flat = FLAT_TO[_b]
        _mean = sum(w * _lerp(v, _X, _Y) for v, w in IDX_DIST)
        check(abs(_mean - _flat) < 2,
              f"0x{_p:06X} flatten value {_flat} equals the index-weighted mean {_mean:.0f} -- the "
              f"MEAN BOOST IS PRESERVED, so this is a modulation change, not an authority change")
        _g = _lerp(2048, _X, _Y) / _lerp(0, _X, _Y)
        _eps_old = (1 - _g) / (1 + _g)
        for k in range(N_FLAT):
            struct.pack_into("<h", code, _p + 2 + 2 * _n + 2 * k, _flat)
            attributed |= {_p + 2 + 2 * _n + 2 * k, _p + 3 + 2 * _n + 2 * k}
        _n2, _X2, _Y2 = _rec(code, _p)
        check(_X2 == _X, f"0x{_p:06X} X axis UNTOUCHED {_X2} -- no breakpoint moves")
        check(_Y2[:N_FLAT] == [_flat] * N_FLAT and _Y2[N_FLAT:] == _Y[N_FLAT:],
              f"0x{_p:06X} Y {_Y} -> {_Y2}")
        _g2 = _lerp(2048, _X2, _Y2) / _lerp(0, _X2, _Y2)
        _eps_new = (1 - _g2) / (1 + _g2)
        check(_eps_new < _eps_old,
              f"0x{_p:06X} pump depth eps over [0,2048] FALLS {_eps_old:.3f} -> {_eps_new:.3f}")
        _s_old = (_Y[N_FLAT] - _Y[N_FLAT - 1]) / (_X[N_FLAT] - _X[N_FLAT - 1])
        _s_new = (_Y2[N_FLAT] - _Y2[N_FLAT - 1]) / (_X2[N_FLAT] - _X2[N_FLAT - 1])
        check(_X[N_FLAT - 1] >= 1741,
              f"the steepened segment starts at index {_X[N_FLAT - 1]}, at or above 1741 -- V59 "
              f"measured 0.04 % of frames at or above 2048, so it is pushed where nothing lives")
        print(f"      0x{_p:06X}  Y {_Y} -> {_Y2}")
        print(f"                 eps {_eps_old:.3f} -> {_eps_new:.3f} ; tail slope "
              f"{_s_old:+.3f} -> {_s_new:+.3f} per count, from index {_X[N_FLAT - 1]}")
        check(all(_Y2[k] >= _Y2[k + 1] for k in range(len(_Y2) - 1)),
              f"0x{_p:06X} Y stays MONOTONE NON-INCREASING -- no plateau-then-rise, so no new "
              f"nonlinearity of the V80 relay kind")

    print("\n  [2d] EVERYTHING ELSE ASSERTED STOCK -- this is the pump ALONE")
    check(code[SAR_R26] == SAR_1X and code[SAR_R24] == SAR_1X, "the sar immediates are stock")
    check(u16(code, 0xC6440) == 2048 and u16(code, 0xC6442) == 1024 and u16(code, 0xC643E) == 1536,
          "the three LIVE rate-lane arms are stock")
    check(u16(code, 0xC6CD0) == 5346 and u16(code, 0xC61B2) == 3072,
          "forward gain and clamp are stock -- authority is untouched")
    for _p in (0xD7A88, 0xD7AC4, 0xD7B00, 0xD7B3C):
        check(bytes(code[_p:_p + 18]) == bytes(base[_p:_p + 18]),
              f"V263's rate-lane gain surface 0x{_p:06X} is UNTOUCHED -- the two builds are disjoint")

    print("\n  [3] MANUAL STEERING MUST BE BYTE-IDENTICAL")
    for _p in man:
        check(bytes(code[_p:_p + 26]) == bytes(base[_p:_p + 26]),
              f"MANUAL (mode 24) boost record 0x{_p:06X} is BYTE-IDENTICAL -- this resolves the "
              f"record's 'GATE 2 is NOT clean, both change manual feel' caveat, which was written "
              f"for a mode-10 edit that is not mode-partitioned")
    for _p in (0xD6760, 0xD67E4, 0xD6820):
        check(bytes(code[_p:_p + 20]) == bytes(base[_p:_p + 20]),
              f"MANUAL damper record 0x{_p:06X} byte-identical")

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
        _allow |= {_p + 14 + k for k in range(2 * N_FLAT)}
    check(set(pay) <= _allow,
          "every payload byte is a flattened Y knot of a mode-26 BOOST record -- no X axis, "
          "no other mode, no code byte, no rate-lane cell")
    check(len(pay) <= 16, f"{len(pay)} payload bytes across the two engaged boost records")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V264 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v264_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V264_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V264 -- KILL THE PARAMETRIC PUMP. THE INTERVENTION NAMED IN 2026-07, NEVER RUN.                    **")
    print("  **   0xD78F8 AMP1  Y [16384,14658,11676,9362,..] -> [15035,15035,15035,15035,..]                      **")
    print("  **   0xD78A4 AMP4  Y [16384,14393,10269,8997,..] -> [13926,13926,13926,13926,..]                      **")
    print("  **   (mode 26 = ENGAGED only; mode 24 MANUAL asserted byte-identical)                                 **")
    print("  ** V59 FLEW AND MEASURED THIS PUMP: the index spectrum peaks at 42.19 Hz = 2x the                     **")
    print("  ** 21.09 Hz mode, prominence 11.10x, coherence 0.795 vs the torsion bar, over 13                      **")
    print("  ** disjoint runs. Disengaged the pump is ABSENT (0/4 runs, prominence 0.00x).                         **")
    print("  ** => a parametric gain pump at 2f into a mode at f -- textbook parametric                            **")
    print("  **    resonance, and the mode at f IS the grinding mode.                                              **")
    print("  ** THE KIT THEN WROTE: 'Only an INTERVENTION (flatten the swept range, re-fly)                        **")
    print("  ** separates drive from echo.' It was never built -- V58/V59/V60 studied mode                         **")
    print("  ** slot 10, and this car runs 24/26, so those edits could not have reached it.                        **")
    print("  ** SIZED FROM V59'S OWN MEASURED DISTRIBUTION (76.93% <512, 18.46% 512-1k,                            **")
    print("  ** 4.57% 1k-2k, 0.04% >=2k): flatten to the index-weighted MEAN boost, so the                         **")
    print("  ** mean is preserved by construction. This changes MODULATION, not LEVEL.                             **")
    print("  **   eps over [0,2048]:  AMP1 0.222 -> 0.000    AMP4 0.301 -> 0.050                                   **")
    print("  ** THE COST, as the GATE 2 rule demands: one segment steepens (-1.00 -> -6.08 and                     **")
    print("  ** -0.62 -> -4.32 per count) -- but it starts at index 2529/1741 and V59 measured                     **")
    print("  ** 0.04% of frames at or above 2048. Pushed where nothing lives.                                      **")
    print("  ** NULL IS LOAD-BEARING: unchanged => the pump was an ECHO and the parametric                         **")
    print("  ** route is CLOSED by experiment. Dropped => it was DRIVING the mode.                                 **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
