# -*- coding: utf-8 -*-
r"""V255 -- RESTORE V62's RATE-LANE DOUBLING.  TWO BYTES ON WHAT IS ACTUALLY ON THE CAR.

THE FINDING THAT JUSTIFIES THIS BUILD.  V62 (`sar 0xa` -> `sar 0x9` at 0x3AB76 and 0x3AC20) is the
ONLY measured grinding fix this kit has ever produced -- 18-22 Hz down 8x (42x at |rate| 16-32 deg/s)
against a flat 30-40 Hz negative control, and the operator's own words: "Original grinding at 2-5 mph
is gone!"

**IT IS NOT ON THE CAR, AND IT IS NOT ON ANY BUILD SINCE V65.**  Read from the IMAGES, not the record:

    build                    0x3AB76  0x3AC20   state
    stock                      aa32     aa42    1x Kd
    V62                        a932     a942    2x Kd   <- the fix
    V65                        a932     a942    2x Kd
    V70                        aa32     aa42    REVERTED
    V88 V100 V108 V111         aa32     aa42    1x Kd
    V112                       aa32     aa42    1x Kd   <- THE CAR
    V122 V241 V251 V254        aa32     aa42    1x Kd   <- the whole current shelf

`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` says "Restored in V71".  **The images say otherwise.**
Whatever V71 did, nothing from V88 onward carries it.  This is a RECORD DEFECT, not a new lever:
the kit has spent sixty builds hunting grinding while its one measured cure sat reverted.

WHY IT SHOULD WORK, mechanically.  The grinding mode is a lightly-damped MECHANICAL resonance --
21.4 Hz, Q = 13.6, ~0.23 s coherence -- not a digital limit cycle.  For the wheel-inertia-on-bar mode

    phi'' + (Kd*k/J_c)*phi' + k*(1/J_w + (1+K)/J_c)*phi = T_road/J_c

the phi' coefficient is POSITIVE and LINEAR IN Kd, and **at Kd = 0 the mode has no damping term at
all.**  The rate lane IS that Kd.  Doubling it doubles the only damping the mode has.

THE ONE THING THAT IS DIFFERENT FROM V62's ERA, stated plainly.  V62 flew with Lever B (0xC6446, the
lane's own arm, loaded at 0x3AC08 into the multiply at 0x3AC18) at its STOCK 512.  **The car runs
5244, 10.2x higher** (introduced at V88).  The lane clamps at +-8192 AFTER the multiply, so:

    saturating input = 8192 * 2^shift / LeverB
        V62 era, LeverB 512:   1x Kd -> 16384   2x Kd -> 8192   (input ceiling 5120: NEVER clips)
        this car, LeverB 5244: 1x Kd ->  1599   2x Kd ->   799

So on this car the doubled lane WILL clip on large transients, where V62's never did.

🛑 AND THAT IS BENIGN HERE -- the distinction matters and the kit has its own counter-example.
A COULOMB RELAY (V80's damper: T = -M*sign(rate)) has describing function 4M/(pi*a), so its gain goes
to INFINITY as amplitude goes to zero -- destabilising for small oscillations, which is exactly why
V80 produced "the worst grinding the car has ever produced".  A SATURATING LINEAR DAMPER
(T = -clamp(K*rate)) is the opposite: its describing function is K for small amplitude and FALLS only
for large.  **Maximum damping precisely at the amplitudes in question** -- the ratchet is 0.72 deg/s
and the ring is 4-7 counts.  The clip costs authority only on large transients, and the symptoms
being treated are small-signal.  V62 pre-committed to exactly this ("expect a PARTIAL improvement,
not elimination") and on-car it did not bind.

GATES.
  GATE 1 (RAM ownership)  VACUOUS -- no cave, no new RAM, two immediate bytes edited in place.
  GATE 2 (closed-loop)    The edit is POST-MULTIPLY, verified in Ghidra this session:
                              0x3AC18  mul   r10, r8, r0      ; r8 = rate * LeverB
                              0x3AC20  sar   0xa, r8          ; <- THE EDIT
                          so the V850 `mul` high-word headroom argument is preserved (47% of
                          INT32_MAX, not 94%).  Editing 0x3AB70/0x3AC1A instead would put it
                          PRE-multiply, which is exactly why V62 chose these two sites.
                          The +-8192 lane rails (0x3AC42 `addi -0x2000` / `movea 0x2000`) and the
                          +-10240 aggregate are UNTOUCHED, so the lane cannot produce an unbounded
                          command.  Kd is a DAMPING term: it adds phase lead; it moves no pole into
                          the right half plane.
  FLIGHT HISTORY          These exact two bytes flew as V62 and V65, fault-free, ST==4 zero over
                          86,278 frames.  This is not a novel edit class.

WHAT A NULL LICENSES (pre-registered, per the design law).
  * 18-22 Hz band drops and the operator reports less grinding  => V62 replicates; the fix was
    simply missing, and it belongs in every subsequent build.
  * band drops, operator reports nothing                        => band moved, symptom did not.
    Report it that way and do NOT call grinding fixed.
  * nothing moves                                               => V62's result did NOT transfer
    across the Lever B change, and the saturation arithmetic above is the first suspect.
  * grinding WORSE                                              => the clip is not benign at
    LeverB 5244; revert, and the follow-up is Lever B DOWN with the doubling kept.

BASE: **V112 -- what the operator says is on the car**, not V122.  Two bytes.  Single variable.
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
WRITE_MODE = os.environ.get("ACCORD_V255_WRITE", "").strip().lower()

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
TAG = "V255-V112BASE-RATELANE.2X.V62.RESTORED"

SAR_R26, SAR_R24 = 0x3AB76, 0x3AC20     # the two `sar` immediates -- V62's exact sites
SAR_1X, SAR_2X = 0xAA, 0xA9             # sar 0xa (stock) -> sar 0x9 (double the lane)
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
    print("  V255 -- V62's RATE-LANE DOUBLING, RESTORED ONTO V112.  TWO BYTES.")
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
    FF.assert_x31_checksum(rwd, "V255 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v255_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V255_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V255 -- V62's RATE-LANE DOUBLING, RESTORED. TWO BYTES ON V112.                                     **")
    print("  **   0x3AB76  aa -> a9    sar 0xa -> sar 0x9   (r26 lane)                                             **")
    print("  **   0x3AC20  aa -> a9    sar 0xa -> sar 0x9   (r24 lane)                                             **")
    print("  ** THE FINDING: V62 is the kit's ONLY measured grinding fix -- 18-22 Hz down 8x,                      **")
    print("  ** operator said 'Original grinding at 2-5 mph is gone!'. Read from the IMAGES,                       **")
    print("  ** it is absent from V70 onward, including the car and the whole current shelf.                       **")
    print("  ** The lineage file says 'Restored in V71'. The images say otherwise.                                 **")
    print("  ** MECHANISM: the grinding mode is MECHANICAL (21.4 Hz, Q=13.6), and its damping                      **")
    print("  ** coefficient is LINEAR in Kd -- at Kd=0 the mode has no damping term at all.                        **")
    print("  ** The rate lane IS that Kd.                                                                          **")
    print("  ** THE HONEST CAVEAT: V62 flew with Lever B at stock 512; this car runs 5244, so                      **")
    print("  ** the doubled lane clips above input 799 where V62's never clipped at all.                           **")
    print("  ** That is BENIGN for these symptoms: a saturating LINEAR damper has maximum gain                     **")
    print("  ** at small amplitude (unlike V80's Coulomb relay, whose gain goes to infinity as                     **")
    print("  ** amplitude goes to zero -- which is why V80 was the worst grinding ever).                           **")
    print("  ** The ratchet is 0.72 deg/s and the ring is 4-7 counts: both small-signal.                           **")
    print("  ** FLIGHT HISTORY: these exact two bytes flew as V62 and V65, fault-free,                             **")
    print("  ** ST==4 zero over 86,278 frames. Not a novel edit class. GATE 1 vacuous.                             **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
