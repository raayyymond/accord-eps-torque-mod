import struct, hashlib
from pathlib import Path
IMG = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
           "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
img = IMG.read_bytes()
assert hashlib.sha256(img).hexdigest() == "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
u32 = lambda a: struct.unpack_from("<I", img, a)[0]
def table(ptrbase, sel=7):
    p = u32(ptrbase + 4*sel)            # firmware: iVar23 = selector*4, selector=7
    n = u16(p)
    X = [u16(p+2+2*i) for i in range(n)]
    Y = [u16(p+2+2*n+2*i) for i in range(n)]
    return p, n, X, Y
pairs = [("fadeA  0xCBB54", 0xCBB54, "fadeA2 0xCBC34", 0xCBC34),
         ("fadeB  0xCBAE4", 0xCBAE4, "fadeB2 0xCBBC4", 0xCBBC4)]
for na, ba, nb, bb in pairs:
    pa,n,Xa,Ya = table(ba); pb,n2,Xb,Yb = table(bb)
    print(f"{na} @{pa:#x} n={n} X={Xa} Y={Ya}")
    print(f"{nb} @{pb:#x} n={n2} X={Xb} Y={Yb}")
    print(f"   EQUAL (X,Y)? {(Xa,Ya)==(Xb,Yb)}")
    print()
# cross-check vs the scorer's loaded CAL fade values
import sys, os
AL = Path(__file__).resolve().parents[2]
for p in (AL, AL/"panel2", AL/"refute_c2r2_nonlinear"): sys.path.insert(0,str(p))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
import score_time as ST
print("scorer CAL fadeA :", [list(a) for a in ST.CAL["fadeA"]])
print("scorer CAL fadeA2:", [list(a) for a in ST.CAL["fadeA2"]])
print("scorer CAL fadeB :", [list(a) for a in ST.CAL["fadeB"]])
print("scorer CAL fadeB2:", [list(a) for a in ST.CAL["fadeB2"]])
