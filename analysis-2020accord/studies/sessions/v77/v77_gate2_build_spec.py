"""v77 GATE 2 -- the exact byte spec for the recommended surface. SPEC ONLY -- builds nothing.

Recommendation V77-a:  keep V75's FactorC Y[0] (the plateau HEIGHT, which sets large-amplitude
damping) and revert V75's FactorE X[1] (the relay ENTRY RATE, which sets small-signal gain).
That is `LEVERS = {"CY0": True, "EX1": False}` in builds/v50_v79/build_v75_tva.py -- a FLAG, not a rewrite.

This script enumerates, per engaged mode, exactly which halfwords differ between the V75 image on
the car and the recommended surface, and asserts the disengaged column is untouched.
"""
import struct
from pathlib import Path

ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord")
STOCK = (ROOT / "stock_fw_dump" / "code.bin").read_bytes()
V74 = (ROOT / "_v74_engagedcols_x0_12_addonly_plain_image.bin").read_bytes()
V75 = (ROOT / "_v75_CY0.566-EX1.200_magprobe_plain_image.bin").read_bytes()

FACTOR_C_PTRS, FACTOR_E_PTRS = 0xC9E9C, 0xC9F84
FRICTION_PTRS = 0xCBE74
ENGAGED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
X_OFF, Y_OFF = 0x02, 0x0A
TARGET_E_X1 = 400            # V74's value -- the ONLY cell V77-a moves


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def rec(b, addr, n=4):
    return ([s16(b, addr + X_OFF + 2 * i) for i in range(n)],
            [s16(b, addr + Y_OFF + 2 * i) for i in range(n)])


print("=" * 108)
print("V77-a BUILD SPEC  --  base image = V75 (the one on the car).  ONE cell per engaged mode.")
print("  FactorE X[1] : 200 -> 400   (record + 0x04)   RULE 7 class: MODE-INDEXED")
print("  everything else in V75 CARRIED UNCHANGED, including FactorC Y[0] = 566 and the cave.")
print("=" * 108)
print(f"{'mode':>5s} {'FactorE rec':>12s} {'addr X[1]':>11s} {'stock':>6s} {'V74':>6s} {'V75':>6s}"
      f" {'V77-a':>6s} {'delta':>7s}   {'FactorC Y[0] (carried)':>24s}")
total = 0
for m in ENGAGED:
    pe = u32(V75, FACTOR_E_PTRS + 4 * m)
    pc = u32(V75, FACTOR_C_PTRS + 4 * m)
    a = pe + X_OFF + 2
    st, v4, v5 = s16(STOCK, a), s16(V74, a), s16(V75, a)
    cy0 = s16(V75, pc + Y_OFF)
    new = TARGET_E_X1 if v5 != TARGET_E_X1 else v5
    # the honest rule: restore that mode's OWN V74 value, which is what EX1=False produces
    new = v4
    if new != v5:
        total += 1
    print(f"{m:5d} {pe:#12x} {a:#11x} {st:6d} {v4:6d} {v5:6d} {new:6d} {new-v5:+7d}"
          f"   {cy0:24d}")
print(f"\n  cells changed: {total} of {len(ENGAGED)} engaged modes  ({2*total} bytes + per-block CRC)")

print()
print("  DISENGAGED column -- must stay byte-stock (V77-a writes NOTHING here):")
ok = True
for m in DISENGAGED:
    pe = u32(V75, FACTOR_E_PTRS + 4 * m)
    pc = u32(V75, FACTOR_C_PTRS + 4 * m)
    same = (V75[pe:pe + 0x14] == STOCK[pe:pe + 0x14] and V75[pc:pc + 0x14] == STOCK[pc:pc + 0x14])
    ok &= same
    if not same:
        print(f"    !! mode {m} is NOT byte-stock on V75")
print(f"    all {len(DISENGAGED)} disengaged modes byte-stock on V75: {ok}"
      "   (V77-a inherits this untouched)")

print()
print("=" * 108)
print("THE LIVE MODE (26) -- the surface V77-a actually delivers, vs both flown builds")
print("=" * 108)
for nm, img in (("stock", STOCK), ("V74", V74), ("V75", V75)):
    pc = u32(img, FACTOR_C_PTRS + 4 * 26)
    pe = u32(img, FACTOR_E_PTRS + 4 * 26)
    print(f"  {nm:6s} C {rec(img, pc)}   E {rec(img, pe)}")
pc = u32(V75, FACTOR_C_PTRS + 4 * 26)
pe = u32(V75, FACTOR_E_PTRS + 4 * 26)
CX_, CY_ = rec(V75, pc)
EX_, EY_ = rec(V75, pe)
EX_[1] = 400
print(f"  V77-a  C ({CX_}, {CY_})   E ({EX_}, {EY_})")

print()
print("=" * 108)
print("FRICTION REVERT CANDIDATES -- addresses and current values (SPEC ONLY)")
print("=" * 108)
for m in (24, 26):
    pf = u32(V75, FRICTION_PTRS + 4 * m)
    n = struct.unpack_from("<H", V75, pf)[0]
    X = [s16(V75, pf + 0x02 + 2 * i) for i in range(n)]
    Ys = [s16(STOCK, pf + 0x02 + 2 * n + 2 * i) for i in range(n)]
    Yv = [s16(V75, pf + 0x02 + 2 * n + 2 * i) for i in range(n)]
    tag = "ENGAGED (live)" if m == 26 else "MANUAL (live)"
    print(f"  mode {m:2d} {tag:15s} rec @{pf:#08x}  n={n}  X={X}")
    print(f"        Y addr {pf + 0x02 + 2*n:#08x}.. stock={Ys}  V74/V75={Yv}"
          f"  ratio={[round(a/b,3) if b else None for a,b in zip(Yv,Ys)]}")
    print(f"        Q15 read: stock {[round(y/32768,4) for y in Ys]}"
          f"  ->  V74/V75 {[round(y/32768,4) for y in Yv]}")
print()
print(f"  0xC407E  stock {struct.unpack_from('<H', STOCK, 0xC407E)[0]}"
      f"  ->  V73+ {struct.unpack_from('<H', V75, 0xC407E)[0]}   (flat cal, NOT mode-indexed)")
print(f"  0xC63A0  stock {struct.unpack_from('<H', STOCK, 0xC63A0)[0]}"
      f"  ->  V72+ {struct.unpack_from('<H', V75, 0xC63A0)[0]}   (flat cal, NOT mode-indexed)")
