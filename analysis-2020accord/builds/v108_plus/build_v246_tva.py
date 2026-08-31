# -*- coding: utf-8 -*-
r"""V246 -- LEVER B RAISED 1.5x. THE FIRST LEVER MEASURED TO HELP THE RATCHET AT FIXED AUTHORITY.

WHY THIS BUILD EXISTS, and it comes out of a measurement made after V241 was cut.

The 6-9 Hz anti-damping -- the thing that makes the wheel ratchet -- tracks the FORWARD LKAS GAIN
across every flown build (rho -0.819, n=17).  Forward gain is also what buys authority, so the two are
locked, and three separate escapes were checked and CLOSED this session:

  * the tracking CLAMP is not independent -- it follows the gain as `gain*512//891`, so a clamp-only
    build is inert;
  * the `0xC646C` FEEDBACK path has |k| = 0.0073 at 7.79 Hz, so zeroing it moves Re(Z) by 0.13 of the
    65 measured;
  * a forward-path LOW-PASS has nothing to cut -- the LKAS command carries only 0.09-1.7 % of its
    0-5 Hz energy at 6-9.5 Hz.

**Lever B is the one cell that is NOT locked to authority and DOES move the ratchet.**  Controlling for
gain (the mirror of the control run on gain itself):

    WITHIN GAIN 6x    LeverB  512 (n=2)   Re(Z) -73.59
                      LeverB 5244 (n=7)   Re(Z) -67.78
                      Mann-Whitney p = 0.0556, +5.81 in favour of the higher dose

More Lever B is LESS anti-damped, at the same authority.  That is the trade the operator has been
asking for and it is the first cell to show it.

WHY 1.5x AND NOT MORE.  Lever B's real ceiling is its DESCRIBING FUNCTION, not its cal range: the lane
is a plain saturation and `N(A) -> 4L*1024/(pi*A)` as k grows, independent of k.  The knee sits at
k = 58624 at p90 torque-rate amplitude, 14080 at p99, and 5184 at max.  **So at typical amplitudes the
car's 5244 is FAR BELOW the knee -- still in the linear region, where raising k genuinely buys
damping** -- while the very largest excursions are already saturated and will not change.

    5244 -> 7866   (1.5x)   stays far below the p99 knee of 14080; V222's 2.5x = 13107 was flagged as
                            over-dosing V88's grinding optimum, so this deliberately does NOT go there.

WHAT IS ASSUMED, STATED PLAINLY.  V62's lesson is *"2x is the OPTIMUM, not a point on a ramp"* -- 5244
was BRACKETED by V88 for GRINDING, and this build moves off that optimum.  Whether that costs grinding
is NOT established: the only cross-build grinding comparison available is an uncontrolled band-fraction
(no speed matching, no road control) whose groups overlap heavily.  It happens to point the same way --
less grinding at the higher dose -- but it is not evidence and is not being claimed as any.

**So this is a ONE-VARIABLE EXPERIMENT with a measured direction at the ratchet and an unmeasured cost
at the grinding band.**  If the operator reports more grinding, the answer is 5244 and the lever is
priced; if he reports less ratchet with grinding unchanged, it is the first cell to beat the trade.

WHAT A DRIVE SETTLES.  Ratchet at creep, against V241 on the same roads.  Both builds carry identical
notch, identical gain, identical everything else -- Lever B is the ONLY variable, 2 bytes.

BASE: V241.  Two bytes.
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
WRITE_MODE = os.environ.get("ACCORD_V246_WRITE", "").strip().lower()

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
GAIN = 0xC6CD0                              # forward LKAS gain -- asserted UNCHANGED
LEVER_B_NEW = 7866                          # 1.5x of V88's 5244; p99 knee is 14080
KNEE_P99 = 14080                            # describing-function knee -- must stay BELOW
FS_HZ = 1000.0                              # the control task rate
POLE_Y, K_STOCK = 0xC6906, 20               # the lag pole -- asserted STOCK, V241 does not touch it
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V246-V241BASE-LEVERB.5244.TO.7866"

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
    check(u16(base, LEVER_B) == LEVER_B_VAL,
          f"base Lever B = {LEVER_B_VAL} -- V88's bracketed optimum, the value this moves off")
    check(LEVER_B_NEW < KNEE_P99,
          f"new dose {LEVER_B_NEW} stays BELOW the p99 describing-function knee {KNEE_P99}, "
          f"so it lands in the lane's LINEAR region rather than its saturated one")
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, LEVER_B, LEVER_B_NEW)
    attributed |= {LEVER_B, LEVER_B + 1}
    check(u16(code, LEVER_B) == LEVER_B_NEW,
          f"Lever B {LEVER_B_VAL} -> {LEVER_B_NEW} "
          f"({LEVER_B_NEW / LEVER_B_VAL:.2f}x, the ONLY variable in this build)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the notch is CARRIED byte-for-byte -- V241's grinding treatment is untouched, so "
          "Lever B is the only variable between this build and V241")
    check(u16(code, GAIN) == u16(base, GAIN),
          "the forward GAIN is UNCHANGED -- this buys ratchet without spending authority, "
          "which is the whole point of the build")
    check(u16(code, LKAS_CLAMP) == 0,
          "0xC616C = 0 -- the map is fed by the driver torque sensor alone; LKAS cannot reach it")
    check(u16(code, LEVER_B) == LEVER_B_NEW,
          f"Lever B now {LEVER_B_NEW} -- deliberately OFF V88's grinding optimum")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")

    print("\n  [4] LEVER B IS THE ONE THING V246 CHANGES; ELSE V241 BYTE FOR BYTE")
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == bytes(base[BIQ:BIQ + BIQ_LEN]),
          "the biquad block is CARRIED byte-for-byte -- V246 changes Lever B and nothing else")
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
    check(len(pay) <= 2, f"{len(pay)} payload byte(s), at most the Lever B halfword")
    check(set(pay) <= {LEVER_B, LEVER_B + 1},
          "every payload byte is Lever B -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V246 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v246_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V246_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V246 RAISES LEVER B 1.5x -- THE FIRST LEVER MEASURED TO HELP THE RATCHET                           **")
    print("  ** AT FIXED AUTHORITY.                                                                                **")
    print("  **   0xC6446   5244 -> 7866   (1.5x; p99 describing-function knee is 14080)                           **")
    print("  ** WHY: the ratchet's anti-damping tracks the FORWARD GAIN, which is also what                        **")
    print("  ** buys authority -- so they are locked, and three escapes were closed this                           **")
    print("  ** session (the clamp tracks the gain; the 0xC646C feedback path is 0.7%; a                           **")
    print("  ** forward low-pass has nothing to cut). Lever B is the one cell that is NOT                          **")
    print("  ** locked to authority and DOES move the ratchet:                                                     **")
    print("  **   WITHIN GAIN 6x   LeverB  512 (n=2)  Re(Z) -73.59                                                 **")
    print("  **                    LeverB 5244 (n=7)  Re(Z) -67.78   p=0.0556, +5.81                               **")
    print("  ** WHY 1.5x: the lane is a saturation and N(A) -> 4L*1024/(pi*A) independent of                       **")
    print("  ** k. The knee is 58624 at p90 amplitude, 14080 at p99, 5184 at max -- so at                          **")
    print("  ** TYPICAL amplitudes 5244 is far BELOW the knee, in the linear region where                          **")
    print("  ** raising k still buys damping. 7866 stays well under the p99 knee.                                  **")
    print("  ** WHAT IS ASSUMED: 5244 is V88's BRACKETED optimum for GRINDING, and this moves                      **")
    print("  ** off it. Whether that costs grinding is NOT established -- the only cross-build                     **")
    print("  ** grinding comparison is uncontrolled and its groups overlap. It happens to point                    **")
    print("  ** the same way, but that is not evidence and is not claimed as any.                                  **")
    print("  ** ONE VARIABLE vs V241: identical notch, identical gain, 2 bytes.                                    **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
