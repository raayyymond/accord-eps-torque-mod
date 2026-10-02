# -*- coding: utf-8 -*-
r"""rev_h1.py -- V299 rev 2 crux check: the REV-2 cave bytes (rev_bytes.py: the 66-B span 0xC4C6A..0xC4CAB re-laid out with
a two-level A3 cap) EXECUTED by the kit's V850E2 interpreter (panel2/score_time.Cpu2, the harness of d3_h1.run_h1 and
the synthesis' syn_h1_inplace) against THE SPEC'S OWN integer mirror `cave_rev2` below (the function printed in the spec).
ANALYSIS ONLY.

Per case (random + edge cases incl. v-word 1381/1382/1383 and 2879/2880/2881, every GB-P knot +-1, hand words at the
1229 edge): exit address, r16 = E', r26 = op, r6 on the freeze/camera exits, no RAM written, non-scratch registers kept.
Controls / negatives (the check can fail):
  C0  the mirror at rev-1 caps (4096 @ <= 1382) == d1_time.D1Lane (D1c) on every case (my mirror = the synthesis' mirror)
  C1  V298 bytes vs the V298 mirror (D1Lane V298)                    must be 0
  C2  rev-1 bytes vs the mirror at rev-1 caps                         must be 0
  N1  rev-2 bytes vs the mirror at rev-1 caps                         must be > 0
  N2  rev-1 bytes vs the mirror at rev-2 caps                         must be > 0
  A4  alt4 bytes (single cap 6144 @ <= 2880) vs the mirror at that cap must be 0 (the rejected alternative is also exact)
usage: python rev_h1.py"""
import contextlib
import io
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
V299 = HERE.parent
AL = V299.parent
KIT = AL.parents[2]
sys.path.insert(0, str(V299 / "D1-firmware-minimal"))
sys.path.insert(0, str(V299 / "D3-authority-first"))
with contextlib.redirect_stdout(io.StringIO()):
    import d1_time as DT
ST = DT.ST
NC, GP = ST.NC, ST.GP
SKIP = 0x2A164
OUT = KIT / "_scratch" / "v299_REV2"


def s16(x):
    return ((int(x) + 0x8000) & 0xFFFF) - 0x8000


def s32(x):
    return ((int(x) + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)


def cave_rev2(sp, r26, ramp, r25, abe, v, a4f68, th, I8, G, caps=((1382, 4096), (2880, 6144))):
    """THE SPEC MIRROR (integer-exact, scalar).  Returns (exit, r16, r26, r6 or None).  caps = ((v_lo, cap_lo), (v_hi,
    cap_hi)); v_hi None = rev-1/V298 single level.  G = the GB-P walk at v (unchanged bytes 0xC4C18..0xC4C52)."""
    E = s32(s32(sp << 2) - r26)                                  # 0xC4C00 shl 2,r16 ; sub r26,r16
    op = s16(abe)                                                # 0xC4C04 ld.h -0x6abe[gp],r26
    if ((op + 13000) & 0xFFFFFFFF) > 26000:                      # 0xC4C08..0xC4C12
        return SKIP, None, None, None                            # 0xC4C14 jr 0x2A164
    Ep = s32(E * G) >> 8                                         # 0xC4C54 mul r8,r16 ; 0xC4C58 sar 8
    if r25 == 0:                                                 # 0xC4C5A cmp r0,r25 ; be 0xC4CC8  (camera gate)
        return NC.FRZ_RET, 0, 0, s32(-(I8 >> 6))                 # 0xC4CC8..0xC4CD4
    if (a4f68 & 0xFFFF) > 1229:                                  # 0xC4C5E ld.hu -0x4f68 ; movea 1229 ; cmp ; bh FRZ
        return NC.FRZ_RET, Ep, op, 0
    r9 = s16(th)                                                 # 0xC4C6A ld.h -0x6a00[gp],r9
    if Ep < 0:                                                   # 0xC4C6E cmp r0,r16 ; bge
        r9 = -r9                                                 # 0xC4C72 subr r0,r9
    if r9 < 0:                                                   # 0xC4C74 cmp r0,r9 ; bge
        r9 = 0                                                   # 0xC4C78 mov 0,r9      -> max(theta*sgn(E'), 0)
    vv = v & 0xFFFF                                              # 0xC4C7A ld.hu -0x6a5e[gp],r8
    if vv > 2880:                                                # 0xC4C7E movea 2880 ; cmp ; bh 0xC4CA6
        r9 = s32((r9 << 6) + 1250)                               # 0xC4CA6 shl 6 ; addi 1250       (no cap)
    else:
        r9 = s32((r9 << 4) + 1250)                               # 0xC4C86 shl 4 ; addi 1250
        (vlo, clo), (vhi, chi) = caps
        if vhi is None:                                          # single-level forms (V298/rev1: vlo 1382; alt4: 2880)
            cap = clo if vv <= vlo else None
        else:
            cap = clo if vv <= vlo else chi                      # 0xC4C8C movea 1382 ; cmp ; bh ; movea 4096 | 6144
        if cap is not None and (r9 & 0xFFFFFFFF) > cap:          # 0xC4C9E cmp r13,r9 ; cmovh r13,r9,r9
            r9 = cap
    t = s32(I8) >> 10                                            # 0xC4CAC ld.w -0x6dd0[gp],r13 ; sar 10
    if Ep < 0:                                                   # 0xC4CB2 cmp r0,r16 ; bge ; subr r0,r13
        t = -t
    if t >= r9:                                                  # 0xC4CB8 cmp r9,r13 ; bge FRZ
        return NC.FRZ_RET, Ep, op, 0
    if (ramp & 0x8000) == 0:                                     # 0xC4CBC andi 0x8000,r14,r13 ; bne DONE
        return NC.FRZ_RET, Ep, op, 0
    return NC.HOOK_RET, Ep, op, None                             # 0xC4CD8 jmp [r6] -> 0x29D7A (Honda's I/P/D)


def cases(N, seed, rows):
    rng = np.random.default_rng(seed)
    knots = [r[0] for r in rows if r[0] < 0xFFFF]
    edges = [-1230, -1229, -513, -512, -301, -300, 0, 300, 301, 512, 513, 1229, 1230, -32768, 32767]
    vedge = [1381, 1382, 1383, 2879, 2880, 2881]
    out = []
    for k in range(N):
        sp = int(rng.integers(-16384, 16385)) if k % 40 else 32767
        r26 = int(rng.integers(-65535, 65536))
        if k % 5 == 0:
            v = int(np.clip(rng.choice(knots + [1382, 2880]) + rng.integers(-1, 2), 0, 12000))
        elif k % 5 == 1:
            v = int(rng.choice(vedge))
        else:
            v = int(rng.integers(0, 12001))
        tq = int(rng.choice([int(rng.integers(-3000, 3001)), int(rng.choice(edges))]))
        ramp = int(rng.choice([0x8000, 0x8000, int(rng.integers(0, 0x8000)), 0xFFFF]))
        th = int(rng.choice([int(rng.integers(-4000, 4001)), int(rng.integers(-40, 41)), int(rng.integers(-32768, 32768))]))
        I8 = int(rng.choice([int(rng.integers(-12288 * 1024, 12288 * 1024)), int(rng.integers(-2 ** 20, 2 ** 20)), 0,
                             int(rng.integers(-8192 * 1024, 8192 * 1024))]))
        abe = int(rng.choice([int(rng.integers(-13000, 13001)), int(rng.integers(-500, 501)), 13000, -13000,
                              13001, -13001, 0x7FFF, int(rng.integers(-32768, 32768))]))
        r25 = 0 if k % 9 == 0 else 1
        out.append((sp, r26, v, tq, ramp, th, I8, abe, r25))
    return out


def cases_targeted(N, seed):
    """the regime the cap edit changes: 1382 < v <= 2880 (and the 1381..1383 / 2879..2881 edges), a large same-sign
    angle, |I8>>10| straddling 4096..6144 with either sign, armed, ramp complete, hand below 1229."""
    rng = np.random.default_rng(seed)
    out = []
    for k in range(N):
        v = int(rng.choice([int(rng.integers(1383, 2881)), 1381, 1382, 1383, 2879, 2880, 2881]))
        sp = int(rng.integers(-16384, 16385))
        r26 = int(rng.integers(-65535, 65536))
        th = int(rng.integers(150, 1200)) * int(rng.choice([-1, 1]))
        I8 = int(rng.integers(3000, 7500)) * 1024 * int(rng.choice([-1, 1])) + int(rng.integers(0, 1024))
        tq = int(rng.integers(-1229, 1230))
        abe = int(rng.integers(-500, 501))
        out.append((sp, r26, v, tq, 0x8000, th, I8, abe, 1))
    return out


def run_bytes(code, C, Gv):
    """the interpreter on `code`, per case; returns list of (exit, r16, r26, r6, ram_same, regs_ok)."""
    rng = np.random.default_rng(99)
    res = []
    for i, (sp, r26, v, tq, ramp, th, I8, abe, r25) in enumerate(C):
        vals = dict(abe=abe, v=v, a4f68=min(abs(tq), 0xFFFF), tq=tq, th=th, I8=I8, Ep6=ST.SENT32, C6=0, W6=0, x=0)
        key = {"6abe": "abe", "6a5e": "v", "4f68": "a4f68", "4f60": "tq", "6a00": "th", "6dd0": "I8", "6cf8": "Ep6",
               "6c44": "C6", "6c40": "W6", "6a56": "x"}
        ram = {(GP + off) & NC.M32: (vals[key[nm]] & ((1 << (8 * w)) - 1), w) for nm, (off, w) in ST.CELLS.items()}
        regs = {16: sp, 26: r26, 14: ramp, 25: r25}
        regs.update({q: int(rng.integers(0, 2 ** 32)) for q in range(1, 32) if q not in (4, 6, 14, 16, 25, 26)})
        mem = {0xC4C00 + j: b for j, b in enumerate(code)}
        for ad, (val, w) in ram.items():
            for q in range(w):
                mem[(ad + q) & NC.M32] = (val >> (8 * q)) & 0xFF
        mem0 = dict(mem)
        cpu = ST.Cpu2(mem)
        for q, v_ in regs.items():
            cpu.r[q] = v_ & NC.M32
        cpu.r[4] = GP
        cpu.r[6] = NC.HOOK_RET
        pc = 0xC4C00
        for _ in range(600):
            if not (0xC4C00 <= pc < 0xC4C00 + len(code)):
                break
            pc = cpu.step(pc)
        ram_same = all(cpu.mem.get(ad, None) == mem0.get(ad, None) for ad in mem0)
        regs_ok = all(cpu.r[q] == (regs[q] & NC.M32) for q in regs if q not in ST.SCRATCH) and cpu.r[4] == GP
        res.append((pc, NC.s32(cpu.r[16]), NC.s32(cpu.r[26]), NC.s32(cpu.r[6]), ram_same, regs_ok))
    return res


def compare(code, C, Gv, caps):
    got = run_bytes(code, C, Gv)
    bad = dict(valid=0, skip=0, cam=0, frz=0, run=0)
    nn = dict(valid=0, skip=0, cam=0, frz=0, run=0)
    first = None
    for i, c in enumerate(C):
        sp, r26, v, tq, ramp, th, I8, abe, r25 = c
        ex, r16m, r26m, r6m = cave_rev2(sp, r26, ramp, r25, abe, v, min(abs(tq), 0xFFFF), th, I8, int(Gv[i]), caps)
        pc, r16b, r26b, r6b, ram_same, regs_ok = got[i]
        if ex == SKIP:
            cls, ok = "skip", pc == SKIP
        elif r25 == 0:
            cls, ok = "cam", pc == ex and r16b == r16m and r26b == r26m and r6b == r6m
        else:
            cls = "frz" if ex == NC.FRZ_RET else "run"
            ok = pc == ex and r16b == r16m and r26b == r26m and (r6m is None or r6b == r6m)
        ok = ok and ram_same and regs_ok
        nn[cls] += 1
        if cls in ("frz", "run"):
            nn["valid"] += 1
        if not ok:
            bad[cls] += 1
            if cls in ("frz", "run"):
                bad["valid"] += 1
            if first is None:
                first = dict(case=c, cls=cls, mirror=hex(ex), bytes=hex(pc))
    return bad, nn, first


def job(args):
    name, hexfile, caps, N, seed = args
    code = bytes.fromhex((OUT / hexfile).read_text().replace(" ", "")) if hexfile else b""
    rows = DT.GBP
    C = cases_targeted(N, seed) if "targeted" in name else cases(N, seed, rows)
    a = np.array(C, np.int64)
    Gv = ST.CandLane([DT.mk("x", 1229, 0, True, ST.ARB_A3)] * N, a[:, 2]).G
    if name.startswith("C1"):
        # V298 bytes vs the V298 mirror = D1Lane V298 (the synthesis' C1 control, its own harness)
        with contextlib.redirect_stdout(io.StringIO()):
            import d3_h1 as D3H
        D3H.ST = ST
        D3H.NC, D3H.GP = ST.NC, ST.GP
        orig = ST.CandLane
        ST.CandLane = DT.D1Lane
        try:
            b, n, f = D3H.run_h1(code, DT.mk("V298", 512, 300, False, ST.ARB_A3), N, seed,
                                 [-1230, -1229, -513, -512, -301, -300, 0, 300, 301, 512, 513, 1229, 1230])
        finally:
            ST.CandLane = orig
        return name, b, n, f
    if name.startswith("C0"):
        # my mirror at rev-1 caps vs D1Lane D1c (no bytes): exit class + E' + op on every valid, armed case
        lane = DT.D1Lane([DT.mk("D1c", 1229, 0, True, ST.ARB_A3)] * N, a[:, 2])
        cv = lane.cave_stage(ST.s16(a[:, 0]), a[:, 1], a[:, 4], a[:, 5], a[:, 7], ST.s16(a[:, 3]), a[:, 6],
                             np.full(N, ST.SENT32, np.int64), np.zeros(N, np.int64), np.zeros(N, np.int64))
        bad = dict(valid=0)
        nn = dict(valid=0)
        first = None
        for i, c in enumerate(C):
            sp, r26, v, tq, ramp, th, I8, abe, r25 = c
            ex, r16m, r26m, r6m = cave_rev2(sp, r26, ramp, r25, abe, v, min(abs(tq), 0xFFFF), th, I8, int(Gv[i]),
                                            ((1382, 4096), (None, None)))
            if ex == SKIP or r25 == 0:
                continue
            nn["valid"] += 1
            frz_l = bool(cv["frz"][i] | cv["leak"][i])
            if not (r16m == int(cv["Ep"][i]) and (ex == NC.FRZ_RET) == frz_l and r26m == int(cv["op"][i])):
                bad["valid"] += 1
                first = first or dict(case=c)
        return name, bad, nn, first
    b, n, f = compare(code, C, Gv, caps)
    return name, b, n, f


if __name__ == "__main__":
    R1 = ((1382, 4096), (None, None))
    R2 = ((1382, 4096), (2880, 6144))
    A4 = ((2880, 6144), (None, None))
    JOBS = [("C0 mirror@rev1 caps vs D1Lane(D1c)", None, None, 20000, 11),
            ("C1 V298 bytes vs V298 mirror (D1Lane)", "../v299_REV2/v298_cave.hex", None, 2000, 7),
            ("C2 rev1 bytes vs mirror@rev1", "rev1_cave.hex", R1, 3000, 12),
            ("THE CHECK rev2 bytes vs mirror@rev2 (a)", "rev2_cave.hex", R2, 6000, 21),
            ("THE CHECK rev2 bytes vs mirror@rev2 (b)", "rev2_cave.hex", R2, 6000, 22),
            ("N1 rev2 bytes vs mirror@rev1", "rev2_cave.hex", R1, 3000, 13),
            ("N2 rev1 bytes vs mirror@rev2", "rev1_cave.hex", R2, 3000, 14),
            ("A4 alt4 bytes vs mirror@single 6144", "alt4_cave.hex", A4, 3000, 15),
            ("T  rev2 bytes vs mirror@rev2 (targeted)", "rev2_cave.hex", R2, 4000, 31),
            ("NT rev2 bytes vs mirror@rev1 (targeted)", "rev2_cave.hex", R1, 2000, 32),
            ("NT2 rev2 bytes vs mirror@alt4 (targeted)", "rev2_cave.hex", A4, 2000, 33)]
    import glob
    import hashlib
    img = open(glob.glob("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v298_*_plain_image.bin")[0], "rb").read()
    assert hashlib.sha256(img).hexdigest().startswith("177abf04")
    (OUT / "v298_cave.hex").write_text(img[0xC4C00:0xC4D04].hex(" "), encoding="utf-8")
    JOBS[1] = ("C1 V298 bytes vs V298 mirror (D1Lane)", "v298_cave.hex", None, 2000, 7)
    with Pool(len(JOBS)) as p:
        res = p.map(job, JOBS)
    L = []
    for name, b, n, f in res:
        L.append(f"{name:44s} mismatches {b} of {n}" + (f"  first {f}" if f else ""))
        print(L[-1])
    L.append(f"wall {time.time() - T0:.1f} s")
    print(L[-1])
    (OUT / "rev_h1.txt").write_text("\n".join(L), encoding="utf-8")
