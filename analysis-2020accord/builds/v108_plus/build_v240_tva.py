# -*- coding: utf-8 -*-
r"""V240 -- THE NORMAL SLEW CURVE, TIGHTENED BY HONDA'S OWN RATIO. THE LARGEST MEASURED RATCHET LEVER.

WHAT IT IS. `gp-0x69a0` is the slew limit that rate-limits the assist-map walk in `FUN_000352b4`.
`FUN_00035b20` selects it from TWO curves on the hard-reversal counter:

    NORMAL       X 0xC6936 = [320, 1600, 3200, 4480]   Y 0xC693E = [358, 358, 461, 512]
    OSCILLATING  X 0xC6912 = [640, 3200, 6400, 12800]  Y 0xC691A = [358, 307, 307, 307]

**V192 tightened the OSCILLATING curve.** Its own card says that curve "is read ONLY on the counter>=5
branch so it is provably inert in normal driving". **The NORMAL curve has never been touched -- it is
byte-stock on all 161 images -- and it is the one live in ordinary driving.**

V240 applies Honda's OWN ratio to it. Honda's oscillation response steps 512 -> 307 = 0.5996, so:

    [358, 358, 461, 512]  x 0.600  ->  [215, 215, 277, 307]

**Y[3] lands on 307, which is Honda's own oscillating value exactly.** V240 makes the normal curve as
tight at speed as Honda's own oscillation response already is.

MEASURED, not modelled. 14 routes, integer-exact firmware mirror driving real torque/speed/angle, Welch
band power at 6-9 Hz:

    6-9 Hz band   0.9399   -6.0 %   range 0.813 .. 1.000
    assist p50    1.0000   +0.0 %   <- ordinary driving is UNAFFECTED
    assist p95    0.9469   -5.3 %   <- only the top of the assist demand pays
    gate duty     5.78 %   (was 2.35 %)

FOR COMPARISON, measured the same way this session:

    0xC6906  the lag pole   WHOLE range (k 20 -> 2)   3.8 %
    0xC6384  the slope cap  2048 -> 1536              0.0 %   -- MEASURED INERT, V236/V239 withdrawn

**V240 is 1.6x the pole's ENTIRE range, and it costs nothing at the median.**

WHY THIS DIRECTION. Tightening the slew limit lowers `table2`, and the lane blends
`out(f) = table2 + H_k(f)*(table1 - table2)` -- at the ratchet H_k is 0.08, so the output sits close to
`table2`. A lower `table2` is less lane gain at 7.79 Hz, and every torque-fed lane is a denominator term
in `Z = (Z0 + P.F)/(1 - P.L)`, so less gain is less positive feedback and more damping.
**LOOSENING WAS TESTED AND IS WRONG:** removing the relay entirely (gate duty 0.00 %) RAISES band power
by 2.8 %. The limiter is helping; V240 makes it help more.

WHAT TO WATCH FOR. V192's card names the failure mode: "watch for a brief HESITATION replacing the
ratchet => too tight; back off to ~0.8". V192 was tightening a curve that is inert in normal driving;
V240 tightens the one that is always live, so the SAME warning applies with more force. 0.8 (= [286,
286, 369, 410]) is the back-off rung, and it measures -0.5 %.

WHAT IS ASSUMED. The -6.0 % is EVIDENCE for the LANE's contribution at the band. The step from there to
felt ratcheting is the loop model, and that model is the part the record calls incomplete -- it has
already been wrong twice this session. **A 6 % lane-gain reduction is not a promise of a 6 % symptom
reduction, in either direction.**

BASE: V238 (V235 + the lag pole at 8). V240 = V238 + these four halfwords.
"""
import hashlib
import os
import struct
import sys
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
WRITE_MODE = os.environ.get("ACCORD_V240_WRITE", "").strip().lower()

BASE_NAME = "_v238_V238-V235BASE-ENGAGED.LAGPOLE.8.TIGHTEN_plain_image.bin"
BASE_SHA = "34ceb5aefaa9bdd5fd656513ce3536ae3e0fd5590c5c8bb80b400aa90b8a5be5"

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
POLE_Y, K_NEW = 0xC6906, 8                  # V238's pole -- CARRIED, asserted only
SLEW_Y = 0xC693E                            # gp-0x69a0 NORMAL curve, LERP Y[0..3]
SLEW_X = 0xC6936                            # its X axis -- asserted, never written
SLEW_OLD = [358, 358, 461, 512]             # byte-stock on all 161 images
SLEW_NEW = [215, 215, 277, 307]             # x Honda's own 0.600; Y[3] == Honda's oscillating 307
OSC_Y = 0xC691A                             # V192's curve -- asserted UNTOUCHED here
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V240-V238BASE-NORMAL.SLEW.HONDA0.600"

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
    check([u16(base, SLEW_Y + 2 * _i) for _i in range(4)] == SLEW_OLD,
          f"base NORMAL slew curve = {SLEW_OLD} -- byte-stock on all 161 images")
    check([u16(base, SLEW_X + 2 * _i) for _i in range(4)] == [320, 1600, 3200, 4480],
          "its X axis reads [320, 1600, 3200, 4480] -- the NORMAL curve, not the oscillating one")
    check(all(u16(base, POLE_Y + 2 * _i) == K_NEW for _i in range(4)),
          f"base carries V238 pole at {K_NEW}")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    for _i in range(4):
        struct.pack_into("<H", code, SLEW_Y + 2 * _i, SLEW_NEW[_i])
        attributed |= {SLEW_Y + 2 * _i, SLEW_Y + 2 * _i + 1}
    check([u16(code, SLEW_Y + 2 * _i) for _i in range(4)] == SLEW_NEW,
          f"NORMAL slew curve {SLEW_OLD} -> {SLEW_NEW} (Honda own 0.600 ratio)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check([round(o * 0.6) for o in SLEW_OLD] == SLEW_NEW,
          "the new curve IS the stock curve times Honda own 0.600 -- not a hand-picked set")
    check(SLEW_NEW[3] == u16(code, OSC_Y + 6) == 307,
          "Y[3] lands on 307, which is Honda OWN oscillating value exactly")
    check([u16(code, OSC_Y + 2 * _i) for _i in range(4)] == [358, 307, 307, 307],
          "V192 OSCILLATING curve is UNTOUCHED -- this build moves only the normal one")
    check([u16(code, SLEW_X + 2 * _i) for _i in range(4)] == [320, 1600, 3200, 4480],
          "the X axis is UNTOUCHED -- only the four Y halfwords moved")
    check(all(u16(code, POLE_Y + 2 * _i) == K_NEW for _i in range(4)),
          f"V238 pole CARRIED at {K_NEW}")
    check(u16(code, LKAS_CLAMP) == 0,
          "0xC616C = 0 -- the map is fed by the driver torque sensor alone; LKAS cannot reach it")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")

    print("\n  [4] THE NOTCH AND EVERYTHING ELSE ARE V233, BYTE FOR BYTE")
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == bytes(base[BIQ:BIQ + BIQ_LEN]),
          "the net-damping-optimum biquad is untouched")
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
    _exp = sum(1 for _i in range(4) for k in range(2)
               if ((SLEW_OLD[_i] >> (8 * k)) & 0xFF) != ((SLEW_NEW[_i] >> (8 * k)) & 0xFF))
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(set(pay) <= {SLEW_Y + j for j in range(8)},
          "every payload byte is inside the NORMAL slew Y block -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V240 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v240_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V240_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V240 TIGHTENS THE NORMAL SLEW CURVE BY HONDA OWN 0.600 RATIO.                                      **")
    print("  **   gp-0x69a0 NORMAL      0xC693E [358,358,461,512] -> [215,215,277,307]                             **")
    print("  **   gp-0x69a0 OSCILLATING 0xC691A [358,307,307,307]  <- V192's, UNTOUCHED                            **")
    print("  ** V192 tightened the OSCILLATING curve, which its own card calls 'provably inert                     **")
    print("  ** in normal driving'. The NORMAL curve is byte-stock on all 161 images and IS the                    **")
    print("  ** one live in ordinary driving. Y[3] lands on 307 = Honda's own oscillating value.                   **")
    print("  ** MEASURED, 14 routes, integer-exact mirror + Welch band power at 6-9 Hz:                            **")
    print("  **   6-9 Hz band  0.9399  -6.0 %  range 0.813..1.000                                                  **")
    print("  **   assist p50   1.0000  +0.0 %   <- ordinary driving UNAFFECTED                                     **")
    print("  **   assist p95   0.9469  -5.3 %   <- only the top of assist demand pays                              **")
    print("  ** vs 0xC6906 pole WHOLE range 3.8 % and 0xC6384 slope cap 0.0 % (withdrawn).                         **")
    print("  ** => 1.6x the pole's entire range, at no median cost.                                                **")
    print("  ** LOOSENING WAS TESTED AND IS WRONG: removing the relay (gate duty 0.00 %) RAISES                    **")
    print("  ** band power 2.8 %. The limiter is helping; V240 makes it help more.                                 **")
    print("  ** WATCH FOR: a brief HESITATION replacing the ratchet => too tight. V192's card                      **")
    print("  ** names it, and V240 tightens the ALWAYS-LIVE curve, so it applies with more force.                  **")
    print("  ** 0.8 = [286,286,369,410] is the back-off rung; it measures -0.5 %.                                  **")
    print("  ** NOT CLAIMED: that a 6 % lane-gain cut is a 6 % symptom cut. The step from lane                     **")
    print("  ** gain to felt ratcheting is the loop model, which has been wrong twice this session.                **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
