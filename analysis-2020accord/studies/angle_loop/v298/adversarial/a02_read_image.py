# -*- coding: utf-8 -*-
"""ADV-ARITHMETIC V298: read the cave G-table and the cal cells straight from the BUILT image (second method = Python
LE byte scan).  No build-script constants used."""
import struct, hashlib
from pathlib import Path
IMG = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
           "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
img = IMG.read_bytes()
assert hashlib.sha256(img).hexdigest() == "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
s16 = lambda a: struct.unpack_from("<h", img, a)[0]
u32 = lambda a: struct.unpack_from("<I", img, a)[0]
# GB-P table at 0xC4CDA: knot triples (X u16, S s16, G s16)? design says (X, G, S). Verify structure from the walk.
# walk: ld.hu 0x0 (X), ld.h 0x4 (S slope), ld.hu 0x2 (G). So layout per 6B row = [X u16][G u16][S s16].
print("GB-P table @0xC4CDA (X, G, S):")
rows=[]
for i in range(7):
    base = 0xC4CDA + 6*i
    X=u16(base); G=u16(base+2); S=s16(base+4)
    rows.append((X,G,S)); print(f"  row{i}: X={X} G={G} S={S}   bytes {img[base:base+6].hex()}")
print("cals:")
for name,a,fmt in [("a 0xC63E8",0xC63E8,'u16'),("b 0xC63EA",0xC63EA,'u16'),("C 0xC62E6",0xC62E6,'u16'),
                   ("DB 0xC62E4",0xC62E4,'u16'),("Ki 0xC63E6",0xC63E6,'u16'),("ICL 0xC61BA",0xC61BA,'u16'),
                   ("DCL 0xC61B6",0xC61B6,'u16'),("PCL 0xC61BC",0xC61BC,'u16'),("SCL 0xC61BE",0xC61BE,'u16'),
                   ("OCL 0xC61B4",0xC61B4,'u16'),("fwd 0x7CD0(tp)",0xBF000+0x7CD0,'s16'),
                   ("KpY 0xE5384",0xE5384,'u16'),("KdY 0xE5126",0xE5126,'u16')]:
    v = u16(a) if fmt=='u16' else s16(a)
    print(f"  {name} = {v}")
# version string
print("version @0x13100:", img[0x13100:0x13120])
