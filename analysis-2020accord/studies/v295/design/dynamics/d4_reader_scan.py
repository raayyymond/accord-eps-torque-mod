# -*- coding: utf-8 -*-
"""d4_reader_scan.py -- lens "dynamics": the SECOND METHOD (raw Python LE scan) for the reader census of every cell this
lens may propose: output lag 0xC63EC / 0xC63EE, fb pole 0xC63E8, Kd bank 0xCB7D4, D clamp 0xC61B6, sum clamp 0xC61BE.
tp = 0xBF000 -> tp-relative displacement = cell - 0xBF000.  Every even-offset halfword in the code region equal to
disp or disp|1 is reported with the preceding halfword decoded (Format VII: reg2<<11 | op<<5 | reg1); absolute LE32
references (mov imm32) are reported too.  POSITIVE CONTROLS first: 0xC63E8 (fb_a) must be found at 0x28F8A, 0xC63EA at
0x28F86, 0xC63EC at 0x2A184, the Kd bank 0xCB7D4 mov imm32 at 0x29E76 (census c2)."""
import hashlib
import os

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
IMG = FW + ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
            "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
TP = 0xBF000
OPS = {0x38: "ld.b", 0x39: "ld.h/ld.w", 0x3A: "st.b", 0x3B: "st.h/st.w", 0x3C: "ld.bu/jarl-coll", 0x3D: "ld.bu(odd)/jr-coll",
       0x3E: "ld.bu?", 0x3F: "ld.hu/mul-coll"}


def hw(b, a):
    return b[a] | (b[a + 1] << 8)


def scan(b, cell, lo=0x13000, hi=0xC0000):
    d = cell - TP
    hits = []
    for a in range(lo + 2, hi - 2, 2):
        h2 = hw(b, a)
        if h2 & 0xFFFE == d & 0xFFFE:
            h1 = hw(b, a - 2)
            op = (h1 >> 5) & 0x3F
            reg1, reg2 = h1 & 0x1F, h1 >> 11
            hits.append((a - 2, "%04x %04x" % (h1, h2), OPS.get(op, "op%02x" % op), reg1, reg2))
    absr = []
    for a in range(lo, hi - 4, 2):
        if int.from_bytes(b[a:a + 4], "little") == cell:
            absr.append(a)
    return hits, absr


def main():
    b = open(IMG, "rb").read()
    print("image sha256", hashlib.sha256(b).hexdigest())
    for cell, want in ((0xC63E8, 0x28F8A), (0xC63EA, 0x28F86), (0xC63EC, 0x2A184), (0xC63EE, 0x2A174)):
        hits, _ = scan(b, cell)
        tpl = [h for h in hits if h[3] == 5]
        print("CONTROL/TARGET 0x%X (tp+0x%X): tp-based hits %s ; expected %s -> %s" % (
            cell, cell - TP, [(hex(h[0]), h[1], h[2]) for h in tpl], hex(want),
            "FOUND" if any(h[0] == want for h in tpl) else "MISSING"))
        other = [h for h in hits if h[3] != 5]
        print("      non-tp halfword matches (not tp-relative, listed for adjudication): %d" % len(other))
    for cell, nm in ((0xC61B6, "D clamp"), (0xC61BE, "sum clamp")):
        hits, absr = scan(b, cell)
        tpl = [(hex(h[0]), h[1], h[2], "r%d" % h[4]) for h in hits if h[3] == 5]
        print("%s 0x%X: tp-based %s ; abs LE32 %s" % (nm, cell, tpl, [hex(a) for a in absr]))
    for bank, nm in ((0xCB7D4, "Kd bank"), (0xCB994, "Kp bank")):
        _, absr = scan(b, bank)
        print("%s 0x%X: absolute LE32 refs (mov imm32 operand at a-2) %s" % (nm, bank, [hex(a - 2) for a in absr]))
        rec = int.from_bytes(b[bank + 4 * 7:bank + 4 * 7 + 4], "little")
        n = hw(b, rec)
        print("   record (selector 7) at 0x%X: n %d X %s Y %s" % (rec, n, [hw(b, rec + 2 + 2 * i) for i in range(n)],
                                                                   [hw(b, rec + 2 + 2 * n + 2 * i) for i in range(n)]))
        recs = sorted(set(int.from_bytes(b[bank + 4 * i:bank + 4 * i + 4], "little") for i in range(28)))
        print("   %d distinct record pointers over the 28 variants" % len(recs))
    print("values: lag a %d  lag b %d  fb_a %d  fb_b %d  Dclamp %d  sumclamp %d" % (
        int.from_bytes(b[0xC63EC:0xC63EE], "little", signed=True), hw(b, 0xC63EE), int.from_bytes(b[0xC63E8:0xC63EA], "little", signed=True),
        hw(b, 0xC63EA), hw(b, 0xC61B6), hw(b, 0xC61BE)))


if __name__ == "__main__":
    main()
