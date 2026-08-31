# -*- coding: utf-8 -*-
r"""V251 -- BREAK THE CLAMP/GAIN TRACKING. THE FIRST LEVER AIMED AT *PEAK COMMAND OSCILLATION*.

THE SYMPTOM THIS ARC HAS ADDRESSED LEAST.  The operator names three: grinding, LKAS authority, and
PEAK COMMAND OSCILLATION.  The third has never had a lever of its own.  It does now, and the mechanism
is specific: **while the command is at its rail the loop is briefly OPEN** -- openpilot asks for more
and receives a fixed value -- which is the textbook setup for a limit cycle.

MEASURED, 2,353 railed vs 5,850 free engaged windows, each symptom band normalised by a 12-18 Hz
CONTROL band so the "hard driving" factor cancels:

    ratchet  / control :  railed 2.378   free 0.788   ratio 3.02   p ~ 0
    grinding / control :  railed 0.631   free 0.335   ratio 1.88   p 2e-265

🛑 THE FIRST VERSION OF THAT TEST FAILED AND ITS CONTROL SAID SO.  Normalising by TOTAL energy
put the control band at ratio 0.250 -- moving more than either symptom band -- because railing
correlates with cornering, whose large low-frequency content inflates the denominator and pushes every
fraction down.  Normalising by the control band instead is what makes the split readable.

WHY THE GAIN LADDER DOES NOT FIX IT, THOUGH IT LOOKS LIKE IT SHOULD.  The forward clamp TRACKS the gain
as `gain*512//891`, so the saturation threshold is

    clamp * 891 / gain  =  512 counts of openpilot command  --  AT EVERY GAIN

Raising the gain moves the clamp with it and buys **no headroom at all**.  V242/V243 would not touch
this symptom.  (This also corrects an earlier note of mine that a clamp-only build is "inert": that was
true of the DAMPER's magnitude at the operating point, and false of SATURATION, which is what this
build is about.)

THE EDIT -- break the tracking, raise the clamp alone:

    0xC61B2   3072 -> 4096    forward clamp +
    0xC61B4   3072 -> 4096    forward clamp -
    0xC6CD0   5346            the GAIN, asserted UNCHANGED at 6x

    rail moves from 512 -> 682.7 counts of openpilot command
    mean rail duty across the flown corpus: 17.6 % -> 13.5 %  =  23 % less time at the rail

WHY 4096 AND NOT MORE.  The forward clamp must stay BELOW the soft-EME interlock `0xC674E` = 5120, and
4096 is a value that **has already flown** -- V101 carried it (at 8x gain), so the clamp itself is not
novel territory.  4608 would give 768 counts and ~26 % reduction, but it crowds the interlock for a
further 3 points of duty.

WHAT IT DOES NOT DO.  It does not raise torque: the gain is untouched, so assist per unit of command is
identical and the ratchet's gain dependence is not engaged.  What changes is that openpilot's larger
requests are delivered instead of clipped, so the loop stays closed more of the time.

🛑 THE RISK.  More delivered command at the peaks IS more authority in absolute terms, even
though the gain is unchanged -- the top 4 % of requests now arrive rather than being clipped at 3072.
If the car feels more aggressive in hard corners, or if the soft-EME interlock starts intervening, this
is the cell and 3072 is the way back.  Observational evidence only: railing is chosen by openpilot, not
assigned, so the 3.0x is an association under a good control, not a controlled experiment.

BASE: V249 -- so this carries the notch, both damper dead zones, and now the rail fix: one build
against all three symptoms.  Four bytes.
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
WRITE_MODE = os.environ.get("ACCORD_V251_WRITE", "").strip().lower()

BASE_NAME = "_v249_V249-V247BASE-FACTORC.SPEED.DEADZONE.OPEN_plain_image.bin"
BASE_SHA = "9c1ac13746538b45e7dc56057ab02728b403b90aeae473c9c18cc874b03ecb50"

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
CLAMP_OLD, CLAMP_NEW = 3072, 4096           # break the tracking: rail 512 -> 682.7 counts
GAIN_CELL, GAIN_VAL = 0xC6CD0, 5346         # 6x -- asserted UNCHANGED, this is not a gain step
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
TAG = "V251-V249BASE-CLAMP.4096.RAIL.HEADROOM"

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
    check(u16(base, CLAMP_P) == CLAMP_OLD and u16(base, CLAMP_N) == CLAMP_OLD,
          f"base forward clamps are {CLAMP_OLD}, i.e. TRACKING the gain as gain*512//891")
    check(u16(base, GAIN_CELL) == GAIN_VAL,
          f"base gain is {GAIN_VAL} (6x) -- the value this build must NOT change")
    check(CLAMP_NEW < u16(base, SOFT_EME),
          f"the new clamp {CLAMP_NEW} stays BELOW the soft-EME interlock "
          f"{u16(base, SOFT_EME)} -- the ceiling that makes the command deliverable")
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, CLAMP_P, CLAMP_NEW)
    struct.pack_into("<H", code, CLAMP_N, CLAMP_NEW)
    attributed |= {CLAMP_P, CLAMP_P + 1, CLAMP_N, CLAMP_N + 1}
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
    check(len(pay) <= 4, f"{len(pay)} payload byte(s), at most the two clamp halfwords")
    check(set(pay) <= {CLAMP_P, CLAMP_P + 1, CLAMP_N, CLAMP_N + 1},
          "every payload byte is a forward clamp -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V251 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v251_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V251_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V251 = V249 + THE CLAMP RAISED ALONE. AIMED AT *PEAK COMMAND OSCILLATION*,                         **")
    print("  ** the one symptom this arc had never given a lever.                                                  **")
    print("  **   0xC61B2/B4   3072 -> 4096     forward clamps, both signs                                         **")
    print("  **   0xC6CD0      5346             the GAIN, asserted UNCHANGED at 6x                                 **")
    print("  ** MECHANISM: while the command is at its rail the loop is briefly OPEN --                            **")
    print("  ** openpilot asks for more and gets a fixed value. Measured over 2353 railed vs                       **")
    print("  ** 5850 free engaged windows, normalised by a 12-18 Hz control band:                                  **")
    print("  **   ratchet / control   railed 2.378  free 0.788  ratio 3.02  p ~ 0                                  **")
    print("  **   grinding/ control   railed 0.631  free 0.335  ratio 1.88  p 2e-265                               **")
    print("  ** WHY THE GAIN LADDER DOES NOT FIX THIS: the clamp TRACKS the gain as                                **")
    print("  ** gain*512//891, so the rail sits at 512 counts of command AT EVERY GAIN.                            **")
    print("  ** V242/V243 buy no headroom at all. Breaking the tracking does:                                      **")
    print("  **   rail 512 -> 683 counts;  mean rail duty 17.6% -> 13.5%  = 23% less                               **")
    print("  ** NOT A TORQUE STEP: the gain is untouched, so assist per unit command is                            **")
    print("  ** identical and the ratchet's gain dependence is not engaged.                                        **")
    print("  ** RISK: the top ~4% of requests now arrive instead of being clipped, so the car                      **")
    print("  ** may feel more decisive in hard corners. 4096 has flown before (V101) and stays                     **")
    print("  ** below the soft-EME interlock 5120. Revert to 3072 to undo.                                         **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
