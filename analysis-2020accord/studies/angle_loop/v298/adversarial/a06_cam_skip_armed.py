# -*- coding: utf-8 -*-
"""ADV-ARITHMETIC V298 -- (a) camera path (r25=0): I decays, no bias, no torque; (b) op-skip path (invalid rate):
reaches 0x2A164, I8:=0, sentinel set, output decays, no NEW RAM cell, no new torque; (c) armed==un-armed delivered
surface (prove the fade neutralization in a RUNNING loop with the V298 image fadeB2, not just static tables)."""
import sys, struct, hashlib, os
from pathlib import Path
HERE = Path(__file__).resolve()
AL = HERE.parents[2]
for p in (AL, AL / "panel2", AL / "refute_c2r2_nonlinear"):
    sys.path.insert(0, str(p))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np
import score_time as ST

M32 = 0xFFFFFFFF
def s32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v
def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)

IMG = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
           "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
img = IMG.read_bytes()
assert hashlib.sha256(img).hexdigest() == "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
ICL = u16(0xC61BA); icl = ((ICL & 0xFFFF) << 10) >> 3
KI = u16(0xC63E6)

# ---- (a) camera path: iterate the I decay from an I at its clamp, both signs -----------------------------
print("== (a) CAMERA PATH (r25=0): E'=0, op=0, e5 = -(I8>>6) ; I accumulator decay ==")
for sign in (+1, -1):
    I = sign * icl                     # start at the I clamp
    I8 = s32(I << 3)
    seq = []
    for t in range(60):
        e5 = s32(-(s32(I8) >> 6))       # cave CAM r6
        exc = e5                        # DB 0
        inc = s32(s32(exc * KI) >> 3)
        I = clamp(s32((s32(I8) >> 3) + inc), -icl, icl)
        I8 = s32(I << 3)
        seq.append(I >> 7)              # the term that enters S
    print(f"  start I>>7={sign*icl>>7:+d} -> after 10:{seq[9]:+d} 20:{seq[19]:+d} 40:{seq[39]:+d} 60:{seq[59]:+d}"
          f"  monotone|decay->0? {abs(seq[59])<=abs(seq[0]) and abs(seq[59])<=2}")

# ---- (b) op-skip epilogue 0x2A164: transcribe the stores, confirm no NEW torque path --------------------
print("\n== (b) OP-SKIP PATH (invalid rate -> jr 0x2A164) ==")
print("  epilogue stores (from the image listing): r24=0 -> st.w -0x6dd0 (I8:=0) ; r16=0x7fffffff -> st.w -0x6cf8"
      " (Eprev sentinel) ; r12=0 feeds the output-lag Sc input (mul r7,r12 -> 0) => Sc-equivalent = 0.")
print("  cells written on skip: -0x6b2e -0x6b32 -0x6cf8 -0x6dd0 -0x6b36 -0x6b34 -0x3d3c -0x6b30 -0x697e -0x697c"
      " -0x6b38 -0x6b3c -0x67a2/-0x67a3/-0x67a7  == Honda's own non-run epilogue set (NO new cave cell).")
# numeric: on skip the lane output = pure decay of the previous output (olag pole), no injected S.
# model the output lag with Sc=0 from a nonzero olag and show it decays toward 0.
oa, ob = u16(0xBF000 + 0x73EC), u16(0xBF000 + 0x73EE)   # tp cals; oa signed
oa = oa - 0x10000 if oa & 0x8000 else oa
olag = 30000
dec = []
for t in range(40):
    t1 = s32(0 * ob) >> 10                 # Sc = 0 on skip
    t2 = s32(oa * olag) >> 10
    o_new = s32(t2 + t1)
    y = s32(olag + o_new) >> 5
    olag = o_new
    dec.append(y)
print(f"  output with Sc=0 from olag=30000 : y[0]={dec[0]} y[5]={dec[5]} y[20]={dec[20]} y[39]={dec[39]}"
      f"  (oa={oa}, ob={ob}) decays->0? {abs(dec[39])<=abs(dec[0])}")

# ---- (c) armed == un-armed delivered surface, in a running loop, with the V298 image fadeB2 --------------
print("\n== (c) ARMED vs UN-ARMED delivered surface (V298 image fadeB2) ==")
rows = tuple((u16(0xC4CDA + 6 * i), u16(0xC4CDA + 6 * i + 2),
              struct.unpack_from("<h", img, 0xC4CDA + 6 * i + 4)[0]) for i in range(7))
# read the V298 image's own fadeB2 (base 0xCBBC4, sel 7) and patch the scorer CAL to it (scorer default = stale V295)
def table(ptrbase, sel=7):
    p = struct.unpack_from("<I", img, ptrbase + 4 * sel)[0]
    n = u16(p)
    X = np.array([u16(p + 2 + 2 * i) for i in range(n)], np.int64)
    Y = np.array([u16(p + 2 + 2 * n + 2 * i) for i in range(n)], np.int64)
    return (X, Y)
cand_un = ST.Cand("V298-unarmed", "E2", rows, dop="fresh", kd=48, kp=112, ki=40, icl=8192, thr=512,
                  sgn_thr=300, arb=ST.ARB_A3, ramp_frz=True, fade2=False)
cand_arm = ST.Cand("V298-armed", "E2", rows, dop="fresh", kd=48, kp=112, ki=40, icl=8192, thr=512,
                   sgn_thr=300, arb=ST.ARB_A3, ramp_frz=True, fade2=True)
# save/patch CAL fadeB2 to the IMAGE's value
old_fb2 = ST.CAL["fadeB2"]
ST.CAL["fadeB2"] = table(0xCBBC4)
print(f"  image fadeB2 X={list(ST.CAL['fadeB2'][0])} Y={list(ST.CAL['fadeB2'][1])}")
print(f"  image fadeB  X={list(ST.CAL['fadeB'][0])} Y={list(ST.CAL['fadeB'][1])}")
N = 200
vw = np.random.default_rng(3).integers(0, 12001, N)
lu = ST.CandLane([cand_un] * N, vw)
la = ST.CandLane([cand_arm] * N, vw)
rng = np.random.default_rng(11)
mism = 0; maxd = 0
for t in range(3000):
    a6a00 = rng.integers(-12000, 12001); xh = rng.integers(-12000, 12001)
    abe = rng.integers(-13000, 13001); cmd = rng.integers(-16384, 16385); tq = rng.integers(-4000, 4001)
    Tu = lu.tick(np.full(N, a6a00), np.zeros(N), np.full(N, xh), np.full(N, abe),
                 np.full(N, cmd), np.full(N, tq), np.full(N, 0x8000), 1, 1, pol=-1)
    Ta = la.tick(np.full(N, a6a00), np.zeros(N), np.full(N, xh), np.full(N, abe),
                 np.full(N, cmd), np.full(N, tq), np.full(N, 0x8000), 1, 1, pol=-1)
    d = int(np.max(np.abs(Tu - Ta)))
    if d:
        mism += 1; maxd = max(maxd, d)
ST.CAL["fadeB2"] = old_fb2
print(f"  armed vs un-armed delivered T over 3000 ticks x {N} cols : mismatch ticks={mism} maxdiff={maxd}"
      f"  => {'IDENTICAL (neutralization holds in-loop)' if mism == 0 else 'DIFFER'}")
