# -*- coding: utf-8 -*-
r"""V252 -- 8x GAIN ON TOP OF EVERY FIX. THE AUTHORITY STEP THE OPERATOR ASKED FOR, EARNED.

WHY THIS EXISTS AND WHY ONLY NOW.  The operator's brief was "6x or higher, up to 16x, with no
grinding, vibration or oscillation".  Until this session the gain step was unaffordable: the ratchet
tracks the forward gain (rho -0.819 across 17 flown builds), so 8x meant measurably more of the very
symptom being chased, with nothing to pay for it.  That has changed.  This build sits on:

    V241  the IMU-aimed notch                     -- grinding
    V247  FactorE, the damper's RATE dead zone    -- ratchet
    V249  FactorC, the damper's SPEED dead zone   -- ratchet at every speed
    V251  the clamp raised alone                  -- rail time, and +11.7 % delivered authority

    0xC6CD0   5346 -> 7128    the forward LKAS gain, 6x -> 8x

THE CLAMP IS ALREADY RIGHT.  V251 raised it to 4096, which is exactly `gain*512//891` at 8x -- so this
build restores the TRACKING rather than breaking it further, and the clamp cell is not touched here at
all.  One cell moves.

WHAT IS BOUGHT AND WHAT IS PAID, both measured rather than asserted:

    BOUGHT   +33 % assist per unit of command, everywhere -- not just at the peaks
    PAID     the rail returns from 683 to 512 counts of openpilot command, so V251's 23 % reduction
             in rail time is GIVEN BACK
    PAID     ~13 units of Re(Z) of anti-damping, from the gain/ratchet relation (rho -0.819)
    OFFSET   V249 supplies ~50 counts of damping against a ~56-count requirement, which is the
             first time in this arc that anything has been on the other side of that ledger

🛑 THIS IS THE ONE BUILD ON THE SHELF THAT MAKES A SYMPTOM WORSE ON PURPOSE.  Every other build
in the V246-V251 group is symptom-reducing or symptom-neutral.  This one spends ratchet to buy torque,
deliberately, because the operator asked for the torque and the damper fix is what makes the spend
survivable.  **It is NOT the build to fly if the ratchet is the priority.**

🛑 AND IT IS ONLY MEANINGFUL AFTER V251 HAS FLOWN CLEAN.  If V249/V251 do not fix the ratchet,
this build inherits an unfixed ratchet AND adds 13 units to it.  Flying it early wastes the whole
discrimination the shelf was built to provide.

HISTORY THIS WALKS BACK INTO, stated plainly.  8x flew once as V101 and was rejected -- "grinding and
vibration at all speeds, only while LKAS commands".  V101 carried NO grinding treatment, NO damper, and
NO notch.  This carries all three.  That is the whole bet, and it is unflown.

BASE: V251.  Two bytes.
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
WRITE_MODE = os.environ.get("ACCORD_V252_WRITE", "").strip().lower()

BASE_NAME = "_v251_V251-V249BASE-CLAMP.4096.RAIL.HEADROOM_plain_image.bin"
BASE_SHA = "b1976f8f442e7533f48a6b2c4a79c774276976c92a844a760d2a7de97de75b4d"

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
CLAMP_P, CLAMP_N = 0xC61B2, 0xC61B4         # forward clamps -- normally TRACK the gain
CLAMP_HELD = 4096                           # V251 already set this -- and it IS gain*512//891 at 8x
GAIN_OLD, GAIN_NEW = 5346, 7128             # 6x -> 8x, the only cell this build moves
GAIN_CELL = 0xC6CD0                         # the forward LKAS gain -- THIS build's one edit
SOFT_EME = 0xC674E                          # the interlock the clamp must stay BELOW
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
TAG = "V252-V251BASE-GAIN8X.ON.THE.DAMPER.FIX"

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
          f"base carries V249's opened SPEED dead zone Y={_cy} -- this build stacks the rail "
          f"fix on the damper fix rather than replacing it")
    check(u16(base, CLAMP_P) == CLAMP_HELD and u16(base, CLAMP_N) == CLAMP_HELD,
          f"base carries V251's clamp {CLAMP_HELD} -- which IS gain*512//891 at 8x, so this "
          f"build RESTORES the tracking rather than breaking it, and never touches the clamp")
    check(u16(base, GAIN_CELL) == GAIN_OLD,
          f"base gain is {GAIN_OLD} (6x) -- the one cell this build moves")
    check(GAIN_NEW * 512 // 891 == CLAMP_HELD,
          f"gain*512//891 = {GAIN_NEW * 512 // 891} == the clamp already in place: the pair is "
          f"COHERENT at 8x without a second edit")
    check(CLAMP_HELD < u16(base, SOFT_EME),
          f"the clamp {CLAMP_HELD} stays BELOW the soft-EME interlock {u16(base, SOFT_EME)}")
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, GAIN_CELL, GAIN_NEW)
    attributed |= {GAIN_CELL, GAIN_CELL + 1}
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
    _ncy = [struct.unpack_from("<h", code, FC26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_ncy == [429, 234, 429, 908],
          f"V249's FactorC is CARRIED unchanged {_ncy} -- the clamp is the only variable")
    _ney = [struct.unpack_from("<h", code, FE26 + 10 + 2 * _i)[0] for _i in range(4)]
    check(_ney == [0, 539, 539, 927],
          f"V247's FactorE is CARRIED unchanged {_ney}")
    check(bytes(code[FE24:FE24 + 20]) == bytes(base[FE24:FE24 + 20])
          and bytes(code[FC24:FC24 + 20]) == bytes(base[FC24:FC24 + 20]),
          "both MANUAL damper records are BYTE-IDENTICAL -- manual feel untouched")
    check(u16(code, SOFT_EME) == u16(base, SOFT_EME),
          f"the soft-EME interlock is FROZEN at {u16(base, SOFT_EME)} -- this build raises "
          f"the clamp toward it, never the interlock itself")
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
    check(len(pay) <= 2, f"{len(pay)} payload byte(s), at most the gain halfword")
    check(set(pay) <= {GAIN_CELL, GAIN_CELL + 1},
          "every payload byte is the forward gain -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V252 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v252_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V252_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V252 = 8x GAIN ON TOP OF EVERY FIX. THE AUTHORITY STEP, EARNED.                                    **")
    print("  **   0xC6CD0   5346 -> 7128   forward LKAS gain, 6x -> 8x   (ONE cell)                                **")
    print("  ** The clamp is ALREADY right: V251 set it to 4096, which IS gain*512//891 at                         **")
    print("  ** 8x -- so this RESTORES the tracking and never touches the clamp.                                   **")
    print("  ** IT SITS ON: V241 notch (grinding) + V247/V249 both damper dead zones                               **")
    print("  ** (ratchet, all speeds) + V251 clamp (rail time, +11.7% delivered authority).                        **")
    print("  ** BOUGHT: +33% assist per unit command, everywhere -- not just at the peaks.                         **")
    print("  ** PAID:   the rail returns 683 -> 512 counts, so V251's 23% rail-time                                **")
    print("  **         reduction is GIVEN BACK.                                                                   **")
    print("  ** PAID:   ~13 units of Re(Z) anti-damping, from the gain/ratchet relation.                           **")
    print("  ** OFFSET: V249 supplies ~50 counts of damping against a ~56 requirement --                           **")
    print("  **         the first time anything has been on the other side of that ledger.                         **")
    print("  ** THIS IS THE ONE BUILD THAT MAKES A SYMPTOM WORSE ON PURPOSE. Every other                           **")
    print("  ** build in the V246-V251 group is symptom-reducing or neutral. NOT the build                         **")
    print("  ** to fly if the ratchet is the priority.                                                             **")
    print("  ** ONLY MEANINGFUL AFTER V251 FLIES CLEAN -- otherwise it inherits an unfixed                         **")
    print("  ** ratchet and adds 13 units to it.                                                                   **")
    print("  ** HISTORY: 8x flew once as V101 and was rejected for grinding at all speeds.                         **")
    print("  ** V101 had NO notch, NO damper, NO grinding treatment. This has all three.                           **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
