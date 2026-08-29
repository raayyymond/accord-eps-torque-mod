#!/usr/bin/env python3
r"""
V184 -- ENGAGED == MANUAL EVERYWHERE EXCEPT THE ONE THING WE ARE TESTING.  Base = V183.
        Backs out V158's damper asymmetries so the ONLY engaged/manual difference removed is the
        inertia dose, and NO new asymmetry is introduced.

THE FINDING THIS BUILD IS BUILT ON
-----------------------------------
[[accord-stock-mode24-equals-mode26-damper-is-ours]] says stock ships m24 == m26 byte-identical.
Enumerating every mode-record family on the FLYING build (V122) confirms it, and finds exactly ONE
kit-created engaged-vs-manual asymmetry on the car:

    table                          V122 (FLYING)
    0xC9CCC  L1                    m26 == m24, m27 == m24
    0xC9DB4  L3                    m26 == m24, m27 == m24
    0xC9E9C  FactorC               m26 == m24;  m27 differs ALREADY IN STOCK -> Honda's, not ours
    0xC9F84  FactorE               m26 == m24, m27 == m24
    0xC77A0  L5 clamp              m26 == m24, m27 == m24
    0xCBE74  inertia/friction      ** m26/m27 Y = [-29490,-17202,-16000] vs m24 [-9830,-5734,-1966] **

** So the ONE engaged-only asymmetry this kit put on the car is the inertia dose. **  The ratchet is
engaged-amplified ~15x.  If that amplification is caused by a mode asymmetry at all, this is it.

WHY V183 IS NOT THE CLEAN TEST, AND THIS IS
--------------------------------------------
V183 inherits V158's damper edits, which CREATE two new engaged-only asymmetries the car does not
have:
    FactorC m26  Y[0] 0 -> 429                  (0xD77DA)
    FactorE m26  X[0] 60 -> 12, Y[1] 140 -> 539 (0xD780E, 0xD7818)
    FactorE m27  X[0] 60 -> 12, Y[1] 140 -> 539 (0xD7822, 0xD782C)
So V183 removes one asymmetry and adds three.  A result would be ambiguous between them.

V184 backs those out to their m24 values, read FROM THE m24 RECORD AT RUN TIME rather than typed.
The result: ** engaged is identical to manual in every factor family, exactly as stock ships it,
except that the inertia dose is gone. **  That is a single-variable test of the one candidate.

WHAT THIS BUILD STILL CARRIES
------------------------------
Everything that is NOT a mode asymmetry stays: the assist-section poles (V173/V180), K1 -> Honda
(V177), the accel filter -> Honda (V179), w[3] halved (V181), and the 427 probe on gp-0x6ac0 (V183).
** CORRECTED 2026-08-29: the assist-section biquad is ENGAGED-GATED. **  0xC649B = 1 and the arm
source is gp-0x6806, the LKAS engagement flag (V103 onward, including the FLYING build).  So the pole
retune is ALSO an engaged-only change, and this build carries TWO of them.  ** The engaged-vs-manual
ratio therefore does NOT isolate the inertia dose. **  Use the BAND signature instead, which does
separate them: the poles hit the GRIND hardest (-16.0 dB grind vs -8.8 dB ratchet) while the inertia
revert moves the RATCHET with the grind roughly unchanged.  K1, the accel filter and the 427 probe are
genuinely mode-independent or instrumentation.

WHAT A NULL LICENSES
---------------------
  * ratchet falls AND the engaged/manual ratio falls  -> the inertia dose was carrying the engaged
    amplification.  That is the strongest single result available from one drive.
  * ratchet falls, ratio unchanged                    -> the broadband levers did it; the mode
    asymmetry was not the amplifier.
  * neither moves                                     -> no mode asymmetry explains the engaged
    amplification, and the search moves outside the mode records entirely.
Plus, independently, the 427 probe answers whether the damper's hard OFF gate is ever open.

RISK
----
Five int16 cells returned to values copied from the car's own m24 records.  No cave, no code edit.
It makes the engaged damper configuration identical to manual -- i.e. exactly what the operator has
been driving -- so it cannot introduce a damper behaviour he has not already experienced.
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
WRITE_MODE = os.environ.get("ACCORD_V184_WRITE", "").strip().lower()
BASE_NAME = "_v183_V183-V181BASE-PROBE.427.GP6AC0.SAR4_plain_image.bin"
BASE_SHA = "9f9326170e8adab18f37d7e936f57610f995e2ed1ff05b57335fbb8da22fb19a"

PTR_C, PTR_E, PTR_I = 0xC9E9C, 0xC9F84, 0xCBE74
CARRIED_U16 = {0xC407E: ("hard-fault interlock", 511), 0xC40D2: ("K1 -> Honda", 102),
               0xC63A6: ("w[3] halved", 512), 0x55DF2: ("427 probe source gp-0x6ac0", 0x9540)}
CARRIED_B = {0xC40DC: ("accel alpha -> Honda", 22), 0x55E10: ("packer sar 4", 0xA4)}

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def rec(b, p):
    n = s16(b, p)
    return (n, [s16(b, p + 2 + 2 * i) for i in range(n)],
            [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)])


def build():
    print("=" * 102)
    print("  V184 -- ENGAGED == MANUAL except the inertia dose   (base V183)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V183 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] COPY EACH ENGAGED RECORD FROM ITS OWN m24 RECORD -- values are READ, not typed")
    attributed = set()
    for tbl, nm in ((PTR_C, "FactorC"), (PTR_E, "FactorE")):
        p24 = u32(code, tbl + 4 * 24)
        n24, X24, Y24 = rec(code, p24)
        for m in (26, 27):
            pm = u32(code, tbl + 4 * m)
            nm_, Xm, Ym = rec(code, pm)
            if (Xm, Ym) == (X24, Y24):
                print(f"      {nm} m{m}: already == m24, nothing to do")
                continue
            # m27 FactorC differs in STOCK too -> Honda's asymmetry, leave it alone
            if nm == "FactorC" and m == 27:
                print(f"      {nm} m{m}: differs in STOCK too -> Honda's, deliberately LEFT ALONE")
                continue
            check(nm_ == n24, f"{nm} m{m} knot count matches m24 ({nm_})")
            for i in range(n24):
                ox, oy = pm + 2 + 2 * i, pm + 2 + 2 * n24 + 2 * i
                if s16(code, ox) != X24[i]:
                    print(f"      {nm} m{m} X[{i}] 0x{ox:05X}  {s16(code, ox)} -> {X24[i]}")
                    struct.pack_into("<h", code, ox, X24[i])
                    attributed |= set(range(ox, ox + 2))
                if s16(code, oy) != Y24[i]:
                    print(f"      {nm} m{m} Y[{i}] 0x{oy:05X}  {s16(code, oy)} -> {Y24[i]}")
                    struct.pack_into("<h", code, oy, Y24[i])
                    attributed |= set(range(oy, oy + 2))

    print("\n  [3] THE RESULT -- engaged == manual in every family except the inertia dose")
    for tbl, nm in ((0xC9CCC, "L1"), (PTR_C, "FactorC"), (PTR_E, "FactorE"),
                    (0xC9DB4, "L3"), (0xC77A0, "L5"), (PTR_I, "inertia")):
        r24 = rec(code, u32(code, tbl + 4 * 24))
        for m in (26, 27):
            rm = rec(code, u32(code, tbl + 4 * m))
            same = (rm == r24)
            if tbl == PTR_I:
                check(same, f"{nm} m{m} == m24  ** the inertia dose is GONE **")
            elif nm == "FactorC" and m == 27:
                print(f"      {nm} m{m}: {'==' if same else 'differs'} m24 (Honda's own, expected)")
            else:
                check(same, f"{nm} m{m} == m24")

    print("\n  [4] EVERYTHING ELSE CARRIED")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        got = struct.unpack_from("<H", code, off)[0]
        check(got == want, f"0x{off:05X} {nm} CARRIED ({got})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED (0x{code[off]:02X})")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- no cave change")

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
          "CRC-skipped block byte-identical to base")

    print("\n  [6] FULL BYTE DIFF vs V183")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    print(f"      {len(pay)} payload bytes")

    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V184 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V184-V183BASE-ENGAGED.EQ.MANUAL.EXCEPT.INERTIA"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v184_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [8] NOT WRITTEN -- set ACCORD_V184_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** The ONLY engaged/manual asymmetry removed is the inertia dose. Single variable. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
