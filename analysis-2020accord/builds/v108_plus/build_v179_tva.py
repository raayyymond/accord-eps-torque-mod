#!/usr/bin/env python3
r"""
V179 -- RESTORE HONDA'S ACCELERATION FILTER.  Base = V177.  ONE BYTE.
        The last unexplored cell in the entire non-stock delta, and it completes Honda's
        inertia lane: V175 restored the lane's GAIN, this restores its FILTER.

HOW IT WAS FOUND
-----------------
After the V178 error I applied the rule it earned: print EVERY non-stock cal across all 139
images IN BUILD ORDER, then classify.
    LADDER      changed 3+ times / steps monotonically -> a deliberate tuning axis, DO NOT revert
    CHURN       changed and changed back              -> already explored, see the record
    SINGLE JUMP changed once, never revisited         -> the candidate class
Every SINGLE JUMP resolved to something known:
    0x14120, 0xC64DE     V2, ancient, 1-count
    0x35A08/12/18        V103, the biquad arm -- documented and deliberate
    0xC61C0, 0xC64B4     V36/V37 -- read together at the SAME four sites, and recorded in memory
                         as the gentle-EME debounce disable that FIXED the problem on-car.
                         ** Reverting those would bring the gentle EME back. **
** `0xC40DC` is the only one left unexplained. **

WHAT IT DOES  (`FUN_00041464`, the acceleration path)
------------------------------------------------------
    gp-0x6c2c = EMA( accel , alpha = cal[0xC40DC] >> 6 ) >> 9        (the FAST EMA)

    build            cal     a       fc        phase lag at 8.17 Hz
    Honda / V108      22   0.3438   67.0 Hz        6.95 deg
    V122+ (flying)     8   0.1250   21.3 Hz       21.03 deg

** V122 slowed the acceleration filter 67 Hz -> 21 Hz and added 14.1 deg of phase lag at the
ratchet frequency. **  `gp-0x6c2c` is the input to `gp-0x6b26`, the apparent-inertia term, which is
POSITIVE acceleration feedback and therefore destabilising.  Extra lag rotates that term toward a
velocity term, changing its character inside the loop.

** HONEST LIMIT.  The magnitude of the change is exact; the SIGN of its effect on damping is NOT
established. **  A rotated destabilising term can end up more or less damaging depending on the loop
phase at 8 Hz, and I have not closed that.  So this build is justified the same way V175 and V177
are: ** it is a revert to Honda's own value, and it makes the inertia lane self-consistent -- Honda's
gain (from V175) now runs with Honda's filter. **  It is NOT justified as an understood lever.

WHY IT IS WORTH ONE BYTE
-------------------------
V175 restored this lane's GAIN to Honda's while leaving V122's filter in place, so the flying
configuration is a hybrid nobody designed: Honda's gain through a filter 3x slower than Honda's.
V179 removes that mismatch.  One byte, fully attributable, lowest risk class.

RISK
----
A single byte returned to the value Honda ships, in a filter that has run on every car of this type.
It makes the acceleration signal FASTER, i.e. closer to the raw derivative -- so it passes slightly
more high-frequency content.  That is Honda's own choice and the downstream clamp (+-0xfa0000 before
the EMA, then the +-511 interlock at `0xC407E`) is untouched.  No cave, no code edit, no RAM claim.
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
WRITE_MODE = os.environ.get("ACCORD_V179_WRITE", "").strip().lower()
BASE_NAME = "_v177_V177-V175BASE-K1.COULOMB.REVERT.HONDA.102_plain_image.bin"
BASE_SHA = "fc93255645014a0f0d70c199c8e86fa11c6a435b2054c97363b92b6dbd1b8d02"

ALPHA_A = 0xC40DC
FLOWN = 8
FROZEN = {0xC40BC: ("Coulomb ramp width", 3000), 0xC40D2: ("K1 Coulomb", 102),
          0xC407E: ("hard-fault interlock", 511), 0xC63A6: ("w[3]", 1024),
          0xC61C0: ("V37 EME debounce disable", 0xFFFF)}
AUTHORITY = {0xC6598: 5.0, 0xC65C4: 5.0}      # the V31/V38 ladder -- asserted UNTOUCHED after V178

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def build():
    import math
    print("=" * 102)
    print("  V179 -- HONDA'S ACCELERATION FILTER RESTORED   (base V177, ONE byte)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V177 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] HONDA'S VALUE IS READ FROM THE STOCK IMAGE, NEVER TYPED")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    honda = stock[ALPHA_A]
    check(honda == 22, f"stock 0x{ALPHA_A:05X} = {honda} -- VERIFIED from the image")
    check(base[ALPHA_A] == FLOWN, f"base carries {FLOWN} (V122's), the thing being undone")

    print("\n  [3] WHAT THE BYTE DOES")
    for nm, c in (("Honda", honda), ("flown", FLOWN)):
        a = c / 64.0
        fc = -math.log(1 - a) * 1000.0 / (2 * math.pi)
        print(f"      {nm:6s} cal {c:3d}  a={a:.4f}  fc={fc:6.2f} Hz  "
              f"phase lag at 8.17 Hz = {math.degrees(math.atan(8.17/fc)):5.2f} deg")

    print("\n  [4] THE EDIT -- ONE byte")
    code[ALPHA_A] = honda
    attributed = {ALPHA_A}
    print(f"      0x{ALPHA_A:05X}  {FLOWN} -> {code[ALPHA_A]}   accel FAST-EMA alpha")
    check(code[ALPHA_A] == honda, f"0x{ALPHA_A:05X} is now Honda's {honda}")

    print("\n  [5] EVERYTHING ELSE CARRIED, ASSERTED -- including the AUTHORITY LADDER")
    for off, (nm, want) in sorted(FROZEN.items()):
        got = struct.unpack_from("<H", code, off)[0]
        check(got == want, f"0x{off:05X} {nm} FROZEN at {got}")
    for off, want in sorted(AUTHORITY.items()):
        got = struct.unpack_from("<f", code, off)[0]
        check(abs(got - want) < 1e-6,
              f"0x{off:05X} V31/V38 authority ladder INTACT at {got} (V178's error, not repeated)")

    print("\n  [6] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = struct.unpack_from("<I", code, blk[1])[0]
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base")

    print("\n  [7] FULL BYTE DIFF vs V177")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    unattributed = [a for a in diff if a not in attributed]
    check(not unattributed, f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) == 1, f"{len(pay)} payload byte (exactly 1)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V179 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V179-V177BASE-ACCEL.EMA.ALPHA.REVERT.HONDA.22"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v179_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V179_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** Completes Honda's inertia lane: V175 gave it Honda's GAIN, this gives it Honda's "
          "FILTER. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
