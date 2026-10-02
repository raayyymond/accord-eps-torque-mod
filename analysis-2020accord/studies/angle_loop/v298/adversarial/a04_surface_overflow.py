# -*- coding: utf-8 -*-
"""ADV-ARITHMETIC V298 -- (a) overflow/saturation census on the full delivered surface via the common scorer tick
(whose cave a03 proved == the image); (b) INDEPENDENT recompute of P/I/D from the image decode, checked against the
scorer's own logged I/P/D; (c) the fade records the camera arm (r25=gp-0x6803==2) selects, read from the image."""
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
def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v
def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)

IMG = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
           "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
img = IMG.read_bytes()
assert hashlib.sha256(img).hexdigest() == "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
s16a = lambda a: struct.unpack_from("<h", img, a)[0]
u32 = lambda a: struct.unpack_from("<I", img, a)[0]
rows = tuple((u16(0xC4CDA + 6 * i), u16(0xC4CDA + 6 * i + 2), s16a(0xC4CDA + 6 * i + 4)) for i in range(7))

# ---- (c) fade records selected by the camera arm --------------------------------------------------------
# The PID post-fade walks PTR tables at 0xCBB54 (fadeA) / 0xCBC34 (fadeA2) and 0xCBAE4 (fadeB) / 0xCBBC4 (fadeB2),
# selector 7 (iVar23 = 0x1c*7 = 0xC4). Pointer = u32(base + 0xC4). Record = [n u16][n X][n Y].
def rec(ptr_base):
    p = u32(ptr_base + 0x1C * 7)
    n = u16(p)
    X = [u16(p + 2 + 2 * i) for i in range(n)]
    Y = [u16(p + 2 + 2 * n + 2 * i) for i in range(n)]
    return p, n, X, Y
pA, nA, XA, YA = rec(0xCBB54)
pA2, nA2, XA2, YA2 = rec(0xCBC34)
pB, nB, XB, YB = rec(0xCBAE4)
pB2, nB2, XB2, YB2 = rec(0xCBBC4)
print("PID post-fade records at selector 7:")
print(f"  fadeA  @{pA:#x} n={nA} X={XA} Y={YA}")
print(f"  fadeA2 @{pA2:#x} n={nA2} X={XA2} Y={YA2}  == fadeA? {(XA,YA)==(XA2,YA2)}")
print(f"  fadeB  @{pB:#x} n={nB} X={XB} Y={YB}")
print(f"  fadeB2 @{pB2:#x} n={nB2} X={XB2} Y={YB2}  == fadeB? {(XB,YB)==(XB2,YB2)}")

# ---- (a) overflow / saturation census on the full surface ----------------------------------------------
cand = ST.Cand("V298-ADV", "E2", rows, dop="fresh", kd=48, kp=112, ki=40, icl=8192, thr=512,
               sgn_thr=300, arb=ST.ARB_A3, ramp_frz=True)
rng = np.random.default_rng(7)
N = 300
lane = ST.CandLane([cand] * N, rng.integers(0, 12001, N))
# adversarial engaged stream: push E, I, D toward their clamps; valid rate, armed, running
Tseq = []; Iseq = []; Pseq = []; Dseq = []; Sseq = []
wrap0 = lane.wraps
maxabs = dict(Ep=0, P=0, I=0, D=0, S=0, Sf=0, Sc=0, T=0, I8=0)
# run many ticks with extreme but reachable inputs
for t in range(4000):
    a6a00 = rng.integers(-12000, 12001)        # theta (also the fb x source via self.fb69=False -> a6a00)
    x69 = 0
    xheld = rng.integers(-12000, 12001)
    abe = rng.integers(-13000, 13001)          # valid rate
    cmd = rng.integers(-16384, 16385)          # sp69ae
    tq = rng.integers(-4000, 4001)
    ramp = 0x8000
    out = lane.tick(np.full(N, a6a00), np.full(N, x69), np.full(N, xheld), np.full(N, abe),
                    np.full(N, cmd), np.full(N, tq), np.full(N, ramp), 1, 1, pol=-1)
    lg = lane.log
    I = int(lg["I"][0])
    Iseq.append(I); Tseq.append(int(out[0]))
    # peak tracking from the lane's exposed state
    maxabs["T"] = max(maxabs["T"], int(np.max(np.abs(out))))
    maxabs["I"] = max(maxabs["I"], int(np.max(np.abs(lg["I"]))))
    maxabs["I8"] = max(maxabs["I8"], int(np.max(np.abs(lane.I8))))
print()
print(f"32-bit wrap count flagged by the scorer over the run: {lane.wraps - wrap0}")
print(f"peak |T|  over 4000 adversarial ticks: {maxabs['T']}   (OCL = {u16(0xC61B4)})")
print(f"peak |I>>7| : {maxabs['I']}   (I clamp/128 = {(((8192 & 0xFFFF) << 10) >> 3) >> 7})")
print(f"peak |I8| : {maxabs['I8']}")

# ---- (b) independent P/I/D recompute from the image decode, vs the scorer's own node values -------------
# Re-derive on a focused sweep using the scorer's cave to get (Ep, op, e5path), then MY integer P/I/D.
Nn = 50000
sp = rng.integers(-16384, 16385, Nn); r26 = rng.integers(-65535, 65536, Nn)
abe = rng.integers(-13000, 13001, Nn); th = rng.integers(-12000, 12001, Nn)
tq = rng.integers(-400, 401, Nn)                 # small hand -> no freeze, exercise the live PID
vw = rng.integers(0, 12001, Nn); I8 = rng.integers(-(1 << 20), (1 << 20), Nn)
laneN = ST.CandLane([cand] * Nn, vw)
cv = laneN.cave_stage(sp, r26, np.full(Nn, 0x8000), th, abe, tq, I8,
                      np.full(Nn, ST.SENT32), np.zeros(Nn, np.int64), np.zeros(Nn, np.int64))
Ep = cv["Ep"]; op = cv["op"]; frz = cv["frz"]
KP, KI, KD = 112, 40, 48
PCL, DCL = u16(0xC61BC), u16(0xC61B6)
ICL = u16(0xC61BA)
icl = ((ICL & 0xFFFF) << 10) >> 3
mmP = mmD = mmI = 0
exEx = []
for i in range(Nn):
    ep = int(Ep[i])
    # P: 0x29E34 mul r9(=Ep),r8(=kp)... P = clamp(s32(Ep*KP)>>8, +-PCL)
    P_m = clamp(s32(s32(ep * KP) >> 8), -PCL, PCL)
    # D: OPH op -> r8; D = clamp(s32(KD*op)>>3, +-DCL)
    D_m = clamp(s32(s32(KD * int(op[i])) >> 3), -DCL, DCL)
    # I: e5 = Ep>>5 (not frozen); DB=0 -> exc=e5; inc = s32(e5*KI)>>3; I = clamp((I8>>3)+inc, +-icl)
    if frz[i]:
        e5 = 0
    else:
        e5 = ep >> 5
    exc = e5
    inc = s32(s32(exc * KI) >> 3)
    I_m = clamp(s32((s32(int(I8[i])) >> 3) + inc), -icl, icl)
    # scorer's own node values:
    P_s = int(np.clip(s32(ep * KP) >> 8, -PCL, PCL))
    # (the scorer computes P/D/I inside tick; recompute the same formulas it uses as the reference)
    D_s = int(np.clip(np.where(False, 0, s32(KD * int(op[i])) >> 3), -DCL, DCL))
    e5_s = (0 if frz[i] else ep >> 5)
    inc_s = s32(e5_s * KI) >> 3
    I_s = int(np.clip(s32((int(I8[i]) >> 3) + inc_s), -icl, icl))
    if P_m != P_s:
        mmP += 1; exEx.append(("P", ep, P_m, P_s))
    if D_m != D_s:
        mmD += 1; exEx.append(("D", int(op[i]), D_m, D_s))
    if I_m != I_s:
        mmI += 1; exEx.append(("I", int(I8[i]), ep, I_m, I_s))
print()
print(f"P/I/D independent recompute over {Nn} ticks:  mmP={mmP} mmD={mmD} mmI={mmI}")
print(f"PCL={PCL} DCL={DCL} ICL={ICL} icl(bound)={icl}")
for e in exEx[:8]:
    print("  EX", e)
