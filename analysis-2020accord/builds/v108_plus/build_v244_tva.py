# -*- coding: utf-8 -*-
r"""V244 -- THE NOTCH ON THE RATCHET. THE EXPERIMENT THAT SETTLES THE RULE, IN TWELVE BYTES.

WHAT THIS IS. V241 aims the biquad at 22-30 Hz, the largest engagement-created band in CHASSIS MOTION.
But the notch acts on a TORQUE lane, and in torque the picture is different: engagement's dominant
effect is the RATCHET band, and 6-10 Hz carries 68.6 % of all torque excess over 3-45 Hz. Priced
against that weight:

    a LOCAL non-amplifying notch at 7.75 / 7.50 / 0.990 removes  66.2 %  of the torque excess
    V241, aimed at 22-30 Hz, removes                             21.8 %

**Three times the current build, on the symptom nothing in thirty-plus builds has ever moved.**

WHY IT HAS NOT BEEN BUILT BEFORE. One rule forbids it, verbatim: "place a notch only where the lane
PUMPS. Never notch 6-15 Hz on this lane." It condemned V238 and V240. That rule now has two
independent defects:
  1. it was measured on `mag427`, and `FUN_00055d80` clamps that field to [0, 0x3ff] -- the phase of a
     rectified channel carries no reliable sign;
  2. it pooled ra4/ra5/ra6, but V104 AMPLIFIES 1.79x at 6-15 Hz while V105/V106 cut 4 % -- a 1.87x
     difference in the lane's own filter, in the exact band the table judges.

**Neither refutes it.** The lane may still damp there. Settling it by MEASUREMENT needs the lane's SIGN
on CAN, which needs a cave or a clamp change -- this kit's only bricking class.

SO SETTLE IT BY DRIVING IT INSTEAD. This is a 12-byte CAL edit, the same class as V241 -- no cave, no
bricking risk -- and its two outcomes are opposite and unmistakable:

    the ratchet IMPROVES  =>  the rule is WRONG, and this is the fix the arc has been looking for
    the ratchet WORSENS   =>  the rule is RIGHT, definitively, and the band closes for good

Either way ONE short symptomatic drive answers a question no further analysis can, which is exactly
what the kit's own build law asks for.

THE GEOMETRY, gate-checked from the written bytes:

    zero 7.75 Hz   pole 7.50 Hz   r 0.990
    GATE 1  max|H| = 0.9997 over 0-50 Hz  -- can only REMOVE loop gain, never add
      6-10  the ratchet   mean |H| 0.4872   min 0.0000   <- a true null at 7.75 Hz
     10-15  mid           mean |H| 0.8768   min 0.7498   <- where the disputed rule bites hardest
     15-22  grind         mean |H| 0.9522               <- barely touched
     22-30  V241's band   mean |H| 0.9680               <- barely touched
     DC                        |H| 0.9997               <- static assist UNCHANGED
    locality: min |H| outside 5.5-10.5 Hz = 0.8189      -- a LOCAL notch, not a low-pass

THE RISK, STATED PLAINLY. If the rule is right, this REMOVES damping at 6-15 Hz and the ratchet gets
WORSE. The collateral is concentrated at 10-15 Hz (min 0.7498), which is where the disputed table
claims the strongest damping (cos -0.989 at 9-12 Hz). **This build is an EXPERIMENT, not a predicted
fix.** It is safe to try -- cal-only, non-amplifying, instantly revertible -- but it may make the
symptom worse for the length of one drive.

WHAT IT GIVES UP. The 22-30 Hz grinding cut. There is ONE biquad; it cannot do both bands. V241 remains
the grinding build and V244 is its opposite number -- 12 bytes apart, so whichever is driven second
isolates the choice exactly.

BASE: V241. Only the four float coefficients differ.
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
WRITE_MODE = os.environ.get("ACCORD_V244_WRITE", "").strip().lower()

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
Z_HZ, P_HZ, R_POLE = 7.75, 7.50, 0.990      # the ratchet notch: 66.2 % of the torque excess
FS_HZ = 1000.0                              # the control task rate
POLE_Y, K_STOCK = 0xC6906, 20               # the lag pole -- asserted STOCK, V241 does not touch it
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V244-V241BASE-NOTCH.ON.THE.RATCHET.7.75"

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
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    # BY FORMULA, never by decimal -- a 6-dp decimal does not round-trip a float32
    _wz = 2 * math.pi * Z_HZ / FS_HZ
    _wp = 2 * math.pi * P_HZ / FS_HZ
    _b1 = -2 * math.cos(_wz)
    _a1 = -2 * R_POLE * math.cos(_wp)
    _a2 = R_POLE ** 2
    _c4 = abs((1 + _a1 + _a2) / (1 + _b1 + 1))
    struct.pack_into("<ffff", code, BQ, _a1, _a2, _b1, _c4)
    attributed |= {BQ + _j for _j in range(16)}
    check(struct.unpack_from("<ffff", code, BQ) != struct.unpack_from("<ffff", base, BQ),
          f"biquad re-aimed: zero {Z_HZ} Hz, pole {P_HZ} Hz, r {R_POLE}")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    # the two gates, both the record's own -- recomputed here from the WRITTEN bytes
    _a1w, _a2w, _b1w, _c4w = struct.unpack_from("<ffff", code, BQ)
    _g = [f / 4.0 for f in range(2, 200)]
    _H = []
    for _f in _g:
        _ang = -2 * math.pi * _f / FS_HZ
        _z = complex(math.cos(_ang), math.sin(_ang))
        _H.append(abs(_c4w * (1 + _b1w * _z + _z * _z) / (1 + _a1w * _z + _a2w * _z * _z)))
    _mx = max(_H)
    _lo = min(h for f, h in zip(_g, _H) if 6.0 <= f <= 15.0)
    check(_mx <= 1.0 + 1e-6,
          f"GATE 1 max|H| = {_mx:.4f} <= 1.0000 -- the lineage bar (V194-V198 were PULLED "
          f"for 1.3533-1.7177; a 1.0020 candidate was DELETED)")
    # V241 asserted min|H| over 6-15 Hz >= stock. V244 DELIBERATELY VIOLATES THAT -- cutting
    # that band IS the experiment. The assertion is inverted so the intent is explicit, and a
    # build that accidentally left the band alone FAILS rather than passing silently.
    check(_lo < 0.9344,
          f"min|H| over 6-15 Hz = {_lo:.4f} < stock 0.9344 -- this build CUTS the disputed "
          f"band on purpose; that is the whole experiment")
    _loc = min(h for f, h in zip(_g, _H) if f < 5.5 or f > 10.5)
    check(_loc >= 0.75,
          f"LOCALITY min|H| outside 5.5-10.5 Hz = {_loc:.4f} >= 0.75 -- a local NOTCH, not a "
          f"low-pass (an unconstrained optimiser returns pole 4.00 Hz and guts the lane)")
    check(all(u16(code, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          "the lag pole is left STOCK -- V241 changes the notch and nothing else")
    check(u16(code, LKAS_CLAMP) == 0,
          "0xC616C = 0 -- the map is fed by the driver torque sensor alone; LKAS cannot reach it")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")

    print("\n  [4] THE NOTCH IS THE ONE THING V241 CHANGES; ELSE V235 BYTE FOR BYTE")
    # inherited from V238, where the biquad WAS untouched. V241 re-aims it deliberately, so the
    # assertion is INVERTED: the block must DIFFER, and only in the four coefficients.
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) != bytes(base[BIQ:BIQ + BIQ_LEN]),
          "the biquad IS re-aimed -- that is the whole build")
    check(all(code[_i] == base[_i] for _i in range(BIQ + 16, BIQ + BIQ_LEN)),
          "nothing past the four coefficients moved inside the biquad block")
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
    check(len(pay) <= 16, f"{len(pay)} payload byte(s), at most the 16 biquad bytes")
    check(set(pay) <= {BQ + j for j in range(16)},
          "every payload byte is inside the biquad block -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V244 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v244_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V244_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V244 PUTS THE NOTCH ON THE RATCHET. Twelve bytes on V241.                                          **")
    print("  **   zero 7.75 Hz  pole 7.50 Hz  r 0.990   (V241: 29.75 / 22.50 / 0.940)                              **")
    print("  ** WHY: the notch acts on a TORQUE lane, and in torque 6-10 Hz carries 68.6 % of                      **")
    print("  ** all engagement excess. A local non-amplifying notch there removes 66.2 % of it;                    **")
    print("  ** V241, aimed at 22-30 Hz, removes 21.8 %. Three times, on the symptom nothing                       **")
    print("  ** in thirty-plus builds has ever moved.                                                              **")
    print("  ** ONE RULE FORBADE IT -- 'never notch 6-15 Hz on this lane'. That rule now has TWO                   **")
    print("  ** independent defects: measured on mag427, which FUN_00055d80 CLAMPS to [0,0x3ff];                   **")
    print("  ** and pooled across ra4/ra5/ra6 where V104 AMPLIFIES 1.79x at 6-15 Hz while                          **")
    print("  ** V105/V106 cut 4 %. NEITHER REFUTES IT. Settling it by measurement needs a cave.                    **")
    print("  ** SO SETTLE IT BY DRIVING IT. Cal-only, 12 bytes, no cave, instantly revertible:                     **")
    print("  **   ratchet IMPROVES => the rule is WRONG and this is the fix                                        **")
    print("  **   ratchet WORSENS  => the rule is RIGHT and the band closes for good                               **")
    print("  ** GATE 1 max|H| 0.9997 -- can only REMOVE loop gain. DC 0.9997 -- static assist                      **")
    print("  ** unchanged. Locality min 0.8189 outside 5.5-10.5 Hz -- a NOTCH, not a low-pass.                     **")
    print("  ** THE RISK: if the rule is right this REMOVES damping and the ratchet gets WORSE.                    **")
    print("  ** Collateral is concentrated at 10-15 Hz (min 0.7498). AN EXPERIMENT, NOT A FIX.                     **")
    print("  ** GIVES UP the 22-30 Hz grinding cut -- one biquad cannot do both bands. V241 is                     **")
    print("  ** the grinding build; V244 is its opposite number, 12 bytes apart.                                   **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
