"""ADV interlocks-gates V298: independent full diff V298 vs V295 over [0x13000,0x100000), grouped into runs.
Re-derives from the IMAGES only. python advig_diff.py"""
import hashlib
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V298 = FW + "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
STOCK = FW + "stock_fw_dump/code.bin"
a = open(V295, "rb").read(); b = open(V298, "rb").read(); s = open(STOCK, "rb").read()
print("V295", hashlib.sha256(a).hexdigest()); print("V298", hashlib.sha256(b).hexdigest()); print("stock", hashlib.sha256(s).hexdigest())
print("len", len(a), len(b), len(s))
d = [i for i in range(0x13000, 0x100000) if a[i] != b[i]]
print("diff bytes", len(d))
runs = []
for i in d:
    if runs and i - runs[-1][1] <= 4: runs[-1][1] = i
    else: runs.append([i, i])
for r0, r1 in runs:
    n = r1 - r0 + 1
    print(f"0x{r0:05X}..0x{r1:05X} ({n:3d}B)  V295 {a[r0:r1+1][:24].hex()}  V298 {b[r0:r1+1][:24].hex()}")
# cave region: verify V295 had 0xFF there
print("V295 cave region 0xC4C00..0xC4D04 all FF:", all(x == 0xFF for x in a[0xC4C00:0xC4D04]))
print("V298 bytes after cave 0xC4D04..0xC4D40:", b[0xC4D04:0xC4D40].hex())
# where does the free FF region end / main block CRC at 0xC4FFC
print("V298 0xC4FF0..0xC5000:", b[0xC4FF0:0xC5000].hex())
# cumulative vs stock
ds = sum(1 for i in range(0x13000, 0x100000) if s[i] != b[i]); ds5 = sum(1 for i in range(0x13000, 0x100000) if s[i] != a[i])
print("cumulative vs stock: V298", ds, "V295", ds5)
