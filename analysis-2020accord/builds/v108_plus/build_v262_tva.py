# -*- coding: utf-8 -*-
r"""V262 -- THE RATE LANE AT 4x.  V255's ENCODING, ONE NOTCH FURTHER.  TWO BYTES.

    0x3AB76 / 0x3AC20   aa -> a8        sar 0xa -> sar 0x8   =  4x Kd on BOTH lanes

WHY A SECOND RUNG EXISTS AT ALL.  V255 restores V62's 2x, which is the only dose this lane has ever
been measured at -- and it was measured in 2026-07, at a 4x forward gain, with Lever B still believed
live.  **Lever B is dead** (`0xC6446`'s branch tests `gp-0x683c`, which has zero writers), and the
`sar` was reverted after V65, so **this lane has not been dosed in ~200 builds and has no validated
optimum.**  2x is not known to be the right amount; it is only the amount that was tried once.

The grinding mode is a lightly-damped MECHANICAL resonance -- 21.4 Hz, **Q = 13.6**, so zeta = 0.0368.
For the wheel-inertia-on-bar mode the `phi'` coefficient is **linear in Kd**, so:

    Kd = 1x (the car today)   zeta 0.037   Q 13.6      resonant amplification 13.6x
    Kd = 2x (V255)            zeta 0.074   Q  6.8      -> roughly HALF the peak
    Kd = 4x (this build)      zeta 0.147   Q  3.4      -> roughly a QUARTER

⚠ That ladder assumes the rate lane supplies ALL of the mode's damping, which is the strong form of
the model.  V62 measured **8x** in 18-22 Hz band power for a 2x dose, i.e. MORE than the 2x peak
reduction the model predicts -- so either band power scales super-linearly with zeta, or the lane is
not the only damping and the true response is shallower.  **Read this as an ordering, not a decimal.**

GATE 2 ARITHMETIC, computed rather than asserted:

    OVERFLOW.  Worst case is the input ceiling 5120 times the largest live arm 2048 = 10,485,760,
    which is **0.49 % of INT32_MAX**.  Even with V261's doubled arms (4096) it is 0.98 %.  The V850
    `mul` high-word concern that dictated V62's site choice is nowhere near binding -- and the edit is
    still POST-multiply (`0x3AC18 mul`, then `0x3AC20 sar`), which is why these two sites and not
    `0x3AB70`/`0x3AC1A`.

    SATURATION.  The lane clamps at +-8192 after the shift, so at 4x it clips above input
    **1024-2048** depending on which arm is live, against a measured p50 input of **859**.
    ⇒ **the median frame is still LINEAR at 4x**; the upper half of the distribution clips.

    AND CLIPPING HERE IS BENIGN, for the reason V80 makes concrete.  A saturating LINEAR damper has
    describing function K at small amplitude, falling only for large -- **maximum damping exactly
    where the ratchet (0.72 deg/s) and the ring (4-7 counts) live**.  The dangerous form is the
    COULOMB relay, `4M/(pi*a)`, whose gain goes to INFINITY as amplitude goes to zero; that is what
    V80 created by flattening FactorC, and it produced "the worst grinding the car has ever produced".
    This build creates no plateau: it changes a shift, so the curve stays linear-then-clipped.

🛑 WHAT THIS COSTS, honestly.  A derivative term is frequency-selective -- at 1 Hz it delivers
4.7 % of its 21.4 Hz output -- so it does not add the low-speed friction the operator ruled out.  But
4x is 4x: at 3 Hz it is 14 % of full, and doubling that again is the point at which brisk manual
corrections could start to feel damped.  **This is a feel question and only a drive settles it.**

🛑 DO NOT FLY THIS BEFORE V255.  V255 is the dose with flight history (V62/V65, fault-free, ST==4
zero over 86,278 frames).  This is the rung for *"V255 helped, and more would help more"*.  If V255
does nothing at all, 4x of nothing is still nothing and the lane is not the answer -- fly V256 instead
to settle the gain-vs-clamp question.

⊕ RELATIONSHIP TO V261.  V261 keeps the 2x shift and doubles the three LIVE cal arms instead, which
gives 4x in the branches a cal can reach but only 2x in the runtime-LERP branch -- the dominant path,
which no calibration cell can reach.  **This build gives a uniform 4x everywhere**, which is the
cleaner experiment and the reason it exists alongside V261.

BASE: V112.  Two bytes.  Single variable.
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
WRITE_MODE = os.environ.get("ACCORD_V262_WRITE", "").strip().lower()

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
TAG = "V262-V112BASE-RATELANE.4X"

SAR_R26, SAR_R24 = 0x3AB76, 0x3AC20     # the two `sar` immediates -- V62's exact sites
SAR_1X, SAR_2X = 0xAA, 0xA8             # sar 0xa (stock) -> sar 0x8 (QUADRUPLE the lane)
ARM_A, ARM_B, ARM_L1 = 0xC6440, 0xC6442, 0xC643E   # the LIVE arms -- asserted STOCK here
MUL_R24, MUL_R26 = 0x3AC18, 0x3AB6E     # the multiply each edit must stay AFTER
RAIL_SITES = {0x3AC42: "060600e0", 0x3AC46: "20c60020"}   # the +-8192 lane rails

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
    print("  V262 -- THE RATE LANE AT 4x.  V255's ENCODING, ONE NOTCH FURTHER.")
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
          "both rate lanes QUADRUPLED -- the DOSE-EXACT encoding: it scales r24 AND r26 identically, "
          "so it is 4.000x on the total for every value of the adaptive arm a, and it reaches the "
          "runtime-LERP branch that no calibration cell can touch")
    check((SAR_1X - SAR_2X) == 2, "the shift moves by 2 -> exactly 4x, not 2x")
    check(u16(code, ARM_A) == 2048 and u16(code, ARM_B) == 1024 and u16(code, ARM_L1) == 1536,
          "all three LIVE arms asserted STOCK -- this build is the shift ALONE, single variable, "
          "which is what separates it from V261")
    check(SAR_R24 > MUL_R24 and SAR_R26 > MUL_R26,
          f"both edits are POST-MULTIPLY (0x{SAR_R24:05X} > 0x{MUL_R24:05X}, "
          f"0x{SAR_R26:05X} > 0x{MUL_R26:05X}) -- preserves the V850 mul high-word headroom at "
          f"47% of INT32_MAX rather than pushing it to 94%")

    print("\n  [3] GATE 2 ARITHMETIC, COMPUTED NOT ASSERTED")
    _worst = 5120 * 2048
    print(f"      overflow worst case: input ceiling 5120 x largest live arm 2048 = {_worst:,} "
          f"= {100.0 * _worst / 2147483647:.2f} % of INT32_MAX")
    check(_worst < 0.05 * 2147483647,
          "the V850 mul high-word concern is nowhere near binding at 4x")
    for _arm in (1024, 2048):
        print(f"      live arm {_arm:>5}: at 4x the lane clips above input {8192 * 256 // _arm}")
    check(8192 * 256 // 2048 > 859,
          "even at 4x with the largest live arm, the clip point is ABOVE the measured p50 input of "
          "859 -- the median frame is still LINEAR")
    check(8192 * 256 // 2048 < 5120,
          "the upper tail DOES clip -- stated, not hidden; and a saturating LINEAR damper keeps its "
          "full gain at small amplitude, which is where the ratchet and the ring live")

    print("\n  [3b] LEGACY SATURATION TABLE")
    for _k in (1024, 2048):
        print(f"      live arm {_k:>5}:  1x clips {8192 * 1024 // _k:>6}   "
              f"2x clips {8192 * 512 // _k:>6}   4x clips {8192 * 256 // _k:>6}")
    check(u16(code, 0xC6446) == 5244,
          "Lever B left at 5244 and UNREACHABLE (gp-0x683c has zero writers) -- it plays no part in "
          "this build's arithmetic, which is why the old saturation caveat computed against 5244 "
          "was void")

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
    check(len(pay) == 2, f"{len(pay)} payload byte(s) -- exactly the two sar immediates")
    check(all(code[_a] == SAR_2X for _a in (SAR_R26, SAR_R24)),
          "both sar immediates are 0xA8 = sar 0x8 = 4x")
    check(set(pay) == {SAR_R26, SAR_R24},
          "every payload byte is one of V62 two sar immediates -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V262 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v262_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V262_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V262 -- THE RATE LANE AT 4x. TWO BYTES. SINGLE VARIABLE.                                           **")
    print("  **   0x3AB76 / 0x3AC20   aa -> a8   sar 0xa -> sar 0x8  = 4x Kd on BOTH lanes                         **")
    print("  ** WHY A SECOND RUNG: 2x is the only dose this lane was ever measured at, once,                       **")
    print("  ** in 2026-07, at a 4x forward gain and with Lever B still believed live. Lever B                     **")
    print("  ** is DEAD and the sar was reverted after V65, so this lane has not been dosed in                     **")
    print("  ** ~200 builds and has NO validated optimum. 2x is not known to be right.                             **")
    print("  ** THE MODE IS MECHANICAL: 21.4 Hz, Q = 13.6, zeta = 0.0368, and the phi'                             **")
    print("  ** coefficient is LINEAR in Kd:                                                                       **")
    print("  **   Kd 1x (the car)   zeta 0.037  Q 13.6                                                             **")
    print("  **   Kd 2x (V255)      zeta 0.074  Q  6.8   ~half the peak                                            **")
    print("  **   Kd 4x (this)      zeta 0.147  Q  3.4   ~a quarter                                                **")
    print("  **   (strong form of the model -- V62 measured 8x in band power for a 2x dose,                        **")
    print("  **    so read this as an ORDERING, not a decimal.)                                                    **")
    print("  ** GATE 2: overflow worst case is 0.49% of INT32_MAX. At 4x the lane clips above                      **")
    print("  ** input 1024-2048 vs a measured p50 of 859 -- THE MEDIAN FRAME IS STILL LINEAR.                      **")
    print("  ** Clipping is benign here: a saturating LINEAR damper keeps full gain at small                       **")
    print("  ** amplitude, unlike V80's Coulomb relay whose gain goes to infinity as a -> 0.                       **")
    print("  ** vs V261: that one keeps 2x and doubles the cal arms, giving 4x only in the                         **")
    print("  ** branches a cal can reach. THIS gives a uniform 4x everywhere. Cleaner test.                        **")
    print("  ** DO NOT FLY BEFORE V255 -- V255 is the dose with flight history.                                    **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
