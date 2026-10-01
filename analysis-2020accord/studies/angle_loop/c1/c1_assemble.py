# -*- coding: utf-8 -*-
"""c1_assemble.py -- assemble the C1 cave listing to bytes (two-pass, labels resolved), then EXECUTE THOSE BYTES with a
minimal V850E2 interpreter of exactly the opcodes the cave uses and compare, on random inputs, with the mirror's cave
arithmetic (c1_lib._C1Core.cave / i_update).  This is the design-time H1: the arithmetic the page lists, the bytes it
prints, and the mirror the harnesses ran are one thing.  The interpreter decodes FROM THE BYTES (field extraction per
format), and every encoding form is controlled against an instruction of the same form already in the V295 image
(the CONTROLS table below, re-read here in Python).  BELIEF until the built image is decoded by Ghidra (H5).
ANALYSIS ONLY: nothing is written to any image.  usage: python c1_assemble.py"""
from __future__ import annotations

import glob
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402

CAVE = 0xC4C00
HOOK = 0x29D76
RET = 0x29D7A
FRZ_RET = 0x29D7E
GP = 0xFEDF8000
IMG = glob.glob(str(C.KIT.parent / "accord-firmwares" / "analysis-2020accord" / "_v295_*plain_image.bin"))[0]

COND = dict(be=0x2, bne=0xA, bh=0xB, bnh=0x3, br=0x5)


def u16(x):
    return x & 0xFFFF


def enc(ins, pc, labels):
    op = ins[0]
    if op == "shl_i":   # shl imm5, reg2  (Format II, 0x16)
        return [u16((ins[2] << 11) | (0x16 << 5) | ins[1])]
    if op == "sar_i":
        return [u16((ins[2] << 11) | (0x15 << 5) | ins[1])]
    if op == "mov_i5":
        return [u16((ins[2] << 11) | (0x10 << 5) | (ins[1] & 0x1F))]
    if op == "sub":      # sub reg1, reg2: reg2 = reg2 - reg1
        return [u16((ins[2] << 11) | (0x0D << 5) | ins[1])]
    if op == "add":
        return [u16((ins[2] << 11) | (0x0E << 5) | ins[1])]
    if op == "cmp":      # cmp reg1, reg2: flags of reg2 - reg1
        return [u16((ins[2] << 11) | (0x0F << 5) | ins[1])]
    if op == "jmp":
        return [u16(0x0060 | ins[1])]
    if op == "mov_i32":
        v = labels[ins[1]] if isinstance(ins[1], str) else ins[1]
        return [u16(0x0620 | ins[2]), u16(v), u16(v >> 16)]
    if op == "movea":    # movea imm16, reg1, reg2
        return [u16((ins[3] << 11) | (0x31 << 5) | ins[2]), u16(ins[1])]
    if op == "addi":
        return [u16((ins[3] << 11) | (0x30 << 5) | ins[2]), u16(ins[1])]
    if op == "andi":
        return [u16((ins[3] << 11) | (0x36 << 5) | ins[2]), u16(ins[1])]
    if op == "ld_hu":    # ld.hu disp16[reg1], reg2
        return [u16((ins[3] << 11) | (0x3F << 5) | ins[2]), u16((ins[1] & 0xFFFE) | 1)]
    if op == "ld_h":
        assert ins[1] % 2 == 0
        return [u16((ins[3] << 11) | (0x39 << 5) | ins[2]), u16(ins[1] & 0xFFFE)]
    if op == "mul":      # mul reg1, reg2, reg3: reg3:reg2 = reg2 * reg1
        return [u16((ins[2] << 11) | (0x3F << 5) | ins[1]), u16((ins[3] << 11) | 0x220)]
    if op in COND:
        disp = labels[ins[1]] - pc
        assert -256 <= disp < 256 and disp % 2 == 0, (ins, disp)
        d = disp & 0x1FF
        return [u16((((d >> 4) & 0x1F) << 11) | (0b1011 << 7) | (((d >> 1) & 0x7) << 4) | COND[op])]
    if op in ("jr", "jarl"):
        tgt = labels[ins[1]] if isinstance(ins[1], str) else ins[1]
        disp = tgt - pc
        assert disp % 2 == 0 and -(1 << 21) <= disp < (1 << 21)
        reg = 0 if op == "jr" else ins[2]
        return [u16((reg << 11) | (0x1E << 6) | ((disp >> 16) & 0x3F)), u16(disp & 0xFFFE)]
    if op == "half":
        return [u16(ins[1])]
    raise KeyError(op)


def size(ins):
    return {"mov_i32": 6, "movea": 4, "addi": 4, "andi": 4, "ld_hu": 4, "ld_h": 4, "mul": 4, "jr": 4,
            "jarl": 4}.get(ins[0], 2)


def listing(tbl, thr=C.FRZ_THR):
    """THE C1 CAVE.  (label, instruction, comment) -- every instruction names its loop term."""
    L = []
    A = L.append
    A(("C1", ("shl_i", 2, 16), "displaced 0x29D76: 4*sp"))
    A((None, ("sub", 26, 16), "displaced 0x29D78: E = 4*sp - r26 = 16*(theta_sp - theta)"))
    A((None, ("ld_hu", -0x6A5E, 4, 8), "v = gp-0x6a5e (64 counts per km/h)            [G(v) LERP]"))
    A((None, ("mov_i32", "TBL", 9), "r9 -> table                                     [G(v) LERP]"))
    A((None, ("ld_hu", 0, 9, 13), "X0                                              [G(v) LERP]"))
    A((None, ("cmp", 13, 8), "v - X0                                          [G(v) LERP]"))
    A((None, ("bh", "L1"), "v > X0 (unsigned): walk                         [G(v) LERP]"))
    A((None, ("ld_hu", 2, 9, 8), "G = G0 (clamp low)                              [G(v) LERP]"))
    A((None, ("br", "APPLY"), ""))
    A(("L1", ("ld_hu", 6, 9, 13), "X(i+1)                                          [G(v) LERP]"))
    A((None, ("cmp", 13, 8), ""))
    A((None, ("bnh", "SEG"), "v <= X(i+1): segment i                          [G(v) LERP]"))
    A((None, ("addi", 6, 9, 9), "next row (the 0xFFFF sentinel row ends the walk)"))
    A((None, ("br", "L1"), ""))
    A(("SEG", ("ld_hu", 0, 9, 13), "X(i)                                            [G(v) LERP]"))
    A((None, ("sub", 13, 8), "dv = v - X(i)"))
    A((None, ("ld_h", 4, 9, 13), "S(i), Q12 slope, signed"))
    A((None, ("mul", 13, 8, 0), "dv * S(i) (low word)"))
    A((None, ("sar_i", 12, 8), ">> 12"))
    A((None, ("ld_hu", 2, 9, 13), "G(i)"))
    A((None, ("add", 13, 8), "G = G(i) + ((v - X(i)) * S(i) >> 12)"))
    A(("APPLY", ("mul", 8, 16, 0), "E * G (low word)                                 [THE SPEED GAIN on P and I]"))
    A((None, ("sar_i", 8, 16), "E' = (E * G) >> 8"))
    A((None, ("ld_hu", -0x4F68, 4, 8), "|driver torque| = gp-0x4f68                     [I FREEZE on the hand]"))
    A((None, ("movea", thr, 0, 13), f"THR = {thr}"))
    A((None, ("cmp", 13, 8), ""))
    A((None, ("bh", "FRZ"), "|tq| > THR (unsigned): freeze"))
    A((None, ("andi", 0x8000, 14, 13), "r14 = the ramp gp-0x69b0 (the 0x2A1E6 multiplier)  [I FREEZE on ramp-in/out]"))
    A((None, ("bne", "DONE"), "ramp == 0x8000 (full): integrate normally"))
    A(("FRZ", ("mov_i5", 0, 6), "r6 := e5 := 0 -> Honda's exc = 0 -> I unchanged"))
    A((None, ("jr", FRZ_RET), "return PAST 0x29D7A mov r16,r6 / 0x29D7C sar 5,r6"))
    A(("DONE", ("jmp", 6), "return to 0x29D7A (r6 = the jarl link)"))
    rows = []
    for (X, G, S) in tbl:
        rows += [("half", X), ("half", G), ("half", S & 0xFFFF)]
    L.append(("TBL", rows[0], "table: X u16, G u16, S s16 Q12 per row"))
    for r in rows[1:]:
        L.append((None, r, ""))
    return L


def assemble(tbl, thr=C.FRZ_THR, base=CAVE):
    L = listing(tbl, thr)
    labels = {}
    pc = base
    for lab, ins, _ in L:
        if lab:
            labels[lab] = pc
        pc += size(ins)
    out = bytearray()
    lines = []
    pc = base
    for lab, ins, com in L:
        hw = enc(ins, pc, labels)
        bs = b"".join(struct.pack("<H", h) for h in hw)
        assert len(bs) == size(ins)
        out += bs
        lines.append((pc, lab or "", ins, bs.hex(" "), com))
        pc += len(bs)
    return bytes(out), labels, lines


# ------------------------------------------------------------------------------------------------- interpreter
def s32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


def run_bytes(code, base, regs, mem16, start, stop_at=(RET, FRZ_RET), max_steps=200):
    """execute from `start`; returns (pc_at_exit, regs).  mem16(addr) -> u16 for loads.  Decodes from the bytes."""
    r = dict(regs)
    r[0] = 0
    pc = start
    Z = CY = S = OV = False

    def get(a):
        return code[a - base] | (code[a - base + 1] << 8)
    for _ in range(max_steps):
        if pc in stop_at:
            return pc, r
        h1 = get(pc)
        op6 = (h1 >> 5) & 0x3F
        reg1, reg2 = h1 & 0x1F, h1 >> 11
        if (op6 >> 2) == 0b1011:                 # Format III Bcond (bits 10..7 = 1011)
            cond = h1 & 0xF
            d = ((h1 >> 11) << 4) | (((h1 >> 4) & 7) << 1)
            d = d - 512 if d & 0x100 else d
            take = {0x2: Z, 0xA: not Z, 0xB: not (CY or Z), 0x3: (CY or Z), 0x5: True}[cond]
            pc = pc + d if take else pc + 2
            continue
        if op6 in (0x3C, 0x3D) and not (get(pc + 2) & 1):   # Format V jr / jarl (bits 10..6 = 11110, hw2[0] = 0)
            h2 = get(pc + 2)
            d = ((h1 & 0x3F) << 16) | (h2 & 0xFFFE)
            d = d - (1 << 22) if d & (1 << 21) else d
            if reg2:
                r[reg2] = pc + 4
            pc = pc + d
            continue
        if h1 & 0xFFE0 == 0x0060:                # jmp [reg1]
            pc = r[reg1] & 0xFFFFFFFF
            continue
        if h1 & 0xFFE0 == 0x0620:                # mov imm32, reg1
            r[reg1] = get(pc + 2) | (get(pc + 4) << 16)
            pc += 6
            continue
        if op6 in (0x16, 0x15, 0x10):            # shl / sar / mov imm5
            imm = h1 & 0x1F
            if op6 == 0x16:
                res = s32(r[reg2] << imm); CY = bool((r[reg2] >> (32 - imm)) & 1) if imm else False
            elif op6 == 0x15:
                res = s32(r[reg2]) >> imm
            else:
                res = imm - 32 if imm & 0x10 else imm
            r[reg2] = s32(res)
            if op6 != 0x10:
                Z, S = r[reg2] == 0, r[reg2] < 0
            pc += 2
            continue
        if op6 in (0x0D, 0x0E, 0x0F):            # sub / add / cmp
            a, b = s32(r[reg2]), s32(r[reg1])
            res = a - b if op6 in (0x0D, 0x0F) else a + b
            ua, ub = a & 0xFFFFFFFF, b & 0xFFFFFFFF
            CY = ua < ub if op6 in (0x0D, 0x0F) else (ua + ub) > 0xFFFFFFFF
            Z = s32(res) == 0
            S = s32(res) < 0
            if op6 != 0x0F:
                r[reg2] = s32(res)
            pc += 2
            continue
        h2 = get(pc + 2)
        if op6 in (0x31, 0x30, 0x36):            # movea / addi / andi
            imm = h2 - 0x10000 if (h2 & 0x8000 and op6 != 0x36) else h2
            if op6 == 0x36:
                res = (r[reg1] & 0xFFFFFFFF) & h2
                Z, S = res == 0, False
            else:
                res = s32(r[reg1] + imm)
                if op6 == 0x30:
                    Z, S = res == 0, res < 0
            r[reg2] = s32(res)
            pc += 4
            continue
        if op6 == 0x3F and (h2 & 1) and reg2:     # ld.hu disp16[reg1], reg2
            disp = (h2 & 0xFFFE) - 0x10000 if h2 & 0x8000 else (h2 & 0xFFFE)
            r[reg2] = mem16((r[reg1] + disp) & 0xFFFFFFFF)
            pc += 4
            continue
        if op6 == 0x3F and (h2 & 0x7FF) == 0x220:  # mul reg1, reg2, reg3
            p = s32(r[reg2]) * s32(r[reg1])
            r[reg2] = s32(p)
            reg3 = h2 >> 11
            if reg3:
                r[reg3] = s32(p >> 32)
            pc += 4
            continue
        if op6 == 0x39 and not (h2 & 1):          # ld.h disp16[reg1], reg2
            disp = h2 - 0x10000 if h2 & 0x8000 else h2
            v = mem16((r[reg1] + disp) & 0xFFFFFFFF)
            r[reg2] = v - 0x10000 if v & 0x8000 else v
            pc += 4
            continue
        raise RuntimeError(f"undecoded halfword {h1:04x} at {pc:#x}")
    raise RuntimeError("no exit")


CONTROLS = [  # (address in V295, expected bytes, the form it controls)
    (0x28F0E, "e4 57 a3 95", "ld.hu -0x6a5e[gp],r10 -> our ld.hu -0x6a5e[gp],r8"),
    (0x35CF8, "e4 37 99 b0", "ld.hu -0x4f68[gp],r6  -> our ld.hu -0x4f68[gp],r8"),
    (0x29D26, "e6 6f 01 00", "ld.hu 0[r6],r13        -> our ld.hu 0/2/6[r9],r13|r8"),
    (0x29CFC, "30 06", "mov imm32,r16           -> our mov imm32,r9"),
    (0x29E50, "ed 41", "cmp r13,r8              -> ours (same bytes)"),
    (0x29ED2, "ed 3f 20 02", "mul r13,r7,r0          -> our mul r13,r8,r0 / mul r8,r16,r0"),
    (0x29E3E, "a8 42", "sar 8,r8                -> our sar 12,r8 / sar 8,r16"),
    (0x52688, "20 6e ff 7f", "movea 0x7fff,r0,r13   -> our movea 512,r0,r13"),
    (0x29A30, "01 32", "mov 1,r6                -> our mov 0,r6"),
    (0x29372, "80 07 c2 03", "jr 0x29734           -> our jr 0x29D7E"),
    (0x2A1E4, "d5 05", "br 0x2A1EE              -> our br (cond 5)"),
    (0x29384, "f3 05", "bnh 0x29392             -> our bnh (cond 3)"),
    (0x29A56, "da 05", "bne 0x29A60             -> our bne (cond A)"),
    (0x29D76, "c2 82 ba 81", "shl 2,r16 ; sub r26,r16 -> displaced verbatim"),
]


def main():
    tbl = C.c1_table()
    code, labels, lines = assemble(tbl)
    img = open(IMG, "rb").read()
    print(f"C1 CAVE at {CAVE:#x}: {len(code)} bytes = {labels['TBL'] - CAVE} code + {len(code) - (labels['TBL'] - CAVE)} "
          f"table ; labels " + " ".join(f"{k}={v:#x}" for k, v in labels.items()))
    print(f"cave region in V295 {CAVE:#x}..{CAVE + len(code):#x} is all 0xFF: "
          f"{all(x == 0xFF for x in img[CAVE:CAVE + len(code)])} ; free span 0xC4BD8..0xC4FEF all 0xFF: "
          f"{all(x == 0xFF for x in img[0xC4BD8:0xC4FF0])}")
    for pc, lab, ins, bs, com in lines:
        print(f"  {pc:#07x} {lab:6s} {bs:18s} {str(ins):38s} {com}")
    hook = enc(("jarl", CAVE, 6), HOOK, {})
    hb = b"".join(struct.pack("<H", h) for h in hook)
    print(f"HOOK at {HOOK:#x}: {img[HOOK:HOOK + 4].hex(' ')} -> {hb.hex(' ')}  (jarl {CAVE:#x}, r6)")
    v112 = enc(("jarl", 0xC4B34, 31), 0x55C0E, {})
    vb = b"".join(struct.pack("<H", h) for h in v112)
    print(f"CONTROL: the flown V112 hook 0x55C0E reads {img[0x55C0E:0x55C12].hex(' ')} ; the encoder gives {vb.hex(' ')} "
          f"for jarl 0xC4B34, lp -> {'MATCH' if vb == img[0x55C0E:0x55C12] else 'MISMATCH'}")
    print("ENCODING-FORM CONTROLS (V295 bytes):")
    for a, exp, what in CONTROLS:
        got = img[a:a + len(bytes.fromhex(exp.replace(' ', '')))].hex(" ")
        print(f"  {a:#07x} {got:12s} {'OK ' if got == exp else 'BAD'} {what}")
    # interpreter self-check on the controls that are branches / jr (decode the image's own bytes)
    # --- H1 at design time: execute the assembled bytes vs the mirror on random inputs ---
    rng = np.random.default_rng(7)
    tb = {CAVE + i: code[i] for i in range(len(code))}

    def mem16_factory(v, tq):
        def m(a):
            if a == (GP - 0x6A5E) & 0xFFFFFFFF:
                return v
            if a == (GP - 0x4F68) & 0xFFFFFFFF:
                return tq
            if CAVE <= a < CAVE + len(code):
                return tb[a] | (tb[a + 1] << 8)
            raise RuntimeError(f"load from {a:#x}")
        return m
    core = C._C1Core()
    core.setup_cave(1, [dict(tbl=tbl, thr=C.FRZ_THR, rampfrz=True, pol="freeze")])
    core.I8 = np.zeros(1, np.int64)
    bad = 0
    N = 200000
    for k in range(N):
        sp = int(rng.integers(-16384, 16385)) if k % 50 else 32767
        r26 = int(rng.integers(-65535, 65536))
        edges = [0, 32000, 65535] + [x + d for x, _, _ in tbl if x < 0xFFFF for d in (-1, 0, 1)]   # this table's knots +-1
        v = int(rng.integers(0, 32001)) if k % 7 else int(rng.choice(edges))
        tq = int(rng.integers(0, 3000)) if k % 3 else int(rng.choice([0, 511, 512, 513, 65535]))
        ramp = int(rng.choice([0x8000, 0x8000, 0x8000, int(rng.integers(1, 0x8000))]))
        regs = {i: int(rng.integers(-2**31, 2**31)) for i in range(32)}
        regs.update({0: 0, 16: sp, 26: r26, 14: ramp, 4: GP - (1 << 32), 6: RET})
        pc_exit, rr = run_bytes(code, CAVE, regs, mem16_factory(v, tq), CAVE)
        E = s32((sp << 2) - r26)
        Ep, frz, G = core.cave(np.array([E], np.int64), np.array([tq], np.int64), np.array([ramp], np.int64),
                               np.array([v], np.int64))
        ok = (rr[16] == int(Ep[0])) and ((pc_exit == FRZ_RET) == bool(frz[0]))
        ok = ok and (pc_exit != FRZ_RET or rr[6] == 0)
        ok = ok and all(rr[i] == regs[i] for i in range(32) if i not in (6, 8, 9, 13, 16))
        if not ok:
            bad += 1
            if bad < 5:
                print("  MISMATCH", dict(sp=sp, r26=r26, v=v, tq=tq, ramp=ramp), rr[16], int(Ep[0]), hex(pc_exit), frz)
    print(f"H1 (design time): the assembled bytes, executed by the interpreter, vs the mirror cave on {N} random "
          f"(E, v, |tq|, ramp, register file) inputs incl. the 0x7FFF sentinel and the table edges: {bad} mismatches "
          f"(checked: r16 = E', exit address = freeze, r6 = 0 on freeze, every register except r6/r8/r9/r13/r16 "
          f"unchanged)")
    print(f"   (r25 -- live 0x29A82..0x2A0AC across the hook per the 2026-09-30 dominance trace -- is among the registers "
          f"checked unchanged: {25 not in (6, 8, 9, 13, 16)})")
    (HERE / ("c1_cave.bin.hex" if C._VAR == "kd16" else f"c1_cave_{C._VAR}.bin.hex")).write_text(code.hex(" "))
    return code, labels


if __name__ == "__main__":
    main()
