"""Dump FactorC / FactorE / ceiling LERP records for every mode, stock vs V74 vs V75.
Crux check: did V75's FactorE X[1] 400->200 break X monotonicity anywhere?
A non-increasing X pair => zero denominator in the LERP => divide/undefined behaviour.
"""
import os, struct
R = r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord"
IMG = {
 "stock": os.path.join(R, "stock_fw_dump", "code.bin"),
 "V74":   os.path.join(R, "_v74_engagedcols_x0_12_addonly_plain_image.bin"),
 "V75":   os.path.join(R, "_v75_CY0.566-EX1.200_magprobe_plain_image.bin"),
}
B = {k: open(v,'rb').read() for k,v in IMG.items()}
BASE = 0x0  # images are flat, address == offset (verified below by anchor)

def u16(b,a): return struct.unpack_from('<H', b, a)[0]
def s16(b,a): return struct.unpack_from('<h', b, a)[0]
def u32(b,a): return struct.unpack_from('<I', b, a)[0]

PTR = {"FactorC":0xC9E9C, "FactorE":0xC9F84, "ceiling":0xC77A0, "friction":0xCBE74}

def record(b, addr):
    n = u16(b, addr)
    if n == 0 or n > 8: return (n, None, None)
    X = [s16(b, addr+2+2*i) for i in range(n)]
    Y = [s16(b, addr+2+2*n+2*i) for i in range(n)]
    return (n, X, Y)

ENGAGED = [2,3,5,11,14,15,17,23,26,27,29,32,33]
DISENG  = [0,1,4,10,12,13,16,22,24,25,28,30,31]

print("anchor check: 0xCBE74[10*4] ->", hex(u32(B['stock'], 0xCBE74+10*4)), "(expect 0xD2A44)")
print()
for name in ("FactorC","FactorE"):
    pa = PTR[name]
    print("="*100); print(name, "pointer array @", hex(pa)); print("="*100)
    for m in range(34):
        ptrs = {k: u32(B[k], pa+m*4) for k in B}
        recs = {k: record(B[k], ptrs[k]) for k in B}
        tag = "ENG" if m in ENGAGED else ("dis" if m in DISENG else "   ")
        changed = recs['V75'] != recs['stock']
        if not changed and m not in ENGAGED: continue
        print(f"mode {m:2d} {tag} rec@{ptrs['stock']:#x}")
        for k in ("stock","V74","V75"):
            n,X,Y = recs[k]
            if X is None: print(f"   {k:5s} n={n} <unparsed>"); continue
            mono = all(X[i] < X[i+1] for i in range(len(X)-1))
            dup  = [i for i in range(len(X)-1) if X[i] == X[i+1]]
            flag = "" if mono else ("  <<<< NON-MONOTONIC" + (f" DUP at idx {dup}" if dup else " DECREASING"))
            print(f"   {k:5s} n={n} X={X} Y={Y}{flag}")
        print()
