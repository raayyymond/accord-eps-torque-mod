# -*- coding: utf-8 -*-
r"""WITHDRAWN 2026-08-30 -- 0xC6384 IS MEASURED INERT at the ratchet (band ratio 1.0000; the cell
only reaches above 2844 torque counts, 1.65 % of engaged frames). DO NOT FLASH. Fly V238.

--- the original docstring follows, retained as the record ---

V236 -- THE RATCHET LEVER, PORTED ONTO THE CURRENT BUILD. TWO BYTES ON V235.

WHY THIS EXISTS. `HANDOFF-2026-08-29-the-ratchet-is-the-assist-map.md` worked out a gated ratchet lever
and built it as V168. **V168 never flew, and every build since reverted the cell.** Read from the
images:

    0xC6384 (base power-assist map slope cap):
      stock 2048 · car V122 2048 · V158 2048 · V222 2048 · V231 2048 · V235 2048
      V168  1536   <- the ONLY build ever to carry it

That is the same failure mode as Lever B earlier in this session: a lever found, gated, built, then
silently lost in the rebase chain. V168 is not a drop-in either -- it differs from V235 in 13 non-CRC
runs on an old base, with no probe and the Honda-era notch. So the lever is ported instead.

THE CASE, FROM THAT HANDOFF, WHICH DID THE WORK.

  * THE RATCHET IS IN TORQUE, NOT WHEEL RATE. Margin over each channel's own slope-matched null:
    tq 7.62, cs_tq 7.42, ws_fr 4.41, cs_rate 1.03 (CHANCE). Every 6-9 Hz endpoint the kit had used
    read the wrong channel.
  * ENGAGEMENT CREATES IT -- engaged clears its null 7/7, manual 0/7, speed-matched 19.9x
    [4.82, 35.64]. It is not a mechanical mode being amplified.
  * NOTHING HAS MOVED IT -- rho -0.14 (p 0.787) post-V102, frequency pinned at 8.64 Hz +- 7.4 % across
    V91->V122, while the GRIND falls rho -0.94 (p 0.005). The two symptoms DISSOCIATE.
  * `gp-0x6b86` is the largest torque-fed term, 5.8-7.8x the entire PID, and its map's slope cap pins
    the small-signal gain at exactly 2.000 -- the ceiling value of `s` in the loop census. The cap
    BINDS 3 of 9 knots over X 0-100.

  GATE 2, anchored on the MEASURED Q ratio rather than on the census phase:

      cap    s       |L|     |1-P.L|   Q ratio    vs stock
      2048   2.000   2.825   0.0700    14.29      stock -- what the car runs
      1536   1.500   2.325   0.2346     4.26      3.4x MORE DAMPED   <- V236
      1024   1.000   1.825   0.3992     2.50      5.7x

  MAGNITUDE passes. PHASE passes -- the term is a REAL GAIN, so lowering the cap scales |L| without
  rotating it: monotone, no reversal at any value. That is the property the notch work lacked.

  IT CANNOT TOUCH LKAS [EVIDENCE, re-verified on V235 here]: `0xC616C` = 0 on stock and all 161
  images, and a clamp with limit 0 annihilates its input, so gp-0x6b76 is in {0, 0x7FFF}, 0x7FFF
  exceeds FUN_0003405a's 20480 gate, and gp-0x6b4a is identically 0. The map is fed by the DRIVER
  TORQUE SENSOR alone.

WHY 1536 AND NOT SOME OTHER VALUE. Because 1536 is the value the GATE 2 work was done at and that V168
was cut at. Inventing an intermediate (1792 interpolates to about 2.2x) would be a NEW untested dose
with no gate behind it, and this kit's own lesson is "2x was the OPTIMUM, not a point on a ramp".

🛑 THE COST, AND IT COLLIDES WITH A STANDING OPERATOR DIRECTIVE. The cap pins the map's SMALL-SIGNAL
gain. Lowering it 2048 -> 1536 cuts the capped slope by 25 % over X 0-100, which is felt as MORE EFFORT
AT SMALL STEERING INPUTS. The operator's standing instruction is: "Increasing mass and friction should
not be our primary approach to resolving the ratcheting if it comes at the cost of max steering angular
velocity and acceleration. We want both." This lever does exactly what he asked not to do -- and it is
the ONLY gated ratchet lever the kit has ever produced. That tension is his to resolve, not mine to
hide, so it is on the drive card in his own words.

  ** It does NOT cost angular velocity or acceleration ** -- the cap is on the map's SLOPE in the
  small-signal region, not on any rate or authority limit, and 0 of 15 command/authority cells move.
  What it costs is small-input assist, i.e. effort, not speed.

THE ASSUMPTION THAT ONLY A DRIVE CAN CLOSE: P.L real-positive. The handoff says so plainly -- "closes
on the V168 drive itself; an unchanged excess falsifies it." V236 is that drive, on a current base.

WHAT V236 IS: V235 plus one cell. The notch at the net-damping optimum (grinding), the assist-map slope
cap lowered (ratchet), the biquad-state probe, and everything else at the car. It is the first build in
this arc aimed at BOTH symptoms with a gate behind each.
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
WRITE_MODE = os.environ.get("ACCORD_V236_WRITE", "").strip().lower()

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
SLOPE_CAP = 0xC6384                         # base power-assist map slope cap
CAP_OLD, CAP_NEW = 2048, 1536               # s 2.000 -> 1.500; Q ratio 14.29 -> 4.26
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V236-V235BASE-ASSISTMAP.SLOPECAP.1536.RATCHET"

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
    check(u16(base, SLOPE_CAP) == CAP_OLD,
          f"base carries 0x{SLOPE_CAP:05X} = {CAP_OLD} -- stock, and the value EVERY build except "
          f"V168 has carried")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, SLOPE_CAP, CAP_NEW)
    attributed |= {SLOPE_CAP, SLOPE_CAP + 1}
    check(u16(code, SLOPE_CAP) == CAP_NEW,
          f"0x{SLOPE_CAP:05X} {CAP_OLD} -> {CAP_NEW} (s 2.000 -> 1.500)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check(CAP_NEW == 1536,
          "1536 is the value GATE 2 was worked at and V168 was cut at -- Q ratio 14.29 -> 4.26, "
          "3.4x more damped. An intermediate would be a NEW untested dose with no gate behind it")
    check(u16(code, LKAS_CLAMP) == 0,
          "0xC616C = 0 -- a clamp with limit 0 annihilates its input, so gp-0x6b4a is identically "
          "0 and the map is fed by the DRIVER TORQUE SENSOR alone. LKAS cannot reach this cell")
    check(u16(code, RESID_SCALE) == RESID_SCALE_VAL,
          f"0xC63AE CARRIED at {RESID_SCALE_VAL} (Honda's)")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL} -- V88's bracketed optimum")
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
    _exp = sum(1 for k in range(2)
               if ((CAP_OLD >> (8 * k)) & 0xFF) != ((CAP_NEW >> (8 * k)) & 0xFF))
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(set(pay) <= {SLOPE_CAP, SLOPE_CAP + 1},
          "every payload byte is 0xC6384 -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V236 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v236_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V236_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V236 LOWERS THE ASSIST-MAP SLOPE CAP 0xC6384, 2048 -> 1536 (s 2.000 -> 1.500).                     **")
    print("  ** This is the ONE gated ratchet lever in the record, built as V168 and then silently                 **")
    print("  ** reverted by every build since. It caps the map's local interpolation slope in the                  **")
    print("  ** build loop of FUN_000352b4 (tp+0x7384, read as float * 1/1024).                                    **")
    print("  ** UNLIKE the lag pole (V238), this cell IS a real gain: it reduces delivered assist                  **")
    print("  ** wherever it binds, so it costs steering effort. That cost is the trade.                            **")
    print("  ** GATE 2 passes on magnitude AND phase; the term is a real gain, so the change is                    **")
    print("  ** monotone with no reversal at any value.                                                            **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
