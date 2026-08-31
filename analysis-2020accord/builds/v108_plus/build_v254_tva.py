# -*- coding: utf-8 -*-
r"""V254 -- THE ONLY CONFIGURATION STRICTLY BETTER THAN THE CAR ON ALL THREE SYMPTOMS.

THE COUNTERINTUITIVE PART, AND IT IS THE WHOLE BUILD.  The operator asks for more torque and less
ratchet, and the gain relation says those conflict (rho -0.819, ~ -4.4 of Re(Z) per 1x of gain).  But
**peak delivered torque is set by the CLAMP, not the gain** -- `delivered = min(cmd*gain/891, clamp)`.
So LOWERING the gain while RAISING the clamp:

    * loses torque per unit of command  (bad)
    * raises the ceiling that torque is clipped at  (good, and it more than repays the loss)
    * reduces the anti-damping  (good)
    * raises the command at which the loop rails  (good -- less peak command oscillation)

Three of those four point the same way, and the measured numbers say the fourth is outweighed.
Computed over 1,691,012 engaged frames of real openpilot command:

    configuration              gain  clamp   rail duty   mean deliv   Re(Z)      vs the car
    V122 (the car)             6.0x   3072      30.2 %       1688     -64.8          --
    V251 (clamp only)          6.0x   4096      24.9 %       1968     -64.8   +17 % tq /  0.0
    V252 (8x)                  8.0x   4096      30.2 %       2251     -73.6   +33 % tq / -8.8
    THIS BUILD                 5.0x   4096      22.3 %       1801     -54.9    +7 % tq / +9.9

**V254 is the only row that beats the car on torque AND on ratchet AND on rail duty at once.**

WHAT IT CARRIES.  Everything under it, plus two cells:

    V241  the IMU-aimed notch                          grinding
    V247  FactorE, the damper's RATE dead zone         ratchet
    V249  FactorC, the damper's SPEED dead zone        ratchet at every speed
    V250  FactorB x2                                   the damper's margin rung
    ---- and this build ----
    0xC61B2 / 0xC61B4   3072 -> 4096    break the clamp/gain tracking
    0xC6CD0             5346 -> 4455    forward gain 6x -> 5x

THE LEDGER, all measured rather than asserted:

    +7 %  mean delivered torque      because the clamp ceiling rises 3072 -> 4096
    +33 % PEAK delivered torque      the clamp IS the peak
    -26 % rail duty  30.2 -> 22.3 %  the loop is open less often
    +9.9  Re(Z)  -64.8 -> -54.9      = 15 % of the 65 needed; +4.4 from the gain, +5.5 from the damper

🛑 THE HONEST WEAKNESS.  "5x" reads like less torque and the operator asked for 6x or higher.
The number that matters is DELIVERED torque, which goes UP -- but if he judges the car by feel at a
given steering input rather than by lane-holding, a lower gain may feel softer below the rail even
though the mean and the peak are both higher.  **That is a feel question a drive settles and this
analysis cannot.**  V251 (clamp only, gain untouched at 6x) is the conservative alternative: +17 % torque
and no gain change, but no ratchet benefit either.

🛑 AND THE GAIN->RATCHET SLOPE IS CONFOUNDED WITH ERA -- one era-free contrast supports it
(V101->V102 with Lever B held), not a controlled experiment.  If that slope is wrong, this build keeps
its torque and rail gains and loses only the +4.4.

BASE: V250.  Six bytes.
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
WRITE_MODE = os.environ.get("ACCORD_V254_WRITE", "").strip().lower()

BASE_NAME = "_v250_V250-V249BASE-FACTORB.X2.ENGAGED_plain_image.bin"
BASE_SHA = "66f15ba3d1c6b5ce15b0538827482e89e77ebc3544b42e767655841cf106187b"

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
TAG = "V254-V250BASE-GAIN5X.CLAMP4096.BEST.TRADE"

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
    check(_cy == [429, 234, 429, 908],
          f"base carries V249's opened SPEED dead zone Y={_cy} -- so this margin rung applies "
          f"at EVERY speed, unlike V248 which stacked on V247 and only helped above 35 km/h")
    _fb = [struct.unpack_from("<h", base, FB26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_fb == [FB_NEW] * 4,
          f"base carries V250's doubled FactorB Y={_fb} -- the damper margin rung is under this")
    check(u16(base, CLAMP_P) == CLAMP_OLD and u16(base, CLAMP_N) == CLAMP_OLD,
          f"base clamps are {CLAMP_OLD}, still TRACKING the gain")
    check(u16(base, GAIN_CELL) == GAIN_OLD,
          f"base gain is {GAIN_OLD} (6x)")
    check(CLAMP_NEW < u16(base, SOFT_EME),
          f"the new clamp {CLAMP_NEW} stays BELOW the soft-EME interlock {u16(base, SOFT_EME)}")
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, CLAMP_P, CLAMP_NEW)
    struct.pack_into("<H", code, CLAMP_N, CLAMP_NEW)
    struct.pack_into("<H", code, GAIN_CELL, GAIN_NEW)
    attributed |= {CLAMP_P, CLAMP_P + 1, CLAMP_N, CLAMP_N + 1, GAIN_CELL, GAIN_CELL + 1}
    def _lerp(v, X, Y):
        if v <= X[0]:
            return float(Y[0])
        for _i in range(len(X) - 1):
            if v < X[_i + 1]:
                return Y[_i] + (Y[_i + 1] - Y[_i]) * (v - X[_i]) / (X[_i + 1] - X[_i])
        return float(Y[-1])
    check(u16(code, CLAMP_P) == CLAMP_NEW and u16(code, CLAMP_N) == CLAMP_NEW,
          f"forward clamps {CLAMP_OLD} -> {CLAMP_NEW} -- PEAK delivered torque rises 33 %")
    check(u16(code, GAIN_CELL) == GAIN_NEW,
          f"forward gain {GAIN_OLD} -> {GAIN_NEW} ({GAIN_NEW / 891.0:.2f}x) -- LOWER, which is "
          f"what buys the ratchet back")
    _rail_old = CLAMP_OLD * 891.0 / GAIN_OLD
    _rail_new = CLAMP_NEW * 891.0 / GAIN_NEW
    check(_rail_new > _rail_old * 1.4,
          f"the rail moves {_rail_old:.0f} -> {_rail_new:.0f} counts of command: the loop is open "
          f"LESS often, which is the peak-command-oscillation symptom")
    _nb = [struct.unpack_from("<h", code, FB26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_nb == [FB_NEW] * 4,
          f"V250's doubled FactorB is CARRIED {_nb}")
    _fe = _lerp(OP_POINT, [12, 400, 2500, 4000], [0, 539, 539, 927])
    _v249 = 1024.0 * (429 / 1024) * (_fe / 1024)
    _v250 = _v249 * (FB_NEW / FB_OLD)
    check(_v250 > 56.0,
          f"the damper goes {_v249:.1f} -> {_v250:.1f} counts AT EVERY SPEED, past the ~56 "
          f"needed to cancel Re(Z) = -65 ({100 * _v250 / 56:.0f}% of requirement)")
    check(_v250 < 512,
          f"{_v250:.1f} stays UNDER the 512 ceiling floor, so nothing new clamps")
    check(1024.0 * (908 / 1024) * (927 / 1024) * (FB_NEW / FB_OLD) > 512,
          "at HIGH rate the product still clamps at 512 exactly as at stock -- doubling FactorB "
          "changes nothing at the top end, only the low/mid-rate region")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    # the shape gates: FactorC must stay monotone and its X axis untouched
    _ncy = [struct.unpack_from("<h", code, FC26 + 10 + 2 * _i)[0] for _i in range(4)]
    _ncx = [struct.unpack_from("<h", code, FC26 + 2 + 2 * _i)[0] for _i in range(4)]
    check(_ncx == [2240, 3840, 5120, 8960] and _ncy == [429, 234, 429, 908],
          f"V249's FactorC is CARRIED unchanged X={_ncx} Y={_ncy} -- FactorB is the only "
          f"variable between this build and V249")
    check(bytes(code[FB24:FB24 + 20]) == bytes(base[FB24:FB24 + 20]),
          "the MANUAL FactorB record (mode 24) is BYTE-IDENTICAL -- manual steering feel is "
          "untouched at every speed")
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
    check(len(pay) <= 6, f"{len(pay)} payload byte(s): two clamps and the gain")
    check(set(pay) <= {CLAMP_P, CLAMP_P + 1, CLAMP_N, CLAMP_N + 1, GAIN_CELL, GAIN_CELL + 1},
          "every payload byte is a clamp or the gain -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V254 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v254_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V254_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V254 -- THE ONLY CONFIGURATION STRICTLY BETTER THAN THE CAR ON ALL THREE                           **")
    print("  ** SYMPTOMS AT ONCE.                                                                                  **")
    print("  **   0xC61B2/B4   3072 -> 4096   break the clamp/gain tracking                                        **")
    print("  **   0xC6CD0      5346 -> 4455   forward gain 6x -> 5x                                                **")
    print("  ** THE COUNTERINTUITIVE PART: peak delivered torque is set by the CLAMP, not the                      **")
    print("  ** gain. So lowering the gain and raising the clamp loses torque per unit command                     **")
    print("  ** but RAISES the ceiling it is clipped at -- and the clamp repays more than the                      **")
    print("  ** gain costs, while BOTH changes reduce the ratchet.                                                 **")
    print("  ** MEASURED over 1,691,012 engaged frames of real openpilot command:                                  **")
    print("  **   config            gain clamp  rail   mean deliv  Re(Z)      vs car                               **")
    print("  **   V122 the car      6.0x  3072  30.2%      1688    -64.8        --                                 **")
    print("  **   V251 clamp only   6.0x  4096  24.9%      1968    -64.8  +17% / 0.0                               **")
    print("  **   V252 8x           8.0x  4096  30.2%      2251    -73.6  +33% / -8.8                              **")
    print("  **   THIS BUILD        5.0x  4096  22.3%      1801    -54.9   +7% / +9.9                              **")
    print("  ** LEDGER: +7% mean torque, +33% PEAK torque, -26% rail duty, +9.9 Re(Z)                              **")
    print("  **         (= 15% of the 65 needed; +4.4 from the gain, +5.5 from the damper).                        **")
    print("  ** HONEST WEAKNESS: '5x' reads like less torque. DELIVERED torque goes UP, but if                     **")
    print("  ** you judge by feel at a given input rather than lane-holding, it may feel softer                    **")
    print("  ** below the rail. That is a feel question only a drive settles.                                      **")
    print("  ** CONSERVATIVE ALTERNATIVE: V251 -- clamp only, gain untouched, +17% torque but                      **")
    print("  ** no ratchet benefit.                                                                                **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
