"""v77 GATE 2 -- raw byte extraction of the base-assist damper surface, stock vs V74 vs V75.

Pure Python byte reads (LE, V850 is little-endian). No Ghidra, no r2.
Record layout (from build_v74/v75_tva.py, REC_STRIDE=0x14, REC4_X_OFF=0x02, REC4_Y_OFF=0x0A):
    [0x00:0x02] header/count      [0x02:0x0A] X[0..3] int16 LE      [0x0A:0x12] Y[0..3] int16 LE
Pointer arrays are 4-byte big/little? -- resolved empirically below against the known live record.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord")
IMGS = {
    "stock": ROOT / "stock_fw_dump" / "code.bin",
    "V74":   ROOT / "_v74_engagedcols_x0_12_addonly_plain_image.bin",
    "V75":   ROOT / "_v75_CY0.566-EX1.200_magprobe_plain_image.bin",
    "V76":   ROOT / "_v76_gate_fb_arm5244_gateprobe_plain_image.bin",
    "V72":   ROOT / "_v72_plain_image.bin",
    "V73":   ROOT / "_v73_plain_image.bin",
}

FACTOR_C_PTRS, FACTOR_E_PTRS = 0xC9E9C, 0xC9F84
FACTOR_B_PTRS, FACTOR_D_PTRS = 0xC9CCC, 0xC9DB4
FRICTION_PTR_ARRAY = 0xCBE74
CEILING_PTRS = 0xC77A0
REC_STRIDE = 0x14
X_OFF, Y_OFF = 0x02, 0x0A

LIVE_MODE = 26
MANUAL_MODE = 24
ENGAGED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)


def load(p):
    return bytearray(Path(p).read_bytes())


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec4(b, addr):
    """A 4-point record: returns (X[0..3], Y[0..3]) as signed int16 LE."""
    X = [s16(b, addr + X_OFF + 2 * i) for i in range(4)]
    Y = [s16(b, addr + Y_OFF + 2 * i) for i in range(4)]
    return X, Y


def rec_hdr(b, addr):
    return u16(b, addr)


def deref(b, ptr_array, mode):
    """Mode-indexed pointer dereference. Pointers are 4-byte LE absolute addresses."""
    return u32(b, ptr_array + 4 * mode)


def main():
    imgs = {}
    for k, p in IMGS.items():
        if p.exists():
            imgs[k] = load(p)
        else:
            print(f"  !! MISSING {k}: {p}")
    stock = imgs["stock"]

    print("=" * 100)
    print("STEP 0 -- resolve the pointer arrays against the KNOWN live-mode record addresses")
    print("  expected (from build_v75_tva.py LIVE_EXPECT): FactorC[26]=0xD77D0  FactorE[26]=0xD780C")
    print("=" * 100)
    for name, arr in (("FactorB", FACTOR_B_PTRS), ("FactorC", FACTOR_C_PTRS),
                      ("FactorD", FACTOR_D_PTRS), ("FactorE", FACTOR_E_PTRS)):
        p26 = deref(stock, arr, LIVE_MODE)
        p24 = deref(stock, arr, MANUAL_MODE)
        print(f"  {name}: ptrs@0x{arr:X}  [24]=0x{p24:X}  [26]=0x{p26:X}")
    pf26 = deref(stock, FRICTION_PTR_ARRAY, LIVE_MODE)
    pf24 = deref(stock, FRICTION_PTR_ARRAY, MANUAL_MODE)
    print(f"  friction: ptrs@0x{FRICTION_PTR_ARRAY:X}  [24]=0x{pf24:X}  [26]=0x{pf26:X}")
    pc26 = deref(stock, CEILING_PTRS, LIVE_MODE)
    print(f"  ceiling : ptrs@0x{CEILING_PTRS:X}  [26]=0x{pc26:X}")

    print()
    print("=" * 100)
    print("STEP 1 -- the LIVE (mode 26, engaged) surface, per build, raw bytes")
    print("=" * 100)
    for bname, b in imgs.items():
        pC = deref(b, FACTOR_C_PTRS, LIVE_MODE)
        pE = deref(b, FACTOR_E_PTRS, LIVE_MODE)
        pB = deref(b, FACTOR_B_PTRS, LIVE_MODE)
        pD = deref(b, FACTOR_D_PTRS, LIVE_MODE)
        pF = deref(b, FRICTION_PTR_ARRAY, LIVE_MODE)
        pCe = deref(b, CEILING_PTRS, LIVE_MODE)
        CX, CY = rec4(b, pC)
        EX, EY = rec4(b, pE)
        BX, BY = rec4(b, pB)
        DX, DY = rec4(b, pD)
        FX, FY = rec4(b, pF)
        CeX, CeY = rec4(b, pCe)
        print(f"\n-- {bname} --  (mode 26)")
        print(f"   FactorC @0x{pC:X} n={rec_hdr(b,pC)}  X={CX}  Y={CY}")
        print(f"   FactorE @0x{pE:X} n={rec_hdr(b,pE)}  X={EX}  Y={EY}")
        print(f"   FactorB @0x{pB:X} n={rec_hdr(b,pB)}  X={BX}  Y={BY}")
        print(f"   FactorD @0x{pD:X} n={rec_hdr(b,pD)}  X={DX}  Y={DY}")
        print(f"   frictn  @0x{pF:X} n={rec_hdr(b,pF)}  X={FX}  Y={FY}")
        print(f"   ceiling @0x{pCe:X} n={rec_hdr(b,pCe)}  X={CeX}  Y={CeY}")
        print(f"   raw C : {bytes(b[pC:pC+REC_STRIDE]).hex()}")
        print(f"   raw E : {bytes(b[pE:pE+REC_STRIDE]).hex()}")
        print(f"   raw F : {bytes(b[pF:pF+REC_STRIDE]).hex()}")

    print()
    print("=" * 100)
    print("STEP 2 -- the MANUAL (mode 24, disengaged) surface, per build -- must be byte-stock")
    print("=" * 100)
    for bname, b in imgs.items():
        pC = deref(b, FACTOR_C_PTRS, MANUAL_MODE)
        pE = deref(b, FACTOR_E_PTRS, MANUAL_MODE)
        pF = deref(b, FRICTION_PTR_ARRAY, MANUAL_MODE)
        CX, CY = rec4(b, pC)
        EX, EY = rec4(b, pE)
        FX, FY = rec4(b, pF)
        same = (bytes(b[pC:pC+REC_STRIDE]) == bytes(stock[pC:pC+REC_STRIDE])
                and bytes(b[pE:pE+REC_STRIDE]) == bytes(stock[pE:pE+REC_STRIDE])
                and bytes(b[pF:pF+REC_STRIDE]) == bytes(stock[pF:pF+REC_STRIDE]))
        print(f"  {bname:6s} C X={CX} Y={CY} | E X={EX} Y={EY} | F Y={FY}  byte-stock={same}")

    print()
    print("=" * 100)
    print("STEP 3 -- 0xC63A0 damper weight + neighbours (tp+0x73A0), per build")
    print("=" * 100)
    for bname, b in imgs.items():
        vals = [u16(b, 0xC63A0 + 2 * i) for i in range(6)]
        print(f"  {bname:6s} 0xC63A0..0xC63AA = {vals}   raw={bytes(b[0xC63A0:0xC63AC]).hex()}")

    print()
    print("=" * 100)
    print("STEP 4 -- 0xC407E (friction-lane cal touched by V73+)")
    print("=" * 100)
    for bname, b in imgs.items():
        print(f"  {bname:6s} 0xC407E = {u16(b,0xC407E)} (u16) / {s16(b,0xC407E)} (s16)"
              f"   ctx 0xC4078..0xC4086 = {[s16(b,0xC4078+2*i) for i in range(7)]}")


if __name__ == "__main__":
    main()
