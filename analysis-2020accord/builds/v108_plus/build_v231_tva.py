# -*- coding: utf-8 -*-
r"""V231 -- V229 PLUS THE FIRST INSTRUMENT EVER PUT ON THE NOTCH. THREE BYTES.

WHY. After 56 builds that moved the notch, **no build has ever measured whether it runs.** V229 carries
the notch revert with no instrument on its own lever, so a "no change" report from it would be
uninterpretable -- exactly the failure the kit's design law names: *"Before cutting, write the sentence
a null will license. If the honest answer is 'we would not be able to tell,' the build is not ready."*

I tried to settle liveness from the flown corpus and could not. The biquad was DORMANT before V103 and
ARMED from V103 on, and five routes carry audio across that boundary (dormant r95/V101, r96/V102; armed
r9e/V103, ra4/V104, r24/V122). Difference-in-differences on the engaged/not audio ratio, speed and gear
matched:

    band        ARMED e/n   DORMANT e/n   armed/dorm
    6-9            1.36x        4.21x        0.32x
    15-22          1.15x        2.63x        0.44x   <- CONTROL, should be ~1.0
    50-60          1.64x        1.93x        0.85x   <- the notch band
    85-99          1.20x        1.02x        1.18x   <- CONTROL

**The control bands move MORE than the test band, and the armed arm spans 6x within itself
(1.64 / 0.73 / 4.38).** That is not a null on the biquad, it is a design that cannot see it -- cabin
audio at 55 Hz is dominated by road and engine, so cutting ONE assist lane 159x barely moves it.

THE PROBE. The filter's two state variables are floats at `gp-0x3814` and `gp-0x3818`, and
`docs/BUILD-LINEAGE.md` established for V103's GATE 1 that both **boot to exactly 0.0f** from the
`.data` initialiser at flash `0x89898`. So:

    if the arming gate never fires on the car, the state stays 0.0f FOREVER.

Tapping it gives a null that licenses one clean sentence: **"the biquad's state was identically zero
across N engaged frames, therefore the filter never executed."** Nonzero means it ran, and the
magnitude distribution then reports how hard it is working.

THE ENCODING, verified in the instruction stream rather than assumed:

    0x55DF0   ld.h  -0x6c18, gp, r6     bytes 2437e893   <- disp16 halfword lives at 0x55DF2
    0x55E10   sar   0x3, r6             bytes a332       <- shift byte is 0xA0 | N

  * `ld.h` is a SIGNED halfword load, and hw2 = 65536 - offset (checked against the stock -0x6C18:
    65536 - 0x6C18 = 0x93E8, which is the halfword actually present).
  * The float at `gp-0x3818` occupies gp-0x3818..gp-0x3815; its HIGH half -- sign + exponent + 7
    mantissa bits -- is at **`gp-0x3816`**, so hw2 = 65536 - 0x3816 = **0xC7EA**. Even-aligned, and
    -0x3816 is inside disp16 range.
  * `sar 3` is kept (byte 0xA3). Any nonzero float has |high half| >= 8 unless it is denormal-small
    (< 2^-120), so `sar 3` cannot turn a real nonzero state into a wire zero. It also keeps the value
    inside the wire field, which `sar 0` would not.

WHAT THIS COSTS. The 427 tap is a shared telemetry channel: V231 gives up whatever V229 was reporting
there (`gp-0x6b4e`). That is a pure instrument trade, no control change.

EVERYTHING ELSE IS V229, BYTE FOR BYTE -- Honda's 55 Hz notch, Lever B 13107, alpha2 22, 0xC63AE 512,
the 0xC407E interlock, and the 164-byte cave BYTE-IDENTICAL.
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
WRITE_MODE = os.environ.get("ACCORD_V231_WRITE", "").strip().lower()

BASE_NAME = "_v229_V229-V228BASE-HONDA.55HZ.NOTCH.RESTORED_plain_image.bin"
BASE_SHA = "078da4b1f22903a5364b54b0035790f0fac6453a4717e881290eefb15bc14a42"

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
PROBE_HW2, SHIFT_OFF = 0x55DF2, 0x55E10
HW2_OLD, HW2_NEW = 0x94B2, 0xC7EA          # gp-0x6b4e -> gp-0x3816 (high half of the z1 float)
SAR_OLD, SAR_NEW = 0xA5, 0xA3              # sar 5 -> sar 3

# carried levers -- asserted, never re-set
LEVER_B, LEVER_B_VAL = 0xC6446, 13107
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
TAG = "V231-V229BASE-PROBE.BIQUAD.STATE"

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


def resp(b, fr, fs=1000.0):
    """|H| and phase from the ENCODED float32 in the image."""
    import cmath
    import math
    z = cmath.exp(2j * math.pi * fr / fs)
    h = (f32(b, BIQ + 12) * (z * z + f32(b, BIQ + 8) * z + 1.0)
         / (z * z + f32(b, BIQ) * z + f32(b, BIQ + 4)))
    return abs(h), math.degrees(cmath.phase(h))


def build():
    print("=" * 102)
    print("  V231 -- V229 + THE FIRST INSTRUMENT EVER PUT ON THE NOTCH.  THREE BYTES.")
    print("=" * 102)

    print("\n  [1] BASE = V229")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V229 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(bytes(base[BIQ:BIQ + BIQ_LEN]) == HONDA_BIQ, "base carries Honda's 55 Hz biquad")
    check(u16(base, PROBE_HW2) == HW2_OLD, f"base 427 tap = 0x{HW2_OLD:04X} (gp-0x6b4e)")
    check(base[SHIFT_OFF] == SAR_OLD, f"base shift = 0x{SAR_OLD:02X} (sar 5)")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE PROBE REPOINT -- three bytes")
    struct.pack_into("<H", code, PROBE_HW2, HW2_NEW)
    code[SHIFT_OFF] = SAR_NEW
    attributed |= {PROBE_HW2, PROBE_HW2 + 1, SHIFT_OFF}
    check(u16(code, PROBE_HW2) == HW2_NEW, f"427 tap -> 0x{HW2_NEW:04X}")
    check(code[SHIFT_OFF] == SAR_NEW, f"shift -> 0x{SAR_NEW:02X} (sar 3)")

    print("\n  [3] THE TARGET ARITHMETIC, DERIVED NOT ASSUMED")
    off = 0x10000 - HW2_NEW
    check(off == 0x3816, f"hw2 0x{HW2_NEW:04X} decodes to gp-0x{off:04X}")
    check(off % 2 == 0, "even-aligned, so ld.h is legal")
    check(-off >= -32768, "displacement inside disp16 range")
    # the float state lives at gp-0x3818; its HIGH half is 2 bytes further on in memory
    check(0x3818 - 2 == off, "gp-0x3816 IS the high half of the float at gp-0x3818 (LE)")
    check(SAR_NEW == 0xA0 | 3, "shift byte follows the 0xA0|N form read out of 0x55E10")

    print("\n  [4] EVERY LEVER IS UNTOUCHED -- this build changes ONLY the instrument")
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == HONDA_BIQ, "Honda's 55 Hz biquad still in place")
    check(u16(code, LEVER_B) == LEVER_B_VAL, f"Lever B 0x{LEVER_B:05X} = {LEVER_B_VAL}")
    check(code[ALPHA2] == ALPHA2_VAL, f"0x{ALPHA2:05X} alpha2 = {ALPHA2_VAL}")
    check(u16(code, RESID_SCALE) == RESID_VAL, f"0x{RESID_SCALE:05X} = {RESID_VAL}")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- no cave change, not the bricking class")

    print("\n  [5] THE ARMING MUST STILL BE INTACT -- a probe on a dormant filter reads nothing")
    for a, want in sorted(ARM_SITES.items()):
        got = bytes(code[a:a + len(bytes.fromhex(want))]).hex()
        check(got == want, f"0x{a:05X} = {want}")
    check(code[ARM_CAL] == 1, f"0x{ARM_CAL:05X} = 1 (biquad enabled)")

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

    print("\n  [7] FULL BYTE DIFF vs V229")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    _exp = sum(1 for k in range(2)
               if ((HW2_OLD >> (8 * k)) & 0xFF) != ((HW2_NEW >> (8 * k)) & 0xFF))
    _exp += 1 if SAR_OLD != SAR_NEW else 0
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(set(pay) <= {PROBE_HW2, PROBE_HW2 + 1, SHIFT_OFF},
          "every payload byte is in the telemetry tap -- no control byte moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V231 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v231_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V231_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V231 = V229 + the FIRST INSTRUMENT ever put on the notch. THREE bytes, all in the  **")
    print("  ** telemetry tap. NO control byte moves, so it is V229 to drive and V229 to score.    **")
    print("  ** After 56 builds that MOVED the notch, none ever measured whether it RUNS. The      **")
    print("  ** filter's state floats boot to exactly 0.0f, so if the arming gate never fires on   **")
    print("  ** the car the state stays zero forever. 427 now taps gp-0x3816 -- the HIGH half of   **")
    print("  ** the z1 float at gp-0x3818 -- so the null licenses ONE clean sentence:              **")
    print("  **   'the state was identically zero across N engaged frames => it never executed'.   **")
    print("  ** Nonzero means it ran, and the distribution says how hard it is working.            **")
    print("  ** I tried to settle this from the flown corpus first and could NOT: dormant-vs-armed **")
    print("  ** audio (r95,r96 vs r9e,ra4,r24) gives 0.85x at 50-60 Hz but 0.44x and 1.18x in the  **")
    print("  ** CONTROL bands, with the armed arm spanning 1.64/0.73/4.38 within itself. Cabin     **")
    print("  ** audio at 55 Hz is road and engine; one assist lane cut 159x barely moves it.       **")
    print("  ** ENCODING VERIFIED IN THE INSTRUCTION STREAM, not assumed: 0x55DF0 is               **")
    print("  ** 'ld.h -0x6c18,gp,r6' (2437e893) so hw2 = 65536-offset and the load is SIGNED;      **")
    print("  ** 0x55E10 is 'sar 0x3,r6' (a332) so the shift byte is 0xA0|N. sar 3 is kept because  **")
    print("  ** any real nonzero float has |high half| >= 8, so it cannot alias a live state to 0. **")
    print("  ** COST: the 427 channel is shared, so V231 gives up V229's gp-0x6b4e reading.        **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
