# us02 -- raw LE scan of gp-relative (r4) loads/stores to named cells in the V298 image, both encodings.
# Positive controls: cells the decompile of V294_lkas_rate_pid visibly writes/reads.
import struct, sys
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
       "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
b = open(IMG, "rb").read()
N = 0xC0000
# Format VII 4-byte: hw1 = reg2<<11 | op6<<5 | reg1 ; hw2 = disp16 (bit0 = sub-op for .h/.w/.hu)
OPS = {0x38: "ld.b", 0x39: "ld.h/ld.w", 0x3A: "st.b", 0x3B: "st.h/st.w", 0x3C: "ld.bu(e)/jr", 0x3D: "ld.bu(o)/jr", 0x3F: "ld.hu/mul"}
def scan(disp):
    d16 = disp & 0xFFFF
    hits = []
    for a in range(0x13000, N - 4, 2):
        hw1 = b[a] | b[a+1] << 8
        hw2 = b[a+2] | b[a+3] << 8
        if (hw1 & 0x1F) != 4:
            continue
        op6 = (hw1 >> 5) & 0x3F
        r2 = hw1 >> 11
        if op6 in (0x38, 0x3A) and hw2 == d16:
            hits.append((a, OPS[op6], r2))
        elif op6 in (0x39, 0x3B) and (hw2 & 0xFFFE) == (d16 & 0xFFFE) and (d16 & 1) == 0:
            hits.append((a, OPS[op6] + ("[.w]" if hw2 & 1 else "[.h]"), r2))
        elif op6 == 0x3F and (hw2 & 1) and (hw2 & 0xFFFE) == (d16 & 0xFFFE):
            hits.append((a, "ld.hu", r2))
        elif op6 in (0x3C, 0x3D) and (hw2 & 1):   # ld.bu: disp bit0 in hw1 bit5 (op6 parity)
            dd = (hw2 & 0xFFFE) | (op6 & 1)
            if dd == d16 and r2 != 0:
                hits.append((a, "ld.bu", r2))
    # 6-byte extended form: hw1 = 0000 0111 10xx reg1 family (V850E2 ld/st disp23) -- check sub-opcode bytes
    for a in range(0x13000, N - 6, 2):
        hw1 = b[a] | b[a+1] << 8
        if (hw1 & 0xFFE0) in (0x0780, 0x07A0) and (hw1 & 0x1F) == 4:
            hw2 = b[a+2] | b[a+3] << 8; hw3 = b[a+4] | b[a+5] << 8
            disp = ((hw3 << 7) | (hw2 >> 9)) if False else None
            hits.append((a, f"EXT6? {b[a:a+6].hex()}", (hw2 >> 11)))
    return hits
for nm, disp in [("CONTROL st.b gp-0x67a2", -0x67a2), ("CONTROL ld.h gp-0x69ae", -0x69ae), ("pol gp-0x6752", -0x6752),
                 ("gp-0x6803", -0x6803), ("gp-0x4f68", -0x4f68), ("gp-0x4f60", -0x4f60), ("gp-0x6a5e", -0x6a5e),
                 ("gp-0x6abe", -0x6abe), ("gp-0x6a00", -0x6a00), ("gp-0x69ae", -0x69ae)]:
    h = [x for x in scan(disp) if not x[1].startswith("EXT6")]
    print(f"{nm:24s} {len(h):3d} hits:", ", ".join(f"0x{a:05X} {k} r{r}" for a, k, r in h))
