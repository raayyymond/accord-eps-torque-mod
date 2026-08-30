# -*- coding: utf-8 -*-
r"""V238 -- THE SAME POLE AS V237, THE OTHER WAY. V237 WAS BACKWARDS.

WHAT V237 GOT WRONG. V237 raised `0xC6906` 20 -> 80 on the argument that the lane is a direct path plus
a parallel lagged branch, so raising the pole "damps". Reading the tail of `FUN_000352b4` properly shows
the lane is not an additive branch at all -- it is a BLEND between two versions of the same assist map:

    gp-0x37e8   Y array, capped by 0xC6384          -> table1 -> gp-0x6b7a     (V236's cell)
    gp-0x3810   Y array, ALSO slewed by gp-0x69a0   -> table2 -> uVar25        (V192's cell)

    bVar3  = (table2 < |table1|)                    the gate: where the SLEW limiter bit
    iVar33 = (table1 - table2) * bVar3              exactly what the slew limiter cut
    iVar34 = table2*bVar3 + table1*!bVar3           the direct path is the LIMITED value
    out    = iVar34 + EMA_k(iVar33)                 the cut, added back through the lag

    =>  out(w) = table2 + H_k(w) * (table1 - table2)
              = table1 at DC (H=1)  ...  table2 at high frequency (H=0)

**k does not set a branch gain. It sets HOW MUCH OF THE SLEW LIMITER'S TIGHTENING SURVIVES TO THE
OUTPUT at a given frequency.** Raising k restores MORE of the cut at the ratchet frequency, which RAISES
the lane's gain there. Every torque-fed lane is a denominator term in `Z = (Z0 + P.F)/(1 - P.L)`, so a
higher gain is MORE positive feedback and LESS damping. **V237 pushed the ratchet the wrong way.**

WHY THIS DIRECTION IS HONDA'S OWN. `gp-0x69a0` is the slew limit `FUN_00035b20` switches on the
hard-reversal counter -- Honda's own oscillation response is to TIGHTEN it (V192 applied Honda's own
0.600 ratio once more). k is the valve on how much of that tightening reaches the output. **Lowering k
opens Honda's own anti-oscillation mechanism further.** Same logic as V192, a different cell.

THE DOSE. The reader clamps k to [2, 204], so 2 is the firmware's own floor.

    k    a=k/2048   corner    |H| at 7.79 Hz   arg      tau
    20   0.009766   1.554 Hz     0.1966      -77.26   0.102 s   <- ENGAGED today
     8   0.003906   0.622 Hz     0.0797      -84.03   0.256 s   <- THIS BUILD
     2   0.000977   0.155 Hz     0.0200      -87.45   1.024 s   <- the floor

**8, not the floor.** At the floor tau is ~1.0 s: the difference the slew limiter cut takes a full
second to be restored, and V192's card already names the failure mode -- "watch for a brief HESITATION
replacing the ratchet => too tight". A one-second soggy restore is a real drivability risk. k=8 cuts the
restore at the ratchet 2.47x (0.1966 -> 0.0797) while keeping tau at a quarter second, and leaves 2 as a
second rung.

WHAT IT DOES NOT DO. DC gain of the EMA is exactly 1 at every k, so static assist is unchanged at any
steering input -- this build does NOT carry V236's effort cost. It also cannot touch LKAS: the map is
fed by the driver torque sensor alone (`0xC616C` = 0 on all 161 images).

WHAT IS ASSUMED. The DIRECTION is now structural -- it follows from the blend, not from a linearisation.
What is NOT established is the SIZE, because that depends on how large `table1 - table2` is in normal
driving, i.e. how hard the slew limiter bites. That is the clip duty, and it has not been measured on a
route. So: direction well-founded, magnitude unknown.

RETRACTED WITH V237: its "manual arm runs k=41 and has no ratchet" consistency check. Under the blend
that check points the OTHER way (manual restores MORE, not less), and either reading is confounded --
engagement adds the whole LKAS path, and the archive already found the pole difference far too small to
explain the engaged/manual contrast. **The manual arm is not evidence for direction in either sense.**

BASE: V235, the no-added-effort build. V238 = V235 + these four halfwords.
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
WRITE_MODE = os.environ.get("ACCORD_V238_WRITE", "").strip().lower()

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
POLE_Y = 0xC6906                            # engaged lag pole, LERP Y[0..3]
POLE_X = 0xC68FE                            # its X axis -- asserted, never written
K_OLD, K_NEW = 20, 8                        # corner 1.554 Hz -> 0.622 Hz; |H| at 7.79 Hz 0.1966 -> 0.0797
K_CLAMP_MIN = 2                             # the firmware's own floor, from the reader
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V238-V235BASE-ENGAGED.LAGPOLE.8.TIGHTEN"

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
    for _i in range(4):
        check(u16(base, POLE_Y + 2 * _i) == K_OLD,
              f"base Y[{_i}] = {K_OLD} (the engaged pole, flat)")
    check([u16(base, POLE_X + 2 * _i) for _i in range(4)] == [0, 9830, 26214, 32768],
          "the X axis reads [0, 9830, 26214, 32768] -- the layout from the LERP reader, confirmed")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    for _i in range(4):
        struct.pack_into("<H", code, POLE_Y + 2 * _i, K_NEW)
        attributed |= {POLE_Y + 2 * _i, POLE_Y + 2 * _i + 1}
    check(all(u16(code, POLE_Y + 2 * _i) == K_NEW for _i in range(4)),
          f"engaged pole Y[0..3] {K_OLD} -> {K_NEW} (corner 1.554 Hz -> 0.622 Hz)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check(K_NEW >= K_CLAMP_MIN,
          f"{K_NEW} is inside the firmware's OWN floor of {K_CLAMP_MIN} -- the reader does "
          f"max(2, min(k, 204)), so this cannot go below what Honda's code already permits")
    check(K_NEW < K_OLD,
          "the direction is LOWER k: out = table2 + H_k*(table1 - table2), so a SMALLER H at "
          "7.79 Hz leaves MORE of the slew limiter's tightening in force -- less lane gain, "
          "less positive feedback, more damping. V237 raised it and was backwards.")
    check(u16(code, SLOPE_CAP) == CAP_STOCK,
          f"0x{SLOPE_CAP:05X} left at {CAP_STOCK} -- this build does NOT carry V236's effort cost")
    check([u16(code, POLE_X + 2 * _i) for _i in range(4)] == [0, 9830, 26214, 32768],
          "the X axis is UNTOUCHED -- only the four Y halfwords moved")
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
    _exp = 4 * sum(1 for k in range(2)
                   if ((K_OLD >> (8 * k)) & 0xFF) != ((K_NEW >> (8 * k)) & 0xFF))
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(set(pay) <= {POLE_Y + j for j in range(8)},
          "every payload byte is inside the pole Y block -- the X axis did not move")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V238 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v238_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V238_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V238 CORRECTS V237, WHICH WAS BACKWARDS. Same cell, opposite direction.                            **")
    print("  ** Reading the tail of FUN_000352b4 properly: the lane is not a direct path plus a                    **")
    print("  ** parallel lagged branch. It is a BLEND of two versions of the same assist map --                    **")
    print("  **     out(w) = table2 + H_k(w) * (table1 - table2)                                                   **")
    print("  ** table1 = the map capped by 0xC6384 (V236's cell); table2 = the same map ALSO slewed                **")
    print("  ** by gp-0x69a0 (V192's cell). k is the valve on how much of the SLEW LIMITER'S                       **")
    print("  ** TIGHTENING survives to the output at a given frequency.                                            **")
    print("  ** => RAISING k restores more of the cut at 7.79 Hz, RAISING the lane's gain there.                   **")
    print("  **    Every torque-fed lane is a denominator term, so that is MORE positive feedback                  **")
    print("  **    and LESS damping. V237 pushed the ratchet the wrong way.                                        **")
    print("  ** LOWERING k is Honda's own direction: FUN_00035b20 TIGHTENS gp-0x69a0 on the                        **")
    print("  ** hard-reversal counter, and V192 applied Honda's own 0.600 ratio once more.                         **")
    print("  ** DOSE: 8, not the floor of 2. At the floor tau is ~1.0 s and V192's card already                    **")
    print("  ** names the failure mode -- 'watch for a brief HESITATION replacing the ratchet'.                    **")
    print("  ** k=8 cuts the restore 2.47x (|H| 0.1966 -> 0.0797) at tau 0.256 s.                                  **")
    print("  ** NOT CLAIMED: the SIZE. That depends on how hard the slew limiter bites (the clip                   **")
    print("  ** duty), which has not been measured on a route. Direction structural, magnitude open.               **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
