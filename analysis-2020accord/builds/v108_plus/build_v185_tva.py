#!/usr/bin/env python3
r"""
V185 -- THE PHASE-SAFE BUILD.  Base = V184.  Four float32 cells.
        Reverts the assist-section biquad to HONDA'S coefficients, spending ZERO phase margin.

WHY THIS EXISTS
---------------
The biquad is ENGAGED-GATED (0xC649B = 1, arm source = the LKAS engagement flag), so every pole edit
is an ENGAGED-ONLY change in both magnitude AND phase.  V184's poles add ** +16.4 deg of lag at
1 Hz **.  That path is part of the plant openpilot controls, so the lag enters openpilot's loop.

I tried to measure whether openpilot can afford it, and ** the attempt FAILED ITS OWN CONTROLS **:
    ENGAGED (loop closed)   Mp = 0.840 at 0.39 Hz
    manual  (loop OPEN)     Mp = 19.59 at 1.17 Hz   <- artifact: Ang/Cmd divides by ~0
    phase-shuffled command  Mp = 0.683 at 0.39 Hz
The engaged peak is BELOW 1 and barely above the shuffled surrogate, because command and angle are
both dominated by road curvature -- the estimate measures the ROAD, not the loop.
=> ** openpilot's phase margin is NOT estimable from this corpus.  The 16.4 deg is an UNQUANTIFIED
   risk, not a small one. **

And the operator lists ** peak command oscillation ** as a CURRENT symptom.  A loop that already
oscillates has thin margin by definition, so spending 16.4 deg of it is the wrong direction for his
third stated goal.

WHAT V185 IS
------------
V184 with the four biquad coefficients returned to Honda's -- the values V122 already flies -- read
from the STOCK image rather than typed.  Everything else in V184 is carried:
    K1 -> Honda (V177) - accel EMA alpha -> Honda (V179) - w[3] halved (V181)
    the engaged inertia dose -> Honda, and engaged == manual in every data table (V184)
    the 427 probe on gp-0x6ac0 (V183)
=> ** phase identical to what he drives today; only the RATCHET levers remain. **

THE TRADE, PLAINLY
------------------
    build   grind 15-25 Hz   ratchet    added lag @1 Hz   spends phase margin?
    V184        -16.0 dB     -8.8 dB       +16.4 deg      YES, unquantified
    V185         ~none       inertia only    ~0 deg       NO
V185 gives up the entire grind attenuation.  It keeps every lever that does not cost phase.
** If the ratchet is driven by the inertia lane, V185 fixes it at zero phase cost.  If it is driven
by loop gain in the assist section, V185 will do nothing and V184 is the answer. **
That is a genuine fork and it is the operator's to choose, not mine to pick for him.
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
WRITE_MODE = os.environ.get("ACCORD_V185_WRITE", "").strip().lower()
BASE_NAME = "_v184_V184-V183BASE-ENGAGED.EQ.MANUAL.EXCEPT.INERTIA_plain_image.bin"
BASE_SHA = "96509cc9b102e02653965bfd719b351f48a941720873a95ee42332bf6a5d5fa4"

BIQUAD = (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4)
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
CARRIED_U16 = {0xC40D2: ("K1 -> Honda (V177)", 102),
               0xC63A6: ("w[3] halved (V181)", 512),
               0x55DF2: ("427 probe source gp-0x6ac0 (V183)", 0x9540)}
CARRIED_B = {0xC40DC: ("accel alpha -> Honda (V179)", 22),
             0x55E10: ("packer sar 4 (V183)", 0xA4)}
PTR_I = 0xCBE74
HONDA_Y = (-9830, -5734, -1966)

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


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def build():
    import cmath
    import math
    print("=" * 102)
    print("  V185 -- PHASE-SAFE: biquad back to Honda, zero added phase   (base V184)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V184 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] HONDA'S COEFFICIENTS ARE READ FROM THE STOCK IMAGE, NEVER TYPED")
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()
    for off in BIQUAD:
        print(f"      0x{off:05X}  stock {f32(stock, off):+.9g}   base {f32(base, off):+.9g}")

    print("\n  [3] THE EDIT -- four float32 cells back to Honda")
    attributed = set()
    for off in BIQUAD:
        before = f32(code, off)
        struct.pack_into("<I", code, off, u32(stock, off))
        attributed |= set(range(off, off + 4))
        if before != f32(code, off):
            print(f"      0x{off:05X}  {before:+.9g} -> {f32(code, off):+.9g}")
    for off in BIQUAD:
        check(u32(code, off) == u32(stock, off),
              f"0x{off:05X} byte-identical to stock (Honda's own)")

    print("\n  [4] ZERO ADDED PHASE -- the section is now what the car already flies")

    def H(b, f):
        z = cmath.exp(2j * math.pi * f / 1000.0)
        return (f32(b, 0xC60B4) * (z * z + f32(b, 0xC60B0) * z + 1.0)
                / (z * z + f32(b, 0xC60A8) * z + f32(b, 0xC60AC)))

    for fr in (1.0, 8.17, 21.0):
        d = math.degrees(cmath.phase(H(code, fr)) - cmath.phase(H(stock, fr)))
        check(abs(d) < 0.01, f"{fr:5.2f} Hz phase vs stock = {d:+.4f} deg (zero by construction)")

    print("\n  [5] EVERY RATCHET LEVER IS CARRIED, AND ASSERTED")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        check(u16(code, off) == want, f"0x{off:05X} {nm} CARRIED ({want})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED (0x{want:02X})")
    for m in (26, 27):
        p = u32(code, PTR_I + 4 * m)
        n = s16(code, p)
        Y = tuple(s16(code, p + 2 + 2 * n + 2 * i) for i in range(3))
        check(Y == HONDA_Y, f"inertia m{m} Y = {Y} -- the dose revert CARRIED")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- no cave change")

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

    print("\n  [7] FULL BYTE DIFF vs V184")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) <= 16, f"{len(pay)} payload bytes (<= 16: four float32 cells)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V185 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V185-V184BASE-BIQUAD.HONDA.PHASE.SAFE"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v185_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V185_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** ZERO added phase. Keeps every ratchet lever that does not cost margin. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
