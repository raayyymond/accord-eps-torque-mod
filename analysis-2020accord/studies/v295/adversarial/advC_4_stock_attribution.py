# -*- coding: utf-8 -*-
"""ADV-C part 4 -- EVERY byte of stock -> V295 over [0x13000, 0x100000), attributed to a named row and to the build that
last set it.  Rows 1-28 are the V282 cumulative-delta rows (docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md),
matched by ADDRESS here (not by reading that doc's numbers); V293/V294/V295 cells by address.  Writes the full list to
out/advC_4_stock_v295_every_offset.txt.  No kit import."""
import glob
import hashlib
import struct
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"


def ld(p):
    g = [x for x in glob.glob(FW + p) if "SUPERSEDED" not in x]
    assert len(g) == 1, g
    return open(g[0], "rb").read()


stock = open(FW + "stock_fw_dump/code.bin", "rb").read()
v282, v293, v294, v295 = ld("_v282_*_plain_image.bin"), ld("_v293_*_plain_image.bin"), ld("_v294_*_plain_image.bin"), ld("_v295_*_plain_image.bin")
assert hashlib.sha256(v295).hexdigest().startswith("5c044d65")
u16 = lambda b, o: struct.unpack_from("<H", b, o)[0]                      # noqa: E731
u32 = lambda b, o: struct.unpack_from("<I", b, o)[0]                      # noqa: E731


def chain(img):
    bs, bl, out = u16(img, 0xFFFF8) << 12, (u16(img, 0xFFFFA) << 12) - 4, []
    while True:
        out.append((bs, bs + bl))
        if bs == 0x13000:
            return out
        bs, bl = u16(img, bs - 8) << 12, (u16(img, bs - 6) << 12) - 4


TRL = {b1 + k for _, b1 in chain(stock) for k in range(4)}


def ybytes(img, tbl):
    s = set()
    for k in range(28):
        p = u32(img, tbl + 4 * k); n = u16(img, p)
        s |= set(range(p + 2 + 2 * n, p + 2 + 4 * n))
    return s


KP, KD = ybytes(v295, 0xCB994), ybytes(v295, 0xCB7D4)
R = {}
def put(name, addrs):
    for a in addrs:
        R.setdefault(a, name)
put("V295/V294/V282-orig gain b 0xC63EA", range(0xC63EA, 0xC63EC))
put("V294 pole a 0xC63E8", range(0xC63E8, 0xC63EA))
put("V294 fb clamp C 0xC62E6 (V276/V280/V293/V294)", range(0xC62E6, 0xC62E8))
put("V294 0x28FA4 add->subr", range(0x28FA4, 0x28FA6))
put("V294 0x29D76 shl5->shl2", range(0x29D76, 0x29D78))
put("V293 D clamp 0xC61B6", range(0xC61B6, 0xC61B8))
put("V293 r24 arm 0xC6446 (V67/V88/V293)", range(0xC6446, 0xC6448))
put("V293/V294 Kp bank Y (all 28)", KP)
put("V293 Kd bank Y (all 28)", KD)
put("R1 version marker", [0x13109, 0x14120])
put("R2 fwd-gain load repoint", range(0x2A1F0, 0x2A1F2))
put("R3 biquad arm", [0x35A08, 0x35A09, 0x35A12, 0x35A18])
put("R4 rate-lane gate", [0x3AA96])
put("R5 gp-0x67fa byte", [0x454FE])
put("R6 0x14A hook", range(0x55C0E, 0x55C12))
put("R7 0x14A cave body", range(0xC4B34, 0xC4BD8))
put("R8 CAN-427 tap window", range(0x55DF2, 0x55E12))
put("R9 private fwd gain 0xC6CD0", range(0xC6CD0, 0xC6CD2))
put("R10 fwd clamps 0xC61B2/B4", range(0xC61B2, 0xC61B6))
put("R12 r24 arm", range(0xC6446, 0xC6448))
put("R13 biquad enable", [0xC649B])
put("R14 lockout 0xC62EA", range(0xC62EA, 0xC62EC))
put("R15 EME quad", list(range(0xC674E, 0xC6752)) + list(range(0xC675A, 0xC675E)))
put("R16 EME ramp", range(0xC6768, 0xC676E))
put("R17 EME float mirrors", [a for b0 in (0xC6598, 0xC659C, 0xC65AC, 0xC65B0, 0xC65C4, 0xC65C8, 0xC65CC) for a in range(b0, b0 + 4)])
put("R18 Coulomb relay", list(range(0xC40BC, 0xC40BE)) + list(range(0xC40D2, 0xC40D4)) + list(range(0xC40DC, 0xC40DE)))
put("R19 STEER_STATUS debounce C0-C4", range(0xC61C0, 0xC61C6))
put("R20 STEER_STATUS debounce B4/B6", range(0xC64B4, 0xC64B8))
put("R21 DTC-0x49 gate", range(0xC64B8, 0xC64BA))
put("R22 square-wave hold", [0xC64DE])
put("R28/+ page-CRC trailers", TRL)


def row(a):
    if a in R:
        return R[a]
    if 0xCE000 <= a < 0xDA000:
        return "R23 damper rate/boost bank flatten"
    if 0xE4000 <= a < 0xE9000:
        return "R24/25/26 LERP data (map / Kp / ceiling)"
    return "UNATTRIBUTED"


def last_build(a):
    for nm, img, prev in (("V295", v295, v294), ("V294", v294, v293), ("V293", v293, v282)):
        if img[a] != prev[a]:
            return nm
    return "<=V282"


diff = [a for a in range(0x13000, 0x100000) if stock[a] != v295[a]]
cnt = Counter(); lines = []
for a in diff:
    r, lb = row(a), last_build(a)
    cnt[(r, lb)] += 1
    lines.append(f"0x{a:05X}  stock {stock[a]:02x}  V295 {v295[a]:02x}  last set by {lb:6s}  {r}")
open("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/adversarial/out/advC_4_stock_v295_every_offset.txt",
     "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"stock -> V295 differing bytes in [0x13000,0x100000): {len(diff)}")
for (r, lb), n in sorted(cnt.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    print(f"  {lb:6s}  {n:5d}  {r}")
un = [l for l in lines if l.endswith("UNATTRIBUTED")]
print(f"UNATTRIBUTED: {len(un)}", un[:20])
