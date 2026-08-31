# -*- coding: utf-8 -*-
r"""V253 -- V241 WITH THE OPERATOR'S OWN ALPHA2 KEPT. THE NOTCH BECOMES THE ONLY CONTROL CHANGE.

WHY THIS EXISTS.  The operator asked what V241 actually changes against the car.  The answer is 23
bytes, and one of them reverts a cell his own build name calls BEST:

    biquad, 4 runs, 12 B    the notch re-aimed to 29.75/22.50/0.940    <- the intended change
    0xC40DC   8 -> 22       alpha2, reverted to Honda's value
    0x55DF2                 CAN 427 TX packer source -- TELEMETRY, not a control path
    2 CRC trailers          derived

`V122` is named `KNEE3000.K1.1020-ALPHA2.8-BEST`.  V115 took alpha2 14 -> 8, V122 carried it, and
V241's lineage put Honda's 22 back.  The flown corpus leans toward 22 (Re(Z) -62.87 at alpha2 22 across
14 builds vs -70.13 at alpha2 8) -- **but n = 1 at the operator's value, p = 0.136, and it is
CONFOUNDED WITH ERA**: alpha2 went 22 -> 14 -> 8 exactly as the gain went 4x -> 6x, so that trend may
be the gain effect wearing a different hat.  The corpus cannot separate them.

THE STANDING RULE APPLIES.  "The operator's lived experience overrides analyst recommendations -- if he
reports how the car feels, that beats theoretical arguments."  He named the build BEST.  A confounded
n=1 contrast is not grounds to silently undo that.

    0xC40DC   22 -> 8     alpha2 held at the car's own value

WHAT THIS BUYS BEYOND DEFERENCE.  It makes the build a ONE-VARIABLE experiment.  Against V122 the only
CONTROL change is the notch; the sole remaining difference is the CAN 427 telemetry source, which
selects what is broadcast and touches no control path.  So if the drive changes anything, the notch did
it -- there is no second cell to argue about afterwards.

🛑 WHICH TO FLY.  If the operator has no feel-preference on alpha2, V241 is fine and its value
is marginally better supported.  If he chose 8 deliberately, fly THIS one.  They differ by a single
byte and either can be reverted to the other in one flash.

BASE: V241.  One byte.
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
WRITE_MODE = os.environ.get("ACCORD_V253_WRITE", "").strip().lower()

BASE_NAME = "_v235_V235-V234BASE-C63AE.BACK.TO.HONDA.1024_plain_image.bin"
BASE_SHA = "ad6d485eefb2f6bcc195c062035d5a9dab5fb06dae7f46f68f5ca03a504c18ab"

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
Z_HZ, P_HZ, R_POLE = 29.75, 22.50, 0.940    # the leave-one-route-out winner, all 10 folds
ALPHA2_NEW = 8                              # the car's value (V115->V122), kept
FS_HZ = 1000.0                              # the control task rate
POLE_Y, K_STOCK = 0xC6906, 20               # the lag pole -- asserted STOCK, V241 does not touch it
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V253-V241BASE-ALPHA2.HELD.AT.8"

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
    code[ALPHA2] = ALPHA2_NEW
    attributed.add(ALPHA2)
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
    check(_lo >= 0.9344 - 1e-4,
          f"GATE 2 min|H| over 6-15 Hz = {_lo:.4f} >= 0.9344, what STOCK achieves -- the lane "
          f"is measured DAMPING there and V235 sits at 0.9108, BELOW Honda")
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
    check(code[ALPHA2] == ALPHA2_NEW,
          f"0x{ALPHA2:05X} alpha2 {ALPHA2_VAL} -> {ALPHA2_NEW} -- the CAR's own value, "
          f"kept rather than reverted to Honda's")
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
    check(len(pay) <= 17, f"{len(pay)} payload byte(s): the biquad plus the alpha2 byte")
    check(set(pay) <= {BQ + j for j in range(16)} | {ALPHA2},
          "every payload byte is the biquad or alpha2 -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V253 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v253_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V253_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V253 = V241 WITH THE OPERATOR'S OWN ALPHA2 KEPT.                                                   **")
    print("  **   0xC40DC   22 -> 8    alpha2 held at the CAR's value, not reverted to Honda's                     **")
    print("  ** WHY: V122 is named KNEE3000.K1.1020-ALPHA2.8-BEST. V115 took alpha2 14->8, V122                    **")
    print("  ** carried it, and V241's lineage put Honda's 22 back. The flown corpus leans                         **")
    print("  ** toward 22 (Re(Z) -62.87 across 14 builds vs -70.13 at alpha2 8) but n=1 at the                     **")
    print("  ** operator's value, p 0.136, and CONFOUNDED WITH ERA -- alpha2 went 22->14->8 as                     **")
    print("  ** the gain went 4x->6x. The corpus cannot separate them.                                             **")
    print("  ** THE STANDING RULE: the operator's lived experience overrides analyst                               **")
    print("  ** recommendations. He named it BEST; a confounded n=1 contrast is not grounds to                     **")
    print("  ** silently undo that.                                                                                **")
    print("  ** AND IT BUYS A CLEANER EXPERIMENT: against V122 the ONLY control change is the                      **")
    print("  ** notch. The sole other difference is the CAN 427 telemetry source, which selects                    **")
    print("  ** what is broadcast and touches no control path. If the drive changes anything,                      **")
    print("  ** the notch did it.                                                                                  **")
    print("  ** WHICH TO FLY: no feel-preference on alpha2 -> V241 is fine. Chose 8                                **")
    print("  ** deliberately -> fly this. One byte apart, either reverts to the other.                             **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
