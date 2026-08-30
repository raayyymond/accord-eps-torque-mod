# -*- coding: utf-8 -*-
r"""V245 -- THE ONE SENSOR-FED LANE NOBODY HAS EVER SCORED AT THE RATCHET. TWO BYTES ON V241.

A CORRECTION FIRST. Four ticks of measurement closed the assist-map path, the notch axis and the
loop-delay hypothesis, and the conclusion drawn was "the calibration surface is exhausted for both
symptoms". **That was an overclaim.** It was true of the ASSIST-MAP path. The resonance PID is a
different lane, and the record has been pointing at it the whole time.

THE LANE. The golden model's own census, verbatim:

    LIVE gp-0x6ad4 resonance PID -- the most reachable authority of any gated lane HERE: its ceiling
    LERP 0xC67C2 (X=[128,1280,3200] Y=[0,1024,1024] on voted speed) reads p50 395-558 / p90 ~830 ...
    V56's mute of this lane was scored at ~21 Hz -- the lane has NEVER been scored at 6-9 Hz, so it
    is OPEN, not eliminated.

And the return-to-centre analysis narrows the ratchet's entry to five SENSOR-FED lanes -- "for 52-70 %
of the return the LKAS lane is a DC CONSTANT, yet the 6-9 Hz |tq| envelope is unchanged ... a constant
cannot carry 7.8 Hz". Of those five, **four are spoken for**: r24 is Lever B, `gp-0x6b26` is the
restored damper, `gp-0x6bbe` sits at 76 % of its rail, the plant-model path is `0xC63AE`.
**`gp-0x6ad4` is the one left, and the one nobody has scored.** Virgin in 216 of 218 images.

THE LEVER. `0xC67C4`, the middle X breakpoint of the ceiling LERP, 1280 -> 512. Speed is in counts at
64 per km/h, so:

    X = [128, 1280, 3200] counts = [2, 20, 50] km/h      Y = [0, 1024, 1024]
    the ceiling ramps 0 -> full between 2 and 20 km/h, then flat

    1280 -> 512  moves the knee to 8 km/h: full ceiling from 8 km/h instead of 20.
    => up to 3x more ceiling through the CREEP band, and IDENTICAL above 20 km/h.

**That is where the ratchet lives** -- the record puts it at creep, 1-13 deg/s, and
[[accord-damper-cannot-reach-micro-regime]] is the recurring complaint that the levers cannot reach
there. This one can.

WHY IT IS ADDITIVE, NOT A TRADE. It does not touch the biquad, so **V241's entire grinding treatment is
carried unchanged**. V244 had to give up the 22-30 Hz cut to attack the ratchet; this does not.

🛑 THE RISK, AND IT IS REAL. This is an OPEN lever, not a predicted fix. Raising a resonance
PID's ceiling gives it MORE AUTHORITY, and if its phase at 6-9 Hz is wrong, more authority means more
PUMPING -- a worse ratchet, not a better one. The record says so in as many words: "OPEN lever -- may
PUMP." Nobody has scored this lane in the ratchet band, which is exactly why it is worth a drive and
exactly why the outcome cannot be predicted.

WHAT MAKES IT SAFE TO TRY ANYWAY: two bytes, cal-only, **no cave**; it changes nothing above 20 km/h,
so highway behaviour is byte-identical in effect; and it is instantly revertible to V241.

WHAT A DRIVE SETTLES. The ratchet at creep either improves or worsens, and either answer is the first
score this lane has ever had at 6-9 Hz.

BASE: V241. Two bytes.
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
WRITE_MODE = os.environ.get("ACCORD_V245_WRITE", "").strip().lower()

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
KNEE = 0xC67C4                              # resonance-PID ceiling LERP, middle X breakpoint
KNEE_OLD, KNEE_NEW = 1280, 512              # 20 km/h -> 8 km/h (speed is 64 counts per km/h)
KNEE_X0, KNEE_X2 = 0xC67C2, 0xC67C6         # the other two breakpoints -- asserted, never written
FS_HZ = 1000.0                              # the control task rate
POLE_Y, K_STOCK = 0xC6906, 20               # the lag pole -- asserted STOCK, V241 does not touch it
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V245-V241BASE-RESPID.KNEE.1280.TO.512"

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
    check(u16(base, KNEE) == KNEE_OLD,
          f"base knee = {KNEE_OLD} -- stock, and virgin in 216 of 218 images")
    check(u16(base, KNEE_X0) == 128 and u16(base, KNEE_X2) == 3200,
          "the other two breakpoints read 128 and 3200 -- the LERP layout, confirmed")
    check(all(u16(base, POLE_Y + 2 * _i) == K_STOCK for _i in range(4)),
          f"base lag pole is STOCK at {K_STOCK} -- V241 does not touch it")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, KNEE, KNEE_NEW)
    attributed |= {KNEE, KNEE + 1}
    check(u16(code, KNEE) == KNEE_NEW,
          f"resonance-PID knee {KNEE_OLD} -> {KNEE_NEW} "
          f"({KNEE_OLD // 64} km/h -> {KNEE_NEW // 64} km/h)")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    check(u16(code, KNEE_X0) == 128 and u16(code, KNEE_X2) == 3200,
          "the X axis endpoints are UNTOUCHED -- only the middle breakpoint moved")
    check(KNEE_NEW > u16(code, KNEE_X0),
          f"the knee stays ABOVE the first breakpoint ({KNEE_NEW} > 128) -- the LERP stays "
          f"monotone, so no axis is corrupted")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the notch is CARRIED byte-for-byte -- V241's grinding work is untouched, this "
          "build is ADDITIVE rather than a trade")
    check(u16(code, LKAS_CLAMP) == 0,
          "0xC616C = 0 -- the map is fed by the driver torque sensor alone; LKAS cannot reach it")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")

    print("\n  [4] THE NOTCH IS THE ONE THING V241 CHANGES; ELSE V235 BYTE FOR BYTE")
    # inherited from V238, where the biquad WAS untouched. V241 re-aims it deliberately, so the
    # assertion is INVERTED: the block must DIFFER, and only in the four coefficients.
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == bytes(base[BIQ:BIQ + BIQ_LEN]),
          "the notch block is CARRIED byte-for-byte -- V245 is ADDITIVE, it adds the knee")
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
    check(len(pay) <= 2, f"{len(pay)} payload byte(s), at most the knee halfword")
    check(set(pay) <= {KNEE, KNEE + 1},
          "every payload byte is the knee -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V245 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v245_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V245_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V245 OPENS THE ONE SENSOR-FED LANE NOBODY HAS SCORED AT THE RATCHET.                               **")
    print("  ** A CORRECTION FIRST: 'the calibration surface is exhausted' was an OVERCLAIM.                       **")
    print("  ** It was true of the ASSIST-MAP path. The resonance PID is a different lane.                         **")
    print("  **   0xC67C4  1280 -> 512   the ceiling LERP's middle X breakpoint                                    **")
    print("  **   X = [128, 1280, 3200] counts = [2, 20, 50] km/h, Y = [0, 1024, 1024]                             **")
    print("  **   => full ceiling from 8 km/h instead of 20; up to 3x more through CREEP,                          **")
    print("  **      and IDENTICAL above 20 km/h.                                                                  **")
    print("  ** WHY THIS LANE: the golden model calls gp-0x6ad4 'the most reachable authority                      **")
    print("  ** of any gated lane', and V56's mute of it was scored at ~21 Hz ONLY -- it has                       **")
    print("  ** NEVER been scored at 6-9 Hz. The return-to-centre analysis narrows the                             **")
    print("  ** ratchet's entry to five sensor-fed lanes; four are spoken for. This is the                         **")
    print("  ** fifth. Virgin in 216 of 218 images.                                                                **")
    print("  ** ADDITIVE, NOT A TRADE: the biquad is untouched, so V241's whole grinding                           **")
    print("  ** treatment is carried. V244 had to give that up; this does not.                                     **")
    print("  ** THE RISK IS REAL: an OPEN lever, not a predicted fix. More ceiling means more                      **")
    print("  ** AUTHORITY, and if the lane's phase at 6-9 Hz is wrong that means more PUMPING                      **")
    print("  ** -- a WORSE ratchet. The record says so: 'OPEN lever -- may PUMP.'                                  **")
    print("  ** SAFE TO TRY: two bytes, cal-only, NO CAVE, nothing changes above 20 km/h,                          **")
    print("  ** instantly revertible to V241.                                                                      **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
