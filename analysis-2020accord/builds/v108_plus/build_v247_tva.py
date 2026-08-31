# -*- coding: utf-8 -*-
r"""V247 -- OPEN THE DAMPER'S RATE DEAD ZONE, ENGAGED ONLY. THE BIGGEST UNFLOWN LEVER IN THE KIT.

WHY THIS IS THE ONE.  The ratchet is a LINEAR anti-damping of Re(Z) ~ -65 that engagement switches on,
and an exhaustive FDR-corrected census of every calibration cell that varies across the 16 flown builds
found only TWO things that track it: the forward GAIN (which is the authority the operator wants) and
LEVER B.  So the CAL SURFACE ON THE FLOWN CORPUS is exhausted.  But that census can only test cells
that have actually VARIED -- and the damper's dead zones have been BYTE-STOCK IN ALL 18 FLOWN BUILDS.
They were never tested because they were never moved.

    FactorE (engaged, mode 26 @0xD780C)   X=[60, 400, 2500, 4000]   Y=[0, 140, 539, 927]

Below X[0]=60 counts of motor rate the LERP clamps flat to Y[0]=0, and zero x anything = 0, so THE
DAMPER IS OFF.  The ratchet's measured operating point is gp-0x6ac0 = 99 counts [94,113] -- just past
the dead zone, on the first rising segment, where the curve is still near zero:

    LERP(99) on X=[60,400] Y=[0,140]   =  16.1   =>  damper delivers ~6.7 counts
    LERP(99) on X=[12,400] Y=[0,539]   = 120.8   =>  damper delivers ~50.6 counts

THE REQUIREMENT, computed independently two ways and agreeing.  Re(Z) = -65 at the measured p50 band
amplitude of 0.86 deg/s is ~56 counts of torque -- 0.5 % of the aggregator's +-10240, so the magnitude
needed to cancel the ratchet is SMALL and the problem was never headroom.  The record's own pricing of
this same lever, done for a different purpose, says "BOTH dead zones opened ~50" against "a requirement
of ~43".  **Two independent routes land at ~50 against a requirement of 43-56.**

WHY IT HAS NEVER FLOWN.  V72 and V73 tried it and were INERT BY TABLE SELECTION -- they edited modes
10/11 on the assumption that this part number is row 2 'TVAA1'.  It is not: the car is row 11 'TVCA4'
and runs mode 24 DISENGAGED / 26 ENGAGED.  So the lever is UNFLOWN and UNFALSIFIED, not tried-and-failed.

    0xD780E   X[0]  60 -> 12    open the rate dead zone
    0xD7818   Y[1] 140 -> 539   := Y[2], so the first segment carries real slope

ENGAGED ONLY, AND THAT IS LOAD-BEARING.  Every mode owns its OWN record -- mode 26 is @0xD780C, mode 24
@0xD6820, no sharing -- so this changes the damper ONLY while openpilot is steering.  **Manual feel is
byte-identical**, which matters because the operator's standing instruction is "increasing mass and
friction should not be our primary approach ... we want LOW apparent steering mass and friction".  A
damper that only exists when the car is driving itself does not spend that.

GATE 2, and V72's exact mistake avoided.  V72 set FactorE Y[0..2] -> 927, i.e. FLAT across the whole
rate axis, turning a rate-proportional damper into a near-BANG-BANG RELAY -- and a relay in a loop at a
lightly-damped resonance is a limit-cycle GENERATOR.  This build does the opposite:

  * Y[0] stays 0, so the damper still goes to ZERO at zero rate -- no relay, no constant magnitude;
  * the curve stays MONOTONE non-decreasing: [0, 539, 539, 927];
  * it OPENS the dead zone rather than raising a gain, so the lane becomes genuinely rate-proportional
    in the symptom's range instead of flatter.

Ceiling: at the ratchet point FactorC(429) x FactorE(120.8) >> 10 = 50.6, far under the 512 floor of
the output ceiling, so nothing new clamps.  At the high-rate end the product already clamped at stock
and still does -- unchanged behaviour.

THE COST, stated plainly.  ~50 counts of added damping against a 3072 forward clamp is ~1.6 % of LKAS
authority, spent only while engaged.  If the operator reports LKAS feeling lazier or less willing to
hold a lane, this is the cell and 60/140 is the way back.

WHAT A DRIVE SETTLES.  The ratchet at the creep/micro regime, against V241 on the same roads.  4 bytes,
one lane, engaged only.

BASE: V241.  Four bytes.
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
WRITE_MODE = os.environ.get("ACCORD_V247_WRITE", "").strip().lower()

BASE_NAME = "_v241_V241-V235BASE-NOTCH.IMU.29.75-22.50-0.940_plain_image.bin"
BASE_SHA = "2ef7eb8eb24179054b0c016d13f2e240b7fe3ea32d419c047405f1a748109df4"

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
TAG = "V247-V241BASE-FACTORE.DEADZONE.OPEN.ENGAGED"

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
    check(_fx == [60, 400, 2500, 4000] and _fy == [0, 140, 539, 927],
          f"base FactorE(engaged) X={_fx} Y={_fy} -- Honda stock, byte-identical in all 18 "
          f"flown builds, which is why this lever has never been tested")
    check(OP_POINT > X0_OLD,
          f"the ratchet operating point {OP_POINT} is just PAST the dead zone edge {X0_OLD} -- "
          f"on the first rising segment, where the curve is still near zero")
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<h", code, FE_X0, X0_NEW)
    struct.pack_into("<h", code, FE_Y1, Y1_NEW)
    attributed |= {FE_X0, FE_X0 + 1, FE_Y1, FE_Y1 + 1}
    def _lerp(v, X, Y):
        if v <= X[0]:
            return float(Y[0])
        for _i in range(len(X) - 1):
            if v < X[_i + 1]:
                return Y[_i] + (Y[_i + 1] - Y[_i]) * (v - X[_i]) / (X[_i + 1] - X[_i])
        return float(Y[-1])
    _was = _lerp(OP_POINT, [60, 400, 2500, 4000], [0, 140, 539, 927])
    _now = _lerp(OP_POINT, [X0_NEW, 400, 2500, 4000], [0, Y1_NEW, 539, 927])
    check(struct.unpack_from("<h", code, FE_X0)[0] == X0_NEW,
          f"FactorE X[0] {X0_OLD} -> {X0_NEW} -- the rate dead zone is OPEN")
    check(struct.unpack_from("<h", code, FE_Y1)[0] == Y1_NEW,
          f"FactorE Y[1] {Y1_OLD} -> {Y1_NEW} -- the first segment carries real slope")
    check(_now > _was * 5,
          f"at the measured operating point {OP_POINT}: FactorE {_was:.1f} -> {_now:.1f} "
          f"({_now / _was:.1f}x more damping where the ratchet actually lives)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    # GATE 2 -- V72 turned this lane into a RELAY and a relay at a lightly-damped resonance is
    # a limit-cycle GENERATOR. These three assertions are what make this the opposite of that.
    _ny = [struct.unpack_from("<h", code, FE26 + 10 + 2 * _i)[0] for _i in range(4)]
    _nx = [struct.unpack_from("<h", code, FE26 + 2 + 2 * _i)[0] for _i in range(4)]
    check(_ny[0] == 0,
          "Y[0] is still ZERO -- the damper goes to zero at zero rate, so this is NOT a relay")
    check(all(_ny[_i] <= _ny[_i + 1] for _i in range(3)),
          f"the curve stays MONOTONE non-decreasing {_ny} -- rate-proportional, not bang-bang")
    check(all(_nx[_i] < _nx[_i + 1] for _i in range(3)),
          f"the X axis stays strictly increasing {_nx} -- the LERP is not corrupted")
    check(bytes(code[FE24:FE24 + 20]) == bytes(base[FE24:FE24 + 20]),
          "the MANUAL FactorE record (mode 24) is BYTE-IDENTICAL -- manual steering feel is "
          "untouched, which is what makes added damping affordable here")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the notch is CARRIED byte-for-byte -- V241's grinding treatment is untouched")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL} -- this build is NOT V246, it is a different lane")
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
    check(len(pay) <= 4, f"{len(pay)} payload byte(s), at most the two FactorE halfwords")
    check(set(pay) <= {FE_X0, FE_X0 + 1, FE_Y1, FE_Y1 + 1},
          "every payload byte is inside the ENGAGED FactorE record -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V247 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v247_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V247_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V247 OPENS THE DAMPER'S RATE DEAD ZONE, ENGAGED ONLY.                                              **")
    print("  ** THE BIGGEST UNFLOWN LEVER IN THE KIT -- byte-stock in ALL 18 flown builds.                         **")
    print("  **   0xD780E   FactorE X[0]  60 -> 12    open the rate dead zone                                      **")
    print("  **   0xD7818   FactorE Y[1] 140 -> 539   := Y[2], real slope on segment 1                             **")
    print("  ** WHY IT REACHES: the ratchet sits at gp-0x6ac0 = 99 counts, just past the                           **")
    print("  ** dead zone edge where the curve is still near zero.                                                 **")
    print("  **   LERP(99) now  =  16.1  -> damper ~6.7 counts                                                     **")
    print("  **   LERP(99) V247 = 120.8  -> damper ~50.6 counts                                                    **")
    print("  ** Re(Z) = -65 at the measured 0.86 deg/s band amplitude is ~56 counts, and the                       **")
    print("  ** record's own independent pricing of this lever says ~50 against a ~43                              **")
    print("  ** requirement. Two routes agree.                                                                     **")
    print("  ** WHY IT NEVER FLEW: V72/V73 edited modes 10/11 assuming row 2 'TVAA1'. The car                      **")
    print("  ** is row 11 'TVCA4', modes 24/26. Inert by table selection -- not falsified.                         **")
    print("  ** ENGAGED ONLY: every mode owns its own record, so MANUAL IS BYTE-IDENTICAL.                         **")
    print("  ** Added damping costs nothing in manual feel, which the operator has ruled out                       **")
    print("  ** spending.                                                                                          **")
    print("  ** GATE 2 -- V72 flattened this to a RELAY (a limit-cycle generator). This does                       **")
    print("  ** the opposite: Y[0] stays 0, the curve stays monotone, and it OPENS the dead                        **")
    print("  ** zone rather than raising a gain.                                                                   **")
    print("  ** COST: ~50 counts against a 3072 clamp is ~1.6% of LKAS authority, engaged only.                    **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
