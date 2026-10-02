# us04 -- who writes gp-0x680a (the alternate-mode flag that routes 0x29A70 -> 0x2A0C6, S = -sign(r26)*LERP(|r26|>>5))?
# Methods: (1) 4-byte gp disp16 stores to any address overlapping 0x680a (st.b -0x680a, st.h -0x680a/-0x680b-ish, st.w -0x680c..-0x680a)
# (2) 6-byte extended-displacement form (V850E2 'ld/st disp23'): hw1 = 0000 0111 1xx0 reg1 pattern scan with disp decode
# (3) movea -0x680a,gp,rX / addi forms that build the address for register-indirect access
# Positive control: gp-0x67a2 st.b (3 hits found in us02), and the same methods on gp-0x6803 (4 st.b writers in us02).
import struct
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
       "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
b = open(IMG, "rb").read()
def hw(a): return b[a] | b[a+1] << 8
def stores_overlapping(target):
    out = []
    for a in range(0x13000, 0xC0000, 2):
        h1 = hw(a)
        if (h1 & 0x1F) != 4: continue
        op6 = (h1 >> 5) & 0x3F; h2 = hw(a+2)
        if op6 == 0x3A:                       # st.b disp16
            d = h2 - 0x10000 if h2 & 0x8000 else h2
            if d == target: out.append((a, "st.b"))
        elif op6 == 0x3B:                     # st.h / st.w
            d = (h2 & 0xFFFE); d = d - 0x10000 if d & 0x8000 else d
            w = 4 if h2 & 1 else 2
            if d <= target < d + w: out.append((a, f"st.{'w' if w==4 else 'h'} {d:#x}"))
        elif op6 in (0x20, 0x31):             # movea imm16,gp,rX (0x31) / addi (0x30) -> address formation
            pass
    return out
def addr_forms(target):
    out = []
    for a in range(0x13000, 0xC0000, 2):
        h1 = hw(a)
        if (h1 & 0x1F) != 4: continue
        op6 = (h1 >> 5) & 0x3F; h2 = hw(a+2)
        d = h2 - 0x10000 if h2 & 0x8000 else h2
        if op6 in (0x30, 0x31) and abs(d - target) <= 16:   # addi/movea imm16, gp, reg2  (near the cell: struct base)
            out.append((a, ("addi" if op6 == 0x30 else "movea") + f" {d:#x},gp,r{h1>>11}"))
    return out
def ext6(target):
    # V850E2 format XIV: ld.b/ld.bu/ld.h/ld.hu/ld.w/st.b/st.h/st.w disp23[reg1]: hw1 = 00000 111 10/01... hard to pin;
    # brute: any 6-byte window whose hw1 low5 = gp and whose (hw3<<7 | hw2>>9) style disp equals target -- try both layouts
    out = []
    for a in range(0x13000, 0xC0000 - 6, 2):
        h1 = hw(a)
        if (h1 & 0x1F) != 4 or (h1 >> 5) & 0x3F != 0x3C and (h1 >> 5) & 0x3F != 0x3D: continue
        h2, h3 = hw(a+2), hw(a+4)
        if not (h2 & 1): continue
        sub = h2 & 0xF
        disp = ((h3 << 7) | (h2 >> 4) >> 0) if False else None
        # disp23 = hw3<<7 | (hw2>>4 & 0x7F) with bit0 from hw2? -- record raw for manual review if hw3 matches
        for d in (((h3 << 7) | ((h2 >> 4) & 0x7F)), ((h3 << 6) | ((h2 >> 5) & 0x3F)) << 1):
            dd = d - (1 << 23) if d & (1 << 22) else d
            if dd == target: out.append((a, b[a:a+6].hex()))
    return out
for nm, t in [("CONTROL gp-0x6803", -0x6803), ("CONTROL gp-0x67a2", -0x67a2), ("gp-0x680a", -0x680a)]:
    print(nm, "stores:", [(hex(a), k) for a, k in stores_overlapping(t)])
    print("   addr-forms (+-16):", [(hex(a), k) for a, k in addr_forms(t)][:12])
    print("   ext6:", [(hex(a), k) for a, k in ext6(t)][:12])
