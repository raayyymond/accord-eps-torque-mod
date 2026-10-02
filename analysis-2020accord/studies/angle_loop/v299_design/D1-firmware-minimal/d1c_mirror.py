# -*- coding: utf-8 -*-
r"""d1c_mirror.py -- the D1c cave stage as SCALAR integer Python, one line per instruction of out/d1c_flight.hex
(addresses = the D1c flight listing printed by d1_cave.py).  `>>` is V850 sar; products are the low 32 bits (s32).
Returns what the cave hands back to Honda's lane: the exit (0x29D7A normal / 0x29D7E freeze / 0x2A164 op-skip),
r16 = E', r6 (e5 on the freeze/CAM exits), r26 = the D operand.  The cave writes NO RAM.
SELF-TEST: equal to d1_time.D1Lane.cave_stage (which is H1-verified against the bytes, 0/8000) on random + edge inputs,
in the score-cave convention (an invalid rate -> op := 0 instead of the flight cave's jr 0x2A164), and the camera gate
r25 != 0.  usage: python d1c_mirror.py   (wall < 10 s)
"""
import sys
import time
from pathlib import Path

import numpy as np

GBP = ((714, 1178, 1041), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570), (4032, 1068, 2118),
       (6198, 2188, 0), (0xFFFF, 2188, 0))
HOOK_RET, FRZ_RET, SKIP = 0x29D7A, 0x29D7E, 0x2A164


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def d1c_cave(sp, r26, r14_ramp, r25, g6abe, g6a5e, g4f68, g6a00, g6dd0, flight=True, rows=GBP, THR=1229):
    """sp = r16 on entry (gp-0x69ae via E4), r26 = 8 th[n] + 8 th[n-1] (the fb sum), r14 = ramp gp-0x69b0,
    r25 = (gp-0x6803 == 2).  RAM cells are passed as the values the cave reads."""
    r16 = s32(sp << 2)                                         # 0xC4C00 shl 2,r16
    r16 = s32(r16 - r26)                                       # 0xC4C02 sub r26,r16      E = 16 (th_sp - th)
    r26 = s16(g6abe)                                           # 0xC4C04 ld.h -0x6abe[gp],r26   D operand
    r8 = s32(r26 + 13000)                                      # 0xC4C08 addi 13000,r26,r8
    if (r8 & 0xFFFFFFFF) > 26000:                              # 0xC4C0C movea ; 0xC4C10 cmp ; 0xC4C12 bnh CONT
        if flight:
            return dict(exit=SKIP, r16=r16, r6=None, r26=r26)  # 0xC4C14 jr 0x2A164 (Honda's A2/B2 epilogue)
        r26 = 0                                                # (score cave: cmovh r0,r26,r26)
    v = g6a5e & 0xFFFF                                         # 0xC4C18 ld.hu -0x6a5e[gp],r8
    i = 0                                                      # 0xC4C1C mov TBL,r9
    if not v > rows[0][0]:                                     # 0xC4C22..0xC4C28 X0 ; cmp ; bh L1
        G = rows[0][1]                                         # 0xC4C2A ld.hu 2[r9],r8 ; br APPLY
    else:
        while not v <= rows[i + 1][0]:                         # 0xC4C30 L1: ld.hu 6[r9] ; cmp ; bnh SEG
            i += 1                                             # 0xC4C38 addi 6,r9,r9 ; br L1
        X, G0, S = rows[i]
        G = s32(G0 + (s32((v - X) * S) >> 12))                 # 0xC4C3E..0xC4C52 SEG: sub ; ld.h S ; mul ; sar 12 ; add
    r16 = s32(r16 * G) >> 8                                    # 0xC4C54 mul r8,r16 ; 0xC4C58 sar 8   E' = (E G) >> 8
    if r25 == 0:                                               # 0xC4C5A cmp r0,r25 ; 0xC4C5C be CAM
        r6 = -(s32(g6dd0) >> 6)                                # 0xC4CC0..0xC4CCA CAM: E' := 0, op := 0, e5 = -(I8 >> 6)
        return dict(exit=FRZ_RET, r16=0, r6=s32(r6), r26=0)
    a4f68 = g4f68 & 0xFFFF                                     # 0xC4C5E ld.hu -0x4f68[gp],r8
    if a4f68 > THR:                                            # 0xC4C62 movea 1229 ; 0xC4C66 cmp ; 0xC4C68 bh FRZ
        return dict(exit=FRZ_RET, r16=r16, r6=0, r26=r26)      # 0xC4CBA FRZ: mov 0,r6 ; jr 0x29D7E
    r9 = s16(g6a00)                                            # 0xC4C6A ld.h -0x6a00[gp],r9    theta (0.1 deg)
    r13 = s32(r9 ^ r16)                                        # 0xC4C6E mov r9,r13 ; 0xC4C70 xor r16,r13   [D1c]
    if r13 < 0:                                                # 0xC4C72 bge AS                             [D1c]
        r9 = 0                                                 # 0xC4C74 mov 0,r9  (toward centre: bound = B)  [D1c]
    if r9 < 0:                                                 # 0xC4C76 AS: cmp r0,r9 ; 0xC4C78 bge A1
        r9 = -r9                                               # 0xC4C7A subr r0,r9  |theta|
    v = g6a5e & 0xFFFF                                         # 0xC4C7C A1: ld.hu -0x6a5e[gp],r8
    r9 = s32(r9 << (6 if v > 2880 else 4))                     # 0xC4C80..0xC4C8C movea 2880 ; cmp ; bh AH ; shl 4|6
    r9 = s32(r9 + 1250)                                        # 0xC4C8E AB: addi 1250,r9,r9   the bound
    if not v > 1382 and (r9 & 0xFFFFFFFF) > 4096:              # 0xC4C92..0xC4CA0 movea 1382 ; bh NC ; movea 4096 ; cmovh
        r9 = 4096
    r13 = s32(g6dd0) >> 10                                     # 0xC4CA4 NC: ld.w -0x6dd0[gp],r13 ; 0xC4CA8 sar 10
    if r16 < 0:                                                # 0xC4CAA cmp r0,r16 ; 0xC4CAC bge A2
        r13 = -r13                                             # 0xC4CAE subr r0,r13   t = sgn(E') I>>7
    if r13 >= r9:                                              # 0xC4CB0 A2: cmp r9,r13 ; 0xC4CB2 bge FRZ
        return dict(exit=FRZ_RET, r16=r16, r6=0, r26=r26)
    if (r14_ramp & 0x8000) == 0:                               # 0xC4CB4 andi 0x8000,r14,r13 ; 0xC4CB8 bne DONE
        return dict(exit=FRZ_RET, r16=r16, r6=0, r26=r26)
    return dict(exit=HOOK_RET, r16=r16, r6=None, r26=r26)      # 0xC4CD0 DONE: jmp [r6]


if __name__ == "__main__":
    t0 = time.time()
    HERE = Path(__file__).resolve().parent
    sys.path.insert(0, str(HERE))
    import d1_time as DT
    ST = DT.ST
    rng = np.random.default_rng(23)
    N = 20000
    sp = rng.integers(-16384, 16385, N)
    r26 = rng.integers(-65535, 65536, N)
    ramp = rng.choice([0x8000, 0x8000, 0x8000, 0x4000, 0xFFFF], N)
    abe = np.where(rng.random(N) < 0.1, rng.choice([13000, 13001, -13000, -13001, 0x7FFF], N), rng.integers(-3000, 3001, N))
    vv = rng.integers(0, 12001, N)
    tq = np.where(rng.random(N) < 0.2, rng.choice([1228, 1229, 1230, -1229, -1230, 512, 513, 300, 301], N),
                  rng.integers(-3000, 3001, N))
    th = np.where(rng.random(N) < 0.5, rng.integers(-40, 41, N), rng.integers(-4000, 4001, N))
    I8 = rng.integers(-8192 * 1024, 8192 * 1024, N)
    c = DT.mk("D1c", 1229, 0, True, ST.ARB_A3)
    lane = DT.D1Lane([c] * N, vv)
    cv = lane.cave_stage(ST.s16(sp), r26, ramp, th, abe, ST.s16(tq), I8, np.full(N, 0x7FFFFFFF), np.zeros(N, np.int64),
                         np.zeros(N, np.int64))
    bad = 0
    for k in range(N):
        m = d1c_cave(int(sp[k]), int(r26[k]), int(ramp[k]), 1, int(abe[k]), int(vv[k]), min(abs(int(tq[k])), 0xFFFF),
                     int(th[k]), int(I8[k]), flight=False)
        frz = bool(cv["frz"][k])
        ok = (m["r16"] == int(cv["Ep"][k]) and (m["exit"] == FRZ_RET) == frz and m["r26"] == int(cv["op"][k])
              and (not frz or m["r6"] == int(cv["r6"][k])))
        bad += not ok
    print(f"d1c_mirror vs D1Lane.cave_stage (H1-verified vs the bytes): {bad}/{N} mismatches (freeze exits {int(cv['frz'].sum())}, op zeroed {int((cv['op'] == 0).sum())}); wall {time.time() - t0:.1f} s")
