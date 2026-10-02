# us01 -- UNIT/SCALE adversary on V298: raw LE byte reads from the BUILT image (and stock, V295 for contrast).
# Every number printed here is read from the image file; nothing is taken from the build script.
import hashlib, struct, os, sys
FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
A = FW + "/analysis-2020accord/"
V298 = A + "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin"
V295 = A + ("_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0"
            "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
STOCK = A + "stock_fw_dump/code.bin"
img = open(V298, "rb").read(); v295 = open(V295, "rb").read(); stk = open(STOCK, "rb").read()
print("V298 sha", hashlib.sha256(img).hexdigest())
print("V295 sha", hashlib.sha256(v295).hexdigest())
print("STOCK sha", hashlib.sha256(stk).hexdigest())
h = lambda b, a, n: b[a:a+n].hex(" ")
u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]
print("\n== in-place sites: stock | V295 | V298")
for a, n in [(0x28F4C,4),(0x28FA4,2),(0x29A50,4),(0x29A56,2),(0x29D6A,4),(0x29D76,4),(0x29EE0,4),(0x13100,14)]:
    print(f"  0x{a:05X}: {h(stk,a,n)} | {h(v295,a,n)} | {h(img,a,n)}")
print("  F181 string V298:", img[0x13100:0x13110])
print("\n== cals (u16 / s16): stock | V295 | V298")
for a, nm in [(0xC63E8,'a'),(0xC63EA,'b'),(0xC62E6,'C'),(0xC62E4,'DB'),(0xC63E6,'Ki'),(0xC61BA,'ICL'),(0xC61B6,'DCL'),
              (0xC61B8,'?C61B8'),(0xC61BC,'?C61BC'),(0xC61B4,'?C61B4')]:
    print(f"  {nm:7s} 0x{a:05X}: {u16(stk,a):6d}/{s16(stk,a):6d} | {u16(v295,a):6d}/{s16(v295,a):6d} | {u16(img,a):6d}/{s16(img,a):6d}")
print("\n== Kp record around 0xE5384 (V298)")
for base in (0xE5370, 0xE5110):
    print("  ", hex(base), [u16(img, base+2*i) for i in range(16)])
    print("   stock", [u16(stk, base+2*i) for i in range(16)])
print("\n== fade records 0xE54FC / 0xE564C (V298 / V295 / stock)")
for a in (0xE54FC, 0xE564C, 0xE55A4, 0xE56F4):
    for nm, b in (("V298", img), ("V295", v295), ("stk", stk)):
        print(f"  0x{a:05X} {nm}: n={u16(b,a)} X={[u16(b,a+2+2*i) for i in range(6)]} Y={[u16(b,a+14+2*i) for i in range(6)]}")
print("\n== cave 0xC4C00..0xC4D10 (V298)")
for a in range(0xC4C00, 0xC4D10, 16):
    print(f"  0x{a:05X}: {h(img,a,16)}")
print("  V295 cave region all FF:", all(x == 0xFF for x in v295[0xC4C00:0xC4D04]))
print("\n== diff V298 vs V295 over [0x13000,0x100000)")
d = [a for a in range(0x13000, 0x100000) if img[a] != v295[a]]
runs = []
for a in d:
    if runs and a == runs[-1][1] + 1: runs[-1][1] = a
    else: runs.append([a, a])
for s, e in runs: print(f"  [0x{s:05X}..0x{e:05X}] {e-s+1} B")
print("  total", len(d))
