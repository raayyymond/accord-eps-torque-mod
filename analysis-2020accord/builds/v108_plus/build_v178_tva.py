#!/usr/bin/env python3
r"""
V178 -- RESTORE HONDA'S RAMP IN THE 0xC6590 FLOAT BLOCK.  Base = V177.  7 float32 cells, 28 bytes.
        Undoes V122's flattening of three LERPs to a constant +-5.0, including a 0 -> 5.0
        BELOW-RANGE FALLBACK that removed a deadband entirely.

WHAT V122 DID, READ FROM THE IMAGES
------------------------------------
    addr       stock   V122+     role (from the disassembly at 0x44374..0x443EE)
    0xC6598      1.0     5.0
    0xC659C      1.0     5.0
    0xC65AC     -1.0    -5.0
    0xC65B0     -1.0    -5.0
    0xC65C4      0.0     5.0     ** Y[0]: the BELOW-RANGE FALLBACK of the X=[700,800,1100] LERP **
    0xC65C8      1.5     5.0
    0xC65CC      2.0     5.0

The third LERP is pinned exactly by the disassembly:

    0x44374  ld.w   0x75b8, tp, r11     ; X[0] = 700.0
    0x44378  cmpf.s le, r9, r11         ; input < X[0] ?
    0x4438e  ld.w   0x75c4, tp, r13     ; -> Y[0]      ** the below-range fallback **

** So below input 700 stock returns 0.0 (no effect) and the flying build returns 5.0 (maximum). **
And with Y = [5,5,5] the whole curve is a CONSTANT 5.0 where stock rose 0.0 -> 1.5 -> 2.0.
V122 replaced a graduated ramp with full effect everywhere, and deleted a deadband.

WHY THAT MATTERS HERE
----------------------
This is the shape change [[accord-v80-damper-relay-and-grind1-inert]] was written about:
"the damper became a RELAY ... worst grinding ever ... ** restore the RAMP, don't merely lower k **".
An abrupt onset at small input is exactly the structure that produces notchiness rather than steady
drag, and it is live on the car.

** HONEST LIMIT ON THIS CLAIM. **  I have pinned the SHAPE change decisively -- the fallback value,
the knot values, and the LERP structure all come straight from the image and the disassembly.  I have
NOT established what the quantity physically is: the input reaches the LERP in r9 and the only nearby
RAM cell (`gp-0x6d94`) has ONE writer and ZERO readers, i.e. it is a diagnostic mirror, not the
source.  So this build is justified as a ** revert to Honda's own values ** -- the kit's safest class
-- and NOT as an understood lever.  Do not describe it as one.

WHY IT IS NOT FLY-FIRST
------------------------
V177 is ONE cell and fully attributable.  V178 adds SEVEN cells whose semantics are unestablished.
Fly V177 first.  V178 is for the operator who wants the whole undocumented V122 delta undone in one
go, accepting that a result could not be attributed to a single cell.

THE RECORD GAP THAT HID ALL OF THIS
------------------------------------
** `docs/BUILD-LINEAGE*.md` stops at V121.  V122 -- the FLYING build -- has no entry, and neither
does anything after it. **  Every lever proposed this session was checked against a lineage that does
not cover what is on the car, which is why V122's four substantive changes (K1 x5, the ramp width x5,
the accel EMA alpha 22->8, and this flattening) only surfaced from a raw byte diff.

NOT INCLUDED, DELIBERATELY
---------------------------
  * `0xC40BC` (ramp width, 600 -> 3000).  Reverting it would make the Coulomb zero-crossing 5x
    SHARPER -- the one thing V122 got right.  Asserted untouched.
  * `0xC40DC` (accel EMA alpha, 22 -> 8).  A PHASE change whose direction is unestablished.
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
WRITE_MODE = os.environ.get("ACCORD_V178_WRITE", "").strip().lower()
BASE_NAME = "_v177_V177-V175BASE-K1.COULOMB.REVERT.HONDA.102_plain_image.bin"
BASE_SHA = "fc93255645014a0f0d70c199c8e86fa11c6a435b2054c97363b92b6dbd1b8d02"

CELLS = [0xC6598, 0xC659C, 0xC65AC, 0xC65B0, 0xC65C4, 0xC65C8, 0xC65CC]
FROZEN = {0xC40BC: ("ramp width", 3000), 0xC40D2: ("K1 Coulomb", 102), 0xC63A6: ("w[3]", 1024),
          0xC407E: ("fault interlock", 511)}
ALPHA_A = 0xC40DC

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def f32(buf, off):
    return struct.unpack_from("<f", buf, off)[0]


def build():
    print("=" * 102)
    print("  V178 -- HONDA'S RAMP RESTORED IN THE 0xC6590 FLOAT BLOCK   (base V177)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V177 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] HONDA'S VALUES ARE READ FROM THE STOCK IMAGE, NEVER TYPED")
    stock_p = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                  "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                   "analysis-2020accord", "stock_fw_dump", "code.bin")
    stock = stock_p.read_bytes()
    check(abs(f32(stock, 0xC65C4)) < 1e-9,
          f"stock 0xC65C4 (the below-range FALLBACK) = {f32(stock, 0xC65C4)} -- a real DEADBAND")
    check(abs(f32(base, 0xC65C4) - 5.0) < 1e-6,
          f"base 0xC65C4 = {f32(base, 0xC65C4)} -- the deadband V122 deleted")

    print("\n  [3] THE EDIT -- 7 float32 cells back to Honda")
    attributed = set()
    for off in CELLS:
        w = struct.unpack_from("<I", stock, off)[0]
        before = f32(code, off)
        struct.pack_into("<I", code, off, w)
        attributed |= set(range(off, off + 4))
        print(f"      0x{off:05X}  {before:+8.4f} -> {f32(code, off):+8.4f}"
              f"{'    <== the below-range FALLBACK / deadband' if off == 0xC65C4 else ''}")
    for off in CELLS:
        check(struct.unpack_from("<I", code, off)[0] == struct.unpack_from("<I", stock, off)[0],
              f"0x{off:05X} is now byte-identical to stock")

    print("\n  [4] WHAT STAYS PUT, AND WHY -- asserted, not assumed")
    for off, (nm, want) in sorted(FROZEN.items()):
        got = struct.unpack_from("<H", code, off)[0]
        check(got == want, f"0x{off:05X} {nm} FROZEN at {got}")
    check(code[ALPHA_A] == base[ALPHA_A],
          f"0x{ALPHA_A:05X} accel EMA alpha UNTOUCHED at {code[ALPHA_A]} (phase, direction unknown)")
    print("      0xC40BC deliberately NOT reverted: 600 would make the Coulomb zero-crossing")
    print("      5x SHARPER, undoing the one V122 change that helps.")

    print("\n  [5] CRC RECOMPUTATION")
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
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [6] FULL BYTE DIFF vs V177 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    _tr = [b[1] for b in blocks]
    for lo, hi in runs:
        tag = "CRC" if any(lo < t + 4 and t < hi for t in _tr) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo < t + 4 and t < hi for t in _tr))
    check(payload <= 28, f"{payload} payload bytes (<= 28: seven float32 cells)")

    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V178 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V178-V177BASE-C6590.RAMP.RESTORE.HONDA"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v178_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [8] NOT WRITTEN -- set ACCORD_V178_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** NOT fly-first. V177 is one cell and attributable; this is seven of unknown "
          "semantics. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
