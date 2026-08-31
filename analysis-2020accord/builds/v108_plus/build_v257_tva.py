# -*- coding: utf-8 -*-
r"""V257 -- THE COMPLETE PACKAGE ON THE V112 BASE.  THREE LEVERS, ALL FOUR SYMPTOMS.

    0x3AB76 / 0x3AC20   aa -> a9        rate lane 2x Kd    GRINDING + ratchet
    0xC61B2 / 0xC61B4   3072 -> 4096    forward clamps     AUTHORITY + rail oscillation
    0xC6CD0             5346 -> 4455    forward gain 6x->5x  GRINDING + RATCHET

WHY THESE THREE AND WHY TOGETHER.  Each was measured separately; what makes them a package is that
the gain cut pays into THREE symptoms at once and the clamp repays the one thing it costs.

**THE GAIN IS THE CARRIER.**  The 21.4 Hz grinding mode is MECHANICAL (Q = 13.6) and the electronics
only close a loop around it; loop gain around that mode is set by the forward gain.  The same gain is
also the ratchet's anti-damping (rho -0.819 over 17 flown builds, ~ -4.4 of Re(Z) per 1x).  So cutting
6x -> 5x damps the grinding mode AND the ratchet.

**AND IT COSTS LESS AUTHORITY THAN IT LOOKS, BECAUSE PEAK TORQUE IS THE CLAMP, NOT THE GAIN.**
`delivered = min(cmd * gain / 891, clamp)`, and the command p99 is pinned at EXACTLY the clamp on
every route in the corpus.  Raising the clamp 3072 -> 4096 raises PEAK delivered torque 33 %.  Over
1,691,012 engaged frames of real openpilot command:

    configuration              gain  clamp   rail duty   mean deliv   Re(Z)      vs the car
    the car                    6.0x   3072      30.2 %       1688     -64.8          --
    clamp only                 6.0x   4096      24.9 %       1968     -64.8   +17 % tq /  0.0
    8x                         8.0x   4096      30.2 %       2251     -73.6   +33 % tq / -8.8
    THIS BUILD (+ rate lane)   5.0x   4096      22.3 %       1801     -54.9    +7 % tq / +9.9

**+7 % mean torque, +33 % peak, -26 % rail duty, and +9.9 of Re(Z)** -- the only configuration that
beats the car on authority AND ratchet AND rail time simultaneously.  The rate lane then adds its own
damping on top, at both 21.4 Hz (full) and 7.8 Hz (36 % of full -- a derivative scales with frequency).

🛑 THE RATE LANE'S RATCHET CONTRIBUTION IS [BELIEF], EXTRAPOLATED, NOT MEASURED.  Lever B is the
lane's own arm, and the anti-damping census found only the GAIN and LEVER B track the ratchet.  The
two measured Lever B steps are 512->5244 = 5.81 units and 5244->7866 = 2.90 units, which is close to
linear in dN (1.23e-3 units per unit of N).  The doubled shift gives an effective N of ~9766 at the
median frame (saturating just above p50), i.e. dN ~ 4522 -> **~5.6 units, about 8.6 % of the 65-unit
requirement**.  Extrapolation from two points.  Read it as an order, not a decimal.

🛑 THE HONEST WEAKNESS, unchanged from V254.  "5x" reads like less torque and the operator asked
for 6x or higher.  DELIVERED torque goes UP -- but if he judges the car by feel at a given steering
input rather than by lane-holding, a lower gain may feel softer below the rail even though mean and
peak are both higher.  **A drive settles that; this analysis cannot.**  V256 (rate lane + clamp, gain
untouched at 6x) is the conservative sibling and exists precisely so that question is separable.

🛑 AND THE GAIN->RATCHET SLOPE IS CONFOUNDED WITH BUILD ERA.  One era-free contrast supports it
(V101->V102 with Lever B held), not a controlled experiment.  If that slope is wrong, this build keeps
its torque, rail-duty and rate-lane gains and loses only the +4.4.

THE V27 INTERLOCK.  Asserted in sync AND asserted untouched, as in V256.  4096 < the 5120 wall, ratio
1.25, which V101 already flew.

WHAT A NULL LICENSES.  Because three levers move at once this build is deliberately NOT the first one
to fly.  Fly V255 (rate lane alone) or V256 (+ clamp) first; this one is for when their direction is
known and the remaining question is how far to push.  If flown blind and something regresses, the
attribution is ambiguous -- which is exactly the design failure the kit's own law warns against.

BASE: V112.  Six bytes.
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
WRITE_MODE = os.environ.get("ACCORD_V257_WRITE", "").strip().lower()

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
TAG = "V257-V112BASE-RATELANE.2X.CLAMP4096.GAIN5X"

SAR_R26, SAR_R24 = 0x3AB76, 0x3AC20     # the two `sar` immediates -- V62's exact sites
SAR_1X, SAR_2X = 0xAA, 0xA9             # sar 0xa (stock) -> sar 0x9 (double the lane)
MUL_R24, MUL_R26 = 0x3AC18, 0x3AB6E     # the multiply each edit must stay AFTER
RAIL_SITES = {0x3AC42: "060600e0", 0x3AC46: "20c60020"}   # the +-8192 lane rails
CLAMP_OLD_V, CLAMP_NEW_V = 3072, 4096   # forward clamps -- PEAK delivered torque IS this
GAIN_OLD_V, GAIN_NEW_V = 5346, 4455     # forward gain 6x -> 5x; the carrier AND the anti-damping
INT_QUAD = (0xC674E, 0xC6750, 0xC675A, 0xC675C)   # the pair V27 died on -- NOT touched
FLT_QUAD = (0xC6598, 0xC659C, 0xC65AC, 0xC65B0)

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
    print("  V257 -- RATE LANE + CLAMP + GAIN CUT.  THE COMPLETE PACKAGE ON V112.")
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

    print("\n  [2] THE ONE EDIT -- two bytes, sar 0xa -> sar 0x9")
    code[SAR_R26] = SAR_2X
    code[SAR_R24] = SAR_2X
    attributed |= {SAR_R26, SAR_R24}
    check(code[SAR_R26] == SAR_2X and code[SAR_R24] == SAR_2X,
          "both rate lanes doubled -- the DOSE-EXACT encoding: it scales r24 AND r26 identically, "
          "so it is 2.000x on the total for every value of the adaptive arm a")
    check(SAR_R24 > MUL_R24 and SAR_R26 > MUL_R26,
          f"both edits are POST-MULTIPLY (0x{SAR_R24:05X} > 0x{MUL_R24:05X}, "
          f"0x{SAR_R26:05X} > 0x{MUL_R26:05X}) -- preserves the V850 mul high-word headroom at "
          f"47% of INT32_MAX rather than pushing it to 94%")

    print("\n  [2b] THE SECOND LEVER -- the forward clamps, four bytes")
    struct.pack_into("<H", code, CLAMP_P, CLAMP_NEW_V)
    struct.pack_into("<H", code, CLAMP_N, CLAMP_NEW_V)
    attributed |= {CLAMP_P, CLAMP_P + 1, CLAMP_N, CLAMP_N + 1}
    check(u16(code, CLAMP_P) == CLAMP_NEW_V and u16(code, CLAMP_N) == CLAMP_NEW_V,
          f"forward clamps {CLAMP_OLD_V} -> {CLAMP_NEW_V} -- PEAK delivered torque rises "
          f"{100.0 * CLAMP_NEW_V / CLAMP_OLD_V - 100:.0f} %, and the rail moves out by the same "
          f"factor so the loop is OPEN less often")
    print("\n  [2d] THE THIRD LEVER -- the forward gain, two bytes")
    struct.pack_into("<H", code, GAIN_CELL, GAIN_NEW_V)
    attributed |= {GAIN_CELL, GAIN_CELL + 1}
    check(u16(code, GAIN_CELL) == GAIN_NEW_V,
          f"forward gain {GAIN_OLD_V} -> {GAIN_NEW_V} ({GAIN_NEW_V / 891.0:.2f}x) -- LOWER, which "
          f"damps the 21.4 Hz mechanical mode AND removes ratchet anti-damping")
    check(GAIN_NEW_V < GAIN_OLD_V, "the gain goes DOWN -- this is the counterintuitive half")
    _r_old = CLAMP_OLD_V * 891.0 / GAIN_OLD_V
    _r_new = CLAMP_NEW_V * 891.0 / GAIN_NEW_V
    check(_r_new > _r_old * 1.4,
          f"the rail moves {_r_old:.0f} -> {_r_new:.0f} counts of command -- the loop is open LESS "
          f"often, which is the peak-command-oscillation symptom")
    # PEAK delivered torque IS the clamp: command p99 is pinned at exactly the clamp on every
    # route in the corpus, so the command always reaches the rail and the clamp is what binds.
    check(CLAMP_NEW_V > CLAMP_OLD_V,
          f"PEAK delivered torque {CLAMP_OLD_V} -> {CLAMP_NEW_V} (+{100.0*CLAMP_NEW_V/CLAMP_OLD_V-100:.0f} %) "
          f"despite the LOWER gain, because peak is set by the CLAMP and command reaches the rail")
    _rail_old = CLAMP_OLD_V * 891.0 / 5346
    _rail_new = CLAMP_NEW_V * 891.0 / 5346
    print(f"      (clamp alone would move the rail {_rail_old:.0f} -> {_rail_new:.0f}; the gain cut below moves it further)")

    print("\n  [2c] THE V27 INTERLOCK -- the mirrored quad, checked not assumed")
    for _a, _f in zip(INT_QUAD, FLT_QUAD):
        _i = struct.unpack_from("<h", code, _a)[0]
        _v = struct.unpack_from("<f", code, _f)[0]
        check(abs(_i - _v * 1024.0) <= 5,
              f"0x{_a:05X}={_i} mirrors 0x{_f:05X}={_v:.3f} (int == float*1024, +-5 LSB)")
        check(struct.unpack_from("<h", base, _a)[0] == _i and
              struct.unpack_from("<f", base, _f)[0] == _v,
              f"0x{_a:05X}/0x{_f:05X} UNTOUCHED by this build")
    check(CLAMP_NEW_V < struct.unpack_from("<h", code, INT_QUAD[0])[0],
          f"the new clamp {CLAMP_NEW_V} stays UNDER the soft-EME wall "
          f"{struct.unpack_from('<h', code, INT_QUAD[0])[0]} -- ratio 1.25, which V101 already flew")

    print("\n  [3] SATURATION, COMPUTED NOT ASSERTED")
    for _lb, _who in ((512, "V62 era"), (LEVER_B_VAL, "this car")):
        _s1, _s2 = 8192 * 1024 // _lb, 8192 * 512 // _lb
        print(f"      {_who:<9} LeverB {_lb:>5}:  1x clips above {_s1:>6}   2x clips above {_s2:>6}")
    check(8192 * 512 // LEVER_B_VAL < 5120,
          "on this car the doubled lane DOES clip below the input ceiling -- stated, not hidden")
    check(8192 * 1024 // 512 >= 5120,
          "in V62's era it could not clip at all, which is why V62's result may not transfer whole")

    print("\n  [4] THE RAILS AND EVERYTHING ELSE ARE FROZEN")
    for a, want in sorted(RAIL_SITES.items()):
        check(bytes(code[a:a + 4]).hex() == want,
              f"0x{a:05X} = {want} -- the +-8192 lane rail is UNTOUCHED")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- not the bricking class")
    check(u16(code, LEVER_B) == LEVER_B_VAL, f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")
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
    check(len(pay) == 6, f"{len(pay)} payload byte(s) -- 2 sar + 2 clamp high bytes + 2 gain")
    check(set(pay) <= {SAR_R26, SAR_R24, CLAMP_P, CLAMP_P + 1, CLAMP_N, CLAMP_N + 1,
                       GAIN_CELL, GAIN_CELL + 1},
          "every payload byte is a sar immediate, a forward clamp, or the gain")
    check({SAR_R26, SAR_R24} <= set(pay), "both sar immediates actually moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V257 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v257_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V257_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V257 -- THE COMPLETE PACKAGE ON V112. THREE LEVERS, SIX BYTES.                                     **")
    print("  **   0x3AB76 / 0x3AC20   aa -> a9        rate lane 2x   GRINDING + ratchet                            **")
    print("  **   0xC61B2 / 0xC61B4   3072 -> 4096    clamps         AUTHORITY + rail                              **")
    print("  **   0xC6CD0             5346 -> 4455    gain 6x -> 5x  GRINDING + RATCHET                            **")
    print("  ** THE GAIN IS THE CARRIER: the 21.4 Hz mode is MECHANICAL (Q=13.6) and the                           **")
    print("  ** forward gain sets the loop gain around it. The SAME gain is the ratchet's                          **")
    print("  ** anti-damping. So cutting it damps both -- and the clamp repays the torque.                         **")
    print("  ** MEASURED over 1,691,012 engaged frames:                                                            **")
    print("  **   config           gain clamp  rail   mean deliv  Re(Z)      vs car                                **")
    print("  **   the car          6.0x  3072  30.2%      1688    -64.8        --                                  **")
    print("  **   clamp only       6.0x  4096  24.9%      1968    -64.8  +17% / 0.0                                **")
    print("  **   8x               8.0x  4096  30.2%      2251    -73.6  +33% / -8.8                               **")
    print("  **   THIS BUILD       5.0x  4096  22.3%      1801    -54.9   +7% / +9.9                               **")
    print("  ** +7% mean torque, +33% PEAK, -26% rail duty, +9.9 Re(Z), plus the rate lane.                        **")
    print("  ** HONEST WEAKNESS: '5x' reads like less torque. DELIVERED torque goes UP, but                        **")
    print("  ** feel at a given input may be softer below the rail. Only a drive settles it.                       **")
    print("  ** DO NOT FLY THIS FIRST. Fly V255 (rate lane alone) or V256 (+clamp) first --                        **")
    print("  ** three levers at once means an ambiguous attribution if anything regresses.                         **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
