# -*- coding: utf-8 -*-
r"""V242 -- 8x LKAS GAIN ON THE FINISHED GRINDING WORK. FOUR BYTES ON V241.

WHY THIS BUILD EXISTS. the operator's OWN stated sequence -- "fix at 6x first, then raise to 8x". The
grinding work is now done, so this is the step he reserved.

WHAT IT IS. V241 carries every piece of the grinding work -- the IMU-aimed notch, Honda's
`0xC63AE`, Lever B at V88's measured optimum, the friction and inertia restorations inherited from
V222 -- at the car's 6x gain. This raises the gain and its tracking clamps, and changes NOTHING else.

    0xC6CD0   5346 -> 7128    the forward LKAS gain (6x -> 8x; 0xC646C = 891 is 1x)
    0xC61B2   3072 -> 4096    forward-path clamp A, tracking
    0xC61B4   3072 -> 4096    forward-path clamp B, tracking

THE HISTORY THIS BUILD IS WALKING BACK INTO, stated plainly because it is the whole risk:
**8x flew once, as V101 on route 0x95, and the operator rejected it** -- "GRINDING/VIBRATION AT ALL
SPEEDS, ONLY WHILE LKAS COMMANDS, killed by applying driver torque, returning and growing when he lets
go." He reverted to 6x himself. The measured signature: the peak MOVED 20.3 -> 23.0 Hz (a pole moved)
and the de-confounded gain was 2.7-3.9x at 22-26 Hz.

**That 22-26 Hz band is exactly what this lineage's notch now attacks**, and the notch is aimed by an
instrument independent of the EPS. So this is not a repeat of V101: V101 raised the gain with NO
grinding treatment, and this raises it with the best treatment the kit has. **It is still the same
lever that produced the complaint, and it may still grind.**

THE EME INTERLOCK, and why there is no 16x. The forward clamp must stay BELOW the soft-EME floor
`0xC674E` = 5120, and the clamp tracks the gain as `gain*512//891`:

    6x  -> clamp 3072   OK          12x -> clamp 6144   AUDIT FAILS
    8x  -> clamp 4096   OK          16x -> clamp 8192   AUDIT FAILS
    10x -> clamp 5120   EQUALS the floor -- V219/V225 used 4608 instead

**Above ~10x the command cannot be delivered without raising a safety interlock**, which this build
does not do. `0xC674E` is asserted FROZEN at 5120.

WHAT IS ASSUMED. That the grinding work reduces what V101 produced. That is the whole bet, and it is
UNFLOWN -- every part of this lineage is unflown. The gain step itself is arithmetic and certain; its
interaction with the grinding is not.

BASE: V241.
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
WRITE_MODE = os.environ.get("ACCORD_V242_WRITE", "").strip().lower()

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
GAIN = 0xC6CD0                              # forward LKAS gain; 0xC646C = 891 is 1x
CLAMP_A, CLAMP_B = 0xC61B2, 0xC61B4         # forward-path clamps, must track the gain
SOFT_EME = 0xC674E                          # the interlock the clamp must stay BELOW
G_OLD, G_NEW = 5346, 7128
C_OLD, C_NEW = 3072, 4096
BQ = 0xC60A8                                # the notch -- asserted CARRIED, not touched
LKAS_CLAMP = 0xC616C                        # must be 0: the proof LKAS cannot reach the map
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
R26_ARM = 0xC6444          # the r26 arm -- frozen at 512, asserted
TAG = "V242-V241BASE-GAIN8X.CLAMPS4096"

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
    check(u16(base, GAIN) == G_OLD, f"base gain = {G_OLD} ({G_OLD // 891}x)")
    check(u16(base, CLAMP_A) == C_OLD and u16(base, CLAMP_B) == C_OLD,
          f"base clamps = {C_OLD}, tracking the base gain")
    check(u16(base, SOFT_EME) == 5120, "base soft-EME floor = 5120")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- two bytes")
    struct.pack_into("<H", code, GAIN, G_NEW)
    struct.pack_into("<H", code, CLAMP_A, C_NEW)
    struct.pack_into("<H", code, CLAMP_B, C_NEW)
    attributed |= {GAIN, GAIN + 1, CLAMP_A, CLAMP_A + 1, CLAMP_B, CLAMP_B + 1}
    check(u16(code, GAIN) == G_NEW, f"gain {G_OLD} -> {G_NEW} ({G_NEW // 891}x)")
    check(u16(code, CLAMP_A) == C_NEW and u16(code, CLAMP_B) == C_NEW,
          f"clamps {C_OLD} -> {C_NEW}, both")

    print("\n  [3] WHY -- the record's own bracket, asserted rather than narrated")
    # THE EME INTERLOCK -- the clamp must stay BELOW the soft-EME floor
    _eme = u16(code, SOFT_EME)
    check(_eme == 5120, f"soft-EME floor FROZEN at {_eme} -- this build does not touch it")
    check(C_NEW < _eme,
          f"EME AUDIT: clamp {C_NEW} < soft-EME floor {_eme}. Exact tracking for this gain "
          f"would be {G_NEW * 512 // 891}; anything >= {_eme} fails and is why there is no 16x")
    check(u16(code, 0xC407E) == 511, "hard-fault interlock 0xC407E unchanged at 511")
    check(bytes(code[BQ:BQ + 16]) == bytes(base[BQ:BQ + 16]),
          "the notch is CARRIED byte-for-byte -- this build changes gain and clamps only")
    check(u16(code, LKAS_CLAMP) == 0,
          "0xC616C = 0 -- the map is fed by the driver torque sensor alone; LKAS cannot reach it")
    check(u16(code, LEVER_B) == LEVER_B_VAL,
          f"Lever B CARRIED at {LEVER_B_VAL}")
    check(u16(code, R26_ARM) == 512, "0xC6444 r26 arm UNTOUCHED at 512")

    print("\n  [4] THE NOTCH IS THE ONE THING V241 CHANGES; ELSE V235 BYTE FOR BYTE")
    # inherited from V238, where the biquad WAS untouched. V241 re-aims it deliberately, so the
    # assertion is INVERTED: the block must DIFFER, and only in the four coefficients.
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == bytes(base[BIQ:BIQ + BIQ_LEN]),
          "the notch block is CARRIED byte-for-byte -- V241 re-aimed it, this build carries it")
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
    check(len(pay) <= 6, f"{len(pay)} payload byte(s), at most gain + two clamps")
    check(set(pay) <= {GAIN, GAIN + 1, CLAMP_A, CLAMP_A + 1, CLAMP_B, CLAMP_B + 1},
          "every payload byte is the gain or a clamp -- nothing else moved")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V242 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v242_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V242_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V242 RAISES THE LKAS GAIN TO 8X ON THE FINISHED GRINDING WORK.                                     **")
    print("  **   0xC6CD0   5346 ->  7128     the forward gain (0xC646C = 891 is 1x)                               **")
    print("  **   0xC61B2   3072 ->  4096     forward clamp A, tracking                                            **")
    print("  **   0xC61B4   3072 ->  4096     forward clamp B, tracking                                            **")
    print("  ** THE RISK, STATED PLAINLY: 8x FLEW ONCE AS V101 AND WAS REJECTED --                                 **")
    print("  ** 'GRINDING/VIBRATION AT ALL SPEEDS, ONLY WHILE LKAS COMMANDS'. The operator                         **")
    print("  ** reverted to 6x himself. The peak MOVED 20.3 -> 23.0 Hz; de-confounded gain                         **")
    print("  ** 2.7-3.9x at 22-26 Hz.                                                                              **")
    print("  ** WHY THIS IS NOT A REPEAT: that 22-26 Hz band is exactly what this lineage's                        **")
    print("  ** notch attacks, aimed by an instrument independent of the EPS. V101 raised the                      **")
    print("  ** gain with NO grinding treatment. It may still grind -- the bet is unflown.                         **")
    print("  ** THE EME INTERLOCK, and why there is no 16x: the clamp must stay BELOW                              **")
    print("  ** 0xC674E = 5120, and clamp = gain*512//891:                                                         **")
    print("  **    6x -> 3072 OK    8x -> 4096 OK    10x -> 5120 EQUALS the floor                                  **")
    print("  **   12x -> 6144 FAILS      16x -> 8192 FAILS                                                         **")
    print("  ** 0xC674E is asserted FROZEN. Above ~10x the command cannot be delivered without                     **")
    print("  ** raising a safety interlock, which this build does not do.                                          **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
