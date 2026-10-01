# -*- coding: utf-8 -*-
"""ds_gate1.py -- GATE 1 census (Python, raw LE scan) for the cave RAM words the D-structure candidates write
(gp-0x6c44 for D1b / D1c, gp-0x6c40 for D2b / D2c) and for the cells the caves READ.  Positive-controlled.
Forms scanned over [0x13000, 0xC0000) U [0xC4000, 0xC5000): Format VII 4-byte gp-relative loads/stores of every width
(ld.b/ld.h/ld.w/ld.bu/ld.hu, st.b/st.h/st.w; the ld.bu odd/even hw1 parity and the hw2|1 forms), the 6-byte extended
ld/st forms (hw1 = 0x0780|reg1 family, hw2 bit 0 / sub-opcode, 32-bit disp in hw2..hw3), the Format VIII bit ops
(set1/clr1/not1/tst1 disp16[gp]), the absolute address as an LE32 literal, and movea/addi disp,gp,reg (address taken).
Every access whose byte range OVERLAPS the target word is reported.  ANALYSIS ONLY."""
import glob, struct, sys

R = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
B = open(glob.glob(R + "_v295_*plain_image.bin")[0], "rb").read()
GP = 0xFEDF8000
u16 = lambda a: struct.unpack_from("<H", B, a)[0]
RANGES = [(0x13000, 0xC0000), (0xC4000, 0xC5000)]


def s16(x):
    return x - 0x10000 if x & 0x8000 else x


def scan():
    hits = []
    for lo, hi in RANGES:
        for pc in range(lo, hi - 4, 2):
            h1, h2 = u16(pc), u16(pc + 2)
            op6 = (h1 >> 5) & 0x3F
            reg1 = h1 & 0x1F
            if reg1 != 4:
                pass
            # Format VII 4-byte loads/stores, base gp
            if reg1 == 4:
                if op6 == 0x38:   # ld.b
                    hits.append((pc, "ld.b", s16(h2), 1))
                elif op6 == 0x39:  # ld.h / ld.w
                    hits.append((pc, "ld.w" if h2 & 1 else "ld.h", s16(h2 & 0xFFFE), 4 if h2 & 1 else 2))
                elif op6 == 0x3A:  # st.b
                    hits.append((pc, "st.b", s16(h2), 1))
                elif op6 == 0x3B:  # st.h / st.w
                    hits.append((pc, "st.w" if h2 & 1 else "st.h", s16(h2 & 0xFFFE), 4 if h2 & 1 else 2))
                elif op6 in (0x3C, 0x3D) and (h2 & 1):   # ld.bu (disp bit0 in hw1 bit 5): hw2[0] = 1 required
                    disp = s16((h2 & 0xFFFE) | ((h1 >> 5) & 1))
                    hits.append((pc, "ld.bu", disp, 1))
                elif op6 == 0x3F and (h2 & 1) and (h1 >> 11):  # ld.hu
                    hits.append((pc, "ld.hu", s16(h2 & 0xFFFE), 2))
                elif op6 == 0x3E:  # Format VIII bit ops: set1/not1/clr1/tst1 bit#3, disp16[reg1]
                    hits.append((pc, "bitop", s16(h2), 1))
                elif op6 in (0x31, 0x30):   # movea / addi disp, gp, reg -> address taken
                    hits.append((pc, "movea/addi", s16(h2), 0))
            # 6-byte extended form: hw1 = 0000 0111 10 / 11 + reg1 (ld.b/ld.bu/ld.h/ld.hu/ld.w and st.*), base gp
            if (h1 & 0xFFE0) in (0x0780, 0x07A0) and reg1 == 4 and pc + 6 <= hi:
                # the kit's decode (build_v292_tva.scan_rel, controlled there on gp-0x6752 @0x48E56..0x48E88):
                w2 = u16(pc + 4)
                disp = (s16(w2) << 7) | ((h2 >> 4) & 0x7F)
                hits.append((pc, "ld/st(6B)", disp, 4))
    return hits


def overlaps(hits, target, width):
    out = []
    for pc, kind, disp, w in hits:
        a0, a1 = disp, disp + max(w, 1)
        if a0 < target + width and target < a1:
            out.append((hex(pc), kind, hex(disp & 0xFFFFFFFF) if disp < 0 else hex(disp), w))
    return out


if __name__ == "__main__":
    hits = scan()
    print(f"{len(hits)} gp-relative candidate sites scanned")
    for name, t, w, expect in (("CONTROL gp-0x3d30 (fb state: 0x28F7C ld.w, 0x28FA8 st.w)", -0x3D30, 4, 2),
                               ("CONTROL gp-0x6cf8 (E_prev: 0x29E5E ld.w, 0x2A18C st.w + the twin)", -0x6CF8, 4, None),
                               ("CONTROL gp-0x6abe (FUN_00041464 writers, FUN_0003f776 reader, ...)", -0x6ABE, 2, None),
                               ("TARGET gp-0x6c44 (D1b d_prev / D1c lp)", -0x6C44, 4, 0),
                               ("TARGET gp-0x6c40 (D2b / D2c lead state w)", -0x6C40, 4, 0),
                               ("neighbour gp-0x6c3c", -0x6C3C, 4, 0), ("neighbour gp-0x6c48", -0x6C48, 4, None),
                               ("READ gp-0x6cc4 (motor accumulator)", -0x6CC4, 4, None),
                               ("CONTROL 6-byte form: gp-0x6752 (0x48E56/68/76/88 per the V292 build)", -0x6752, 1, None)):
        o = overlaps(hits, t, w)
        print(f"{name}: {len(o)} overlapping accesses" + (f"  (expected {expect})" if expect is not None else ""))
        for x in o[:20]:
            print("    ", x)
    lit = [hex(i) for a in (GP - 0x6C44, GP - 0x6C40) for i in range(0x13000, 0xC0000, 2)
           if struct.unpack_from("<I", B, i)[0] & 0xFFFFFFFC == (a & 0xFFFFFFFF) & 0xFFFFFFFC]
    print("absolute-address LE32 literals of 0xFEDF13BC / 0xFEDF13C0:", lit)
