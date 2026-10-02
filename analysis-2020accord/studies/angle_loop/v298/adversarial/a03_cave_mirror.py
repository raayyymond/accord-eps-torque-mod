# -*- coding: utf-8 -*-
"""ADV-ARITHMETIC V298 -- INDEPENDENT integer mirror of the BUILT image's CAVE (0xC4C00..0xC4CD8), transcribed
instruction-by-instruction from the GhidraMCP decode of my own import of the image, each line annotated with its
instruction address.  Compared tick-for-tick against the common scorer's CandLane.cave_stage.

A disagreement on any VALID-RATE, camera-ON tick is a FINDING (F7).  The SKIP and CAM paths are checked separately.
Semantics written from the V850E2 manual (LE, arithmetic sar, 32-bit mul low word), NOT copied from the scorer.
"""
import sys, struct, hashlib, os
from pathlib import Path
HERE = Path(__file__).resolve()
AL = HERE.parents[2]                       # studies/angle_loop
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


IMG = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
           "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
img = IMG.read_bytes()
assert hashlib.sha256(img).hexdigest() == "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
s16i = lambda a: struct.unpack_from("<h", img, a)[0]
TABLE = [(u16(0xC4CDA + 6 * i), u16(0xC4CDA + 6 * i + 2), s16i(0xC4CDA + 6 * i + 4)) for i in range(7)]


def walk_G_image(v):
    """the cave G walk, 0xC4C18..0xC4C52.  v = u16 speed word."""
    v &= 0xFFFF
    X0 = TABLE[0][0]                                  # 0xC4C22 ld.hu 0x0
    if not (v > X0):                                  # 0xC4C26 cmp ; 0xC4C28 bh (UNSIGNED)
        return TABLE[0][1]                            # 0xC4C2A ld.hu 0x2 -> G[0]
    i = 0
    while True:                                       # 0xC4C30 loop
        Xn = TABLE[i + 1][0]                          # 0xC4C30 ld.hu 0x6 (next row X)
        if not (v > Xn):                              # 0xC4C34 cmp ; 0xC4C36 bnh -> interp
            break
        i += 1                                        # 0xC4C38 addi 0x6
    Xlo = TABLE[i][0]                                 # 0xC4C3E ld.hu 0x0
    d = s32(v - Xlo)                                  # 0xC4C42 sub r13,r8
    S = TABLE[i][2]                                   # 0xC4C44 ld.h 0x4 (signed slope)
    prod = s32(S * d)                                 # 0xC4C48 mul (low 32)
    sh = s32(prod) >> 12                              # 0xC4C4C sar 0xc (arith)
    G = TABLE[i][1]                                   # 0xC4C4E ld.hu 0x2
    return s32(G + sh)                                # 0xC4C52 add


def cave_image(sp, r26, ramp, a6a00, abe, tq4f68, tq4f60, I8, vw, r25=1):
    """returns (Ep, op_r26, e5_r6_on_028D7E_exit, exit) ; exit in normal|freeze|cam|skip."""
    r16 = s32(s32(sp << 2) - r26)                     # 0xC4C00 shl 2 ; 0xC4C02 sub r26  -> E
    r26o = s16(abe)                                   # 0xC4C04 ld.h -0x6abe
    r8 = s32(r26o + 0x32C8)                           # 0xC4C08 addi 13000
    if not ((r8 & M32) <= 0x6590):                    # 0xC4C10 cmp 26000 ; 0xC4C12 bnh (UNSIGNED)
        return (None, None, None, "skip")             # 0xC4C14 jr 0x2A164
    g = walk_G_image(vw)                              # 0xC4C18..0xC4C52
    r16 = s32(s32(g * r16) >> 8)                      # 0xC4C54 mul ; 0xC4C58 sar 8 -> Ep
    Ep = r16
    if r25 == 0:                                      # 0xC4C5A cmp r0,r25 ; 0xC4C5C be CAM
        r6 = s32(-(s32(I8) >> 6))                     # 0xC4CCC ld.w ; 0xC4CD0 sar 6 ; 0xC4CD2 subr
        return (0, 0, r6, "cam")                      # 0xC4CC8 E'=0 ; 0xC4CCA op=0
    atq = tq4f68 & 0xFFFF                             # 0xC4C5E ld.hu -0x4f68
    if atq > 512:                                     # 0xC4C62/66/68 bh -> FRZ
        return (Ep, r26o, 0, "freeze")
    if atq > 300:                                     # 0xC4C6A/6E/70 bnh skip-OPH
        r9 = s16(tq4f60)                              # 0xC4C72 ld.h -0x4f60
        if s32((Ep & M32) ^ (r9 & M32)) < 0:          # 0xC4C76 xor ; 0xC4C78 blt -> FRZ
            return (Ep, r26o, 0, "freeze")
    r9 = s16(a6a00)                                   # 0xC4C7A ld.h -0x6a00 (theta)
    if r9 < 0:                                        # 0xC4C7E/80 bge
        r9 = s32(-r9)                                 # 0xC4C82 subr -> |theta|
    r8 = vw & 0xFFFF                                  # 0xC4C84 ld.hu -0x6a5e
    if r8 > 2880:                                     # 0xC4C88/8C/8E bh
        r9 = s32(r9 << 6)                             # 0xC4C94 shl 6
    else:
        r9 = s32(r9 << 4)                             # 0xC4C90 shl 4
    r9 = s32(r9 + 0x4E2)                              # 0xC4C96 addi 1250 -> bound
    if not (r8 > 1382):                               # 0xC4C9A/9E/A0 bh skip-cap
        if r9 > 4096:                                 # 0xC4CA6 cmp ; 0xC4CA8 cmovh
            r9 = 4096
    r13 = s32(I8) >> 10                               # 0xC4CAC ld.w ; 0xC4CB0 sar 0xa
    if Ep < 0:                                        # 0xC4CB2/B4 bge
        r13 = s32(-r13)                               # 0xC4CB6 subr -> t
    if r13 >= r9:                                     # 0xC4CB8/BA bge -> FRZ
        return (Ep, r26o, 0, "freeze")
    if (ramp & 0x8000) != 0:                          # 0xC4CBC andi ; 0xC4CC0 bne -> DONE
        return (Ep, r26o, None, "normal")             # 0xC4CD8 jmp r6
    return (Ep, r26o, 0, "freeze")                    # 0xC4CC2 r6=0 ; jr 0x29D7E


rows = tuple(TABLE)
cand = ST.Cand("V298-ADV", "E2", rows, dop="fresh", kd=48, kp=112, ki=40, icl=8192, thr=512,
               sgn_thr=300, arb=ST.ARB_A3, ramp_frz=True)
rng = np.random.default_rng(20261001)
N = 200000
sp = rng.integers(-16384, 16385, N)
r26 = rng.integers(-65535, 65536, N)
abe = rng.integers(-18000, 18001, N)
th = rng.integers(-16000, 16001, N)
tq = rng.integers(-5000, 5001, N)
vw = rng.integers(0, 12001, N)
I8 = rng.integers(-(1 << 27), (1 << 27), N)
ramp = np.where(rng.integers(0, 2, N) == 1, 0x8000, 0x0000)

laneN = ST.CandLane([cand] * N, vw)
tq68 = np.minimum(np.abs(tq), 0xFFFF)
cv = laneN.cave_stage(sp, r26, ramp, th, abe, tq, I8,
                      np.zeros(N, np.int64), np.zeros(N, np.int64), np.zeros(N, np.int64))

abev = ((abe + 13000) & M32) <= 26000
mism_Ep = mism_op = mism_frz = mism_e5 = 0
examples = []
for i in range(N):
    if not abev[i]:
        continue
    Ep_m, op_m, e5_m, ex = cave_image(int(sp[i]), int(r26[i]), int(ramp[i]), int(th[i]), int(abe[i]),
                                      int(tq68[i]), int(tq[i]), int(I8[i]), int(vw[i]), r25=1)
    Ep_s = int(cv["Ep"][i]); op_s = int(cv["op"][i]); frz_s = bool(cv["frz"][i]); r6_s = int(cv["r6"][i])
    if Ep_m != Ep_s:
        mism_Ep += 1
        if len(examples) < 10: examples.append(("Ep", i, Ep_m, Ep_s, int(sp[i]), int(r26[i]), int(vw[i])))
    if op_m != op_s:
        mism_op += 1
        if len(examples) < 10: examples.append(("op", i, op_m, op_s, int(abe[i])))
    frz_m = (ex == "freeze")
    if frz_m != frz_s:
        mism_frz += 1
        if len(examples) < 10:
            examples.append(("frz", i, frz_m, frz_s, int(tq68[i]), int(tq[i]), Ep_m, int(th[i]), int(vw[i]),
                             int(I8[i]), int(ramp[i])))
    if frz_m and frz_s and (0 != r6_s):
        mism_e5 += 1
        if len(examples) < 10: examples.append(("e5frz", i, 0, r6_s))

Gsc = ST.glut(rows)
Gmine = np.array([walk_G_image(v) for v in range(12001)], np.int64)
dG = int(np.count_nonzero(Gmine != Gsc))

print(f"valid-rate ticks compared : {int(abev.sum())}")
print(f"mismatch Ep   : {mism_Ep}")
print(f"mismatch op   : {mism_op}")
print(f"mismatch frz  : {mism_frz}")
print(f"mismatch e5   : {mism_e5}")
print(f"G walk mismatch vs scorer glut over v 0..12000 : {dG}")
print(f"min G = {int(Gmine.min())} at v={int(Gmine.argmin())} ; max G = {int(Gmine.max())}")
for e in examples:
    print("  EX", e)
