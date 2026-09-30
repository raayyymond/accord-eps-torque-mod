# -*- coding: utf-8 -*-
"""adv3_lineage.py -- the fb former's cells down EVERY 1 MB image on disk in ../accord-firmwares (not the designer's list):
a 0xC63E8 (s16), b 0xC63EA (u16), C 0xC62E6, the operand opcode at 0x28FA4 (add 0x0E / subr 0x0C), the shl immediate at
0x29D76, and whether the code bytes at 0x28F86..0x28FBE are V294's.  Groups images by (op, shl, a, b, C).
Also: every image whose DIFFERENCE operand is live (subr), and every b value ever carried, by operand."""
import glob
import hashlib
import os
from collections import defaultdict

ROOT = "C:/Users/dudei/Desktop/Projects/accord-firmwares"
V294 = open(ROOT + "/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT."
            "960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
ref_code = V294[0x28F86:0x28FBE]
files = sorted(set(glob.glob(ROOT + "/**/*.bin", recursive=True)))
rows = []
seen = {}
for f in files:
    b = open(f, "rb").read()
    if len(b) != 0x100000:
        continue
    h = hashlib.sha256(b).hexdigest()
    if h in seen:
        continue
    seen[h] = f
    rd = lambda a, s=False: int.from_bytes(b[a:a + 2], "little", signed=s)  # noqa: E731
    op = (rd(0x28FA4) >> 5) & 0x3F
    sh = rd(0x29D76)
    shl = sh & 0x1F if ((sh >> 5) & 0x3F) == 0x16 else None
    rows.append(dict(f=os.path.basename(f), op={0x0E: "add", 0x0C: "subr"}.get(op, "op%02x" % op), shl=shl,
                     a=rd(0xC63E8, True), b=rd(0xC63EA), C=rd(0xC62E6), code_ok=(b[0x28F86:0x28FBE] == ref_code) or None))
print("%d distinct 1 MB images (by sha256) under %s" % (len(rows), ROOT))
grp = defaultdict(list)
for r in rows:
    grp[(r["op"], r["shl"], r["a"], r["b"], r["C"])].append(r["f"])
print("\n(op @0x28FA4, shl @0x29D76, a, b, C) -> count : examples")
for k in sorted(grp, key=lambda k: -len(grp[k])):
    ex = [x[:70] for x in grp[k][:3]]
    print("  %-40s %4d : %s" % (k, len(grp[k]), ex))
print("\nimages with the DIFFERENCE operand (subr at 0x28FA4):")
for r in rows:
    if r["op"] == "subr":
        print("   ", r)
print("\nevery b value by operand:", {op: sorted({r["b"] for r in rows if r["op"] == op}) for op in ("add", "subr")})
print("b = 964 on any image: %s" % any(r["b"] == 964 for r in rows))
