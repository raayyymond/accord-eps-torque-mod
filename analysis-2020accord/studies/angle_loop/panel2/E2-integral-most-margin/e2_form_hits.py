# -*- coding: utf-8 -*-
r"""e2_form_hits.py -- for every instruction the E2 policy blocks ADD to P2's cave, find the same exact bytes at an
even address inside the V295 code region, so each can be decoded by Ghidra (dry run) as an encoding control.
ANALYSIS ONLY."""
import glob
from pathlib import Path
HERE = Path(__file__).resolve().parent
B = open(glob.glob("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v295_*plain_image.bin")[0], "rb").read()
FORMS = {"ld.h -0x6a00[gp],r9": "24 4f 00 96", "cmp r0,r9": "e0 49", "subr r0,r9": "80 49", "shl 4,r9": "c4 4a",
         "shl 6,r9": "c6 4a", "addi 1250,r9,r9": "09 4e e2 04", "ld.w -0x6dd0[gp],r13": "24 6f 31 92",
         "sar 10,r13": "aa 6a", "cmp r0,r16": "e0 81", "cmp r9,r13": "e9 69", "subr r0,r13": "80 69",
         "xor r16,r9": "30 49", "ld.h -0x4f60[gp],r9": "24 4f a0 b0", "movea 300,r0,r13": "20 6e 2c 01",
         "movea 2880,r0,r13": "20 6e 40 0b", "ld.w -0x6dd0[gp],r6": "24 37 31 92", "sar 13,r6": "ad 32",
         "subr r0,r6": "80 31", "cmp r0,r25": "e0 c9", "mov 0,r16": "00 82", "mov 0,r26": "00 d2", "sar 6,r6": "a6 32"}
L = []
for nm, hx in FORMS.items():
    pat = bytes.fromhex(hx.replace(" ", ""))
    hits = []
    i = B.find(pat, 0x13000)
    while i != -1 and i < 0xB0000 and len(hits) < 3:
        if i % 2 == 0:
            hits.append(hex(i))
        i = B.find(pat, i + 1)
    L.append(f"{nm:24s} {hx:12s} first even hits in V295 code: {hits}")
print("\n".join(L))
(HERE / "e2_form_hits_out.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
