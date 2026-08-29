#!/usr/bin/env python3
# ############################################################################################
# RETRACTED 2026-08-29 -- DO NOT BUILD, DO NOT FLASH. THE STATED AXIS IS WRONG.
#
# This build raises FactorC Y[0] on the belief that X[0] = 2240 counts = 35.0 km/h, i.e. that
# Y[0] is the fallback across the 1-24 km/h creep band.  ** THAT IS NUMEROLOGY. **  2240/64
# happens to equal 35, and I built on the coincidence.
#
# FUN_00034350 (decompiled) shows gp-0x6bd0 is a FIVE-factor product, and:
#     FactorC = LERP(0xC9E9C[mode], index = gp-0x6a5e)     <-- NOT vehicle speed
#     FactorE = LERP(0xC9F84[mode], index = gp-0x6ac0)     <-- the resolver/FOC electrical rate
# with gates: FactorC needs gp-0x67f4==1 and gp-0x6a5e<=0x7d00, else it is 1024 (UNITY, not 0);
# FactorE needs gp-0x6ac0<0x32c9 and |gp-0x6abe|<=0x6590, else THE WHOLE PRODUCT IS ZEROED.
#
# So the edit raises a fallback on the gp-0x6a5e axis.  Whether that axis is ever in its
# below-range region during creep ratcheting is UNKNOWN and was never established.  The
# 272-crossing knot-step null I computed tested SPEED crossings against a knot that is not on
# speed, so it does not support this build either.
#
# Artifacts renamed SUPERSEDED-DO-NOT-FLASH-WRONGAXIS-*.  Kept as a record of the error.
# LESSON: read the INDEX EXPRESSION from the code. Never infer a table axis from a unit
# conversion that happens to come out round.
# ############################################################################################
r"""
V182 -- ADD DAMPING AT CREEP: raise FactorC's below-range fallback on the ENGAGED modes.
        Base = V181.  Two int16 cells, 4 bytes.  0xD77DA 429 -> 700, 0xD77EE 426 -> 700.

WHY THIS IS DIFFERENT FROM EVERY OTHER BUILD IN THE SESSION
------------------------------------------------------------
V173..V181 all REMOVE loop gain (poles, K1, the inertia dose, the inertia weight).  ** This is the
only build that ADDS DAMPING **, which is the textbook fix for a lightly damped resonance.  It uses
Honda's own base-assist damper rather than introducing anything new.

    ch0 = ( FactorC(speed) x FactorE(rate) ) >> 10

MODE-PROOFED  (RULE 7 -- this took three attempts to get right; see docs/STATE.md)
----------------------------------------------------------------------------------
The index is pinned by disassembly:
    0x34502  ld.bu  0x63fd, gp, r13     ; the MODE INDEX byte
    0x34506  mov    0xc9e9c, r16        ; FactorC pointer table
    0x3450c  shl 0x2 / add / ld.w       ; -> the per-mode record
`gp+0x63FD` is the same byte FUN_00036c12 uses for 0xCBE74, and this car runs m24 = MANUAL,
m26/27 = ENGAGED.  Resolving AT THOSE INDICES:

    FactorC 0xC9E9C[m]        X                       Y                    record
      m24 -> 0xD67E4   [2240,3840,5120,8960]   [  0,234,429,908]   STOCK -- untouched by this build
      m26 -> 0xD77D0   [2240,3840,5120,8960]   [429,234,429,908]   Y[0] at 0xD77DA
      m27 -> 0xD77E4   [2240,3840,5120,8960]   [426,233,426,875]   Y[0] at 0xD77EE

X[0] = 2240 counts = ** exactly 35.0 km/h **, and Y[0] is the BELOW-RANGE FALLBACK.  So below
35 km/h -- i.e. across the whole 1-24 km/h creep band where the ratchet lives -- FactorC returns Y[0].

WHY IT REACHES THE RATCHET
---------------------------
FactorE is rate-gated (m26/27: X = [12,400,2500,4000], Y = [0,539,539,927]).  An 8 Hz ratchet of even
1 degree generates ~50 deg/s, which clears FactorE's knee comfortably, so FactorE is ALREADY live
during the oscillation.  Only FactorC's fallback limits the product.
    now   ch0 ~ (429 x ~310) >> 10 = ~129
    V182  ch0 ~ (700 x ~310) >> 10 = ~212        (~1.63x more creep damping while engaged)
** And because FactorE is rate-gated, this stays small in smooth low-speed driving ** -- it grows
with rate, which is exactly when a resonance needs damping.

RISK, STATED PLAINLY
---------------------
  * ENGAGED-ONLY.  m24 (manual) is stock and is asserted untouched, so manual and parking feel
    cannot change.  It is also separable on a drive by the same engaged-vs-manual contrast the card
    already uses.
  * The knot discontinuity worry is MEASURED AWAY: 272 crossings of 35 km/h vs 1069 control
    crossings at 25/30/40/45 give a median torque-activity ratio of 1.030 against a permutation null
    of [0.863, 1.190] -- the knot sits exactly on the smooth speed trend, so a step at X[0] is not
    detectable on-car.
  * ** It adds drag while engaged at creep. **  It is VISCOUS (rate-proportional), not stiction, so
    it does not add static friction -- but the operator will feel more damping in engaged creep and
    should be told.
  * Dose is 1.63x, not the maximum.  Y[0] could go to 908 (= Y[3], the 140 km/h value), which would
    make creep damping equal highway damping.  Headroom is deliberately left.

NOT INCLUDED
------------
  * FactorE.  Its knee is already open (X[0] 60 -> 12) and it is live during the oscillation; moving
    it further would add damping in SMOOTH driving too, which is the drag the operator does not want.
  * m24.  Manual stays exactly stock.
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
WRITE_MODE = os.environ.get("ACCORD_V182_WRITE", "").strip().lower()
BASE_NAME = "_v181_V181-V180BASE-W3.INERTIA.WEIGHT.1024.TO.512_plain_image.bin"
BASE_SHA = "49ca42da43e95f31fc90c4e7709b042d6ec02e3ca287b77146bd8af6c52d35c4"

PTR_C, PTR_E = 0xC9E9C, 0xC9F84
M_MANUAL, M_ENG = 24, (26, 27)
NEW_Y0 = 700
EXPECT = {26: (0xD77D0, 429), 27: (0xD77E4, 426)}
FROZEN_U16 = {0xC407E: ("hard-fault interlock", 511),
              0xC40D2: ("K1 -> Honda (V177)", 102),
              0xC63A6: ("w[3] halved (V181)", 512)}

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


def rec(b, ptr):
    n = s16(b, ptr)
    X = [s16(b, ptr + 2 + 2 * i) for i in range(n)]
    Y = [s16(b, ptr + 2 + 2 * n + 2 * i) for i in range(n)]
    return n, X, Y, ptr + 2 + 2 * n          # last = address of Y[0]


def build():
    raise SystemExit("V182 IS RETRACTED -- see the banner at the top of this file.")

    print("=" * 102)
    print("  V182 -- ADD DAMPING AT CREEP: FactorC fallback, ENGAGED modes only   (base V181)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V181 ({BASE_SHA[:16]}...)")
    code = bytearray(base)
    stock = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                 "analysis-2020accord", "stock_fw_dump", "code.bin").read_bytes()

    print("\n  [2] MODE-PROOF -- resolve the pointer table AT THE INDEX THE CAR RUNS")
    for m in (M_MANUAL,) + M_ENG:
        p = u32(code, PTR_C + 4 * m)
        n, X, Y, y0 = rec(code, p)
        check(0x13000 <= p < 0x100000, f"FactorC[m{m}] -> 0x{p:05X} is a plausible image address")
        print(f"      m{m:2d} -> 0x{p:05X}  n={n}  X={X}  Y={Y}   Y[0]@0x{y0:05X}")
        if m in EXPECT:
            want_p, want_y0 = EXPECT[m]
            check(p == want_p and Y[0] == want_y0,
                  f"m{m} record and Y[0] match the mode-proofed record (0x{want_p:05X}, {want_y0})")
    pm = u32(code, PTR_C + 4 * M_MANUAL)
    check(rec(code, pm)[2] == rec(stock, pm)[2],
          f"m{M_MANUAL} (MANUAL) FactorC Y is STOCK -- and stays stock")
    check(s16(code, u32(code, PTR_C + 4 * 26) + 2) == 2240,
          "X[0] = 2240 counts = exactly 35.0 km/h -- Y[0] is the BELOW-RANGE fallback for creep")

    print("\n  [3] THE EDIT -- Y[0] on the ENGAGED modes only")
    attributed = set()
    for m in M_ENG:
        p = u32(code, PTR_C + 4 * m)
        _, _, _, y0 = rec(code, p)
        before = s16(code, y0)
        struct.pack_into("<h", code, y0, NEW_Y0)
        attributed |= set(range(y0, y0 + 2))
        print(f"      m{m}  0x{y0:05X}  {before} -> {s16(code, y0)}   FactorC below-35 km/h fallback")

    print("\n  [4] THE RESULT")
    for m in M_ENG:
        n, X, Y, _ = rec(code, u32(code, PTR_C + 4 * m))
        check(Y[0] == NEW_Y0, f"m{m} FactorC Y[0] is now {NEW_Y0}")
        check(Y[0] <= max(Y), f"m{m} Y[0]={Y[0]} does not exceed the in-range max {max(Y)}")
    for nm, fc in (("now ", 429), ("V182", NEW_Y0)):
        print(f"      {nm}  ch0 at creep during an 8 Hz ratchet "
              f"~ ({fc} x 310) >> 10 = {(fc * 310) >> 10}")
    print(f"      => ~{NEW_Y0/429.0:.2f}x more creep damping WHILE ENGAGED; manual unchanged")

    print("\n  [5] WHAT IS ASSERTED UNTOUCHED")
    for off, (nm, want) in sorted(FROZEN_U16.items()):
        check(struct.unpack_from("<H", code, off)[0] == want, f"0x{off:05X} {nm} FROZEN at {want}")
    for m in (M_MANUAL,) + M_ENG:
        pe = u32(code, PTR_C + 4 * m)
        check(rec(code, pe)[1] == rec(base, pe)[1], f"m{m} FactorC X axis untouched")
    for m in (M_MANUAL,) + M_ENG:
        pe = u32(code, PTR_E + 4 * m)
        check(rec(code, pe)[1:3] == rec(base, pe)[1:3], f"m{m} FactorE untouched (X and Y)")

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

    print("\n  [7] FULL BYTE DIFF vs V181")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) <= 4, f"{len(pay)} payload bytes (<= 4: two int16 cells)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V182 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V182-V181BASE-FACTORC.CREEP.FALLBACK.700.ENGAGED"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v182_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V182_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** The ONLY build in the session that ADDS damping. ENGAGED-ONLY; manual is stock. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
